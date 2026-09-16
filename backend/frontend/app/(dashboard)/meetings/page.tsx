"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { format, startOfWeek, endOfWeek, parseISO, isWithinInterval } from "date-fns";
import { cn, formatDuration, relativeTime } from "@/lib/utils";
import { type Meeting } from "@/lib/types";
import {
  MOCK_MEETINGS,
  MEETING_SOURCE,
  MEETING_OWNER,
} from "@/lib/data/mock";
import { Badge } from "@/components/ui/card";
import {
  Search,
  Sparkles,
  Video,
  Users,
  MoreHorizontal,
  FolderPlus,
  ChevronDown,
  Clock,
  Filter,
  MonitorPlay,
} from "lucide-react";

// ─── Source Icon ──────────────────────────────────────────────────────────────
function SourceIcon({ source }: { source: "Zoom" | "Teams" | "Meet" }) {
  const styles: Record<string, { bg: string; label: string; color: string }> = {
    Zoom:  { bg: "bg-blue-500/10 border border-blue-500/20", label: "Z", color: "text-blue-400" },
    Teams: { bg: "bg-violet-500/10 border border-violet-500/20", label: "T", color: "text-violet-400" },
    Meet:  { bg: "bg-green-500/10 border border-green-500/20", label: "G", color: "text-green-400" },
  };
  const s = styles[source];
  return (
    <div className={cn("w-9 h-9 rounded-xl flex items-center justify-center shrink-0 font-bold text-xs", s.bg, s.color)}>
      {s.label}
    </div>
  );
}

// ─── Status badge map ─────────────────────────────────────────────────────────
const STATUS_BADGE: Record<string, "success" | "warning" | "default" | "danger"> = {
  COMPLETED: "success",
  PROCESSING: "warning",
  PENDING: "default",
  FAILED: "danger",
};

// ─── Owner Avatar ─────────────────────────────────────────────────────────────
function OwnerAvatar({ initials, name }: { initials: string; name: string }) {
  return (
    <div
      title={name}
      className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white text-[10px] font-bold shrink-0"
    >
      {initials}
    </div>
  );
}

// ─── Meeting Row ──────────────────────────────────────────────────────────────
function MeetingRow({ meeting }: { meeting: Meeting }) {
  const source = MEETING_SOURCE[meeting.id] ?? "Teams";
  const owner  = MEETING_OWNER[meeting.id] ?? { initials: "?", name: "Unknown" };

  return (
    <div className="group flex items-center gap-4 px-5 py-4 hover:bg-[var(--surface-2)] transition-colors duration-150 border-b border-[var(--border)] last:border-0">
      <SourceIcon source={source} />

      {/* Title + meta */}
      <div className="flex-1 min-w-0">
        <Link
          href={`/meetings/${meeting.id}`}
          className="text-sm font-medium text-[var(--foreground)] hover:text-[var(--primary)] transition-colors truncate block"
        >
          {meeting.title}
        </Link>
        <div className="flex items-center gap-3 mt-0.5 flex-wrap">
          {meeting.participant_count && (
            <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
              <Users size={10} />
              {meeting.participant_count} participants
            </span>
          )}
          {meeting.duration_seconds && (
            <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
              <Clock size={10} />
              {formatDuration(meeting.duration_seconds)}
            </span>
          )}
          <span className="text-[11px] text-[var(--muted)]">{source}</span>
        </div>
      </div>

      {/* Date */}
      <div className="hidden md:flex flex-col items-end shrink-0">
        <span className="text-xs text-[var(--muted-strong)]">
          {format(parseISO(meeting.created_at), "MMM d")}
        </span>
        <span className="text-[10px] text-[var(--muted)]">
          {format(parseISO(meeting.created_at), "h:mm a")}
        </span>
      </div>

      {/* Status */}
      <div className="hidden sm:block shrink-0">
        <Badge variant={STATUS_BADGE[meeting.status]}>{meeting.status}</Badge>
      </div>

      {/* Owner + actions */}
      <div className="flex items-center gap-2 shrink-0">
        <OwnerAvatar initials={owner.initials} name={owner.name} />
        <button
          className="p-1.5 rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-3)] transition-colors opacity-0 group-hover:opacity-100"
          title="Add to Folder"
          aria-label="Add to folder"
        >
          <FolderPlus size={14} />
        </button>
        <button
          className="p-1.5 rounded-lg text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-3)] transition-colors opacity-0 group-hover:opacity-100"
          title="More options"
          aria-label="More options"
        >
          <MoreHorizontal size={14} />
        </button>
      </div>
    </div>
  );
}

// ─── Week Group ───────────────────────────────────────────────────────────────
function WeekGroup({ label, meetings }: { label: string; meetings: Meeting[] }) {
  return (
    <div className="mb-6">
      <div className="flex items-center gap-3 px-5 py-2.5">
        <span className="text-[10px] font-semibold uppercase tracking-widest text-[var(--muted)]">
          {label}
        </span>
        <div className="flex-1 h-px bg-[var(--border)]" />
        <span className="text-[10px] text-[var(--muted)]">{meetings.length} meetings</span>
      </div>
      <div className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] overflow-hidden">
        {meetings.map((m) => (
          <MeetingRow key={m.id} meeting={m} />
        ))}
      </div>
    </div>
  );
}

