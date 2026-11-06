"use client";

import { useCallback, useRef, useState } from "react";

import { streamChat } from "../lib/chat-stream";
import type { AgentSSEEvent, ChatMessage, TimelineStep } from "../lib/sse-types";

function newId(): string {
  return crypto.randomUUID();
}

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(async (raw?: string) => {
    const query = (raw ?? input).trim();
    if (!query || streaming) return;

    setError(null);
    setInput("");
    setStreaming(true);

    const userMsg: ChatMessage = {
      id: newId(),
      role: "user",
      content: query,
      timeline: [],
    };
    const assistantId = newId();
    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: "assistant", content: "", timeline: [] },
    ]);

    const ac = new AbortController();
    abortRef.current = ac;

    const patchAssistant = (fn: (m: ChatMessage) => ChatMessage) => {
      setMessages((prev) =>
        prev.map((m) => (m.id === assistantId ? fn(m) : m)),
      );
    };

    try {
      await streamChat(query, {
        signal: ac.signal,
        onEvent(ev: AgentSSEEvent) {
          if (ev.event === "node_transition") {
            const step: TimelineStep = {
              node: ev.data.node,
              status: ev.data.status,
              latency_ms: ev.data.latency_ms,
              summary: ev.data.summary,
            };
            patchAssistant((m) => ({
              ...m,
              timeline: [...m.timeline, step],
            }));
          } else if (ev.event === "token_chunk") {
            patchAssistant((m) => ({
              ...m,
              content: m.content + ev.data.delta,
            }));
          } else if (ev.event === "verification_complete") {
            patchAssistant((m) => ({
              ...m,
              verification: { ...ev.data },
            }));
          } else if (ev.event === "grading_verdict") {
            patchAssistant((m) => ({
              ...m,
              timeline: m.timeline.map((t, i) =>
                i === m.timeline.length - 1 && t.node === "grader"
                  ? {
                      ...t,
                      summary: `${t.summary} · kept ${ev.data.passed_count}`,
                    }
                  : t,
              ),
            }));
          }
        },
        onError(err) {
          setError(err.message);
        },
      });
    } catch (err) {
      if (!(err instanceof DOMException && err.name === "AbortError")) {
        setError(err instanceof Error ? err.message : String(err));
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, [input, streaming]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return { messages, input, setInput, send, stop, streaming, error };
}
