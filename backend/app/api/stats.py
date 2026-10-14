from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.stats_service import get_stats

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("", summary="学习统计：总正确率、各模块正确率")
def stats(db: Session = Depends(get_db)):
    return get_stats(db)
