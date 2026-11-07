# Document Grading and Query Rewrite

## Batch grader (Node 3)

To conserve Gemini free-tier RPM, the grader evaluates **all retrieved chunks in
one structured LLM call**. It returns a `BatchGradeResult` with one evaluation
per chunk. Chunks with confidence **≥ 0.70** are kept for synthesis.

## Rewrite loop (Node 4)

If every chunk is filtered and `rewrite_count < 2`, the query rewriter produces a
clearer search string and hybrid retrieve runs again. Hard ceiling:
`MAX_QUERY_REWRITES = 2`.

## Web fallback (Node 5)

If grading still fails after two rewrites, the graph sets
`web_fallback_triggered = True` and calls Tavily or DuckDuckGo with a
`httpx.Timeout(4.0)`. Web snippets are treated as graded context for synthesis.

## Self-RAG verifier (Node 7)

After synthesis, the verifier checks groundedness and query coverage. On failure
the synthesizer may retry once (`MAX_HALLUCINATION_RETRIES = 1`). A second failure
emits `partial_verification` for an amber UI badge.
