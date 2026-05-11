#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.11"
# dependencies = ["openai"]
# ///
"""
LLM 委员会 — 通过 OpenRouter 使用多个模型对 index.html 进行事实核查。
每个模型独立审查内容并标记不准确之处。
最终由一个模型将 verdict 综合成报告。

使用方法：
    export OPENROUTER_API_KEY=sk-or-...
    uv run council.py
"""

import os
import json
import re
import random
import datetime
from html.parser import HTMLParser
from openai import OpenAI

API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not API_KEY:
    raise SystemExit("请先设置 OPENROUTER_API_KEY 环境变量。")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY,
)

COUNCIL = [
    ("GPT-4.1",          "openai/gpt-4.1"),
    ("Gemini 2.5 Pro",   "google/gemini-2.5-pro-preview-05-06"),
    ("Llama 4 Maverick", "meta-llama/llama-4-maverick"),
]

SYNTHESISER = ("Claude Opus 4.7", "anthropic/claude-opus-4-7")

# ── 从 HTML 中提取可读文本 ──────────────────────────────────────────

class TextExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "noscript"}

    def __init__(self):
        super().__init__()
        self.chunks = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP_TAGS:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self.SKIP_TAGS and self._skip:
            self._skip -= 1

    def handle_data(self, data):
        if not self._skip:
            stripped = data.strip()
            if stripped:
                self.chunks.append(stripped)

def extract_text(html: str) -> str:
    p = TextExtractor()
    p.feed(html)
    text = "\n".join(p.chunks)
    # Collapse excessive blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── 提示词 ───────────────────────────────────────────────────────────────────

REVIEWER_PROMPT = """\
你是一位严谨的事实核查员，正在审查一份关于大语言模型工作原理的教育性网页指南。
该指南面向技术背景但非专业的读者。

你的任务：阅读以下内容，找出任何事实错误、误导性论断、过时数据，
或过度简化导致错误的内容。不要标记为教学目的而故意简化的内容。

对于发现的每个问题，返回如下 JSON 数组：
[
  {{
    "claim": "论断的原文或近似改写",
    "verdict": "wrong | misleading | outdated | unverifiable",
    "explanation": "简要说明错误之处以及真相是什么"
  }}
]

如果没有发现问题，返回空数组：[]
只返回 JSON 数组，不要其他文字。

--- 内容开始 ---
{content}
--- 内容结束 ---
"""

SYNTHESISER_PROMPT = """\
你正在综合 {n} 个不同 LLM 的事实核查报告，它们各自独立审查了同一份关于 LLM 工作原理的教育指南。

以下是它们的发现：

{reports}

你的任务：
1. 找出被多个模型标记的论断（高置信度问题）。
2. 记录仅被一个模型标记的论断（低置信度，值得复查）。
3. 驳回那些看起来是对故意简化过度挑剔的标记。
4. 生成一份简洁的 Markdown 报告，包含以下章节：
   - ## 高置信度问题  （被 2+ 个模型标记）
   - ## 低置信度 / 值得复查  （被 1 个模型标记）
   - ## 总结  （一段总体评估）

保持简洁。每个问题一个 bullet point。
"""


# ── 核心逻辑 ────────────────────────────────────────────────────────────────

def call(model_id: str, prompt: str, label: str) -> str:
    print(f"  → 正在调用 {label}...", flush=True)
    resp = client.chat.completions.create(
        model=model_id,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    return resp.choices[0].message.content.strip()


def parse_json_array(text: str) -> list:
    # 去除 Markdown 代码围栏（如果存在）
    text = re.sub(r"^```[a-z]*\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    try:
        result = json.loads(text)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def main():
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    print("正在从 index.html 中提取文本...")
    content = extract_text(html)
    print(f"  已提取 {len(content):,} 个字符。\n")

    prompt = REVIEWER_PROMPT.format(content=content)

    reviews = {}
    print("召集委员会：")
    for label, model_id in COUNCIL:
        raw = call(model_id, prompt, label)
        issues = parse_json_array(raw)
        reviews[label] = issues
        print(f"     {label}: 标记了 {len(issues)} 个问题")

    # 在发送给综合模型之前匿名化 —— 打乱顺序并使用
    # 通用标签，防止 Opus 根据模型身份加权
    labels = list(reviews.keys())
    random.shuffle(labels)
    anon_map = {label: f"审查员 {chr(65 + i)}" for i, label in enumerate(labels)}

    anon_reports_text = ""
    for label in labels:
        issues = reviews[label]
        anon_label = anon_map[label]
        anon_reports_text += f"\n### {anon_label}\n"
        if issues:
            for issue in issues:
                anon_reports_text += (
                    f"- **论断：** {issue.get('claim','?')}\n"
                    f"  **裁决：** {issue.get('verdict','?')}\n"
                    f"  **解释：** {issue.get('explanation','?')}\n"
                )
        else:
            anon_reports_text += "- 未发现问题。\n"

    synth_prompt = SYNTHESISER_PROMPT.format(
        n=len(COUNCIL), reports=anon_reports_text
    )

    print(f"\n正在使用 {SYNTHESISER[0]} 进行综合（审查员已匿名化）...")
    synthesis = call(SYNTHESISER[1], synth_prompt, SYNTHESISER[0])

    # 为报告构建去匿名化的原始部分
    raw_text = ""
    for label, issues in reviews.items():
        raw_text += f"\n### {label}（原 {anon_map[label]}）\n"
        if issues:
            for issue in issues:
                raw_text += (
                    f"- **论断：** {issue.get('claim','?')}\n"
                    f"  **裁决：** {issue.get('verdict','?')}\n"
                    f"  **解释：** {issue.get('explanation','?')}\n"
                )
        else:
            raw_text += "- 未发现问题。\n"

    # 写入报告
    report_path = os.path.join(os.path.dirname(__file__), "council_report.md")
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    council_names = ", ".join(l for l, _ in COUNCIL)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(f"# LLM 委员会事实核查报告\n")
        f.write(f"**生成时间：** {timestamp}  \n")
        f.write(f"**委员会：** {council_names}  \n")
        f.write(f"**综合者：** {SYNTHESISER[0]}（审查了匿名化输入）\n\n---\n\n")
        f.write(synthesis)
        f.write("\n\n---\n\n## 各模型原始发现\n")
        f.write(raw_text)

    print(f"\n完成。报告已写入 council_report.md")


if __name__ == "__main__":
    main()
