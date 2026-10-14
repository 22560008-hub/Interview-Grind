from pydantic import BaseModel


class QuestionOut(BaseModel):
    id: int
    module: str
    chapter: str
    type: str
    stem: str
    options: dict | None = None
    answer: str
    explanation: str = ""
    difficulty: int = 1

    model_config = {"from_attributes": True}
