# Push 链路的第二次 fan-out 不能汇聚到共享节点

**Status:** accepted

ADR-0002 定下"Graph 从 calculate_score 开始按部门 fan-out"，Phase 4 把这条链路延伸到 `should_push → resolve_owner → build_message → send_dingtalk`。最初的设计想让所有部门分支最后汇聚到一个共享的 `archive` 节点上统一写 `Event.status`（跟 `calculate_score → finalize_result` 目前的写法一样）。这个设计在实现前用一个脚本对着实际装的 `langgraph==1.2.11` 验证过，结果是**错的**：`should_push=NO` 的分支两跳就能到 `archive`，`should_push=YES` 的分支要经过 `resolve_owner`/`build_message`/`send_dingtalk` 四跳才到——LangGraph 会在每一个"到达波次"都执行一次共享节点，而不是等所有分支都到齐了才执行一次。按最初设计实现的话，`archive` 会被跑两次，第一次看到的部门列表还是不完整的，`Event.status`/`push_record` 会基于不完整数据被写一遍。

最终采用：`archive` 不做共享汇聚，改成跟 `calculate_score` 完全一样的模式——每个部门分支各自通过 `Send("archive", payload)` 各跑一份独立的 `archive` 实例，各自写自己那一条 `push_record`；`Event.status` 的更新改成数据库层面的条件 UPDATE（推送成功无条件写 PUSHED，未推送/失败只在当前状态不是 PUSHED 时才降级成 ARCHIVED），不依赖图状态里的跨分支聚合。

## Consequences

以后任何"多个 Send 分支要汇聚到同一个终点节点"的场景，都不能默认"共享节点 = 等所有分支到齐再跑一次"——只有当所有并行分支到达该节点所需的跳数完全相同时，共享汇聚才是安全的；跳数不同就必须让终点节点本身也是 Send 分发的独立分支（不等待兄弟分支），配合数据库层面的幂等/条件写入来聚合最终结果。这条经验对后续任何类似的多阶段 fan-out 设计都适用，不只是这一次的 push 链路。
