from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.wrong_service import list_wrong_questions

router = APIRouter(prefix="/api/wrong-questions", tags=["错题本"])


@router.get("", summary="查看错题本列表")
def get_wrong_questions(db: Session = Depends(get_db)):
    return list_wrong_questions(db)
