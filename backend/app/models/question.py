from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    module: Mapped[str] = mapped_column(String(32), index=True, comment="所属模块")
    chapter: Mapped[str] = mapped_column(String(64), default="", comment="章节")
    type: Mapped[str] = mapped_column(String(16), index=True, comment="题型")
    stem: Mapped[str] = mapped_column(Text, comment="题干")
    options: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="选项")
    answer: Mapped[str] = mapped_column(Text, comment="参考答案")
    key_points: Mapped[list[str] | None] = mapped_column(
        JSON, nullable=True, comment="简答题关键点"
    )
    explanation: Mapped[str] = mapped_column(Text, default="", comment="解析")
    difficulty: Mapped[int] = mapped_column(Integer, default=1, comment="难度")
