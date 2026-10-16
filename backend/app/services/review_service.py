from datetime import datetime
from sqlalchemy.orm import Session
from app.models.question import Question
from app.models.progress import QuestionProgress


def get_review_questions(db: Session, limit: int = 10):
    """查出所有该复习的题：next_review_at <= 现在，且还没熟练。"""
    now = datetime.now()
    results = (
        db.query(Question, QuestionProgress)
        .join(QuestionProgress, Question.id == QuestionProgress.question_id)
        .filter(QuestionProgress.next_review_at <= now)
        .filter(QuestionProgress.mastery_level < 3)
        .order_by(QuestionProgress.next_review_at)
        .limit(limit)
        .all()
    )
    questions = []
    for q, p in results:
        q_dict = {
            "id": q.id,
            "module": q.module,
            "chapter": q.chapter,
            "type": q.type,
            "stem": q.stem,
            "options": q.options,
            "mastery_level": p.mastery_level,
            "next_review_at": p.next_review_at.strftime("%Y-%m-%d %H:%M"),
        }
        questions.append(q_dict)
    return questions
