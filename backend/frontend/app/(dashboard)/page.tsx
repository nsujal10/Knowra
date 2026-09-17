"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { MEETINGS, EVALUATION } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type Meeting, type QualityOverview, type CostSummary } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, Badge, Spinner } from "@/components/ui/card";
import { formatMetric, formatCost, relativeTime, metricColor, cn } from "@/lib/utils";
import { Video, Brain, DollarSign, CheckCircle2, TrendingUp, Clock } from "lucide-react";
import Link from "next/link";

export default function DashboardPage() {
  const { data: meetings, isLoading: meetingsLoading } = useQuery({
    queryKey: queryKeys.meetings.list(),
    queryFn: () => api.get<{ items: Meeting[]; total: number }>(MEETINGS.list()),
  });

  const { data: quality } = useQuery({
    queryKey: queryKeys.evaluation.quality(),
    queryFn: () => api.get<QualityOverview>(EVALUATION.quality()),
  });

  const { data: costs } = useQuery({
    queryKey: queryKeys.evaluation.costs(),
    queryFn: () => api.get<CostSummary>(EVALUATION.costs()),
  });

  const recentMeetings = meetings?.items?.slice(0, 5) ?? [];
  const total = meetings?.total ?? 0;

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<Video size={18} />}
          label="Total Meetings"
          value={total.toString()}
          sub="all time"
          color="primary"
          loading={meetingsLoading}
        />
        <StatCard
          icon={<Brain size={18} />}
          label="Avg Faithfulness"
          value={formatMetric(quality?.avg_faithfulness)}
          sub="RAG quality"
          color={quality?.avg_faithfulness && quality.avg_faithfulness >= 0.85 ? "success" : "warning"}
          loading={!quality}
        />
        <StatCard
          icon={<TrendingUp size={18} />}
          label="Avg WER"
          value={formatMetric(quality?.avg_wer)}
          sub="transcription error"
          color={quality?.avg_wer !== undefined && quality.avg_wer !== null && quality.avg_wer <= 0.1 ? "success" : "warning"}
          loading={!quality}
        />
        <StatCard
          icon={<DollarSign size={18} />}
          label="AI Cost (30d)"
          value={costs ? formatCost(costs.total_cost_usd) : "—"}
          sub={costs ? `${costs.total_prompt_tokens.toLocaleString()} tokens` : "—"}
          color="secondary"
          loading={!costs}
        />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent Meetings */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Recent Meetings</CardTitle>
              <Link href="/meetings" className="text-xs text-[var(--primary)] hover:underline">
                View all →
              </Link>
            </CardHeader>
            <CardContent>
              {meetingsLoading ? (
                <div className="flex justify-center py-8"><Spinner /></div>
              ) : recentMeetings.length === 0 ? (
                <p className="text-sm text-[var(--muted)] text-center py-8">
                  No meetings yet. Process a video to get started.
                </p>
              ) : (
                <div className="space-y-1">
                  {recentMeetings.map((m) => (
                    <MeetingRow key={m.id} meeting={m} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Quality Panel */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>AI Quality</CardTitle>
              <Link href="/evaluation" className="text-xs text-[var(--primary)] hover:underline">
                Details →
              </Link>
            </CardHeader>
            <CardContent>
              {quality ? (
                <div className="space-y-3">
                  <MetricRow label="Faithfulness" value={quality.avg_faithfulness} />
                  <MetricRow label="Answer Relevance" value={quality.avg_answer_relevance} />
                  <MetricRow label="Hallucination Rate" value={1 - quality.hallucination_rate} invert />
                  <div className="pt-2 border-t border-[var(--border)] flex items-center justify-between text-xs">
                    <span className="text-[var(--muted)]">Eval Runs Passed</span>
                    <span className="text-[var(--success)] font-medium flex items-center gap-1">
                      <CheckCircle2 size={12} />
                      {quality.passed_runs}/{quality.total_runs}
                    </span>
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="skeleton h-4 w-full rounded" />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Token Usage</CardTitle>
            </CardHeader>
            <CardContent>
              {costs ? (
                <div className="space-y-2">
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--muted)]">Prompt Tokens</span>
                    <span className="text-[var(--foreground)] font-mono">{costs.total_prompt_tokens.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-[var(--muted)]">Completion Tokens</span>
                    <span className="text-[var(--foreground)] font-mono">{costs.total_completion_tokens.toLocaleString()}</span>
                  </div>
                  <div className="flex justify-between text-xs pt-2 border-t border-[var(--border)]">
                    <span className="text-[var(--muted)]">Total Cost ({costs.period_days}d)</span>
                    <span className="text-[var(--primary)] font-semibold font-mono">{formatCost(costs.total_cost_usd)}</span>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="skeleton h-4 w-full rounded" />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

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
  color: "primary" | "success" | "warning" | "secondary";
  loading?: boolean;
}) {
  const colorMap = {
    primary: "text-[var(--primary)] bg-[var(--primary-muted)]",
    success: "text-[var(--success)] bg-[var(--success-muted)]",
    warning: "text-[var(--warning)] bg-[var(--warning-muted)]",
    secondary: "text-[var(--secondary)] bg-[var(--secondary-muted)]",
  };

  return (
    <Card>
      <CardContent>
        <div className="flex items-start gap-3">
          <div className={cn("p-2 rounded-[var(--radius-sm)]", colorMap[color])}>
            {icon}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider font-medium">{label}</p>
            {loading ? (
              <div className="skeleton h-5 w-16 mt-1 rounded" />
            ) : (
              <p className="text-xl font-bold text-[var(--foreground)] leading-tight">{value}</p>
            )}
            <p className="text-[10px] text-[var(--muted)] mt-0.5">{sub}</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function MeetingRow({ meeting }: { meeting: Meeting }) {
  const statusColors: Record<string, string> = {
    COMPLETED: "success",
    PROCESSING: "warning",
    PENDING: "default",
    FAILED: "danger",
  };

  return (
    <Link
      href={`/meetings/${meeting.id}/recap`}
      className="flex items-center gap-3 p-2.5 rounded-[var(--radius-sm)] hover:bg-[var(--surface-2)] transition-colors group"
    >
      <div className="w-8 h-8 rounded-[var(--radius-sm)] bg-[var(--primary-muted)] flex items-center justify-center shrink-0">
        <Video size={14} className="text-[var(--primary)]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--foreground)] truncate group-hover:text-[var(--primary)] transition-colors">
          {meeting.title}
        </p>
        <p className="text-[10px] text-[var(--muted)] flex items-center gap-1 mt-0.5">
          <Clock size={9} />
          {relativeTime(meeting.created_at)}
        </p>
      </div>
      <Badge variant={statusColors[meeting.status] as "success" | "warning" | "danger" | "default"}>
        {meeting.status}
      </Badge>
    </Link>
  );
}

function MetricRow({ label, value, invert }: { label: string; value: number; invert?: boolean }) {
  const display = invert ? 1 - value : value;
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="text-xs text-[var(--muted)] shrink-0">{label}</span>
      <div className="flex items-center gap-2 flex-1">
        <div className="flex-1 h-1 rounded-full bg-[var(--surface-3)]">
          <div
            className="h-full rounded-full bg-gradient-to-r from-[var(--primary)] to-[var(--secondary)] transition-all"
            style={{ width: `${Math.min(100, display * 100)}%` }}
          />
        </div>
        <span className={cn("text-xs font-medium w-10 text-right", metricColor(display))}>
          {formatMetric(display)}
        </span>
      </div>
    </div>
  );
}
