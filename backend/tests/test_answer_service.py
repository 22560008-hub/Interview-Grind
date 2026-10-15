from datetime import datetime, timedelta

from app.models.answer import AnswerRecord, WrongQuestion
from app.models.progress import QuestionProgress
from app.services.answer_service import grade_answer


def test_wrong_answer_records_attempt_wrong_question_and_due_progress(db, question_factory):
    question = question_factory(
        stem="答错后立即复习", options={"A": "正确", "B": "错误"}
    )

    result = grade_answer(db, question_id=question.id, user_answer="B")

    assert result["is_correct"] is False
    assert db.query(AnswerRecord).filter_by(question_id=question.id).count() == 1
    assert db.query(WrongQuestion).filter_by(question_id=question.id).one().wrong_count == 1

    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert progress.attempt_count == 1
    assert progress.correct_count == 0
    assert progress.mastery_level == 1
    assert progress.consecutive_correct == 0
    assert progress.next_review_at <= datetime.now() + timedelta(seconds=1)


def test_repeated_wrong_answers_increment_wrong_count_and_attempt_count(db, question_factory):
    question = question_factory(
        stem="重复答错", options={"A": "正确", "B": "错误"}
    )

    grade_answer(db, question_id=question.id, user_answer="B")
    grade_answer(db, question_id=question.id, user_answer="B")

    wrong = db.query(WrongQuestion).filter_by(question_id=question.id).one()
    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert wrong.wrong_count == 2
    assert progress.attempt_count == 2
    assert progress.correct_count == 0


def test_first_correct_answer_schedules_review_in_one_day(db, question_factory):
    question = question_factory(stem="第一次答对", options={"A": "正确"})

    result = grade_answer(db, question_id=question.id, user_answer="A")

    assert result["is_correct"] is True
    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert progress.attempt_count == 1
    assert progress.correct_count == 1
    assert progress.mastery_level == 2
    assert progress.consecutive_correct == 1
    assert abs((progress.next_review_at - (datetime.now() + timedelta(days=1))).total_seconds()) < 60


def test_second_consecutive_correct_answer_schedules_review_in_three_days(db, question_factory):
    question = question_factory(stem="第二次答对", options={"A": "正确"})

    grade_answer(db, question_id=question.id, user_answer="A")
    grade_answer(db, question_id=question.id, user_answer="A")

    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert progress.consecutive_correct == 2
    assert progress.mastery_level == 2
    assert abs((progress.next_review_at - (datetime.now() + timedelta(days=3))).total_seconds()) < 60


def test_three_consecutive_correct_answers_make_question_mastered(db, question_factory):
    question = question_factory(stem="第三次答对", options={"A": "正确"})

    for _ in range(3):
        grade_answer(db, question_id=question.id, user_answer="A")

    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert progress.consecutive_correct == 3
    assert progress.mastery_level == 3
    assert abs((progress.next_review_at - (datetime.now() + timedelta(days=7))).total_seconds()) < 60


def test_four_or_more_consecutive_correct_answers_cap_interval_at_fourteen_days(db, question_factory):
    question = question_factory(stem="第四次答对", options={"A": "正确"})

    for _ in range(4):
        grade_answer(db, question_id=question.id, user_answer="A")

    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert progress.consecutive_correct == 4
    assert progress.mastery_level == 3
    assert abs((progress.next_review_at - (datetime.now() + timedelta(days=14))).total_seconds()) < 60


def test_wrong_answer_after_correct_streak_resets_progress(db, question_factory):
    question = question_factory(
        stem="答错会重置连续答对", options={"A": "正确", "B": "错误"}
    )

    grade_answer(db, question_id=question.id, user_answer="A")
    grade_answer(db, question_id=question.id, user_answer="A")
    grade_answer(db, question_id=question.id, user_answer="B")

    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert progress.attempt_count == 3
    assert progress.correct_count == 2
    assert progress.consecutive_correct == 0
    assert progress.mastery_level == 1
    assert progress.next_review_at <= datetime.now() + timedelta(seconds=1)


def test_short_answer_requires_every_keyword_but_ignores_case(db, question_factory):
    question = question_factory(
        stem="简答关键词",
        q_type="short_answer",
        answer="TCP、拥塞控制",
    )

    incorrect = grade_answer(db, question_id=question.id, user_answer="只回答 TCP")
    correct = grade_answer(db, question_id=question.id, user_answer="tcp 有拥塞控制机制")

    assert incorrect["is_correct"] is False
    assert correct["is_correct"] is True


def test_unknown_question_returns_error_without_creating_records(db):
    result = grade_answer(db, question_id=99999, user_answer="A")

    assert result == {"error": "题目不存在"}
    assert db.query(AnswerRecord).count() == 0
