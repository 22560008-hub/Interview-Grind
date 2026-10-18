import random
from datetime import date, datetime
from html import escape

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.answer import AnswerRecord
from app.models.daily import DailyPractice, DailyPracticeItem
from app.models.progress import QuestionProgress
from app.models.question import Question


def parse_question_ids(value: str | None) -> list[int]:
    if not value:
        return []
    return [int(part) for part in value.split(",") if part.strip()]


def ensure_daily_items(db: Session, practice: DailyPractice) -> list[DailyPracticeItem]:
    items = (
        db.query(DailyPracticeItem)
        .filter_by(practice_id=practice.id)
        .order_by(DailyPracticeItem.position)
        .all()
    )
    if items:
        return items

    saved_ids = parse_question_ids(practice.question_ids)
    if not saved_ids:
        return []

    # 兼容已经存在的 daily_practice 数据：首次加载时补齐明细。
    for position, question_id in enumerate(saved_ids):
        record = (
            db.query(AnswerRecord)
            .filter_by(question_id=question_id)
            .filter(AnswerRecord.created_at >= practice.started_at)
            .order_by(AnswerRecord.id.desc())
            .first()
        )
        db.add(
            DailyPracticeItem(
                practice_id=practice.id,
                question_id=question_id,
                position=position,
                user_answer=record.user_answer if record else None,
                is_correct=record.is_correct if record else None,
                answered_at=record.created_at if record else None,
            )
        )

    db.flush()
    items = (
        db.query(DailyPracticeItem)
        .filter_by(practice_id=practice.id)
        .order_by(DailyPracticeItem.position)
        .all()
    )
    answered_count = sum(item.user_answer is not None for item in items)
    practice.correct = sum(item.is_correct is True for item in items)
    practice.is_completed = practice.total > 0 and answered_count >= practice.total
    practice.completed_at = datetime.now() if practice.is_completed else None
    db.commit()
    return items


def _select_questions(db: Session, count: int, today: str) -> list[Question]:
    rng = random.Random(today)
    all_questions = db.query(Question).filter(Question.is_active.is_(True)).all()
    now = datetime.now()

    review_ids = {
        row[0]
        for row in db.query(QuestionProgress.question_id)
        .filter(QuestionProgress.next_review_at <= now)
        .filter(QuestionProgress.mastery_level < 3)
        .all()
    }
    review_pool = [q for q in all_questions if q.id in review_ids]
    rng.shuffle(review_pool)

    weak_ids = {
        row[0]
        for row in db.query(QuestionProgress.question_id)
        .filter(QuestionProgress.mastery_level == 1)
        .all()
    }
    weak_pool = [
        q for q in all_questions if q.id in weak_ids and q.id not in review_ids
    ]
    rng.shuffle(weak_pool)

    answered_ids = {row[0] for row in db.query(QuestionProgress.question_id).all()}
    new_pool = [q for q in all_questions if q.id not in answered_ids]
    rng.shuffle(new_pool)

    selected = [*review_pool[:2], *weak_pool[:2], *new_pool[:1]]
    selected_ids = {q.id for q in selected}
    remaining = [q for q in all_questions if q.id not in selected_ids]
    rng.shuffle(remaining)
    while len(selected) < count and remaining:
        selected.append(remaining.pop())
    return selected[:count]


def _create_daily_practice(
    db: Session, selected: list[Question], today: str
) -> DailyPractice:
    practice = DailyPractice(
        date=today,
        question_ids=",".join(str(q.id) for q in selected),
        total=len(selected),
    )
    db.add(practice)
    db.flush()
    for position, question in enumerate(selected):
        db.add(
            DailyPracticeItem(
                practice_id=practice.id,
                question_id=question.id,
                position=position,
            )
        )
    db.commit()
    return practice


def get_or_create_daily_practice(db: Session, count: int = 5) -> DailyPractice:
    today = date.today().isoformat()
    practice = db.query(DailyPractice).filter_by(date=today).first()
    if practice is not None:
        ensure_daily_items(db, practice)
        return practice

    selected = _select_questions(db, count=count, today=today)
    try:
        return _create_daily_practice(db, selected=selected, today=today)
    except IntegrityError:
        # 两个首次请求同时创建时，唯一日期约束只保留其中一份。
        db.rollback()
        practice = db.query(DailyPractice).filter_by(date=today).one()
        ensure_daily_items(db, practice)
        return practice


def get_daily_questions(db: Session, count: int = 5) -> list[dict]:
    practice = get_or_create_daily_practice(db, count=count)
    items = ensure_daily_items(db, practice)
    question_ids = [item.question_id for item in items]
    questions_by_id = {
        question.id: question
        for question in db.query(Question).filter(Question.id.in_(question_ids)).all()
    }

    result = []
    for item in items:
        question = questions_by_id.get(item.question_id)
        if question is None:
            continue
        progress = (
            db.query(QuestionProgress).filter_by(question_id=question.id).first()
        )
        result.append(
            {
                "id": question.id,
                "module": question.module,
                "chapter": question.chapter,
                "type": question.type,
                "stem": question.stem,
                "options": question.options,
                "mastery_level": progress.mastery_level if progress else 0,
                "user_answer": item.user_answer,
                "display_user_answer": (
                    escape(item.user_answer) if item.user_answer is not None else None
                ),
                "is_correct": item.is_correct,
                "correct_answer": question.answer if item.user_answer is not None else None,
                "explanation": (
                    question.explanation if item.user_answer is not None else None
                ),
            }
        )
    return result
