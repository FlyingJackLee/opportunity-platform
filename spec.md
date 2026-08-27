# AI 商务机会发现与行业专家研判平台一期技术规格说明书
**版本：V1.0**  
**技术路线：Python + FastAPI + LangGraph + RAG + PostgreSQL/pgvector + 钉钉**  
**建设阶段：一期 MVP / 试运行版本**

---

# 1. 项目概述

## 1.1 项目名称

**AI 商务机会发现与行业专家研判平台**

英文内部名称：

**Opportunity Intelligence Platform**

一期核心目标：

> 自动发现可能影响客户业务建设的公开事件，通过行业专家 AI 对事件进行快速商务研判，并将高价值机会自动推送给对应客户经理。

---

# 2. 一期核心目标

一期不建设完整 CRM、不建设大型多 Agent 平台、不建设复杂知识图谱。

一期只解决三个核心问题：

```text
1. 发生了什么？
2. 这件事有没有商务机会？
3. 应该让谁知道？
```

形成最小完整闭环：

```text
公开信息
     │
     │ 定时采集
     ▼
Collector
     │
     │ Standard Event
     ▼
Expert Engine
     │
     │ Opportunity Result
     ▼
Push Decision
     │
     ▼
钉钉
     │
     ▼
客户经理
```

同时支持：

```text
人工录入事件
     │
     └────────→ Expert Engine
```

---

# 3. 一期系统范围

一期分为三大核心模块：

```text
┌────────────────────────────┐
│     Collector Module       │
│                            │
│ 公开数据采集 / 去重 / 初筛 │
└─────────────┬──────────────┘
              │
              │ Event
              ▼
┌────────────────────────────┐
│       Expert Engine        │
│                            │
│ 事件理解 / RAG / 专家研判  │
│ 评分 / Reviewer            │
└─────────────┬──────────────┘
              │
              │ Expert Result
              ▼
┌────────────────────────────┐
│      Delivery Module       │
│                            │
│ Push Decision / Owner      │
│ Routing / DingTalk         │
└────────────────────────────┘
```

其中三个模块可以先部署在**同一个代码仓库、同一个服务体系**内，不要求一期拆成三个微服务。

---

# 4. 技术选型

## 4.1 核心技术栈

| 层级 | 技术 |
|---|---|
| 开发语言 | Python 3.12+ |
| API | FastAPI |
| Agent编排 | LangGraph |
| ORM | SQLAlchemy 2.x |
| 数据库 | PostgreSQL |
| 向量检索 | pgvector |
| 缓存 | Redis |
| 定时任务 | APScheduler |
| HTTP | httpx |
| 页面抓取 | BeautifulSoup / lxml |
| JS动态页面 | Playwright |
| LLM | 统一 LLM Gateway |
| Embedding | 可配置 |
| 文件存储 | MinIO，可选 |
| 消息渠道 | 钉钉企业机器人 / OpenAPI |
| 容器 | Docker |
| 部署 | Docker Compose 一期即可 |

LangGraph 当前官方提供 StateGraph、节点级 RetryPolicy、持久化 checkpoint、interrupt/Command 等机制，适合后续扩展人工审核、异常恢复和复杂条件路由。

钉钉开放平台当前提供企业机器人群消息和单聊消息等能力，可作为一期主要商务信息触达渠道。

---

# 5. 总体技术架构

```text
                 ┌─────────────────────┐
                 │     Public Web      │
                 │                     │
                 │ 政府网/行业网/招标网│
                 └──────────┬──────────┘
                            │
                            ▼
                ┌──────────────────────┐
                │   Collector Module   │
                │                      │
                │ Scheduler            │
                │ Crawler              │
                │ Parser               │
                │ Dedup                │
                │ Filter               │
                └──────────┬───────────┘
                           │
                           │ Standard Event
                           ▼
                 ┌─────────────────────┐
人工事件 ───────→│     LangGraph       │
                 │    Expert Graph     │
                 └──────────┬──────────┘
                            │
          ┌─────────────────┼───────────────────┐
          │                 │                   │
          ▼                 ▼                   ▼
      Industry RAG      Organization       Capability RAG
                           Data
          │                 │                   │
          └─────────────────┼───────────────────┘
                            ▼
                      Expert Judge
                            │
                            ▼
                         Review
                            │
                            ▼
                    Opportunity Result
                            │
                            ▼
                   Push Decision Node
                            │
                            ▼
                   Owner Routing Node
                            │
                  ┌─────────┴────────┐
                  ▼                  ▼
              客户经理              公共群
                  │                  │
                  └───────钉钉───────┘
```

