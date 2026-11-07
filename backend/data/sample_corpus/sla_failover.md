# SLA: Gemini to Groq LLM Failover

## Overview

This Agentic CRAG system uses **Google Gemini 2.5 Flash** as the primary LLM and
**Groq `llama-3.3-70b-versatile`** as the automatic failover provider. All structured
generation goes through the unified `LLMGatewayPort` adapter.

## Gemini free-tier quota

Google Gemini Free Tier permits **15 Requests Per Minute (RPM)**. When the primary
provider raises `429 RESOURCE_EXHAUSTED` or `503 UNAVAILABLE`, the gateway must not
crash the LangGraph run.

## Failover after a 429

When Gemini returns HTTP **429** (quota exhausted / rate limited):

1. A `tenacity` decorator catches the 429.
2. The gateway waits **2 seconds** with random jitter and **retries once**.
3. If the retry still fails, the gateway emits an SSE event `provider_failover`
   with `from_provider=gemini-2.5-flash` and `to_provider=groq-llama-3.3-70b`.
4. The **identical structured prompt** is executed against Groq without aborting
   the graph.

The same path applies for **503 UNAVAILABLE**.

## Observability

The UI workbench listens for `provider_failover` SSE events so recruiters can see
when a request transparently switched providers mid-pipeline.

## Non-goals

Failover does **not** change embedding providers mid-request. Dense embeddings stay
on Gemini `text-embedding-004` (or the local hash stub in tests).
