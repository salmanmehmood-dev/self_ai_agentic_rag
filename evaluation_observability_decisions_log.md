# Corrective & Self-Reflective Agentic RAG — Architecture Specification (HLD & LLD)

## 1. Executive Summary

This system implements an enterprise-grade **Corrective & Self-Reflective Retrieval-Augmented Generation (CRAG + Self-RAG)** architecture. Unlike naive linear pipelines ($Query \rightarrow Retrieve \rightarrow Generate$), this cyclic state machine evaluates retrieved context relevance, autonomously rewrites suboptimal queries, falls back to live web search when local corpora fail, and verifies final syntheses against source documents to prevent factual hallucinations—operating entirely on zero-cost API tiers.

## 2. High-Level Design (HLD)

### 2.1 Cyclic State Graph Topology

```
                  ┌────────────────────────────────────┐
                  │   Client Request (POST /api/chat)  │
                  └─────────────────┬──────────────────┘
                                    │
                                    ▼
                  ┌────────────────────────────────────┐
                  │   Node 1: Sanitizer & Router       │
                  │   (Guardrails + Intent Classifier) │
                  └────────┬──────────────────┬────────┘
           route=="direct" │                  │ route=="rag"
                           │                  ▼
                           │       ┌───────────────────────┐
                           │       │ Node 2: Hybrid Search │
                           │       │ (Dense + BM25 + RRF)  │
                           │       └──────────┬────────────┘
                           │                  │
                           │                  ▼
                           │       ┌───────────────────────┐
                           │       │ Node 3: Batch Grader  │◄─────────────────────────┐
                           │       │ (Single Structured    │                          │
                           │       │  LLM Evaluation Call) │                          │
                           │       └──────────┬────────────┘                          │
                           │                  │                                       │
                           │          Filter score >= 0.70                            │
                           │                  │                                       │
                           │        ┌─────────┴─────────┐                             │
                           │        │ Any Docs Passed?  │                             │
                           │        └─────────┬─────────┘                             │
                           │           Yes    │    No                                 │
                           │        ┌─────────┘    └─────────────┐                    │
                           │        │                            ▼                    │
                           │        │                 ┌─────────────────────┐         │
                           │        │                 │ loop_count < limit? │         │
                           │        │                 └──┬───────────────┬──┘         │
                           │        │                 Yes│             No│            │
                           │        │                    ▼               ▼            │
                           │        │          ┌───────────────┐ ┌──────────────────┐ │
                           │        │          │Node 4: Query  │ │Node 5: Web Search│ │
                           │        │          │Rewriter       │ │Fallback (Tavily/ │ │
                           │        │          └───────┬───────┘ │DuckDuckGo)       │ │
                           │        │                  │         └────────┬─────────┘ │
                           │        │                  └─────────────────►│           │
                           │        │             (Loops to Node 2)       └───────────┘
                           ▼        ▼                                    (To Node 6)
                  ┌────────────────────────────────────┐
                  │   Node 6: Response Synthesizer     │
                  │   (Grounded Generation + Citations)│
                  └─────────────────┬──────────────────┘
                                    │
                                    ▼
                  ┌────────────────────────────────────┐
                  │   Node 7: Self-RAG Verifier        │
                  │   (Faithfulness + Relevance Check) │
                  └─────────────────┬──────────────────┘
                                    │
                        Pass / Max Hallucination Retry
                                    │
                                    ▼
                  ┌────────────────────────────────────┐
                  │   Typed SSE Stream to Next.js UI   │
                  └────────────────────────────────────┘

```

### 2.2 Infrastructure & Zero-Cost Stack Budget

| Subsystem | Primary Choice | Fallback Choice | Free Tier Quota / Constraints | 
| ----- | ----- | ----- | ----- | 
| **LLM Inference** | Google Gemini 2.5 Flash (`google-genai`) | Groq (`llama-3.3-70b-versatile`) | Gemini: 15 RPM, 1M TPM. Groq: 30 RPM, 14.4K RPD | 
| **Dense Embeddings** | Google `gemini-embedding-001` (output 768-dim; replaces shut-down `text-embedding-004`) | Local `FastEmbed` (`BAAI/bge-small-en-v1.5`) / `HashEmbedder` in tests | Gemini embed free tier; FastEmbed: CPU-native, 0 API latency | 
| **Sparse Embeddings** | Qdrant FastEmbed `Qdrant/bm25` | `rank_bm25` in-memory index | 100% Free Local / Docker | 
| **Vector Store** | Qdrant (Docker or Cloud Free 1GB) | ChromaDB Persistent Client | Qdrant Cloud: 1GB RAM persistent cluster free forever | 
| **Web Fallback** | Tavily Search API (Research Tier) | `duckduckgo-search` (Async DDGS) | Tavily: 1,000 req/month free (no CC); DDGS: Unlimited free | 
| **Orchestration** | LangGraph (`StateGraph` + `AsyncSqliteSaver`) | Pure Python Async State Machine | Open-source MIT | 
| **Observability** | Arize Phoenix (Local Docker) or Langfuse | Structured JSON stdout logs | Langfuse Cloud: 50k observations/mo free | 

