"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import { format, parseISO, startOfWeek, endOfWeek } from "date-fns";
import { cn, formatDuration } from "@/lib/utils";
import { type Meeting } from "@/lib/types";
import { MOCK_MEETINGS, MEETING_SOURCE, MEETING_OWNER } from "@/lib/data/mock";
import { Badge } from "@/components/ui/card";
import {
  Search, Sparkles, Users, Clock, MoreHorizontal, FolderPlus, ChevronDown, Filter,
} from "lucide-react";

// ─── Source Icon ──────────────────────────────────────────────────────────────
const SOURCE_CONFIG = {
  Zoom:  { letter: "Z", bg: "bg-blue-500/15",   text: "text-blue-400",   border: "border-blue-500/25" },
  Teams: { letter: "T", bg: "bg-violet-500/15", text: "text-violet-400", border: "border-violet-500/25" },
  Meet:  { letter: "G", bg: "bg-green-500/15",  text: "text-green-400",  border: "border-green-500/25" },
} as const;

function SourceIcon({ source }: { source: keyof typeof SOURCE_CONFIG }) {
  const c = SOURCE_CONFIG[source];
  return (
    <div className={cn("w-8 h-8 rounded-lg flex items-center justify-center shrink-0 font-bold text-xs border", c.bg, c.text, c.border)}>
      {c.letter}
    </div>
  );
}

const STATUS_CONFIG: Record<string, { label: string; class: string }> = {
  COMPLETED:  { label: "Completed",  class: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" },
  PROCESSING: { label: "Processing", class: "bg-amber-500/10 text-amber-400 border border-amber-500/20" },
  PENDING:    { label: "Pending",    class: "bg-[var(--surface-3)] text-[var(--muted-strong)] border border-[var(--border)]" },
  FAILED:     { label: "Failed",     class: "bg-red-500/10 text-red-400 border border-red-500/20" },
};

// ─── Week grouping ────────────────────────────────────────────────────────────
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
        label: `Week of ${format(ws, "MMM d")} – ${format(we, "MMM d, yyyy")}`.toUpperCase(),
        weekStart: ws,
        meetings: [],
      });
    }
    map.get(key)!.meetings.push(m);
  }
  return Array.from(map.values()).sort((a, b) => b.weekStart.getTime() - a.weekStart.getTime());
}

