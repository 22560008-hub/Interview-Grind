"""把题库、关键点别名和可选的本地学习数据导出成 APK 用的 JSON。

用法（在 backend 目录下）：

    python -m scripts.export_app_data
    python -m scripts.export_app_data --with-user-data
    python -m scripts.export_app_data --out ../shared

题目用稳定 code 作为 APK 里的 id，避免以后 seed 调整顺序导致学习记录错位。
默认输出到 mobile/www/data，直接给 Capacitor 工程使用。
"""

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

from app.core.key_point_aliases import (
    KEY_POINT_ALIASES,
    WEAK_KEY_POINT_ALIASES,
)
from scripts.seed import QUESTIONS


def _question_payload(question) -> dict:
    return {
        "id": question.code or f"q{question.id}",
        "code": question.code or f"q{question.id}",
        "module": question.module,
        "chapter": question.chapter,
        "type": question.type,
        "stem": question.stem,
        "options": question.options,
        "answer": question.answer,
        "key_points": question.key_points,
        "explanation": question.explanation,
        "difficulty": question.difficulty,
    }


def build_questions_payload() -> list[dict]:
    """优先从数据库导出（code 已经由 seed 同步生成），没有库时退回 seed。"""
    try:
        from app.core.database import SessionLocal
        from app.models.question import Question

        db = SessionLocal()
        try:
            rows = (
                db.query(Question)
                .filter(Question.is_active.is_(True))
                .order_by(Question.id)
                .all()
            )
            if rows:
                return [_question_payload(question) for question in rows]
        finally:
            db.close()
    except Exception as exc:
        print(f"数据库不可用，改用 seed 数据：{exc}")

    questions = []
    for index, item in enumerate(QUESTIONS, 1):
        code = item.get("code") or f"{item['module']}-{index:04d}"
        questions.append(
            {
                "id": code,
                "code": code,
                "module": item["module"],
                "chapter": item["chapter"],
                "type": item["type"],
                "stem": item["stem"],
                "options": item.get("options"),
                "answer": item["answer"],
                "key_points": item.get("key_points"),
                "explanation": item["explanation"],
                "difficulty": item["difficulty"],
            }
        )
    return questions


def build_manifest(questions: list[dict]) -> dict:
    return {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "questionCount": len(questions),
        "byModule": dict(Counter(question["module"] for question in questions)),
        "byType": dict(Counter(question["type"] for question in questions)),
    }


def build_user_payload() -> dict | None:
    """导出单用户版的学习数据；数据库不存在或未迁移时返回 None。"""
    try:
        from app.core.database import SessionLocal
        from app.models.answer import AnswerRecord, WrongQuestion
        from app.models.daily import DailyPractice, DailyPracticeItem
        from app.models.favorite import Favorite
        from app.models.progress import QuestionProgress
        from app.models.question import Question
    except Exception:
        return None

    db = SessionLocal()
    try:
        code_by_id = {
            question.id: question.code
            for question in db.query(Question).all()
            if question.code
        }

        def code(question_id: int) -> str | None:
            return code_by_id.get(question_id)

        answers = [
            {
                "questionId": code(record.question_id),
                "userAnswer": record.user_answer,
                "isCorrect": record.is_correct,
                "createdAt": record.created_at.isoformat() if record.created_at else None,
            }
            for record in db.query(AnswerRecord)
            .order_by(AnswerRecord.id)
            .all()
            if code(record.question_id)
        ]
        progress = [
            {
                "questionId": code(row.question_id),
                "attemptCount": row.attempt_count,
                "correctCount": row.correct_count,
                "consecutiveCorrect": row.consecutive_correct,
                "masteryLevel": row.mastery_level,
                "lastAnsweredAt": (
                    row.last_answered_at.isoformat()
                    if row.last_answered_at
                    else None
                ),
                "nextReviewAt": (
                    row.next_review_at.isoformat() if row.next_review_at else None
                ),
            }
            for row in db.query(QuestionProgress)
            .all()
            if code(row.question_id)
        ]
        wrong = [
            {
                "questionId": code(row.question_id),
                "wrongCount": row.wrong_count,
                "lastWrongAt": (
                    row.last_wrong_at.isoformat() if row.last_wrong_at else None
                ),
            }
            for row in db.query(WrongQuestion)
            .all()
            if code(row.question_id)
        ]
        favorites = [
            {
                "questionId": code(row.question_id),
                "createdAt": row.created_at.isoformat() if row.created_at else None,
            }
            for row in db.query(Favorite)
            .all()
            if code(row.question_id)
        ]

        practices = []
        for practice in (
            db.query(DailyPractice)
            .order_by(DailyPractice.date)
            .all()
        ):
            items = (
                db.query(DailyPracticeItem)
                .filter_by(practice_id=practice.id)
                .order_by(DailyPracticeItem.position)
                .all()
            )
            practices.append(
                {
                    "date": practice.date,
                    "total": practice.total,
                    "correct": practice.correct,
                    "isCompleted": practice.is_completed,
                    "startedAt": (
                        practice.started_at.isoformat()
                        if practice.started_at
                        else None
                    ),
                    "completedAt": (
                        practice.completed_at.isoformat()
                        if practice.completed_at
                        else None
                    ),
                    "items": [
                        {
                            "questionId": code(item.question_id),
                            "position": item.position,
                            "userAnswer": item.user_answer,
                            "isCorrect": item.is_correct,
                            "answeredAt": (
                                item.answered_at.isoformat()
                                if item.answered_at
                                else None
                            ),
                        }
                        for item in items
                        if code(item.question_id)
                    ],
                }
            )

        return {
            "answers": answers,
            "progress": progress,
            "wrong": wrong,
            "favorites": favorites,
            "dailyPractices": practices,
        }
    except Exception as exc:  # 数据库不存在或还是旧结构时不阻塞题库导出
        print(f"跳过用户数据导出：{exc}")
        return None
    finally:
        db.close()


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 APK 用的题库 JSON")
    parser.add_argument(
        "--out",
        default="../mobile/www/data",
        help="输出目录，默认 mobile/www/data",
    )
    parser.add_argument(
        "--with-user-data",
        action="store_true",
        help="同时导出本地学习数据",
    )
    args = parser.parse_args()

    out_dir = (Path(__file__).parents[1] / args.out).resolve()
    questions = build_questions_payload()

    write_json(out_dir / "questions.json", questions)
    write_json(
        out_dir / "key_point_aliases.json",
        {"strong": KEY_POINT_ALIASES, "weak": WEAK_KEY_POINT_ALIASES},
    )
    write_json(out_dir / "manifest.json", build_manifest(questions))

    print(f"题库：{len(questions)} 道 -> {out_dir / 'questions.json'}")

    if args.with_user_data:
        user_data = build_user_payload()
        if user_data is not None:
            write_json(out_dir / "user_data.json", user_data)
            print(
                "学习数据："
                f"{len(user_data['answers'])} 条答题、"
                f"{len(user_data['wrong'])} 条错题、"
                f"{len(user_data['progress'])} 条进度 -> "
                f"{out_dir / 'user_data.json'}"
            )


if __name__ == "__main__":
    main()
