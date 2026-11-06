# 操作约定

运行 `python <技能绝对路径>/scripts/workflow.py <命令> --workspace <任务绝对目录>`。参数见 `--help`。命令输出 JSON；失败退出码 2，不推进阶段。Python 3.10+ 标准库即可。

## 创建、恢复、开始

- `init --title <名称>`：仅接受新目录或空目录，建立八阶段骨架、默认快照、任务要求、状态和附件目录。
- `status` 或 `resume`：重新核对文件和需求，返回最早未完成阶段、问题与变更历史，不自动通过阶段。
- `begin --stage N`：仅开始最早未完成阶段；先填写实际成果，初始骨架不算完成。

阶段 3 有独立的重点检查点：`focus-report` 展示讨论稿，`check-focus` 检查内容，`approve-focus --message <用户原话> --source <出处>` 保存确认，`begin-outline` 解锁逐页大纲。具体材料目录与分析字段见 [内容分析](content-analysis.md)。重点确认与大纲确认是不同成果，分别记录。

## 检查与完成

填写阶段成果、`artifacts.json` 与 `review.json`。固定检查项不可删除或增改 ID；每项 `passed: true`，`evidence` 为实际依据，`summary` 为结论。`check --stage N` 核对所有必要成果。

默认阶段 1、3、4 需用户确认。展示成果，得到直接回复后记录：

```text
approve --stage 1 --message <用户实际回复> --source <可定位聊天消息或日期和上下文>
complete --stage 1
```

`approve` 记录当前成果指纹，不鉴定发言者身份，助手必须诚实引用。任何相关更改都使确认失效；已有明确授权可再次引用，但必须能覆盖当前变更，不得把旧确认默认用于新版本。自动阶段用 `complete`；它自己重跑检查，不能通过省略 `check` 绕过条件。

阶段3、7还需按 [专项审查](role-review.md) 填写 `review.json.assessment`。`review-context --stage 3|7` 返回输入指纹和空白审查模板，不自动判定通过。新任务启用此检查；旧任务已完成记录保持原状，重新 `begin` 相关阶段时启用。逐页覆盖不足、版本过期、重要问题未解决或缺少复查依据均会阻止 `check/approve/complete`。

确认记录应写明所覆盖的具体重点、大纲或视觉版本。用户要求开始/完成制作时，结合已展示成果判断授权范围；不要把笼统请求同时解释为对尚未展示的各项设计质量的认可。用户已明确授权的动作继续执行，不新增重复确认。

## 变更与回退

UTF-8 JSON 文件例如 `{"audience":"声学研究组","slide_count":12}`：

```text
revise --changes <JSON文件绝对路径> --reason <原因>
reopen --stage N --reason <扩大复查范围的原因>
```

程序保留成果与历史，重置相关阶段的检查项、清除确认。直接编辑成果后运行 `status` 也会回退。`reopen` 不能跳到未完成前置阶段之后。

用户明确改变审核偏好时：`set-review --stage N --mode user|agent --message <用户原话> --source <出处>`。只修改当前或后续阶段；已完成阶段先回退。该委托不取消文件和检查要求。

## 工作目录

```text
任务目录/
  defaults.snapshot.json   初始化时默认设置
  requirements.json       本次要求
  state.json              阶段、版本、确认与事件记录
  files/                  实际输入和成果附件
  stages/01-brief/ ... 08-delivery/
    对应阶段成果
    review.json
    artifacts.json
    focus/                 仅阶段3：analysis.json、review.json
```

`topic/audience/objective/duration_minutes/slide_count/source_scope` 初始未定；时长接受正数或 `not_applicable`。`template` 在阶段 4 前可为空，此阶段须填写模板标识/路径或 `free_design`。`source_notes/visual_notes` 保存补充要求。默认中文、16:9、可编辑 PPTX、开启讲稿；默认值可覆盖，没有真实视觉母版。

状态采用原子替换和短生命周期锁；同一任务不得多个操作同时写。异常中断遗留 `.workflow.lock` 时，先确认没有进程正在操作该任务，再删除锁恢复。不要手改 `state.json`。

程序管理流程，不生成页面、不联网。内容、视觉、兼容性和对象编辑能力仍需实际检查。`scripts/test_workflow.py` 在临时目录用最小结构文件验证规则，测试附件不是可交付演示稿。

当前状态版本 v2。旧版 v1 首次恢复时自动补充内容分析结构，并将材料及后续阶段标记为待复查；不会覆盖旧分析或大纲。升级后旧大纲若已填写，先按内容分析文档备份，清空当前大纲，确认新重点后再编排。

阶段指纹按该阶段负责的要求字段绑定；例如页数调整从阶段 3 重新验收，原阶段 1 对听众/目标等基础约定仍有效。如果修改同时改变了早期文档中的内容，文件检查会进一步将回退范围扩大到该文档所在阶段。

## 文件收尾

内容与设计记录沿用已有文件，源代码优先集中维护一个可复用入口，避免为推进状态临时堆叠脚本。构建过程可使用临时目录，交付时只保留需要恢复、修改和证明实际检查的产物；重复预览、中间导出和转换缓存不必永久归档。

清理前核对 `artifacts.json`、阶段指纹和脚本引用。注册为当前检查证据的预览或验证报告须保留，不能为减少文件数而使完成记录失效。未注册、无依赖的本次临时产物可在授权范围内收尾；涉及历史版本、用户材料或已经归档的旧任务时，先列出范围并遵从用户授权。不要以递归删除构建目录的方式处理含运行时目录链接的工作区。
