/**
 * Split user copy vs developer detail; tag logs [frontend] vs [backend].
 * Callers: chat-stream.ts, useAgentChat.ts, ChatWorkbench.tsx.
 * User: FE errors for FE devs, BE errors for BE; meaningful msgs for users.
 */

export type ErrorLayer = "frontend" | "backend";

export type UserFacingError = {
  title: string;
  message: string;
  code: string;
  /** Developer-only detail (console / optional UI). */
  technical: string;
  layer: ErrorLayer;
};

const SHOW_DEV =
  process.env.NEXT_PUBLIC_SHOW_DEV_ERRORS === "1" ||
  process.env.NEXT_PUBLIC_SHOW_DEV_ERRORS === "true";

export function isDevErrorDetailEnabled(): boolean {
  return SHOW_DEV;
}

const CODE_MESSAGES: Record<string, Pick<UserFacingError, "title" | "message">> =
  {
    ERR_GRAPH_STREAM: {
      title: "Couldn't finish that answer",
      message:
        "The agent hit a snag while generating a reply. Try again, or rephrase your question.",
    },
    ERR_GRAPH_NOT_READY: {
      title: "Assistant unavailable",
      message:
        "The chat service isn't ready yet. Try again in a moment.",
    },
    ERR_SCANNED_OR_EMPTY_PDF: {
      title: "PDF couldn't be read",
      message:
        "Use a text-based PDF (not a scanned image). Each page needs extractable text.",
    },
    E01_EMPTY_CORPUS: {
      title: "No documents matched yet",
      message:
        "The agent may rewrite your query or search the web for an answer.",
    },
    ERR_INGEST_UNAVAILABLE: {
      title: "Ingest unavailable",
      message: "Document upload isn't ready. Try again after the API finishes starting.",
    },
    ERR_VALIDATION: {
      title: "Request not accepted",
      message:
        "Check your question length (2–2000 characters) or upload format, then try again.",
    },
    ERR_INTERNAL: {
      title: "Something went wrong on the server",
      message: "Please try again. If it keeps failing, ask a backend developer to check logs.",
    },
    ERR_NETWORK: {
      title: "Can't reach the API",
      message:
        "Check that the backend is running and NEXT_PUBLIC_API_URL points to it.",
    },
    ERR_HTTP_503: {
      title: "Assistant unavailable",
      message:
        "The chat service isn't ready. Try again shortly.",
    },
    ERR_HTTP_422: {
      title: "Request not accepted",
      message:
        "Check your input and try again.",
    },
    ERR_HTTP_429: {
      title: "Too many requests",
      message: "Slow down for a few seconds, then send your question again.",
    },
    ERR_CHAT_RATE_LIMIT: {
      title: "Too many chat requests",
      message:
        "You've hit the per-network chat limit. Wait about a minute, then try again.",
    },
    E02_PROVIDER_QUOTA: {
      title: "AI provider is busy",
      message:
        "The model provider is rate-limited. Wait a few seconds and try again.",
    },
    ERR_HTTP_500: {
      title: "Something went wrong on the server",
      message: "Please try again.",
    },
    ERR_SSE_OPEN: {
      title: "Couldn't start the chat stream",
      message:
        "The connection to the assistant failed. Confirm the API is up, then retry.",
    },
    ERR_PARSE: {
      title: "Unexpected response",
      message: "The app couldn't read the server response. Try again.",
    },
    ERR_UNKNOWN: {
      title: "Something went wrong",
      message: "Please try again. If the problem continues, refresh the page.",
    },
  };

export function logForDevelopers(err: UserFacingError): void {
  const tag = err.layer === "backend" ? "[backend]" : "[frontend]";
  console.error(tag, {
    code: err.code,
    title: err.title,
    user_message: err.message,
    developer_message: err.technical,
  });
}

type BackendEnvelope = {
  code?: string;
  user_message?: string;
  developer_message?: string;
  message?: string;
  layer?: string;
};

/** Parse FastAPI `{ detail: ApiErrorBody | string }` or raw envelope. */
export function parseBackendErrorPayload(payload: unknown): UserFacingError | null {
  if (!payload || typeof payload !== "object") return null;
  const root = payload as { detail?: unknown };
  const detail = root.detail ?? payload;
  if (typeof detail === "string") {
    return {
      title: "Request failed",
      message: "Something went wrong. Please try again.",
      code: "ERR_HTTP",
      technical: detail,
      layer: "backend",
    };
  }
  if (!detail || typeof detail !== "object") return null;
  const d = detail as BackendEnvelope;
  if (!d.code && !d.user_message && !d.message && !d.developer_message) {
    return null;
  }
  const code = d.code || "ERR_HTTP";
  const known = CODE_MESSAGES[code];
  return {
    title: known?.title ?? "Request failed",
    message: d.user_message || known?.message || d.message || "Please try again.",
    code,
    technical: d.developer_message || d.message || JSON.stringify(d),
    layer: "backend",
  };
}

export function mapHttpStatus(
  status: number,
  technical: string,
  backend?: UserFacingError | null,
): UserFacingError {
  if (backend) {
    logForDevelopers(backend);
    return backend;
  }
  const code =
    status === 503
      ? "ERR_HTTP_503"
      : status === 422
        ? "ERR_HTTP_422"
        : status === 429
          ? "ERR_HTTP_429"
          : status >= 500
            ? "ERR_HTTP_500"
            : "ERR_SSE_OPEN";
  const base = CODE_MESSAGES[code] ?? CODE_MESSAGES.ERR_UNKNOWN;
  const out: UserFacingError = {
    ...base,
    code,
    technical: technical || `HTTP ${status}`,
    layer: "backend",
  };
  logForDevelopers(out);
  return out;
}

export function mapSystemWarning(data: {
  code: string;
  user_message?: string;
  developer_message?: string;
  message?: string;
}): UserFacingError {
  const known = CODE_MESSAGES[data.code];
  const out: UserFacingError = {
    title: known?.title ?? "Heads up",
    message:
      data.user_message ||
      known?.message ||
      data.message ||
      "The agent continued with a reduced-confidence path. You can retry for a fresh answer.",
    code: data.code || "ERR_UNKNOWN",
    technical:
      data.developer_message || data.message || data.code || "system_warning",
    layer: "backend",
  };
  logForDevelopers(out);
  return out;
}

export function mapFrontendError(err: unknown, code = "ERR_UNKNOWN"): UserFacingError {
  const technical =
    err instanceof Error
      ? err.message
      : typeof err === "string"
        ? err
        : String(err);
  const lower = technical.toLowerCase();
  if (
    lower.includes("failed to fetch") ||
    lower.includes("networkerror") ||
    lower.includes("load failed") ||
    lower.includes("network request failed")
  ) {
    const out: UserFacingError = {
      ...CODE_MESSAGES.ERR_NETWORK,
      code: "ERR_NETWORK",
      technical,
      layer: "frontend",
    };
    logForDevelopers(out);
    return out;
  }
  const known = CODE_MESSAGES[code] ?? CODE_MESSAGES.ERR_UNKNOWN;
  const out: UserFacingError = {
    ...known,
    code,
    technical,
    layer: "frontend",
  };
  logForDevelopers(out);
  return out;
}

/** @deprecated prefer mapFrontendError / mapHttpStatus */
export function mapUnknownError(err: unknown): UserFacingError {
  return mapFrontendError(err);
}
