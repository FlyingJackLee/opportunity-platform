# Opportunity Intelligence Platform

AI 商务机会发现与行业专家研判平台。自动发现可能影响客户业务建设的公开事件，通过行业专家 AI 快速研判商务价值，并将高价值机会推送给对应客户经理。

## Language

**Event**：
Collector 采集或人工录入的、经过标准化的一条公开信息单元（政策发布、招标公告等），是整条流水线的输入原子单位。
_Avoid_: Standard Event（仅指 Collector 输出该结构时的技术描述，指代对象与 Event 相同，不作为独立术语使用）

**Opportunity（商机）**：
不是独立持久化的实体，没有专属数据表，也不追踪"是否已跟进/已转化"等生命周期状态。最小颗粒度是"一个 Event 的 FinalResult 中，某一个被识别出的 Department（或未识别出部门时的整个 Organization）"——同一个 Event 只要识别出多个部门，就产生多条**互相独立**的 Opportunity，分别解析各自的 Customer Owner、各自成一条推送消息，即使解析出的 Customer Owner 是同一个人也不合并、不去重。
_Avoid_: 把 Opportunity 等同于一整个 Event（一个 Event 可能同时对应多条 Opportunity）；把 Opportunity 当作数据库里真实存在的一张表或一个有状态生命周期的对象。

**ExpertResult**：
`expert_judge` 节点的原始结构化输出（needs / organizations / departments / capabilities / stage / risks / recommended_action），代表 LLM 对"有没有机会、可能需要什么、谁牵头"的直接判断，尚未经过打分和审核。
_Avoid_: Opportunity Result（已废弃的早期草稿用词，指代对象与 ExpertResult/FinalResult 之一含混不清，不再使用）

**FinalResult**：
`finalize_result` 节点的输出，在 ExpertResult 基础上叠加了 Code 计算出的 `score`/`level`/`confidence` 以及 `summary`，是一次 ExpertRun 的最终、完整判断结果。**score/level/confidence 按每个 Department 分别计算并挂在各自的 department 条目上**（因为一个 Department 就是一条独立 Opportunity）；`FinalResult` 顶层的 `score`/`level`/`confidence` 是"分数最高的那一个 Department 分支的完整三元组"——三个字段来自**同一个**部门，不是三个字段分别独立取各自的最高值——只用于列表排序/展示，真正驱动某个部门是否推送、往哪推的是这个部门自己的 score/level/confidence。
_Avoid_: Expert Result（与打分/审核前的 ExpertResult 混淆时不要用这个说法指代最终结果）, Opportunity Result（已废弃）；把顶层 score/level/confidence 当成推送依据（实际依据是每个部门自己的三元组）；把顶层三元组理解成三个字段分别独立取最高（实际是同一部门的一组值）

**Need Maturity**：
每个 need（`ExpertResult.needs[]` 中的一项）的成熟度分类：`CONCEPT / POTENTIAL / EXPLICIT / PROJECT / PROCUREMENT`，由 `expert_judge` 节点（LLM）逐条判断，是唯一描述"这个具体需求发展到什么阶段"的字段。
_Avoid_: Opportunity Stage（曾设想的第二条"商机整体阶段"枚举，与 Need Maturity 语义重叠、且由 LLM 独立判断缺乏一致性保证，设计阶段已废弃，不再出现在 ExpertResult/FinalResult 中）

**Department（客户部门）**：
Organization 下的一个具体处室/科室，是 Expert Judge 判断"谁可能牵头"的对象。在 ExpertResult 中，每个被识别出的 Department 携带它相关的 Needs（而不是反过来由 Need 指向 Department），后续在 `finalize_result` 阶段还会携带它自己独立计算出的 Score/Level——一条 Opportunity 本质上就是"一个 Department + 它相关的 Needs + 它自己的 Score/Level"这个组合。

**Customer Owner（客户经理）**：
`customer_owner` 表中的一条记录，代表我方内部负责跟进某个客户单位（Organization）或客户单位下某个部门（Department）关系的商务/客户经理。**不是**客户单位内部的联系人或牵头人——一期不追踪客户单位内部具体是谁在牵头（对应"一期不建的表"里的"联系人关系图谱"）。一个 Department 最多解析出一个 Customer Owner。
_Avoid_: 部门负责人 / 组织负责人（容易被误解为客户单位内部的人；实际指的是我方指派负责该客户关系的 Customer Owner）

**Industry / Region Tag**：
`event`/`organization`/`knowledge_chunk`/`collector_source` 等表里的 `industry`/`region` 字段必须取自一份受控词表（一期以代码常量/枚举维护，不必建数据库表），而不是自由文本，保证跨表打标能精确匹配（避免"重庆"/"重庆市"/"渝"互相匹配不上）。

**Score Level**：
`FinalResult` 中每个 Department 各自的分档：`A(≥80) / B(65~79) / C(50~64) / WATCH(<50)`，由 Code 针对该部门单独按加权总分（§47 评分模型）计算——`Organization Match`/`Department Match` 用该部门自身的匹配置信度，`Need Clarity`/`Company Capability` 用挂在该部门下的 related Needs/related Capabilities，`Event Relevance`/`Project Signal`/`Procurement Signal` 全部门共用同一个 event 级别的值。驱动**该部门自己**的 `should_push` 决策；`expert_run`/`FinalResult` 顶层保留的 score/level（连同 confidence）是所有部门里分数最高那一个的完整三元组，仅用于列表排序展示。
_Avoid_: 不要与 Need Maturity 混淆——Level 是分数分档，不代表需求发展到什么阶段；不要把顶层汇总 level 当成某个具体部门的推送依据；不要把顶层三元组理解成三个字段分别独立取最高。
