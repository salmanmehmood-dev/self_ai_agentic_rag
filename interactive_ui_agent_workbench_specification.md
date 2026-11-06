# Interactive Frontend Workbench & SSE Protocol Specification

## 1. Design Philosophy: "Show the Agent Thinking"
Recruiters and senior engineers evaluating an AI portfolio project need immediate visual proof that the system is executing a cyclic, self-correcting state machine rather than calling a wrapper around ChatGPT.

The UI is designed as a **Three-Pane Split-Screen Agent Observability Workbench** inspired by modern developer tools (Linear, Vercel Logs, LangGraph Studio) and aligned with **AG-UI (Agent-User Interaction Protocol)** principles.

---

## 2. Ecosystem & Open-Source Libraries
* **Framework**: Next.js 15 (App Router, TypeScript strict mode)
* **Styling & Primitives**: Tailwind CSS v4 + `shadcn/ui` (Radix UI primitives)
* **Live State Machine Canvas**: `@xyflow/react` (React Flow v12) with custom animated SVG edges
* **Micro-Animations**: `framer-motion` (spring physics for reasoning steps & drawer transitions)
* **Stream Parsing**: `@microsoft/fetch-event-source` (supports POST payloads with reconnection logic)
* **Markdown & Code Highlighting**: `react-markdown` + `remark-gfm` + `shiki`
* **Telemetry Visualization**: `recharts` (Radar & Bar charts for Ragas Evaluation Drawer)

---

## 3. Typed Server-Sent Events (SSE) Wire Protocol

All communication over `POST /api/v1/chat/stream` uses `Content-Type: text/event-stream`. Every event carries a strict JSON payload discriminated by `event`:

```typescript
export type AgentSSEEvent =
  | {
      event: "node_transition";
      data: {
        node: "router" | "retriever" | "grader" | "rewriter" | "web_search" | "synthesizer" | "verifier";
        status: "running" | "completed" | "skipped" | "fallback";
        latency_ms?: number;
        summary: string;
      };
    }
  | {
      event: "retrieval_results";
      data: {
        query_used: string;
        attempt: number;
        chunks: Array<{
          chunk_id: string;
          source_file: string;
          section_header: string;
          rrf_score: number;
          dense_rank: number;
          sparse_rank: number;
          preview_text: string;
        }>;
      };
    }
  | {
      event: "grading_verdict";
      data: {
        passed_count: number;
        rejected_count: number;
        evaluations: Array<{
          chunk_id: string;
          relevant: boolean;
          confidence: number;
          reasoning: string;
        }>;
      };
    }
  | {
      event: "query_rewritten";
      data: {
        previous_query: string;
        new_query: string;
        reason: string;
        rewrite_count: number;
      };
    }
  | {
      event: "token_chunk";
      data: {
        delta: string;
      };
    }
  | {
      event: "verification_complete";
      data: {
        is_grounded: boolean;
        addresses_query: boolean;
        confidence_score: number;
        provider_used: "gemini-2.5-flash" | "groq-llama-3.3-70b";
        total_latency_ms: number;
      };
    };
```

---

## 4. Core Interactive UI Components

### 4.1 Left/Center Pane: Conversational Synthesis & Thought Accordion
1. **Zero-Friction Recruiter Preset Bar**:
   * Above the input box, display 3 one-click scenario pills:
     * `[🟢 Scenario 1: Direct High-Confidence Match]` — Shows single-pass hybrid retrieval and verified synthesis.
     * `[🟡 Scenario 2: Ambiguous Query → Rewrite Loop]` — Demonstrates Grader rejecting noisy chunks, Node 4 rewriting the query, and Node 2 succeeding on attempt #2.
     * `[🔵 Scenario 3: Out-of-Corpus → Live Web Fallback]` — Triggers 2 local misses followed by autonomous Tavily/DuckDuckGo fallback.
2. **Collapsible Chain-of-Action Timeline**:
   * Inline above every assistant message, render a sleek vertical stepper showing exact node durations (`Router: 310ms` $\rightarrow$ `Hybrid RRF: 140ms` $\rightarrow$ `Grader: 480ms [3/5 kept]`).
3. **Interactive Citation Badges (`[1]`, `[2]`)**:
   * Hovering over `[1]` displays a floating popover with the source filename and confidence score.
   * Clicking `[1]` opens and scrolls the Right Rail Inspector to that exact chunk with highlighted text spans.

### 4.2 Right Pane (Top): Live React Flow Execution Graph
* Renders the 7-node CRAG topology using `@xyflow/react`.
* **Visual States**:
  * **Idle Node**: Muted slate border (`border-slate-800 bg-slate-900/60`).
  * **Active Node**: Glowing emerald/indigo pulse ring with animated SVG dashed edge (`stroke-dasharray` animation).
  * **Loopback Edge (Query Rewrite)**: Lights up in amber when `query_rewritten` fires, visually animating the cycle back to `Hybrid Retriever`.
  * **Web Fallback Node**: Pulses cyan when local documents fail threshold checks.

### 4.3 Right Pane (Bottom): Live Context & Grader Inspector
* Displays retrieved chunks in real time as soon as `retrieval_results` arrives—even before the final answer is synthesized.
* When `grading_verdict` arrives, cards animate:
  * **Accepted Chunks ($\ge 0.70$)**: Emerald badge `[KEEP • 0.92]` with the LLM Grader's 1-sentence justification.
  * **Rejected Chunks ($< 0.70$)**: Collapsed/dimmed with a rose badge `[FILTERED • 0.35]` (expandable on click so recruiters can inspect what noise was filtered out).

### 4.4 Header Modal: Ragas Evaluation & Telemetry Dashboard
* A top-right button `[📊 View Evals & Benchmarks]` opens a slide-over sheet showing:
  * Radar chart comparing **Naive Dense RAG** vs. **This Agentic CRAG System** across 4 metrics: *Context Precision*, *Context Recall*, *Faithfulness*, and *Answer Relevance*.
  * Table of the 30 golden test queries with latency and pass/fail badges.