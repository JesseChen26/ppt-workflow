# 八阶段验收

每阶段都有 `review.json`（固定检查项、逐项依据、阶段结论）和 `artifacts.json`（附件）。初始化的空白内容不算完成；Markdown 中 `<!-- WORKFLOW_DRAFT -->` 在实际完成后删除。附件缺失或变化使已完成阶段和下游失效。

| 阶段 | 必要成果 | 检查项 ID 与完成标准 | 默认用户确认 |
|---|---|---|---|
| 1 明确任务 | `brief.md` 与 `requirements.json` | `requirements` 要求完整；`defaults` 默认与本次覆盖明确；`scope` 材料范围、模式和交付条件明确 | 是 |
| 2 整理材料 | `sources.md`、`sources.json`、注册的原始材料快照 | `provenance` 来源可定位；`coverage` 关键事实和素材有依据；`gaps` 缺口已有处理决定 | 否 |
| 3 组织内容 | `focus/analysis.json`、`focus/review.json`、重点确认、`outline.json` | 先按 [内容分析规则](content-analysis.md) 确认重点；再检查 `story` 章节/逐页推进与具体表达、`evidence` 来源和呈现方式、`coverage` 页数与重点覆盖 | 重点和大纲分别确认 |
| 4 确定视觉 | `visual.md` 与至少一份 `representative` 附件 | `template` 模板/自由设计及分职责的视觉规则；`readability` 代表页信息层级、图文关系和观看尺度；`editability` 对象编辑要求 | 是 |
| 5 准备素材 | `assets.md` 与所需素材附件 | `readiness` 素材就绪或说明无需素材的理由；`provenance` 来源与位置明确；`accuracy` 数据、公式、原图核对 | 否 |
| 6 完整制作 | `production.md`、`draft` 与 `source` 附件 | `roster` 页面与大纲对应；`editable` 必要对象可编辑；`notes` 备注符合要求 | 否 |
| 7 检查修正 | `qa.md` 与 `reviewed_deck` 附件 | `facts` 标题/结论与证据核对；`visual` 逐页检查焦点、证据可读性、布局适配与整稿节奏；`structure` 导出结构和页数核对；`editability` 对象编辑能力核对；`export_review` 检查最终导出文件 | 否 |
| 8 交付归档 | `delivery.md`、`final` 与 `source` 附件 | `version` 成稿与阶段7审阅文件一致；`package` 成稿和源文件可用；`handoff` 交付链接和使用限制明确 | 否 |

程序只证明文件存在、字段完整和版本一致等条件，不自动证明这些内容标准。视觉检查必须看实际渲染结果，不能从生成代码推断。

阶段3和7的 `review.json` 另含 `assessment`，记录实际审查者、当前输入指纹、逐页覆盖、问题及复查结果。新任务必填，旧任务重新进入相关阶段时启用。细则见 [逻辑与成稿审查](role-review.md)；它不增加新的阶段或用户确认点。

阶段3、4、7的人工设计与复核方法见 [内容表达与页面设计](design-method.md)。规则更新不会自动重评旧任务；恢复或改稿时按实际影响复查，不改写历史验收记录。

## 逐页大纲

`outline.json` 为数组，数量等于 `slide_count`，每项含以下字段。非证据页允许 `evidence: []`，人工检查防止关键结论漏引用。

```json
{
  "id": "p01",
  "title": "本页标题",
  "purpose": "在汇报中的作用",
  "message": "本页要让听众理解的主要事情",
  "content": "具体内容",
  "focus_ids": ["c01"],
  "evidence": ["sources.md 中的来源及页码/图号，或明确标注的假设"],
  "visual_priority": "must",
  "visual": "表达形式、具体来源图或数据，以及要强调的比较或局部",
  "layout": "视觉主体、辅助说明的位置和阅读顺序",
  "editable_requirements": "必须可编辑的对象",
  "speaker_notes": "讲解要点，不需要时说明原因"
}
```

`message`、`visual_priority`、`layout` 为本次方法更新要求人工填写的设计细节；现有程序允许扩展字段，但未自动强制校验它们。`chapter` 在有章节结构时填写。旧任务仅因方法文档更新不会自动失效，修改大纲时仍按原回退规则重新验收。

## 附件

文件在本任务 `files/` 下，清单用相对路径；禁止外部路径或把状态文件当证据。目录需展开到文件，公共字体/样式/生成脚本也在首次使用阶段注册。

```json
[{"role": "representative", "path": "files/representative.png"}]
```

阶段 6 `draft` 接受 PPTX/PDF，必须涵盖本次要求的格式。阶段 7 `reviewed_deck` 必须和阶段 6 草稿字节相同；阶段 8 `final` 与阶段 7 审阅文件字节相同，每种输出格式都需审阅交付。PPTX 页数从 XML 核对；PDF 页数人工检查。结构检查不等于在 PowerPoint 中打开测试。源文件可多份，交付源文件必须覆盖阶段 6 注册的所有 `source` 内容。

## 变更影响

主题/听众/目标/时长/材料范围/输出模式或格式/审核设置 → 阶段 1；来源补充说明 → 阶段 2；页数/语言 → 阶段 3；比例/模板/视觉说明 → 阶段 4；讲稿开关 → 阶段 6。

文件改动回到首次注册该文件的阶段；语义影响由助手判断，必要时 `reopen` 更早阶段。调整已完成阶段的检查记录也需要重新验收。
