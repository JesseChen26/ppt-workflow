# PPT Workflow

[![Workflow tests](https://github.com/JesseChen26/ppt-workflow/actions/workflows/tests.yml/badge.svg)](https://github.com/JesseChen26/ppt-workflow/actions/workflows/tests.yml)

面向中文技术汇报、科研分享与培训课件的分阶段 PPT 工作流。先讨论汇报重点，再组织章节与逐页内容，最后完成视觉设计、制作、检查和交付。

包含可安装的 **Agent Skill**、仅依赖 Python 标准库的流程管理脚本，以及内容分析与页面设计参考。

## 能做什么

- 每次新任务重新明确听众、目标、时长与材料范围；默认设置独立保存。
- 八阶段顺序推进，检查通过后才解锁下一阶段。
- 内容阶段先确认重点，再确认章节与逐页大纲。
- 保存来源、检查依据、确认版本与变更记录；上游改动使相关下游阶段重新进入复查。
- 从任务目录恢复进度，避免只依赖聊天记忆。
- 在大纲与成稿阶段进行专项审查：逐页记录依据，重要问题处理并复查后再通过；输入变化使旧审查失效。

**流程脚本不直接生成 PPT，也不自动理解文档。** 阅读、内容判断与页面制作由助手及当前环境可用工具完成。制作 PPTX 需要另配演示文稿制作工具；结构检查通过不能证明内容准确、视觉质量优秀或已通过 PowerPoint 实机验证。

## 八阶段

| 阶段 | 主要产物 | 默认确认方式 |
|---|---|---|
| 1 明确任务 | 本次要求、范围与默认设置快照 | 用户确认 |
| 2 整理材料 | 来源目录、材料快照、缺口记录 | 助手检查 |
| 3 组织内容 | 重点分析 → 章节与逐页大纲 | 重点和大纲分别确认 |
| 4 确定视觉 | 视觉规范、代表页 | 用户确认 |
| 5 准备素材 | 图表、图片、数据与来源 | 助手检查 |
| 6 完整制作 | 演示稿、讲稿及制作记录 | 助手检查 |
| 7 检查修正 | 内容、视觉、结构与最终导出检查 | 助手检查 |
| 8 交付归档 | 交付包与版本说明 | 助手检查 |

`review_all=true` 可启用逐阶段用户确认。明确委托助手决定某阶段时，可记录授权；客观检查仍须完成。确认记录是可复查凭据，不是身份认证或不可篡改审计系统。

## 快速使用

运行环境：**Python 3.10+**，无第三方 Python 依赖。以下命令在克隆后的仓库根目录执行：

```sh
git clone https://github.com/JesseChen26/ppt-workflow.git
cd ppt-workflow
python scripts/workflow.py --help
python -m unittest discover -s scripts -p "test_*.py"
```

### 作为 Skill 使用

整个仓库根目录就是一个 Skill。可让技能安装器安装这个仓库，或者将其克隆到宿主支持的技能目录。以 Codex 当前官方文档的用户级目录为例：

```sh
git clone https://github.com/JesseChen26/ppt-workflow.git ~/.agents/skills/ppt-workflow
```

已有同名技能时，先比较版本和自定义设置，避免覆盖。项目级技能可放在 `.agents/skills/ppt-workflow`。不同宿主或旧版应用的扫描位置可能不同，以实际环境为准。参见 [官方技能文档](https://developers.openai.com/codex/skills#where-to-save-skills)。

在支持技能的助手中提出：

> 使用 ppt-workflow，把我提供的报告做成约 15 分钟的技术汇报。先分析材料并与我确认重点，再组织章节与逐页内容。任务文件保存到我指定的绝对路径。

### 直接使用命令行

工作目录必须是**新的或空的绝对目录**。Windows PowerShell 示例：

```powershell
$taskDir = Join-Path $PWD 'tasks/demo'
python scripts/workflow.py init --workspace "$taskDir" --title '技术汇报示例'
python scripts/workflow.py status --workspace "$taskDir"
```

macOS / Linux 示例：

```sh
python scripts/workflow.py init --workspace "$PWD/tasks/demo" --title '技术汇报示例'
python scripts/workflow.py status --workspace "$PWD/tasks/demo"
```

初始化只建立骨架，不代表任何阶段已完成。填写 `requirements.json` 和当前阶段的成果、附件登记及 `review.json` 后，再运行 `check`。默认审核阶段须展示具体成果并记录用户真实回复后才能 `complete`。

中断恢复使用 `resume`；要求变更使用 `revise --changes <JSON文件> --reason <原因>`。详细字段和命令见 [操作约定](references/operations.md)、[验收标准](references/stages.md) 与 [内容分析](references/content-analysis.md)。可复制 [示例要求](examples/technical-report-changes.json) 作为讨论起点，按实际任务修改。

## 默认设置与文件

大纲写好后、成稿检查时，可分别用 `review-context --stage 3` / `--stage 7` 取得当前版本的审查上下文，结合 `--workspace <任务绝对目录>` 使用。按 [逻辑与成稿审查](references/role-review.md) 填写现有 `review.json.assessment`；命令只提供上下文，不会代替实际审查。参考 [定向案例](examples/review-walkthrough.md)。

默认中文、16:9、可编辑 PPTX、开启讲稿；视觉模板初始为空。每次 `init` 都保存默认快照，修改 `defaults.json` 不会改变已有任务。

```text
SKILL.md              技能入口
defaults.json         默认设置
agents/openai.yaml    技能界面信息
scripts/              流程、内容检查及行为测试
references/           内容、视觉、验收与操作方法
examples/             通用要求示例
.github/workflows/    自动运行现有测试
```

真实材料和产物放在各自任务目录的 `files/` 并登记。建议将任务目录存放在仓库外；仓库已忽略 `tasks/`、`ppt_tasks/`、环境变量文件和 Python 缓存。

## 验证与范围

行为测试覆盖阶段顺序、重点确认、变更回退、来源与产物指纹、恢复和旧状态迁移等规则。测试中的最小 PPTX 是结构夹具，不是可展示的样稿，也不证明渲染兼容性。

本仓库发布通用工作流，不包含个人报告、内部培训课件、客户数据或专有演示文稿运行库。复现的是流程及记录结构；具体页面质量还取决于材料、制作工具与实际审阅。

## 参考与许可

方法受到 PPT Master 的阶段产物组织、[baoyu-skills](https://github.com/JimLiu/baoyu-skills) 的内容分析与逐页规划，以及 [gstack](https://github.com/garrytan/gstack) 的角色分工和证据化审查启发。对应文档保留来源与适配范围；本仓库没有捆绑这些项目的实现，也不依赖安装它们。

[MIT License](LICENSE)。维护者：[JesseChen26](https://github.com/JesseChen26)。[个人网站项目介绍](https://jessechen26.github.io/ppt-workflow.html)。
