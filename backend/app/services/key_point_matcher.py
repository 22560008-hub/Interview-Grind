"""简答题关键点匹配。

流程：

1. 归一化：NFKC（全角转半角）、大小写折叠、中文数字转阿拉伯数字
   （只在后面跟量词时转换，避免把“一致性”改成“1致性”），去掉空格和标点。
2. 强别名匹配：关键点原文 + `KEY_POINT_ALIASES` 中的等价说法，命中即覆盖。
   纯 ASCII 的别名按“单词”匹配（`tcp` 不会误命中 `tcps`），中文别名按子串匹配。
3. 否定判断：命中位置前 9 个字符内出现“不 / 没 / 无 / 非 / 未 / 不能 / 无法”
   等否定词时，不认为覆盖；但“不是 A，而是 B”这类转折会放行 B。
4. 弱别名匹配：`WEAK_KEY_POINT_ALIASES` 中的宽泛说法只返回“疑似覆盖”，
   不计入覆盖率，避免把“索引”当成“覆盖索引”。

这一层只做提示，不参与最终判分；复习节奏仍由用户自评决定。
"""

import re
import unicodedata
from dataclasses import dataclass

from app.core.key_point_aliases import KEY_POINT_ALIASES, WEAK_KEY_POINT_ALIASES

_CN_DIGITS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
_CN_UNITS = "次个种天年层路台条轮步颗位只张页周月秒倍"
_CN_NUMBER_RE = re.compile(
    rf"([零一二两三四五六七八九十]+)(?=(?:分钟|毫秒|[{_CN_UNITS}]))"
)
_NON_WORD_RE = re.compile(r"[^0-9a-z\u4e00-\u9fff]+")
_SEPARATOR_RE = re.compile(r"[-_/]+")
_SPACE_RE = re.compile(r"\s+")
# 否定只在一个小句内生效。用顿号、逗号、分号等切开后，
# “不可剥夺、循环等待”里的“不”不会误伤后一个关键点。
_CLAUSE_SPLIT_RE = re.compile(r"[，。；、！？,.;!?：:（）()【】\[\]\n\r]+")

_NEGATIONS = ("不", "没", "无", "非", "未", "无需", "不能", "不会", "无法")
_NEGATION_WINDOW = 5
_CONTRAST_MARKERS = ("而是", "但是", "然而", "反而", "不过")
_FALSE_NEGATIONS = ("非常", "不仅", "不但", "无论", "不断", "不同")
# 这些关键点本身描述“已经发生的负面事件”，前面的“未/没”往往修饰另一个分句，
# 例如“业务尚未完成，锁已过期”，不应因此判为未覆盖。
# “锁未过期”不会命中，因为“锁过期”不是连续子串。
_NEGATION_EXEMPT_POINTS = {"锁过期"}


@dataclass(frozen=True)
class KeyPointMatch:
    matched: list[str]
    missing: list[str]
    uncertain: list[str]

    @property
    def coverage(self) -> int:
        total = len(self.matched) + len(self.missing) + len(self.uncertain)
        return round(len(self.matched) / total * 100) if total else 0


def _parse_cn_number(text: str) -> int | None:
    if not text:
        return None
    if "十" in text:
        tens_text, _, ones_text = text.partition("十")
        tens = _CN_DIGITS.get(tens_text, 1) if tens_text else 1
        ones = _CN_DIGITS.get(ones_text, 0) if ones_text else 0
        return tens * 10 + ones
    if len(text) == 1:
        return _CN_DIGITS.get(text)
    return None


def _replace_cn_number(match: re.Match) -> str:
    value = _parse_cn_number(match.group(1))
    return str(value) if value is not None else match.group(0)


def normalize(text: str) -> str:
    """把文本压成适合比较的紧凑形式。"""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = _CN_NUMBER_RE.sub(_replace_cn_number, text)
    return _NON_WORD_RE.sub("", text)


def _token_form(text: str) -> str:
    """保留分隔符的单词形式，供纯 ASCII 别名按词匹配。"""
    text = unicodedata.normalize("NFKC", text).casefold()
    text = _SEPARATOR_RE.sub(" ", text)
    return _SPACE_RE.sub(" ", text).strip()


def _is_negated(text: str, index: int) -> bool:
    window = text[max(0, index - _NEGATION_WINDOW) : index]
    for word in _FALSE_NEGATIONS:
        window = window.replace(word, "")
    if any(marker in window for marker in _CONTRAST_MARKERS):
        return False
    return any(word in window for word in _NEGATIONS)


def _matches_compact(alias: str, compact_text: str, check_negation: bool = True) -> bool:
    start = 0
    while True:
        index = compact_text.find(alias, start)
        if index == -1:
            return False
        if not check_negation or not _is_negated(compact_text, index):
            return True
        start = index + 1


def _matches_token(
    alias: str, token_text: str, check_negation: bool = True
) -> bool:
    pattern = rf"(?<![0-9a-z]){re.escape(alias)}(?![0-9a-z])"
    for match in re.finditer(pattern, token_text):
        if not check_negation or not _is_negated(token_text, match.start()):
            return True
    return False


def _alias_matches(
    alias: str,
    compact_text: str,
    token_text: str,
    check_negation: bool = True,
) -> bool:
    alias = alias.strip()
    if not alias:
        return False
    if alias.isascii():
        token = _token_form(alias)
        return bool(token) and _matches_token(token, token_text, check_negation)
    compact_alias = normalize(alias)
    return bool(compact_alias) and _matches_compact(
        compact_alias, compact_text, check_negation
    )


def _split_clauses(text: str) -> list[str]:
    return [part for part in _CLAUSE_SPLIT_RE.split(text) if part.strip()]


def _matches_any(
    point: str,
    aliases: tuple[str, ...],
    compact_clauses: list[str],
    token_clauses: list[str],
) -> bool:
    check_negation = point not in _NEGATION_EXEMPT_POINTS
    for compact_text, token_text in zip(compact_clauses, token_clauses):
        for alias in (point, *aliases):
            if _alias_matches(
                alias, compact_text, token_text, check_negation
            ):
                return True
    return False


def match_key_points(key_points: list[str], user_answer: str) -> KeyPointMatch:
    clauses = _split_clauses(user_answer)
    compact_clauses = [normalize(clause) for clause in clauses]
    token_clauses = [_token_form(clause) for clause in clauses]

    matched: list[str] = []
    missing: list[str] = []
    uncertain: list[str] = []

    for point in key_points:
        if _matches_any(
            point,
            KEY_POINT_ALIASES.get(point, ()),
            compact_clauses,
            token_clauses,
        ):
            matched.append(point)
        elif _matches_any(
            point,
            WEAK_KEY_POINT_ALIASES.get(point, ()),
            compact_clauses,
            token_clauses,
        ):
            uncertain.append(point)
        else:
            missing.append(point)

    return KeyPointMatch(matched=matched, missing=missing, uncertain=uncertain)