---

# 6. 核心业务流程

主流程：

```text
START
  │
  ▼
receive_event
  │
  ▼
analyze_event
  │
  ▼
retrieve_context
  │
  ▼
expert_judge
  │
  ▼
calculate_score
  │
  ▼
mini_review
  │
  ▼
finalize_result
  │
  ▼
should_push
  │
  ├── NO ──→ archive ──→ END
  │
  └── YES
       │
       ▼
  resolve_owner
       │
       ▼
  send_dingtalk
       │
       ▼
      END
```

---

# 7. 系统一：Collector Module

## 7.1 目标

Collector 不负责深度商务判断。

它只负责：

> **将互联网中值得关注的信息转换成统一 Event。**

---

# 8. Collector 数据来源

一期支持：

### 自动来源

- 政府门户
- 委办局网站
- 发改委
- 经信委
- 住建部门
- 数据部门
- 国资部门
- 公共资源交易网站
- 行业协会
- 指定新闻源

### 人工来源

- 手工输入文字
- 输入 URL
- 粘贴政策
- 粘贴客户反馈
- 手工创建 Event

---

# 9. Source 配置

数据库：

```text
collector_source
```

字段：

```text
id
name

source_type

base_url

list_url

enabled

schedule

parser_type

industry_tags

region_tags

priority

created_at
updated_at
```

示例：

```json
{
  "name": "XX市住建委政策发布",
  "source_type": "GOV_WEB",
  "list_url": "...",
  "schedule": "0 */2 * * *",
  "industry_tags": ["住建"],
  "region_tags": ["XX市"]
}
```

---

# 10. 定时采集

一期：

```text
APScheduler
```

适用于少量固定数据源。

建议：

```text
10～100个数据源
```

如果后期达到：

```text
500+
```

再升级：

```text
Celery Beat
+
Celery Worker
```

一期不要提前引入复杂任务基础设施。

---

# 11. Crawler

根据站点类型支持：

```text
StaticCrawler
APICollector
RSSCollector
DynamicCrawler
```

StaticCrawler：

```text
httpx
+
BeautifulSoup
```

DynamicCrawler：

```text
Playwright
```

原则：

> 非必要不使用浏览器爬虫。

---

# 12. 内容解析

Crawler 最终提取：

```text
title
content
published_at
source
url
attachments
```

所有站点 Parser 与 Collector 解耦。

例如：

```text
collectors/
├── gov_generic.py
├── tender.py
├── rss.py
└── custom/
```

---

# 13. Event Dedup

防止同一政策被多个网站转载后重复研判。

Dedup 分三层：

### URL

```text
url_hash
```

### 文本

```text
content_hash
```

### Semantic Dedup

可选：

```text
title_embedding similarity
```

一期优先：

```text
URL + title normalization + content hash
```

---

# 14. Filter

Collector 内设置轻量 Filter。

目标：

```text
100条信息
↓
10～30条进入Expert
```

---

# 15. Filter 第一层：规则

关键词配置：

```text
event_filter_rule
```

示例：

```text
AI
人工智能
平台
建设
数据治理
数字化
试点
实施方案
专项资金
采购
招标
升级
改造
```

支持：

```text
include keywords
exclude keywords
source priority
region
industry
```

---

# 16. Filter 第二层：Small LLM

规则筛选之后，可以使用低成本模型判断：

```text
这条事件是否可能与政企信息化、数字化、
AI、数据、平台建设产生商务机会？
```

Structured Output：

```json
{
  "relevant": true,
  "confidence": 0.82,
  "reason": "..."
}
```

过滤阈值：

```text
confidence >= 0.6
→ Expert
```

阈值后台配置。

---

# 17. Standard Event

Collector 唯一核心输出：

```json
{
  "event_id": "EVT-20260827-001",

  "source_type": "PUBLIC_WEB",

  "title": "...",

  "content": "...",

  "source_name": "...",

  "source_url": "...",

  "published_at": "...",

  "collected_at": "...",

  "region_hint": "...",

  "industry_hint": "...",

  "metadata": {}
}
```

---

# 18. Event 状态

```text
NEW

FILTERED_OUT

WAITING_ANALYSIS

ANALYZING

ANALYZED

PUSHED

ARCHIVED

FAILED
```

---

# 19. Event 表

```text
event
```

字段：

