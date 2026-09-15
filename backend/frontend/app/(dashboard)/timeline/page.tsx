"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { CROSS_MEETING } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type TimelineEvent } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, Badge, Spinner, EmptyState, Input } from "@/components/ui/card";
import { cn, formatDate, speakerColor, truncate } from "@/lib/utils";
import { Clock, Search, Filter } from "lucide-react";
import Link from "next/link";

const EVENT_TYPE_COLORS: Record<string, string> = {
  decision: "warning",
  action: "success",
  topic: "secondary",
  meeting: "primary",
  default: "default",
};

export default function TimelinePage() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");

  const { data: events = [], isLoading } = useQuery({
    queryKey: queryKeys.timeline.decisions(),
    queryFn: () => api.get<TimelineEvent[]>(CROSS_MEETING.decisions()),
  });

  const EVENT_TYPES = ["ALL", ...Array.from(new Set(events.map((e) => e.event_type.toUpperCase())))];

  const filtered = events.filter((e) => {
    const matchSearch =
      !search ||
      e.entity_name.toLowerCase().includes(search.toLowerCase()) ||
      e.summary.toLowerCase().includes(search.toLowerCase()) ||
      e.meeting_title.toLowerCase().includes(search.toLowerCase());
    const matchType =
      typeFilter === "ALL" || e.event_type.toUpperCase() === typeFilter;
    return matchSearch && matchType;
  });

  // Group by date
  const grouped = filtered.reduce<Record<string, TimelineEvent[]>>((acc, ev) => {
    const day = ev.occurred_at.slice(0, 10);
    if (!acc[day]) acc[day] = [];
    acc[day].push(ev);
    return acc;
  }, {});
  const sortedDays = Object.keys(grouped).sort((a, b) => b.localeCompare(a));

  return (
    <div className="space-y-5 animate-fade-in max-w-4xl">
      {/* Filters */}
      <Card>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <div className="flex-1">
              <Input
                placeholder="Search entities, summaries, meetings…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                leftIcon={<Search size={13} />}
                id="timeline-search"
              />
            </div>
            <div className="flex gap-1.5 flex-wrap items-center">
              <Filter size={13} className="text-[var(--muted)]" />
              {EVENT_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setTypeFilter(t)}
                  className={cn(
                    "px-3 py-1.5 rounded-[var(--radius-sm)] text-xs font-medium border transition-all",
                    typeFilter === t
                      ? "bg-[var(--primary-muted)] border-[rgba(79,124,255,0.3)] text-[var(--primary)]"
                      : "bg-transparent border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)]"
                  )}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Timeline */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <Spinner size={24} />
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Clock />}
          title="No timeline events found"
          description="Process meetings to extract cross-meeting intelligence."
        />
      ) : (
        <div className="space-y-8">
          {sortedDays.map((day) => (
            <div key={day} className="relative">
              {/* Day Label */}
              <div className="flex items-center gap-3 mb-4">
                <div className="h-px flex-1 bg-[var(--border)]" />
                <span className="text-[10px] text-[var(--muted)] uppercase tracking-wider font-medium px-2">
                  {new Date(day).toLocaleDateString("en-US", {
                    weekday: "long",
                    month: "long",
                    day: "numeric",
                    year: "numeric",
                  })}
                </span>
                <div className="h-px flex-1 bg-[var(--border)]" />
              </div>

              {/* Events */}
              <div className="space-y-3 pl-6 relative">
                {/* Vertical line */}
                <div className="absolute left-2 top-0 bottom-0 w-px bg-[var(--border)]" />

                {grouped[day].map((ev) => (
                  <TimelineCard key={ev.id} event={ev} />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function TimelineCard({ event }: { event: TimelineEvent }) {
  const badgeVariant = (EVENT_TYPE_COLORS[event.event_type.toLowerCase()] ??
    "default") as "warning" | "success" | "secondary" | "primary" | "default";

  const speakerCol = event.speaker ? speakerColor(event.speaker) : undefined;

  return (
    <div className="relative">
      {/* Dot on timeline */}
      <div
        className="absolute -left-4 top-4 w-2 h-2 rounded-full border border-[var(--surface-1)]"
        style={{
          background:
            badgeVariant === "warning"
              ? "var(--warning)"
              : badgeVariant === "success"
              ? "var(--success)"
              : "var(--primary)",
        }}
      />

      <Card hoverable className="ml-2">
        <CardContent>
          <div className="flex items-start gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-1">
                <Badge variant={badgeVariant}>{event.event_type}</Badge>
                <span className="text-[10px] text-[var(--muted)] font-mono">
                  {formatDate(event.occurred_at)}
                </span>
              </div>
              <p className="text-sm font-semibold text-[var(--foreground)]">
                {event.entity_name}
              </p>
              <p className="text-xs text-[var(--muted-strong)] mt-1 leading-relaxed">
                {event.summary}
              </p>
              {event.evidence_text && (
                <blockquote className="mt-2 text-xs text-[var(--muted)] italic border-l-2 border-[var(--primary)] pl-2">
                  &ldquo;{truncate(event.evidence_text, 120)}&rdquo;
                </blockquote>
              )}
              <div className="flex items-center gap-3 mt-2">
                <Link
                  href={`/meetings/${event.meeting_id}`}
                  className="text-[10px] text-[var(--primary)] hover:underline flex items-center gap-1"
                >
                  📋 {event.meeting_title}
                </Link>
                {event.speaker && (
                  <span
                    className="text-[10px] font-medium"
                    style={{ color: speakerCol }}
                  >
                    👤 {event.speaker}
                  </span>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
