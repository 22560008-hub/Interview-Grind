import pytest

from app.core.key_point_aliases import (
    KEY_POINT_ALIASES,
    WEAK_KEY_POINT_ALIASES,
)
from app.services.answer_service import analyze_short_answer
from app.services.key_point_matcher import match_key_points, normalize
from scripts import seed


def test_normalize_handles_fullwidth_case_spacing_and_chinese_numbers():
    assert normalize("ＴＣＰ／ＩＰ 地址") == normalize("tcp/ip地址")
    assert normalize("三次握手") == normalize("3 次握手")
    assert normalize("十五分钟") == normalize("15分钟")
    # 数字转换只在量词前生效，不能把“一致性”改成“1致性”
    assert normalize("一致性") == "一致性"


@pytest.mark.parametrize(
    ("point", "answer"),
    [
        ("IP 地址", "用 IP地址 做逻辑寻址"),
        ("序列号", "给每个字节编号"),
        ("确认", "收到后回 ACK"),
        ("TLB", "页表缓存也叫快表"),
        ("不可剥夺", "资源不能被抢占"),
        ("覆盖索引", "using covering index"),
        ("0-RTT", "恢复会话可以用 0RTT"),
        ("三次握手", "3 次握手"),
        ("HTTP", "ｈｔｔｐ 请求"),
    ],
)
def test_synonyms_and_spelling_variants_are_matched(point, answer):
    result = match_key_points([point], answer)

    assert result.matched == [point]
    assert result.coverage == 100


def test_negated_term_is_not_counted():
    result = match_key_points(["三次握手"], "TCP 不需要三次握手")

    assert result.matched == []
    assert result.missing == ["三次握手"]


def test_negation_does_not_cross_list_items():
    result = match_key_points(["循环等待"], "互斥、持有并等待、不可剥夺、循环等待")

    assert result.matched == ["循环等待"]


def test_negation_does_not_cross_clause_boundary():
    result = match_key_points(["业务处理"], "尚未持久化就崩溃、业务处理失败")

    assert result.matched == ["业务处理"]


def test_term_word_does_not_negate_later_point():
    result = match_key_points(["同一行"], "不可重复读是同一行前后值改变")

    assert result.matched == ["同一行"]


def test_contrast_keeps_correct_term():
    result = match_key_points(["三次握手"], "不是四次挥手，而是三次握手")

    assert result.matched == ["三次握手"]


def test_prefixed_term_is_not_counted():
    result = match_key_points(["聚簇索引"], "非聚簇索引是二级索引")

    assert "聚簇索引" not in result.matched


def test_lock_expiry_is_not_cancelled_by_unfinished_business():
    result = match_key_points(["锁过期"], "业务尚未完成锁已过期")

    assert result.matched == ["锁过期"]


def test_broad_term_is_uncertain_and_not_counted():
    result = match_key_points(["覆盖索引"], "给这个查询加索引")

    assert result.matched == []
    assert result.uncertain == ["覆盖索引"]
    assert result.coverage == 0


def test_alias_tables_only_contain_real_key_points():
    all_points = {
        point
        for question in seed.QUESTIONS
        if question["type"] == "short_answer"
        for point in question["key_points"]
    }

    assert set(KEY_POINT_ALIASES) == all_points
    assert set(WEAK_KEY_POINT_ALIASES) <= all_points


def test_reference_answers_cover_their_key_points():
    short_answers = [
        question for question in seed.QUESTIONS if question["type"] == "short_answer"
    ]
    coverages = []

    for question in short_answers:
        result = match_key_points(question["key_points"], question["answer"])
        assert result.coverage >= 75, (question["stem"], result.missing)
        coverages.append(result.coverage)

    assert sum(coverages) / len(coverages) >= 95


def test_analyze_short_answer_exposes_uncertain_points(question_factory):
    question = question_factory(
        stem="疑似覆盖",
        q_type="short_answer",
        answer="通过覆盖索引避免回表。",
        key_points=["覆盖索引"],
    )

    result = analyze_short_answer(question, "给这个查询加索引")

    assert result["matched_points"] == []
    assert result["missing_points"] == []
    assert result["uncertain_points"] == ["覆盖索引"]
    assert result["coverage"] == 0
