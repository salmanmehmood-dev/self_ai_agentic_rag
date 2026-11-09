/**
 * SSE client for POST /api/v1/chat/stream.
 * Caller: hooks/useAgentChat.ts. Parses backend ApiErrorBody on HTTP failures.
 * User: meaningful BE msgs for FE users; BE developer_message logged as [backend].
 */

import { fetchEventSource } from "@microsoft/fetch-event-source";

import type { AgentSSEEvent } from "./sse-types";
import {
  mapFrontendError,
  mapHttpStatus,
  parseBackendErrorPayload,
  type UserFacingError,
} from "./user-facing-errors";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

/** Resolved backend origin (build-time NEXT_PUBLIC_API_URL). */
export function getApiBase(): string {
  return API_BASE;
}

export type StreamHandlers = {
  onEvent: (event: AgentSSEEvent) => void;
  onError?: (err: UserFacingError) => void;
  signal?: AbortSignal;
};

async function readBackendError(
  response: Response,
): Promise<UserFacingError | null> {
  try {
    const json: unknown = await response.json();
    return parseBackendErrorPayload(json);
  } catch (err) {
    mapFrontendError(err, "ERR_PARSE");
    return null;
  }
}

export async function streamChat(
  query: string,
  handlers: StreamHandlers,
): Promise<void> {
  // #region agent log
  fetch("http://127.0.0.1:7283/ingest/8fc48db5-58f2-4836-8f69-28901c6320b9", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-Debug-Session-Id": "9c6d38",
    },
    body: JSON.stringify({
      sessionId: "9c6d38",
      runId: "api-url-check",
      hypothesisId: "A",
      location: "chat-stream.ts:streamChat",
      message: "resolved API_BASE at request",
      data: {
        apiBase: API_BASE,
        envRaw: process.env.NEXT_PUBLIC_API_URL ?? null,
        usedFallback: !process.env.NEXT_PUBLIC_API_URL,
      },
      timestamp: Date.now(),
    }),
  }).catch(() => {});
  // #endregion
  await fetchEventSource(`${API_BASE}/api/v1/chat/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "text/event-stream",
    },
    body: JSON.stringify({ query }),
    signal: handlers.signal,
    openWhenHidden: true,
    async onopen(response) {
      if (!response.ok) {
        const backend = await readBackendError(response);
        const mapped = mapHttpStatus(
          response.status,
          `SSE open failed: HTTP ${response.status}`,
          backend,
        );
        handlers.onError?.(mapped);
        throw new Error(mapped.technical);
      }
    },
    onmessage(msg) {
      if (!msg.data) return;
      try {
        const parsed = JSON.parse(msg.data) as AgentSSEEvent;
        if (parsed && typeof parsed === "object" && "event" in parsed) {
          handlers.onEvent(parsed);
        }
      } catch (err) {
        mapFrontendError(err, "ERR_PARSE");
      }
    },
    onerror(err) {
      const mapped = mapFrontendError(err);
      handlers.onError?.(mapped);
      throw err;
    },
  });
}