// ─── Filter Pill ──────────────────────────────────────────────────────────────
function FilterPill({ label, active, onClick }: { label: string; active?: boolean; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150",
        active
          ? "bg-[var(--primary-muted)] border-[rgba(79,124,255,0.35)] text-[var(--primary)]"
          : "bg-[var(--surface-2)] border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)]"
      )}
    >
      {label}
      <ChevronDown size={11} />
    </button>
  );
}

// ─── Grouping helper ──────────────────────────────────────────────────────────
type WeekGroup = { label: string; weekStart: Date; meetings: Meeting[] };

function groupByWeek(meetings: Meeting[]): WeekGroup[] {
  const map = new Map<string, WeekGroup>();
  for (const m of meetings) {
    const d = parseISO(m.created_at);
    const ws = startOfWeek(d, { weekStartsOn: 1 });
    const we = endOfWeek(d, { weekStartsOn: 1 });
    const key = format(ws, "yyyy-MM-dd");
    if (!map.has(key)) {
      map.set(key, {
        label: `WEEK OF ${format(ws, "MMM d")} – ${format(we, "MMM d, yyyy")}`,
        weekStart: ws,
        meetings: [],
      });
    }
    map.get(key)!.meetings.push(m);
  }
  return Array.from(map.values()).sort((a, b) => b.weekStart.getTime() - a.weekStart.getTime());
}

// ─── Main Page ────────────────────────────────────────────────────────────────
const STATUS_FILTERS = ["All Meetings", "Completed", "Processing", "Pending"] as const;
type StatusFilter = typeof STATUS_FILTERS[number];

const SOURCE_FILTERS = ["All Sources", "Teams", "Zoom", "Meet"] as const;

export default function MeetingsPage() {
  const [search, setSearch] = useState("");
  const [aiSearch, setAiSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All Meetings");
  const [sourceFilter, setSourceFilter] = useState<typeof SOURCE_FILTERS[number]>("All Sources");

  const filtered = useMemo(() => {
    let list = MOCK_MEETINGS as Meeting[];
    if (search) {
      const q = search.toLowerCase();
      list = list.filter((m) => m.title.toLowerCase().includes(q));
    }
    if (statusFilter !== "All Meetings") {
      list = list.filter((m) => m.status === statusFilter.toUpperCase());
    }
    if (sourceFilter !== "All Sources") {
      list = list.filter((m) => MEETING_SOURCE[m.id] === sourceFilter);
    }
    return list;
  }, [search, statusFilter, sourceFilter]);

  const groups = useMemo(() => groupByWeek(filtered), [filtered]);

  return (
    <div className="space-y-5 animate-fade-in max-w-5xl mx-auto">

      {/* ── AI Search Bar ── */}
      <div className="relative">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--primary)]">
          <Sparkles size={16} />
        </div>
        <input
          id="ai-search-input"
          type="text"
          placeholder="Ask Knowra anything… e.g. 'What did we decide about Pinecone in last week's call?'"
          value={aiSearch}
          onChange={(e) => setAiSearch(e.target.value)}
          className={cn(
            "w-full h-12 pl-11 pr-4 rounded-[var(--radius-md)]",
            "bg-[var(--surface-1)] border border-[var(--border)]",
            "text-sm text-[var(--foreground)] placeholder:text-[var(--muted)]",
            "focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)]/30",
            "transition-all duration-200",
          )}
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
          <kbd className="hidden sm:inline-flex h-5 items-center gap-1 rounded border border-[var(--border)] bg-[var(--surface-2)] px-1.5 text-[10px] text-[var(--muted)]">⌘K</kbd>
        </div>
      </div>

      {/* ── Filters Bar ── */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 min-w-52">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
          <input
            id="meeting-filter-input"
            type="text"
            placeholder="Filter by meeting title…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={cn(
              "w-full h-9 pl-9 pr-3 rounded-[var(--radius-sm)]",
              "bg-[var(--surface-2)] border border-[var(--border)]",
              "text-xs text-[var(--foreground)] placeholder:text-[var(--muted)]",
              "focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)]/30",
              "transition-all duration-200"
            )}
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {STATUS_FILTERS.map((f) => (
            <button
              key={f}
              onClick={() => setStatusFilter(f)}
              className={cn(
                "px-3 py-1.5 rounded-lg text-xs font-medium border transition-all duration-150",
                statusFilter === f
                  ? "bg-[var(--primary-muted)] border-[rgba(79,124,255,0.35)] text-[var(--primary)]"
                  : "bg-[var(--surface-2)] border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)]"
              )}
            >
              {f}
            </button>
          ))}
          <FilterPill
            label={sourceFilter}
            active={sourceFilter !== "All Sources"}
          />
          <button
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)] transition-all duration-150"
          >
            <Filter size={11} />
            Anytime
            <ChevronDown size={11} />
          </button>
        </div>
        <div className="ml-auto text-xs text-[var(--muted)]">
          {filtered.length} meetings
        </div>
      </div>

      {/* ── Grouped List ── */}
      {groups.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-4">
          <div className="w-16 h-16 rounded-2xl bg-[var(--surface-2)] border border-[var(--border)] flex items-center justify-center">
            <MonitorPlay size={28} className="text-[var(--muted)]" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-[var(--muted-strong)]">No meetings found</p>
            <p className="text-xs text-[var(--muted)] mt-1">Try adjusting your filters</p>
          </div>
        </div>
      ) : (
        groups.map((g) => (
          <WeekGroup key={g.label} label={g.label} meetings={g.meetings} />
        ))
      )}
    </div>
  );
}
