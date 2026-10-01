"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { MEETINGS, EVALUATION, ACTIONS, DECISIONS, CHAT } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import {
  type Meeting,
  type ChatSession,
  type EnterpriseActionsResponse,
  type EnterpriseDecisionsResponse,
} from "@/lib/types";
import { Spinner } from "@/components/ui/card";
import { cn, relativeTime, formatDuration } from "@/lib/utils";
import {
  Video,
  Brain,
  DollarSign,
  CheckCircle2,
  TrendingUp,
  Clock,
  MessageSquare,
  Target,
  Gavel,
  ArrowRight,
  Sparkles,
  Users,
  ChevronRight,
  Activity,
  BarChart3,
  ShieldCheck,
  Zap,
  Plus,
} from "lucide-react";
import Link from "next/link";

// ─── Backend response types (match actual API schemas) ────────────────────────
interface BackendQualityOverview {
  tenant_id: string;
  average_wer: number | null;
  average_der: number | null;
  average_faithfulness: number | null;
  average_answer_relevance: number | null;
  hallucination_rate: number | null;
  total_evaluations: number;
  regression_count: number;
}

interface BackendCostAggregation {
  tenant_id: string;
  total_traces: number;
  total_prompt_tokens: number;
  total_completion_tokens: number;
  total_tokens: number;
  total_estimated_cost_usd: number;
  by_stage: Record<string, { total_tokens: number; cost_usd: number; count: number }>;
  by_model: Record<string, { total_tokens: number; cost_usd: number; count: number }>;
}

