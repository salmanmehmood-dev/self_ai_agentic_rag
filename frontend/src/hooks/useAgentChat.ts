"use client";

import { useCallback, useRef, useState } from "react";

import { streamChat } from "../lib/chat-stream";
import type {
  AgentNode,
  AgentSSEEvent,
  ChatMessage,
  GraphLiveState,
  TimelineStep,
  UserNotice,
} from "../lib/sse-types";
import {
  isDevErrorDetailEnabled,
  mapSystemWarning,
  mapUnknownError,
  type UserFacingError,
} from "../lib/user-facing-errors";

function newId(): string {
  return crypto.randomUUID();
}

const EMPTY_GRAPH: GraphLiveState = {
  activeNode: null,
  completedNodes: [],
  rewriteActive: false,
  webActive: false,
  chunks: [],
  evaluations: [],
};

export function useAgentChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [userError, setUserError] = useState<UserFacingError | null>(null);
  const [graphLive, setGraphLive] = useState<GraphLiveState>(EMPTY_GRAPH);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (raw?: string) => {
      const query = (raw ?? input).trim();
      if (!query || streaming) return;

      setUserError(null);
      setInput("");
      setStreaming(true);
      setGraphLive(EMPTY_GRAPH);

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
              setGraphLive((g) => {
                const node = ev.data.node as AgentNode;
                const completed =
                  ev.data.status === "completed" || ev.data.status === "fallback"
                    ? g.completedNodes.includes(node)
                      ? g.completedNodes
                      : [...g.completedNodes, node]
                    : g.completedNodes;
                return {
                  ...g,
                  activeNode:
                    ev.data.status === "running"
                      ? node
                      : g.activeNode === node
                        ? null
                        : g.activeNode,
                  completedNodes: completed,
                  webActive:
                    node === "web_search" &&
                    (ev.data.status === "running" ||
                      ev.data.status === "fallback")
                      ? true
                      : g.webActive,
                };
              });
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
              setGraphLive((g) => ({ ...g, activeNode: null }));
            } else if (ev.event === "retrieval_results") {
              setGraphLive((g) => ({
                ...g,
                chunks: ev.data.chunks,
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
              setGraphLive((g) => ({
                ...g,
                evaluations: ev.data.evaluations,
              }));
            } else if (ev.event === "query_rewritten") {
              setGraphLive((g) => ({ ...g, rewriteActive: true }));
            } else if (ev.event === "system_warning") {
              const mapped = mapSystemWarning(ev.data);
              const notice: UserNotice = {
                code: mapped.code,
                title: mapped.title,
                message: mapped.message,
                technical: mapped.technical,
                layer: mapped.layer,
              };
              patchAssistant((m) => ({
                ...m,
                notices: [...(m.notices ?? []), notice],
              }));
              if (ev.data.code === "ERR_GRAPH_STREAM") {
                setUserError(mapped);
                if (!isDevErrorDetailEnabled()) {
                  patchAssistant((m) =>
                    m.content.trim()
                      ? m
                      : {
                          ...m,
                          content:
                            "I couldn't complete a verified answer for that question. Please try again.",
                        },
                  );
                }
              }
            }
          },
          onError(err) {
            setUserError(err);
          },
        });
      } catch (err) {
        if (!(err instanceof DOMException && err.name === "AbortError")) {
          setUserError((prev) => prev ?? mapUnknownError(err));
        }
      } finally {
        setStreaming(false);
        abortRef.current = null;
        setGraphLive((g) => ({ ...g, activeNode: null }));
      }
    },
    [input, streaming],
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clearError = useCallback(() => setUserError(null), []);

  return {
    messages,
    input,
    setInput,
    send,
    stop,
    streaming,
    userError,
    clearError,
    showDevErrors: isDevErrorDetailEnabled(),
    graphLive,
  };
}
