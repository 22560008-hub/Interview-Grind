"""一次性题库迁移：把旧题上的学习记录并到接替它的新题上。

早期版本以题干作为题目的唯一标识，题干改写后，旧题会变成 seed 里不存在、
但数据库里仍带着答题流水、错题本、收藏和掌握度的“孤儿题”。
直接删除会丢学习记录，所以这里按显式映射把记录迁移到新题，再删除空壳旧题。

映射必须手工维护，且只用于两题考点确实互相接替的情况：
如果只是删掉了一道题，宁可让它保持停用（is_active=0），也不要错误合并记录。
"""

from sqlalchemy.orm import Session

from app.models.answer import AnswerRecord, WrongQuestion
from app.models.daily import DailyPractice, DailyPracticeItem
from app.models.favorite import Favorite
from app.models.progress import QuestionProgress
from app.models.question import Question


LEGACY_REPLACEMENTS = {
    "关于进程和线程，下列说法正确的是？": "进程与线程的典型关系是？",
    "TCP 建立连接需要几次握手？": "TCP 建立连接使用三次握手的核心原因之一是？",
}


def _merge_progress(db: Session, old_id: int, new_id: int) -> bool:
    old = db.query(QuestionProgress).filter_by(question_id=old_id).first()
    if old is None:
        return False

    new = db.query(QuestionProgress).filter_by(question_id=new_id).first()
    if new is None:
        old.question_id = new_id
        return True

    new.attempt_count = (new.attempt_count or 0) + (old.attempt_count or 0)
    new.correct_count = (new.correct_count or 0) + (old.correct_count or 0)
    new.consecutive_correct = max(
        new.consecutive_correct or 0, old.consecutive_correct or 0
    )
    new.mastery_level = max(new.mastery_level or 0, old.mastery_level or 0)
    if old.last_answered_at and (
        new.last_answered_at is None
        or old.last_answered_at > new.last_answered_at
    ):
        new.last_answered_at = old.last_answered_at
    if old.next_review_at and (
        new.next_review_at is None or old.next_review_at < new.next_review_at
    ):
        new.next_review_at = old.next_review_at
    db.delete(old)
    return True


def _merge_wrong_question(db: Session, old_id: int, new_id: int) -> bool:
    old = db.query(WrongQuestion).filter_by(question_id=old_id).first()
    if old is None:
        return False

    new = db.query(WrongQuestion).filter_by(question_id=new_id).first()
    if new is None:
        old.question_id = new_id
        return True

    new.wrong_count = (new.wrong_count or 0) + (old.wrong_count or 0)
    if old.last_wrong_at and (
        new.last_wrong_at is None or old.last_wrong_at > new.last_wrong_at
    ):
        new.last_wrong_at = old.last_wrong_at
    db.delete(old)
    return True


def _merge_favorite(db: Session, old_id: int, new_id: int) -> bool:
    old = db.query(Favorite).filter_by(question_id=old_id).first()
    if old is None:
        return False

    new = db.query(Favorite).filter_by(question_id=new_id).first()
    if new is not None:
        db.delete(old)
    else:
        old.question_id = new_id
    return True


def _move_daily_items(db: Session, old_id: int, new_id: int) -> int:
    moved = 0
    items = db.query(DailyPracticeItem).filter_by(question_id=old_id).all()
    for item in items:
        conflict = (
            db.query(DailyPracticeItem)
            .filter_by(practice_id=item.practice_id, question_id=new_id)
            .first()
        )
        if conflict is not None:
            # 同一场练习里新旧题都出现过，保留新题那条明细。
            db.delete(item)
        else:
            item.question_id = new_id
            moved += 1
    return moved


def _rewrite_daily_question_ids(db: Session, old_id: int, new_id: int) -> int:
    changed = 0
    for practice in db.query(DailyPractice).all():
        raw_ids = (practice.question_ids or "").split(",")
        ids = [int(part) for part in raw_ids if part.strip().isdigit()]
        if old_id not in ids:
            continue
        rewritten: list[int] = []
        for question_id in ids:
            replacement = new_id if question_id == old_id else question_id
            if replacement not in rewritten:
                rewritten.append(replacement)
        practice.question_ids = ",".join(str(item) for item in rewritten)
        changed += 1
    return changed


def replace_legacy_questions(
    db: Session, replacements: dict[str, str] | None = None
) -> list[dict]:
    """把旧题的学习记录迁到新题并删除旧题，重复执行安全。"""
    mapping = LEGACY_REPLACEMENTS if replacements is None else replacements
    replaced: list[dict] = []

    for old_stem, new_stem in mapping.items():
        old_question = db.query(Question).filter_by(stem=old_stem).first()
        new_question = db.query(Question).filter_by(stem=new_stem).first()
        if (
            old_question is None
            or new_question is None
            or old_question.id == new_question.id
        ):
            continue

        old_id, new_id = old_question.id, new_question.id
        answer_count = (
            db.query(AnswerRecord)
            .filter_by(question_id=old_id)
            .update({"question_id": new_id}, synchronize_session=False)
        )
        moved = {
            "answers": answer_count,
            "daily_items": _move_daily_items(db, old_id, new_id),
            "progress": _merge_progress(db, old_id, new_id),
            "wrong": _merge_wrong_question(db, old_id, new_id),
            "favorite": _merge_favorite(db, old_id, new_id),
            "daily_practices": _rewrite_daily_question_ids(db, old_id, new_id),
        }
        db.flush()
        db.delete(old_question)
        db.flush()
        replaced.append(
            {"from": old_stem, "to": new_stem, "moved": moved}
        )

    db.commit()
    return replaced
