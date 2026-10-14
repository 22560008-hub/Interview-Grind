from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Favorite(Base):
    __tablename__ = "favorite"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, comment="收藏的题目"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="收藏时间"
    )
