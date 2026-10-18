from sqlalchemy import Boolean, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.database import Base


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=True,
        comment="稳定标识，用于题干改写后仍能对上同一道题",
    )
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
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=text("1"),
        nullable=False,
        index=True,
        comment="是否在役；退出题库的题只停用、不删除",
    )
