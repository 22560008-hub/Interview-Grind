from datetime import datetime
from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class QuestionProgress(Base):
    __tablename__ = "question_progress"

    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(
        Integer, ForeignKey("question.id"), unique=True, nullable=False
    )
    attempt_count = Column(Integer, default=0)  # 答过几次
    correct_count = Column(Integer, default=0)  # 答对几次
    consecutive_correct = Column(Integer, default=0)  # 连续答对几次
    mastery_level = Column(Integer, default=0)  # 0=没做过 1=薄弱 2=一般 3=熟练
    last_answered_at = Column(DateTime, nullable=True)  # 上次答题时间
    next_review_at = Column(DateTime, nullable=True)  # 下次该复习时间

    question = relationship("Question")
