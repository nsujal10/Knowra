/**
 * Knowra — Zod Schemas & TypeScript Types
 * Single source of truth for all backend API response shapes.
 */
import { z } from "zod";

// ─── Common ──────────────────────────────────────────────────────────────────

export const UUIDSchema = z.string().uuid();

export const PaginatedResponseSchema = <T extends z.ZodTypeAny>(schema: T) =>
  z.object({
    items: z.array(schema),
    total: z.number(),
    page: z.number(),
    page_size: z.number(),
    has_more: z.boolean().optional(),
  });

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const UserSchema = z.object({
  id: z.string(),
  email: z.string().email(),
  full_name: z.string(),
  role_code: z.string(),
  tenant_id: z.string(),
  is_active: z.boolean(),
});
export type User = z.infer<typeof UserSchema>;

export const SessionSchema = z.object({
  access_token: z.string(),
  refresh_token: z.string().optional(),
  token_type: z.string().default("bearer"),
  user: UserSchema,
  tenant_id: z.string(),
});
export type Session = z.infer<typeof SessionSchema>;

// ─── Meetings ─────────────────────────────────────────────────────────────────

export const MeetingStatus = z.enum([
  "PENDING",
  "PROCESSING",
  "COMPLETED",
  "FAILED",
]);

export const MeetingSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().nullable().optional(),
  status: MeetingStatus,
  duration_seconds: z.number().nullable().optional(),
  participant_count: z.number().nullable().optional(),
  created_at: z.string(),
  updated_at: z.string(),
  tenant_id: z.string(),
  created_by: z.string().nullable().optional(),
  tags: z.array(z.string()).optional(),
});
export type Meeting = z.infer<typeof MeetingSchema>;

// ─── Transcripts ─────────────────────────────────────────────────────────────

export const TranscriptSegmentSchema = z.object({
  id: z.string(),
  speaker_label: z.string().nullable().optional(),
  speaker_name: z.string().nullable().optional(),
  text: z.string(),
  start_time: z.number(),
  end_time: z.number(),
  confidence: z.number().nullable().optional(),
});
export type TranscriptSegment = z.infer<typeof TranscriptSegmentSchema>;

export const TranscriptSchema = z.object({
  id: z.string(),
  meeting_id: z.string(),
  segments: z.array(TranscriptSegmentSchema),
  full_text: z.string().optional(),
  language: z.string().optional(),
  created_at: z.string(),
});
export type Transcript = z.infer<typeof TranscriptSchema>;

// ─── Chat ─────────────────────────────────────────────────────────────────────

export const CitationSchema = z.object({
  chunk_id: z.string(),
  segment_id: z.string().optional(),
  meeting_id: z.string().nullable().optional(),
  meeting_title: z.string().nullable().optional(),
  text: z.string().optional(),
  quote: z.string().optional(),
  speaker: z.string().nullable().optional(),
  speaker_name: z.string().nullable().optional(),
  timestamp: z.number().optional(),
  start_seconds: z.number().optional(),
  end_seconds: z.number().optional(),
  relevance_score: z.number().optional(),
  verified: z.boolean().optional(),
});
export type Citation = z.infer<typeof CitationSchema>;

export const ChatMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  citations: z.array(CitationSchema).optional(),
  created_at: z.string(),
});
export type ChatMessage = z.infer<typeof ChatMessageSchema>;

