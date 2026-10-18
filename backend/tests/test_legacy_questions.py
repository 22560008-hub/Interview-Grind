from app.models.answer import AnswerRecord, WrongQuestion
from app.models.favorite import Favorite
from app.models.progress import QuestionProgress
from app.models.question import Question
from scripts.legacy_questions import replace_legacy_questions


def add_answer(db, question_id, *, answer="A", is_correct=True):
    db.add(
        AnswerRecord(
            question_id=question_id, user_answer=answer, is_correct=is_correct
        )
    )


def test_replacement_moves_all_learning_records_to_successor(
    db, question_factory, progress_factory
):
    old = question_factory(stem="旧题", code="network-0001")
    new = question_factory(stem="新题", code="network-0087")
    add_answer(db, old.id)
    add_answer(db, old.id, answer="B", is_correct=False)
    db.add(WrongQuestion(question_id=old.id, wrong_count=2))
    db.add(Favorite(question_id=old.id))
    db.commit()
    progress_factory(old, mastery_level=2, attempt_count=2, correct_count=1)

    replaced = replace_legacy_questions(db, {"旧题": "新题"})

    assert replaced == [
        {
            "from": "旧题",
            "to": "新题",
            "moved": {
                "answers": 2,
                "daily_items": 0,
                "progress": True,
                "wrong": True,
                "favorite": True,
                "daily_practices": 0,
            },
        }
    ]
    assert db.query(AnswerRecord).filter_by(question_id=new.id).count() == 2
    assert db.query(WrongQuestion).filter_by(question_id=new.id).one().wrong_count == 2
    assert db.query(Favorite).filter_by(question_id=new.id).count() == 1
    assert db.query(QuestionProgress).filter_by(question_id=new.id).one().attempt_count == 2
    assert db.get(Question, old.id) is None


def test_replacement_merges_progress_and_wrong_count_when_target_already_has_them(
    db, question_factory, progress_factory
):
    old = question_factory(stem="旧题")
    new = question_factory(stem="新题")
    db.add(WrongQuestion(question_id=old.id, wrong_count=2))
    db.add(WrongQuestion(question_id=new.id, wrong_count=1))
    db.commit()
    progress_factory(
        old, mastery_level=2, attempt_count=3, correct_count=2, consecutive_correct=2
    )
    progress_factory(
        new, mastery_level=1, attempt_count=1, correct_count=0, consecutive_correct=0
    )

    replace_legacy_questions(db, {"旧题": "新题"})

    merged = db.query(QuestionProgress).filter_by(question_id=new.id).one()
    assert merged.attempt_count == 4
    assert merged.correct_count == 2
    assert merged.consecutive_correct == 2
    assert merged.mastery_level == 2
    assert db.query(WrongQuestion).filter_by(question_id=new.id).one().wrong_count == 3
    assert db.query(QuestionProgress).count() == 1


def test_replacement_is_idempotent_and_skips_missing_stems(db, question_factory):
    old = question_factory(stem="旧题")
    question_factory(stem="新题")

    first = replace_legacy_questions(db, {"旧题": "新题"})
    second = replace_legacy_questions(db, {"旧题": "新题"})
    missing = replace_legacy_questions(db, {"不存在的题": "新题"})

    assert len(first) == 1
    assert second == []
    assert missing == []
    assert db.get(Question, old.id) is None
