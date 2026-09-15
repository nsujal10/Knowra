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
  list: () => "/integrations",
  create: () => "/integrations",
  test: (id: string) => `/integrations/${id}/test`,
};

// ─── Actions ─────────────────────────────────────────────────────────────────
export const ACTIONS = {
  list: (meetingId?: string) =>
    meetingId ? `/meetings/${meetingId}/actions` : "/actions",
};

// ─── Decisions ───────────────────────────────────────────────────────────────
export const DECISIONS = {
  list: (meetingId?: string) =>
    meetingId ? `/meetings/${meetingId}/decisions` : "/decisions",
};
