"use client";

import { useAgentChat } from "../hooks/useAgentChat";
import { AgentFlowCanvas } from "./AgentFlowCanvas";
import { GraderInspector } from "./GraderInspector";
import { ThoughtTimeline } from "./ThoughtTimeline";

const PRESETS = [
  {
    label: "High-confidence match",
    query: "How does Gemini to Groq failover work after a 429?",
  },
  {
    label: "Ambiguous → rewrite",
    query: "What about the SLA xyz failover thing?",
  },
  {
    label: "Out-of-corpus → web",
    query: "Latest news on Qdrant hybrid RRF fusion outside our docs",
  },
];

export function ChatWorkbench() {
  const { messages, input, setInput, send, stop, streaming, error, graphLive } =
    useAgentChat();

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6 lg:flex-row lg:gap-6">
      <div className="flex min-h-0 flex-1 flex-col lg:max-w-[52%]">
        <header className="mb-6">
          <p className="text-sm tracking-wide text-zinc-500">Agentic CRAG</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-zinc-900 dark:text-zinc-50">
            Workbench
          </h1>
          <p className="mt-2 text-sm text-zinc-600 dark:text-zinc-400">
            Live agent timeline + streamed answer over typed SSE.
          </p>
        </header>

        <div className="mb-4 flex flex-wrap gap-2">
          {PRESETS.map((p) => (
            <button
              key={p.label}
              type="button"
              disabled={streaming}
              onClick={() => void send(p.query)}
              className="border border-zinc-300 bg-zinc-50 px-3 py-1.5 text-left text-xs text-zinc-800 hover:bg-zinc-100 disabled:opacity-50 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200 dark:hover:bg-zinc-800"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div className="flex-1 space-y-6 overflow-y-auto">
          {messages.length === 0 ? (
            <p className="text-sm text-zinc-500">
              Ask a question or pick a scenario above. Backend must be on{" "}
              <code className="text-zinc-700 dark:text-zinc-300">
                NEXT_PUBLIC_API_URL
              </code>{" "}
              (default http://localhost:8000).
            </p>
          ) : null}

          {messages.map((m) => (
            <article
              key={m.id}
              className={
                m.role === "user"
                  ? "ml-4 border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-800 dark:bg-zinc-900/60"
                  : "mr-4 border border-zinc-200 p-4 dark:border-zinc-800"
              }
            >
              <p className="mb-2 text-[11px] uppercase tracking-wider text-zinc-500">
                {m.role}
              </p>
              {m.role === "assistant" ? (
                <ThoughtTimeline steps={m.timeline} />
              ) : null}
              <div className="whitespace-pre-wrap text-sm leading-relaxed text-zinc-900 dark:text-zinc-100">
                {m.content ||
                  (streaming && m.role === "assistant" ? "…" : null)}
              </div>
              {m.verification ? (
                <p className="mt-3 text-xs text-zinc-500">
                  {m.verification.is_grounded ? "Verified" : "Partial"} ·{" "}
                  {m.verification.provider_used} ·{" "}
                  {m.verification.total_latency_ms}ms · confidence{" "}
                  {m.verification.confidence_score.toFixed(2)}
                </p>
              ) : null}
            </article>
          ))}
        </div>

        {error ? (
          <p
            className="mt-4 text-sm text-red-700 dark:text-red-400"
            role="alert"
          >
            {error}
          </p>
        ) : null}

        <form
          className="sticky bottom-0 mt-4 flex gap-2 border-t border-zinc-200 bg-[var(--background)] py-4 dark:border-zinc-800"
          onSubmit={(e) => {
            e.preventDefault();
            void send();
          }}
        >
          <label className="sr-only" htmlFor="query">
            Query
          </label>
          <input
            id="query"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask the agentic RAG system…"
            maxLength={2000}
            disabled={streaming}
            className="min-w-0 flex-1 border border-zinc-300 bg-white px-3 py-2 text-sm text-zinc-900 outline-none focus:border-zinc-500 dark:border-zinc-700 dark:bg-zinc-950 dark:text-zinc-100"
          />
          {streaming ? (
            <button
              type="button"
              onClick={stop}
              className="border border-zinc-400 px-4 py-2 text-sm text-zinc-800 dark:text-zinc-200"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              className="bg-zinc-900 px-4 py-2 text-sm text-white dark:bg-zinc-100 dark:text-zinc-900"
            >
              Send
            </button>
          )}
        </form>
      </div>

      <aside className="mt-8 flex w-full flex-col gap-4 border-t border-zinc-200 pt-6 dark:border-zinc-800 lg:mt-0 lg:w-[48%] lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
        <div>
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
            Live execution graph
          </h2>
          <AgentFlowCanvas live={graphLive} />
        </div>
        <GraderInspector live={graphLive} />
      </aside>
    </div>
  );
}
