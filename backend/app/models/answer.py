from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AnswerRecord(Base):
    __tablename__ = "answer_record"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(Integer, index=True, comment="哪道题")
    user_answer: Mapped[str] = mapped_column(Text, comment="用户的答案")
    is_correct: Mapped[bool] = mapped_column(Boolean, comment="是否答对")
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="作答时间"
    )


class WrongQuestion(Base):
    __tablename__ = "wrong_question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(
        Integer, unique=True, index=True, comment="错题ID，唯一"
    )
    wrong_count: Mapped[int] = mapped_column(Integer, default=1, comment="累计答错次数")
    last_wrong_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, comment="最近答错时间"
    )
