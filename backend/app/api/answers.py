from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.answer import AnswerSubmit, GradeResult
from app.services.answer_service import grade_answer

router = APIRouter(prefix="/api/answers", tags=["作答"])


@router.post("", response_model=GradeResult, summary="提交答案，返回判分结果")
def submit_answer(
    body: AnswerSubmit,
    db: Session = Depends(get_db),
):
    try:
        return grade_answer(
            db,
            question_id=body.question_id,
            user_answer=body.user_answer,
            daily_practice_id=body.daily_practice_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
