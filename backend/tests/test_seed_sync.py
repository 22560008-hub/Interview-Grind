import pytest

from app.models.question import Question
from scripts import seed


def question_data(**overrides):
    data = {
        "code": None,
        "module": "network",
        "chapter": "TCP",
        "type": "choice",
        "stem": "TCP 三次握手",
        "options": {"A": "正确", "B": "错误"},
        "answer": "A",
        "key_points": None,
        "explanation": "旧解析",
        "difficulty": 2,
    }
    data.update(overrides)
    return data


def test_sync_updates_every_content_field_for_existing_stem(db, question_factory):
    existing = question_factory(
        stem="TCP 三次握手",
        answer="A",
        options={"A": "正确", "B": "错误"},
        explanation="旧解析",
        difficulty=2,
    )

    result = seed.sync_questions(
        db,
        [
            question_data(
                stem="TCP 三次握手",
                answer="B",
                options={"A": "错误", "B": "正确"},
                explanation="修正后的解析",
                difficulty=3,
            )
        ],
    )
    db.refresh(existing)

    assert result.added == 0
    assert result.updated == 1
    assert existing.answer == "B"
    assert existing.options == {"A": "错误", "B": "正确"}
    assert existing.explanation == "修正后的解析"
    assert existing.difficulty == 3
    assert existing.is_active is True
    assert existing.code == f"network-{existing.id:04d}"


def test_sync_retires_questions_removed_from_seed(db, question_factory):
    kept = question_factory(stem="保留的题")
    removed = question_factory(stem="被删掉的题")

    result = seed.sync_questions(db, [question_data(stem="保留的题")])
    db.refresh(kept)
    db.refresh(removed)

    assert result.retired == 1
    assert kept.is_active is True
    assert removed.is_active is False
    # 停用而不是删除，答题记录和进度仍然留在库里。
    assert db.get(Question, removed.id) is not None


def test_sync_reactivates_question_that_returns_to_seed(db, question_factory):
    question = question_factory(stem="先停用再恢复", is_active=False)

    result = seed.sync_questions(db, [question_data(stem="先停用再恢复")])
    db.refresh(question)

    assert result.added == 0
    assert question.is_active is True


def test_sync_keeps_same_row_when_stem_changes_with_code(db, question_factory):
    existing = question_factory(stem="旧题干", code="network-0042")
    existing_id = existing.id

    result = seed.sync_questions(
        db, [question_data(code="network-0042", stem="改写后的题干")]
    )
    db.refresh(existing)

    assert result.added == 0
    assert result.retired == 0
    assert existing.id == existing_id
    assert existing.stem == "改写后的题干"
    assert existing.code == "network-0042"


def test_sync_without_code_creates_new_row_for_renamed_stem(db, question_factory):
    existing = question_factory(stem="旧题干")

    result = seed.sync_questions(db, [question_data(stem="全新题干")])
    db.refresh(existing)

    assert result.added == 1
    assert result.retired == 1
    assert existing.is_active is False
    assert db.query(Question).count() == 2


def test_validate_questions_rejects_duplicate_codes_and_stems():
    with pytest.raises(ValueError, match="code 重复"):
        seed.validate_questions(
            [question_data(code="x"), question_data(code="x", stem="另一道题")]
        )

    with pytest.raises(ValueError, match="题干重复"):
        seed.validate_questions([question_data(), question_data()])


def test_seed_question_bank_has_unique_stems_and_codes():
    seed.validate_questions(seed.QUESTIONS)

    assert len(seed.QUESTIONS) == 224
