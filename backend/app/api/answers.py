from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.question import Question
from app.schemas.answer import (
    AnswerSubmit,
    GradeResult,
    ShortAnswerPreviewResult,
    ShortAnswerPreviewSubmit,
)
from app.services.answer_service import analyze_short_answer, grade_answer

router = APIRouter(prefix="/api/answers", tags=["作答"])


@router.post(
    "/preview",
    response_model=ShortAnswerPreviewResult,
    summary="分析简答题关键点，不记录作答",
)
def preview_short_answer(
    body: ShortAnswerPreviewSubmit,
    db: Session = Depends(get_db),
):
    question = db.get(Question, body.question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="题目不存在")
    try:
        return analyze_short_answer(question, body.user_answer)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


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
            self_rating=body.self_rating,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
