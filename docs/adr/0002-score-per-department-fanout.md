# Score 按 Department 分别计算，Graph 从 calculate_score 起按部门 fan-out

**Status:** accepted

ADR-0001 确定了 Opportunity 的颗粒度是"一个 Department"而不是整个 Event。§47 的评分模型里 `Organization Match`（20%）和 `Department Match`（15%）本质上是"跟这个具体部门匹配得好不好"，天然按部门变化。如果 `calculate_score` 仍然对整个 ExpertRun 只算一次，会导致同一次判断里的 LEAD 部门和低置信度的 SUPPORT 部门被套用同一个分数，一起被同等对待地推送或归档——这与"每个部门是独立商机"矛盾。

因此：`calculate_score` 改为对每个识别出的 Department 分别计算一次分数（`Event Relevance`/`Project Signal`/`Procurement Signal` 三项全部门共用同一个 event 级别值，`Organization Match`/`Department Match`/`Need Clarity`/`Company Capability` 用该部门自己的匹配度和挂载的 Needs）。Graph 从 `calculate_score` 开始，一路到 `should_push` → `resolve_owner` → `build_message` → `send_dingtalk`，按识别出的部门数量 fan-out（用 LangGraph 的 `Send` API，而不是单节点内部循环处理一个列表）——这样每个部门分支的重试（§71 RetryPolicy）和失败互不影响：某个部门推送失败重试，不会重发已经成功的其他部门。

## Consequences

- `expert_run`/`FinalResult` 顶层的 `score`/`level` 字段语义变成"本次 run 所有部门中的最高档"，仅用于列表排序/展示，不再是推送决策的直接依据——真正驱动推送的是每个 department 条目自己的 score/level（见 `CONTEXT.md` 的 Score Level 词条）。
- `push_record` 需要 `department_id` 字段（ADR-0001 已提出），用于把每条推送记录对应回具体的部门分支。
- `mini_review`（Reviewer）仍然是**一次全局审核**，不按部门 fan-out——它检查的是"是否存在虚构单位/部门/能力"这类跨部门的整体合理性，适合在 fan-out 之前统一做一遍。