// ─── Meeting Row ──────────────────────────────────────────────────────────────
function MeetingRow({ meeting }: { meeting: Meeting }) {
  const source = MEETING_SOURCE[meeting.id] ?? "Teams";
  const owner  = MEETING_OWNER[meeting.id] ?? { initials: "?", name: "Unknown" };
  const st     = STATUS_CONFIG[meeting.status] ?? STATUS_CONFIG.PENDING;
  const date   = parseISO(meeting.created_at);

  return (
    <div className="group relative flex items-center gap-4 px-5 py-3.5 hover:bg-[var(--surface-hover)] transition-colors duration-100 border-b border-[var(--border)] last:border-0">
      {/* Hover indicator */}
      <div className="absolute left-0 top-0 bottom-0 w-0.5 rounded-r bg-[var(--primary)] opacity-0 group-hover:opacity-100 transition-opacity" />

      <SourceIcon source={source} />

      {/* Main content */}
      <div className="flex-1 min-w-0 grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-x-4 gap-y-0.5 items-center">
        <Link href={`/meetings/${meeting.id}`} className="min-w-0">
          <p className="text-sm font-medium text-[var(--foreground)] truncate group-hover:text-[var(--primary)] transition-colors leading-tight">
            {meeting.title}
          </p>
          <div className="flex items-center gap-3 mt-0.5">
            {meeting.participant_count && (
              <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                <Users size={10} />{meeting.participant_count}
              </span>
            )}
            {meeting.duration_seconds && (
              <span className="flex items-center gap-1 text-[11px] text-[var(--muted)]">
                <Clock size={10} />{formatDuration(meeting.duration_seconds)}
              </span>
            )}
            <span className="text-[11px] text-[var(--muted)]">{source}</span>
          </div>
        </Link>
        <div className="hidden sm:flex flex-col items-end shrink-0">
          <span className="text-xs font-medium text-[var(--muted-strong)]">{format(date, "MMM d")}</span>
          <span className="text-[11px] text-[var(--muted)]">{format(date, "h:mm a")}</span>
        </div>
      </div>

      {/* Status + owner + actions */}
      <div className="flex items-center gap-2.5 shrink-0">
        <span className={cn("hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold tracking-wide", st.class)}>
          {st.label}
        </span>
        <div
          title={owner.name}
          className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0 ring-2 ring-[var(--surface-1)]"
          style={{ background: `hsl(${owner.initials.charCodeAt(0) * 31 % 360}, 65%, 45%)` }}
        >
          {owner.initials}
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button className="p-1.5 rounded-md text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-3)] transition-colors" title="Add to Folder">
            <FolderPlus size={13} />
          </button>
          <button className="p-1.5 rounded-md text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-3)] transition-colors" title="More">
            <MoreHorizontal size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Filter chip ──────────────────────────────────────────────────────────────
function Chip({ label, active, onClick }: { label: string; active?: boolean; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all duration-150 whitespace-nowrap",
        active
          ? "bg-[var(--primary-muted)] border-[rgba(79,124,255,0.4)] text-[var(--primary)]"
          : "bg-transparent border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)]"
      )}
    >
      {label}
    </button>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
const STATUS_FILTERS = ["All Meetings", "Completed", "Processing", "Pending"] as const;
type StatusFilter = typeof STATUS_FILTERS[number];

export default function MeetingsPage() {
  const [search, setSearch]             = useState("");
  const [aiSearch, setAiSearch]         = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("All Meetings");
  const [sourceFilter, setSourceFilter] = useState("All Sources");

  const filtered = useMemo(() => {
    let list = MOCK_MEETINGS as Meeting[];
    if (search) list = list.filter((m) => m.title.toLowerCase().includes(search.toLowerCase()));
    if (statusFilter !== "All Meetings") list = list.filter((m) => m.status === statusFilter.toUpperCase());
    if (sourceFilter !== "All Sources")  list = list.filter((m) => MEETING_SOURCE[m.id] === sourceFilter);
    return list;
  }, [search, statusFilter, sourceFilter]);

  const groups = useMemo(() => groupByWeek(filtered), [filtered]);

  return (
    <div className="space-y-4 animate-fade-in">

      {/* ── AI Search ── */}
      <div className="relative group">
        <div className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--primary)] transition-opacity">
          <Sparkles size={15} />
        </div>
        <input
          id="ai-search-input"
          type="text"
          placeholder="Ask Knowra anything… e.g. 'What did we decide about Pinecone in last week's call?'"
          value={aiSearch}
          onChange={(e) => setAiSearch(e.target.value)}
          className={cn(
            "w-full h-11 pl-10 pr-16 rounded-[var(--radius-md)]",
            "bg-[var(--surface-1)] border border-[var(--border)]",
            "text-sm text-[var(--foreground)] placeholder:text-[var(--muted)]",
            "focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)]/20",
            "transition-all duration-200"
          )}
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:inline-flex h-5 items-center rounded border border-[var(--border)] bg-[var(--surface-2)] px-1.5 text-[10px] text-[var(--muted)] font-mono">⌘K</kbd>
      </div>

      {/* ── Filters bar ── */}
      <div className="flex items-center gap-2 flex-wrap">
        {/* Title search */}
        <div className="relative">
          <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
          <input
            id="meeting-filter-input"
            type="text"
            placeholder="Filter by meeting title…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className={cn(
              "h-8 w-52 pl-8 pr-3 rounded-[var(--radius-sm)]",
              "bg-[var(--surface-2)] border border-[var(--border)]",
              "text-[11px] text-[var(--foreground)] placeholder:text-[var(--muted)]",
              "focus:outline-none focus:border-[var(--primary)] focus:ring-1 focus:ring-[var(--primary)]/20",
              "transition-all duration-200"
            )}
          />
        </div>

        <div className="w-px h-5 bg-[var(--border)]" />

        {/* Status filters */}
        {STATUS_FILTERS.map((f) => (
          <Chip key={f} label={f} active={statusFilter === f} onClick={() => setStatusFilter(f)} />
        ))}

        <div className="w-px h-5 bg-[var(--border)]" />

        {/* Source filter */}
        <button className={cn(
          "flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all duration-150",
          sourceFilter !== "All Sources"
            ? "bg-[var(--primary-muted)] border-[rgba(79,124,255,0.4)] text-[var(--primary)]"
            : "bg-transparent border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)]"
        )}>
          {sourceFilter} <ChevronDown size={11} />
        </button>

        <button className="flex items-center gap-1 px-2.5 py-1 rounded-full text-[11px] font-medium border border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] transition-all">
          <Filter size={10} />Anytime <ChevronDown size={11} />
        </button>

        <span className="ml-auto text-[11px] text-[var(--muted)]">{filtered.length} meetings</span>
      </div>

      {/* ── Week groups ── */}
      {groups.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <p className="text-sm font-medium text-[var(--muted-strong)]">No meetings found</p>
          <p className="text-xs text-[var(--muted)]">Try adjusting your filters</p>
        </div>
      ) : (
        groups.map((g) => (
          <div key={g.label}>
            {/* Week header */}
            <div className="flex items-center gap-3 mb-2">
              <span className="text-[10px] font-bold uppercase tracking-widest text-[var(--muted)]">
                {g.label}
              </span>
              <div className="flex-1 h-px bg-[var(--border)]" />
              <span className="text-[10px] text-[var(--muted)]">{g.meetings.length} meetings</span>
            </div>
            {/* Cards */}
            <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] overflow-hidden">
              {g.meetings.map((m) => <MeetingRow key={m.id} meeting={m} />)}
            </div>
          </div>
        ))
      )}
    </div>
  );
}