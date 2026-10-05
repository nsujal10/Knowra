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
  timeline: (entityId?: string) => (entityId ? `/cross-meeting/timeline/${entityId}` : "/cross-meeting/timeline"),
  decisions: () => "/cross-meeting/decisions",
  sync: () => "/cross-meeting/sync",
};

// ─── Knowledge Graph ─────────────────────────────────────────────────────────
export const GRAPH = {
  nodes: () => "/graph/nodes",
  edges: () => "/graph/edges",
  entity: (id: string) => `/graph/entities/${id}`,
  expand: (entityId: string) => `/graph/entities/${entityId}/expand`,
  sync: () => "/graph/sync",
  query: () => "/graph/query",
  metrics: () => "/graph/metrics",
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
  get: (id: string) => `/integrations/${id}`,
  update: (id: string) => `/integrations/${id}`,
  delete: (id: string) => `/integrations/${id}`,
  test: (id: string) => `/integrations/${id}/test`,
  events: () => "/integrations/events/history",
  testResend: () => "/integrations/resend/test",
  calendarStatus: () => "/integrations/calendar/status",
  calendarEvents: (provider?: string) =>
    provider ? `/integrations/calendar/events?provider=${provider}` : "/integrations/calendar/events",
  calendarConnect: () => "/integrations/calendar/connect",
  calendarDisconnect: () => "/integrations/calendar/disconnect",
  calendarSync: () => "/integrations/calendar/sync",
  calendarToggleBot: () => "/integrations/calendar/toggle-bot",
  googleCalendarAuthUrl: () => "/integrations/google-calendar/auth-url",
  googleCalendarSync: () => "/integrations/google-calendar/sync",
  zoomAuthUrl: () => "/integrations/zoom/auth-url",
  outlookAuthUrl: () => "/integrations/outlook/auth-url",
  outlookSync: () => "/integrations/outlook/sync",
  jiraConnect: () => "/integrations/jira/connect",
  jiraStatus: () => "/integrations/jira/status",
  jiraProjects: () => "/integrations/jira/projects",
  jiraIssues: (maxResults: number = 10) => `/integrations/jira/issues?max_results=${maxResults}`,
  jiraCreateIssue: () => "/integrations/jira/create-issue",
  jiraDisconnect: () => "/integrations/jira/disconnect",
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

