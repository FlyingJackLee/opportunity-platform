# Opportunity 不作为独立持久化实体

**Status:** accepted

一期的核心业务概念"商机"（Opportunity）不建独立数据表，也不设置跟进/转化等生命周期状态。它是 `Event` 最新一次 `ExpertRun` 产出的 `FinalResult` 中，某一个被识别出的 Department（或未识别出部门时的整个 Organization）——一旦该 Department/Organization 解析出的路由达到推送条件，这个组合就被称为一条 Opportunity。**一个 Event 可能同时产生多条 Opportunity**（识别出几个部门就有几条），各自独立解析 Customer Owner、独立推送，互不合并。选择不建独立实体是为了避免一期就构建轻量 CRM 式的商机跟踪能力（spec §103 明确排除"自动CRM"、"复杂销售流程"），把复杂度留到验证"发现-判断-推送"这条核心链路的价值之后再决定是否需要。

## Consequences

后续如果需要跟踪商机的人工处理状态（如"已联系"/"已转化"/"已作废"），需要新增一张独立的 `opportunity` 表（或等价结构）来承载这个状态，不能简单往 `event` 或 `expert_run` 上加字段——因为一个 `event` 可能对应多次 `expert_run`（见 reanalyze 流程），状态需要挂在"某次被推送的判断结果"这个层级，而不是挂在 Event 或 ExpertRun 本身。
