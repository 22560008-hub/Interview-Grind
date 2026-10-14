from sqlalchemy.orm import Session

from app.models.answer import AnswerRecord, WrongQuestion
from app.models.question import Question


def grade_answer(db: Session, question_id: int, user_answer: str) -> dict:
    # 1. 根据 question_id 查出这道题
    question = db.get(Question, question_id)
    if question is None:
        return {"error": "题目不存在"}

    # 2. 判分：忽略大小写和首尾空格，比较用户答案和正确答案
    if question.type == "choice":
        # 选择题：精确匹配（A/B/C/D）
        is_correct = user_answer.strip().upper() == question.answer.strip().upper()
    else:
        # 简答题：把正确答案按顿号拆成关键词，用户答案里包含所有关键词就算对
        keywords = [k.strip() for k in question.answer.split("、") if k.strip()]
        user_lower = user_answer.lower()
        is_correct = all(kw.lower() in user_lower for kw in keywords)

    # 3. 写一条作答流水
    db.add(
        AnswerRecord(
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct,
        )
    )

    # 4. 如果答错了，收进错题本
    if not is_correct:
        wrong = db.query(WrongQuestion).filter_by(question_id=question_id).first()
        if wrong:
            wrong.wrong_count += 1  # 已经在错题本里，错次+1
        else:
            db.add(WrongQuestion(question_id=question_id, wrong_count=1))  # 新错题

    db.commit()

    return {
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
    }
