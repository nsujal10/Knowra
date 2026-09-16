/**
 * Knowra — Rich mock data for UI development & fallback rendering.
 * All types conform to the existing Zod schemas in lib/types/index.ts
 */

import { type Meeting, type Transcript, type ActionItem, type Decision } from "@/lib/types";

// ─── Meetings ────────────────────────────────────────────────────────────────

export const MOCK_MEETINGS: Meeting[] = [
  {
    id: "m-001",
    title: "Q4 Product Roadmap Planning",
    status: "COMPLETED",
    duration_seconds: 3720,
    participant_count: 8,
    created_at: "2026-09-16T09:00:00Z",
    updated_at: "2026-09-16T10:02:00Z",
    tenant_id: "t-softude",
    created_by: "Sujal Nage",
    tags: ["product", "roadmap", "Q4"],
  },
  {
    id: "m-002",
    title: "Engineering Sprint 42 Retrospective",
    status: "COMPLETED",
    duration_seconds: 2700,
    participant_count: 6,
    created_at: "2026-09-15T14:00:00Z",
    updated_at: "2026-09-15T14:45:00Z",
    tenant_id: "t-softude",
    created_by: "Ananya Sharma",
    tags: ["engineering", "retrospective"],
  },
  {
    id: "m-003",
    title: "Client Onboarding — TechCorp Inc.",
    status: "COMPLETED",
    duration_seconds: 1800,
    participant_count: 4,
    created_at: "2026-09-15T11:00:00Z",
    updated_at: "2026-09-15T11:30:00Z",
    tenant_id: "t-softude",
    created_by: "Rahul Mehta",
    tags: ["client", "onboarding"],
  },
  {
    id: "m-004",
    title: "Design System Review — Knowra v2",
    status: "PROCESSING",
    duration_seconds: 5400,
    participant_count: 5,
    created_at: "2026-09-14T10:00:00Z",
    updated_at: "2026-09-14T11:30:00Z",
    tenant_id: "t-softude",
    created_by: "Priya Kapoor",
    tags: ["design", "ui"],
  },
  {
    id: "m-005",
    title: "All Hands — September 2026",
    status: "COMPLETED",
    duration_seconds: 6600,
    participant_count: 32,
    created_at: "2026-09-12T12:00:00Z",
    updated_at: "2026-09-12T13:50:00Z",
    tenant_id: "t-softude",
    created_by: "Sujal Nage",
    tags: ["all-hands", "strategy"],
  },
  {
    id: "m-006",
    title: "Sales Pipeline Review — Week 37",
    status: "COMPLETED",
    duration_seconds: 2100,
    participant_count: 7,
    created_at: "2026-09-11T09:30:00Z",
    updated_at: "2026-09-11T10:05:00Z",
    tenant_id: "t-softude",
    created_by: "Vikram Das",
    tags: ["sales", "pipeline"],
  },
  {
    id: "m-007",
    title: "Infrastructure Cost Optimization",
    status: "COMPLETED",
    duration_seconds: 3300,
    participant_count: 4,
    created_at: "2026-09-09T15:00:00Z",
    updated_at: "2026-09-09T15:55:00Z",
    tenant_id: "t-softude",
    created_by: "Ananya Sharma",
    tags: ["infra", "cost"],
  },
  {
    id: "m-008",
    title: "Investor Update Call — Series A",
    status: "PENDING",
    duration_seconds: undefined,
    participant_count: 3,
    created_at: "2026-09-08T16:00:00Z",
    updated_at: "2026-09-08T16:00:00Z",
    tenant_id: "t-softude",
    created_by: "Sujal Nage",
    tags: ["investor", "fundraising"],
  },
];

// Source / owner metadata (UI-only, not in base type)
export const MEETING_SOURCE: Record<string, "Zoom" | "Teams" | "Meet"> = {
  "m-001": "Teams",
  "m-002": "Zoom",
  "m-003": "Meet",
  "m-004": "Teams",
  "m-005": "Teams",
  "m-006": "Zoom",
  "m-007": "Meet",
  "m-008": "Zoom",
};

export const MEETING_OWNER: Record<string, { initials: string; name: string }> = {
  "m-001": { initials: "SN", name: "Sujal Nage" },
  "m-002": { initials: "AS", name: "Ananya Sharma" },
  "m-003": { initials: "RM", name: "Rahul Mehta" },
  "m-004": { initials: "PK", name: "Priya Kapoor" },
  "m-005": { initials: "SN", name: "Sujal Nage" },
  "m-006": { initials: "VD", name: "Vikram Das" },
  "m-007": { initials: "AS", name: "Ananya Sharma" },
  "m-008": { initials: "SN", name: "Sujal Nage" },
};

// ─── Transcript ───────────────────────────────────────────────────────────────

