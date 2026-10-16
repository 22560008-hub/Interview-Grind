from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.daily_service import (
    ensure_daily_items,
    get_daily_questions,
    parse_question_ids,
)
from app.models.daily import DailyPractice, DailyPracticeItem
from app.models.question import Question
from datetime import date
import random

router = APIRouter(prefix="/api/daily", tags=["每日一练"])


@router.get("", summary="获取今日题目和进度")
def daily(db: Session = Depends(get_db)):
    questions = get_daily_questions(db, count=5)
    today = date.today().isoformat()
    practice = db.query(DailyPractice).filter_by(date=today).first()
    return {
        "date": today,
        "practice_id": practice.id if practice else None,
        "count": len(questions),
        "questions": questions,
        "correct": practice.correct if practice else 0,
        "is_completed": practice.is_completed if practice else False,
    }


@router.post("/extend", summary="追加5道每日练习")
def extend_daily(db: Session = Depends(get_db)):
    today = date.today().isoformat()
    practice = db.query(DailyPractice).filter_by(date=today).first()
    if not practice:
        return {"error": "请先开始今日练习"}

    items = ensure_daily_items(db, practice)
    existing_ids = [item.question_id for item in items]
    if not existing_ids:
        existing_ids = parse_question_ids(practice.question_ids)
    all_questions = db.query(Question).filter(~Question.id.in_(existing_ids)).all()

    if not all_questions:
        return {"questions": [], "count": 0}

    random.shuffle(all_questions)
    new_questions = all_questions[:5]

    new_ids = [q.id for q in new_questions]
    practice.question_ids = ",".join(str(i) for i in existing_ids + new_ids)
    practice.total = len(existing_ids) + len(new_ids)
    practice.is_completed = False
    practice.completed_at = None
    for offset, question in enumerate(new_questions, start=len(existing_ids)):
        db.add(
            DailyPracticeItem(
                practice_id=practice.id,
                question_id=question.id,
                position=offset,
            )
        )
    db.commit()

    all_results = get_daily_questions(db, count=practice.total)
    results_by_id = {item["id"]: item for item in all_results}
    result = [results_by_id[question_id] for question_id in new_ids]
    return {"questions": result, "count": len(result)}
