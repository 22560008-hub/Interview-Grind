from datetime import datetime, timedelta

import pytest

from app.models.progress import QuestionProgress


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


def test_daily_endpoint_respects_exclude_parameter(client, question_factory):
    questions = [
        question_factory(stem=f"接口每日题 {index}", options={"A": "正确"})
        for index in range(6)
    ]

    response = client.get(f"/api/daily?exclude={questions[0].id},{questions[1].id}")

    assert response.status_code == 200
    returned_ids = {question["id"] for question in response.json()["questions"]}
    assert not returned_ids.intersection({questions[0].id, questions[1].id})


def test_question_delivery_hides_answer_and_explanation_before_submission(
    client, question_factory
):
    question_factory(stem="答案不应提前泄露", options={"A": "正确"})

    response = client.get("/api/questions?limit=1")

    assert "answer" not in response.json()[0]
    assert "explanation" not in response.json()[0]
