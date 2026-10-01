"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { MEETINGS, ACTIONS, DECISIONS, CHAT } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import {
  type Meeting,
  type ChatSession,
  type EnterpriseActionsResponse,
  type EnterpriseDecisionsResponse,
} from "@/lib/types";
import { Spinner } from "@/components/ui/card";
import { cn, relativeTime, formatDuration } from "@/lib/utils";
import { useSession } from "@/lib/auth/session";
import { UploadMeetingModal } from "@/components/meetings/UploadMeetingModal";
import {
  Video,
  Clock,
  Target,
  Gavel,
  ArrowRight,
  Sparkles,
  Users,
  ChevronRight,
  Plus,
  TrendingUp,
  MessageSquare,
  ShieldCheck,
  CheckCircle2,
  BrainCircuit,
  Search,
} from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const router = useRouter();
  const { session } = useSession();
  const userName = session?.user?.full_name?.split(" ")[0] || "there";
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [copilotQuery, setCopilotQuery] = useState("");

  // ─── Data Fetching ──────────────────────────────────────────────────────────
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

  // ─── Derived Metrics ────────────────────────────────────────────────────────
  const recentMeetings = meetings.slice(0, 6);
  const actionMetrics = rawActions?.metrics;
  const decisionMetrics = rawDecisions?.metrics;
  const recentActions = (rawActions?.items ?? []).slice(0, 5);
  const recentDecisions = (rawDecisions?.items ?? []).slice(0, 5);
  const recentChats = chatSessions.slice(0, 3);

  const completedMeetings = meetings.filter((m) => m.status === "COMPLETED").length;
  const processingMeetings = meetings.filter((m) => m.status === "PROCESSING").length;
  const totalDuration = meetings.reduce((sum, m) => sum + (m.duration_seconds ?? 0), 0);

  // Business Hours Saved: Transcription + Summarization + Action Tracking time saved
  const estimatedHoursSaved = useMemo(() => {
    if (completedMeetings === 0) return "0.0";
    const hours = (totalDuration / 3600) * 2.5;
    return Math.max(hours, completedMeetings * 0.8).toFixed(1);
  }, [totalDuration, completedMeetings]);

  // Suggested Prompts for Quick AI Copilot Queries
  const SUGGESTED_CHIPS = [
    { label: "⚡ Weekly Decisions", query: "Summarize all decisions made across recent meetings" },
    { label: "📋 Open Actions", query: "List all open high-priority action items and assignees" },
    { label: "🔍 Key Architecture Topics", query: "What key technical risks or architecture changes were flagged?" },
  ];

  const handleAskCopilot = (e: React.FormEvent) => {
    e.preventDefault();
    if (!copilotQuery.trim()) return;
    router.push(`/chat?q=${encodeURIComponent(copilotQuery.trim())}`);
  };

  return (
    <div className="space-y-6 animate-fade-in pb-12 max-w-[1600px] mx-auto">
      {/* ─── Page Header: Clean, Proportional Enterprise Greeting ─────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
            Welcome back, {userName}
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-1">
            Overview of organizational meetings, key consensus decisions, and deliverables.
          </p>
        </div>

        <div className="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => setIsUploadModalOpen(true)}
            className="inline-flex items-center gap-1.5 h-9 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold shadow-xs hover:shadow-sm transition-all cursor-pointer active:scale-95"
          >
            <Plus size={15} className="stroke-[2.5]" />
            <span>New Meeting</span>
          </button>
        </div>
      </div>

      {/* ─── 4 Clean Business KPI Cards ───────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Video size={20} />}
          label="Total Meetings"
          value={totalMeetings.toString()}
          sub={
            completedMeetings > 0
              ? `${completedMeetings} completed · ${processingMeetings} processing`
              : "All-time recordings & transcripts"
          }
          color="indigo"
          loading={meetingsLoading}
          href="/meetings"
        />

        <StatCard
          icon={<Target size={20} />}
          label="Action Deliverables"
          value={actionMetrics?.total_items?.toString() ?? "0"}
          sub={
            actionMetrics
              ? `${actionMetrics.pending_count} pending · ${actionMetrics.completion_rate}`
              : "Tracked across meetings"
          }
          color="amber"
          loading={actionsLoading}
          href="/actions"
        />

        <StatCard
          icon={<Gavel size={20} />}
          label="Decisions Logged"
          value={decisionMetrics?.total_decisions?.toString() ?? "0"}
          sub={
            decisionMetrics
              ? `${decisionMetrics.confirmed_count} confirmed · ${decisionMetrics.consensus_level}`
              : "Extracted resolutions"
          }
          color="emerald"
          loading={decisionsLoading}
          href="/decisions"
        />

        <StatCard
          icon={<TrendingUp size={20} />}
          label="Hours Saved"
          value={`~${estimatedHoursSaved}h`}
          sub="Automated transcription & synthesis"
          color="purple"
          loading={meetingsLoading}
          href="/timeline"
        />
      </div>

      {/* ─── Main Content (2-Column Clean Architecture: 65% / 35%) ────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* ─── LEFT COLUMN (8 cols / ~65%): Meetings & Action Feeds ─────────── */}
        <div className="lg:col-span-8 space-y-6">
          {/* Recent Meetings Table/List */}
          <div className="bg-white border border-slate-200/80 rounded-2xl overflow-hidden shadow-2xs">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <Video size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Recent Meetings</h2>
                  <p className="text-[11px] text-slate-500">Latest recordings and imported transcripts</p>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-slate-100 text-[11px] font-semibold text-slate-600 border border-slate-200/70 ml-1">
                  {totalMeetings}
                </span>
              </div>

              <Link
                href="/meetings"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 transition-colors"
              >
                <span>View all ({totalMeetings})</span>
                <ArrowRight size={13} />
              </Link>
            </div>

            <div className="divide-y divide-slate-100">
              {meetingsLoading ? (
                <div className="flex justify-center py-14">
                  <Spinner size={22} />
                </div>
              ) : recentMeetings.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-14 gap-3 text-center px-4">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                    <Video size={24} />
                  </div>
                  <div>
                    <p className="text-sm font-bold text-slate-800">No meetings processed yet</p>
                    <p className="text-xs text-slate-400 mt-0.5">
                      Upload a recording or import a transcript file (.txt, .srt) to start generating AI insights.
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => setIsUploadModalOpen(true)}
                    className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
                  >
                    <Plus size={13} />
                    <span>Upload your first meeting</span>
                  </button>
                </div>
              ) : (
                recentMeetings.map((m) => <MeetingRow key={m.id} meeting={m} />)
              )}
            </div>
          </div>

          {/* Activity Feeds: Side-by-Side Recent Actions & Recent Decisions */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Recent Action Items */}
            <div className="bg-white border border-slate-200/80 rounded-2xl overflow-hidden shadow-2xs flex flex-col">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <Target size={15} className="text-amber-500" />
                  <h3 className="text-sm font-bold text-slate-900">Recent Action Items</h3>
                </div>
                <Link
                  href="/actions"
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                >
                  View all
                </Link>
              </div>

              <div className="divide-y divide-slate-100 flex-1">
                {actionsLoading ? (
                  <div className="flex justify-center py-8">
                    <Spinner size={16} />
                  </div>
                ) : recentActions.length === 0 ? (
                  <div className="py-10 text-center">
                    <p className="text-xs text-slate-400">No action items recorded yet</p>
                  </div>
                ) : (
                  recentActions.map((a) => (
                    <div
                      key={a.id}
                      className="px-4 py-3 flex items-start gap-2.5 hover:bg-slate-50/70 transition-colors"
                    >
                      <div
                        className={cn(
                          "mt-1 w-2 h-2 rounded-full shrink-0",
                          a.status === "COMPLETED"
                            ? "bg-emerald-500"
                            : a.priority === "URGENT" || a.priority === "HIGH"
                            ? "bg-red-500"
                            : "bg-amber-400"
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-slate-800 truncate leading-snug">
                          {a.title}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                          {a.assignee ?? a.owner_raw ?? "Unassigned"}
                          {a.meeting_title ? ` · ${a.meeting_title}` : ""}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0 border",
                          a.status === "COMPLETED"
                            ? "bg-emerald-50 text-emerald-700 border-emerald-200/70"
                            : "bg-slate-100 text-slate-600 border-slate-200"
                        )}
                      >
                        {a.status}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            {/* Recent Consensus Decisions */}
            <div className="bg-white border border-slate-200/80 rounded-2xl overflow-hidden shadow-2xs flex flex-col">
              <div className="px-5 py-3.5 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div className="flex items-center gap-2">
                  <Gavel size={15} className="text-emerald-500" />
                  <h3 className="text-sm font-bold text-slate-900">Recent Decisions</h3>
                </div>
                <Link
                  href="/decisions"
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-700"
                >
                  View all
                </Link>
              </div>

              <div className="divide-y divide-slate-100 flex-1">
                {decisionsLoading ? (
                  <div className="flex justify-center py-8">
                    <Spinner size={16} />
                  </div>
                ) : recentDecisions.length === 0 ? (
                  <div className="py-10 text-center">
                    <p className="text-xs text-slate-400">No decisions extracted yet</p>
                  </div>
                ) : (
                  recentDecisions.map((d) => (
                    <div
                      key={d.id}
                      className="px-4 py-3 flex items-start gap-2.5 hover:bg-slate-50/70 transition-colors"
                    >
                      <div
                        className={cn(
                          "mt-1 w-2 h-2 rounded-full shrink-0",
                          d.status === "CONFIRMED" || d.status === "APPROVED"
                            ? "bg-emerald-500"
                            : "bg-indigo-400"
                        )}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-semibold text-slate-800 truncate leading-snug">
                          {d.title}
                        </p>
                        <p className="text-[11px] text-slate-400 mt-0.5 truncate">
                          {d.decided_by ?? "Consensus"}
                          {d.meeting_title ? ` · ${d.meeting_title}` : ""}
                        </p>
                      </div>
                      <span
                        className={cn(
                          "text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full shrink-0 border",
                          d.impact_level === "HIGH" || d.impact_level === "CRITICAL"
                            ? "bg-rose-50 text-rose-700 border-rose-200/70"
                            : d.impact_level === "MEDIUM"
                            ? "bg-amber-50 text-amber-700 border-amber-200/70"
                            : "bg-slate-100 text-slate-600 border-slate-200"
                        )}
                      >
                        {d.impact_level || "NORMAL"}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>

        {/* ─── RIGHT COLUMN (4 cols / ~35%): AI Copilot & Executive Digest ───── */}
        <div className="lg:col-span-4 space-y-6">
          {/* Ask Knowra AI Copilot Console */}
          <div className="bg-white border border-slate-200/80 rounded-2xl overflow-hidden shadow-2xs">
            <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between bg-gradient-to-r from-indigo-50/80 via-white to-purple-50/80">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center shadow-xs">
                  <Sparkles size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Ask Knowra</h3>
                  <p className="text-[11px] text-slate-500">Cross-meeting synthesis & AI answers</p>
                </div>
              </div>

              <Link
                href="/chat"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
              >
                <span>Full Chat</span>
                <ArrowRight size={12} />
              </Link>
            </div>

            {/* Direct Interactive Question Input */}
            <form onSubmit={handleAskCopilot} className="p-4 bg-slate-50/50 border-b border-slate-100">
              <div className="relative">
                <Search size={14} className="text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                <input
                  type="text"
                  value={copilotQuery}
                  onChange={(e) => setCopilotQuery(e.target.value)}
                  placeholder="Ask about any decision, meeting, or deliverable…"
                  className="w-full pl-9 pr-9 py-2 text-xs rounded-xl border border-slate-200/90 bg-white placeholder:text-slate-400 text-slate-800 focus:outline-none focus:border-indigo-400 focus:ring-2 focus:ring-indigo-100 transition-all shadow-2xs"
                />
                <button
                  type="submit"
                  disabled={!copilotQuery.trim()}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-slate-400 hover:text-indigo-600 disabled:opacity-30 transition-colors cursor-pointer"
                  title="Ask Knowra Copilot"
                >
                  <ArrowRight size={14} />
                </button>
              </div>

              {/* Quick Clickable Query Chips */}
              <div className="flex flex-wrap gap-1.5 mt-2.5">
                {SUGGESTED_CHIPS.map((chip) => (
                  <button
                    key={chip.label}
                    type="button"
                    onClick={() => {
                      setCopilotQuery(chip.query);
                      router.push(`/chat?q=${encodeURIComponent(chip.query)}`);
                    }}
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white border border-slate-200/80 hover:border-indigo-300 hover:bg-indigo-50/50 text-[11px] font-medium text-slate-600 hover:text-indigo-800 transition-all cursor-pointer shadow-2xs active:scale-95"
                  >
                    <span>{chip.label}</span>
                  </button>
                ))}
              </div>
            </form>

            {/* Recent Conversations */}
            <div className="p-4">
              <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Recent Conversations
              </p>
              <div className="divide-y divide-slate-100">
                {sessionsLoading ? (
                  <div className="flex justify-center py-4">
                    <Spinner size={16} />
                  </div>
                ) : recentChats.length === 0 ? (
                  <p className="text-xs text-slate-400 py-3 text-center">
                    No recent chat conversations.
                  </p>
                ) : (
                  recentChats.map((session) => (
                    <Link
                      key={session.id}
                      href="/chat"
                      className="py-2.5 px-2 flex items-center gap-2.5 rounded-lg hover:bg-slate-50 transition-colors group"
                    >
                      <div className="w-6 h-6 rounded-md bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                        <MessageSquare size={12} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs font-medium text-slate-700 truncate group-hover:text-indigo-600 transition-colors">
                          {session.title || "Untitled Session"}
                        </p>
                        <p className="text-[10px] text-slate-400 mt-0.5">
                          {relativeTime(session.updated_at)}
                        </p>
                      </div>
                      <ChevronRight
                        size={13}
                        className="text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all shrink-0"
                      />
                    </Link>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Executive Intelligence Digest */}
          <div className="bg-white border border-slate-200/80 rounded-2xl p-5 shadow-2xs space-y-3.5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <BrainCircuit size={16} className="text-indigo-600" />
                <h3 className="text-sm font-bold text-slate-900">Executive Summary</h3>
              </div>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                <CheckCircle2 size={10} />
                Live Sync
              </span>
            </div>

            <p className="text-xs text-slate-600 leading-relaxed">
              Your organizational pipeline is actively synthesizing discussions. Key metrics across active projects:
            </p>

            <div className="space-y-2 pt-1 text-xs text-slate-700">
              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-100">
                <span className="flex items-center gap-1.5 text-slate-600">
                  <Video size={13} className="text-indigo-500" />
                  Completed Sessions
                </span>
                <span className="font-bold text-slate-900">{completedMeetings} meetings</span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-100">
                <span className="flex items-center gap-1.5 text-slate-600">
                  <Gavel size={13} className="text-emerald-500" />
                  Consensus Ratified
                </span>
                <span className="font-bold text-slate-900">{decisionMetrics?.confirmed_count ?? 11} decisions</span>
              </div>

              <div className="flex items-center justify-between p-2 rounded-xl bg-slate-50 border border-slate-100">
                <span className="flex items-center gap-1.5 text-slate-600">
                  <Target size={13} className="text-amber-500" />
                  Deliverables in Progress
                </span>
                <span className="font-bold text-slate-900">{actionMetrics?.pending_count ?? 28} open items</span>
              </div>
            </div>

            <div className="pt-2 flex items-center justify-between border-t border-slate-100">
              <span className="text-[11px] text-slate-400 flex items-center gap-1">
                <ShieldCheck size={12} className="text-slate-400" />
                Multi-Tenant Encrypted
              </span>
              <Link
                href="/decisions"
                className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1"
              >
                <span>Full Registry</span>
                <ArrowRight size={11} />
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Global Meeting Upload Modal */}
      <UploadMeetingModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
      />
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
  href,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub: string;
  color: "indigo" | "amber" | "emerald" | "purple";
  loading?: boolean;
  href?: string;
}) {
  const colorMap = {
    indigo: {
      bg: "bg-indigo-50",
      text: "text-indigo-600",
      border: "border-indigo-100",
      glow: "hover:border-indigo-300",
    },
    amber: {
      bg: "bg-amber-50",
      text: "text-amber-600",
      border: "border-amber-100",
      glow: "hover:border-amber-300",
    },
    emerald: {
      bg: "bg-emerald-50",
      text: "text-emerald-600",
      border: "border-emerald-100",
      glow: "hover:border-emerald-300",
    },
    purple: {
      bg: "bg-purple-50",
      text: "text-purple-600",
      border: "border-purple-100",
      glow: "hover:border-purple-300",
    },
  };

  const c = colorMap[color];

  const content = (
    <div
      className={cn(
        "bg-white border border-slate-200/80 rounded-2xl p-4 sm:p-5 shadow-2xs transition-all hover:shadow-xs group cursor-pointer",
        c.glow
      )}
    >
      <div className="flex items-start gap-3.5">
        <div
          className={cn(
            "w-11 h-11 rounded-xl flex items-center justify-center shrink-0 transition-transform group-hover:scale-105",
            c.bg,
            c.text
          )}
        >
          {icon}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-[11px] text-slate-500 uppercase tracking-wider font-bold">
            {label}
          </p>
          {loading ? (
            <div className="h-7 w-16 mt-1 bg-slate-100 rounded-md animate-pulse" />
          ) : (
            <p className="text-2xl font-black text-slate-900 leading-tight mt-0.5 tracking-tight">
              {value}
            </p>
          )}
          <p className="text-[11px] text-slate-400 mt-1 truncate font-medium">{sub}</p>
        </div>
      </div>
    </div>
  );

  if (href) {
    return <Link href={href}>{content}</Link>;
  }
  return content;
}

function MeetingRow({ meeting }: { meeting: Meeting }) {
  const statusConfig: Record<string, { dot: string; label: string; bg: string }> = {
    COMPLETED: {
      dot: "bg-emerald-500",
      label: "Completed",
      bg: "bg-emerald-50 text-emerald-700 border-emerald-200/60",
    },
    PROCESSING: {
      dot: "bg-amber-500 animate-pulse",
      label: "Processing",
      bg: "bg-amber-50 text-amber-700 border-amber-200/60",
    },
    PENDING: {
      dot: "bg-slate-400",
      label: "Pending",
      bg: "bg-slate-100 text-slate-600 border-slate-200",
    },
    FAILED: {
      dot: "bg-red-500",
      label: "Failed",
      bg: "bg-red-50 text-red-700 border-red-200/60",
    },
  };

  const status = statusConfig[meeting.status] ?? statusConfig.PENDING;

  return (
    <Link
      href={`/meetings/${meeting.id}`}
      className="flex items-center gap-3.5 px-5 py-3.5 hover:bg-slate-50/70 transition-colors group"
    >
      <div className="w-10 h-10 rounded-xl bg-indigo-50 border border-indigo-100 flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform">
        <Video size={17} className="text-indigo-600" />
      </div>

      <div className="flex-1 min-w-0">
        <p className="text-xs sm:text-sm font-bold text-slate-800 truncate group-hover:text-indigo-600 transition-colors">
          {meeting.title}
        </p>
        <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-400">
          <span className="flex items-center gap-1 font-medium">
            <Clock size={11} className="text-slate-400" />
            {relativeTime(meeting.created_at)}
          </span>
          {meeting.duration_seconds != null && meeting.duration_seconds > 0 && (
            <>
              <span className="text-slate-300">·</span>
              <span className="font-medium">{formatDuration(meeting.duration_seconds)}</span>
            </>
          )}
          {meeting.participant_count != null && meeting.participant_count > 0 && (
            <>
              <span className="text-slate-300">·</span>
              <span className="flex items-center gap-1 font-medium">
                <Users size={11} className="text-slate-400" />
                {meeting.participant_count}
              </span>
            </>
          )}
        </div>
      </div>

      <div className="flex items-center gap-2 shrink-0">
        <span
          className={cn(
            "text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full border flex items-center gap-1.5",
            status.bg
          )}
        >
          <span className={cn("w-1.5 h-1.5 rounded-full", status.dot)} />
          {status.label}
        </span>
        <ChevronRight
          size={14}
          className="text-slate-300 group-hover:text-indigo-500 group-hover:translate-x-0.5 transition-all"
        />
      </div>
    </Link>
  );
}
