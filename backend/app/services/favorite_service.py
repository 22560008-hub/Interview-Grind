from sqlalchemy.orm import Session

from app.models.favorite import Favorite
from app.models.question import Question


def add_favorite(db: Session, question_id: int) -> bool:
    exists = db.query(Favorite).filter_by(question_id=question_id).first()
    if exists:
        return False
    db.add(Favorite(question_id=question_id))
    db.commit()
    return True


def remove_favorite(db: Session, question_id: int) -> bool:
    fav = db.query(Favorite).filter_by(question_id=question_id).first()
    if fav is None:
        return False
    db.delete(fav)
    db.commit()
    return True


def list_favorites(db: Session):
    rows = (
        db.query(Favorite, Question)
        .join(Question, Favorite.question_id == Question.id)
        .filter(Question.is_active.is_(True))
        .order_by(Favorite.created_at.desc())
        .all()
    )
    result = []
    for fav, question in rows:
        result.append(
            {
                "question_id": question.id,
                "module": question.module,
                "stem": question.stem,
                "answer": question.answer,
                "explanation": question.explanation,
            }
        )
    return result
