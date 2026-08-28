import { Fragment, useState } from "react";
import MermaidDiagram from "../components/MermaidDiagram";
import { useEvent, useEvents, useGraphMermaid, useRun } from "../api/monitoring";

const STATUS_LABELS: Record<string, string> = {
  NEW: "新建",
  FILTERED_OUT: "已过滤",
  WAITING_ANALYSIS: "等待分析",
  ANALYZING: "分析中",
  ANALYZED: "已分析",
  PUSHED: "已推送",
  ARCHIVED: "已归档",
  FAILED: "失败",
  RUNNING: "运行中",
  COMPLETED: "已完成",
  SENT: "已发送",
  SKIPPED: "已跳过",
};

function statusLabel(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

function RunDetail({ runId }: { runId: string }) {
  const { data: run, isLoading } = useRun(runId);
  if (isLoading) return <p className="muted">加载 run 详情…</p>;
  if (!run) return null;
  return (
    <div style={{ marginTop: 8 }}>
      {run.error && <div className="error-banner">{run.error}</div>}
      {run.push && run.push.length > 0 && (
        <>
          <h3>推送情况</h3>
          <table>
            <thead>
              <tr>
                <th>部门</th>
                <th>接收方类型</th>
                <th>接收方</th>
                <th>状态</th>
                <th>发送时间</th>
                <th>错误</th>
              </tr>
            </thead>
            <tbody>
              {run.push.map((p, i) => (
                <tr key={i}>
                  <td>{p.department_id}</td>
                  <td>{p.recipient_type}</td>
                  <td>{p.recipient_id ?? "-"}</td>
                  <td>{statusLabel(p.status)}</td>
                  <td>{p.sent_at ?? "-"}</td>
                  <td>{p.error ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {run.values && (
        <>
          <h3>研判结果</h3>
          <pre
            style={{
              whiteSpace: "pre-wrap",
              background: "var(--bg-alt)",
              padding: 12,
              borderRadius: 6,
              fontSize: 12,
              maxHeight: 400,
              overflow: "auto",
            }}
          >
            {JSON.stringify(run.values, null, 2)}
          </pre>
        </>
      )}
    </div>
  );
}

function EventDetailPanel({ eventId }: { eventId: string }) {
  const { data: event, isLoading } = useEvent(eventId);
  const [expandedRunId, setExpandedRunId] = useState<string | null>(null);

  if (isLoading) return <p className="muted">加载事件详情…</p>;
  if (!event) return null;

  return (
    <div style={{ padding: "8px 0 16px 24px" }}>
      <p style={{ maxWidth: 640 }}>{event.content}</p>
      <p className="muted">
        {event.region} · {event.industry} · {event.source_type}
        {event.source_url && (
          <>
            {" · "}
            <a href={event.source_url} target="_blank" rel="noreferrer">
              原文链接
            </a>
          </>
        )}
      </p>

      <h3>分析历史({event.runs.length} 次)</h3>
      <table>
        <thead>
          <tr>
            <th>开始时间</th>
            <th>状态</th>
            <th>分数</th>
            <th>档位</th>
            <th>置信度</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {event.runs.map((run) => (
            <tr key={run.id}>
              <td>{run.started_at ?? "-"}</td>
              <td>{statusLabel(run.status)}</td>
              <td>{run.score ?? "-"}</td>
              <td>{run.level ?? "-"}</td>
              <td>{run.confidence?.toFixed(2) ?? "-"}</td>
              <td>
                <button onClick={() => setExpandedRunId(expandedRunId === run.id ? null : run.id)}>
                  {expandedRunId === run.id ? "收起" : "详情"}
                </button>
              </td>
            </tr>
          ))}
          {event.runs.length === 0 && (
            <tr>
              <td colSpan={6} className="muted">
                还没有分析记录
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {expandedRunId && <RunDetail runId={expandedRunId} />}
    </div>
  );
}

export default function EventsPage() {
  const { data: events, isLoading } = useEvents();
  const { data: graph } = useGraphMermaid();
  const [expandedEventId, setExpandedEventId] = useState<string | null>(null);
  const [showGraph, setShowGraph] = useState(false);

  return (
    <div>
      <div className="toolbar">
        <h2>事件 / 运行监控</h2>
        <button onClick={() => setShowGraph(!showGraph)}>
          {showGraph ? "隐藏流程图" : "查看 Graph 拓扑"}
        </button>
      </div>
      <p className="muted">只读——手工建事件请用 /docs 里的 POST /api/v1/events，或直接 curl。</p>

      {showGraph && (
        <div style={{ margin: "12px 0", border: "1px solid var(--border)", borderRadius: 8, padding: 12 }}>
          {graph ? <MermaidDiagram source={graph.mermaid} /> : <p className="muted">加载中…</p>}
        </div>
      )}

      {isLoading && <p className="muted">加载中…</p>}

      <table>
        <thead>
          <tr>
            <th />
            <th>标题</th>
            <th>地区/行业</th>
            <th>状态</th>
            <th>创建时间</th>
          </tr>
        </thead>
        <tbody>
          {events?.map((event) => (
            <Fragment key={event.id}>
              <tr>
                <td>
                  <button
                    onClick={() =>
                      setExpandedEventId(expandedEventId === event.id ? null : event.id)
                    }
                  >
                    {expandedEventId === event.id ? "收起" : "详情"}
                  </button>
                </td>
                <td style={{ maxWidth: 400 }}>{event.title}</td>
                <td>
                  {event.region} / {event.industry}
                </td>
                <td>
                  <span className="status-badge">{statusLabel(event.status)}</span>
                </td>
                <td>{event.created_at}</td>
              </tr>
              {expandedEventId === event.id && (
                <tr>
                  <td colSpan={5}>
                    <EventDetailPanel eventId={event.id} />
                  </td>
                </tr>
              )}
            </Fragment>
          ))}
          {events?.length === 0 && (
            <tr>
              <td colSpan={5} className="muted">
                还没有事件
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
