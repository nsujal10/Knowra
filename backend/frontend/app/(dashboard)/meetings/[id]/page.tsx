"use client";

import { use } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { MEETINGS, TRANSCRIPTS, ACTIONS, DECISIONS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type Meeting, type Transcript, type ActionItem, type Decision } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, Badge, Spinner } from "@/components/ui/card";
import { formatDuration, formatDate, speakerColor, cn } from "@/lib/utils";
import { Video, Clock, Users, Mic2, CheckSquare, AlertCircle } from "lucide-react";

interface Props {
  params: Promise<{ id: string }>;
}

export default function MeetingDetailPage({ params }: Props) {
  const { id } = use(params);

  const { data: meeting, isLoading: mLoading } = useQuery({
    queryKey: queryKeys.meetings.detail(id),
    queryFn: () => api.get<Meeting>(MEETINGS.get(id)),
  });

  const { data: transcript, isLoading: tLoading } = useQuery({
    queryKey: queryKeys.transcripts.byMeeting(id),
    queryFn: () => api.get<Transcript>(TRANSCRIPTS.get(id)),
    enabled: meeting?.status === "COMPLETED",
  });

  const { data: actionsData } = useQuery({
    queryKey: queryKeys.actions.byMeeting(id),
    queryFn: () => api.get<{ items: ActionItem[] }>(ACTIONS.list(id)),
    enabled: meeting?.status === "COMPLETED",
  });

  const { data: decisionsData } = useQuery({
    queryKey: queryKeys.decisions.byMeeting(id),
    queryFn: () => api.get<{ items: Decision[] }>(DECISIONS.list(id)),
    enabled: meeting?.status === "COMPLETED",
  });

  if (mLoading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Spinner size={24} />
      </div>
    );
  }

  if (!meeting) {
    return (
      <div className="flex justify-center items-center h-64">
        <p className="text-[var(--muted)]">Meeting not found</p>
      </div>
    );
  }

  const segments = transcript?.segments ?? [];
  const actions = actionsData?.items ?? [];
  const decisions = decisionsData?.items ?? [];

  const uniqueSpeakers = [...new Set(segments.map((s) => s.speaker_label).filter(Boolean))];

  return (
    <div className="space-y-5 animate-fade-in max-w-7xl">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-[var(--radius-md)] bg-[var(--primary-muted)] flex items-center justify-center shrink-0">
          <Video size={20} className="text-[var(--primary)]" />
        </div>
        <div className="flex-1 min-w-0">
          <h2 className="text-xl font-semibold text-[var(--foreground)] truncate">{meeting.title}</h2>
          <div className="flex items-center gap-4 mt-1 flex-wrap">
            <span className="text-xs text-[var(--muted)] flex items-center gap-1">
              <Clock size={11} /> {formatDate(meeting.created_at)}
            </span>
            {meeting.duration_seconds && (
              <span className="text-xs text-[var(--muted)] flex items-center gap-1">
                <Clock size={11} /> {formatDuration(meeting.duration_seconds)}
              </span>
            )}
            {uniqueSpeakers.length > 0 && (
              <span className="text-xs text-[var(--muted)] flex items-center gap-1">
                <Users size={11} /> {uniqueSpeakers.length} speakers
              </span>
            )}
          </div>
        </div>
        <Badge
          variant={
            meeting.status === "COMPLETED"
              ? "success"
              : meeting.status === "FAILED"
              ? "danger"
              : "warning"
          }
        >
          {meeting.status}
        </Badge>
      </div>

      {/* Speaker Legend */}
      {uniqueSpeakers.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm flex items-center gap-2">
              <Mic2 size={14} className="text-[var(--primary)]" />
              Speakers
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-3">
              {uniqueSpeakers.map((label) => (
                <div key={label} className="flex items-center gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ background: speakerColor(label!) }}
                  />
                  <span className="text-xs text-[var(--muted-strong)]">{label}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Transcript */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Transcript</CardTitle>
              {tLoading && <Spinner size={14} />}
            </CardHeader>
            <CardContent>
              {tLoading ? (
                <div className="space-y-3">
                  {[...Array(6)].map((_, i) => (
                    <div key={i} className="space-y-1">
                      <div className="skeleton h-3 w-20 rounded" />
                      <div className="skeleton h-4 w-full rounded" />
                    </div>
                  ))}
                </div>
              ) : segments.length === 0 ? (
                <p className="text-sm text-[var(--muted)] text-center py-8">
                  Transcript not available for this meeting.
                </p>
              ) : (
                <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
                  {segments.map((seg, i) => (
                    <TranscriptSegment key={seg.id ?? i} segment={seg} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Intelligence Sidebar */}
        <div className="space-y-4">
          {/* Actions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <CheckSquare size={14} className="text-[var(--success)]" />
                Action Items
              </CardTitle>
              <Badge variant="default">{actions.length}</Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {actions.length === 0 ? (
                  <p className="text-xs text-[var(--muted)]">No action items extracted.</p>
                ) : (
                  actions.map((a) => (
                    <div key={a.id} className="p-2 rounded-[var(--radius-sm)] bg-[var(--surface-2)] space-y-1">
                      <p className="text-xs font-medium text-[var(--foreground)]">{a.title}</p>
                      {a.assignee && (
                        <p className="text-[10px] text-[var(--muted)]">→ {a.assignee}</p>
                      )}
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>

          {/* Decisions */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <AlertCircle size={14} className="text-[var(--warning)]" />
                Key Decisions
              </CardTitle>
              <Badge variant="default">{decisions.length}</Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {decisions.length === 0 ? (
                  <p className="text-xs text-[var(--muted)]">No decisions extracted.</p>
                ) : (
                  decisions.map((d) => (
                    <div key={d.id} className="p-2 rounded-[var(--radius-sm)] bg-[var(--surface-2)] space-y-1">
                      <p className="text-xs font-medium text-[var(--foreground)]">{d.title}</p>
                      <p className="text-[10px] text-[var(--muted)] line-clamp-2">{d.summary}</p>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

function TranscriptSegment({
  segment,
}: {
  segment: {
    speaker_label?: string | null;
    speaker_name?: string | null;
    text: string;
    start_time: number;
    end_time: number;
    confidence?: number | null;
  };
}) {
  const speaker = segment.speaker_name ?? segment.speaker_label ?? "Unknown";
  const color = speakerColor(segment.speaker_label ?? speaker);

  return (
    <div className="flex gap-3 group">
      <div className="flex flex-col items-center gap-1 shrink-0 pt-0.5">
        <div
          className="w-2 h-2 rounded-full mt-1"
          style={{ background: color }}
        />
        <span className="text-[9px] text-[var(--muted)] font-mono whitespace-nowrap">
          {formatDuration(segment.start_time)}
        </span>
      </div>
      <div className="flex-1 min-w-0">
        <span
          className="text-[10px] font-semibold uppercase tracking-wider"
          style={{ color }}
        >
          {speaker}
        </span>
        <p className="text-sm text-[var(--muted-strong)] leading-relaxed mt-0.5 group-hover:text-[var(--foreground)] transition-colors">
          {segment.text}
        </p>
        {segment.confidence !== null && segment.confidence !== undefined && (
          <span
            className={cn(
              "text-[9px] font-mono",
              segment.confidence > 0.85
                ? "text-[var(--muted)]"
                : "text-[var(--warning)]"
            )}
          >
            {(segment.confidence * 100).toFixed(0)}% confidence
          </span>
        )}
      </div>
    </div>
  );
}
