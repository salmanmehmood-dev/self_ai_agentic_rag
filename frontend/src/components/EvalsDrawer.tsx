"use client";

import { useEffect, useState } from "react";

type Metric = { key: string; naive: number; agentic: number };
type GoldenRow = { id: number; query: string; latency_ms: number; pass: boolean };

type BenchmarksPayload = {
  source?: string;
  metrics?: Metric[];
  golden_sample?: GoldenRow[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

const FALLBACK_METRICS: Metric[] = [
  { key: "Context Precision", naive: 0.62, agentic: 0.84 },
  { key: "Context Recall", naive: 0.71, agentic: 0.88 },
  { key: "Faithfulness", naive: 0.68, agentic: 0.91 },
  { key: "Answer Relevance", naive: 0.74, agentic: 0.89 },
];

function polar(cx: number, cy: number, r: number, angle: number) {
  const a = angle - Math.PI / 2;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

function RadarChart({ metrics }: { metrics: Metric[] }) {
  const cx = 120;
  const cy = 110;
  const maxR = 80;
  const n = metrics.length || 1;

  const ring = (t: number) =>
    metrics
      .map((_, i) => {
        const p = polar(cx, cy, maxR * t, (i / n) * Math.PI * 2);
        return `${p.x},${p.y}`;
      })
      .join(" ");

  const series = (values: number[]) =>
    values
      .map((v, i) => {
        const p = polar(cx, cy, maxR * v, (i / n) * Math.PI * 2);
        return `${p.x},${p.y}`;
      })
      .join(" ");

  return (
    <svg viewBox="0 0 240 230" className="mx-auto h-52 w-full max-w-xs" aria-hidden>
      {[0.25, 0.5, 0.75, 1].map((t) => (
        <polygon
          key={t}
          points={ring(t)}
          fill="none"
          stroke="#9cc5bc"
          strokeWidth={1}
        />
      ))}
      {metrics.map((m, i) => {
        const p = polar(cx, cy, maxR + 16, (i / n) * Math.PI * 2);
        return (
          <text
            key={m.key}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            className="fill-[var(--muted-foreground)]"
            fontSize={8}
          >
            {m.key.split(" ")[0]}
          </text>
        );
      })}
      <polygon
        points={series(metrics.map((m) => m.naive))}
        fill="rgba(61,92,86,0.12)"
        stroke="#3d5c56"
        strokeWidth={1.5}
      />
      <polygon
        points={series(metrics.map((m) => m.agentic))}
        fill="rgba(13,148,136,0.18)"
        stroke="#0d9488"
        strokeWidth={1.5}
      />
    </svg>
  );
}

export function EvalsDrawer({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const [metrics, setMetrics] = useState<Metric[]>(FALLBACK_METRICS);
  const [sample, setSample] = useState<GoldenRow[]>([]);
  const [source, setSource] = useState("loading");

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/benchmarks`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = (await res.json()) as BenchmarksPayload;
        if (cancelled) return;
        if (data.metrics?.length) setMetrics(data.metrics);
        if (data.golden_sample?.length) setSample(data.golden_sample);
        setSource(data.source || "api");
      } catch (err) {
        console.error("[agentic-crag] benchmarks fetch failed", err);
        if (!cancelled) setSource("offline preview");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-40 flex justify-end"
      role="dialog"
      aria-modal
      aria-label="Evals and benchmarks"
    >
      <button
        type="button"
        className="absolute inset-0 cursor-pointer bg-foreground/40"
        aria-label="Close evals drawer"
        onClick={onClose}
      />
      <aside className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-border bg-surface shadow-xl">
        <header className="flex items-center justify-between border-b border-border px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-foreground">
              Evals &amp; benchmarks
            </h2>
            <p className="font-mono text-[11px] text-muted-foreground">
              Source: {source} (golden offline / Ragas snapshot)
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="cursor-pointer border border-border px-2 py-1 text-xs text-foreground transition-colors duration-200 hover:border-accent hover:text-accent"
          >
            Close
          </button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4">
          <section>
            <h3 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Naive dense vs agentic CRAG
            </h3>
            <RadarChart metrics={metrics} />
            <div className="mt-1 flex justify-center gap-4 font-mono text-[10px] text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-2 w-2 bg-muted-foreground" />{" "}
                Naive dense
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-2 w-2 bg-accent" /> Agentic CRAG
              </span>
            </div>
            <ul className="mt-3 space-y-1 font-mono text-[11px] text-muted-foreground">
              {metrics.map((m) => (
                <li key={m.key} className="flex justify-between tabular-nums">
                  <span>{m.key}</span>
                  <span>
                    {m.naive.toFixed(2)} →{" "}
                    <span className="text-accent">{m.agentic.toFixed(2)}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h3 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
              Golden queries (sample)
            </h3>
            <div className="overflow-x-auto border border-border">
              <table className="w-full text-left text-[11px]">
                <thead className="bg-muted text-muted-foreground">
                  <tr>
                    <th className="px-2 py-1.5 font-medium">#</th>
                    <th className="px-2 py-1.5 font-medium">Query</th>
                    <th className="px-2 py-1.5 font-medium">ms</th>
                    <th className="px-2 py-1.5 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {sample.map((q) => (
                    <tr
                      key={q.id}
                      className="border-t border-border text-foreground"
                    >
                      <td className="px-2 py-1.5 font-mono tabular-nums text-muted-foreground">
                        {q.id}
                      </td>
                      <td className="max-w-[12rem] truncate px-2 py-1.5">
                        {q.query}
                      </td>
                      <td className="px-2 py-1.5 font-mono tabular-nums">
                        {q.latency_ms}
                      </td>
                      <td className="px-2 py-1.5 font-mono">
                        {q.pass ? (
                          <span className="text-ok">pass</span>
                        ) : (
                          <span className="text-danger">fail</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </aside>
    </div>
  );
}
