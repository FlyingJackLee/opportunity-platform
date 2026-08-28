# Opportunity Intelligence Platform

AI 商务机会发现与行业专家研判平台。自动发现可能影响客户业务建设的公开事件，通过行业专家 AI 快速研判商务价值，并将高价值机会推送给对应客户经理。

一期 MVP 的完整技术规格见 [`spec.md`](spec.md)；领域术语表见 [`CONTEXT.md`](CONTEXT.md)；架构取舍记录见 [`docs/adr/`](docs/adr/)。

## 核心闭环

```text
公开信息 ──定时采集──▶ Collector ──Standard Event──▶ Expert Engine ──Opportunity Result──▶ Push Decision ──▶ 钉钉 ──▶ 客户经理
                                                                                  ▲
人工录入事件 ─────────────────────────────────────────────────────────────────────┘
```

三大模块（对应 `app/` 下的代码）：

| 模块 | 目录 | 职责 |
|---|---|---|
| Collector | `app/collector/` | 定时抓取公开信息源、解析、去重、两层 Filter |
| Expert Engine | `app/nodes/`, `app/graph/`, `app/knowledge/` | LangGraph 驱动的分析/RAG检索/专家研判/打分/复核 |
| Delivery | `app/delivery/`, `app/nodes/resolve_owner.py`, `app/nodes/send_dingtalk.py` | Push 决策、客户经理路由、钉钉推送、Fallback 群 |

## 当前进度

按 `spec.md` §96 开发阶段划分，已完成（见 git log，一个 phase 一个提交）：

- **Phase 1 — 基础工程**：FastAPI + Postgres + Alembic + LangGraph State + LLM Gateway + 日志
- **Phase 2 — Expert MVP**：Analyze Event → Industry/Org/Capability RAG → Expert Judge → Score → Mini Reviewer
- **Phase 3 — Collector**：Source 配置、Scheduler、Static Crawler、Parser、Dedup、两层 Filter
- **Phase 4 — Push**：Push Decision、Customer Owner 路由、DingTalk Adapter、Fallback 群

代码层面 LLM Gateway 和 DingTalk 都**已经是真实实现**，不再是纯 stub：

- `app/llm/providers/openai_compatible.py` — 任意 OpenAI 兼容 Chat Completions API 的真实调用（structured output + embedding）
- `app/delivery/dingtalk.py` — 真实钉钉自定义机器人 webhook（含签名）

`app/main.py` 只根据环境变量选择实现，**切换到真实服务不需要改代码**，见下方"从 stub 切到真实服务"。其中 LLM 部分是 `build_llm_gateway` 组装出的 `CompositeLLMGateway`（`app/llm/providers/composite.py`）——Chat（structured_generate）和 Embedding 各自独立选型，不共用一个厂商配置，原因见 [ADR-0004](docs/adr/0004-embedding-provider-independent-of-chat-provider.md)（起因是 DeepSeek 等厂商只有 chat 接口、没有 embeddings 接口）。

### 还没做的

对照 `spec.md` §100/§101/§102：

- **Phase 5 — 联调**：把定时抓取 → Event → Filter → Expert → Score → Push → 钉钉整条链路用真实数据跑通（当前各阶段都有独立测试覆盖，但还没有一次端到端的真实环境联调）
- **Phase 6 — 试运行**：接入真实数据后的观察/验收阶段
- **一期数据准备**（§102，纯运营工作，不是代码）：
  - 5～10 个真实公开信息源（`collector_source` 表，`scripts/seed_phase3.py` 目前只插入一条禁用的占位模板）
  - 20～50 条行业知识、20～30 个重点单位及其部门、10～20 项公司能力（通过 `app/knowledge/ingestion.py` 的 `ingest_knowledge_chunk`/`ingest_capability` 灌入，可参考 `scripts/seed_phase2.py` 的写法）
  - Customer Owner 名单（`POST /api/v1/customer-owners`）
  - 真实钉钉 webhook 与 LLM API Key（见下）

## 快速开始

### 依赖

