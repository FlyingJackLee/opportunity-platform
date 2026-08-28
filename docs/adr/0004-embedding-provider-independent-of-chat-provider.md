# Embedding provider 与 Chat provider 独立配置、独立选型

**Status:** accepted

spec §75 的 `LLMGateway` 接口把 `structured_generate`（Filter/Analyzer/Judge/Reviewer 四个 task_type 共用）和 `embed` 放在同一个类里，Phase 1 的实现也确实只用一个 `LLM_PROVIDER` 选出一个 `OpenAICompatibleLLMGateway`/`StubLLMGateway` 实例，两个方法都从这一个实例来。这在厂商恰好同时提供 chat completions 和 embeddings 时（比如 OpenAI）没问题，但不是所有厂商都两者都提供——典型的是 DeepSeek：官方 API（`api-docs.deepseek.com`）只有 `/chat/completions`，没有 embeddings 端点。一旦把 `LLM_PROVIDER` 指向这类纯 chat 厂商，`app/knowledge/` 的 RAG 检索/灌入调用 `gateway.embed()` 会直接打到一个不存在的端点上报错——这跟 spec §77 明确写的"Embedding → 独立Embedding模型"是矛盾的：规格从一开始就设想 embedding 可以换成跟 chat 不同的模型/厂商。

## 决策

不改 `LLMGateway` 接口本身（`app/nodes/*.py`、`app/knowledge/embedding.py` 等调用点继续只认一个 `LLMGateway` 对象，不知道背后有几个厂商）。改为新增 `CompositeLLMGateway`（`app/llm/providers/composite.py`），内部持有两个独立的 `LLMGateway` 子实例——一个只用来接 `structured_generate`（由 `LLM_PROVIDER`/`LLM_API_KEY`/`LLM_MODEL`/`LLM_BASE_URL` 选型），一个只用来接 `embed`（由新增的 `EMBEDDING_PROVIDER`/`EMBEDDING_API_KEY`/`EMBEDDING_MODEL`/`EMBEDDING_BASE_URL` 独立选型）。`app/main.py` 的 `build_llm_gateway` 分别 build 这两个子实例再组装成一个 `CompositeLLMGateway`。

两条配置轴彻底独立、互不隐式回退：

- `EMBEDDING_PROVIDER` 默认 `stub`，跟 `LLM_PROVIDER` 是否等于 `openai_compatible` 无关——把 `LLM_PROVIDER` 换成真实厂商（哪怕是 DeepSeek）不会连带让 embedding 也变成真实调用，必须显式再设一遍 `EMBEDDING_PROVIDER=openai_compatible`。
- `EMBEDDING_PROVIDER=openai_compatible` 时，`EMBEDDING_API_KEY`/`EMBEDDING_BASE_URL` 不允许留空后偷偷复用 `LLM_API_KEY`/`LLM_BASE_URL`（哪怕两边真的用同一个厂商，也要各填一遍）；缺失时跟现有 `LLM_API_KEY` 检查一样，在 `build_embedding_gateway` 里直接 `RuntimeError`，不会静默退化。

选择"默认安全、不做隐式回退"是因为这条 ADR要解决的正是"配置一个厂商时不小心连带破坏另一半"这个问题——任何隐式回退都会把同样的坑换个形式带回来。

一期明确不做的：spec §77 里 Filter/Analyzer/Judge/Reviewer 四个 task_type 各自用不同模型（"低成本模型 vs 高能力模型"）的 Model Profile 路由——现在这四个 task_type 仍然共用同一个 `LLM_MODEL`，`task_type` 参数目前只用于日志/prompt 版本记录，不参与选型。这个更细粒度的路由留到二期，本 ADR 只解决"chat 整体 vs embedding"这一层的独立性。

## Consequences

- `.env.example` 需要同时维护两组几乎并列的配置块（`LLM_*` 和 `EMBEDDING_*`），初次看容易以为是冗余——这正是本 ADR 存在的原因，配置注释里也指回了这里。
- 想要真实跑通 RAG（行业知识/组织/能力检索）必须显式配置 `EMBEDDING_PROVIDER=openai_compatible` 及对应厂商信息；只配 `LLM_PROVIDER` 不会让 embedding 自动可用，这是有意为之，不是遗漏。
- pgvector 列宽是写死的（`app/models/knowledge.py`、`migrations/versions/0002_*`/`0006_*`），不会跟着 `EMBEDDING_MODEL` 自动变化，也没法"自动识别"——一列必须固定一个宽度，任何厂商的 API 也不会在调用前预告输出维度。当前实际配置是 BGE-m3（1024 维），`0006` 已经把列宽从 Phase 1 默认的 1536（当时假设 OpenAI）改成了 1024。换一个输出维度不同的 embedding 模型需要照 `0006` 的样子再写一条 migration，本 ADR 不试图消灭这个步骤，只是把约束写进了 `.env.example` 的注释里。
- 以后任何"一个逻辑接口背后可能有多个厂商/职责"的场景（比如未来真的要做 Filter/Judge 各自选模型的 Model Profile），可以复用这里的 Composite 模式——接口不变，多个独立配置的子实现在组装层被组合起来，而不是把多厂商的凭证塞进同一个 provider 类的构造函数里。
