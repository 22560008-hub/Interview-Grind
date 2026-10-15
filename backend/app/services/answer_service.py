from sqlalchemy.orm import Session

from app.models.answer import AnswerRecord, WrongQuestion
from app.models.question import Question
from app.models.progress import QuestionProgress
from datetime import datetime, timedelta


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

        # 更新题目进度
    progress = db.query(QuestionProgress).filter_by(question_id=question.id).first()
    if not progress:
        progress = QuestionProgress(
            question_id=question.id,
            attempt_count=0,
            correct_count=0,
            consecutive_correct=0,
            mastery_level=0,
        )
        db.add(progress)

    progress.attempt_count += 1
    progress.last_answered_at = datetime.now()

    if is_correct:
        progress.correct_count += 1
        progress.consecutive_correct += 1
        # 根据连续答对次数更新掌握程度
        if progress.consecutive_correct >= 3:
            progress.mastery_level = 3  # 熟练
        elif progress.consecutive_correct >= 1:
            progress.mastery_level = 2  # 一般
        # 答对了，下次复习往后推
        intervals = [
            0,
            1,
            3,
            7,
            14,
        ]  # 连续对0次→今天再练，1次→1天后，2次→3天后，3次→7天后...
        idx = min(progress.consecutive_correct, len(intervals) - 1)
        progress.next_review_at = datetime.now() + timedelta(days=intervals[idx])
    else:
        progress.consecutive_correct = 0
        progress.mastery_level = 1  # 薄弱
        # 答错了，马上再复习
        progress.next_review_at = datetime.now()

    db.commit()

    return {
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
    }
