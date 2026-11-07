# Hybrid Retrieval: Dense + Sparse RRF

## Architecture

Node 2 (`hybrid_retrieve`) queries Qdrant with **Prefetch** for:

- Dense vectors from Gemini `gemini-embedding-001` truncated to 768 dimensions
  (replaces deprecated `text-embedding-004`, shut down 2026-01-14)
- Sparse hashed TF vectors (BM25-shaped, local — no FastEmbed download required)

Results are fused with **Reciprocal Rank Fusion (RRF)** and the top $K=5$ chunks
are returned for grading.

## Latency SLA

Hybrid retrieve should complete in under **250ms** on a warm local Qdrant.

## Why hybrid

Dense retrieval captures semantic paraphrases. Sparse retrieval catches exact
tokens (API names, error codes like `429`, file names). RRF merges both rankings
without needing score calibration.

## Cold start

If the Qdrant collection is missing or has **zero points**, retrieval returns an
empty list. The agent then rewrite-loops and eventually falls back to live web
search (Tavily / DuckDuckGo). Operators should ingest the sample corpus on boot.