```text
id

external_id

title
content

source_type
source_name
source_url

published_at
collected_at

region

industry

status

content_hash

filter_score

created_at
updated_at
```

---

# 20. 手工 Event API

```http
POST /api/v1/events
```

Request：

```json
{
  "title": "...",
  "content": "...",
  "source_type": "MANUAL",
  "region": "重庆"
}
```

---

# 21. Collector API

手工触发：

```http
POST /api/v1/collectors/{id}/run
```

查看：

```http
GET /api/v1/collectors
```

---

# 22. 系统二：Expert Engine

Expert Engine 一期的目标：

> 根据 Event 和有限专家知识快速给出商务判断。

不进行复杂 autonomous research。

---

# 23. Expert Engine 核心 Graph

```text
START
  │
  ▼
analyze_event          LLM
  │
  ▼
retrieve_context       RAG / SQL
  │
  ▼
expert_judge           LLM
  │
  ▼
calculate_score        CODE
  │
  ▼
mini_review            LLM
  │
  ▼
finalize_result        CODE
  │
  ▼
END
```

---

# 24. Expert State

```python
class ExpertState(TypedDict):
    run_id: str

    event: dict

    event_analysis: dict

    industry_context: list

    organization_context: list

    capability_context: list

    expert_result: dict

    score: float

    level: str

    review: dict

    final_result: dict
```

State 保持精简。

禁止直接保存大量原文 chunk。

---

# 25. Node 1：Analyze Event

使用：

```text
LLM Structured Output
```

目标：

> 理解事件，而不是进行商务判断。

---

# 26. Event Analysis Schema

```json
{
  "event_type": "POLICY",

  "region": "XX市",

  "industry": [
    "住建"
  ],

  "topics": [
    "城市生命线"
  ],

  "tasks": [
    "建设基础设施风险监测能力"
  ],

  "objects": [
    "燃气",
    "桥梁",
    "供水"
  ],

  "signals": {
    "project_signal": "MEDIUM",
    "budget_signal": "UNKNOWN",
    "procurement_signal": "UNKNOWN"
  }
}
```

---

# 27. Analyze Prompt 原则

必须约束：

```text
只分析事件原文明确表达的内容。

不得：
- 判断客户
- 推荐部门
- 推测公司能力
- 将政策目标视为采购需求
```

---

# 28. Node 2：Retrieve Context

核心：

```text
三类知识
```

分别为：

```text
Industry Knowledge

Organization Knowledge

Company Capability
```

---

# 29. Industry Knowledge

回答：

> 这件事情在这个行业里通常意味着什么？

包含：

```text
业务主题
常见建设需求
常见建设内容
常见客户类型
典型职责关系
行业规则
容易误判点
```

---

# 30. Industry Knowledge 示例

```text
主题：
城市生命线

典型业务：
燃气
供水
桥梁
地下管网

常见需求：
物联感知
风险监测
风险预警
数据治理
综合监管

判断原则：
业务建设优先寻找业务主管部门；
存在数字化建设不代表科技信息部门必然牵头。
```

---

# 31. Organization Knowledge

回答：

> 具体应该找谁？

一期使用：

```text
PostgreSQL
+
可选 pgvector
```

结构化数据优先。

---

# 32. Organization 表

```text
organization
```

字段：

```text
id

name
short_name

region

organization_type

parent_id

description

source_url

status
```

---

# 33. Department 表

```text
department
```

字段：

```text
id

organization_id

name

responsibility

topic_tags

role_hint

source_url

status
```

---

# 34. Company Capability Knowledge

回答：

> 我们能做什么？

包含：

```text
Capability
Solution
Case
```

一期可以主要通过 RAG。

---

# 35. Capability 结构

```json
{
  "name": "数据治理",

  "scenarios": [
    "多源数据汇聚",
    "数据标准",
    "数据质量"
  ],

  "industries": [],

  "solutions": [],

  "cases": []
}
```

---

# 36. RAG

一期采用：

```text
PostgreSQL
+
pgvector
```

不引入：

```text
Milvus
Neo4j
Elasticsearch/OpenSearch
```

除非实际数据量证明需要。

---

# 37. Knowledge Chunk

字段：

```text
id

knowledge_type

title

content

industry

region

topic

embedding

metadata

status
```

---

# 38. RAG Query

根据 Event Analysis 生成：

```text
industry
topics
tasks
region
```

例如：

```text
城市生命线
风险监测
住建
XX市
```

