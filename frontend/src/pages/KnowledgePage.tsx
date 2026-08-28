import { useState } from "react";
import { ApiError } from "../api/client";
import { knowledgeApi } from "../api/resources";
import type { KnowledgeChunk, KnowledgeChunkCreate } from "../api/types";

const EMPTY: KnowledgeChunkCreate = {
  title: "",
  content: "",
  industry: "住建",
  region: "重庆市",
  topic: "",
};

export default function KnowledgePage() {
  const { data: chunks, isLoading } = knowledgeApi.useList();
  const createMutation = knowledgeApi.useCreate();
  const updateMutation = knowledgeApi.useUpdate();
  const activateMutation = knowledgeApi.useAction("activate");
  const deactivateMutation = knowledgeApi.useAction("deactivate");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<KnowledgeChunkCreate>(EMPTY);
  const [showForm, setShowForm] = useState(false);

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY);
    setShowForm(true);
  }

  function startEdit(chunk: KnowledgeChunk) {
    setEditingId(chunk.id);
    setForm({
      title: chunk.title,
      content: chunk.content,
      industry: chunk.industry ?? "",
      region: chunk.region ?? "",
      topic: chunk.topic ?? "",
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
        <h2>行业知识</h2>
        <button className="primary" onClick={startCreate}>
          + 新建知识条目
        </button>
      </div>
      <p className="muted">
        保存/更新时会自动调用配置的 Embedding 服务计算向量，用于 RAG 检索，无需手动填写。
      </p>

      {isLoading && <p className="muted">加载中…</p>}

      <table>
        <thead>
          <tr>
            <th>标题</th>
            <th>行业</th>
            <th>地区</th>
            <th>主题</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {chunks?.map((chunk) => (
            <tr key={chunk.id}>
              <td>{chunk.title}</td>
              <td>{chunk.industry}</td>
              <td>{chunk.region}</td>
              <td>{chunk.topic}</td>
              <td>
                <span className={`status-badge ${chunk.status === "ACTIVE" ? "" : "inactive"}`}>
                  {chunk.status}
                </span>
              </td>
              <td className="row-actions">
                <button onClick={() => startEdit(chunk)}>编辑</button>
                {chunk.status === "ACTIVE" ? (
                  <button onClick={() => deactivateMutation.mutate(chunk.id)}>停用</button>
                ) : (
                  <button onClick={() => activateMutation.mutate(chunk.id)}>启用</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showForm && (
        <form className="panel" onSubmit={handleSubmit}>
          <h2>{editingId ? "编辑知识条目" : "新建知识条目"}</h2>
          <label>
            标题
            <input
              required
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
            />
          </label>
          <label>
            内容
            <textarea
              required
              value={form.content}
              onChange={(e) => setForm({ ...form, content: e.target.value })}
            />
          </label>
          <label>
            行业
            <input
              value={form.industry ?? ""}
              onChange={(e) => setForm({ ...form, industry: e.target.value })}
            />
          </label>
          <label>
            地区
            <input
              value={form.region ?? ""}
              onChange={(e) => setForm({ ...form, region: e.target.value })}
            />
          </label>
          <label>
            主题
            <input
              value={form.topic ?? ""}
              onChange={(e) => setForm({ ...form, topic: e.target.value })}
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
