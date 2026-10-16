from datetime import date, datetime, timedelta

from app.models.answer import AnswerRecord
from app.models.daily import DailyPractice, DailyPracticeItem


def create_practice(
    db,
    *,
    day: date,
    total: int,
    completed: bool = False,
) -> DailyPractice:
    practice = DailyPractice(
        date=day.isoformat(),
        question_ids="",
        total=total,
        correct=0,
        is_completed=completed,
        completed_at=datetime.now() if completed else None,
    )
    db.add(practice)
    db.commit()
    return practice


def add_item(
    db,
    practice: DailyPractice,
    question_id: int,
    position: int,
    *,
    user_answer: str | None = None,
    is_correct: bool | None = None,
) -> None:
    db.add(
        DailyPracticeItem(
            practice_id=practice.id,
            question_id=question_id,
            position=position,
            user_answer=user_answer,
            is_correct=is_correct,
            answered_at=datetime.now() if user_answer is not None else None,
        )
    )
    db.commit()


def test_history_separates_answer_accuracy_from_completion_rate(
    client, db, question_factory
):
    questions = [
        question_factory(stem=f"历史统计题 {index}", options={"A": "正确"})
        for index in range(4)
    ]
    practice = create_practice(db, day=date.today(), total=4)
    add_item(db, practice, questions[0].id, 0, user_answer="A", is_correct=True)
    add_item(db, practice, questions[1].id, 1, user_answer="B", is_correct=False)
    add_item(db, practice, questions[2].id, 2)
    add_item(db, practice, questions[3].id, 3)

    record = client.get("/api/daily/history").json()["records"][0]

    assert record == {
        "date": date.today().isoformat(),
        "total": 4,
        "answered": 2,
        "correct": 1,
        "accuracy": 50,
        "completion_rate": 50,
        "is_completed": False,
    }


def test_streak_keeps_yesterdays_run_until_today_ends(client, db):
    today = date.today()
    create_practice(db, day=today, total=5, completed=False)
    create_practice(db, day=today - timedelta(days=1), total=5, completed=True)
    create_practice(db, day=today - timedelta(days=2), total=5, completed=True)

    result = client.get("/api/daily/history?days=1").json()

    assert result["streak"] == 2
    assert [record["date"] for record in result["records"]] == [today.isoformat()]


def test_history_parameters_reject_invalid_ranges_and_dates(client):
    assert client.get("/api/daily/history?days=0").status_code == 422
    assert client.get("/api/daily/history?days=366").status_code == 422
    assert client.get("/api/daily/history/not-a-date").status_code == 422


def test_missing_history_day_returns_not_found(client):
    response = client.get("/api/daily/history/2000-01-01")

    assert response.status_code == 404


def test_history_detail_returns_safe_answer_without_current_mastery(
    client, db, question_factory
):
    question = question_factory(
        stem="历史安全题",
        q_type="short_answer",
        answer="参考答案",
    )
    practice = create_practice(db, day=date.today(), total=1, completed=True)
    unsafe_answer = '<img src=x onerror="alert(1)">'
    add_item(
        db,
        practice,
        question.id,
        0,
        user_answer=unsafe_answer,
        is_correct=False,
    )

    item = client.get(f"/api/daily/history/{date.today().isoformat()}").json()[
        "questions"
    ][0]

    assert item["user_answer"] == unsafe_answer
    assert item["display_user_answer"] == (
        "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;"
    )
    assert "mastery_level" not in item


def test_history_detail_migrates_legacy_question_ids(
    client, db, question_factory
):
    question = question_factory(stem="旧历史题", options={"A": "正确"})
    practice = create_practice(db, day=date.today(), total=1)
    practice.question_ids = str(question.id)
    db.add(
        AnswerRecord(
            question_id=question.id,
            user_answer="A",
            is_correct=True,
            created_at=datetime.now(),
        )
    )
    db.commit()

    result = client.get(f"/api/daily/history/{date.today().isoformat()}").json()

    assert result["questions"][0]["id"] == question.id
    assert result["questions"][0]["user_answer"] == "A"