---

# 39. Retrieval TopK

一期默认：

```text
Industry = Top 5

Capability = Top 5
```

Organization 先 SQL candidate filter，再视需要做向量匹配。

---

# 40. Node 3：Expert Judge

这是整个系统最核心 LLM Node。

输入：

```text
Event Analysis
+
Industry Knowledge
+
Organization Candidates
+
Company Capabilities
```

---

# 41. Expert Judge 目标

回答：

```text
有没有机会？

可能需要什么？

哪些单位？

哪些部门？

谁可能牵头？

我们能提供什么？

下一步做什么？
```

---

# 42. 强约束

Expert Judge 必须遵守：

```text
不得创建不存在于候选列表的部门。

不得创建不存在于公司能力库的能力。

不得将 POTENTIAL Need 说成明确项目。

不得将 Policy Signal 直接判断为 Procurement。

信息不足时允许 UNKNOWN。
```

---

# 43. Expert Judge Output

```json
{
  "needs": [
    {
      "name": "风险监测预警",
      "confidence": 0.90,
      "maturity": "EXPLICIT"
    }
  ],

  "organizations": [
    {
      "organization_id": "ORG001",
      "score": 0.91
    }
  ],

  "departments": [
    {
      "department_id": "DEP001",
      "role": "LEAD",
      "confidence": 0.84
    }
  ],

  "capabilities": [
    {
      "capability": "AI风险预警",
      "score": 0.88
    }
  ],

  "stage": "EARLY_OPPORTUNITY",

  "reason": "...",

  "risks": [],

  "recommended_action": "..."
}
```

---

# 44. Need Maturity

统一：

```text
CONCEPT

POTENTIAL

EXPLICIT

PROJECT

PROCUREMENT
```

---

# 45. 商机阶段

统一：

```text
WATCH

LEAD

EARLY_OPPORTUNITY

PROJECT

PROCUREMENT
```

---

# 46. Node 4：Calculate Score

禁止 LLM 直接输出最终商务分。

使用 Python。

---

# 47. 一期评分模型

```text
Event Relevance         15%

Need Clarity            20%

Organization Match      20%

Department Match        15%

Company Capability      20%

Project Signal          5%

Procurement Signal      5%
```

---

# 48. Score

```text
A ≥ 80

B = 65～79

C = 50～64

WATCH < 50
```

权重配置数据库化。

---

# 49. Score 与 Confidence

必须区分：

```text
Score
=
机会价值

Confidence
=
判断可靠性
```

可能存在：

```text
Score = 90

Confidence = 0.55
```

意义：

> 如果判断成立，价值很高，但目前信息不足。

---

# 50. Node 5：Mini Reviewer

一期不做复杂 Reviewer Loop。

只做一次轻量 Review。

---

# 51. Reviewer 检查

只检查：

```text
是否把潜在需求说成明确采购？

是否出现不存在的单位/部门？

是否出现公司不存在的能力？

部门职责解释是否合理？

是否存在明显过度判断？
```

---

# 52. Reviewer Output

```json
{
  "approved": true,

  "adjustments": [],

  "risk_note": "暂无明确采购依据"
}
```

---

# 53. Reviewer 不通过

一期：

```text
不重新进入复杂Research
```

只执行：

```text
降低置信度
+
增加风险提示
```

未来二期可扩展：

```text
Reviewer
→ Research Again
```

LangGraph 的条件边、持久化及 retry 能力可为该升级路径提供基础。

---

# 54. Final Result

统一：

```json
{
  "event_id": "...",

  "score": 82,

  "level": "A",

  "confidence": 0.81,

  "stage": "EARLY_OPPORTUNITY",

  "summary": "...",

  "needs": [],

  "organizations": [],

  "departments": [],

  "capabilities": [],

  "risks": [],

  "recommended_action": "..."
}
```

---

# 55. Expert Run

每次执行生成：

```text
expert_run
```

字段：

```text
id

event_id

graph_version

model_version

prompt_version

started_at

completed_at

status

score

level

confidence

result_json

error
```

---

# 56. 系统三：Delivery Module

Delivery 不需要一期独立成复杂系统。

定义为：

> LangGraph 后半段的确定性业务节点。

---

# 57. Delivery Graph

```text
Expert Result
     │
     ▼
should_push
     │
     ├── NO → archive
     │
     └── YES
           │
           ▼
      resolve_owner
           │
           ▼
      build_message
           │
           ▼
      send_dingtalk
```

