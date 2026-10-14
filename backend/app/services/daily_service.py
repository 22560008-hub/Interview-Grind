import random
from datetime import date
from sqlalchemy.orm import Session
from app.models.question import Question


def get_daily_questions(db: Session, count: int = 5):
    """根据日期返回当天固定的题目列表。"""
    today = date.today().isoformat()  # 例如 "2026-10-14"
    all_questions = db.query(Question).all()
    if len(all_questions) <= count:
        return all_questions

    # 用日期当随机种子，保证同一天抽出来的题是同一套
    rng = random.Random(today)
    return rng.sample(all_questions, count)
