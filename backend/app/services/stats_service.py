from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.answer import AnswerRecord
from app.models.question import Question
from app.models.progress import QuestionProgress


def get_stats(db: Session):
    # 总答题数
    total = db.query(AnswerRecord).count()
    # 答对多少
    correct = db.query(AnswerRecord).filter(AnswerRecord.is_correct == True).count()
    # 总正确率
    accuracy = round(correct / total * 100, 1) if total > 0 else 0

    # 按模块分组统计正确率
    rows = (
        db.query(
            Question.module,
            func.count(AnswerRecord.id).label("total"),
            func.sum(AnswerRecord.is_correct).label("correct"),
        )
        .join(AnswerRecord, AnswerRecord.question_id == Question.id)
        .group_by(Question.module)
        .all()
    )

    module_stats = []
    for module, cnt, cor in rows:
        module_stats.append(
            {
                "module": module,
                "total": cnt,
                "correct": cor,
                "accuracy": round(cor / cnt * 100, 1) if cnt > 0 else 0,
            }
        )
    mastery_rows = (
        db.query(QuestionProgress.mastery_level, func.count(QuestionProgress.id))
        .group_by(QuestionProgress.mastery_level)
        .all()
    )
    mastery = {"薄弱": 0, "一般": 0, "熟练": 0}
    for level, cnt in mastery_rows:
        if level == 1:
            mastery["薄弱"] = cnt
        elif level == 2:
            mastery["一般"] = cnt
        elif level == 3:
            mastery["熟练"] = cnt

    return {
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
        "by_module": module_stats,
        "mastery": mastery,
    }
