from datetime import datetime, timedelta

import pytest

from app.services.answer_service import grade_answer
from app.services.daily_service import get_daily_questions
from app.services.review_service import get_review_questions
from app.services.stats_service import get_stats


def test_review_returns_only_due_questions_that_are_not_mastered(
    db, question_factory, progress_factory
):
    due = question_factory(stem="到期题", options={"A": "正确"})
    future = question_factory(stem="未来题", options={"A": "正确"})
    mastered = question_factory(stem="熟练题", options={"A": "正确"})
    progress_factory(
        due, mastery_level=1, next_review_at=datetime.now() - timedelta(minutes=5)
    )
    progress_factory(
        future, mastery_level=1, next_review_at=datetime.now() + timedelta(days=1)
    )
    progress_factory(
        mastered, mastery_level=3, next_review_at=datetime.now() - timedelta(minutes=5)
    )

    result = get_review_questions(db)

    assert [question["id"] for question in result] == [due.id]


def test_review_orders_due_questions_by_oldest_review_time(
    db, question_factory, progress_factory
):
    oldest = question_factory(stem="最早到期", options={"A": "正确"})
    latest = question_factory(stem="较晚到期", options={"A": "正确"})
    progress_factory(oldest, next_review_at=datetime.now() - timedelta(days=2))
    progress_factory(latest, next_review_at=datetime.now() - timedelta(days=1))

    result = get_review_questions(db)

    assert [question["id"] for question in result] == [oldest.id, latest.id]


def test_daily_questions_exclude_seen_ids_and_do_not_repeat(db, question_factory):
    questions = [
        question_factory(stem=f"每日题 {index}", options={"A": "正确"})
        for index in range(8)
    ]
    excluded_ids = [questions[0].id, questions[1].id]

    result = get_daily_questions(db, count=5, exclude_ids=excluded_ids)
    result_ids = [question["id"] for question in result]

    assert len(result_ids) == 5
    assert not set(result_ids).intersection(excluded_ids)
    assert len(result_ids) == len(set(result_ids))


def test_daily_questions_returns_all_available_questions_when_pool_is_smaller_than_limit(
    db, question_factory
):
    questions = [
        question_factory(stem=f"少量每日题 {index}", options={"A": "正确"})
        for index in range(3)
    ]

    result = get_daily_questions(db, count=5, exclude_ids=[questions[0].id])

    assert {question["id"] for question in result} == {questions[1].id, questions[2].id}


def test_daily_questions_include_current_mastery_level(
    db, question_factory, progress_factory
):
    question = question_factory(stem="带掌握度的每日题", options={"A": "正确"})
    progress_factory(question, mastery_level=2)

    result = get_daily_questions(db, count=1)

    assert result == [
        {
            "id": question.id,
            "module": "network",
            "chapter": "测试章节",
            "type": "choice",
            "stem": "带掌握度的每日题",
            "options": {"A": "正确"},
            "answer": "A",
            "explanation": "测试解析",
            "mastery_level": 2,
        }
    ]


@pytest.mark.xfail(
    strict=True,
    reason="当前实现最多先取 3 道到期题，5 题时会挤掉新题，不满足产品声明的 50/30/20 分配。",
)
def test_daily_five_question_plan_balances_due_weak_and_new_questions(
    db, question_factory, progress_factory
):
    due_questions = [
        question_factory(stem=f"到期每日题 {index}", options={"A": "正确"})
        for index in range(3)
    ]
    weak_questions = [
        question_factory(stem=f"薄弱每日题 {index}", options={"A": "正确"})
        for index in range(3)
    ]
    new_questions = [
        question_factory(stem=f"新每日题 {index}", options={"A": "正确"})
        for index in range(3)
    ]
    for question in due_questions:
        progress_factory(
            question,
            mastery_level=2,
            next_review_at=datetime.now() - timedelta(minutes=1),
        )
    for question in weak_questions:
        progress_factory(
            question, mastery_level=1, next_review_at=datetime.now() + timedelta(days=1)
        )

    result_ids = {question["id"] for question in get_daily_questions(db, count=5)}

    assert (
        len(result_ids.intersection({question.id for question in due_questions})) == 2
    )
    assert (
        len(result_ids.intersection({question.id for question in weak_questions})) == 2
    )
    assert (
        len(result_ids.intersection({question.id for question in new_questions})) == 1
    )


def test_stats_reports_answer_accuracy_module_breakdown_and_mastery(
    db, question_factory
):
    network = question_factory(
        module="network", stem="网络统计题", options={"A": "正确", "B": "错误"}
    )
    mysql = question_factory(
        module="mysql", stem="MySQL统计题", options={"A": "正确", "B": "错误"}
    )
    grade_answer(db, question_id=network.id, user_answer="A")
    grade_answer(db, question_id=mysql.id, user_answer="B")

    stats = get_stats(db)

    assert stats["total"] == 2
    assert stats["correct"] == 1
    assert stats["accuracy"] == 50.0
    assert {item["module"]: item["accuracy"] for item in stats["by_module"]} == {
        "mysql": 0.0,
        "network": 100.0,
    }
    assert stats["mastery"] == {"薄弱": 1, "一般": 1, "熟练": 0}


def test_stats_returns_empty_values_when_no_one_has_answered(db):
    stats = get_stats(db)

    assert stats == {
        "total": 0,
        "correct": 0,
        "accuracy": 0,
        "by_module": [],
        "mastery": {"薄弱": 0, "一般": 0, "熟练": 0},
    }
