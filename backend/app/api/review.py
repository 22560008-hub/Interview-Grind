from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.review_service import get_review_questions

router = APIRouter(prefix="/api/review", tags=["复习"])


@router.get("", summary="查看待复习题目")
def review(db: Session = Depends(get_db)):
    questions = get_review_questions(db, limit=10)
    return {
        "count": len(questions),
        "questions": questions,
    }
