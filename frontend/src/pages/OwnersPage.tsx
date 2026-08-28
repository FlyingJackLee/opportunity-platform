import { useState } from "react";
import { ApiError } from "../api/client";
import { departmentsApi, organizationsApi, ownersApi } from "../api/resources";
import type { CustomerOwner, CustomerOwnerCreate } from "../api/types";

const EMPTY: CustomerOwnerCreate = {
  organization_id: "",
  department_id: null,
  owner_name: "",
  owner_user_id: "",
  dingtalk_user_id: "",
};

export default function OwnersPage() {
  const { data: owners, isLoading } = ownersApi.useList();
  const { data: orgs } = organizationsApi.useList();
  const createMutation = ownersApi.useCreate();
  const updateMutation = ownersApi.useUpdate();
  const enableMutation = ownersApi.useAction("enable");
  const disableMutation = ownersApi.useAction("disable");

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<CustomerOwnerCreate>(EMPTY);
  const [showForm, setShowForm] = useState(false);

  const { data: departmentsForOrg } = departmentsApi.useList(
    form.organization_id ? { organization_id: form.organization_id } : undefined,
  );

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY);
    setShowForm(true);
  }

  function startEdit(owner: CustomerOwner) {
    setEditingId(owner.id);
    setForm({
      organization_id: owner.organization_id,
      department_id: owner.department_id,
      owner_name: owner.owner_name,
      owner_user_id: owner.owner_user_id ?? "",
      dingtalk_user_id: owner.dingtalk_user_id ?? "",
    });
    setShowForm(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editingId) {
      // organization_id/department_id aren't editable after creation (see
      // CustomerOwnerUpdate) -- only the contact fields are.
      updateMutation.mutate(
        {
          id: editingId,
          body: {
            owner_name: form.owner_name,
            owner_user_id: form.owner_user_id,
            dingtalk_user_id: form.dingtalk_user_id,
          },
        },
        { onSuccess: () => setShowForm(false) },
      );
    } else {
      createMutation.mutate(form, { onSuccess: () => setShowForm(false) });
    }
  }

  const mutationError = createMutation.error ?? updateMutation.error;
  const orgNameById = new Map((orgs ?? []).map((o) => [o.id, o.name]));

  return (
    <div>
      <div className="toolbar">
        <h2>客户经理</h2>
        <button className="primary" onClick={startCreate}>
          + 新建客户经理
        </button>
      </div>

      {isLoading && <p className="muted">加载中…</p>}

      <table>
        <thead>
          <tr>
            <th>姓名</th>
            <th>单位</th>
            <th>钉钉 UserId</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {owners?.map((owner) => (
            <tr key={owner.id}>
              <td>{owner.owner_name}</td>
              <td>{orgNameById.get(owner.organization_id) ?? owner.organization_id}</td>
              <td>{owner.dingtalk_user_id}</td>
              <td>
                <span className={`status-badge ${owner.enabled ? "" : "disabled"}`}>
                  {owner.enabled ? "启用" : "停用"}
                </span>
              </td>
              <td className="row-actions">
                <button onClick={() => startEdit(owner)}>编辑</button>
                {owner.enabled ? (
                  <button onClick={() => disableMutation.mutate(owner.id)}>停用</button>
                ) : (
                  <button onClick={() => enableMutation.mutate(owner.id)}>启用</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showForm && (
        <form className="panel" onSubmit={handleSubmit}>
          <h2>{editingId ? "编辑客户经理" : "新建客户经理"}</h2>
          <label>
            所属单位
            <select
              required
              disabled={!!editingId}
              value={form.organization_id}
              onChange={(e) =>
                setForm({ ...form, organization_id: e.target.value, department_id: null })
              }
            >
              <option value="" disabled>
                选择单位
              </option>
              {orgs?.map((org) => (
                <option key={org.id} value={org.id}>
                  {org.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            所属部门(可选,不选则代表整个单位的负责人)
            <select
              disabled={!!editingId || !form.organization_id}
              value={form.department_id ?? ""}
              onChange={(e) => setForm({ ...form, department_id: e.target.value || null })}
            >
              <option value="">(整个单位)</option>
              {departmentsForOrg?.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            姓名
            <input
              required
              value={form.owner_name}
              onChange={(e) => setForm({ ...form, owner_name: e.target.value })}
            />
          </label>
          <label>
            内部 UserId(可选)
            <input
              value={form.owner_user_id ?? ""}
              onChange={(e) => setForm({ ...form, owner_user_id: e.target.value })}
            />
          </label>
          <label>
            钉钉 UserId(用于 @ 通知)
            <input
              value={form.dingtalk_user_id ?? ""}
              onChange={(e) => setForm({ ...form, dingtalk_user_id: e.target.value })}
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