export default function DashboardPage() {
  // ─── Data Fetching (all real backend APIs) ──────────────────────────────────
  const { data: rawMeetings, isLoading: meetingsLoading } = useQuery({
    queryKey: queryKeys.meetings.list(),
    queryFn: () => api.get<{ items: Meeting[]; total: number } | Meeting[]>(MEETINGS.list()),
  });
  const meetings: Meeting[] = useMemo(() => {
    if (Array.isArray(rawMeetings)) return rawMeetings;
    if (rawMeetings && Array.isArray((rawMeetings as { items?: Meeting[] }).items)) {
      return (rawMeetings as { items: Meeting[] }).items;
    }
    return [];
  }, [rawMeetings]);
  const totalMeetings = Array.isArray(rawMeetings)
    ? rawMeetings.length
    : (rawMeetings as { total?: number })?.total ?? meetings.length;

  const { data: quality, isLoading: qualityLoading } = useQuery({
    queryKey: queryKeys.evaluation.quality(),
    queryFn: () => api.get<BackendQualityOverview>(EVALUATION.quality()),
  });

  const { data: costs, isLoading: costsLoading } = useQuery({
    queryKey: queryKeys.evaluation.costs(),
    queryFn: () => api.get<BackendCostAggregation>(EVALUATION.costs()),
  });

  const { data: rawActions, isLoading: actionsLoading } = useQuery({
    queryKey: queryKeys.actions.byMeeting(),
    queryFn: () => api.get<EnterpriseActionsResponse>(ACTIONS.list()),
  });

  const { data: rawDecisions, isLoading: decisionsLoading } = useQuery({
    queryKey: queryKeys.decisions.byMeeting(),
    queryFn: () => api.get<EnterpriseDecisionsResponse>(DECISIONS.list()),
  });

  const { data: rawSessions, isLoading: sessionsLoading } = useQuery({
    queryKey: queryKeys.chat.sessions(),
    queryFn: () => api.get<ChatSession[] | { items: ChatSession[] }>(CHAT.sessions()),
  });
  const chatSessions: ChatSession[] = useMemo(() => {
    if (Array.isArray(rawSessions)) return rawSessions;
    if (rawSessions && Array.isArray((rawSessions as { items?: ChatSession[] }).items)) {
      return (rawSessions as { items: ChatSession[] }).items;
    }
    return [];
  }, [rawSessions]);

  // ─── Derived metrics ────────────────────────────────────────────────────────
  const recentMeetings = meetings.slice(0, 6);
  const actionMetrics = rawActions?.metrics;
  const decisionMetrics = rawDecisions?.metrics;
  const recentActions = (rawActions?.items ?? []).slice(0, 5);
  const recentDecisions = (rawDecisions?.items ?? []).slice(0, 5);
  const recentChats = chatSessions.slice(0, 5);

  const completedMeetings = meetings.filter((m) => m.status === "COMPLETED").length;
  const processingMeetings = meetings.filter((m) => m.status === "PROCESSING").length;
  const totalParticipants = meetings.reduce((sum, m) => sum + (m.participant_count ?? 0), 0);
  const totalDuration = meetings.reduce((sum, m) => sum + (m.duration_seconds ?? 0), 0);

  const formatCostValue = (usd: number | null | undefined): string => {
    if (usd === null || usd === undefined || isNaN(usd)) return "$0.00";
    if (usd < 0.01) return `$${usd.toFixed(4)}`;
    return `$${usd.toFixed(2)}`;
  };

  const formatPct = (v: number | null | undefined): string => {
    if (v === null || v === undefined) return "—";
    return `${(v * 100).toFixed(1)}%`;
  };

  return (
    <div className="space-y-6 animate-fade-in">
      {/* ─── Page Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Overview of your meeting intelligence pipeline
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/chat"
            className="inline-flex items-center gap-2 h-9 px-4 rounded-lg bg-indigo-600 text-white text-sm font-medium shadow-xs hover:bg-indigo-700 transition-colors"
          >
            <Sparkles size={14} />
            Ask Knowra
          </Link>
        </div>
      </div>

      {/* ─── Stats Grid ──────────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Video size={18} />}
          label="Total Meetings"
          value={totalMeetings.toString()}
          sub={
            completedMeetings > 0
              ? `${completedMeetings} completed${processingMeetings > 0 ? ` · ${processingMeetings} processing` : ""}`
              : "all time"
          }
          color="indigo"
          loading={meetingsLoading}
        />
        <StatCard
          icon={<Target size={18} />}
          label="Action Items"
          value={actionMetrics?.total_items?.toString() ?? "0"}
          sub={
            actionMetrics
              ? `${actionMetrics.pending_count} pending · ${actionMetrics.completion_rate}`
              : "tracked across meetings"
          }
          color="amber"
          loading={actionsLoading}
        />
        <StatCard
          icon={<Gavel size={18} />}
          label="Decisions"
          value={decisionMetrics?.total_decisions?.toString() ?? "0"}
          sub={
            decisionMetrics
              ? `${decisionMetrics.confirmed_count} confirmed · ${decisionMetrics.consensus_level}`
              : "extracted from meetings"
          }
          color="emerald"
          loading={decisionsLoading}
        />
        <StatCard
          icon={<DollarSign size={18} />}
          label="AI Cost"
          value={formatCostValue(costs?.total_estimated_cost_usd)}
          sub={
            costs
              ? `${costs.total_tokens.toLocaleString()} tokens · ${costs.total_traces} traces`
              : "—"
          }
          color="slate"
          loading={costsLoading}
        />
      </div>

      {/* ─── Main Content Grid ───────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* ─── Left Column: Recent Meetings ────────────────────────────────── */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Video size={15} className="text-slate-400" />
                <h2 className="text-sm font-semibold text-slate-800">Recent Meetings</h2>
                <span className="px-1.5 py-0.5 rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">
                  {totalMeetings}
                </span>
              </div>
              <Link
                href="/meetings"
                className="text-xs font-medium text-indigo-600 hover:text-indigo-700 flex items-center gap-1 transition-colors"
              >
                View all <ArrowRight size={12} />
              </Link>
            </div>
            <div className="divide-y divide-slate-50">
              {meetingsLoading ? (
                <div className="flex justify-center py-12">
                  <Spinner size={20} />
                </div>
              ) : recentMeetings.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-12 gap-2 text-center">
                  <Video size={28} className="text-slate-300" />
                  <p className="text-sm text-slate-500">No meetings processed yet</p>
                  <p className="text-xs text-slate-400">
                    Upload a recording or connect a calendar integration to get started.
                  </p>
                </div>
              ) : (
                recentMeetings.map((m) => (
                  <MeetingRow key={m.id} meeting={m} />
                ))
              )}
            </div>
          </div>

          {/* ─── Activity Feed ───────────────────────────────────────────────── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Recent Actions */}
            <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Target size={14} className="text-amber-500" />
                  <h3 className="text-sm font-semibold text-slate-800">Recent Actions</h3>
                </div>
                <Link
                  href="/actions"
                  className="text-[11px] font-medium text-indigo-600 hover:text-indigo-700"
                >
                  View all
                </Link>
              </div>
              <div className="divide-y divide-slate-50">
                {actionsLoading ? (
                  <div className="flex justify-center py-8">
                    <Spinner size={16} />
                  </div>
                ) : recentActions.length === 0 ? (
                  <div className="py-8 text-center">
                    <p className="text-xs text-slate-400">No action items yet</p>
                  </div>
                ) : (
                  recentActions.map((a) => (
                    <div
                      key={a.id}
                      className="px-4 py-2.5 flex items-start gap-2.5 hover:bg-slate-50/50 transition-colors"
                    >
                      <div
                        className={cn(
                          "mt-0.5 w-1.5 h-1.5 rounded-full shrink-0",
                          a.status === "COMPLETED"
                            ? "bg-emerald-500"
                            : a.priority === "URGENT" || a.priority === "HIGH"
                              ? "bg-red-500"
                              : "bg-amber-400"
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-slate-700 truncate leading-tight">
                          {a.title}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5 truncate">
                          {a.assignee ?? a.owner_raw ?? "Unassigned"}
                          {a.meeting_title ? ` · ${a.meeting_title}` : ""}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full shrink-0",
                          a.status === "COMPLETED"
                            ? "bg-emerald-50 text-emerald-600"
                            : "bg-slate-100 text-slate-500"
                        )}
                      >
                        {a.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent Decisions */}
            <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Gavel size={14} className="text-emerald-500" />
                  <h3 className="text-sm font-semibold text-slate-800">Recent Decisions</h3>
                </div>
                <Link
                  href="/decisions"
                  className="text-[11px] font-medium text-indigo-600 hover:text-indigo-700"
                >
                  View all
                </Link>
              </div>
              <div className="divide-y divide-slate-50">
                {decisionsLoading ? (
                  <div className="flex justify-center py-8">
                    <Spinner size={16} />
                  </div>
                ) : recentDecisions.length === 0 ? (
                  <div className="py-8 text-center">
                    <p className="text-xs text-slate-400">No decisions extracted yet</p>
                  </div>
                ) : (
                  recentDecisions.map((d) => (
                    <div
                      key={d.id}
                      className="px-4 py-2.5 flex items-start gap-2.5 hover:bg-slate-50/50 transition-colors"
                    >
                      <div
                        className={cn(
                          "mt-0.5 w-1.5 h-1.5 rounded-full shrink-0",
                          d.status === "CONFIRMED" || d.status === "APPROVED"
                            ? "bg-emerald-500"
                            : d.status === "SUPERSEDED"
                              ? "bg-slate-400"
                              : "bg-blue-400"
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-slate-700 truncate leading-tight">
                          {d.title}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5 truncate">
                          {d.decided_by ?? "—"}
                          {d.meeting_title ? ` · ${d.meeting_title}` : ""}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "text-[9px] font-semibold uppercase tracking-wider px-1.5 py-0.5 rounded-full shrink-0",
                          d.impact_level === "HIGH" || d.impact_level === "CRITICAL"
                            ? "bg-red-50 text-red-600"
                            : d.impact_level === "MEDIUM"
                              ? "bg-amber-50 text-amber-600"
                              : "bg-slate-100 text-slate-500"
                        )}
                      >
                        {d.impact_level}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ─── Right Column: Quality, Costs, Chats ─────────────────────────── */}
        <div className="space-y-4">
          {/* AI Quality Card */}
          <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck size={14} className="text-indigo-500" />
                <h3 className="text-sm font-semibold text-slate-800">AI Quality</h3>
              </div>
              <Link
                href="/evaluation"
                className="text-[11px] font-medium text-indigo-600 hover:text-indigo-700"
              >
                Details →
              </Link>
            </div>
            <div className="p-4 space-y-3">
              {qualityLoading ? (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-4 bg-slate-100 rounded animate-pulse" />
                  ))}
                </div>
              ) : quality ? (
                <>
                  <MetricRow label="Faithfulness" value={quality.average_faithfulness} />
                  <MetricRow label="Answer Relevance" value={quality.average_answer_relevance} />
                  <MetricRow
                    label="Hallucination Rate"
                    value={quality.hallucination_rate != null ? 1 - quality.hallucination_rate : null}
                    invert
                  />
                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-xs">
                    <span className="text-slate-500">Eval Runs</span>
                    <span className="font-medium text-slate-700 flex items-center gap-1">
                      <CheckCircle2 size={12} className="text-emerald-500" />
                      {quality.total_evaluations - quality.regression_count}/{quality.total_evaluations} passed
                    </span>
                  </div>
                </>
              ) : (
                <p className="text-xs text-slate-400 text-center py-4">
                  No evaluation data available yet
                </p>
              )}
            </div>
          </div>

          {/* Token Usage Card */}
          <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BarChart3 size={14} className="text-slate-500" />
                <h3 className="text-sm font-semibold text-slate-800">Token Usage</h3>
              </div>
            </div>
            <div className="p-4 space-y-2.5">
              {costsLoading ? (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-4 bg-slate-100 rounded animate-pulse" />
                  ))}
                </div>
              ) : costs ? (
                <>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Prompt Tokens</span>
                    <span className="text-slate-800 font-mono font-medium">
                      {costs.total_prompt_tokens.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Completion Tokens</span>
                    <span className="text-slate-800 font-mono font-medium">
                      {costs.total_completion_tokens.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Total Tokens</span>
                    <span className="text-slate-800 font-mono font-medium">
                      {costs.total_tokens.toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs pt-2 border-t border-slate-100">
                    <span className="text-slate-500">Total Cost</span>
                    <span className="text-indigo-600 font-semibold font-mono">
                      {formatCostValue(costs.total_estimated_cost_usd)}
                    </span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-500">Traces</span>
                    <span className="text-slate-800 font-mono font-medium">
                      {costs.total_traces.toLocaleString()}
                    </span>
                  </div>
                  {/* Stage breakdown */}
                  {Object.keys(costs.by_stage).length > 0 && (
                    <div className="pt-2 border-t border-slate-100 space-y-1.5">
                      <p className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                        By Stage
                      </p>
                      {Object.entries(costs.by_stage).map(([stage, data]) => (
                        <div key={stage} className="flex justify-between text-[11px]">
                          <span className="text-slate-500 capitalize">
                            {stage.toLowerCase().replace(/_/g, " ")}
                          </span>
                          <span className="text-slate-700 font-mono">
                            {formatCostValue(data.cost_usd)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              ) : (
                <p className="text-xs text-slate-400 text-center py-4">
                  No cost data available
                </p>
              )}
            </div>
          </div>

          {/* Recent Chats */}
          <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MessageSquare size={14} className="text-indigo-500" />
                <h3 className="text-sm font-semibold text-slate-800">Recent Chats</h3>
                {chatSessions.length > 0 && (
                  <span className="px-1.5 py-0.5 rounded-full bg-slate-100 text-[10px] font-semibold text-slate-600">
                    {chatSessions.length}
                  </span>
                )}
              </div>
              <Link
                href="/chat"
                className="text-[11px] font-medium text-indigo-600 hover:text-indigo-700"
              >
                Open Knowra
              </Link>
            </div>
            <div className="divide-y divide-slate-50">
              {sessionsLoading ? (
                <div className="flex justify-center py-8">
                  <Spinner size={16} />
                </div>
              ) : recentChats.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 gap-2 text-center px-4">
                  <MessageSquare size={24} className="text-slate-300" />
                  <p className="text-xs text-slate-400">
                    No conversations yet. Start asking questions in the Knowra.
                  </p>
                  <Link
                    href="/chat"
                    className="inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 hover:text-indigo-700 mt-1"
                  >
                    <Plus size={12} />
                    New Chat
                  </Link>
                </div>
              ) : (
                recentChats.map((session) => (
                  <Link
                    key={session.id}
                    href="/chat"
                    className="px-4 py-2.5 flex items-center gap-2.5 hover:bg-slate-50/50 transition-colors group"
                  >
                    <div className="w-7 h-7 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0">
                      <Sparkles size={12} className="text-indigo-500" />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-xs font-medium text-slate-700 truncate group-hover:text-indigo-600 transition-colors">
                        {session.title || "Untitled Chat"}
                      </p>
                      <p className="text-[10px] text-slate-400 mt-0.5 flex items-center gap-1">
                        <Clock size={9} />
                        {relativeTime(session.updated_at)}
                      </p>
                    </div>
                    <ChevronRight
                      size={12}
                      className="text-slate-300 group-hover:text-indigo-400 transition-colors shrink-0"
                    />
                  </Link>
                ))
              )}
            </div>
          </div>

          {/* Pipeline Overview */}
          <div className="bg-white border border-slate-200/80 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-100 flex items-center gap-2">
              <Zap size={14} className="text-amber-500" />
              <h3 className="text-sm font-semibold text-slate-800">Pipeline</h3>
            </div>
            <div className="p-4 space-y-2">
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Users size={11} />
                  Total Participants
                </span>
                <span className="text-slate-800 font-medium">{totalParticipants}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Clock size={11} />
                  Total Duration
                </span>
                <span className="text-slate-800 font-medium">{formatDuration(totalDuration)}</span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <Activity size={11} />
                  Processing
                </span>
                <span className={cn("font-medium", processingMeetings > 0 ? "text-amber-600" : "text-slate-800")}>
                  {processingMeetings} meetings
                </span>
              </div>
              <div className="flex justify-between text-xs">
                <span className="text-slate-500 flex items-center gap-1.5">
                  <CheckCircle2 size={11} />
                  Completed
                </span>
                <span className="text-emerald-600 font-medium">{completedMeetings} meetings</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Sub-Components ───────────────────────────────────────────────────────────

function StatCard({
  icon,
  label,
  value,
  sub,
  color,
  loading,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  color: "indigo" | "amber" | "emerald" | "slate";
  loading?: boolean;
}) {
  const colorMap = {
    indigo: {
      bg: "bg-indigo-50",
      text: "text-indigo-600",
      ring: "ring-indigo-100",
    },
    amber: {
      bg: "bg-amber-50",
      text: "text-amber-600",
      ring: "ring-amber-100",
    },
    emerald: {
      bg: "bg-emerald-50",
      text: "text-emerald-600",
      ring: "ring-emerald-100",
    },
    slate: {
      bg: "bg-slate-100",
      text: "text-slate-600",
      ring: "ring-slate-200",
    },
  };

  const c = colorMap[color];

  return (
    <div className="bg-white border border-slate-200/80 rounded-xl p-4 hover:border-slate-300/80 transition-colors">
      <div className="flex items-start gap-3">
        <div className={cn("p-2 rounded-lg ring-1", c.bg, c.text, c.ring)}>
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
            {label}
          </p>
          {loading ? (
            <div className="h-6 w-14 mt-1 bg-slate-100 rounded animate-pulse" />
          ) : (
            <p className="text-xl font-bold text-slate-900 leading-tight">{value}</p>
          )}
          <p className="text-[10px] text-slate-400 mt-0.5 truncate">{sub}</p>
        </div>
      </div>
    </div>
  );
}

function MeetingRow({ meeting }: { meeting: Meeting }) {
  const statusConfig: Record<string, { dot: string; label: string; bg: string }> = {
    COMPLETED: { dot: "bg-emerald-500", label: "Completed", bg: "bg-emerald-50 text-emerald-700" },
    PROCESSING: { dot: "bg-amber-500 animate-pulse", label: "Processing", bg: "bg-amber-50 text-amber-700" },
    PENDING: { dot: "bg-slate-400", label: "Pending", bg: "bg-slate-100 text-slate-600" },
    FAILED: { dot: "bg-red-500", label: "Failed", bg: "bg-red-50 text-red-700" },
  };

  const status = statusConfig[meeting.status] ?? statusConfig.PENDING;

  return (
    <Link
      href={`/meetings/${meeting.id}`}
      className="flex items-center gap-3 px-5 py-3 hover:bg-slate-50/50 transition-colors group"
    >
      <div className="w-9 h-9 rounded-lg bg-indigo-50 flex items-center justify-center shrink-0 ring-1 ring-indigo-100/60">
        <Video size={15} className="text-indigo-500" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-800 truncate group-hover:text-indigo-600 transition-colors">
          {meeting.title}
        </p>
        <div className="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
          <span className="flex items-center gap-1">
            <Clock size={9} />
            {relativeTime(meeting.created_at)}
          </span>
          {meeting.duration_seconds != null && meeting.duration_seconds > 0 && (
            <>
              <span className="text-slate-300">·</span>
              <span>{formatDuration(meeting.duration_seconds)}</span>
            </>
          )}
          {meeting.participant_count != null && meeting.participant_count > 0 && (
            <>
              <span className="text-slate-300">·</span>
              <span className="flex items-center gap-0.5">
                <Users size={9} />
                {meeting.participant_count}
              </span>
            </>
          )}
        </div>
      </div>
      <div className="flex items-center gap-1.5 shrink-0">
        <span className={cn("w-1.5 h-1.5 rounded-full", status.dot)} />
        <span className={cn("text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded-full", status.bg)}>
          {status.label}
        </span>
      </div>
    </Link>
  );
}

function MetricRow({
  label,
  value,
  invert,
}: {
  label: string;
  value: number | null | undefined;
  invert?: boolean;
}) {
  const display = value != null ? (invert ? 1 - value : value) : null;
  const pct = display != null ? Math.min(100, display * 100) : 0;

  const barColor =
    display == null
      ? "bg-slate-300"
      : display >= 0.85
        ? "bg-emerald-500"
        : display >= 0.65
          ? "bg-amber-500"
          : "bg-red-500";

  const textColor =
    display == null
      ? "text-slate-400"
      : display >= 0.85
        ? "text-emerald-600"
        : display >= 0.65
          ? "text-amber-600"
          : "text-red-600";

  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-slate-500 shrink-0">{label}</span>
      <div className="flex items-center gap-2 flex-1">
        <div className="flex-1 h-1.5 rounded-full bg-slate-100">
          <div
            className={cn("h-full rounded-full transition-all", barColor)}
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className={cn("text-xs font-semibold w-10 text-right tabular-nums", textColor)}>
          {display != null ? `${(display * 100).toFixed(1)}%` : "—"}
        </span>
      </div>
    </div>
  );
}