## 3. Low-Level Design (LLD)

### 3.1 Graph State Schema (`orchestration/state.py`)

All graph nodes accept and return partial updates to a strongly typed state schema.

* `session_id: str` — Unique UUIDv4 for conversation thread and checkpointer.

* `original_query: str` — Immutable raw user query.

* `sanitized_query: str` — PII-redacted, injection-checked query.

* `active_query: str` — Current search string (mutated by Query Rewriter).

* `route_decision: Literal["direct", "rag", "blocked"]` — Output of Node 1.

* `retrieved_chunks: list[DocumentChunk]` — Output of Node 2 (Hybrid RRF).

* `graded_chunks: list[GradedChunk]` — Chunks surviving Node 3 ($\text{score} \ge 0.70$).

* `rewrite_count: int` — Number of query reformulations executed (Max: `2`).

* `hallucination_retry_count: int` — Number of synthesis retries (Max: `1`).

* `web_fallback_triggered: bool` — Flag indicating external search usage.

* `draft_answer: str` — Synthesized response containing `[n]` inline markers.

* `verification_report: VerificationResult` — Groundedness and completeness scores.

* `citations: list[CitationItem]` — Mapped metadata for UI inspection drawer.

* `node_trace: list[NodeExecutionEvent]` — Telemetry array for SSE UI visualization.

### 3.2 Mathematical Formulations

#### Reciprocal Rank Fusion (Node 2)

Given a set of rankings $R$ from Dense Cosine Similarity ($r_{\text{dense}}$) and Sparse BM25 ($r_{\text{sparse}}$), the unified RRF score for document $d \in D$ with smoothing constant $k = 60$ is:

$$
\text{RRF\_Score}(d) = \frac{1}{k + r_{\text{dense}}(d)} + \frac{1}{k + r_{\text{sparse}}(d)}
$$

#### Context Relevance Filtering (Node 3)

To conserve the 15 RPM quota on the Gemini Free Tier, **Node 3 MUST batch-grade all** $K$ **chunks in a single LLM call** using structured JSON array output rather than $K$ parallel calls.

$$
\text{Retained\_Chunks} = \{ c_i \in C \mid \text{LLM\_Grade}(q, c_i).\text{confidence} \ge 0.70 \}
$$

### 3.3 Node-by-Node Execution Contracts

1. **Node 1 (`sanitize_and_route`)**:

   * **Input**: `original_query`

   * **Logic**: Runs deterministic regex/heuristic check for prompt injection (`"ignore previous"`, `"system prompt"`). Calls LLM with structured output `RouteSchema`.

   * **Token Budget**: $\le 250$ input tokens, $\le 60$ output tokens.

   * **Latency SLA**: $< 600\text{ms}$.

2. **Node 2 (`hybrid_retrieve`)**:

   * **Input**: `active_query`

   * **Logic**: Executes Qdrant `query_points` using `Prefetch` for both `dense_vector` (top 10) and `sparse_vector` (top 10), fused via `Fusion.RRF` returning top $K=5$ chunks.

   * **Latency SLA**: $< 250\text{ms}$.

3. **Node 3 (`grade_documents_batch`)**:

   * **Input**: `active_query`, `retrieved_chunks`

   * **Logic**: Evaluates all 5 chunks in **one** structured LLM call returning `BatchGradeResult(evaluations: list[ChunkEvaluation])`.

   * **Edge Routing**:

     * If `len(graded_chunks) >= 1` $\rightarrow$ `synthesize_response`.

     * If `len(graded_chunks) == 0` and `rewrite_count < 2` $\rightarrow$ `rewrite_query`.

     * If `len(graded_chunks) == 0` and `rewrite_count >= 2` $\rightarrow$ `web_search_fallback`.

4. **Node 4 (`rewrite_query`)**:

   * **Input**: `original_query`, `active_query`, `rewrite_count`

   * **Logic**: Prompts LLM to expand acronyms, extract underlying technical entities, and strip conversational fluff. Increments `rewrite_count += 1`.

5. **Node 5 (`web_search_fallback`)**:

   * **Input**: `active_query`

   * **Logic**: Queries Tavily API (or DuckDuckGo fallback), sanitizes HTML/Markdown, splits into 400-token chunks, assigns `source_type="web"`, and populates `graded_chunks`.

6. **Node 6 (`synthesize_response`)**:

   * **Input**: `original_query`, `graded_chunks`

   * **Logic**: Streams response tokens while enforcing strict XML boundary tags (`<context_chunk id="1">...</context_chunk>`) and mandatory `[1]` citation anchors.

7. **Node 7 (`verify_response`)**:

   * **Input**: `original_query`, `graded_chunks`, `draft_answer`

   * **Logic**: Evaluates two axes in one structured call:

     1. `is_grounded: bool` (Zero unsupported factual claims).

     2. `addresses_query: bool` (Directly answers user intent).

   * **Edge Routing**:

     * If `is_grounded and addresses_query` $\rightarrow$ `END`.

     * If `not is_grounded` and `hallucination_retry_count < 1` $\rightarrow$ `synthesize_response` (with critique appended).

     * Otherwise $\rightarrow$ Append transparent confidence disclaimer and `END`.