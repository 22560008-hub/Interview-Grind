from sqlalchemy import create_engine, inspect

from app.core import database


def test_schema_upgrade_adds_question_columns_to_legacy_table(tmp_path):
    legacy_database = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{legacy_database}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE question (id INTEGER PRIMARY KEY, stem TEXT NOT NULL)"
        )

    assert hasattr(database, "ensure_question_schema")
    database.ensure_question_schema(engine)
    database.ensure_question_schema(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("question")}
    assert {"key_points", "code", "is_active"} <= columns

    index_names = {index["name"] for index in inspect(engine).get_indexes("question")}
    assert "ix_question_code" in index_names
    assert "ix_question_is_active" in index_names
    engine.dispose()
