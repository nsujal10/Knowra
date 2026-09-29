/**
 * Knowra — Typed API Endpoint Builders
 * All backend routes with typed path parameters.
 */

// ─── Auth ─────────────────────────────────────────────────────────────────────
export const AUTH = {
  login: () => "/auth/login",
  logout: () => "/auth/logout",
  refresh: () => "/auth/refresh",
  me: () => "/auth/me",
};

// ─── Meetings ─────────────────────────────────────────────────────────────────
export const MEETINGS = {
  list: () => "/meetings",
  get: (id: string) => `/meetings/${id}`,
  create: () => "/meetings",
  delete: (id: string) => `/meetings/${id}`,
};

// ─── Transcripts ─────────────────────────────────────────────────────────────
export const TRANSCRIPTS = {
  get: (meetingId: string) => `/meetings/${meetingId}/transcript`,
  list: () => "/transcripts",
};

// ─── Diarization ─────────────────────────────────────────────────────────────
export const DIARIZATION = {
  get: (meetingId: string) => `/meetings/${meetingId}/diarization`,
};

// ─── Knowledge / Search ───────────────────────────────────────────────────────
export const KNOWLEDGE = {
  search: () => "/knowledge/search",
};

export const SEARCH = {
  enterprise: () => "/search",
};

// ─── Chat ─────────────────────────────────────────────────────────────────────
export const CHAT = {
  sessions: () => "/chat/sessions",
  session: (id: string) => `/chat/sessions/${id}`,
  messages: (sessionId: string) => `/chat/sessions/${sessionId}/messages`,
  stream: (sessionId: string) => `/chat/sessions/${sessionId}/stream`,
  query: () => "/chat/query",
};

// ─── Cross-Meeting Intelligence ───────────────────────────────────────────────
export const CROSS_MEETING = {
  query: () => "/cross-meeting/query",
  timeline: (entityId: string) => `/cross-meeting/timeline/${entityId}`,
  decisions: () => "/cross-meeting/decisions",
};

// ─── Knowledge Graph ─────────────────────────────────────────────────────────
export const GRAPH = {
  nodes: () => "/graph/nodes",
  edges: () => "/graph/edges",
  entity: (id: string) => `/graph/entities/${id}`,
  expand: (entityId: string) => `/graph/entities/${entityId}/expand`,
};

// ─── Evaluation & Observability ───────────────────────────────────────────────
export const EVALUATION = {
  runs: () => "/evaluation/runs",
  evaluate: () => "/evaluation/evaluate",
  quality: () => "/evaluation/quality",
  costs: () => "/evaluation/costs",
  traces: () => "/evaluation/traces",
  prompts: () => "/evaluation/prompts",
};

// ─── Integrations ─────────────────────────────────────────────────────────────
export const INTEGRATIONS = {
  list: (params?: { provider?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.provider && params.provider !== "ALL") q.append("provider", params.provider);
    if (params?.status && params.status !== "ALL") q.append("status_filter", params.status);
    const qs = q.toString();
    return qs ? `/integrations?${qs}` : "/integrations";
  },
  create: () => "/integrations",
  get: (id: string) => `/integrations/${id}`,
  update: (id: string) => `/integrations/${id}`,
  delete: (id: string) => `/integrations/${id}`,
  test: (id: string) => `/integrations/${id}/test`,
  eventsHistory: (params?: { integrationId?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.integrationId) q.append("integration_id", params.integrationId);
    if (params?.limit) q.append("limit", params.limit.toString());
    const qs = q.toString();
    return qs ? `/integrations/events/history?${qs}` : "/integrations/events/history";
  },
};

// ─── Actions ─────────────────────────────────────────────────────────────────
export const ACTIONS = {
  list: (params?: { meetingId?: string; status?: string; priority?: string; owner?: string; search?: string } | string) => {
    if (typeof params === "string") {
      return `/meetings/${params}/actions`;
    }
    const q = new URLSearchParams();
    if (params?.meetingId) q.append("meeting_id", params.meetingId);
    if (params?.status) q.append("status", params.status);
    if (params?.priority) q.append("priority", params.priority);
    if (params?.owner) q.append("owner", params.owner);
    if (params?.search) q.append("search", params.search);
    const qs = q.toString();
    const base = params?.meetingId ? `/meetings/${params.meetingId}/actions` : "/actions";
    return qs ? `${base}?${qs}` : base;
  },
  toggle: (id: string) => `/actions/${id}/toggle`,
};

// ─── Decisions ───────────────────────────────────────────────────────────────
export const DECISIONS = {
  list: (params?: { meetingId?: string; status?: string; category?: string; search?: string } | string) => {
    if (typeof params === "string") {
      return `/meetings/${params}/decisions`;
    }
    const q = new URLSearchParams();
    if (params?.meetingId) q.append("meeting_id", params.meetingId);
    if (params?.status) q.append("status", params.status);
    if (params?.category) q.append("category", params.category);
    if (params?.search) q.append("search", params.search);
    const qs = q.toString();
    const base = params?.meetingId ? `/meetings/${params.meetingId}/decisions` : "/decisions";
    return qs ? `${base}?${qs}` : base;
  },
};

