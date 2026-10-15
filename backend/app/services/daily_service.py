import random
from datetime import date, datetime
from sqlalchemy.orm import Session
from app.models.question import Question
from app.models.progress import QuestionProgress


def get_daily_questions(
    db: Session, count: int = 5, exclude_ids: list[int] | None = None
):
    """按 50%复习 + 30%薄弱 + 20%新题 选题。"""
    today = date.today().isoformat()
    rng = random.Random(today)

    if exclude_ids is None:
        exclude_ids = []

    all_questions = db.query(Question).filter(~Question.id.in_(exclude_ids)).all()
    if len(all_questions) <= count:
        selected = all_questions
    else:
        now = datetime.now()

        # 1. 到期复习题：next_review_at <= 现在，且没到熟练
        review_ids = [
            row[0]
            for row in db.query(QuestionProgress.question_id)
            .filter(QuestionProgress.next_review_at <= now)
            .filter(QuestionProgress.mastery_level < 3)
            .all()
        ]
        review_pool = [q for q in all_questions if q.id in review_ids]
        rng.shuffle(review_pool)

        # 2. 薄弱题：mastery_level = 1
        weak_ids = [
            row[0]
            for row in db.query(QuestionProgress.question_id)
            .filter(QuestionProgress.mastery_level == 1)
            .all()
        ]
        weak_pool = [
            q for q in all_questions if q.id in weak_ids and q.id not in review_ids
        ]
        rng.shuffle(weak_pool)

        # 3. 新题：progress 表里没有记录的
        answered_ids = [row[0] for row in db.query(QuestionProgress.question_id).all()]
        new_pool = [q for q in all_questions if q.id not in answered_ids]
        rng.shuffle(new_pool)

        # 按比例取：复习2-3道，薄弱1-2道，新题1道
        selected = []
        selected.extend(review_pool[:3])  # 最多3道复习
        selected.extend(weak_pool[:2])  # 最多2道薄弱
        selected.extend(new_pool[:1])  # 1道新题

        # 不够5道就从剩下的题里补
        remaining = [q for q in all_questions if q not in selected]
        rng.shuffle(remaining)
        while len(selected) < count:
            selected.append(remaining.pop())

        selected = selected[:count]

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
