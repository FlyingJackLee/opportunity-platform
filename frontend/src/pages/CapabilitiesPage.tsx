import { useState } from "react";
import { ApiError } from "../api/client";
import { capabilitiesApi } from "../api/resources";
import type { Capability, CapabilityCreate } from "../api/types";

const EMPTY: CapabilityCreate = {
  name: "",
  scenarios: [],
  industries: [],
  description: "",
};

function toTags(text: string): string[] {
  return text
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function CapabilitiesPage() {
  const { data: capabilities, isLoading } = capabilitiesApi.useList();
  const createMutation = capabilitiesApi.useCreate();
  const updateMutation = capabilitiesApi.useUpdate();
  const activateMutation = capabilitiesApi.useAction("activate");
  const deactivateMutation = capabilitiesApi.useAction("deactivate");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<CapabilityCreate>(EMPTY);
  const [showForm, setShowForm] = useState(false);

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY);
    setShowForm(true);
  }

  function startEdit(capability: Capability) {
    setEditingId(capability.id);
    setForm({
      name: capability.name,
      scenarios: capability.scenarios ?? [],
      industries: capability.industries ?? [],
      description: capability.description ?? "",
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
        <h2>公司能力</h2>
        <button className="primary" onClick={startCreate}>
          + 新建能力
        </button>
      </div>
      <p className="muted">
        保存/更新时会自动调用配置的 Embedding 服务计算向量，用于 RAG 检索，无需手动填写。
      </p>

      {isLoading && <p className="muted">加载中…</p>}

      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>适用场景</th>
            <th>适用行业</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {capabilities?.map((capability) => (
            <tr key={capability.id}>
              <td>{capability.name}</td>
              <td>{(capability.scenarios ?? []).join(", ")}</td>
              <td>{(capability.industries ?? []).join(", ")}</td>
              <td>
                <span
                  className={`status-badge ${capability.status === "ACTIVE" ? "" : "inactive"}`}
                >
                  {capability.status}
                </span>
              </td>
              <td className="row-actions">
                <button onClick={() => startEdit(capability)}>编辑</button>
                {capability.status === "ACTIVE" ? (
                  <button onClick={() => deactivateMutation.mutate(capability.id)}>停用</button>
                ) : (
                  <button onClick={() => activateMutation.mutate(capability.id)}>启用</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showForm && (
        <form className="panel" onSubmit={handleSubmit}>
          <h2>{editingId ? "编辑能力" : "新建能力"}</h2>
          <label>
            名称
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            适用场景(逗号分隔)
            <input
              value={(form.scenarios ?? []).join(", ")}
              onChange={(e) => setForm({ ...form, scenarios: toTags(e.target.value) })}
            />
          </label>
          <label>
            适用行业(逗号分隔)
            <input
              value={(form.industries ?? []).join(", ")}
              onChange={(e) => setForm({ ...form, industries: toTags(e.target.value) })}
            />
          </label>
          <label>
            描述
            <textarea
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <div className="row-actions">
            <button type="submit" className="primary" disabled={createMutation.isPending || updateMutation.isPending}>
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
