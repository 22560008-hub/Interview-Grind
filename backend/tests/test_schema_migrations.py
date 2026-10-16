from sqlalchemy import create_engine, inspect

from app.core import database


def test_schema_upgrade_adds_key_points_to_existing_question_table(tmp_path):
    legacy_database = tmp_path / "legacy.db"
    engine = create_engine(f"sqlite:///{legacy_database}")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE question (id INTEGER PRIMARY KEY, stem TEXT NOT NULL)"
        )

    assert hasattr(database, "ensure_question_key_points_column")
    database.ensure_question_key_points_column(engine)
    database.ensure_question_key_points_column(engine)

    columns = {column["name"] for column in inspect(engine).get_columns("question")}
    assert "key_points" in columns
    engine.dispose()
