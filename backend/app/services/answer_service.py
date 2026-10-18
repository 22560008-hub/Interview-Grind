from datetime import datetime, timedelta
from html import escape

from sqlalchemy.orm import Session

from app.core.constants import QuestionType
from app.models.answer import AnswerRecord, WrongQuestion
from app.models.daily import DailyPractice, DailyPracticeItem
from app.models.progress import QuestionProgress
from app.models.question import Question
from app.services.key_point_matcher import match_key_points


def analyze_short_answer(question: Question, user_answer: str) -> dict:
    if question.type == QuestionType.CHOICE.value:
        raise ValueError("选择题不支持简答题预判")

    key_points = question.key_points or []
    match = match_key_points(key_points, user_answer)
    return {
        "display_user_answer": escape(user_answer),
        "correct_answer": question.answer,
        "explanation": question.explanation,
        "matched_points": match.matched,
        "missing_points": match.missing,
        "uncertain_points": match.uncertain,
        "coverage": match.coverage,
        "requires_self_rating": True,
    }


def grade_answer(
    db: Session,
    question_id: int,
    user_answer: str,
    daily_practice_id: int | None = None,
    self_rating: str | None = None,
) -> dict:
    # 1. 根据 question_id 查出这道题
    question = db.get(Question, question_id)
    if question is None:
        raise LookupError("题目不存在")
    if question.type != QuestionType.CHOICE.value and self_rating is None:
        raise ValueError("简答题提交前请选择掌握程度")

    daily_item = None
    practice = None
    if daily_practice_id is not None:
        practice = db.get(DailyPractice, daily_practice_id)
        daily_item = (
            db.query(DailyPracticeItem)
            .filter_by(
                practice_id=daily_practice_id,
                question_id=question_id,
            )
            .first()
        )
        if practice is None or daily_item is None:
            raise ValueError("题目不属于这次每日练习")
        if daily_item.user_answer is not None:
            return {
                "is_correct": daily_item.is_correct,
                "correct_answer": question.answer,
                "explanation": question.explanation,
                "display_user_answer": escape(daily_item.user_answer),
                "self_rating": None,
            }

    # 2. 判分：忽略大小写和首尾空格，比较用户答案和正确答案
    if question.type == QuestionType.CHOICE.value:
        # 选择题：精确匹配（A/B/C/D）
        is_correct = user_answer.strip().upper() == question.answer.strip().upper()
    else:
        # 简答题先展示关键点反馈，再由用户自评决定本次学习结果。
        is_correct = self_rating == "mastered"

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
        if question.type != QuestionType.CHOICE.value and self_rating == "fuzzy":
            progress.next_review_at = datetime.now() + timedelta(days=1)
        else:
            # 选择题答错或简答题选择“不会”，马上再复习。
            progress.next_review_at = datetime.now()

    if daily_item is not None:
        daily_item.user_answer = user_answer
        daily_item.is_correct = is_correct
        daily_item.answered_at = datetime.now()
        db.flush()

        answered_count = (
            db.query(DailyPracticeItem)
            .filter_by(practice_id=practice.id)
            .filter(DailyPracticeItem.user_answer.is_not(None))
            .count()
        )
        practice.correct = (
            db.query(DailyPracticeItem)
            .filter_by(practice_id=practice.id, is_correct=True)
            .count()
        )
        practice.is_completed = practice.total > 0 and answered_count >= practice.total
        practice.completed_at = datetime.now() if practice.is_completed else None

    db.commit()

    return {
        "is_correct": is_correct,
        "correct_answer": question.answer,
        "explanation": question.explanation,
        "display_user_answer": escape(user_answer),
        "self_rating": self_rating,
    }