export const MOCK_TRANSCRIPT: Transcript = {
  id: "tr-m-001",
  meeting_id: "m-001",
  language: "en",
  created_at: "2026-09-16T10:02:30Z",
  full_text: "Complete Q4 roadmap planning session transcript...",
  segments: [
    { id: "seg-001", speaker_label: "SPEAKER_00", speaker_name: "Sujal Nage", text: "Alright, let's kick things off. The goal today is to finalize our Q4 roadmap. We have three major themes: AI enhancements, enterprise integrations, and the new mobile experience.", start_time: 8, end_time: 28, confidence: 0.97 },
    { id: "seg-002", speaker_label: "SPEAKER_01", speaker_name: "Ananya Sharma", text: "Before we dive in, I want to flag that the transcript processing pipeline is showing some latency. We should prioritize that in the infra queue for Q4.", start_time: 30, end_time: 48, confidence: 0.94 },
    { id: "seg-003", speaker_label: "SPEAKER_00", speaker_name: "Sujal Nage", text: "Noted. Ananya, can you own that task and get back to us with an ETA by end of this week?", start_time: 50, end_time: 60, confidence: 0.98 },
    { id: "seg-004", speaker_label: "SPEAKER_01", speaker_name: "Ananya Sharma", text: "Absolutely. I'll have a proposal ready by Thursday.", start_time: 61, end_time: 68, confidence: 0.99 },
    { id: "seg-005", speaker_label: "SPEAKER_02", speaker_name: "Rahul Mehta", text: "On the enterprise integrations front, the Jira and Slack connectors are 80% done. The remaining work is mainly around webhook retry logic and error handling. I'm estimating two more weeks.", start_time: 70, end_time: 95, confidence: 0.95 },
    { id: "seg-006", speaker_label: "SPEAKER_00", speaker_name: "Sujal Nage", text: "That's great progress. Let's make sure we have a demo-ready build for the investor update next week. Rahul, can we get that done by Friday?", start_time: 97, end_time: 112, confidence: 0.96 },
    { id: "seg-007", speaker_label: "SPEAKER_02", speaker_name: "Rahul Mehta", text: "Friday is tight, but I'll pull in Priya to help with the UI polish. We should be able to get a solid demo build out.", start_time: 114, end_time: 128, confidence: 0.93 },
    { id: "seg-008", speaker_label: "SPEAKER_01", speaker_name: "Ananya Sharma", text: "I want to revisit the decision on the vector database. We made a provisional choice on Pinecone in the last sprint, but Weaviate has some compelling cost advantages at scale. Should we re-evaluate?", start_time: 134, end_time: 158, confidence: 0.92 },
    { id: "seg-009", speaker_label: "SPEAKER_00", speaker_name: "Sujal Nage", text: "Good point. Let's confirm the Pinecone decision for now and schedule a dedicated architecture review in week 2 of October. We can't afford to block the roadmap on this.", start_time: 160, end_time: 180, confidence: 0.97 },
    { id: "seg-010", speaker_label: "SPEAKER_02", speaker_name: "Rahul Mehta", text: "Agreed. Locking Pinecone for Q4. I'll document the rationale and add a Q1 review flag so we revisit with proper load data.", start_time: 182, end_time: 198, confidence: 0.95 },
    { id: "seg-011", speaker_label: "SPEAKER_01", speaker_name: "Ananya Sharma", text: "For the mobile experience, the React Native prototype is looking great. The offline-first transcript viewing is particularly impressive. I think we should showcase it at the October summit.", start_time: 210, end_time: 235, confidence: 0.94 },
    { id: "seg-012", speaker_label: "SPEAKER_00", speaker_name: "Sujal Nage", text: "Confirmed. Mobile showcase at October summit is now on the agenda. Key takeaways: Ananya owns the pipeline latency fix, Rahul delivers integration demo by Friday, Pinecone locked for Q4.", start_time: 237, end_time: 268, confidence: 0.98 },
    { id: "seg-013", speaker_label: "SPEAKER_02", speaker_name: "Rahul Mehta", text: "One last thing — the risk assessment for the new LLM provider should happen before we go live in October. I'd suggest we allocate a risk review session next week.", start_time: 270, end_time: 290, confidence: 0.91 },
    { id: "seg-014", speaker_label: "SPEAKER_00", speaker_name: "Sujal Nage", text: "Added. Rahul, you're the DRI on scheduling that. Thanks everyone — great session.", start_time: 292, end_time: 304, confidence: 0.99 },
    { id: "seg-015", speaker_label: "SPEAKER_01", speaker_name: "Ananya Sharma", text: "Thanks! Talk soon.", start_time: 305, end_time: 310, confidence: 0.99 },
  ],
};

// ─── Action Items ─────────────────────────────────────────────────────────────

