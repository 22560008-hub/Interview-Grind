from pydantic import BaseModel


class AnswerSubmit(BaseModel):
    """用户提交答案时，前端要发过来的数据格式。"""

    question_id: int
    user_answer: str


class GradeResult(BaseModel):
    """判分后返回给前端的结果。"""

    is_correct: bool
    correct_answer: str
    explanation: str = ""
