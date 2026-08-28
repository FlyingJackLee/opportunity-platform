import mermaid from "mermaid";
import { useEffect, useId, useState } from "react";

mermaid.initialize({ startOnLoad: false, theme: "neutral" });

export default function MermaidDiagram({ source }: { source: string }) {
  const id = useId().replace(/:/g, "-");
  const [svg, setSvg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    mermaid
      .render(`mermaid-${id}`, source)
      .then(({ svg }) => {
        if (!cancelled) setSvg(svg);
      })
      .catch((err) => {
        if (!cancelled) setError(String(err));
      });
    return () => {
      cancelled = true;
    };
  }, [id, source]);

  if (error) return <div className="error-banner">流程图渲染失败: {error}</div>;
  if (!svg) return <p className="muted">渲染流程图…</p>;
  // eslint-disable-next-line react/no-danger -- mermaid.render's own SVG output, not user input
  return <div dangerouslySetInnerHTML={{ __html: svg }} />;
}