---

# 58. Should Push

代码判断：

```text
A
→ Push Immediately

B
→ Push

C
→ 可配置Push / Digest

WATCH
→ Archive
```

一期默认：

```text
A / B
→ Push

C / WATCH
→ Archive
```

---

# 59. Customer Owner

一期只维护一张非常轻量的映射表：

```text
customer_owner
```

字段：

```text
id

organization_id

department_id nullable

owner_name

owner_user_id

dingtalk_user_id

enabled
```

---

# 60. Owner Routing

优先级：

```text
Department Owner
       ↓
Organization Owner
       ↓
Default Business Group
```

一期不做：

```text
区域经理
行业负责人
复杂多级审批
```

减少复杂度。

---

# 61. 示例

数据库：

```text
某市住建委
→ 张三

某市住建委 / 科技处
→ 李四
```

Expert：

```text
某市住建委
城建处
```

城建处没有单独负责人。

则：

```text
Organization Owner
→ 张三
```

---

# 62. Owner 不存在

Fallback：

```text
公共商机群
```

同时钉钉消息显示：

```text
【暂未配置客户负责人】
```

管理员后续处理。

---

# 63. 钉钉集成

一期优先采用：

```text
企业机器人
```

支持：

```text
群消息
单聊消息
```

钉钉开放平台当前明确提供企业机器人发送群消息与单聊消息等能力。

---

# 64. 钉钉消息模板

```text
🔥 AI发现A级商务机会｜82分

【事件】
XX市发布城市生命线安全工程实施意见

【AI判断】
政策已明确提出基础设施风险监测相关建设任务，
存在较强前置数字化建设机会。

【重点单位】
XX市住建委

【建议部门】
城建处｜可能业务牵头
科技信息处｜可能技术协同

【潜在需求】
• 风险监测预警
• IoT感知接入
• 基础设施数据治理

【我方切入】
• AI风险预警
• 数据治理
• IoT平台

【当前风险】
暂无明确采购及预算信息。

【建议动作】
建议近期联系相关业务部门确认年度建设计划。

【原始信息】
查看原文
```

---

# 65. 消息长度

钉钉正文保持：

```text
200～600字
```

完整 Expert Result 不全部推送。

未来可以增加：

```text
查看详情
```

跳转 Web 页面。

一期可以直接：

```text
原文URL
```

---

# 66. Push Record

```text
push_record
```

字段：

```text
id

event_id

expert_run_id

channel

recipient_type

recipient_id

owner_id

status

message

sent_at

error
```

---

# 67. LangGraph 主 State

最终完整 State：

```python
class OpportunityState(TypedDict):
    run_id: str

    event: dict

    event_analysis: dict

    industry_context: list
    organization_context: list
    capability_context: list

    expert_result: dict

    score: float
    level: str
    confidence: float

    review_result: dict

    should_push: bool

    owner: dict | None

    push_result: dict | None

    error: str | None
```

---

# 68. LangGraph 节点定义

一期正式节点：

```text
initialize

analyze_event

retrieve_industry

retrieve_organization

retrieve_capability

expert_judge

calculate_score

mini_review

finalize_result

should_push

resolve_owner

build_message

send_dingtalk

archive
```

---

# 69. Graph 结构

建议：

```text
START
 ↓
initialize
 ↓
analyze_event
 ↓
retrieve_context
 ↓
expert_judge
 ↓
calculate_score
 ↓
mini_review
 ↓
finalize_result
 ↓
should_push
 ├ NO → archive → END
 │
 └ YES
      ↓
 resolve_owner
      ↓
 build_message
      ↓
 send_dingtalk
      ↓
     END
```

---

# 70. Retrieval 是否并行

一期可以：

```text
retrieve_industry
retrieve_organization
retrieve_capability
```

并行执行。

后续 Merge：

```text
retrieve_context
```

也可以一期先串行，优先保证开发简单。

---

# 71. Retry Policy

以下节点设置 LangGraph 技术重试：

```text
analyze_event

retrieve_context

expert_judge

mini_review

send_dingtalk
```

推荐：

```text
max_attempts = 3
```

只处理：

```text
Timeout
Connection Error
HTTP 5xx
LLM transient errors
```

LangGraph 当前支持节点级 RetryPolicy。

---

# 72. 业务错误不 Retry

例如：

```text
找不到客户经理
```

不是错误。

执行：

```text
fallback public group
```

例如：

```text
找不到部门
```

不是错误。

