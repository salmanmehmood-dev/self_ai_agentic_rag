"use client";

import { useMemo, useState } from "react";

import type { GradeEvaluation, RetrievalChunk } from "../lib/sse-types";

type CiteMeta = {
  index: number;
  chunk?: RetrievalChunk;
  evaluation?: GradeEvaluation;
};

function parseParts(content: string): Array<
  { kind: "text"; value: string } | { kind: "cite"; index: number }
> {
  const parts: Array<
    { kind: "text"; value: string } | { kind: "cite"; index: number }
  > = [];
  const re = /\[(\d+)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(content)) !== null) {
    if (m.index > last) {
      parts.push({ kind: "text", value: content.slice(last, m.index) });
    }
    parts.push({ kind: "cite", index: Number(m[1]) });
    last = m.index + m[0].length;
  }
  if (last < content.length) {
    parts.push({ kind: "text", value: content.slice(last) });
  }
  return parts;
}

function CitationBadge({
  meta,
  onCite,
}: {
  meta: CiteMeta;
  onCite: (index: number) => void;
}) {
  const [hover, setHover] = useState(false);
  const source = meta.chunk?.source_file ?? `chunk ${meta.index}`;
  const confidence = meta.evaluation?.confidence;

  return (
    <span
      className="relative inline-block"
      onMouseEnter={() => setHover(true)}
      onMouseLeave={() => setHover(false)}
    >
      <button
        type="button"
        onClick={() => onCite(meta.index)}
        className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded bg-emerald-100 px-1 align-super text-[10px] font-semibold text-emerald-900 hover:bg-emerald-200 dark:bg-emerald-950 dark:text-emerald-300 dark:hover:bg-emerald-900"
        aria-label={`Citation ${meta.index}: ${source}`}
      >
        {meta.index}
      </button>
      {hover ? (
        <span
          role="tooltip"
          className="absolute bottom-full left-1/2 z-20 mb-1 w-48 -translate-x-1/2 border border-zinc-700 bg-zinc-950 px-2 py-1.5 text-[10px] leading-snug text-zinc-200 shadow-lg"
        >
          <span className="block truncate font-medium">{source}</span>
          {confidence != null ? (
            <span className="mt-0.5 block tabular-nums text-zinc-400">
              confidence {confidence.toFixed(2)}
            </span>
          ) : (
            <span className="mt-0.5 block text-zinc-500">open in inspector</span>
          )}
        </span>
      ) : null}
    </span>
  );
}

export function CitedAnswer({
  content,
  chunks,
  evaluations,
  onCite,
  streaming,
}: {
  content: string;
  chunks: RetrievalChunk[];
  evaluations: GradeEvaluation[];
  onCite: (index: number) => void;
  streaming?: boolean;
}) {
  const parts = useMemo(() => parseParts(content), [content]);
  const evalById = useMemo(
    () => new Map(evaluations.map((e) => [e.chunk_id, e] as const)),
    [evaluations],
  );

  if (!content) {
    return streaming ? <>…</> : null;
  }

  return (
    <div className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-900 dark:text-zinc-100">
      {parts.map((part, i) => {
        if (part.kind === "text") {
          return <span key={i}>{part.value}</span>;
        }
        const chunk = chunks[part.index - 1];
        return (
          <CitationBadge
            key={`c-${part.index}-${i}`}
            meta={{
              index: part.index,
              chunk,
              evaluation: chunk ? evalById.get(chunk.chunk_id) : undefined,
            }}
            onCite={onCite}
          />
        );
      })}
    </div>
  );
}
