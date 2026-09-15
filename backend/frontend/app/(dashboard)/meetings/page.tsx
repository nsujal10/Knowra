"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { MEETINGS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type Meeting } from "@/lib/types";
import { Card, CardContent, CardHeader, CardTitle, Badge, Input, Spinner, EmptyState } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { relativeTime, formatDuration, cn } from "@/lib/utils";
import { Video, Search, Clock, Users, ChevronRight } from "lucide-react";
import Link from "next/link";

const STATUS_OPTIONS = ["ALL", "COMPLETED", "PROCESSING", "PENDING", "FAILED"] as const;
type StatusFilter = (typeof STATUS_OPTIONS)[number];

const STATUS_BADGE: Record<string, "success" | "warning" | "default" | "danger"> = {
  COMPLETED: "success",
  PROCESSING: "warning",
  PENDING: "default",
  FAILED: "danger",
};

export default function MeetingsPage() {
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("ALL");
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 10;

  const { data, isLoading, isFetching } = useQuery({
    queryKey: queryKeys.meetings.list({ search, status: statusFilter, page }),
    queryFn: () =>
      api.get<{ items: Meeting[]; total: number }>(
        `${MEETINGS.list()}?search=${encodeURIComponent(search)}&page=${page}&page_size=${PAGE_SIZE}${statusFilter !== "ALL" ? `&status=${statusFilter}` : ""}`
      ),
    placeholderData: (prev) => prev,
  });

  const meetings = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / PAGE_SIZE);

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Filters */}
      <Card>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center">
            <div className="flex-1">
              <Input
                placeholder="Search meetings by title…"
                value={search}
                onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                leftIcon={<Search size={13} />}
                id="meeting-search"
              />
            </div>
            <div className="flex gap-1.5 flex-wrap">
              {STATUS_OPTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => { setStatusFilter(s); setPage(1); }}
                  className={cn(
                    "px-3 py-1.5 rounded-[var(--radius-sm)] text-xs font-medium border transition-all",
                    statusFilter === s
                      ? "bg-[var(--primary-muted)] border-[rgba(79,124,255,0.3)] text-[var(--primary)]"
                      : "bg-transparent border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)]"
                  )}
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      <Card>
        <CardHeader>
          <CardTitle>
            Meetings{" "}
            {!isLoading && (
              <span className="text-[var(--muted)] text-sm font-normal">
                ({total.toLocaleString()})
              </span>
            )}
          </CardTitle>
          {isFetching && !isLoading && <Spinner size={14} />}
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {[...Array(5)].map((_, i) => (
                <div key={i} className="skeleton h-14 w-full rounded-[var(--radius-sm)]" />
              ))}
            </div>
          ) : meetings.length === 0 ? (
            <EmptyState
              icon={<Video />}
              title="No meetings found"
              description="Try adjusting your search or status filter."
            />
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {meetings.map((meeting) => (
                <MeetingRow key={meeting.id} meeting={meeting} />
              ))}
            </div>
          )}
        </CardContent>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between px-5 py-3 border-t border-[var(--border)]">
            <p className="text-xs text-[var(--muted)]">
              Page {page} of {totalPages}
            </p>
            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </Button>
              <Button
                variant="secondary"
                size="sm"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}

function MeetingRow({ meeting }: { meeting: Meeting }) {
  return (
    <Link
      href={`/meetings/${meeting.id}`}
      className="flex items-center gap-4 py-3.5 px-1 hover:bg-[var(--surface-2)] rounded-[var(--radius-sm)] transition-colors group"
    >
      <div className="w-9 h-9 rounded-[var(--radius-sm)] bg-[var(--primary-muted)] flex items-center justify-center shrink-0">
        <Video size={15} className="text-[var(--primary)]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-[var(--foreground)] truncate group-hover:text-[var(--primary)] transition-colors">
          {meeting.title}
        </p>
        <div className="flex items-center gap-3 mt-0.5">
          <span className="text-[10px] text-[var(--muted)] flex items-center gap-1">
            <Clock size={9} /> {relativeTime(meeting.created_at)}
          </span>
          {meeting.duration_seconds && (
            <span className="text-[10px] text-[var(--muted)]">
              {formatDuration(meeting.duration_seconds)}
            </span>
          )}
          {meeting.participant_count && (
            <span className="text-[10px] text-[var(--muted)] flex items-center gap-1">
              <Users size={9} /> {meeting.participant_count}
            </span>
          )}
        </div>
      </div>
      <Badge variant={STATUS_BADGE[meeting.status]}>{meeting.status}</Badge>
      <ChevronRight size={14} className="text-[var(--muted)] group-hover:text-[var(--primary)] transition-colors shrink-0" />
    </Link>
  );
}
