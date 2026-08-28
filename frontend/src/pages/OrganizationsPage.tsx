import { Fragment, useState } from "react";
import { ApiError } from "../api/client";
import { organizationsApi } from "../api/resources";
import type { Organization, OrganizationCreate } from "../api/types";
import { ORGANIZATION_TYPES } from "../api/vocabulary";
import DeleteButton from "../components/DeleteButton";
import DepartmentsPanel from "./DepartmentsPanel";

const EMPTY: OrganizationCreate = {
  name: "",
  short_name: "",
  region: "重庆市",
  organization_type: "GOV",
  description: "",
  source_url: "",
};

export default function OrganizationsPage() {
  const { data: orgs, isLoading } = organizationsApi.useList();
  const createMutation = organizationsApi.useCreate();
  const updateMutation = organizationsApi.useUpdate();
  const activateMutation = organizationsApi.useAction("activate");
  const deactivateMutation = organizationsApi.useAction("deactivate");
  const deleteMutation = organizationsApi.useDelete();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<OrganizationCreate>(EMPTY);
  const [showForm, setShowForm] = useState(false);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY);
    setShowForm(true);
  }

  function startEdit(org: Organization) {
    setEditingId(org.id);
    setForm({
      name: org.name,
      short_name: org.short_name ?? "",
      region: org.region ?? "",
      organization_type: org.organization_type ?? "",
      description: org.description ?? "",
      source_url: org.source_url ?? "",
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
        <h2>重点单位</h2>
        <button className="primary" onClick={startCreate}>
          + 新建单位
        </button>
      </div>

      {isLoading && <p className="muted">加载中…</p>}

      <table>
        <thead>
          <tr>
            <th />
            <th>名称</th>
            <th>地区</th>
            <th>类型</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {orgs?.map((org) => (
            <Fragment key={org.id}>
              <tr>
                <td>
                  <button onClick={() => setExpandedId(expandedId === org.id ? null : org.id)}>
                    {expandedId === org.id ? "收起" : "部门"}
                  </button>
                </td>
                <td>{org.name}</td>
                <td>{org.region}</td>
                <td>
                  {ORGANIZATION_TYPES.find((t) => t.value === org.organization_type)?.label ??
                    org.organization_type}
                </td>
                <td>
                  <span className={`status-badge ${org.status === "ACTIVE" ? "" : "inactive"}`}>
                    {org.status}
                  </span>
                </td>
                <td className="row-actions">
                  <button onClick={() => startEdit(org)}>编辑</button>
                  {org.status === "ACTIVE" ? (
                    <button onClick={() => deactivateMutation.mutate(org.id)}>停用</button>
                  ) : (
                    <button onClick={() => activateMutation.mutate(org.id)}>启用</button>
                  )}
                  <DeleteButton label={org.name} onDelete={() => deleteMutation.mutate(org.id)} />
                </td>
              </tr>
              {expandedId === org.id && (
                <tr>
                  <td colSpan={6}>
                    <DepartmentsPanel organizationId={org.id} />
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
        </tbody>
      </table>
      {deleteMutation.error && (
        <div className="error-banner">
          {deleteMutation.error instanceof ApiError
            ? deleteMutation.error.message
            : String(deleteMutation.error)}
        </div>
      )}

      {showForm && (
        <form className="panel" onSubmit={handleSubmit}>
          <h2>{editingId ? "编辑单位" : "新建单位"}</h2>
          <label>
            名称
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </label>
          <label>
            简称
            <input
              value={form.short_name ?? ""}
              onChange={(e) => setForm({ ...form, short_name: e.target.value })}
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
            单位类型
            <select
              value={form.organization_type ?? ""}
              onChange={(e) => setForm({ ...form, organization_type: e.target.value })}
            >
              <option value="">(未分类)</option>
              {ORGANIZATION_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            职责描述
            <textarea
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </label>
          <label>
            来源链接
            <input
              value={form.source_url ?? ""}
              onChange={(e) => setForm({ ...form, source_url: e.target.value })}
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
