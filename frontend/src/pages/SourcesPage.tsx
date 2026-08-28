import { useState } from "react";
import { Link } from "react-router-dom";
import { collectorsApi } from "../api/resources";
import { ApiError } from "../api/client";
import type { CollectorRunResponse, CollectorSource, CollectorSourceCreate } from "../api/types";
import { SOURCE_TYPES } from "../api/vocabulary";
import DeleteButton from "../components/DeleteButton";
import { useElapsedSeconds } from "../hooks/useElapsedSeconds";

const EMPTY: CollectorSourceCreate = {
  name: "",
  source_type: "GOV_WEB",
  base_url: "",
  list_url: "",
  enabled: true,
  schedule: "0 */2 * * *",
  parser_type: "GOV_GENERIC",
  industry_tags: [],
  region_tags: [],
  priority: 0,
};

function toTags(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function SourcesPage() {
  const { data: sources, isLoading } = collectorsApi.useList();
  const createMutation = collectorsApi.useCreate();
  const updateMutation = collectorsApi.useUpdate();
  const enableMutation = collectorsApi.useAction("enable");
  const disableMutation = collectorsApi.useAction("disable");
  const runMutation = collectorsApi.useAction<CollectorRunResponse>("run");
  const deleteMutation = collectorsApi.useDelete();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<CollectorSourceCreate>(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [runResult, setRunResult] = useState<{ name: string; data: CollectorRunResponse } | null>(
    null,
  );
  const [runningId, setRunningId] = useState<string | null>(null);
  const elapsedSeconds = useElapsedSeconds(runningId !== null);

  function handleRun(source: CollectorSource) {
    setRunningId(source.id);
    setRunResult(null);
    runMutation.mutate(source.id, {
      onSuccess: (data) => setRunResult({ name: source.name, data }),
      onSettled: () => setRunningId(null),
    });
  }

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY);
    setShowForm(true);
  }

  function startEdit(source: CollectorSource) {
    setEditingId(source.id);
    setForm({
      name: source.name,
      source_type: source.source_type,
      base_url: source.base_url ?? "",
      list_url: source.list_url,
      enabled: source.enabled,
      schedule: source.schedule,
      parser_type: source.parser_type,
      industry_tags: source.industry_tags ?? [],
      region_tags: source.region_tags ?? [],
      priority: source.priority,
    });
    setShowForm(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editingId) {
      updateMutation.mutate(
        { id: editingId, body: form },
        { onSuccess: () => setShowForm(false) },
      );
    } else {
      createMutation.mutate(form, { onSuccess: () => setShowForm(false) });
    }
  }

  const mutationError = createMutation.error ?? updateMutation.error;

  return (
    <div>
      <div className="toolbar">
        <h2>信息源</h2>
        <button className="primary" onClick={startCreate}>
          + 新建信息源
        </button>
      </div>

      {isLoading && <p className="muted">加载中…</p>}

      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>类型</th>
            <th>抓取列表页</th>
            <th>调度</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {sources?.map((s) => (
            <tr key={s.id}>
              <td>{s.name}</td>
              <td>{SOURCE_TYPES.find((t) => t.value === s.source_type)?.label ?? s.source_type}</td>
              <td style={{ maxWidth: 280, overflow: "hidden", textOverflow: "ellipsis" }}>
                {s.list_url}
              </td>
              <td>{s.schedule}</td>
              <td>
                <span className={`status-badge ${s.enabled ? "" : "disabled"}`}>
                  {s.enabled ? "启用" : "停用"}
                </span>
              </td>
              <td className="row-actions">
                <button onClick={() => startEdit(s)}>编辑</button>
                {s.enabled ? (
                  <button onClick={() => disableMutation.mutate(s.id)}>停用</button>
                ) : (
                  <button onClick={() => enableMutation.mutate(s.id)}>启用</button>
                )}
                <button onClick={() => handleRun(s)} disabled={runningId !== null}>
                  {runningId === s.id ? `抓取中…(${elapsedSeconds}s)` : "立即抓取"}
                </button>
                <DeleteButton label={s.name} onDelete={() => deleteMutation.mutate(s.id)} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {runningId && (
        <p className="muted" style={{ marginTop: 8 }}>
          正在抓取，如果这个源触发了 LLM 兜底解析，可能需要几十秒到几分钟——这是真实的网络+LLM
          调用耗时，不是卡住了，请不要重复点击或刷新页面。
        </p>
      )}

      {runResult && (
        <div
          style={{
            marginTop: 12,
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: 12,
          }}
        >
          <strong>{runResult.name}</strong> 抓取完成：抓到 {runResult.data.fetched} 条，新建{" "}
          {runResult.data.created} 条，去重 {runResult.data.deduped} 条，过滤掉{" "}
          {runResult.data.filtered_out} 条，触发分析 {runResult.data.triggered_analysis} 条。
          {runResult.data.created > 0 && (
            <>
              {" "}
              去 <Link to="/events">事件页面</Link> 能看到新建的 Event。
            </>
          )}
          {runResult.data.errors.length > 0 && (
            <ul style={{ marginTop: 8 }}>
              {runResult.data.errors.map((err, i) => (
                <li key={i} style={{ fontSize: 12 }}>
                  {err}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
      {runMutation.error && (
        <div className="error-banner">
          抓取请求失败：
          {runMutation.error instanceof ApiError
            ? runMutation.error.message
            : String(runMutation.error)}
        </div>
      )}
      {deleteMutation.error && (
        <div className="error-banner">
          {deleteMutation.error instanceof ApiError
            ? deleteMutation.error.message
            : String(deleteMutation.error)}
        </div>
      )}

      {showForm && (
        <form className="panel" onSubmit={handleSubmit}>
          <h2>{editingId ? "编辑信息源" : "新建信息源"}</h2>
          <label>
            名称
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            站点类型
            <select
              required
              value={form.source_type}
              onChange={(e) => setForm({ ...form, source_type: e.target.value })}
            >
              {SOURCE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            列表页 URL
            <input
              required
              value={form.list_url}
              onChange={(e) => setForm({ ...form, list_url: e.target.value })}
            />
          </label>
          <label>
            base_url(可选)
            <input
              value={form.base_url ?? ""}
              onChange={(e) => setForm({ ...form, base_url: e.target.value })}
            />
          </label>
          <label>
            调度(cron)
            <input
              required
              value={form.schedule}
              onChange={(e) => setForm({ ...form, schedule: e.target.value })}
            />
          </label>
          <label>
            parser_type
            <input
              required
              value={form.parser_type}
              onChange={(e) => setForm({ ...form, parser_type: e.target.value })}
            />
          </label>
          <label>
            行业标签(逗号分隔)
            <input
              value={(form.industry_tags ?? []).join(", ")}
              onChange={(e) => setForm({ ...form, industry_tags: toTags(e.target.value) })}
            />
          </label>
          <label>
            地区标签(逗号分隔)
            <input
              value={(form.region_tags ?? []).join(", ")}
              onChange={(e) => setForm({ ...form, region_tags: toTags(e.target.value) })}
            />
          </label>
          <label>
            优先级
            <input
              type="number"
              value={form.priority ?? 0}
              onChange={(e) => setForm({ ...form, priority: Number(e.target.value) })}
            />
          </label>
          <div className="row-actions">
            <button type="submit" className="primary">
              保存
            </button>
            <button type="button" onClick={() => setShowForm(false)}>
              取消
            </button>
          </div>
          {mutationError && (
            <div className="error-banner">
              {mutationError instanceof ApiError ? mutationError.message : String(mutationError)}
            </div>
          )}
        </form>
      )}
    </div>
  );
}
