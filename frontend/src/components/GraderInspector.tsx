"use client";

import { useMemo, useState } from "react";

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
      <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
        PENDING
      </span>
    );
  }
  if (evaln.relevant) {
    return (
      <span className="rounded bg-emerald-950 px-1.5 py-0.5 text-[10px] font-medium text-emerald-300">
        KEEP · {evaln.confidence.toFixed(2)}
      </span>
    );
  }
  return (
    <span className="rounded bg-rose-950 px-1.5 py-0.5 text-[10px] font-medium text-rose-300">
      FILTERED · {evaln.confidence.toFixed(2)}
    </span>
  );
}

function ChunkCard({ row }: { row: Row }) {
  const filtered = row.evaluation && !row.evaluation.relevant;
  const [open, setOpen] = useState(!filtered);

  return (
    <article
      className={`border border-slate-800 p-3 transition-opacity ${
        filtered && !open ? "opacity-45" : "opacity-100"
      } ${filtered ? "bg-slate-950/40" : "bg-slate-900/50"}`}
    >
      <button
        type="button"
        className="flex w-full items-start justify-between gap-2 text-left"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        <div className="min-w-0">
          <p className="truncate text-xs font-medium text-slate-100">
            {row.chunk.source_file}
            {row.chunk.section_header
              ? ` · ${row.chunk.section_header}`
              : ""}
          </p>
          <p className="mt-0.5 text-[10px] tabular-nums text-slate-500">
            RRF {row.chunk.rrf_score.toFixed(3)} · d#{row.chunk.dense_rank} ·
            s#{row.chunk.sparse_rank}
          </p>
        </div>
        {badge(row.evaluation)}
      </button>
      {open ? (
        <div className="mt-2 space-y-1.5">
          <p className="text-[11px] leading-relaxed text-slate-300">
            {row.chunk.preview_text}
          </p>
          {row.evaluation?.reasoning ? (
            <p className="text-[11px] italic text-slate-400">
              {row.evaluation.reasoning}
            </p>
          ) : null}
        </div>
      ) : null}
    </article>
  );
}

export function GraderInspector({ live }: { live: GraphLiveState }) {
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
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-400">
          Context &amp; grader
        </h2>
        {live.evaluations.length > 0 ? (
          <p className="text-[10px] tabular-nums text-slate-500">
            {kept} kept · {filtered} filtered
          </p>
        ) : live.chunks.length > 0 ? (
          <p className="text-[10px] text-slate-500">awaiting grade…</p>
        ) : null}
      </header>

      {rows.length === 0 ? (
        <p className="text-xs text-slate-500">
          Retrieved chunks appear here when hybrid search finishes.
        </p>
      ) : (
        <div className="min-h-0 flex-1 space-y-2 overflow-y-auto pr-1">
          {rows.map((row) => (
            <ChunkCard key={row.chunk.chunk_id} row={row} />
          ))}
        </div>
      )}
    </section>
  );
}
