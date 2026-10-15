from collections.abc import Callable, Generator
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.database import get_db
from app.main import app
from app.models import answer, favorite, progress, question  # noqa: F401
from app.models.progress import QuestionProgress
from app.models.question import Question


@pytest.fixture
def db(tmp_path) -> Generator[Session, None, None]:
    """Give every test an isolated SQLite database."""
    database_path = tmp_path / "interview-test.db"
    engine = create_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def question_factory(db: Session) -> Callable[..., Question]:
    def create_question(
        *,
        module: str = "network",
        chapter: str = "测试章节",
        q_type: str = "choice",
        stem: str,
        answer: str = "A",
        options: dict[str, str] | None = None,
        explanation: str = "测试解析",
        difficulty: int = 2,
    ) -> Question:
        question = Question(
            module=module,
            chapter=chapter,
            type=q_type,
            stem=stem,
            answer=answer,
            options=options if q_type == "choice" else None,
            explanation=explanation,
            difficulty=difficulty,
        )
        db.add(question)
        db.commit()
        return question

    return create_question


@pytest.fixture
def progress_factory(db: Session) -> Callable[..., QuestionProgress]:
    def create_progress(
        question: Question,
        *,
        mastery_level: int = 1,
        attempt_count: int = 1,
        correct_count: int = 0,
        consecutive_correct: int = 0,
        next_review_at: datetime | None = None,
    ) -> QuestionProgress:
        progress = QuestionProgress(
            question_id=question.id,
            mastery_level=mastery_level,
            attempt_count=attempt_count,
            correct_count=correct_count,
            consecutive_correct=consecutive_correct,
            last_answered_at=datetime.now(),
            next_review_at=next_review_at or datetime.now() - timedelta(minutes=1),
        )
        db.add(progress)
        db.commit()
        return progress

    return create_progress


@pytest.fixture
def client(db: Session) -> Generator[TestClient, None, None]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
