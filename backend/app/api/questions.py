from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.question import QuestionOut
from app.services.question_service import pick_questions

router = APIRouter(prefix="/api/questions", tags=["题目"])


@router.get(
    "", response_model=list[QuestionOut], summary="组卷：按模块/题型/题量随机抽题"
)
def list_questions(
    module: str | None = Query(
        None, description="模块：os/network/db/algorithm/pattern"
    ),
    type: str | None = Query(None, description="题型：choice/judge/short_answer"),
    limit: int = Query(10, ge=1, le=50, description="抽题数量 1-50"),
    db: Session = Depends(get_db),
):
    return pick_questions(db, module=module, q_type=type, limit=limit)
