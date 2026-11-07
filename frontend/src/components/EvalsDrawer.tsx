"use client";

import { useEffect } from "react";

/** Shell metrics — Phase 9 fills from golden eval runs. */
const METRICS = [
  { key: "Context Precision", naive: 0.62, agentic: 0.84 },
  { key: "Context Recall", naive: 0.71, agentic: 0.88 },
  { key: "Faithfulness", naive: 0.68, agentic: 0.91 },
  { key: "Answer Relevance", naive: 0.74, agentic: 0.89 },
] as const;

const SAMPLE_QUERIES = [
  { id: 1, query: "Gemini→Groq failover after 429", latency_ms: 1840, pass: true },
  { id: 2, query: "Hybrid RRF dense+sparse fusion", latency_ms: 1520, pass: true },
  { id: 3, query: "Ambiguous SLA rewrite path", latency_ms: 3210, pass: true },
  { id: 4, query: "Out-of-corpus web fallback", latency_ms: 4100, pass: true },
  { id: 5, query: "Empty collection cold start", latency_ms: 890, pass: false },
  { id: 6, query: "Citation index bounds strip", latency_ms: 2010, pass: true },
] as const;

function polar(cx: number, cy: number, r: number, angle: number) {
  const a = angle - Math.PI / 2;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}

function RadarChart() {
  const cx = 120;
  const cy = 110;
  const maxR = 80;
  const n = METRICS.length;

  const ring = (t: number) =>
    METRICS.map((_, i) => {
      const p = polar(cx, cy, maxR * t, (i / n) * Math.PI * 2);
      return `${p.x},${p.y}`;
    }).join(" ");

  const series = (values: readonly number[]) =>
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
          stroke="#334155"
          strokeWidth={1}
        />
      ))}
      {METRICS.map((m, i) => {
        const p = polar(cx, cy, maxR + 16, (i / n) * Math.PI * 2);
        return (
          <text
            key={m.key}
            x={p.x}
            y={p.y}
            textAnchor="middle"
            className="fill-slate-400"
            fontSize={8}
          >
            {m.key.split(" ")[0]}
          </text>
        );
      })}
      <polygon
        points={series(METRICS.map((m) => m.naive))}
        fill="rgba(148,163,184,0.2)"
        stroke="#94a3b8"
        strokeWidth={1.5}
      />
      <polygon
        points={series(METRICS.map((m) => m.agentic))}
        fill="rgba(52,211,153,0.2)"
        stroke="#34d399"
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
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 flex justify-end" role="dialog" aria-modal aria-label="Evals and benchmarks">
      <button
        type="button"
        className="absolute inset-0 bg-black/50"
        aria-label="Close evals drawer"
        onClick={onClose}
      />
      <aside className="relative z-10 flex h-full w-full max-w-md flex-col border-l border-slate-800 bg-slate-950 shadow-2xl">
        <header className="flex items-center justify-between border-b border-slate-800 px-4 py-3">
          <div>
            <h2 className="text-sm font-semibold text-slate-100">
              Evals &amp; benchmarks
            </h2>
            <p className="text-[11px] text-slate-500">
              Shell preview — Phase 9 wires live Ragas runs.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-900"
          >
            Close
          </button>
        </header>

        <div className="flex-1 space-y-6 overflow-y-auto px-4 py-4">
          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Naive dense vs agentic CRAG
            </h3>
            <RadarChart />
            <div className="mt-1 flex justify-center gap-4 text-[10px] text-slate-400">
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-2 w-2 bg-slate-400" /> Naive dense
              </span>
              <span className="inline-flex items-center gap-1">
                <span className="inline-block h-2 w-2 bg-emerald-400" /> Agentic CRAG
              </span>
            </div>
            <ul className="mt-3 space-y-1 text-[11px] text-slate-400">
              {METRICS.map((m) => (
                <li key={m.key} className="flex justify-between tabular-nums">
                  <span>{m.key}</span>
                  <span>
                    {m.naive.toFixed(2)} →{" "}
                    <span className="text-emerald-400">{m.agentic.toFixed(2)}</span>
                  </span>
                </li>
              ))}
            </ul>
          </section>

          <section>
            <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
              Golden queries (sample)
            </h3>
            <div className="overflow-x-auto border border-slate-800">
              <table className="w-full text-left text-[11px]">
                <thead className="bg-slate-900 text-slate-400">
                  <tr>
                    <th className="px-2 py-1.5 font-medium">#</th>
                    <th className="px-2 py-1.5 font-medium">Query</th>
                    <th className="px-2 py-1.5 font-medium">ms</th>
                    <th className="px-2 py-1.5 font-medium">Result</th>
                  </tr>
                </thead>
                <tbody>
                  {SAMPLE_QUERIES.map((q) => (
                    <tr key={q.id} className="border-t border-slate-800 text-slate-300">
                      <td className="px-2 py-1.5 tabular-nums text-slate-500">
                        {q.id}
                      </td>
                      <td className="max-w-[12rem] truncate px-2 py-1.5">
                        {q.query}
                      </td>
                      <td className="px-2 py-1.5 tabular-nums">{q.latency_ms}</td>
                      <td className="px-2 py-1.5">
                        {q.pass ? (
                          <span className="text-emerald-400">pass</span>
                        ) : (
                          <span className="text-rose-400">fail</span>
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
