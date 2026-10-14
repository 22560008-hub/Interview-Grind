from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.wrong_service import list_wrong_questions, remove_wrong_question

router = APIRouter(prefix="/api/wrong-questions", tags=["错题本"])


@router.get("", summary="查看错题本列表")
def get_wrong_questions(db: Session = Depends(get_db)):
    return list_wrong_questions(db)


@router.delete("/{question_id}", summary="已掌握，移出错题本")
def delete_wrong_question(question_id: int, db: Session = Depends(get_db)):
    ok = remove_wrong_question(db, question_id)
    if not ok:
        raise HTTPException(status_code=404, detail="错题不存在")
    return {"deleted": question_id}
