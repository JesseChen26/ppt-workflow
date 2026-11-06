"""Behavioral tests. Minimal deck fixtures exercise gates, not visual quality."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

import workflow as w


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="ppt-workflow-test-")
        self.root = Path(self.temp.name).resolve()
        self.ws = self.root / "中文任务"
        self.run_cmd("init", "--title", "阶段流程测试")
        self.change(topic="项目进展", audience="研究组", objective="讨论下一步实验",
                    duration_minutes=10, slide_count=2, source_scope="仅用户材料",
                    template="free_design")

    def tearDown(self):
        self.temp.cleanup()

    def run_cmd(self, cmd, *args):
        return w.execute(w.parser().parse_args([cmd, "--workspace", str(self.ws), *map(str, args)]))

    def change(self, **changes):
        path = self.root / "changes.json"
        w.write(path, changes)
        return self.run_cmd("revise", "--changes", path, "--reason", "测试用户变更")

    def attach(self, n, entries):
        w.write(w.stage_dir(self.ws, n) / "artifacts.json", entries)

    def deck(self, name="draft.pptx", pages=2):
        path = self.ws / "files" / name
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("[Content_Types].xml", "<Types/>")
            slides = "".join(f'<p:sldId id="{256 + i}"/>' for i in range(pages))
            archive.writestr("ppt/presentation.xml", '<p:presentation xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:sldIdLst>' + slides + '</p:sldIdLst></p:presentation>')
        return path

    def fill(self, n):
        folder = w.stage_dir(self.ws, n)
        path = folder / w.STAGES[n - 1][2]
        if n == 3:
            req = w.load(self.ws / "requirements.json")
            w.write(path, [{"id": f"p{i}", "title": "测试标题", "purpose": "解释实验结果",
                            "content": "仅用于测试的明确内容", "evidence": [], "visual": "文字与图表",
                            "focus_ids": ["c1"],
                            "editable_requirements": "标题和数据可编辑", "speaker_notes": "讲解实验条件"}
                           for i in range(req["slide_count"])])
        else:
            path.write_text("# 已填写的阶段记录\n\n测试夹具，不用于真实演示稿交付。", encoding="utf-8")
        if n == 2:
            source = self.ws / "files" / "input.md"
            source.write_text("# 测试材料\n\n实验对比需要保留条件。", encoding="utf-8")
            self.attach(2, [{"role": "input", "path": "files/input.md"}])
            w.write(folder / "sources.json", [{"id": "s1", "title": "测试输入", "kind": "document",
                                               "path": "files/input.md", "origin": "隔离测试材料"}])
        if n == 4:
            (self.ws / "files" / "representative.svg").write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720"><text x="20" y="60">TEST FIXTURE</text></svg>', encoding="utf-8")
            self.attach(n, [{"role": "representative", "path": "files/representative.svg"}])
        elif n == 6:
            self.deck()
            (self.ws / "files" / "source.js").write_text("// test source", encoding="utf-8")
            self.attach(n, [{"role": "draft", "path": "files/draft.pptx"},
                            {"role": "source", "path": "files/source.js"}])
        elif n == 7:
            self.attach(n, [{"role": "reviewed_deck", "path": "files/draft.pptx"}])
        elif n == 8:
            self.attach(n, [{"role": "final", "path": "files/draft.pptx"},
                            {"role": "source", "path": "files/source.js"}])
        report = w.fresh_review(n)
        report["summary"] = "测试检查已完成；不表示实际视觉检查"
        for item in report["checks"].values():
            item.update(passed=True, evidence="测试用的明确评估依据")
        if n in (3, 7):
            context = w.review_context(self.ws, w.load(self.ws / "requirements.json"), n)
            report["assessment"] = {**context["assessment_template"],
                "reviewer": "隔离测试夹具（非真实审查）", "verdict": "pass",
                "coverage": [{"page_id": pid, "evidence": "结构测试夹具，不声称看过实际页面",
                              **({"artifact": "files/draft.pptx"} if n == 7 else {})}
                             for pid in context["page_ids"]]}
        w.write(folder / "review.json", report)

    def finish(self, n):
        self.run_cmd("begin", "--stage", n)
        if n == 3:
            self.prepare_focus()
            self.run_cmd("check-focus")
            self.run_cmd("approve-focus", "--message", "测试用户确认汇报重点", "--source", "隔离测试输入")
            self.run_cmd("begin-outline")
        self.fill(n)
        result = self.run_cmd("check", "--stage", n)
        if result["stages"][n - 1]["user_confirmation"]:
            self.run_cmd("approve", "--stage", n, "--message", "测试用户：同意当前成果",
                         "--source", "隔离的自动测试输入")
        return self.run_cmd("complete", "--stage", n)

    def prepare_focus(self):
        analysis = {
            "document_summary": {"problem": "比较实验结果", "approach": "受控条件下比较",
                                 "findings": ["条件影响结果解释"], "limitations": ["仅为测试材料"]},
            "audience_fit": {"existing_knowledge": "了解实验基础", "desired_outcome": "讨论下一步实验",
                             "adaptation": "压缩背景，保留条件"},
            "core_message": "实验结论必须结合适用条件讨论",
            "candidates": [{"id": "c1", "title": "对比条件", "claim": "比较时需交代条件",
                            "disposition": "main", "reason": "帮助听众判断适用范围", "claim_kind": "fact",
                            "evidence": [{"source_id": "s1", "locator": "第1节第1段"}],
                            "visual_opportunity": "可用条件对照表", "caveats": ["不夸大样本范围"]}],
            "open_questions": [],
        }
        w.write(w.focus_dir(self.ws) / "analysis.json", analysis)
        report = w.fresh_focus_review()
        report["summary"] = "测试内容分析检查"
        for check in report["checks"].values():
            check.update(passed=True, evidence="测试资料中有对应内容和适用条件")
        w.write(w.focus_dir(self.ws) / "review.json", report)

    def through(self, end):
        for n in range(1, end + 1):
            self.finish(n)

    def test_predecessor_blocks_begin_and_complete(self):
        for cmd in ("begin", "complete"):
            with self.assertRaises(w.WorkflowError):
                self.run_cmd(cmd, "--stage", 2)
        self.assertEqual(self.run_cmd("status")["current_stage"], 1)

    def test_empty_scaffold_and_removed_check_block(self):
        self.run_cmd("begin", "--stage", 1)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 1)
        self.fill(1)
        path = w.stage_dir(self.ws, 1) / "review.json"
        report = w.load(path)
        del report["checks"]["scope"]
        w.write(path, report)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check", "--stage", 1)

    def test_missing_requirements_block(self):
        self.change(audience=None)
        self.run_cmd("begin", "--stage", 1)
        self.fill(1)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check", "--stage", 1)

    def test_approval_required_and_bound_to_content(self):
        self.run_cmd("begin", "--stage", 1)
        self.fill(1)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 1)
        self.run_cmd("approve", "--stage", 1, "--message", "同意", "--source", "测试用户")
        with (w.stage_dir(self.ws, 1) / "brief.md").open("a", encoding="utf-8") as f:
            f.write("\n更改已确认内容")
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 1)
        state = w.load(self.ws / "state.json")
        self.assertIsNone(state["stages"][0]["approval"])
        self.assertEqual(state["stages"][0]["status"], "needs_revision")

    def test_complete_eight_stages_and_resume_process(self):
        self.through(8)
        process = subprocess.run([sys.executable, str(Path(w.__file__)), "resume",
                                  "--workspace", str(self.ws)], capture_output=True,
                                 encoding="utf-8", check=True)
        result = json.loads(process.stdout)
        self.assertTrue(result["complete"])
        self.assertIsNone(result["current_stage"])

    def test_page_count_change_invalidates_from_outline(self):
        self.through(4)
        result = self.change(slide_count=3)
        self.assertEqual(result["current_stage"], 3)
        self.assertEqual(result["stages"][0]["status"], "completed")
        self.assertEqual(result["stages"][3]["status"], "needs_revision")
        self.assertFalse(any(c["passed"] for c in
                             w.load(w.stage_dir(self.ws, 3) / "review.json")["checks"].values()))
        self.run_cmd("begin", "--stage", 3)
        self.fill(3)
        outline = w.load(w.stage_dir(self.ws, 3) / "outline.json")
        w.write(w.stage_dir(self.ws, 3) / "outline.json", outline[:2])
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check", "--stage", 3)

    def test_audience_change_restarts_contract(self):
        self.through(4)
        result = self.change(audience="非专业听众")
        self.assertEqual(result["current_stage"], 1)
        self.assertTrue(all(x["status"] == "needs_revision" for x in result["stages"][:4]))

    def test_external_requirements_change_detected(self):
        self.through(4)
        req = w.load(self.ws / "requirements.json")
        req["language"] = "en"
        w.write(self.ws / "requirements.json", req)
        self.assertEqual(self.run_cmd("resume")["current_stage"], 3)

    def test_shared_attachment_invalidates_first_owner(self):
        self.through(3)
        self.run_cmd("begin", "--stage", 4)
        self.fill(4)
        shared = self.ws / "files" / "shared.css"
        shared.write_text("body { color: black; }", encoding="utf-8")
        entries = w.artifacts(self.ws, 4)
        self.attach(4, entries + [{"role": "shared_style", "path": "files/shared.css"}])
        self.run_cmd("approve", "--stage", 4, "--message", "确认", "--source", "测试用户")
        self.run_cmd("complete", "--stage", 4)
        for n in (5, 6, 7):
            self.finish(n)
        shared.write_text("body { color: red; }", encoding="utf-8")
        self.assertEqual(self.run_cmd("status")["current_stage"], 4)

    def test_deleted_artifact_and_failed_action_persist_rollback(self):
        self.through(7)
        (self.ws / "files" / "source.js").unlink()
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("begin", "--stage", 8)
        self.assertEqual(w.load(self.ws / "state.json")["stages"][5]["status"], "needs_revision")

    def test_wrong_deck_review_and_final_bytes_rejected(self):
        self.through(6)
        self.run_cmd("begin", "--stage", 7)
        self.fill(7)
        self.deck("other.pptx")
        # ZIPs made at the same instant may have identical bytes; add a distinct payload.
        with zipfile.ZipFile(self.ws / "files" / "other.pptx", "a") as archive:
            archive.writestr("different.txt", "another version")
        self.attach(7, [{"role": "reviewed_deck", "path": "files/other.pptx"}])
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check", "--stage", 7)
        self.attach(7, [{"role": "reviewed_deck", "path": "files/draft.pptx"}])
        self.run_cmd("complete", "--stage", 7)
        self.run_cmd("begin", "--stage", 8)
        self.fill(8)
        self.attach(8, [{"role": "final", "path": "files/other.pptx"},
                        {"role": "source", "path": "files/source.js"}])
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 8)

    def test_pptx_count_and_requested_formats_enforced(self):
        self.change(outputs=["pptx", "pdf"])
        self.through(5)
        self.run_cmd("begin", "--stage", 6)
        self.fill(6)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check", "--stage", 6)
        pdf = self.ws / "files" / "deck.pdf"
        pdf.write_bytes(b"%PDF-1.4\nTest fixture only")
        self.attach(6, w.artifacts(self.ws, 6) + [{"role": "draft", "path": "files/deck.pdf"}])
        self.run_cmd("check", "--stage", 6)
        self.deck(pages=1)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check", "--stage", 6)

    def test_path_escape_rejected(self):
        self.finish(1)
        self.run_cmd("begin", "--stage", 2)
        self.fill(2)
        outside = self.root / "outside.txt"
        outside.write_text("not a task attachment", encoding="utf-8")
        for path in (str(outside), "files/../../outside.txt", "../state.json"):
            self.attach(2, [{"role": "source", "path": path}])
            with self.assertRaises(w.WorkflowError):
                self.run_cmd("check", "--stage", 2)

    def test_review_all_and_explicit_delegation(self):
        self.change(review_all=True)
        self.finish(1)
        self.run_cmd("begin", "--stage", 2)
        self.fill(2)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 2)
        self.run_cmd("set-review", "--stage", 2, "--mode", "agent",
                     "--message", "第二阶段由你按标准判断", "--source", "测试用户")
        self.run_cmd("begin", "--stage", 2)
        self.fill(2)
        self.run_cmd("complete", "--stage", 2)
        self.assertEqual(self.run_cmd("status")["current_stage"], 3)

    def test_defaults_snapshot_and_previous_task_are_independent(self):
        before = w.load(self.ws / "defaults.snapshot.json")
        self.change(language="en", template="custom")
        self.assertEqual(w.load(self.ws / "defaults.snapshot.json"), before)
        self.assertEqual(w.load(w.ROOT / "defaults.json")["template"], None)

    def test_nonempty_init_and_concurrent_lock_rejected(self):
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("init", "--title", "overwrite")
        lock = self.ws / ".workflow.lock"
        lock.write_text("test process", encoding="utf-8")
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("status")
        self.assertTrue(lock.exists())
        lock.unlink()

    def test_reopen_preserves_files_and_archives_prior_review(self):
        self.through(4)
        path = w.stage_dir(self.ws, 3) / "outline.json"
        original = path.read_bytes()
        self.run_cmd("reopen", "--stage", 3, "--reason", "用户调整论证")
        self.assertEqual(path.read_bytes(), original)
        self.assertTrue(any(e["action"] == "review_archived" and e["stage"] == 3
                            for e in w.load(self.ws / "state.json")["events"]))

    def test_default_library_update_does_not_change_existing_task(self):
        before = w.load(self.ws / "requirements.json")
        alternate = self.root / "alternate-skill-config"
        alternate.mkdir()
        w.write(alternate / "defaults.json", {**w.load(w.ROOT / "defaults.json"), "language": "en"})
        original_root = w.ROOT
        try:
            w.ROOT = alternate
            new_workspace = self.root / "second-task"
            w.init(new_workspace, "采用新默认的任务")
            self.assertEqual(w.load(new_workspace / "requirements.json")["language"], "en")
            self.assertEqual(self.run_cmd("status")["requirements"], before)
        finally:
            w.ROOT = original_root

    def test_delivery_source_coverage_and_post_delivery_change(self):
        self.through(7)
        self.run_cmd("begin", "--stage", 8)
        self.fill(8)
        (self.ws / "files" / "wrong-source.js").write_text("// wrong source", encoding="utf-8")
        self.attach(8, [{"role": "final", "path": "files/draft.pptx"},
                        {"role": "source", "path": "files/wrong-source.js"}])
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 8)
        self.fill(8)
        self.run_cmd("complete", "--stage", 8)
        (self.ws / "files" / "source.js").write_text("// changed after delivery", encoding="utf-8")
        result = self.run_cmd("resume")
        self.assertFalse(result["complete"])
        self.assertEqual(result["current_stage"], 6)

    def test_cli_failure_exit_code_does_not_advance(self):
        process = subprocess.run([sys.executable, str(Path(w.__file__)), "begin",
                                  "--workspace", str(self.ws), "--stage", "8"],
                                 capture_output=True, encoding="utf-8")
        self.assertEqual(process.returncode, 2)
        self.assertFalse(json.loads(process.stdout)["ok"])
        self.assertEqual(self.run_cmd("status")["current_stage"], 1)

    def start_focus(self):
        self.through(2)
        self.run_cmd("begin", "--stage", 3)
        self.prepare_focus()

    def approve_focus(self):
        self.run_cmd("check-focus")
        return self.run_cmd("approve-focus", "--message", "确认本次候选重点和取舍", "--source", "测试用户回复")

    def edit_analysis(self, mutate):
        path = w.focus_dir(self.ws) / "analysis.json"
        analysis = w.load(path)
        mutate(analysis)
        w.write(path, analysis)

    def test_focus_is_separate_gate_before_outline(self):
        self.start_focus()
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("begin-outline")
        result = self.run_cmd("check-focus")
        self.assertEqual(result["focus"]["status"], "awaiting_confirmation")
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("begin-outline")
        self.approve_focus()
        self.assertEqual(self.run_cmd("begin-outline")["focus"]["status"], "outline")
        self.fill(3)
        # Approval of focus alone cannot approve the resulting slide plan.
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 3)

    def test_written_outline_cannot_bypass_focus(self):
        self.start_focus()
        self.fill(3)
        for command, args in (("check-focus", ()), ("approve", ("--stage", 3)),
                              ("complete", ("--stage", 3))):
            if command == "approve":
                args += ("--message", "批准大纲", "--source", "测试用户")
            with self.assertRaises(w.WorkflowError):
                self.run_cmd(command, *args)

    def test_focus_requires_known_sources_and_locations(self):
        self.start_focus()
        for change in (
            lambda a: a["candidates"][0]["evidence"][0].update(source_id="nonexistent"),
            lambda a: a["candidates"][0]["evidence"][0].update(locator=""),
            lambda a: a["candidates"][0].update(evidence=[]),
        ):
            self.prepare_focus()
            self.edit_analysis(change)
            with self.assertRaises(w.WorkflowError):
                self.run_cmd("check-focus")

    def test_focus_requires_rationale_and_explicit_assumptions(self):
        self.start_focus()
        self.edit_analysis(lambda a: a["candidates"][0].update(reason=""))
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check-focus")
        self.prepare_focus()
        self.edit_analysis(lambda a: a["candidates"][0].update(claim_kind="assumption", evidence=[]))
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("check-focus")
        self.edit_analysis(lambda a: a["candidates"][0].update(assumption_note="仅为待验证实验建议"))
        report = self.run_cmd("check-focus")["proposal_markdown"]
        self.assertIn("尚非事实", report)

    def test_unresolved_question_is_visible_but_blocks_approval(self):
        self.start_focus()
        self.edit_analysis(lambda a: a["open_questions"].append(
            {"question": "本次更强调方法还是结果？", "blocking": True, "resolution": ""}))
        report = self.run_cmd("focus-report")["proposal_markdown"]
        self.assertIn("本次更强调方法还是结果", report)
        with self.assertRaises(w.WorkflowError):
            self.approve_focus()
        self.edit_analysis(lambda a: a["open_questions"][0].update(resolution="用户选择优先讨论方法"))
        self.approve_focus()

    def test_focus_edit_expires_confirmation_before_stage_complete(self):
        self.start_focus()
        self.approve_focus()
        self.edit_analysis(lambda a: a.update(core_message="更改本次核心信息"))
        state = self.run_cmd("resume")
        self.assertEqual(state["current_stage"], 3)
        self.assertFalse(state["focus"]["approved"])
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("begin-outline")

    def test_source_change_expires_focus_and_restarts_materials(self):
        self.start_focus()
        self.approve_focus()
        (self.ws / "files" / "input.md").write_text("# 新材料\n新的实验条件", encoding="utf-8")
        result = self.run_cmd("status")
        self.assertEqual(result["current_stage"], 2)
        self.assertFalse(result["focus"]["approved"])

    def test_outline_covers_main_points_and_excludes_omitted_content(self):
        self.start_focus()
        self.edit_analysis(lambda a: a["candidates"].append({**a["candidates"][0], "id": "c2", "disposition": "omit"}))
        self.approve_focus()
        self.run_cmd("begin-outline")
        self.fill(3)
        path = w.stage_dir(self.ws, 3) / "outline.json"
        original = w.load(path)
        for refs in ([], ["c2"], ["unknown"]):
            edited = [{**slide, "focus_ids": refs} for slide in original]
            w.write(path, edited)
            with self.assertRaises(w.WorkflowError):
                self.run_cmd("check", "--stage", 3)
        w.write(path, original)
        self.run_cmd("check", "--stage", 3)

    def test_outline_only_revision_preserves_unchanged_focus(self):
        self.through(3)
        path = w.stage_dir(self.ws, 3) / "outline.json"
        rows = w.load(path)
        rows[0]["title"] = "更清楚地说明实验条件"
        w.write(path, rows)
        result = self.run_cmd("status")
        self.assertEqual(result["current_stage"], 3)
        self.assertTrue(result["focus"]["approved"])
        self.assertEqual(result["focus"]["status"], "outline")

    def test_focus_resume_from_new_process(self):
        self.start_focus()
        self.approve_focus()
        process = subprocess.run([sys.executable, str(Path(w.__file__)), "resume",
                                  "--workspace", str(self.ws)], capture_output=True,
                                 encoding="utf-8", check=True)
        result = json.loads(process.stdout)
        self.assertEqual(result["focus"]["next_action"], "begin-outline")

    def test_explicit_stage_delegation_still_checks_focus(self):
        self.start_focus()
        self.run_cmd("set-review", "--stage", 3, "--mode", "agent", "--message", "重点与大纲均委托你决定",
                     "--source", "测试用户")
        self.run_cmd("begin", "--stage", 3)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("begin-outline")
        self.prepare_focus()
        self.run_cmd("check-focus")
        self.run_cmd("begin-outline")
        self.fill(3)
        self.assertEqual(self.run_cmd("complete", "--stage", 3)["current_stage"], 4)

    def test_legacy_task_upgrade_preserves_existing_files(self):
        self.through(4)
        path = w.stage_dir(self.ws, 3) / "outline.json"
        before = path.read_bytes()
        state = w.load(self.ws / "state.json")
        state["schema"] = "ppt-workflow.v1"
        del state["focus"]
        w.write(self.ws / "state.json", state)
        (w.stage_dir(self.ws, 2) / "sources.json").unlink()
        (w.focus_dir(self.ws) / "analysis.json").unlink()
        (w.focus_dir(self.ws) / "review.json").unlink()
        result = self.run_cmd("resume")
        self.assertEqual(result["current_stage"], 2)
        self.assertEqual(path.read_bytes(), before)
        self.assertTrue((w.stage_dir(self.ws, 2) / "sources.json").is_file())
        self.assertEqual(w.load(self.ws / "state.json")["schema"], "ppt-workflow.v2")

    def test_approved_analysis_is_archived_and_survives_later_edit(self):
        self.start_focus()
        self.approve_focus()
        receipt = w.load(self.ws / "state.json")["focus"]["approval"]
        archived = self.ws / receipt["record_path"]
        approved_message = w.load(archived)["analysis"]["core_message"]
        self.edit_analysis(lambda a: a.update(core_message="后来的修改内容"))
        self.run_cmd("status")
        self.assertEqual(w.load(archived)["analysis"]["core_message"], approved_message)
        self.assertEqual(w.load(archived)["receipt"]["message"], "确认本次候选重点和取舍")

    def test_missing_or_modified_approval_archive_invalidates_focus(self):
        self.start_focus()
        self.approve_focus()
        receipt = w.load(self.ws / "state.json")["focus"]["approval"]
        path = self.ws / receipt["record_path"]
        payload = w.load(path)
        payload["receipt"]["message"] = "被修改的确认记录"
        w.write(path, payload)
        self.assertFalse(self.run_cmd("status")["focus"]["approved"])
        self.run_cmd("begin", "--stage", 3)
        self.prepare_focus()
        self.approve_focus()
        receipt = w.load(self.ws / "state.json")["focus"]["approval"]
        (self.ws / receipt["record_path"]).unlink()
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("begin-outline")

    def test_source_catalog_cannot_reference_unregistered_material(self):
        self.finish(1)
        self.run_cmd("begin", "--stage", 2)
        self.fill(2)
        path = w.stage_dir(self.ws, 2) / "sources.json"
        catalog = w.load(path)
        catalog[0]["path"] = "files/unregistered.md"
        (self.ws / "files" / "unregistered.md").write_text("新材料", encoding="utf-8")
        w.write(path, catalog)
        with self.assertRaises(w.WorkflowError):
            self.run_cmd("complete", "--stage", 2)


    def assessment_fixture(self, n=3):
        self.through(n - 1)
        self.run_cmd("begin", "--stage", n)
        if n == 3:
            self.prepare_focus()
            self.run_cmd("approve-focus", "--message", "测试确认", "--source", "隔离测试")
            self.run_cmd("begin-outline")
        self.fill(n)
        path = w.stage_dir(self.ws, n) / "review.json"
        return path, w.load(path)

    def test_assessment_cannot_be_removed_from_new_task(self):
        path, report = self.assessment_fixture()
        del report["assessment"]
        w.write(path, report)
        with self.assertRaisesRegex(w.WorkflowError, "缺少专项审查"):
            self.run_cmd("complete", "--stage", 3)

    def test_assessment_blocks_serious_findings_until_verified(self):
        path, report = self.assessment_fixture()
        issue = {"id": "L1", "page_id": "p1", "problem": "将仿真改善当成实测结论",
                 "evidence": "材料只有仿真数据", "suggestion": "限定为仿真结果",
                 "severity": "major", "status": "open"}
        report["assessment"]["findings"] = [issue]
        w.write(path, report)
        with self.assertRaisesRegex(w.WorkflowError, "blocker/major"):
            self.run_cmd("check", "--stage", 3)
        issue.update(status="fixed", resolution="已限定标题")
        w.write(path, report)
        with self.assertRaisesRegex(w.WorkflowError, "复查结果"):
            self.run_cmd("check", "--stage", 3)
        issue["verification"] = "测试复查记录，实际任务需读取修订内容"
        w.write(path, report)
        self.run_cmd("check", "--stage", 3)

    def test_assessment_stale_after_outline_changes(self):
        _, _ = self.assessment_fixture()
        outline_path = w.stage_dir(self.ws, 3) / "outline.json"
        outline = w.load(outline_path)
        outline[1]["title"] = "修改后的标题"
        w.write(outline_path, outline)
        with self.assertRaisesRegex(w.WorkflowError, "输入已变化"):
            self.run_cmd("check", "--stage", 3)
        context = self.run_cmd("review-context", "--stage", 3)["review_context"]
        self.assertEqual(context["assessment_template"]["verdict"], "pending")
        self.assertEqual(context["assessment_template"]["coverage"], [])

    def test_assessment_requires_all_pages_and_honest_notes(self):
        path, report = self.assessment_fixture()
        last = report["assessment"]["coverage"].pop()
        w.write(path, report)
        with self.assertRaisesRegex(w.WorkflowError, "全部页面"):
            self.run_cmd("check", "--stage", 3)
        report["assessment"]["coverage"].append(last)
        report["assessment"]["limitations"] = ["未进行独立审查"]
        w.write(path, report)
        with self.assertRaisesRegex(w.WorkflowError, "pass_with_notes"):
            self.run_cmd("check", "--stage", 3)
        report["assessment"]["verdict"] = "pass_with_notes"
        w.write(path, report)
        self.run_cmd("check", "--stage", 3)

    def test_deck_assessment_requires_registered_evidence(self):
        path, report = self.assessment_fixture(7)
        report["assessment"]["coverage"][0]["artifact"] = "files/unseen.png"
        w.write(path, report)
        with self.assertRaisesRegex(w.WorkflowError, "成稿逐页审查"):
            self.run_cmd("complete", "--stage", 7)
        report["assessment"]["coverage"][0]["artifact"] = "files/draft.pptx"
        report["assessment"]["mode"] = "independent"
        w.write(path, report)
        with self.assertRaisesRegex(w.WorkflowError, "独立审查须注册"):
            self.run_cmd("complete", "--stage", 7)

    def test_completed_legacy_task_stays_complete_until_reopened(self):
        self.through(8)
        state = w.load(self.ws / "state.json")
        for n in (3, 7):
            path = w.stage_dir(self.ws, n) / "review.json"
            report = w.load(path)
            del report["assessment"]
            w.write(path, report)
            item = state["stages"][n - 1]
            del item["assessment_required"]
            item["snapshot"] = w.snapshot(self.ws, state["requirements"], n)
            if item["approval"]:
                item["approval"]["snapshot"] = item["snapshot"]
        w.write(self.ws / "state.json", state)
        self.assertTrue(self.run_cmd("resume")["complete"])
        self.run_cmd("reopen", "--stage", 7, "--reason", "复查导出")
        self.run_cmd("begin", "--stage", 7)
        state = w.load(self.ws / "state.json")
        self.assertTrue(state["stages"][6]["assessment_required"])
        self.assertEqual(w.load(w.stage_dir(self.ws, 7) / "review.json")["assessment"]["verdict"], "pending")


if __name__ == "__main__":
    unittest.main(verbosity=2)
