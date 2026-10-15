from app.models.answer import WrongQuestion
from app.services.favorite_service import add_favorite, list_favorites, remove_favorite
from app.services.question_service import pick_questions
from app.services.wrong_service import list_wrong_questions, remove_wrong_question


def test_pick_questions_filters_by_module_type_and_limit(db, question_factory):
    network_choice = question_factory(
        module="network", stem="网络选择题", options={"A": "正确"}
    )
    question_factory(module="network", q_type="short_answer", stem="网络简答题", answer="TCP")
    question_factory(module="mysql", stem="MySQL 选择题", options={"A": "正确"})

    result = pick_questions(db, module="network", q_type="choice", limit=1)

    assert [question.id for question in result] == [network_choice.id]


def test_pick_questions_returns_at_most_requested_limit(db, question_factory):
    for index in range(3):
        question_factory(stem=f"限量题 {index}", options={"A": "正确"})

    result = pick_questions(db, limit=2)

    assert len(result) == 2
    assert len({question.id for question in result}) == 2


def test_favorite_service_prevents_duplicates_and_can_remove_favorite(db, question_factory):
    question = question_factory(stem="收藏题", options={"A": "正确"})

    assert add_favorite(db, question.id) is True
    assert add_favorite(db, question.id) is False
    assert [item["question_id"] for item in list_favorites(db)] == [question.id]
    assert remove_favorite(db, question.id) is True
    assert remove_favorite(db, question.id) is False
    assert list_favorites(db) == []


def test_wrong_question_service_lists_question_details_and_removes_item(db, question_factory):
    question = question_factory(stem="错题详情", options={"A": "正确"})
    db.add(WrongQuestion(question_id=question.id, wrong_count=2))
    db.commit()

    wrong_questions = list_wrong_questions(db)

    assert len(wrong_questions) == 1
    assert wrong_questions[0]["question_id"] == question.id
    assert wrong_questions[0]["stem"] == "错题详情"
    assert wrong_questions[0]["wrong_count"] == 2
    assert remove_wrong_question(db, question.id) is True
    assert remove_wrong_question(db, question.id) is False
