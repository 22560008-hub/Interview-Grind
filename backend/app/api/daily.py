from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.daily_service import get_daily_questions

router = APIRouter(prefix="/api/daily", tags=["每日一练"])


@router.get("", summary="获取今日题目")
def daily(db: Session = Depends(get_db)):
    questions = get_daily_questions(db, count=5)
    return {
        "date": str(__import__("datetime").date.today()),
        "count": len(questions),
        "questions": questions,
    }
