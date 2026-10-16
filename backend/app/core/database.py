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


def ensure_question_key_points_column(database_engine: Engine) -> None:
    """Upgrade databases created before structured short-answer key points."""
    inspector = inspect(database_engine)
    if "question" not in inspector.get_table_names():
        return
    column_names = {
        column["name"] for column in inspector.get_columns("question")
    }
    if "key_points" in column_names:
        return
    with database_engine.begin() as connection:
        connection.exec_driver_sql(
            "ALTER TABLE question ADD COLUMN key_points JSON"
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