输出：

```text
department = UNKNOWN
```

---

# 73. Persistence

一期即建议：

```text
PostgreSQL-backed Checkpointer
```

用于：

- 运行状态
- 故障恢复
- 后续人工 interrupt
- debugging

LangGraph persistence 会在执行节点之间保存 checkpoint，并用于 fault tolerance 与人工介入流程。

---

# 74. Human-in-the-loop

一期暂不必须在主流程启用。

但 Graph 预留：

```text
human_review
```

未来：

```text
Confidence低
+
Score高
→ interrupt
```

要求行业专家确认。

LangGraph 的 `interrupt()` 可以暂停图并通过 `Command(resume=...)` 恢复运行，因此后续无需重构主执行模型。

---

# 75. LLM Gateway

任何 Node 不直接依赖某模型厂商。

设计：

```python
class LLMGateway:
    async def structured_generate(task_type, prompt, schema): ...

    async def embed(texts): ...
```

---

# 76. Model Profile

```text
model_profile
```

示例：

```json
{
  "task": "EVENT_ANALYZE",
  "provider": "...",
  "model": "...",
  "temperature": 0.1
}
```

---

# 77. 模型使用策略

```text
Filter
→ 低成本模型

Event Analyzer
→ 中等模型

Expert Judge
→ 高能力模型

Reviewer
→ 高能力模型 / 中等模型

Embedding
→ 独立Embedding模型
```

---

# 78. Prompt 管理

Prompt 不写死在 Node 中。

表：

```text
prompt_template
```

字段：

```text
id

name

task_type

version

content

enabled

created_at
```

---

# 79. Prompt 版本

每次 Run 必须记录：

```text
event_prompt_version

judge_prompt_version

review_prompt_version
```

方便回归测试。

---

# 80. 一期数据库核心表

```text
collector_source

event

organization

department

customer_owner

knowledge_chunk

capability

expert_run

prompt_template

score_config

push_record
```

这 10 张核心表基本足够一期。

---

# 81. 一期不建的表

暂不需要：

```text
复杂CRM

联系人关系图谱

知识图谱

Expert Knowledge Candidate

复杂Case Memory

多层客户组织关系

销售漏斗
```

---

# 82. API 设计

## Event 创建

```http
POST /api/v1/events
```

---

## Event 分析

```http
POST /api/v1/events/{event_id}/analyze
```

---

## Run 查询

```http
GET /api/v1/runs/{run_id}
```

---

## Event 查询

```http
GET /api/v1/events
```

---

## 手工重新分析

```http
POST /api/v1/events/{event_id}/reanalyze
```

---

## Collector

```http
GET /api/v1/collectors

POST /api/v1/collectors/{id}/run
```

---

## Owner

```http
GET /api/v1/customer-owners

POST /api/v1/customer-owners
```

---

## Knowledge

```http
POST /api/v1/knowledge

GET /api/v1/knowledge/search
```

---

# 83. 异步执行

`analyze` 不建议同步等 LLM 完成。

请求：

```http
POST /events/{id}/analyze
```

返回：

```json
{
  "run_id": "...",
  "status": "PROCESSING"
}
```

后端执行 Graph。

---

# 84. 一期任务队列

如果并发很低：

```text
FastAPI BackgroundTasks
```

即可 PoC。

正式试运行建议：

```text
Redis Queue / Celery
```

但不要与 LangGraph 混淆。

任务队列负责：

> 哪个 Graph 什么时候运行。

LangGraph负责：

> Graph内部怎么运行。

---

# 85. 错误类型

统一：

```text
COLLECT_ERROR

PARSE_ERROR

FILTER_ERROR

LLM_ERROR

RAG_ERROR

STRUCTURED_OUTPUT_ERROR

PUSH_ERROR

UNKNOWN
```

---

# 86. Structured Output

所有 LLM 核心输出必须使用：

```text
Pydantic
```

例如：

```python
class ExpertResult(BaseModel):
    needs: list[Need]
    organizations: list[OrganizationResult]
    departments: list[DepartmentResult]
    capabilities: list[CapabilityResult]
    stage: OpportunityStage
    risks: list[str]
    recommended_action: str
```

---

# 87. 日志

至少：

```text
timestamp

run_id

event_id

node

duration

status

model

token_usage

error
```

---

# 88. LLM 成本

每个 Run 记录：

```text
input_tokens

output_tokens

model

estimated_cost
```

后续可以分析：

```text
每产生一个A级商机花多少钱。
```

