from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text, UniqueConstraint
from datetime import datetime
from app.core.database import Base


class DailyPractice(Base):
    __tablename__ = "daily_practice"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, unique=True, index=True)  # 哪一天，比如 "2026-10-16"
    question_ids = Column(String)  # 当天出了哪些题，存 "1,5,10,22,30"
    total = Column(Integer, default=5)  # 总题数
    correct = Column(Integer, default=0)  # 答对几道
    is_completed = Column(Boolean, default=False)  # 是否做完
    started_at = Column(DateTime, default=datetime.now)  # 开始时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间


class DailyPracticeItem(Base):
    __tablename__ = "daily_practice_item"
    __table_args__ = (
        UniqueConstraint(
            "practice_id", "question_id", name="uq_daily_practice_question"
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    practice_id = Column(Integer, nullable=False, index=True)
    question_id = Column(Integer, nullable=False, index=True)
    position = Column(Integer, nullable=False)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime, nullable=True)