export const MOCK_ACTION_ITEMS: ActionItem[] = [
  { id: "act-001", title: "Propose pipeline latency fix with ETA", assignee: "Ananya Sharma", due_date: "2026-09-19T00:00:00Z", status: "OPEN", meeting_id: "m-001", segment_id: "seg-003", created_at: "2026-09-16T10:02:30Z" },
  { id: "act-002", title: "Deliver demo-ready integration build (Jira + Slack)", assignee: "Rahul Mehta", due_date: "2026-09-20T00:00:00Z", status: "IN_PROGRESS", meeting_id: "m-001", segment_id: "seg-006", created_at: "2026-09-16T10:02:30Z" },
  { id: "act-003", title: "Document Pinecone rationale and add Q1 review flag", assignee: "Rahul Mehta", due_date: "2026-09-23T00:00:00Z", status: "OPEN", meeting_id: "m-001", segment_id: "seg-010", created_at: "2026-09-16T10:02:30Z" },
  { id: "act-004", title: "Schedule LLM provider risk review session", assignee: "Rahul Mehta", due_date: "2026-09-23T00:00:00Z", status: "OPEN", meeting_id: "m-001", segment_id: "seg-013", created_at: "2026-09-16T10:02:30Z" },
  { id: "act-005", title: "Coordinate mobile showcase slot for October summit", assignee: "Sujal Nage", due_date: "2026-09-25T00:00:00Z", status: "OPEN", meeting_id: "m-001", segment_id: "seg-012", created_at: "2026-09-16T10:02:30Z" },
];

// ─── Decisions ────────────────────────────────────────────────────────────────

export const MOCK_DECISIONS: Decision[] = [
  { id: "dec-001", title: "Pinecone confirmed as vector database for Q4", summary: "After brief re-evaluation of Weaviate, the team locked Pinecone for Q4 to avoid roadmap disruption. A Q1 architectural review will be scheduled with proper load data.", made_by: "Sujal Nage", confidence: 0.96, meeting_id: "m-001", segment_id: "seg-009", created_at: "2026-09-16T10:02:30Z" },
  { id: "dec-002", title: "Mobile experience to be showcased at October summit", summary: "The React Native offline-first prototype is ready for a summit showcase. This feature will be highlighted as a key enterprise differentiator.", made_by: "Sujal Nage", confidence: 0.98, meeting_id: "m-001", segment_id: "seg-012", created_at: "2026-09-16T10:02:30Z" },
  { id: "dec-003", title: "LLM provider risk review before October go-live", summary: "A dedicated risk assessment session will be held before the new LLM provider goes live in October.", made_by: "Sujal Nage", confidence: 0.91, meeting_id: "m-001", segment_id: "seg-014", created_at: "2026-09-16T10:02:30Z" },
];

// ─── AI Summary ───────────────────────────────────────────────────────────────

export const MOCK_SUMMARY = `The team held a comprehensive Q4 roadmap planning session covering three strategic themes: AI enhancements, enterprise integrations, and the new mobile experience.

**Infrastructure:** Ananya flagged transcript processing latency as a priority. She will deliver a remediation proposal by Thursday.

**Integrations:** The Jira and Slack connectors are 80% complete. Rahul will deliver a demo-ready build by Friday with support from Priya on UI polish.

**Vector Database:** After a brief discussion on Weaviate cost advantages, the team confirmed Pinecone as the Q4 vector database. A Q1 architectural review was added to the calendar.

**Mobile:** The React Native prototype impressed the team. A showcase slot has been confirmed for the October summit.

**Risk:** A LLM provider risk review session will be scheduled before the October production go-live.`;

// ─── Chapters (Topics) ───────────────────────────────────────────────────────

export interface Chapter {
  id: string;
  title: string;
  start_time: number;
  end_time: number;
  emoji?: string;
}

export const MOCK_CHAPTERS: Chapter[] = [
  { id: "ch-1", title: "Intro & Agenda", start_time: 0, end_time: 30, emoji: "📋" },
  { id: "ch-2", title: "Infrastructure Latency", start_time: 30, end_time: 70, emoji: "⚡" },
  { id: "ch-3", title: "Enterprise Integrations", start_time: 70, end_time: 134, emoji: "🔗" },
  { id: "ch-4", title: "Vector DB Decision", start_time: 134, end_time: 210, emoji: "🗃️" },
  { id: "ch-5", title: "Mobile Experience", start_time: 210, end_time: 250, emoji: "📱" },
  { id: "ch-6", title: "Wrap-up & Action Items", start_time: 250, end_time: 320, emoji: "✅" },
];

export const MOCK_SPEAKERS = [
  { id: "SPEAKER_00", label: "SPEAKER_00", displayName: "Sujal Nage", talkTime: 145, initials: "SN" },
  { id: "SPEAKER_01", label: "SPEAKER_01", displayName: "Ananya Sharma", talkTime: 98, initials: "AS" },
  { id: "SPEAKER_02", label: "SPEAKER_02", displayName: "Rahul Mehta", talkTime: 72, initials: "RM" },
];

export function getSegmentTimestamp(segmentId: string | null | undefined): number {
  if (!segmentId) return 0;
  const seg = MOCK_TRANSCRIPT.segments.find((s) => s.id === segmentId);
  return seg?.start_time ?? 0;
}
