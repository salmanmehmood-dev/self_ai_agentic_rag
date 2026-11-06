import { fetchEventSource } from "@microsoft/fetch-event-source";

import type { AgentSSEEvent } from "./sse-types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export type StreamHandlers = {
  onEvent: (event: AgentSSEEvent) => void;
  onError?: (error: Error) => void;
  signal?: AbortSignal;
};

export async function streamChat(
  query: string,
  handlers: StreamHandlers,
): Promise<void> {
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
        throw new Error(`SSE open failed: HTTP ${response.status}`);
      }
    },
    onmessage(msg) {
      if (!msg.data) return;
      try {
        const parsed = JSON.parse(msg.data) as AgentSSEEvent;
        if (parsed && typeof parsed === "object" && "event" in parsed) {
          handlers.onEvent(parsed);
        }
      } catch {
        // ignore malformed frames
      }
    },
    onerror(err) {
      handlers.onError?.(err instanceof Error ? err : new Error(String(err)));
      throw err;
    },
  });
}
