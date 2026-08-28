import { useState } from "react";
import { ApiError } from "../api/client";
import { filterRulesApi } from "../api/resources";
import type { EventFilterRule, EventFilterRuleCreate } from "../api/types";
import DeleteButton from "../components/DeleteButton";

const RULE_TYPES = [
  { value: "INCLUDE_KEYWORD", label: "包含关键词（命中即通过）" },
  { value: "EXCLUDE_KEYWORD", label: "排除关键词（命中即拒绝，优先于包含）" },
  { value: "RELEVANCE_THRESHOLD", label: "LLM 相关性阈值（0~1 的数字，只需一条）" },
] as const;

const EMPTY: EventFilterRuleCreate = {
  rule_type: "INCLUDE_KEYWORD",
  value: "",
};

function ruleTypeLabel(value: string): string {
  return RULE_TYPES.find((t) => t.value === value)?.label ?? value;
}

export default function FilterRulesPage() {
  const { data: rules, isLoading } = filterRulesApi.useList();
  const createMutation = filterRulesApi.useCreate();
  const updateMutation = filterRulesApi.useUpdate();
  const enableMutation = filterRulesApi.useAction("enable");
  const disableMutation = filterRulesApi.useAction("disable");
  const deleteMutation = filterRulesApi.useDelete();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<EventFilterRuleCreate>(EMPTY);
  const [showForm, setShowForm] = useState(false);

  function startCreate() {
    setEditingId(null);
    setForm(EMPTY);
    setShowForm(true);
  }

  function startEdit(rule: EventFilterRule) {
    setEditingId(rule.id);
    setForm({ rule_type: rule.rule_type, value: rule.value });
    setShowForm(true);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (editingId) {
      updateMutation.mutate(
        { id: editingId, body: { value: form.value } },
        { onSuccess: () => setShowForm(false) },
      );
    } else {
      createMutation.mutate(form, { onSuccess: () => setShowForm(false) });
    }
  }

  const mutationError = createMutation.error ?? updateMutation.error;
  const byType = (type: string) => (rules ?? []).filter((r) => r.rule_type === type);

  return (
    <div>
      <div className="toolbar">
        <h2>过滤规则</h2>
        <button className="primary" onClick={startCreate}>
          + 新建规则
        </button>
      </div>
      <p className="muted">
        Layer 1(规则，免费，先跑）+ Layer 2（LLM 相关性判断，Layer 1 通过后才跑，阈值看这里配的
        RELEVANCE_THRESHOLD）。没有任何启用中的规则时，Collector 用 spec §15 的示例关键词兜底。
      </p>

      {isLoading && <p className="muted">加载中…</p>}

      <table>
        <thead>
          <tr>
            <th>类型</th>
            <th>值</th>
            <th>状态</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          {RULE_TYPES.flatMap((t) => byType(t.value)).map((rule) => (
            <tr key={rule.id}>
              <td>{ruleTypeLabel(rule.rule_type)}</td>
              <td>{rule.value}</td>
              <td>
                <span className={`status-badge ${rule.enabled ? "" : "disabled"}`}>
                  {rule.enabled ? "启用" : "停用"}
                </span>
              </td>
              <td className="row-actions">
                <button onClick={() => startEdit(rule)}>编辑</button>
                {rule.enabled ? (
                  <button onClick={() => disableMutation.mutate(rule.id)}>停用</button>
                ) : (
                  <button onClick={() => enableMutation.mutate(rule.id)}>启用</button>
                )}
                <DeleteButton
                  label={`${ruleTypeLabel(rule.rule_type)}: ${rule.value}`}
                  onDelete={() => deleteMutation.mutate(rule.id)}
                />
              </td>
            </tr>
          ))}
          {rules?.length === 0 && (
            <tr>
              <td colSpan={4} className="muted">
                还没有配置规则，Collector 正在用代码里的兜底默认值
              </td>
            </tr>
          )}
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
          <h2>{editingId ? "编辑规则" : "新建规则"}</h2>
          <label>
            类型
            <select
              required
              disabled={!!editingId}
              value={form.rule_type}
              onChange={(e) => setForm({ ...form, rule_type: e.target.value })}
            >
              {RULE_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            值
            <input
              required
              value={form.value}
              onChange={(e) => setForm({ ...form, value: e.target.value })}
              placeholder={
                form.rule_type === "RELEVANCE_THRESHOLD" ? "例如 0.6" : "例如 智慧工地"
              }
            />
          </label>
          <div className="row-actions">
            <button
              type="submit"
              className="primary"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
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
