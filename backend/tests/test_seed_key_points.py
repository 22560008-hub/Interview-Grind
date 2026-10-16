from app.models.question import Question
from scripts import seed


def test_every_seed_short_answer_has_distinct_key_points():
    short_answers = [
        question for question in seed.QUESTIONS if question["type"] == "short_answer"
    ]

    assert len(short_answers) == 40
    for question in short_answers:
        points = question.get("key_points")
        assert points is not None, question["stem"]
        assert 2 <= len(points) <= 6, question["stem"]
        assert len(points) == len(set(points)), question["stem"]
        assert all(point.strip() == point and point for point in points)


def test_seed_sync_backfills_key_points_for_existing_question(db):
    existing = Question(
        module="network",
        chapter="TCP",
        type="short_answer",
        stem="需要补关键点的旧题",
        options=None,
        answer="旧参考答案",
        key_points=None,
        explanation="旧解析",
        difficulty=2,
    )
    db.add(existing)
    db.commit()
    question_data = {
        "module": "network",
        "chapter": "TCP",
        "type": "short_answer",
        "stem": existing.stem,
        "options": None,
        "answer": "旧参考答案",
        "key_points": ["序列号", "确认应答"],
        "explanation": "旧解析",
        "difficulty": 2,
    }

    assert hasattr(seed, "sync_questions")
    added, updated = seed.sync_questions(db, [question_data])
    db.refresh(existing)

    assert (added, updated) == (0, 1)
    assert existing.key_points == ["序列号", "确认应答"]