---

# 89. 安全

内部知识必须区分：

```text
PUBLIC

INTERNAL
```

一期公司能力可以：

```text
INTERNAL
```

但不得把联系人、内部敏感商务数据发送给无授权外部模型。

---

# 90. Secrets

以下不得写入代码：

```text
LLM API KEY

DingTalk Secret

Database Password

Webhook Secret
```

统一：

```text
.env
+
Secret Manager
```

生产环境建议使用正式 Secret 管理。

---

# 91. Collector 合规要求

只抓取：

```text
合法公开信息
```

遵循：

```text
访问频率限制

站点公开访问规则

接口调用限制
```

一期避免高频攻击式爬取。

---

# 92. 性能指标

一期目标：

### Collector

```text
单站任务失败不影响其他站点
```

### Expert

普通 Event：

```text
P95 < 60秒
```

目标：

```text
20～40秒
```

### Push

Expert 完成后：

```text
< 10秒
```

完成消息推送。

---

# 93. 业务指标

一期最重要：

```text
有效事件进入Expert比例

Expert商机命中率

高价值消息人工认可率

单位判断准确率

部门判断准确率

公司能力匹配准确率
```

---

# 94. 一期不要设置过高 AI 指标

冷启动阶段建议重点人工统计：

```text
Top3单位合理率

Top3部门合理率

潜在需求合理率

推送有价值比例
```

上线后再逐渐形成 Benchmark。

---

# 95. 开发目录

```text
opportunity-platform/

├── app/
│
│   ├── api/
│   │   ├── events.py
│   │   ├── collectors.py
│   │   ├── runs.py
│   │   ├── knowledge.py
│   │   └── owners.py
│   │
│   ├── collector/
│   │   ├── scheduler.py
│   │   ├── crawler.py
│   │   ├── parser.py
│   │   ├── dedup.py
│   │   └── filter.py
│   │
│   ├── graph/
│   │   ├── graph.py
│   │   ├── state.py
│   │   ├── routing.py
│   │   └── checkpoint.py
│   │
│   ├── nodes/
│   │   ├── initialize.py
│   │   ├── analyze_event.py
│   │   ├── retrieve_context.py
│   │   ├── expert_judge.py
│   │   ├── scoring.py
│   │   ├── review.py
│   │   ├── push_decision.py
│   │   ├── owner_routing.py
│   │   └── dingtalk.py
│   │
│   ├── knowledge/
│   │   ├── retriever.py
│   │   ├── ingestion.py
│   │   └── embedding.py
│   │
│   ├── llm/
│   │   ├── gateway.py
│   │   └── providers/
│   │
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   └── core/
│
├── migrations/
├── tests/
├── scripts/
├── deploy/
└── docs/
```

---

# 96. 开发阶段

## Phase 1：基础工程

完成：

```text
FastAPI

PostgreSQL

Alembic

LLM Gateway

LangGraph State

Logging
```

验收：

```text
手工输入 Event
→ Graph正常执行
```

---

# 97. Phase 2：Expert MVP

完成：

```text
Analyze Event

Industry RAG

Organization Query

Capability RAG

Expert Judge

Score

Mini Reviewer
```

验收：

```text
Event
→
结构化商务研判结果
```

这是一期最核心里程碑。

---

# 98. Phase 3：Collector

完成：

```text
Source配置

Scheduler

Static Crawler

Parser

Dedup

Filter
```

第一批只接：

```text
5～10个重点信息源
```

不要一开始做几十个。

---

# 99. Phase 4：Push

完成：

```text
Push Decision

Customer Owner

DingTalk Adapter

Fallback Group
```

验收：

```text
A级 Event
→
自动找到负责人
→
钉钉消息
```

---

# 100. Phase 5：联调

完整：

```text
定时抓取
↓
Event
↓
Filter
↓
Expert
↓
Score
↓
Push
↓
钉钉
```

---

# 101. Phase 6：试运行

选择：

```text
1个行业

5～10个信息源

20～30个目标单位

10～20项公司能力
```

进行试运行。

---

# 102. 一期数据准备

首个行业只准备：

### 行业知识

```text
20～50条高质量主题知识
```

### 组织职责

```text
20～30个重点单位
```

### 部门

每单位重点：

```text
3～10个核心处室
```

### 公司能力

```text
10～20项
```

### Customer Owner

只维护：

```text
目标单位 → 客户经理
```

部门映射有就填，没有就走单位负责人。

