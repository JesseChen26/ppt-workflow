#!/usr/bin/env python3
"""Local sequential PPT workflow. Standard library only; no rendering or network."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import zipfile
from xml.etree import ElementTree as ET
import content_analysis as ca

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "ppt-workflow.v2"
DRAFT = "<!-- WORKFLOW_DRAFT -->"
STAGES = [
    ("brief", "明确任务", "brief.md", ("requirements", "defaults", "scope")),
    ("sources", "整理材料", "sources.md", ("provenance", "coverage", "gaps")),
    ("outline", "组织内容", "outline.json", ("story", "evidence", "coverage")),
    ("visual", "确定视觉", "visual.md", ("template", "readability", "editability")),
    ("assets", "准备素材", "assets.md", ("readiness", "provenance", "accuracy")),
    ("production", "完整制作", "production.md", ("roster", "editable", "notes")),
    ("qa", "检查修正", "qa.md", ("facts", "visual", "structure", "editability", "export_review")),
    ("delivery", "交付归档", "delivery.md", ("version", "package", "handoff")),
]
# First stage owning each decision. Earlier approvals cover their own scope only.
FIELDS = {
    "topic": 1, "audience": 1, "objective": 1, "duration_minutes": 1,
    "source_scope": 1, "output_mode": 1, "outputs": 1, "review_all": 1,
    "source_notes": 2, "slide_count": 3, "language": 3,
    "aspect_ratio": 4, "template": 4, "visual_notes": 4, "speaker_notes": 6,
}


WorkflowError = ca.AnalysisError


def require(condition, message):
    if not condition:
        raise WorkflowError(message)


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".write-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def text_ok(value):
    return isinstance(value, str) and bool(value.strip()) and DRAFT not in value


def stage_dir(workspace, n):
    return workspace / "stages" / f"{n:02d}-{STAGES[n - 1][0]}"


def fresh_review(n):
    return {"summary": "", "checks": {
        key: {"passed": False, "evidence": ""} for key in STAGES[n - 1][3]
    }}


def event(state, action, **data):
    state["events"].append({"at": now(), "action": action, **data})


def next_stage(state):
    return next((i for i, item in enumerate(state["stages"], 1)
                 if item["status"] != "completed"), None)


def fresh_focus():
    return {"status": "analysis", "snapshot": None, "approval": None}


def focus_dir(workspace):
    return stage_dir(workspace, 3) / "focus"


def fresh_focus_review():
    return {"summary": "", "checks": {key: {"passed": False, "evidence": ""}
            for key in ("source_fidelity", "audience_fit", "selection", "limitations", "questions")}}


def setup_content_files(workspace):
    # Also used on legacy tasks: preserve every existing author-owned file.
    files = {
        stage_dir(workspace, 2) / "sources.json": [],
        focus_dir(workspace) / "analysis.json": ca.template(),
        focus_dir(workspace) / "review.json": fresh_focus_review(),
    }
    for path, value in files.items():
        if not path.exists():
            write(path, value)


def invalidate(workspace, state, start, reason, preserve_focus=False):
    if start <= 3:
        retain = False
        if start == 3 and preserve_focus and state.get("focus", {}).get("snapshot"):
            try:
                retain = focus_snapshot(workspace, state["requirements"]) == state["focus"]["snapshot"]
            except (OSError, ValueError, TypeError, KeyError):
                pass
        if not retain:
            if state.get("focus"):
                event(state, "focus_invalidated", previous=state["focus"], reason=reason)
            state["focus"] = fresh_focus()
            path = focus_dir(workspace) / "review.json"
            if path.is_file():
                try:
                    event(state, "focus_review_archived", review=load(path))
                except (OSError, ValueError):
                    event(state, "focus_review_archived", unreadable_sha256=sha(path))
            write(path, fresh_focus_review())
    for n in range(start, 9):
        item = state["stages"][n - 1]
        touched = item["status"] != "not_started" or item.get("approval")
        if touched:
            item["status"] = "needs_revision"
            item["reason"] = reason
            path = stage_dir(workspace, n) / "review.json"
            if path.is_file():
                # Retain actual old assessment in the atomic state history before reset.
                try:
                    previous = load(path)
                except (OSError, ValueError):
                    previous = {"unreadable_sha256": sha(path)}
                event(state, "review_archived", stage=n, review=previous)
            write(path, fresh_review(n))
        item["approval"] = None
        item["snapshot"] = None
    event(state, "invalidated", stage=start, reason=reason)


def requirements_shape(req, complete=False):
    require(isinstance(req, dict) and set(req) == set(FIELDS), "任务要求字段不完整或含未知字段")
    for key in ("topic", "audience", "objective", "source_scope", "source_notes", "visual_notes"):
        require(req[key] is None or isinstance(req[key], str), f"{key} 必须是文本")
    for key in ("speaker_notes", "review_all"):
        require(type(req[key]) is bool, f"{key} 必须是布尔值")
    require(req["output_mode"] in ("editable", "image"), "output_mode 只接受 editable/image")
    outputs = req["outputs"]
    require(isinstance(outputs, list) and outputs and all(x in ("pptx", "pdf") for x in outputs)
            and len(set(outputs)) == len(outputs), "outputs 只接受不重复的 pptx/pdf 列表")
    require(req["aspect_ratio"] in ("16:9", "4:3"), "aspect_ratio 只接受 16:9/4:3")
    require(text_ok(req["language"]), "language 不能为空")
    require(req["template"] is None or text_ok(req["template"]), "template 必须为空或非空模板标识")
    duration = req["duration_minutes"]
    require(duration is None or duration == "not_applicable" or
            (type(duration) in (int, float) and 0 < duration < float("inf")), "时长须为正数或 not_applicable")
    count = req["slide_count"]
    require(count is None or (type(count) is int and count > 0), "页数须为正整数")
    if complete:
        for key in ("topic", "audience", "objective", "source_scope"):
            require(text_ok(req[key]), f"尚未明确 {key}")
        require(duration is not None and count is not None, "尚未明确时长或页数")


def attachment_path(workspace, relative):
    require(isinstance(relative, str) and "\\" not in relative, "附件使用 files/ 下的相对路径和正斜线")
    parts = relative.split("/")
    require(len(parts) >= 2 and parts[0] == "files" and
            all(part not in ("", ".", "..") for part in parts), "附件必须位于本任务 files/ 内")
    target = (workspace / relative).resolve()
    require(target.is_relative_to((workspace / "files").resolve()) and
            target.is_relative_to(workspace), "附件不能通过链接指向任务外部")
    require(target.is_file() and target.stat().st_size > 0, f"附件缺失或为空: {relative}")
    return target


def artifacts(workspace, n):
    entries = load(stage_dir(workspace, n) / "artifacts.json")
    require(isinstance(entries, list), "artifacts.json 必须为数组")
    seen = set()
    for entry in entries:
        require(isinstance(entry, dict) and set(entry) == {"role", "path"}
                and text_ok(entry["role"]), "附件须含 role/path")
        require((entry["role"], entry["path"]) not in seen, "附件 role/path 重复")
        attachment_path(workspace, entry["path"])
        seen.add((entry["role"], entry["path"]))
    return entries


def source_catalog(workspace):
    rows = load(stage_dir(workspace, 2) / "sources.json")
    require(isinstance(rows, list) and rows, "缺少可追溯的来源目录 sources.json")
    registered = {x["path"] for x in artifacts(workspace, 2)}
    sources = {}
    for row in rows:
        require(isinstance(row, dict), "来源目录每项须为对象")
        for key in ("id", "title", "path", "origin"):
            require(text_ok(row.get(key)), f"来源目录缺少 {key}")
        require(row["id"] not in sources, "来源 ID 重复")
        require(row.get("kind") in ("document", "data", "user_brief", "research"), "来源 kind 无效")
        require(row["path"] in registered, "来源文件须先在阶段2附件清单注册")
        attachment_path(workspace, row["path"])
        sources[row["id"]] = row
    return sources


def focus_snapshot(workspace, req):
    paths = sorted(focus_dir(workspace).glob("*.json"))
    require({p.name for p in paths} >= {"analysis.json", "review.json"}, "缺少重点分析文件")
    require(all(p.resolve().is_relative_to(workspace) for p in paths), "重点文件不能链接到任务外部")
    return {"files": {p.relative_to(workspace).as_posix(): sha(p) for p in paths},
            "source_stage": snapshot(workspace, req, 2),
            "requirements": {k: req[k] for k, owner in FIELDS.items() if owner <= 3}}


def focus_validate(workspace, req, resolved=True, reviewed=True):
    sources = source_catalog(workspace)
    analysis = ca.validate(load(focus_dir(workspace) / "analysis.json"), sources, resolved=resolved)
    if reviewed:
        check_report(load(focus_dir(workspace) / "review.json"), fresh_focus_review()["checks"])
    return analysis, sources


def check_report(report, keys):
    require(isinstance(report, dict) and text_ok(report.get("summary")), "缺少实际检查结论")
    checks = report.get("checks")
    require(isinstance(checks, dict) and set(checks) == set(keys), "固定检查项缺失或 ID 被改动")
    for key, check in checks.items():
        require(isinstance(check, dict) and check.get("passed") is True
                and text_ok(check.get("evidence")), f"检查项尚未通过或缺少依据: {key}")


def focus_ready(workspace, state, req):
    focus = state["focus"]
    require(focus["status"] in ("approved", "outline"), "先确认汇报重点，再开始逐页方案")
    require(focus["snapshot"] == focus_snapshot(workspace, req), "重点确认已过期")
    require(focus_record_current(workspace, focus), "重点确认归档缺失或被修改")
    focus_validate(workspace, req)


def focus_record_current(workspace, focus):
    receipt = focus.get("approval")
    if not isinstance(receipt, dict):
        return False
    relative = receipt.get("record_path")
    if not isinstance(relative, str) or not relative.startswith("history/focus-"):
        return False
    path = (workspace / relative).resolve()
    return (path.is_relative_to(workspace / "history") and path.is_file() and
            sha(path) == receipt.get("record_sha256"))


def record_focus(workspace, state, req, analysis, sources, message, source, mode):
    snap = focus_snapshot(workspace, req)
    receipt = {"at": now(), "message": message, "source": source, "mode": mode,
               "fingerprint": digest(snap)}
    payload = {"analysis": analysis, "sources": sources, "requirements": snap["requirements"],
               "input_snapshot": snap, "receipt": receipt}
    relative = "history/focus-" + digest(payload) + ".json"
    write(workspace / relative, payload)
    receipt.update(record_path=relative, record_sha256=sha(workspace / relative))
    state["focus"].update(status="approved", snapshot=snap, approval=receipt)
    event(state, "focus_approved" if mode == "user" else "focus_delegated", receipt=receipt)


def focus_command(args, workspace, state, req):
    require(next_stage(state) == 3 and state["stages"][2]["status"] in
            ("in_progress", "awaiting_confirmation"), "先完成阶段1、2并 begin 阶段3")
    focus = state["focus"]
    if args.command == "begin-outline":
        if state.get("review_overrides", {}).get("3") == "agent" and focus["status"] == "awaiting_confirmation":
            # Explicit stage-3 delegation covers both of its review steps; preserve its receipt in history.
            analysis, sources = focus_validate(workspace, req)
            require(focus["snapshot"] == focus_snapshot(workspace, req), "重点检查已过期")
            authorization = next((e for e in reversed(state["events"]) if
                                  e["action"] == "review_policy" and e["stage"] == 3 and e["mode"] == "agent"), None)
            require(authorization is not None, "缺少阶段3委托的用户授权记录")
            record_focus(workspace, state, req, analysis, sources,
                         authorization["message"], authorization["source"], "delegated")
        focus_ready(workspace, state, req)
        focus["status"] = "outline"
        event(state, "outline_started", fingerprint=digest(focus["snapshot"]))
        return None
    report_only = args.command == "focus-report"
    analysis, sources = focus_validate(workspace, req, resolved=not report_only, reviewed=not report_only)
    if report_only:
        return ca.render(analysis, sources)
    if focus["status"] not in ("approved", "outline"):
        require(load(stage_dir(workspace, 3) / "outline.json") == [],
                "检测到未确认重点前已填写逐页大纲；先备份并清空大纲，再确认重点")
    snap = focus_snapshot(workspace, req)
    if args.command == "approve-focus":
        require(text_ok(args.message) and text_ok(args.source), "须记录用户确认重点的原话与出处")
        record_focus(workspace, state, req, analysis, sources, args.message, args.source, "user")
    elif args.command == "check-focus":
        if focus["status"] not in ("approved", "outline"):
            focus.update(status="awaiting_confirmation", snapshot=snap, approval=None)
        event(state, "focus_checked", fingerprint=digest(snap))
    return ca.render(analysis, sources)


def snapshot(workspace, req, n):
    folder = stage_dir(workspace, n)
    files = {}
    for path in folder.rglob("*"):
        if path.is_file():
            resolved = path.resolve()
            require(resolved.is_relative_to(workspace), "阶段文件不能链接到外部")
            files[path.relative_to(workspace).as_posix()] = sha(path)
    for entry in artifacts(workspace, n):
        files[entry["path"]] = sha(attachment_path(workspace, entry["path"]))
    if n == 1:
        files["defaults.snapshot.json"] = sha(workspace / "defaults.snapshot.json")
    return {"requirements": {k: req[k] for k, owner in FIELDS.items() if owner == n},
            "files": files}


def sync(workspace, state):
    req = load(workspace / "requirements.json")
    requirements_shape(req)
    prior = state["requirements"]
    changed = [k for k in FIELDS if prior[k] != req[k]]
    if changed:
        first = min(FIELDS[k] for k in changed)
        current = next_stage(state)
        if current:
            first = min(first, current)
        invalidate(workspace, state, first, "任务要求变化: " + ", ".join(changed))
        event(state, "requirements_changed", before=prior, after=req,
              reason="检测到文件直接变更", affected_from=first)
        state["requirements"] = req
        state["requirement_revision"] += 1
    for n, item in enumerate(state["stages"], 1):
        if item["status"] == "completed" or item.get("approval"):
            try:
                current = snapshot(workspace, req, n)
                expected = item.get("snapshot") or item["approval"]["snapshot"]
                match = current == expected
            except (WorkflowError, OSError, ValueError, TypeError, KeyError):
                match = False
            if not match:
                invalidate(workspace, state, n, f"阶段 {n} 成果、附件或检查记录改变/缺失", preserve_focus=True)
                break
    if state["focus"].get("snapshot"):
        try:
            same = state["focus"]["snapshot"] == focus_snapshot(workspace, req)
            if state["focus"]["status"] in ("approved", "outline"):
                same = same and focus_record_current(workspace, state["focus"])
        except (OSError, ValueError, TypeError, KeyError):
            same = False
        if not same:
            invalidate(workspace, state, 3, "重点分析、来源或检查记录改变，需重新确认重点")
    return req


def approval_needed(state, req, n):
    override = state.get("review_overrides", {}).get(str(n))
    return (override == "user") if override else (req["review_all"] or n in (1, 3, 4))


def deck_formats(workspace, entries, role, req):
    selected = [attachment_path(workspace, x["path"]) for x in entries if x["role"] == role]
    require(selected, f"缺少 {role} 附件")
    formats = set()
    for path in selected:
        suffix = path.suffix.lower().lstrip(".")
        require(suffix in ("pptx", "pdf"), f"{role} 只接受 PPTX/PDF")
        formats.add(suffix)
        if suffix == "pptx":
            try:
                with zipfile.ZipFile(path) as archive:
                    require(archive.testzip() is None, "PPTX ZIP 校验失败")
                    require("[Content_Types].xml" in archive.namelist(), "缺少 PPTX 内容类型")
                    root = ET.fromstring(archive.read("ppt/presentation.xml"))
                    ns = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
                    listing = root.find(ns + "sldIdLst")
                    require(listing is not None and len(listing) == req["slide_count"], "PPTX 页数与要求不符")
            except (zipfile.BadZipFile, KeyError, ET.ParseError) as exc:
                raise WorkflowError(f"PPTX 基本结构无效: {path.name}") from exc
        else:
            with path.open("rb") as stream:
                require(stream.read(5) == b"%PDF-", "PDF 文件头无效")
    require(set(req["outputs"]) <= formats, f"{role} 未覆盖要求的输出格式")
    return {sha(path) for path in selected}


def validate(workspace, req, n):
    folder = stage_dir(workspace, n)
    path = folder / STAGES[n - 1][2]
    require(path.is_file(), f"缺少 {path.name}")
    if path.suffix == ".md":
        content = path.read_text(encoding="utf-8-sig")
        require(text_ok(content) and len(content.strip()) > 10, f"{path.name} 仍为空白或草稿")
    check_report(load(folder / "review.json"), STAGES[n - 1][3])
    entries = artifacts(workspace, n)
    roles = {x["role"] for x in entries}
    if n == 1:
        requirements_shape(req, complete=True)
    elif n == 2:
        source_catalog(workspace)
    elif n == 3:
        focus_state = load(workspace / "state.json")
        require(focus_state["focus"]["status"] == "outline", "先 begin-outline 解锁逐页方案")
        focus_ready(workspace, focus_state, req)
        analysis, _ = focus_validate(workspace, req)
        candidates = {x["id"]: x for x in analysis["candidates"]}
        outline = load(path)
        require(isinstance(outline, list) and len(outline) == req["slide_count"], "大纲页数不符")
        ids = set()
        covered = set()
        for slide in outline:
            require(isinstance(slide, dict), "大纲每页须为对象")
            for key in ("id", "title", "purpose", "content", "visual", "editable_requirements", "speaker_notes"):
                require(text_ok(slide.get(key)), f"大纲缺少 {key}")
            require(slide["id"] not in ids, "大纲页面 ID 重复")
            ids.add(slide["id"])
            require(isinstance(slide.get("evidence"), list) and
                    all(text_ok(x) for x in slide["evidence"]), "大纲证据须为来源文本数组")
            refs = slide.get("focus_ids")
            require(isinstance(refs, list) and all(text_ok(x) and x in candidates for x in refs),
                    "每页须用 focus_ids 引用已确认的候选内容，结构页可为空数组")
            require(all(candidates[x]["disposition"] != "omit" for x in refs), "大纲不能采用已决定省略的内容")
            covered.update(refs)
        required_ids = {x["id"] for x in analysis["candidates"] if x["disposition"] == "main"}
        require(required_ids <= covered, "大纲遗漏已确认的汇报重点")
    elif n == 4:
        require(text_ok(req["template"]), "阶段4需确定模板或 free_design")
        require("representative" in roles, "缺少实际代表页附件")
        for entry in entries:
            if entry["role"] == "representative":
                require(Path(entry["path"]).suffix.lower() in
                        (".png", ".jpg", ".jpeg", ".webp", ".svg", ".html", ".pdf", ".pptx"),
                        "代表页需为可查看的图片、SVG、HTML、PDF 或 PPTX")
    elif n == 6:
        require("source" in roles, "缺少制作源文件附件")
        deck_formats(workspace, entries, "draft", req)
    elif n == 7:
        reviewed = deck_formats(workspace, entries, "reviewed_deck", req)
        drafts = deck_formats(workspace, artifacts(workspace, 6), "draft", req)
        require(reviewed == drafts, "阶段7审阅文件与阶段6草稿不一致，先更新制作阶段")
    elif n == 8:
        final = deck_formats(workspace, entries, "final", req)
        reviewed = deck_formats(workspace, artifacts(workspace, 7), "reviewed_deck", req)
        require(final == reviewed, "交付文件不是阶段7已审阅的版本")
        source_hashes = {sha(attachment_path(workspace, x["path"])) for x in entries if x["role"] == "source"}
        original_sources = {sha(attachment_path(workspace, x["path"])) for x in artifacts(workspace, 6)
                            if x["role"] == "source"}
        require(original_sources and original_sources <= source_hashes, "交付源文件未覆盖全部制作源文件")
    return snapshot(workspace, req, n)


@contextmanager
def lock(workspace):
    target = workspace / ".workflow.lock"
    try:
        fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise WorkflowError("任务已有操作锁；确认没有其他操作后再恢复") from exc
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(json.dumps({"pid": os.getpid(), "at": now()}))
        yield
    finally:
        target.unlink(missing_ok=True)


def init(workspace, title):
    require(text_ok(title), "任务名称不能为空")
    require(not workspace.exists() or not any(workspace.iterdir()), "初始化只接受新目录或空目录")
    defaults = load(ROOT / "defaults.json")
    req = dict.fromkeys(FIELDS)
    req.update(defaults)
    req.update(source_notes="", visual_notes="")
    requirements_shape(req)
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "files").mkdir()
    write(workspace / "defaults.snapshot.json", defaults)
    write(workspace / "requirements.json", req)
    for n, (_, name, filename, _) in enumerate(STAGES, 1):
        folder = stage_dir(workspace, n)
        folder.mkdir(parents=True)
        if filename.endswith(".json"):
            write(folder / filename, [])
        else:
            (folder / filename).write_text(f"# {name}\n\n{DRAFT}\n\n", encoding="utf-8")
        write(folder / "artifacts.json", [])
        write(folder / "review.json", fresh_review(n))
    setup_content_files(workspace)
    state = {"schema": SCHEMA, "title": title, "created_at": now(),
             "requirements": req, "requirement_revision": 1, "review_overrides": {},
             "focus": fresh_focus(),
             "stages": [{"status": "not_started", "snapshot": None, "approval": None} for _ in STAGES],
             "events": []}
    event(state, "initialized")
    write(workspace / "state.json", state)
    return status(workspace, state, req)


def status(workspace, state, req):
    current = next_stage(state)
    return {"ok": True, "workspace": str(workspace), "title": state["title"],
            "requirement_revision": state["requirement_revision"], "current_stage": current,
            "complete": current is None, "requirements": req,
            "focus": {"status": state["focus"]["status"],
                      "approved": state["focus"]["status"] in ("approved", "outline"),
                      "next_action": ("begin --stage 3" if state["stages"][2]["status"] in ("not_started", "needs_revision") else
                                      "begin-outline" if state["focus"]["status"] == "approved" else
                                      "逐页方案" if state["focus"]["status"] == "outline" else
                                      "begin-outline" if state["focus"]["status"] == "awaiting_confirmation" and
                                      state.get("review_overrides", {}).get("3") == "agent" else
                                      "approve-focus" if state["focus"]["status"] == "awaiting_confirmation" else
                                      "填写 analysis.json 并 check-focus") if current == 3 else None},
            "stages": [{"stage": n, "name": STAGES[n - 1][1], "status": item["status"],
                        "user_confirmation": approval_needed(state, req, n),
                        "approved": bool(item.get("approval")), "reason": item.get("reason")}
                       for n, item in enumerate(state["stages"], 1)],
            "recent_events": state["events"][-8:]}


def execute(args):
    if hasattr(args, "reason"):
        require(text_ok(args.reason), "须说明变更或回退原因")
    raw = Path(args.workspace).expanduser()
    require(raw.is_absolute(), "任务目录必须使用绝对路径")
    workspace = raw.resolve()
    if args.command == "init":
        return init(workspace, args.title)
    require((workspace / "state.json").is_file(), "此目录没有工作流任务")
    with lock(workspace):
        state = load(workspace / "state.json")
        if state.get("schema") == "ppt-workflow.v1":
            setup_content_files(workspace)
            state["schema"] = SCHEMA
            state["focus"] = fresh_focus()
            invalidate(workspace, state, 2, "升级内容分析模块，旧任务从材料阶段补齐来源与重点确认")
            event(state, "migrated", before="ppt-workflow.v1", after=SCHEMA)
            write(workspace / "state.json", state)
        require(state.get("schema") == SCHEMA, "工作流状态版本不兼容")
        req = sync(workspace, state)
        write(workspace / "state.json", state)  # Persist invalidations even if the requested action fails.
        current = next_stage(state)
        if args.command in ("status", "resume"):
            return status(workspace, state, req)
        proposal = None
        if args.command in ("focus-report", "check-focus", "approve-focus", "begin-outline"):
            proposal = focus_command(args, workspace, state, req)
        elif args.command == "revise":
            changes = load(Path(args.changes))
            require(isinstance(changes, dict) and changes and set(changes) <= set(FIELDS), "变更须为已知要求字段的非空对象")
            updated = {**req, **changes}
            requirements_shape(updated)
            changed = [k for k in changes if req[k] != updated[k]]
            if changed:
                first = min(FIELDS[k] for k in changed)
                if current:
                    first = min(first, current)
                invalidate(workspace, state, first, args.reason)
                event(state, "requirements_changed", before=req, after=updated,
                      reason=args.reason, affected_from=first)
                state["requirements"] = updated
                state["requirement_revision"] += 1
                write(workspace / "requirements.json", updated)
                req = updated
        else:
            n = args.stage
            item = state["stages"][n - 1]
            if args.command == "reopen":
                require(current is None or n <= current, "不能越过未完成前置阶段回退")
                invalidate(workspace, state, n, args.reason)
            elif args.command == "set-review":
                require(current is not None and n >= current, "修改已完成阶段审核偏好前先 reopen")
                require(text_ok(args.message) and text_ok(args.source), "须记录用户原话和出处")
                state["review_overrides"][str(n)] = args.mode
                invalidate(workspace, state, n, "用户调整审核方式")
                event(state, "review_policy", stage=n, mode=args.mode,
                      message=args.message, source=args.source)
            else:
                require(n == current, f"只能操作最早未完成阶段: {current or '任务已完成'}")
                if args.command == "begin":
                    item["status"] = "in_progress"
                    event(state, "began", stage=n)
                else:
                    require(item["status"] in ("in_progress", "awaiting_confirmation"), "先 begin 当前阶段并完成实际工作")
                    snap = validate(workspace, req, n)
                    needed = approval_needed(state, req, n)
                    if args.command == "approve":
                        require(needed, "此阶段无需用户确认")
                        require(text_ok(args.message) and text_ok(args.source), "须记录用户原话和出处")
                        item["approval"] = {"snapshot": snap, "message": args.message,
                                            "source": args.source, "at": now()}
                        item["status"] = "awaiting_confirmation"
                        event(state, "approved", stage=n, message=args.message, source=args.source,
                              fingerprint=digest(snap))
                    elif args.command == "complete":
                        require(not needed or (item.get("approval") and
                                item["approval"]["snapshot"] == snap), "当前版本缺少用户确认，不能完成阶段")
                        item.update(status="completed", snapshot=snap, completed_at=now(), reason=None)
                        event(state, "completed", stage=n, fingerprint=digest(snap))
                    elif args.command == "check":
                        item["status"] = "awaiting_confirmation" if needed else "in_progress"
                        event(state, "checked", stage=n, fingerprint=digest(snap))
        write(workspace / "state.json", state)
        result = status(workspace, state, req)
        if proposal is not None:
            result["proposal_markdown"] = proposal
        return result


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    commands = p.add_subparsers(dest="command", required=True)
    for name in ("init", "status", "resume", "begin", "check", "approve", "complete", "revise", "reopen", "set-review",
                 "focus-report", "check-focus", "approve-focus", "begin-outline"):
        sub = commands.add_parser(name)
        sub.add_argument("--workspace", required=True)
        if name == "init":
            sub.add_argument("--title", required=True)
        if name in ("begin", "check", "approve", "complete", "reopen", "set-review"):
            sub.add_argument("--stage", type=int, choices=range(1, 9), required=True)
        if name in ("approve", "set-review", "approve-focus"):
            sub.add_argument("--message", required=True)
            sub.add_argument("--source", required=True)
        if name in ("revise", "reopen"):
            sub.add_argument("--reason", required=True)
        if name == "revise":
            sub.add_argument("--changes", required=True)
        if name == "set-review":
            sub.add_argument("--mode", choices=("user", "agent"), required=True)
    return p


def main():
    try:
        result = execute(parser().parse_args())
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (WorkflowError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