export const ChatSessionSchema = z.object({
  id: z.string(),
  title: z.string().optional(),
  meeting_id: z.string().nullable().optional(),
  messages: z.array(ChatMessageSchema).optional(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type ChatSession = z.infer<typeof ChatSessionSchema>;

// ─── Cross-Meeting Intelligence ───────────────────────────────────────────────

export const TimelineEventSchema = z.object({
  id: z.string(),
  event_type: z.string(),
  entity_name: z.string(),
  entity_type: z.string(),
  meeting_id: z.string(),
  meeting_title: z.string(),
  segment_id: z.string().nullable().optional(),
  speaker: z.string().nullable().optional(),
  summary: z.string(),
  occurred_at: z.string(),
  evidence_text: z.string().optional(),
});
export type TimelineEvent = z.infer<typeof TimelineEventSchema>;

// ─── Knowledge Graph ─────────────────────────────────────────────────────────

export const GraphNodeSchema = z.object({
  id: z.string(),
  label: z.string(),
  type: z.enum(["person", "topic", "decision", "meeting", "action", "entity"]),
  metadata: z.record(z.unknown()).optional(),
  mention_count: z.number().optional(),
});
export type GraphNode = z.infer<typeof GraphNodeSchema>;

export const GraphEdgeSchema = z.object({
  id: z.string(),
  source: z.string(),
  target: z.string(),
  label: z.string().optional(),
  weight: z.number().optional(),
  meeting_id: z.string().optional(),
});
export type GraphEdge = z.infer<typeof GraphEdgeSchema>;

export const GraphDataSchema = z.object({
  nodes: z.array(GraphNodeSchema),
  edges: z.array(GraphEdgeSchema),
});
export type GraphData = z.infer<typeof GraphDataSchema>;

// ─── Evaluation ───────────────────────────────────────────────────────────────

export const EvaluationMetricsSchema = z.object({
  wer: z.number().nullable().optional(),
  cer: z.number().nullable().optional(),
  der: z.number().nullable().optional(),
  faithfulness: z.number().nullable().optional(),
  answer_relevance: z.number().nullable().optional(),
  context_precision: z.number().nullable().optional(),
  context_recall: z.number().nullable().optional(),
});
export type EvaluationMetrics = z.infer<typeof EvaluationMetricsSchema>;

export const EvaluationRunSchema = z.object({
  id: z.string(),
  pipeline_version: z.string(),
  dataset_name: z.string(),
  metrics: EvaluationMetricsSchema,
  status: z.enum(["PASSED", "REGRESSED", "FAILED"]),
  created_at: z.string(),
});
export type EvaluationRun = z.infer<typeof EvaluationRunSchema>;

export const AITraceSchema = z.object({
  id: z.string(),
  request_id: z.string(),
  stage: z.enum(["QUERY_REWRITE", "RETRIEVAL", "GENERATION"]),
  latency_ms: z.number(),
  prompt_tokens: z.number(),
  completion_tokens: z.number(),
  estimated_cost_usd: z.number(),
  error_message: z.string().nullable().optional(),
  created_at: z.string(),
});
export type AITrace = z.infer<typeof AITraceSchema>;

export const QualityOverviewSchema = z.object({
  avg_faithfulness: z.number(),
  avg_answer_relevance: z.number(),
  avg_wer: z.number().nullable().optional(),
  hallucination_rate: z.number(),
  total_runs: z.number(),
  passed_runs: z.number(),
});
export type QualityOverview = z.infer<typeof QualityOverviewSchema>;

export const CostSummarySchema = z.object({
  total_cost_usd: z.number(),
  total_prompt_tokens: z.number(),
  total_completion_tokens: z.number(),
  cost_by_stage: z.record(z.number()).optional(),
  period_days: z.number(),
});
export type CostSummary = z.infer<typeof CostSummarySchema>;

// ─── Integrations ─────────────────────────────────────────────────────────────

export const IntegrationProviderSchema = z.enum([
  "SLACK",
  "TEAMS",
  "JIRA",
  "WEBHOOK",
  "EMAIL",
]);
export type IntegrationProvider = z.infer<typeof IntegrationProviderSchema>;

export const IntegrationStatusSchema = z.enum(["ACTIVE", "INACTIVE", "ERROR"]);

export const IntegrationSchema = z.object({
  id: z.string(),
  tenant_id: z.string().optional(),
  provider: z.string(),
  name: z.string().optional(),
  status: z.string(),
  webhook_url: z.string().nullable().optional(),
  channel_or_project_id: z.string().nullable().optional(),
  channel_or_project: z.string().nullable().optional(),
  events_subscribed: z.array(z.string()).optional(),
  metadata_json: z.record(z.any()).optional(),
  created_at: z.string(),
  updated_at: z.string(),
});
export type Integration = z.infer<typeof IntegrationSchema>;

export interface IntegrationEvent {
  id: string;
  tenant_id: string;
  integration_id?: string;
  direction: string;
  external_event_id: string;
  event_type: string;
  status: string;
  attempt_count: number;
  max_retries: number;
  payload_json: Record<string, any>;
  response_status_code?: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
}

export interface TestDispatchResponse {
  integration_id: string;
  event_type: string;
  dispatched: boolean;
  status: string;
  detail: string;
}

// ─── Actions & Decisions ──────────────────────────────────────────────────────

export const ActionItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  description: z.string().nullable().optional(),
  assignee: z.string().nullable().optional(),
  owner_raw: z.string().nullable().optional(),
  owner_id: z.string().nullable().optional(),
  due_date: z.string().nullable().optional(),
  due_date_raw: z.string().nullable().optional(),
  status: z.string(),
  priority: z.string().nullable().optional(),
  meeting_id: z.string(),
  meeting_title: z.string().nullable().optional(),
  segment_id: z.string().nullable().optional(),
  timestamp: z.string().nullable().optional(),
  start_seconds: z.number().nullable().optional(),
  evidence_snippet: z.string().nullable().optional(),
  evidence_segment_ids: z.array(z.string()).optional(),
  created_at: z.string(),
  completed_at: z.string().nullable().optional(),
});
export type ActionItem = z.infer<typeof ActionItemSchema>;
export type ActionItemDetail = ActionItem;

export const ActionsMetricsSchema = z.object({
  total_items: z.number(),
  pending_count: z.number(),
  completed_count: z.number(),
  urgent_count: z.number(),
  completion_rate: z.string(),
});
export type ActionsMetrics = z.infer<typeof ActionsMetricsSchema>;

export const ActionMeetingSummarySchema = z.object({
  id: z.string(),
  title: z.string(),
  action_count: z.number(),
});
export type ActionMeetingSummary = z.infer<typeof ActionMeetingSummarySchema>;

export const EnterpriseActionsResponseSchema = z.object({
  items: z.array(ActionItemSchema),
  total: z.number(),
  metrics: ActionsMetricsSchema,
  meetings: z.array(ActionMeetingSummarySchema),
  owners: z.array(z.string()),
});
export type EnterpriseActionsResponse = z.infer<typeof EnterpriseActionsResponseSchema>;


export const DecisionSchema = z.object({
  id: z.string(),
  title: z.string(),
  summary: z.string().optional(),
  description: z.string().optional(),
  rationale: z.string().nullable().optional(),
  made_by: z.string().nullable().optional(),
  decided_by: z.string().nullable().optional(),
  confidence: z.number().nullable().optional(),
  meeting_id: z.string(),
  meeting_title: z.string().nullable().optional(),
  segment_id: z.string().nullable().optional(),
  category: z.string().optional(),
  status: z.string().optional(),
  impact_level: z.string().optional(),
  timestamp: z.string().nullable().optional(),
  start_seconds: z.number().nullable().optional(),
  evidence_snippet: z.string().nullable().optional(),
  created_at: z.string(),
});
export type Decision = z.infer<typeof DecisionSchema>;

export const EnterpriseDecisionItemSchema = z.object({
  id: z.string(),
  meeting_id: z.string(),
  meeting_title: z.string().nullable().optional(),
  title: z.string(),
  description: z.string(),
  rationale: z.string().nullable().optional(),
  status: z.string(),
  impact_level: z.string(),
  category: z.string(),
  decided_by: z.string().nullable().optional(),
  timestamp: z.string().nullable().optional(),
  start_seconds: z.number().nullable().optional(),
  evidence_snippet: z.string().nullable().optional(),
  evidence_segment_ids: z.array(z.string()).optional(),
  created_at: z.string(),
});
export type EnterpriseDecisionItem = z.infer<typeof EnterpriseDecisionItemSchema>;

export const DecisionsMetricsSchema = z.object({
  total_decisions: z.number(),
  consensus_level: z.string(),
  ai_verified: z.string(),
  confirmed_count: z.number(),
  superseded_count: z.number(),
});
export type DecisionsMetrics = z.infer<typeof DecisionsMetricsSchema>;

export const MeetingSummaryItemSchema = z.object({
  id: z.string(),
  title: z.string(),
  decision_count: z.number(),
});
export type MeetingSummaryItem = z.infer<typeof MeetingSummaryItemSchema>;

export const EnterpriseDecisionsResponseSchema = z.object({
  items: z.array(EnterpriseDecisionItemSchema),
  total: z.number(),
  metrics: DecisionsMetricsSchema,
  meetings: z.array(MeetingSummaryItemSchema),
});
export type EnterpriseDecisionsResponse = z.infer<typeof EnterpriseDecisionsResponseSchema>;

