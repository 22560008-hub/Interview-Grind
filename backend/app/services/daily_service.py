import random
from datetime import date
from sqlalchemy.orm import Session
from app.models.question import Question
from app.models.progress import QuestionProgress


def get_daily_questions(db: Session, count: int = 5):
    """根据日期返回当天固定的题目列表。"""
    today = date.today().isoformat()
    all_questions = db.query(Question).all()
    if len(all_questions) <= count:
        selected = all_questions
    else:
        rng = random.Random(today)
        selected = rng.sample(all_questions, count)

    result = []
    for q in selected:
        progress = db.query(QuestionProgress).filter_by(question_id=q.id).first()
        result.append(
            {
                "id": q.id,
                "module": q.module,
                "chapter": q.chapter,
                "type": q.type,
                "stem": q.stem,
                "options": q.options,
                "answer": q.answer,
                "explanation": q.explanation,
                "mastery_level": progress.mastery_level if progress else 0,
            }
        )
    return result
