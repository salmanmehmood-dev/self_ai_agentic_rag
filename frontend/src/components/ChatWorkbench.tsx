"use client";

import { useCallback, useState } from "react";

import { useAgentChat } from "../hooks/useAgentChat";
import { AgentFlowCanvas } from "./AgentFlowCanvas";
import { CitedAnswer } from "./CitedAnswer";
import { EvalsDrawer } from "./EvalsDrawer";
import { GraderInspector } from "./GraderInspector";
import { ThoughtTimeline } from "./ThoughtTimeline";

const PRESETS = [
  {
    n: "01",
    title: "Failover path",
    blurb: "High-confidence corpus hit",
    query: "How does Gemini to Groq failover work after a 429?",
  },
  {
    n: "02",
    title: "Rewrite loop",
    blurb: "Ambiguous → query rewrite",
    query: "What about the SLA xyzq9 obfuscated doodad failover thing?",
  },
  {
    n: "03",
    title: "Web fallback",
    blurb: "Out-of-corpus → live search",
    query:
      "Who won the most recent FIFA Women's World Cup and what was the final score?",
  },
];

export function ChatWorkbench() {
  const {
    messages,
    input,
    setInput,
    send,
    stop,
    streaming,
    userError,
    clearError,
    showDevErrors,
    graphLive,
  } = useAgentChat();
  const [focusCiteIndex, setFocusCiteIndex] = useState<number | null>(null);
  const [evalsOpen, setEvalsOpen] = useState(false);

  const onCite = useCallback((index: number) => {
    setFocusCiteIndex(index);
  }, []);

  const statusLabel = streaming
    ? "Streaming"
    : graphLive.activeNode
      ? "Live"
      : "Idle";
  const statusClass = streaming
    ? "border-accent-hot bg-accent-hot/10 text-accent-hot"
    : graphLive.activeNode
      ? "border-accent bg-accent/10 text-accent"
      : "border-border bg-muted text-muted-foreground";

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col px-4 py-6 lg:flex-row lg:gap-8">
      <div className="flex min-h-0 flex-1 flex-col lg:max-w-[52%]">
        <header className="animate-instrument-fade-up mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="font-mono text-[11px] uppercase tracking-[0.18em] text-accent">
              Instrument panel
            </p>
            <h1 className="mt-1 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
              Agentic CRAG
            </h1>
            <p className="mt-2 max-w-md text-sm text-muted-foreground">
              Corrective RAG you can watch: timeline, grader, failover, citations.
            </p>
          </div>
          <div className="flex shrink-0 flex-col items-end gap-2">
            <span
              className={`inline-flex items-center border px-2 py-1 font-mono text-[10px] uppercase tracking-wider ${statusClass}`}
              aria-live="polite"
            >
              {statusLabel}
            </span>
            <button
              type="button"
              onClick={() => setEvalsOpen(true)}
              className="cursor-pointer border border-border bg-surface px-3 py-1.5 text-xs text-foreground transition-colors duration-200 hover:border-accent hover:text-accent"
            >
              View evals
            </button>
          </div>
        </header>

        <div className="mb-5 grid gap-2 sm:grid-cols-3">
          {PRESETS.map((p, i) => (
            <button
              key={p.n}
              type="button"
              disabled={streaming}
              onClick={() => {
                setFocusCiteIndex(null);
                void send(p.query);
              }}
              style={{ animationDelay: `${80 + i * 70}ms` }}
              className="animate-instrument-stagger cursor-pointer border border-border bg-surface p-3 text-left transition-colors duration-200 hover:border-accent disabled:cursor-not-allowed disabled:opacity-50"
            >
              <span className="font-mono text-[10px] text-accent">{p.n}</span>
              <span className="mt-1 block text-sm font-medium text-foreground">
                {p.title}
              </span>
              <span className="mt-0.5 block text-[11px] text-muted-foreground">
                {p.blurb}
              </span>
            </button>
          ))}
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="border border-dashed border-border bg-surface/80 p-5">
              <p className="text-sm font-medium text-foreground">
                Run a scenario to start the demo
              </p>
              <p className="mt-1 text-sm text-muted-foreground">
                You will see the agent timeline, live graph, chunk grades, and
                cited answer stream in one pass.
              </p>
              <p className="mt-3 font-mono text-[10px] text-muted-foreground">
                API · NEXT_PUBLIC_API_URL · default http://localhost:8000
              </p>
            </div>
          ) : null}

          {messages.map((m) => (
            <article
              key={m.id}
              className={
                m.role === "user"
                  ? "ml-3 border-2 border-border bg-muted/40 p-4"
                  : "mr-3 border border-border bg-surface p-4"
              }
            >
              <p className="mb-2 font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground">
                {m.role === "user" ? "query" : "agent"}
              </p>
              {m.role === "assistant" ? (
                <ThoughtTimeline steps={m.timeline} />
              ) : null}
              {m.role === "assistant" ? (
                <CitedAnswer
                  content={m.content}
                  chunks={graphLive.chunks}
                  evaluations={graphLive.evaluations}
                  onCite={onCite}
                  streaming={streaming}
                />
              ) : (
                <div className="whitespace-pre-wrap text-sm leading-relaxed text-foreground">
                  {m.content}
                </div>
              )}
              {m.notices?.length ? (
                <ul className="mt-2 space-y-2" aria-live="polite">
                  {m.notices.map((n, i) => (
                    <li
                      key={`${n.code}-${i}`}
                      className="border border-warn/50 bg-warn/10 px-3 py-2 text-xs text-foreground"
                    >
                      <p className="font-medium text-warn">{n.title}</p>
                      <p className="mt-0.5 text-muted-foreground">{n.message}</p>
                      {showDevErrors ? (
                        <details className="mt-1 font-mono text-[10px] opacity-70">
                          <summary>
                            Developer detail ({n.layer ?? "backend"})
                          </summary>
                          <code className="break-all">
                            [{n.code}] {n.technical}
                          </code>
                        </details>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
              {m.verification ? (
                <p
                  className={
                    m.verification.status === "partial_verification"
                      ? "mt-3 inline-flex items-center gap-2 border border-warn/60 bg-warn/10 px-2 py-1 font-mono text-[11px] text-warn"
                      : m.verification.is_grounded
                        ? "mt-3 font-mono text-[11px] text-ok"
                        : "mt-3 font-mono text-[11px] text-muted-foreground"
                  }
                >
                  {m.verification.status === "partial_verification"
                    ? "Partial verification — some claims unchecked"
                    : m.verification.is_grounded
                      ? "Verified against sources"
                      : "Needs review"}
                  {showDevErrors ? (
                    <>
                      {" "}
                      · {m.verification.provider_used} ·{" "}
                      {m.verification.total_latency_ms}ms · confidence{" "}
                      {m.verification.confidence_score.toFixed(2)}
                    </>
                  ) : null}
                </p>
              ) : null}
            </article>
          ))}
        </div>

        {userError ? (
          <div
            className="mt-4 border border-danger/50 bg-danger/10 px-3 py-2 text-sm text-foreground"
            role="alert"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-medium text-danger">{userError.title}</p>
                <p className="mt-0.5 text-xs text-muted-foreground">
                  {userError.message}
                </p>
                {showDevErrors ? (
                  <details className="mt-1 font-mono text-[10px] opacity-70">
                    <summary>
                      Developer detail ({userError.layer ?? "unknown"})
                    </summary>
                    <code className="break-all">
                      [{userError.code}] {userError.technical}
                    </code>
                  </details>
                ) : null}
              </div>
              <button
                type="button"
                onClick={clearError}
                className="cursor-pointer shrink-0 text-xs underline opacity-80 hover:opacity-100"
              >
                Dismiss
              </button>
            </div>
          </div>
        ) : null}

        <form
          className="sticky bottom-0 mt-4 flex gap-2 border-t border-border bg-background py-4"
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
            className="min-w-0 flex-1 border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none transition-colors duration-200 focus:border-accent disabled:opacity-60"
          />
          {streaming ? (
            <button
              type="button"
              onClick={stop}
              className="cursor-pointer border border-accent-hot bg-accent-hot px-4 py-2 text-sm font-medium text-white transition-opacity duration-200 hover:opacity-90"
            >
              Stop
            </button>
          ) : (
            <button
              type="submit"
              className="cursor-pointer bg-accent px-4 py-2 text-sm font-medium text-on-accent transition-opacity duration-200 hover:opacity-90"
            >
              Send
            </button>
          )}
        </form>
      </div>

      <aside className="mt-8 flex w-full flex-col gap-5 border-t border-border pt-6 lg:mt-0 lg:w-[48%] lg:border-l lg:border-t-0 lg:pl-8 lg:pt-0">
        <div>
          <h2 className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
            Live execution
          </h2>
          <AgentFlowCanvas live={graphLive} />
        </div>
        <GraderInspector live={graphLive} focusCiteIndex={focusCiteIndex} />
      </aside>

      <EvalsDrawer open={evalsOpen} onClose={() => setEvalsOpen(false)} />
    </div>
  );
}
