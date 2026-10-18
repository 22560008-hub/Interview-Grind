from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

_connect_args = (
    {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


# 题库表从旧版本升级时需要补的列。每加一列就往这里登记一条，
# 这样老数据库（包括只有 id/stem 的最早版本）都能原地升级、不丢数据。
_QUESTION_COLUMNS = {
    "key_points": "ALTER TABLE question ADD COLUMN key_points JSON",
    "code": "ALTER TABLE question ADD COLUMN code VARCHAR(64)",
    "is_active": (
        "ALTER TABLE question ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
    ),
}

_QUESTION_INDEXES = {
    "ix_question_code": (
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_question_code ON question (code)"
    ),
    "ix_question_is_active": (
        "CREATE INDEX IF NOT EXISTS ix_question_is_active ON question (is_active)"
    ),
}


def ensure_question_schema(database_engine: Engine) -> None:
    """把旧版 question 表原地升级到当前模型，重复执行安全。

    已经是最新结构时直接返回，不开启写事务——正常启动和测试都不会因为
    数据库只读而失败，只有真正需要升级时才写库。
    """
    inspector = inspect(database_engine)
    if "question" not in inspector.get_table_names():
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("question")
    }
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("question")
    }
    missing_columns = [
        ddl for name, ddl in _QUESTION_COLUMNS.items() if name not in existing_columns
    ]
    missing_indexes = [
        ddl
        for name, ddl in _QUESTION_INDEXES.items()
        if name not in existing_indexes
    ]
    if not missing_columns and not missing_indexes:
        return

    with database_engine.begin() as connection:
        for ddl in missing_columns:
            connection.exec_driver_sql(ddl)
        for ddl in missing_indexes:
            connection.exec_driver_sql(ddl)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
