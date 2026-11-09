"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type {
  GradeEvaluation,
  GraphLiveState,
  RetrievalChunk,
} from "../lib/sse-types";

type Row = {
  chunk: RetrievalChunk;
  evaluation?: GradeEvaluation;
};

function badge(evaln: GradeEvaluation | undefined) {
  if (!evaln) {
    return (
      <span className="border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">
        PENDING
      </span>
    );
  }
  if (evaln.relevant) {
    return (
      <span className="border border-ok/40 bg-ok/10 px-1.5 py-0.5 font-mono text-[10px] font-medium text-ok">
        KEEP · {evaln.confidence.toFixed(2)}
      </span>
    );
  }
  return (
    <span className="border border-danger/40 bg-danger/10 px-1.5 py-0.5 font-mono text-[10px] font-medium text-danger">
      FILTERED · {evaln.confidence.toFixed(2)}
    </span>
  );
}

function ChunkCard({
  row,
  focused,
  citeIndex,
}: {
  row: Row;
  focused: boolean;
  citeIndex: number;
}) {
  const filtered = row.evaluation && !row.evaluation.relevant;
  const [open, setOpen] = useState(!filtered || focused);
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!focused) return;
    setOpen(true);
    ref.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [focused]);

  return (
    <article
      ref={ref}
      id={`inspector-chunk-${citeIndex}`}
      data-chunk-id={row.chunk.chunk_id}
      className={`border p-3 transition-colors duration-200 ${
        focused
          ? "border-accent bg-accent/10"
          : "border-border bg-surface"
      } ${filtered && !open && !focused ? "opacity-45" : "opacity-100"}`}
    >
      <button
        type="button"
        className="flex w-full cursor-pointer items-start justify-between gap-2 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-foreground">
            <span className="mr-1 font-mono text-muted-foreground">
              [{citeIndex}]
            </span>
            {row.chunk.source_file}
            {row.chunk.section_header
              ? ` · ${row.chunk.section_header}`
              : ""}
          </p>
          <p className="mt-0.5 font-mono text-[10px] tabular-nums text-muted-foreground">
            RRF {row.chunk.rrf_score.toFixed(3)} · d#{row.chunk.dense_rank} ·
            s#{row.chunk.sparse_rank}
          </p>
        </div>
        {badge(row.evaluation)}
      </button>
      {open ? (
        <div className="mt-2 space-y-1.5">
          <p
            className={`text-[11px] leading-relaxed text-muted-foreground ${
              focused ? "bg-accent/10 px-1 py-0.5 text-foreground" : ""
            }`}
          >
            {row.chunk.preview_text}
          </p>
          {row.evaluation?.reasoning ? (
            <p className="text-[11px] italic text-muted-foreground">
              {row.evaluation.reasoning}
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

export function GraderInspector({
  live,
  focusCiteIndex,
}: {
  live: GraphLiveState;
  focusCiteIndex: number | null;
}) {
  const rows = useMemo(() => {
    const byId = new Map(
      live.evaluations.map((e) => [e.chunk_id, e] as const),
    );
    return live.chunks.map((chunk) => ({
      chunk,
      evaluation: byId.get(chunk.chunk_id),
    }));
  }, [live.chunks, live.evaluations]);

  const kept = live.evaluations.filter((e) => e.relevant).length;
  const filtered = live.evaluations.filter((e) => !e.relevant).length;

  return (
    <section className="flex min-h-0 flex-1 flex-col">
      <header className="mb-2 flex items-baseline justify-between gap-2">
        <h2 className="font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
          Chunk grader
        </h2>
        {live.evaluations.length > 0 ? (
          <p className="font-mono text-[10px] tabular-nums text-muted-foreground">
            {kept} kept · {filtered} filtered
          </p>
        ) : live.chunks.length > 0 ? (
          <p className="font-mono text-[10px] text-muted-foreground">
            awaiting grade…
          </p>
        ) : null}
      </header>

      {rows.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          Retrieved chunks appear here when hybrid search finishes.
        </p>
      ) : (
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {rows.map((row, i) => (
            <ChunkCard
              key={row.chunk.chunk_id}
              row={row}
              citeIndex={i + 1}
              focused={focusCiteIndex === i + 1}
            />
          ))}
        </div>
      )}
    </section>
  );
}
