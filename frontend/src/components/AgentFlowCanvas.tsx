"use client";

import {
  Background,
  type Edge,
  Handle,
  MarkerType,
  type Node,
  type NodeProps,
  Position,
  ReactFlow,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useMemo } from "react";

import type { AgentNode, GraphLiveState } from "../lib/sse-types";

const LABELS: Record<AgentNode, string> = {
  router: "Router",
  retriever: "Hybrid RRF",
  grader: "Grader",
  rewriter: "Rewriter",
  web_search: "Web",
  synthesizer: "Synthesize",
  verifier: "Verify",
};

type AgentNodeData = {
  label: string;
  kind: AgentNode;
  active: boolean;
  done: boolean;
  accent?: "rewrite" | "web";
};

function AgentNodeView({ data }: NodeProps<Node<AgentNodeData>>) {
  const ring = data.active
    ? data.accent === "web"
      ? "ring-2 ring-cyan-400 shadow-[0_0_16px_rgba(34,211,238,0.45)]"
      : data.accent === "rewrite"
        ? "ring-2 ring-amber-400 shadow-[0_0_16px_rgba(251,191,36,0.4)]"
        : "ring-2 ring-emerald-400 shadow-[0_0_16px_rgba(52,211,153,0.45)]"
    : data.done
      ? "border-emerald-700/80 bg-emerald-950/40"
      : "border-slate-700 bg-slate-900/70";

  return (
    <div
      className={`min-w-[108px] rounded-md border px-3 py-2 text-center text-[11px] font-medium text-slate-100 ${ring}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-500" />
      <div>{data.label}</div>
      {data.active ? (
        <div className="mt-0.5 text-[9px] uppercase tracking-wide text-emerald-300">
          live
        </div>
      ) : null}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-slate-500"
      />
    </div>
  );
}

const nodeTypes = { agent: AgentNodeView };

const LAYOUT: Array<{ id: AgentNode; x: number; y: number }> = [
  { id: "router", x: 180, y: 0 },
  { id: "retriever", x: 180, y: 90 },
  { id: "grader", x: 180, y: 180 },
  { id: "rewriter", x: 20, y: 180 },
  { id: "web_search", x: 340, y: 270 },
  { id: "synthesizer", x: 180, y: 360 },
  { id: "verifier", x: 180, y: 450 },
];

function buildNodes(live: GraphLiveState): Node<AgentNodeData>[] {
  return LAYOUT.map(({ id, x, y }) => {
    const active = live.activeNode === id;
    const accent =
      id === "rewriter" && (active || live.rewriteActive)
        ? "rewrite"
        : id === "web_search" && (active || live.webActive)
          ? "web"
          : undefined;
    return {
      id,
      type: "agent",
      position: { x, y },
      data: {
        label: LABELS[id],
        kind: id,
        active:
          active ||
          (id === "rewriter" && live.rewriteActive && !live.activeNode),
        done: live.completedNodes.includes(id),
        accent,
      },
      draggable: false,
      selectable: false,
    };
  });
}

function buildEdges(live: GraphLiveState): Edge[] {
  const animated = (from: AgentNode, to: AgentNode) =>
    live.activeNode === to ||
    (live.activeNode === from && !live.completedNodes.includes(to));

  const base: Edge[] = [
    { id: "e-router-retriever", source: "router", target: "retriever" },
    { id: "e-retriever-grader", source: "retriever", target: "grader" },
    { id: "e-grader-synth", source: "grader", target: "synthesizer" },
    { id: "e-grader-web", source: "grader", target: "web_search" },
    { id: "e-web-synth", source: "web_search", target: "synthesizer" },
    { id: "e-synth-verify", source: "synthesizer", target: "verifier" },
    {
      id: "e-grader-rewriter",
      source: "grader",
      target: "rewriter",
      style: { stroke: live.rewriteActive ? "#fbbf24" : undefined },
    },
    {
      id: "e-rewriter-retriever",
      source: "rewriter",
      target: "retriever",
      type: "smoothstep",
      animated: live.rewriteActive,
      label: live.rewriteActive ? "rewrite" : undefined,
      style: {
        stroke: live.rewriteActive ? "#fbbf24" : "#64748b",
        strokeDasharray: live.rewriteActive ? "6 4" : undefined,
      },
      labelStyle: { fill: "#fbbf24", fontSize: 10 },
    },
  ];

  return base.map((e) => ({
    ...e,
    markerEnd: { type: MarkerType.ArrowClosed, width: 14, height: 14 },
    animated:
      e.animated ?? animated(e.source as AgentNode, e.target as AgentNode),
    style: {
      stroke: "#64748b",
      strokeWidth: 1.5,
      ...e.style,
    },
  }));
}

export function AgentFlowCanvas({ live }: { live: GraphLiveState }) {
  const nodes = useMemo(() => buildNodes(live), [live]);
  const edges = useMemo(() => buildEdges(live), [live]);

  return (
    <div className="h-72 w-full overflow-hidden rounded-md border border-slate-800 bg-slate-950">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        panOnDrag
        zoomOnScroll={false}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background gap={18} size={1} color="#1e293b" />
      </ReactFlow>
    </div>
  );
}
