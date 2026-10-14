from sqlalchemy.orm import Session

from app.models.answer import WrongQuestion
from app.models.question import Question


def list_wrong_questions(db: Session):
    # 错题本和题目表关联查：错题本只存了 question_id，题目内容在 question 表里
    rows = (
        db.query(WrongQuestion, Question)
        .join(Question, WrongQuestion.question_id == Question.id)
        .order_by(WrongQuestion.last_wrong_at.desc())
        .all()
    )

    result = []
    for wrong, question in rows:
        result.append(
            {
                "wrong_id": wrong.id,
                "wrong_count": wrong.wrong_count,
                "question_id": question.id,
                "module": question.module,
                "type": question.type,
                "stem": question.stem,
                "answer": question.answer,
                "explanation": question.explanation,
            }
        )
    return result
