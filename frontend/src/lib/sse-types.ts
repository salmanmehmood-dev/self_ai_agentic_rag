/** Typed Agent SSE wire protocol (matches backend domain events). */

export type AgentNode =
  | "router"
  | "retriever"
  | "grader"
  | "rewriter"
  | "web_search"
  | "synthesizer"
  | "verifier";

export type NodeStatus = "running" | "completed" | "skipped" | "fallback";

export type AgentSSEEvent =
  | {
      event: "node_transition";
      data: {
        node: AgentNode;
        status: NodeStatus;
        latency_ms?: number;
        summary: string;
      };
    }
  | {
      event: "retrieval_results";
      data: {
        query_used: string;
        attempt: number;
        chunks: Array<{
          chunk_id: string;
          source_file: string;
          section_header: string;
          rrf_score: number;
          dense_rank: number;
          sparse_rank: number;
          preview_text: string;
        }>;
      };
    }
  | {
      event: "grading_verdict";
      data: {
        passed_count: number;
        rejected_count: number;
        evaluations: Array<{
          chunk_id: string;
          relevant: boolean;
          confidence: number;
          reasoning: string;
        }>;
      };
    }
  | {
      event: "query_rewritten";
      data: {
        previous_query: string;
        new_query: string;
        reason: string;
        rewrite_count: number;
      };
    }
  | {
      event: "token_chunk";
      data: { delta: string };
    }
  | {
      event: "verification_complete";
      data: {
        is_grounded: boolean;
        addresses_query: boolean;
        confidence_score: number;
        provider_used: "gemini-2.5-flash" | "groq-llama-3.3-70b";
        total_latency_ms: number;
      };
    }
  | {
      event: "provider_failover";
      data: {
        from_provider: string;
        to_provider: string;
        reason: string;
      };
    };

export type TimelineStep = {
  node: AgentNode;
  status: NodeStatus;
  latency_ms?: number;
  summary: string;
};

export type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timeline: TimelineStep[];
  verification?: {
    is_grounded: boolean;
    addresses_query: boolean;
    confidence_score: number;
    provider_used: string;
    total_latency_ms: number;
  };
};

export type RetrievalChunk = {
  chunk_id: string;
  source_file: string;
  section_header: string;
  rrf_score: number;
  dense_rank: number;
  sparse_rank: number;
  preview_text: string;
};

export type GradeEvaluation = {
  chunk_id: string;
  relevant: boolean;
  confidence: number;
  reasoning: string;
};

export type GraphLiveState = {
  activeNode: AgentNode | null;
  completedNodes: AgentNode[];
  rewriteActive: boolean;
  webActive: boolean;
  chunks: RetrievalChunk[];
  evaluations: GradeEvaluation[];
};
