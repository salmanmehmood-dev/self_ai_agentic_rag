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
      ? "animate-instrument-pulse border-2 border-sky-600 bg-sky-50 text-sky-950"
      : data.accent === "rewrite"
        ? "animate-instrument-pulse border-2 border-warn bg-warn/10 text-foreground"
        : "animate-instrument-pulse border-2 border-accent bg-accent/10 text-foreground"
    : data.done
      ? "border border-ok bg-ok/10 text-foreground"
      : "border border-border bg-surface text-muted-foreground";

  return (
    <div
      className={`min-w-[108px] border px-3 py-2 text-center font-mono text-[11px] font-medium ${ring}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-accent" />
      <div>{data.label}</div>
      {data.active ? (
        <div className="mt-0.5 text-[9px] uppercase tracking-wide text-accent">
          live
        </div>
      ) : null}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!bg-accent"
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
      style: { stroke: live.rewriteActive ? "#b45309" : undefined },
    },
    {
      id: "e-rewriter-retriever",
      source: "rewriter",
      target: "retriever",
      type: "smoothstep",
      animated: live.rewriteActive,
      label: live.rewriteActive ? "rewrite" : undefined,
      style: {
        stroke: live.rewriteActive ? "#b45309" : "#9cc5bc",
        strokeDasharray: live.rewriteActive ? "6 4" : undefined,
      },
      labelStyle: { fill: "#b45309", fontSize: 10 },
    },
  ];

  return base.map((e) => ({
    ...e,
    markerEnd: {
      type: MarkerType.ArrowClosed,
      width: 14,
      height: 14,
      color: "#0d9488",
    },
    animated:
      e.animated ?? animated(e.source as AgentNode, e.target as AgentNode),
    style: {
      stroke: "#9cc5bc",
      strokeWidth: 1.5,
      ...e.style,
    },
  }));
}

export function AgentFlowCanvas({ live }: { live: GraphLiveState }) {
  const nodes = useMemo(() => buildNodes(live), [live]);
  const edges = useMemo(() => buildEdges(live), [live]);

  return (
    <div className="h-72 w-full overflow-hidden border border-border bg-surface">
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
        proOptions={{ hideAttribution: true }}
      >
        <Background gap={18} size={1} color="#d7e8e4" />
      </ReactFlow>
    </div>
  );
}
