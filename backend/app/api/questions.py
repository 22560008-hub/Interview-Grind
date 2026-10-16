from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.question_service import pick_questions
from app.models.progress import QuestionProgress

router = APIRouter(prefix="/api/questions", tags=["题目"])


@router.get("", summary="组卷：按模块/题型/题量随机抽题")
def list_questions(
    module: str | None = Query(None),
    type: str | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    questions = pick_questions(db, module=module, q_type=type, limit=limit)
    result = []
    for q in questions:
        progress = db.query(QuestionProgress).filter_by(question_id=q.id).first()
        result.append(
            {
                "id": q.id,
                "module": q.module,
                "chapter": q.chapter,
                "type": q.type,
                "stem": q.stem,
                "options": q.options,
                "mastery_level": progress.mastery_level if progress else 0,
            }
        )
    return result
