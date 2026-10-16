import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest


INDEX_PATH = Path(__file__).parents[1] / "static" / "index.html"


def run_frontend_script(tmp_path: Path, harness: str) -> str:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for frontend behavior tests")

    html = INDEX_PATH.read_text(encoding="utf-8")
    match = re.search(r"<script>(.*?)</script>", html, re.DOTALL)
    assert match is not None

    script_path = tmp_path / "frontend-daily-test.js"
    script_path.write_text(f"{match.group(1)}\n{harness}", encoding="utf-8")
    result = subprocess.run(
        [node, str(script_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_daily_answer_submission_includes_practice_id(tmp_path):
    output = run_frontend_script(
        tmp_path,
        """
global.window = {
    dailyQuestions: [{ id: 42 }],
    dailyPracticeId: 99,
    dailyAnswers: []
};
let submittedBody = null;
global.fetch = async (_url, options) => {
    submittedBody = JSON.parse(options.body);
    return {
        json: async () => ({
            is_correct: true,
            correct_answer: "A",
            explanation: "ok",
            display_user_answer: "A"
        })
    };
};
renderDailyScore = () => {};
const option = {
    classList: { add: () => {} },
    parentNode: { querySelectorAll: () => [] }
};
(async () => {
    await submitDailyAnswer(0, "A", option);
    console.log(JSON.stringify(submittedBody));
})().catch(error => { console.error(error); process.exit(1); });
""",
    )

    assert json.loads(output) == {
        "question_id": 42,
        "user_answer": "A",
        "daily_practice_id": 99,
    }


def test_daily_history_renders_safe_answer_text(tmp_path):
    output = run_frontend_script(
        tmp_path,
        """
const view = {
    innerHTML: "",
    insertAdjacentHTML: function (_position, value) { this.innerHTML += value; }
};
global.window = {};
global.document = {
    getElementById: id => id === "view-daily" ? view : null
};
global.fetch = async () => ({
    json: async () => ({
        date: "2026-10-16",
        practice_id: 7,
        questions: [{
            id: 42,
            module: "network",
            stem: "安全展示",
            type: "short_answer",
            options: null,
            mastery_level: 1,
            user_answer: "<img src=x onerror=alert(1)>",
            display_user_answer: "&lt;img src=x onerror=alert(1)&gt;",
            is_correct: false,
            correct_answer: "参考答案",
            explanation: "解析"
        }]
    })
});
(async () => {
    await loadDaily();
    console.log(view.innerHTML);
})().catch(error => { console.error(error); process.exit(1); });
""",
    )

    assert "<img src=x onerror=alert(1)>" not in output
    assert "&lt;img src=x onerror=alert(1)&gt;" in output


def test_history_page_renders_answered_progress_and_accessible_toggle(tmp_path):
    output = run_frontend_script(
        tmp_path,
        """
const view = { innerHTML: "" };
global.window = {};
global.document = {
    getElementById: id => id === "view-history" ? view : null
};
global.fetch = async () => ({
    ok: true,
    json: async () => ({
        streak: 3,
        records: [{
            date: "2026-10-16",
            total: 5,
            answered: 2,
            correct: 2,
            accuracy: 100,
            completion_rate: 40,
            is_completed: false
        }]
    })
});
(async () => {
    if (typeof loadHistory !== "function") {
        console.log(JSON.stringify({ missing: true }));
        return;
    }
    await loadHistory();
    console.log(JSON.stringify({ missing: false, html: view.innerHTML }));
})().catch(error => { console.error(error); process.exit(1); });
""",
    )
    result = json.loads(output)

    assert result["missing"] is False
    assert "连续打卡 3 天" in result["html"]
    assert "已答 2/5" in result["html"]
    assert "<button" in result["html"]


def test_history_detail_uses_safe_text_and_cached_response(tmp_path):
    output = run_frontend_script(
        tmp_path,
        """
const box = {
    innerHTML: "",
    style: { display: "none" }
};
const arrow = { textContent: "▼" };
const toggle = {
    expanded: "false",
    setAttribute: (name, value) => {
        if (name === "aria-expanded") toggle.expanded = value;
    }
};
global.window = {};
global.document = {
    getElementById: id => {
        if (id === "history-2026-10-16") return box;
        if (id === "history-arrow-2026-10-16") return arrow;
        if (id === "history-toggle-2026-10-16") return toggle;
        return null;
    }
};
let fetchCount = 0;
global.fetch = async () => {
    fetchCount++;
    return {
        ok: true,
        json: async () => ({
            date: "2026-10-16",
            questions: [{
                id: 42,
                module: "network",
                stem: "历史安全展示",
                type: "short_answer",
                options: null,
                user_answer: "<img src=x onerror=alert(1)>",
                display_user_answer: "&lt;img src=x onerror=alert(1)&gt;",
                is_correct: false,
                correct_answer: "参考答案",
                explanation: "解析"
            }]
        })
    };
};
(async () => {
    await loadDailyHistory("2026-10-16");
    await loadDailyHistory("2026-10-16");
    await loadDailyHistory("2026-10-16");
    console.log(JSON.stringify({
        html: box.innerHTML,
        fetchCount,
        arrow: arrow.textContent,
        display: box.style.display,
        expanded: toggle.expanded
    }));
})().catch(error => { console.error(error); process.exit(1); });
""",
    )
    result = json.loads(output)

    assert "<img src=x onerror=alert(1)>" not in result["html"]
    assert "&lt;img src=x onerror=alert(1)&gt;" in result["html"]
    assert result["fetchCount"] == 1
    assert result["arrow"] == "▲"
    assert result["display"] == "block"
    assert result["expanded"] == "true"
