import { useState } from "react";
import { ApiError } from "../api/client";
import { departmentsApi } from "../api/resources";

export default function DepartmentsPanel({ organizationId }: { organizationId: string }) {
  const { data: departments, isLoading } = departmentsApi.useList({
    organization_id: organizationId,
  });
  const createMutation = departmentsApi.useCreate();
  const activateMutation = departmentsApi.useAction("activate");
  const deactivateMutation = departmentsApi.useAction("deactivate");

  const [name, setName] = useState("");
  const [responsibility, setResponsibility] = useState("");

  function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    createMutation.mutate(
      { organization_id: organizationId, name, responsibility },
      {
        onSuccess: () => {
          setName("");
          setResponsibility("");
        },
      },
    );
  }

  return (
    <div style={{ padding: "8px 0 16px 24px" }}>
      {isLoading && <p className="muted">加载部门中…</p>}
      <table>
        <thead>
          <tr>
            <th>处室</th>
            <th>职责</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {departments?.map((dept) => (
            <tr key={dept.id}>
              <td>{dept.name}</td>
              <td>{dept.responsibility}</td>
              <td>
                <span className={`status-badge ${dept.status === "ACTIVE" ? "" : "inactive"}`}>
                  {dept.status}
                </span>
              </td>
              <td className="row-actions">
                {dept.status === "ACTIVE" ? (
                  <button onClick={() => deactivateMutation.mutate(dept.id)}>停用</button>
                ) : (
                  <button onClick={() => activateMutation.mutate(dept.id)}>启用</button>
                )}
              </td>
            </tr>
          ))}
          {departments?.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                还没有部门
              </td>
            </tr>
          )}
        </tbody>
      </table>

      <form onSubmit={handleAdd} style={{ display: "flex", gap: 8, marginTop: 10 }}>
        <input
          required
          placeholder="处室名称"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <input
          placeholder="职责(可选)"
          value={responsibility}
          onChange={(e) => setResponsibility(e.target.value)}
          style={{ flex: 1 }}
        />
        <button type="submit" className="primary">
          + 添加部门
        </button>
      </form>
      {createMutation.error && (
        <div className="error-banner">
          {createMutation.error instanceof ApiError
            ? createMutation.error.message
            : String(createMutation.error)}
        </div>
      )}
    </div>
  );
}
