"""Structured content planning; reasoning remains the author's responsibility."""
from __future__ import annotations


class AnalysisError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise AnalysisError(message)


def text(value):
    return isinstance(value, str) and bool(value.strip()) and "<!-- WORKFLOW_DRAFT -->" not in value


def template():
    return {
        "document_summary": {"problem": "", "approach": "", "findings": [], "limitations": []},
        "audience_fit": {"existing_knowledge": "", "desired_outcome": "", "adaptation": ""},
        "core_message": "",
        "candidates": [],
        "open_questions": [],
    }


def validate(analysis, sources, resolved=True):
    require(isinstance(analysis, dict), "分析结果须为对象")
    summary = analysis.get("document_summary")
    require(isinstance(summary, dict), "缺少文档分析")
    for key in ("problem", "approach"):
        require(text(summary.get(key)), f"文档分析缺少 {key}")
    for key in ("findings", "limitations"):
        value = summary.get(key)
        require(isinstance(value, list) and value and all(text(x) for x in value),
                f"文档分析 {key} 须明确填写，原文未报告时如实说明")
    audience = analysis.get("audience_fit")
    require(isinstance(audience, dict), "缺少听众适配分析")
    for key in ("existing_knowledge", "desired_outcome", "adaptation"):
        require(text(audience.get(key)), f"听众分析缺少 {key}")
    require(text(analysis.get("core_message")), "缺少本次汇报核心信息")
    candidates = analysis.get("candidates")
    require(isinstance(candidates, list) and candidates, "缺少候选汇报重点")
    ids = set()
    for candidate in candidates:
        require(isinstance(candidate, dict), "每个候选重点须为对象")
        for key in ("id", "title", "claim", "reason", "visual_opportunity"):
            require(text(candidate.get(key)), f"候选重点缺少 {key}")
        require(candidate["id"] not in ids, "候选重点 ID 重复")
        ids.add(candidate["id"])
        require(candidate.get("disposition") in ("main", "support", "backup", "omit"),
                "候选内容取舍只接受 main/support/backup/omit")
        kind = candidate.get("claim_kind")
        require(kind in ("fact", "assumption"), "候选重点须区分 fact/assumption")
        refs = candidate.get("evidence")
        require(isinstance(refs, list), "候选证据须为数组")
        require(kind != "fact" or refs, "事实型候选重点必须有来源和位置")
        if kind == "assumption":
            require(text(candidate.get("assumption_note")), "假设必须明确标注依据或待验证条件")
        for ref in refs:
            require(isinstance(ref, dict) and text(ref.get("source_id")) and
                    ref["source_id"] in sources, "证据引用了未知来源")
            require(text(ref.get("locator")), "证据缺少章节/页码/图号或段落位置")
        caveats = candidate.get("caveats")
        require(isinstance(caveats, list) and all(text(x) for x in caveats), "候选重点 caveats 须为限制说明数组")
    require(any(x["disposition"] == "main" for x in candidates), "至少需要一个建议重点")
    questions = analysis.get("open_questions")
    require(isinstance(questions, list), "open_questions 须为数组")
    for question in questions:
        require(isinstance(question, dict) and text(question.get("question")) and
                type(question.get("blocking")) is bool and isinstance(question.get("resolution"), str),
                "待讨论问题须含 question/blocking/resolution")
        if resolved:
            require(not question["blocking"] or text(question["resolution"]), "尚有影响重点选择的未解决问题")
    return analysis


def render(analysis, sources):
    """Derived review surface. This string is not the source of approval state."""
    labels = {"main": "重点讲", "support": "简要交代", "backup": "备用", "omit": "省略"}
    lines = ["# 汇报重点讨论稿", "", "核心信息：" + analysis["core_message"], ""]
    summary = analysis["document_summary"]
    lines += ["文档问题：" + summary["problem"], "", "方法或论述方式：" + summary["approach"], "",
              "主要发现：" + "；".join(summary["findings"]), "",
              "限制：" + "；".join(summary["limitations"]), "",
              "听众已有知识：" + analysis["audience_fit"]["existing_knowledge"], "",
              "希望听众理解或决定：" + analysis["audience_fit"]["desired_outcome"], "",
              "表达调整：" + analysis["audience_fit"]["adaptation"], ""]
    for item in analysis["candidates"]:
        lines += [f"## {item['id']} · {labels[item['disposition']]} · {item['title']}", "",
                  "内容：" + item["claim"], "", "取舍理由：" + item["reason"], ""]
        if item["claim_kind"] == "assumption":
            lines += ["假设（尚非事实）：" + item["assumption_note"], ""]
        for ref in item["evidence"]:
            source = sources[ref["source_id"]]
            lines += [f"来源：{ref['source_id']} · {source['title']} · {ref['locator']}", ""]
        lines += ["图片或图表建议：" + item["visual_opportunity"], "",
                  "需要保留的限制：" + ("；".join(item["caveats"]) or "无额外限制记录"), ""]
    if analysis["open_questions"]:
        lines += ["## 待讨论或已解决的问题", ""]
        for item in analysis["open_questions"]:
            lines += ["- " + item["question"] + "；处理：" + (item["resolution"] or "待讨论")]
    return "\n".join(lines) + "\n"