---

# 103. 一期不做

明确排除：

```text
自动知识学习

复杂Case Memory

Knowledge Candidate

全量政府网站抓取

自主Web Research

多Agent辩论

知识图谱

Fine-tuning

自动CRM

自动客户沟通

自动邮件

自动生成完整解决方案

复杂销售流程
```

---

# 104. 一期最核心的技术原则

## 原则一

Collector 与 Expert 解耦。

```text
Collector
只产生 Event。
```

---

## 原则二

Expert 与 Delivery 解耦。

```text
Expert
只产生 Expert Result。
```

---

## 原则三

LLM 不决定一切。

```text
LLM
负责理解和判断。

Code
负责评分、权限、路由和推送。
```

---

## 原则四

结构化数据优先。

单位和部门优先来自：

```text
PostgreSQL
```

不要完全靠 RAG。

---

## 原则五

RAG 保持小而精。

一期只维护：

```text
行业知识
+
公司能力
```

组织职责以 SQL 为主。

---

## 原则六

允许 UNKNOWN。

系统不知道的时候：

```text
UNKNOWN
```

比 AI 猜一个部门更好。

---

# 105. 一期最终 Demo

场景：

Collector 自动抓取：

> XX市发布《城市生命线安全工程实施方案》。

Filter：

```text
RELEVANT
0.91
```

Expert：

```text
商机等级：
A

Score：
84

Confidence：
0.82
```

判断：

```text
潜在需求：

风险监测预警
物联感知接入
数据治理
```

推荐：

```text
XX市住建委

城建处
→ BUSINESS LEAD

科技信息处
→ TECH SUPPORT
```

我方：

```text
AI风险预警

IoT

数据治理
```

系统查询：

```text
XX市住建委
→ 客户经理 张三
```

最终：

```text
钉钉
→ @张三

🔥 AI发现A级商务机会
...
```

整个过程无人干预。

---

# 106. 一期验收条件

一期完成必须满足：

### 自动采集

至少：

```text
5个真实公开信息源
```

稳定运行。

### 自动去重

同一个事件不得重复大量推送。

### Filter

能够明显减少无关信息进入 Expert。

### Expert

可以稳定输出：

```text
需求
单位
部门
能力
风险
建议动作
```

### Score

分数可以由代码复算。

### Push

可以根据：

```text
Organization
```

找到对应负责人。

### DingTalk

A级/B级事件可以成功推送。

### Fallback

没有配置负责人时：

```text
发送公共线索群
```

### Trace

任意 Event 可以追踪：

```text
从哪里抓到
什么时候分析
模型输出什么
为什么推给某人
是否发送成功
```

---

# 107. 后续二期扩展

一期架构完成后，可以自然增加：

```text
更多数据源

自动Web Research

Reviewer Retry

Case Retrieval

Expert Knowledge

Human-in-the-loop

CRM集成

区域/行业负责人路由

商机认领

反馈学习

钉钉待办
```

其中 LangGraph 的 persistence 和 interrupt 机制可以用于后续需要人工确认后继续执行的场景。

---

# 108. 一期最终架构定版

```text
                    Opportunity Intelligence
                             Platform
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
    Collector                Expert                  Delivery
                                │
    Scheduler               LangGraph             Push Decision
    Crawler                    │                       │
    Parser                     │                    Owner Routing
    Dedup                      │                       │
    Filter                  Analyze                 DingTalk
        │                     │
        └── Event ─────────→ RAG
                              │
                           Expert Judge
                              │
                            Score
                              │
                           Reviewer
                              │
                         Expert Result
                              │
                              └────────────→ Delivery
```

最终一期技术组合确定为：

```text
Python 3.12
FastAPI
LangGraph
PostgreSQL
pgvector
Redis
APScheduler
httpx
BeautifulSoup
Playwright
Pydantic
SQLAlchemy
Alembic
Docker
DingTalk OpenAPI
```

---

# 109. 一期核心价值

一期的真正目标不是建设一个复杂 Agent 平台。

而是验证一条最有价值的业务链：

> **系统能不能主动发现外部变化，并在商务人员还没有关注到之前，判断它与哪些客户有关、可能有什么需求，以及谁应该立即跟进。**

因此整个一期应始终围绕：

```text
发现得及时
+
判断得准确
+
推给正确的人
```

三个指标进行开发。

如果这三件事成立，后续才值得继续增加 Research、Case Memory、Expert Knowledge 和自动学习能力。