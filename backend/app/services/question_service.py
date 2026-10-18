import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.question import Question


def pick_questions(
    db: Session,
    module: str | None = None,
    q_type: str | None = None,
    limit: int = 10,
) -> list[Question]:
    stmt = select(Question).where(Question.is_active.is_(True))
    if module:
        stmt = stmt.where(Question.module == module)
    if q_type:
        stmt = stmt.where(Question.type == q_type)

    rows = list(db.scalars(stmt).all())
    random.shuffle(rows)
    return rows[:limit]
