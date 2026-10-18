from datetime import datetime, timedelta

import pytest

from app.models.answer import AnswerRecord
from app.models.daily import DailyPractice
from app.models.progress import QuestionProgress


def test_short_answer_preview_reports_coverage_without_persisting(
    client, db, question_factory
):
    question = question_factory(
        stem="简答题预判",
        q_type="short_answer",
        answer="TCP 通过序列号、确认应答和超时重传保证可靠传输。",
        key_points=["序列号", "确认应答", "超时重传"],
        explanation="三个机制共同保证可靠性。",
    )

    response = client.post(
        "/api/answers/preview",
        json={
            "question_id": question.id,
            "user_answer": '<b>序列号</b>和确认应答',
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "display_user_answer": "&lt;b&gt;序列号&lt;/b&gt;和确认应答",
        "correct_answer": question.answer,
        "explanation": "三个机制共同保证可靠性。",
        "matched_points": ["序列号", "确认应答"],
        "missing_points": ["超时重传"],
        "coverage": 67,
        "requires_self_rating": True,
    }
    assert db.query(AnswerRecord).count() == 0
    assert db.query(QuestionProgress).count() == 0


def test_short_answer_preview_rejects_choice_question(client, question_factory):
    question = question_factory(stem="选择题不能预判", options={"A": "正确"})

    response = client.post(
        "/api/answers/preview",
        json={"question_id": question.id, "user_answer": "A"},
    )

    assert response.status_code == 400


def test_short_answer_cannot_be_finalized_without_self_rating(
    client, db, question_factory
):
    question = question_factory(
        stem="简答题需要自评",
        q_type="short_answer",
        answer="参考答案",
        key_points=["关键点"],
    )

    response = client.post(
        "/api/answers",
        json={"question_id": question.id, "user_answer": "我的回答"},
    )

    assert response.status_code == 400
    assert db.query(AnswerRecord).count() == 0


def test_health_endpoint_reports_running_app(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_questions_endpoint_filters_questions_and_adds_mastery_level(
    client, question_factory
):
    network_question = question_factory(
        module="network", stem="接口网络题", options={"A": "正确"}
    )
    question_factory(module="mysql", stem="接口 MySQL 题", options={"A": "正确"})

    response = client.get("/api/questions?module=network&type=choice&limit=1")

    assert response.status_code == 200
    assert response.json()[0]["id"] == network_question.id
    assert response.json()[0]["mastery_level"] == 0


def test_answer_endpoint_returns_grade_and_persists_progress(
    client, db, question_factory
):
    question = question_factory(stem="接口答题", options={"A": "正确", "B": "错误"})

    response = client.post(
        "/api/answers", json={"question_id": question.id, "user_answer": "B"}
    )

    assert response.status_code == 200
    assert response.json()["is_correct"] is False
    progress = db.query(QuestionProgress).filter_by(question_id=question.id).one()
    assert progress.mastery_level == 1


def test_review_endpoint_returns_due_question(
    client, question_factory, progress_factory
):
    question = question_factory(stem="接口复习题", options={"A": "正确"})
    progress_factory(
        question, mastery_level=1, next_review_at=datetime.now() - timedelta(minutes=1)
    )

    response = client.get("/api/review")

    assert response.status_code == 200
    assert response.json()["count"] == 1
    assert response.json()["questions"][0]["id"] == question.id


def test_daily_endpoint_is_persisted_and_extend_appends_five_questions(
    client, question_factory
):
    for index in range(12):
        question_factory(stem=f"接口每日题 {index}", options={"A": "正确"})

    first = client.get("/api/daily")
    second = client.get("/api/daily")
    first_ids = [q["id"] for q in first.json()["questions"]]

    assert first.status_code == 200
    assert len(first_ids) == 5
    assert [q["id"] for q in second.json()["questions"]] == first_ids

    extend = client.post("/api/daily/extend")
    new_ids = [q["id"] for q in extend.json()["questions"]]

    assert extend.status_code == 200
    assert len(new_ids) == 5
    assert not set(new_ids).intersection(first_ids)

    after = client.get("/api/daily")
    assert [q["id"] for q in after.json()["questions"]] == first_ids + new_ids


def test_daily_answer_updates_score_and_completion(client, db, question_factory):
    question = question_factory(
        stem="每日成绩题", options={"A": "正确", "B": "错误"}
    )
    daily = client.get("/api/daily").json()

    response = client.post(
        "/api/answers",
        json={
            "question_id": question.id,
            "user_answer": "A",
            "daily_practice_id": daily["practice_id"],
        },
    )

    assert response.status_code == 200
    refreshed = client.get("/api/daily").json()
    assert refreshed["correct"] == 1
    assert refreshed["is_completed"] is True
    assert refreshed["questions"][0]["user_answer"] == "A"
    assert refreshed["questions"][0]["is_correct"] is True
    practice = db.get(DailyPractice, daily["practice_id"])
    assert practice.completed_at is not None


def test_non_daily_answer_does_not_complete_daily_question(
    client, question_factory
):
    question = question_factory(
        stem="普通答题不能串入每日记录", options={"A": "正确", "B": "错误"}
    )
    client.get("/api/daily")

    response = client.post(
        "/api/answers",
        json={"question_id": question.id, "user_answer": "A"},
    )

    assert response.status_code == 200
    refreshed = client.get("/api/daily").json()
    assert refreshed["correct"] == 0
    assert refreshed["is_completed"] is False
    assert refreshed["questions"][0]["user_answer"] is None
    assert refreshed["questions"][0]["is_correct"] is None


def test_repeated_daily_submission_is_idempotent(client, db, question_factory):
    question = question_factory(
        stem="重复提交只记录第一次", options={"A": "正确", "B": "错误"}
    )
    practice_id = client.get("/api/daily").json()["practice_id"]

    first = client.post(
        "/api/answers",
        json={
            "question_id": question.id,
            "user_answer": "B",
            "daily_practice_id": practice_id,
        },
    )
    second = client.post(
        "/api/answers",
        json={
            "question_id": question.id,
            "user_answer": "A",
            "daily_practice_id": practice_id,
        },
    )

    assert first.json()["is_correct"] is False
    assert second.json()["is_correct"] is False
    assert db.query(AnswerRecord).filter_by(question_id=question.id).count() == 1


def test_daily_extend_returns_remaining_questions_when_fewer_than_five_exist(
    client, question_factory
):
    for index in range(7):
        question_factory(stem=f"不足五道的追加题 {index}", options={"A": "正确"})
    initial_ids = {
        question["id"] for question in client.get("/api/daily").json()["questions"]
    }

    response = client.post("/api/daily/extend")

    assert response.status_code == 200
    assert response.json()["count"] == 2
    new_ids = {question["id"] for question in response.json()["questions"]}
    assert len(new_ids) == 2
    assert new_ids.isdisjoint(initial_ids)


def test_daily_short_answer_provides_html_safe_display_text(
    client, question_factory
):
    question = question_factory(
        stem="每日简答题安全显示",
        q_type="short",
        answer="安全关键词",
        key_points=["安全", "关键词"],
    )
    practice_id = client.get("/api/daily").json()["practice_id"]
    unsafe_answer = '<img src=x onerror="alert(1)">'

    submitted = client.post(
        "/api/answers",
        json={
            "question_id": question.id,
            "user_answer": unsafe_answer,
            "daily_practice_id": practice_id,
            "self_rating": "fuzzy",
        },
    )
    restored = client.get("/api/daily").json()["questions"][0]

    expected = "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    assert submitted.json()["display_user_answer"] == expected
    assert restored["user_answer"] == unsafe_answer
    assert restored["display_user_answer"] == expected


def test_daily_short_answer_preview_does_not_complete_practice(
    client, db, question_factory
):
    question = question_factory(
        stem="预判不完成每日练习",
        q_type="short_answer",
        answer="参考答案",
        key_points=["关键点一", "关键点二"],
    )
    daily = client.get("/api/daily").json()

    preview = client.post(
        "/api/answers/preview",
        json={"question_id": question.id, "user_answer": "关键点一"},
    )
    after_preview = client.get("/api/daily").json()

    assert preview.status_code == 200
    assert after_preview["is_completed"] is False
    assert after_preview["questions"][0]["user_answer"] is None
    assert db.query(AnswerRecord).count() == 0

    finalized = client.post(
        "/api/answers",
        json={
            "question_id": question.id,
            "user_answer": "关键点一",
            "daily_practice_id": daily["practice_id"],
            "self_rating": "fuzzy",
        },
    )
    after_final = client.get("/api/daily").json()

    assert finalized.status_code == 200
    assert after_final["is_completed"] is True
    assert after_final["correct"] == 0
    assert after_final["questions"][0]["user_answer"] == "关键点一"


def test_question_delivery_hides_answer_and_explanation_before_submission(
    client, question_factory
):
    question_factory(stem="答案不应提前泄露", options={"A": "正确"})

    response = client.get("/api/questions?limit=1")

    assert "answer" not in response.json()[0]
    assert "explanation" not in response.json()[0]


def test_questions_endpoint_rejects_unknown_module_and_type(client):
    assert client.get("/api/questions?module=unknown").status_code == 422
    assert client.get("/api/questions?type=essay").status_code == 422


def test_unknown_question_returns_404_instead_of_200_with_error(
    client, db
):
    response = client.post("/api/answers", json={"question_id": 999, "user_answer": "A"})

    assert response.status_code == 404
    assert response.json() == {"detail": "题目不存在"}
    assert db.query(AnswerRecord).count() == 0


def test_extend_without_daily_practice_returns_404(client):
    response = client.post("/api/daily/extend")

    assert response.status_code == 404
    assert response.json()["detail"] == "请先开始今日练习"
