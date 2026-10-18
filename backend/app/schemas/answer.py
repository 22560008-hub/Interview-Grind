from typing import Literal

from pydantic import BaseModel


class AnswerSubmit(BaseModel):
    """用户提交答案时，前端要发过来的数据格式。"""

    question_id: int
    user_answer: str
    daily_practice_id: int | None = None
    self_rating: Literal["mastered", "fuzzy", "unknown"] | None = None


class ShortAnswerPreviewSubmit(BaseModel):
    question_id: int
    user_answer: str


class ShortAnswerPreviewResult(BaseModel):
    display_user_answer: str
    correct_answer: str
    explanation: str = ""
    matched_points: list[str]
    missing_points: list[str]
    uncertain_points: list[str] = []
    coverage: int
    requires_self_rating: bool = True


class GradeResult(BaseModel):
    """判分后返回给前端的结果。"""

    is_correct: bool
    correct_answer: str
    explanation: str = ""
    display_user_answer: str
    self_rating: Literal["mastered", "fuzzy", "unknown"] | None = None
