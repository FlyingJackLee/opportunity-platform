import { useState } from "react";
import { collectorsApi } from "../api/resources";
import { ApiError } from "../api/client";
import type { CollectorSource, CollectorSourceCreate } from "../api/types";

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
  const runMutation = collectorsApi.useAction("run");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<CollectorSourceCreate>(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [runResult, setRunResult] = useState<string | null>(null);

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
              <td>{s.source_type}</td>
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
                <button
                  onClick={() =>
                    runMutation.mutate(s.id, {
                      onSuccess: (result) =>
                        setRunResult(`${s.name}: ${JSON.stringify(result)}`),
                    })
                  }
                  disabled={runMutation.isPending}
                >
                  立即抓取
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {runResult && <div className="error-banner">{runResult}</div>}

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
            source_type(站点分类,如 GOV_WEB)
            <input
              required
              value={form.source_type}
              onChange={(e) => setForm({ ...form, source_type: e.target.value })}
            />
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
