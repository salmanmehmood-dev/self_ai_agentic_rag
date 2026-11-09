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
    <ol className="mb-3 space-y-1.5 border-l-2 border-border pl-3 font-mono text-[11px] text-muted-foreground">
      {steps.map((step, idx) => (
        <li
          key={`${step.node}-${idx}`}
          className="animate-timeline-step relative"
          style={{ animationDelay: `${idx * 40}ms` }}
        >
          <span className="absolute -left-[0.97rem] top-1.5 h-1.5 w-1.5 bg-accent" />
          <span className="font-medium text-foreground">
            {LABELS[step.node] ?? step.node}
          </span>
          {step.latency_ms != null ? (
            <span className="ml-1 tabular-nums text-accent">
              : {step.latency_ms}ms
            </span>
          ) : null}
          <span className="ml-1">— {step.summary}</span>
        </li>
      ))}
    </ol>
  );
}
