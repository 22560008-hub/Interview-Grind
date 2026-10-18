"""检查简答题关键点匹配结果。

用法（在 backend 目录下）：

    python -m scripts.check_key_points                 # 用参考答案跑一遍全部简答题
    python -m scripts.check_key_points --list          # 列出简答题编号
    python -m scripts.check_key_points --id 7 --answer "TLS 1.3 精简了握手流程，1-RTT 完成密钥协商"
    python -m scripts.check_key_points --list          # 编号来自这里的顺序
"""

import argparse

from app.services.key_point_matcher import KeyPointMatch, match_key_points
from scripts.seed import QUESTIONS


def short_answers() -> list[dict]:
    return [question for question in QUESTIONS if question["type"] == "short_answer"]


def print_result(index: int, question: dict, answer: str) -> KeyPointMatch:
    result = match_key_points(question["key_points"], answer)
    print(f'[{index}] {question["stem"]}')
    print(f'  覆盖率：{result.coverage}%')
    print(f'  已覆盖：{"、".join(result.matched) or "无"}')
    if result.uncertain:
        print(f'  疑似覆盖（不计入）：{"、".join(result.uncertain)}')
    if result.missing:
        print(f'  待补充：{"、".join(result.missing)}')
    print()
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="检查简答题关键点匹配")
    parser.add_argument("--list", action="store_true", help="列出简答题编号")
    parser.add_argument("--id", type=int, help="简答题编号（从 1 开始）")
    parser.add_argument("--answer", help="要检查的用户答案")
    args = parser.parse_args()

    questions = short_answers()

    if args.list:
        for index, question in enumerate(questions, 1):
            print(f'{index:2}. [{question["module"]}] {question["stem"]}')
        return

    if args.id is not None:
        if not 1 <= args.id <= len(questions):
            parser.error(f"编号必须在 1-{len(questions)} 之间")
        if not args.answer:
            parser.error("使用 --id 时需要通过 --answer 提供答案")
        print_result(args.id, questions[args.id - 1], args.answer)
        return

    coverages = []
    low: list[tuple[int, dict, KeyPointMatch]] = []
    for index, question in enumerate(questions, 1):
        result = match_key_points(question["key_points"], question["answer"])
        coverages.append(result.coverage)
        if result.missing or result.uncertain:
            low.append((index, question, result))

    print(
        f"参考答案平均覆盖率：{sum(coverages) / len(coverages):.1f}%，"
        f"共 {len(questions)} 道简答题。"
    )
    if not low:
        print("全部关键点都能被参考答案命中。")
        return

    print(f"有 {len(low)} 道未完全命中：")
    for index, question, result in low:
        print(f'[{index}] {result.coverage}% {question["stem"]}')
        if result.uncertain:
            print(f'  疑似：{"、".join(result.uncertain)}')
        if result.missing:
            print(f'  遗漏：{"、".join(result.missing)}')


if __name__ == "__main__":
    main()
