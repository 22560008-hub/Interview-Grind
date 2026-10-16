from datetime import date, timedelta
from html import escape

from sqlalchemy.orm import Session

from app.models.daily import DailyPractice, DailyPracticeItem
from app.models.question import Question
from app.services.daily_service import ensure_daily_items


def get_daily_history(db: Session, days: int, today: date | None = None) -> dict:
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    practices = (
        db.query(DailyPractice)
        .filter(DailyPractice.date >= start.isoformat())
        .filter(DailyPractice.date <= today.isoformat())
        .order_by(DailyPractice.date.desc())
        .all()
    )

    # 旧版本只保存 question_ids；首次查看历史时补齐题目明细。
    for practice in practices:
        ensure_daily_items(db, practice)

    practice_ids = [practice.id for practice in practices]
    items_by_practice: dict[int, list[DailyPracticeItem]] = {
        practice_id: [] for practice_id in practice_ids
    }
    if practice_ids:
        items = (
            db.query(DailyPracticeItem)
            .filter(DailyPracticeItem.practice_id.in_(practice_ids))
            .all()
        )
        for item in items:
            items_by_practice[item.practice_id].append(item)

    records = []
    for practice in practices:
        items = items_by_practice[practice.id]
        answered = sum(item.user_answer is not None for item in items)
        correct = sum(
            item.user_answer is not None and item.is_correct is True for item in items
        )
        records.append(
            {
                "date": practice.date,
                "total": practice.total,
                "answered": answered,
                "correct": correct,
                "accuracy": round(correct / answered * 100) if answered else 0,
                "completion_rate": (
                    round(answered / practice.total * 100) if practice.total else 0
                ),
                "is_completed": practice.is_completed,
            }
        )

    completed_dates = {
        value
        for (value,) in (
            db.query(DailyPractice.date)
            .filter(DailyPractice.date <= today.isoformat())
            .filter(DailyPractice.is_completed.is_(True))
            .all()
        )
    }
    cursor = today if today.isoformat() in completed_dates else today - timedelta(days=1)
    streak = 0
    while cursor.isoformat() in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return {"streak": streak, "records": records}


def get_daily_history_detail(db: Session, day: date) -> dict | None:
    day_text = day.isoformat()
    practice = db.query(DailyPractice).filter_by(date=day_text).first()
    if practice is None:
        return None

    items = ensure_daily_items(db, practice)
    question_ids = [item.question_id for item in items]
    questions_by_id = {
        question.id: question
        for question in db.query(Question).filter(Question.id.in_(question_ids)).all()
    }

    questions = []
    for item in items:
        question = questions_by_id.get(item.question_id)
        if question is None:
            continue
        answered = item.user_answer is not None
        questions.append(
            {
                "id": question.id,
                "module": question.module,
                "type": question.type,
                "stem": question.stem,
                "options": question.options,
                "user_answer": item.user_answer,
                "display_user_answer": (
                    escape(item.user_answer) if answered else None
                ),
                "is_correct": item.is_correct,
                "correct_answer": question.answer if answered else None,
                "explanation": question.explanation if answered else None,
            }
        )

    return {"date": day_text, "questions": questions}