- Python 3.12+，[`uv`](https://docs.astral.sh/uv/)
- Docker（跑 Postgres/pgvector + Redis）

### 1. 启动依赖服务

```bash
docker compose -f deploy/docker-compose.yml up -d
```

Postgres 映射到 `55432`，Redis 映射到 `56379`（避免和本机其它服务冲突，见 `docker-compose.yml` 注释）。

### 2. 配置环境变量

```bash
cp .env.example .env
```

默认配置（`LLM_PROVIDER=stub`、未设置钉钉 webhook）可以直接跑通全流程，用的是假数据和"只记录不发送"的 delivery channel，适合本地开发/测试。

### 3. 建表

```bash
uv run alembic upgrade head
uv run python scripts/init_checkpointer.py   # LangGraph checkpointer 表，独立于 Alembic
```

### 4.（可选）灌入 Phase 2/3 的演示数据

```bash
uv run python scripts/seed_phase2.py   # 行业知识/组织/部门/能力等演示数据
uv run python scripts/seed_phase3.py   # 一条禁用的 collector_source 占位模板
```

### 5. 启动服务

```bash
uv run uvicorn app.main:app --reload
```

FastAPI docs：http://localhost:8000/docs

## 从 stub 切到真实服务

三者都只需要改 `.env`，不需要改代码。

### LLM（Chat / structured-generate）

驱动 `analyze_event`/`expert_judge`/`mini_review`/Collector 的 `FILTER_RELEVANCE` 小模型层，四个 task_type 共用一个模型（一期不做按 task_type 分模型的 Model Profile 路由，见 ADR-0004）。

```bash
LLM_PROVIDER=openai_compatible
LLM_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini          # 换成实际要用的模型
LLM_BASE_URL=https://api.openai.com/v1   # 任何 OpenAI 兼容 chat-completions 端点都可以
```

常见厂商（都是 OpenAI 兼容 chat-completions，直接换 `LLM_MODEL`/`LLM_BASE_URL` 即可）：

| 厂商 | `LLM_MODEL` | `LLM_BASE_URL` |
|---|---|---|
| OpenAI | `gpt-4o-mini` | `https://api.openai.com/v1` |
| DeepSeek | `deepseek-chat` | `https://api.deepseek.com` |
| Moonshot | `moonshot-v1-8k` | `https://api.moonshot.cn/v1` |
| Qwen / 百炼 | `qwen-plus` | `https://dashscope.aliyuncs.com/compatible-mode/v1` |

`LLM_API_KEY` 未设置且 `LLM_PROVIDER=openai_compatible` 时，应用会在启动时直接报错（`app/main.py` 的显式检查），不会静默退回 stub。

**注意**：DeepSeek、Moonshot 只提供 chat completions，**没有 embeddings 端点**——设置 `LLM_PROVIDER` 只影响上面这四个 task_type，不会让 RAG 用的 embedding 也变成真实调用（也不会报错，因为下面这块默认独立留在 stub）。要接入真实 RAG，必须单独配置下面的 Embedding 部分。

### Embedding（独立于 Chat，见 ADR-0004）

用于 `app/knowledge/` 的 RAG 灌入/检索（行业知识、组织、公司能力）。`EMBEDDING_PROVIDER` 默认 `stub`，跟上面的 `LLM_PROVIDER` **完全独立**，不会因为 Chat 切了真实厂商就跟着变。

```bash
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_API_KEY=sk-...            # 不会退回复用 LLM_API_KEY，必须单独填
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1
```

选一个真正提供 embeddings 的厂商，比如 OpenAI（`text-embedding-3-small`，1536 维）、Qwen/百炼 DashScope（`text-embedding-v3`，默认 1024 维）或任意代理出 BGE-m3 的服务。当前 pgvector 列宽固定在 **1024 维**（`app/models/knowledge.py`，`migrations/versions/0006_*`，对应 BGE-m3）——这不是配置项，是数据库 schema 的硬约束，没有"自动识别"这回事：pgvector 一列必须固定一个宽度，且没有任何厂商的 API 会在调用前告诉你输出维度。换一个输出维度不同的模型（比如换回 OpenAI 1536 维），需要照着 `0006` 的样子再写一条 migration 改列宽度。`.env` 里的 `EMBEDDING_DIMENSION` 本身**不驱动** schema，只用来给 `EMBEDDING_PROVIDER=stub` 的假向量定长——保持它和当前迁移后的真实列宽一致就行。

### 钉钉

```bash
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=...
DINGTALK_WEBHOOK_SECRET=SEC...                     # 群机器人若开启了"加签"才需要
DINGTALK_PUBLIC_GROUP_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=...
DINGTALK_PUBLIC_GROUP_WEBHOOK_SECRET=SEC...
```

- 只要 `DINGTALK_WEBHOOK_URL` 有值，`build_delivery_channel` 就会切到真实的 `DingTalkAdapter`；不设置则用 `RecordingDeliveryChannel`（只记录、不真实发送，方便本地测试）。
- 主群 webhook 用于按 Customer Owner `@` 到人；Fallback 群 webhook（`DINGTALK_PUBLIC_GROUP_WEBHOOK_*`）用于该部门/单位没配 Customer Owner 时的兜底推送（spec §62）。
- 该机器人类型只能群发 + `@`群内成员，不能真正私聊到人（需要企业自建应用的"工作通知"能力，一期不做，见 `app/delivery/dingtalk.py` 顶部注释）。

## 测试

```bash
uv run pytest
```

注：测试依赖 `psycopg`（需要本机能加载 `libpq`）和 Postgres/Redis 已启动（`deploy/docker-compose.yml`）。macOS 上如果报 `no pq wrapper available`，装一下 libpq（如 `brew install libpq` 并将其加入 `DYLD_LIBRARY_PATH`/`PATH`，或改用 `psycopg[binary]`）。

## 前端管理界面

`frontend/`（Vite + React + TypeScript）分两部分：**配置数据的管理后台**——信息源、重点单位/部门、行业知识、公司能力、客户经理，对应 spec §102 的数据准备，不用手动连数据库改；以及一个只读的**事件/运行监控页**（`/events`）——按 Event 查看它的分析历史（分数/档位/状态）、点开某次 run 看完整研判结果和推送记录（spec §106 Trace），外加一个"查看 Graph 拓扑"按钮，用 `graph.get_graph().draw_mermaid()`（LangGraph 自带、不需要 LangGraph Platform）画出节点拓扑，前端用 `mermaid` 包渲染成 SVG——这是静态结构图，不是逐步骤的实时执行动画。手工建 Event 还是走 API/`/docs`，监控页不含创建入口。不含登录鉴权（一期内网工具）。

```bash
# 后端(先按上面的步骤起好，监听默认的 8000)
uv run uvicorn app.main:app --reload

# 前端(另开一个终端)
cd frontend
cp .env.example .env   # VITE_API_BASE_URL 默认指向 http://localhost:8000
npm install
npm run dev             # http://localhost:5173
```

前端跨源调用后端依赖 CORS，`Settings.cors_allow_origins`（`app/core/config.py`）默认已放行 `http://localhost:5173`；如果改了前端端口或部署到别的域名，在后端 `.env` 里加：

```bash
CORS_ALLOW_ORIGINS=["http://localhost:5173","https://your-domain"]
```

行业知识/公司能力的新建、编辑都会实时调用当前配置的 Embedding 服务（见上面"从 stub 切到真实服务"）算向量，前端表单不暴露 embedding 字段。

## 主要 API

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/v1/events` | 手工创建 Event（spec §20） |
| GET | `/api/v1/events` | 列出 Event（最新在前，一期无分页） |
| GET | `/api/v1/events/{id}` | Event 详情 + 它的完整分析历史（run 列表） |
| POST | `/api/v1/events/{id}/analyze` | 触发一次 Expert 分析（异步，返回 `run_id`） |
| POST | `/api/v1/events/{id}/reanalyze` | 对同一 Event 发起新的一次分析 |
| GET | `/api/v1/runs/{run_id}` | 查询某次分析的状态/结果/推送情况（spec §106 Trace） |
| GET | `/api/v1/graph/mermaid` | 当前 Graph 的静态节点拓扑（Mermaid 源码） |
| GET/POST/PATCH | `/api/v1/collectors` | 信息源 CRUD，另有 `/enable`、`/disable`、`/{id}/run`（手动触发一次采集） |
| GET/POST/PATCH | `/api/v1/organizations` | 重点单位 CRUD，另有 `/activate`、`/deactivate` |
| GET/POST/PATCH | `/api/v1/departments` | 部门 CRUD（`?organization_id=` 过滤），另有 `/activate`、`/deactivate` |
| GET/POST/PATCH | `/api/v1/knowledge-chunks` | 行业知识 CRUD（自动算 embedding），另有 `/activate`、`/deactivate` |
| GET/POST/PATCH | `/api/v1/capabilities` | 公司能力 CRUD（自动算 embedding），另有 `/activate`、`/deactivate` |
| GET/POST/PATCH | `/api/v1/customer-owners` | 客户经理 CRUD，另有 `/enable`、`/disable` |

完整列表见 `/docs`（FastAPI 自动生成）。除 `collector_source`/`customer_owner` 用 `enabled: bool` 外，其余实体统一用 `status: "ACTIVE"/"INACTIVE"` 做软删除，没有硬 DELETE。

## 目录速览

```text
app/
  api/          FastAPI 路由
  collector/    采集：scheduler / crawler / parser / dedup / filter
  core/         配置、DB、日志、异常、受控词表
  delivery/     推送渠道抽象 + DingTalk 真实实现 + Recording 假实现
  graph/        LangGraph 组装、checkpoint、重试、路由
  knowledge/    RAG：embedding / ingestion / retriever
  llm/          LLM Gateway 抽象 + stub / openai_compatible / composite 实现
  models/       SQLAlchemy 模型
  nodes/        Graph 节点（analyze_event ... send_dingtalk）
  repositories/ 数据访问层
  schemas/      Pydantic I/O schema
migrations/     Alembic
scripts/        一次性/种子脚本
tests/          按模块划分（collector/、push/、根目录下 graph 相关）
docs/adr/       架构决策记录
frontend/       管理界面（Vite + React + TS），见上面"前端管理界面"一节
  src/api/      fetch 封装 + 各资源的 react-query hooks（resource.ts 是共用工厂）
  src/pages/    事件/运行监控 + 信息源/重点单位/行业知识/公司能力/客户经理 5 个配置页面
```

更细的领域术语（Event / Opportunity / ExpertResult / FinalResult / Score Level 等的精确定义和易混淆点）见 [`CONTEXT.md`](CONTEXT.md)。
