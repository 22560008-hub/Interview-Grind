from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.favorite_service import (
    add_favorite,
    list_favorites,
    remove_favorite,
)

router = APIRouter(prefix="/api/favorites", tags=["收藏"])


@router.get("", summary="查看收藏列表")
def get_favorites(db: Session = Depends(get_db)):
    return list_favorites(db)


@router.post("/{question_id}", summary="收藏一道题")
def create_favorite(question_id: int, db: Session = Depends(get_db)):
    ok = add_favorite(db, question_id)
    if not ok:
        raise HTTPException(status_code=400, detail="已经收藏过了")
    return {"favorited": question_id}


@router.delete("/{question_id}", summary="取消收藏")
def delete_favorite(question_id: int, db: Session = Depends(get_db)):
    ok = remove_favorite(db, question_id)
    if not ok:
        raise HTTPException(status_code=404, detail="没收藏过这道题")
    return {"deleted": question_id}
