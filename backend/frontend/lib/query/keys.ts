/**
 * Knowra — Query Key Factory
 * Centralized, type-safe TanStack Query key definitions.
 */

export const queryKeys = {
  meetings: {
    all: ["meetings"] as const,
    list: (filters?: Record<string, unknown>) =>
      ["meetings", "list", filters] as const,
    detail: (id: string) => ["meetings", "detail", id] as const,
  },
  transcripts: {
    byMeeting: (meetingId: string) =>
      ["transcripts", "meeting", meetingId] as const,
  },
  chat: {
    sessions: () => ["chat", "sessions"] as const,
    session: (id: string) => ["chat", "session", id] as const,
    messages: (sessionId: string) =>
      ["chat", "messages", sessionId] as const,
  },
  graph: {
    data: (filters?: Record<string, unknown>) =>
      ["graph", "data", filters] as const,
    entity: (id: string) => ["graph", "entity", id] as const,
  },
  timeline: {
    byEntity: (entityId: string) =>
      ["timeline", "entity", entityId] as const,
    decisions: () => ["timeline", "decisions"] as const,
  },
  evaluation: {
    runs: () => ["evaluation", "runs"] as const,
    quality: () => ["evaluation", "quality"] as const,
    costs: () => ["evaluation", "costs"] as const,
    traces: (filters?: Record<string, unknown>) =>
      ["evaluation", "traces", filters] as const,
  },
  integrations: {
    list: () => ["integrations"] as const,
  },
  actions: {
    byMeeting: (meetingId?: string) =>
      ["actions", meetingId ?? "all"] as const,
  },
  decisions: {
    byMeeting: (meetingId?: string) =>
      ["decisions", meetingId ?? "all"] as const,
  },
} as const;
