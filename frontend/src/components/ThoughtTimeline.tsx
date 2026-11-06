"use client";

import type { TimelineStep } from "../lib/sse-types";

const LABELS: Record<string, string> = {
  router: "Router",
  retriever: "Hybrid RRF",
  grader: "Grader",
  rewriter: "Rewriter",
  web_search: "Web fallback",
  synthesizer: "Synthesizer",
  verifier: "Verifier",
};

export function ThoughtTimeline({ steps }: { steps: TimelineStep[] }) {
  if (steps.length === 0) return null;

  return (
    <ol className="mb-3 space-y-1.5 border-l border-zinc-300 pl-3 text-xs text-zinc-600 dark:border-zinc-700 dark:text-zinc-400">
      {steps.map((step, idx) => (
        <li key={`${step.node}-${idx}`} className="relative">
          <span className="absolute -left-[0.91rem] top-1.5 h-1.5 w-1.5 rounded-full bg-emerald-600" />
          <span className="font-medium text-zinc-800 dark:text-zinc-200">
            {LABELS[step.node] ?? step.node}
          </span>
          {step.latency_ms != null ? (
            <span className="ml-1 tabular-nums">: {step.latency_ms}ms</span>
          ) : null}
          <span className="ml-1 text-zinc-500">— {step.summary}</span>
        </li>
      ))}
    </ol>
  );
}
