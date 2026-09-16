"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { format, parseISO } from "date-fns";
import { cn, formatDuration, speakerColor } from "@/lib/utils";
import {
  MOCK_MEETINGS, MOCK_TRANSCRIPT, MOCK_ACTION_ITEMS, MOCK_DECISIONS,
  MOCK_CHAPTERS, MOCK_SPEAKERS, MOCK_SUMMARY, MEETING_SOURCE, getSegmentTimestamp,
} from "@/lib/data/mock";
import {
  ArrowLeft, Download, Share2, FolderPlus, Users, Clock, Play, Pause,
  Volume2, Maximize2, CheckSquare, Gavel, Mic, Bookmark, LayoutList,
} from "lucide-react";

// ─── Source config ────────────────────────────────────────────────────────────
const SRC = {
  Teams: { color: "text-violet-400", bg: "bg-violet-500/10" },
  Zoom:  { color: "text-blue-400",   bg: "bg-blue-500/10"   },
  Meet:  { color: "text-green-400",  bg: "bg-green-500/10"  },
};

const STATUS_CONFIG: Record<string, string> = {
  COMPLETED:  "bg-emerald-500/10 text-emerald-400 border border-emerald-500/25",
  PROCESSING: "bg-amber-500/10 text-amber-400 border border-amber-500/25",
  PENDING:    "bg-[var(--surface-3)] text-[var(--muted-strong)] border border-[var(--border)]",
  FAILED:     "bg-red-500/10 text-red-400 border border-red-500/25",
};

// ─── Timestamp Pill ───────────────────────────────────────────────────────────
function TsPill({ seconds }: { seconds: number }) {
  return (
    <button className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[var(--primary-muted)] border border-[rgba(79,124,255,0.25)] text-[10px] font-mono font-semibold text-[var(--primary)] hover:bg-[var(--primary)] hover:text-white transition-all shrink-0 tabular-nums">
      {formatDuration(seconds)}
    </button>
  );
}

// ─── Video Player ─────────────────────────────────────────────────────────────
function VideoPlayer() {
  const [playing, setPlaying] = useState(false);
  return (
    <div className="relative rounded-[var(--radius-md)] overflow-hidden bg-[#06080a] border border-[var(--border)] aspect-video flex items-center justify-center">
      <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-transparent to-black/10" />
      <button
        onClick={() => setPlaying((p) => !p)}
        className="relative z-10 w-12 h-12 rounded-full bg-white/10 border border-white/20 flex items-center justify-center hover:bg-white/20 hover:scale-105 transition-all duration-200"
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? <Pause size={18} className="text-white" /> : <Play size={18} className="text-white ml-0.5" />}
      </button>
      <div className="absolute bottom-0 left-0 right-0 p-3 flex items-center gap-2 z-10">
        <div className="flex-1 h-0.5 bg-white/15 rounded-full cursor-pointer">
          <div className="h-full w-1/3 bg-[var(--primary)] rounded-full" />
        </div>
        <button className="text-white/60 hover:text-white transition-colors"><Volume2 size={12} /></button>
        <button className="text-white/60 hover:text-white transition-colors"><Maximize2 size={12} /></button>
      </div>
      <div className="absolute top-2.5 right-2.5 px-1.5 py-0.5 rounded bg-black/50 backdrop-blur-sm text-[10px] font-mono text-white/70 z-10">1:02:00</div>
    </div>
  );
}

// ─── Right Panel (Player + Chapters) ─────────────────────────────────────────
type RightTab = "chapters" | "highlights" | "speakers";
function RightPanel() {
  const [rt, setRt] = useState<RightTab>("chapters");
  const tabs = [
    { id: "chapters" as RightTab, label: "Chapters",   Icon: LayoutList },
    { id: "highlights" as RightTab, label: "Highlights", Icon: Bookmark },
    { id: "speakers" as RightTab, label: "Speakers",   Icon: Mic },
  ];
  return (
    <div className="space-y-3 sticky top-0">
      <VideoPlayer />
      <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] overflow-hidden">
        {/* Tab bar */}
        <div className="flex border-b border-[var(--border)]">
          {tabs.map(({ id, label, Icon }) => (
            <button key={id} onClick={() => setRt(id)}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2 text-[11px] font-medium transition-all",
                rt === id
                  ? "text-[var(--primary)] bg-[var(--primary-muted)] border-b-2 border-[var(--primary)]"
                  : "text-[var(--muted-strong)] hover:text-[var(--foreground)] hover:bg-[var(--surface-2)]"
              )}>
              <Icon size={12} />{label}
            </button>
          ))}
        </div>
        {/* Tab content */}
        <div className="max-h-80 overflow-y-auto scrollable divide-y divide-[var(--border)]">
          {rt === "chapters" && MOCK_CHAPTERS.map((ch) => (
            <button key={ch.id} className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--surface-2)] transition-colors text-left group">
              <span className="text-sm shrink-0">{ch.emoji}</span>
              <p className="flex-1 text-[11px] font-medium text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors truncate min-w-0">{ch.title}</p>
              <TsPill seconds={ch.start_time} />
            </button>
          ))}
          {rt === "highlights" && (
            <div className="py-8 text-center"><p className="text-[11px] text-[var(--muted)]">AI highlights coming soon</p></div>
          )}
          {rt === "speakers" && MOCK_SPEAKERS.map((sp) => (
            <div key={sp.id} className="flex items-center gap-3 px-4 py-2.5">
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0" style={{ background: speakerColor(sp.label) }}>{sp.initials}</div>
              <div className="flex-1 min-w-0">
                <p className="text-[11px] font-medium text-[var(--foreground)] truncate">{sp.displayName}</p>
                <div className="mt-1 h-1 bg-[var(--surface-3)] rounded-full overflow-hidden">
                  <div className="h-full rounded-full" style={{ width: `${(sp.talkTime / 145) * 100}%`, background: speakerColor(sp.label) }} />
                </div>
              </div>
              <span className="text-[10px] text-[var(--muted)] font-mono shrink-0">{formatDuration(sp.talkTime)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Recap Tab ────────────────────────────────────────────────────────────────
function RecapTab() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
      <div className="space-y-4 min-w-0">
        {/* Summary */}
        <section className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1 h-4 rounded-full bg-gradient-to-b from-[var(--primary)] to-[var(--secondary)]" />
            <h3 className="text-sm font-semibold text-[var(--foreground)]">AI Summary</h3>
            <span className="ml-auto text-[9px] font-medium text-[var(--muted)] px-2 py-0.5 rounded-full bg-[var(--surface-2)] border border-[var(--border)] uppercase tracking-wider">GPT-4o</span>
          </div>
          <div className="space-y-2.5">
            {MOCK_SUMMARY.split("\n\n").filter(Boolean).map((para, i) => {
              const m = para.match(/^\*\*(.+?)\*\*([\s\S]*)$/);
              if (m) return (
                <p key={i} className="text-[13px] text-[var(--muted-strong)] leading-relaxed">
                  <span className="font-semibold text-[var(--foreground)]">{m[1]}</span>{m[2]}
                </p>
              );
              return <p key={i} className="text-[13px] text-[var(--muted-strong)] leading-relaxed">{para}</p>;
            })}
          </div>
        </section>

        {/* Action Items */}
        <section className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckSquare size={14} className="text-emerald-400 shrink-0" />
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Action Items</h3>
            <span className="ml-auto inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-500/10 text-emerald-400 text-[10px] font-bold border border-emerald-500/20">{MOCK_ACTION_ITEMS.length}</span>
          </div>
          <div className="space-y-1.5">
            {MOCK_ACTION_ITEMS.map((a) => (
              <div key={a.id} className="flex items-center gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] transition-colors group">
                <div className="w-1 h-1 rounded-full bg-emerald-400 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] font-medium text-[var(--foreground)] leading-tight">{a.title}</p>
                  {a.assignee && <p className="text-[10px] text-[var(--muted)] mt-0.5">→ {a.assignee}</p>}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  {a.status === "IN_PROGRESS" && (
                    <span className="text-[9px] font-semibold px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 uppercase tracking-wide">In Progress</span>
                  )}
                  <TsPill seconds={getSegmentTimestamp(a.segment_id)} />
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Decisions */}
        <section className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Gavel size={14} className="text-amber-400 shrink-0" />
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Key Decisions</h3>
            <span className="ml-auto inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-500/10 text-amber-400 text-[10px] font-bold border border-amber-500/20">{MOCK_DECISIONS.length}</span>
          </div>
          <div className="space-y-1.5">
            {MOCK_DECISIONS.map((d) => (
              <div key={d.id} className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] transition-colors">
                <div className="w-1 h-1 rounded-full bg-amber-400 mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] font-medium text-[var(--foreground)] leading-tight">{d.title}</p>
                  <p className="text-[10px] text-[var(--muted)] mt-0.5 line-clamp-1">{d.summary}</p>
                  {d.made_by && <p className="text-[10px] text-[var(--muted)] mt-0.5">by {d.made_by}</p>}
                </div>
                <TsPill seconds={getSegmentTimestamp(d.segment_id)} />
              </div>
            ))}
          </div>
        </section>
      </div>

      <RightPanel />
    </div>
  );
}

// ─── Transcript Tab ───────────────────────────────────────────────────────────
function TranscriptTab() {
  const segs = MOCK_TRANSCRIPT.segments;
  const getName = (lbl: string) => MOCK_SPEAKERS.find((s) => s.label === lbl)?.displayName ?? lbl;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
      <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] p-5 min-w-0">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-1 h-4 rounded-full bg-gradient-to-b from-[var(--secondary)] to-[var(--primary)]" />
          <h3 className="text-sm font-semibold text-[var(--foreground)]">Full Transcript</h3>
          <span className="ml-auto text-[10px] text-[var(--muted)]">{segs.length} segments</span>
        </div>
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2 scrollable">
          {segs.map((seg) => {
            const color = speakerColor(seg.speaker_label ?? "");
            const name  = getName(seg.speaker_label ?? "");
            return (
              <div key={seg.id} className="flex gap-3 group cursor-pointer" title="Click to seek">
                {/* Timestamp */}
                <div className="w-12 shrink-0 pt-0.5">
                  <span className="inline-block px-1 py-0.5 rounded text-[10px] font-mono text-[var(--muted)] bg-[var(--surface-2)] border border-[var(--border)] tabular-nums w-full text-center">
                    {formatDuration(seg.start_time)}
                  </span>
                </div>
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5 mb-1">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
                    <span className="text-[11px] font-semibold" style={{ color }}>{name}</span>
                  </div>
                  <p className="text-[13px] text-[var(--muted-strong)] leading-relaxed group-hover:text-[var(--foreground)] transition-colors">
                    {seg.text}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <RightPanel />
    </div>
  );
}

// ─── Decisions Full Tab ───────────────────────────────────────────────────────
function DecisionsTab() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
      <div className="space-y-3 min-w-0">
        {MOCK_DECISIONS.map((d, i) => (
          <div key={d.id} className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] p-5 hover:border-[var(--border-strong)] transition-colors">
            <div className="flex gap-4">
              <div className="w-8 h-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400 text-sm font-bold shrink-0">{i + 1}</div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-[var(--foreground)]">{d.title}</p>
                <p className="text-[12px] text-[var(--muted-strong)] mt-1.5 leading-relaxed">{d.summary}</p>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {d.made_by && <span className="text-[10px] text-[var(--muted)]">by {d.made_by}</span>}
                  {d.confidence && <span className="text-[10px] text-emerald-400">{Math.round(d.confidence * 100)}% confidence</span>}
                  <TsPill seconds={getSegmentTimestamp(d.segment_id)} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <RightPanel />
    </div>
  );
}

// ─── Actions Full Tab ─────────────────────────────────────────────────────────
function ActionsTab() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
      <div className="space-y-2 min-w-0">
        {MOCK_ACTION_ITEMS.map((a) => (
          <div key={a.id} className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] p-4 hover:border-[var(--border-strong)] transition-colors flex items-center gap-3">
            <div className="w-4 h-4 rounded border-2 border-[var(--border-strong)] shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-[13px] font-medium text-[var(--foreground)]">{a.title}</p>
              <div className="flex items-center gap-3 mt-1 flex-wrap">
                {a.assignee && <span className="text-[10px] text-[var(--muted)]">→ {a.assignee}</span>}
                {a.due_date && <span className="text-[10px] text-[var(--muted)]">Due {format(parseISO(a.due_date), "MMM d")}</span>}
                {a.status === "IN_PROGRESS" && <span className="text-[10px] font-medium text-amber-400">In Progress</span>}
                <TsPill seconds={getSegmentTimestamp(a.segment_id)} />
              </div>
            </div>
          </div>
        ))}
      </div>
      <RightPanel />
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────
type TabId = "recap" | "transcript" | "decisions" | "actions";
const TABS: { id: TabId; label: string; badge?: number }[] = [
  { id: "recap",       label: "Recap" },
  { id: "transcript",  label: "Transcript" },
  { id: "decisions",   label: "Decisions", badge: 3 },
  { id: "actions",     label: "Actions",   badge: 5 },
];

interface Props { params: Promise<{ id: string }> }

export default function MeetingDetailPage({ params }: Props) {
  const { id } = use(params);
  const searchParams = useSearchParams();
  const router       = useRouter();
  const activeTab    = (searchParams.get("tab") ?? "recap") as TabId;
  const setTab       = (t: TabId) => router.push(`/meetings/${id}?tab=${t}`, { scroll: false });

  const meeting  = MOCK_MEETINGS.find((m) => m.id === id) ?? MOCK_MEETINGS[0];
  const source   = MEETING_SOURCE[meeting.id] ?? "Teams";
  const srcStyle = SRC[source] ?? SRC.Teams;

  return (
    <div className="animate-fade-in pb-10">
      {/* Back */}
      <Link href="/meetings" className="inline-flex items-center gap-1.5 text-[11px] text-[var(--muted)] hover:text-[var(--foreground)] transition-colors mb-4">
        <ArrowLeft size={11} />Back to Meetings
      </Link>

      {/* ── Header card ── */}
      <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] p-6 mb-5">
        {/* Top meta row */}
        <div className="flex items-center gap-2 mb-3">
          <span className={cn("px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wide", STATUS_CONFIG[meeting.status])}>
            {meeting.status}
          </span>
          <span className={cn("text-[11px] font-medium", srcStyle.color)}>{source}</span>
          <div className="ml-auto flex items-center gap-2">
            <button className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-[var(--radius-sm)] text-[11px] font-medium border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)] transition-all">
              <FolderPlus size={12} />Add to Folder
            </button>
            <button aria-label="Download" className="p-1.5 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)] transition-all">
              <Download size={13} />
            </button>
            <button aria-label="Share" className="p-1.5 rounded-[var(--radius-sm)] border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)] transition-all">
              <Share2 size={13} />
            </button>
          </div>
        </div>

        {/* Title */}
        <h1 className="text-2xl font-bold text-[var(--foreground)] leading-tight mb-3">{meeting.title}</h1>

        {/* Meta */}
        <div className="flex items-center gap-4 flex-wrap">
          <span className="flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
            <Clock size={11} />{format(parseISO(meeting.created_at), "EEEE, MMMM d, yyyy · h:mm a")}
          </span>
          {meeting.duration_seconds && (
            <span className="flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
              <Clock size={11} />{formatDuration(meeting.duration_seconds)}
            </span>
          )}
          {meeting.participant_count && (
            <span className="flex items-center gap-1.5 text-[11px] text-[var(--muted)]">
              <Users size={11} />{meeting.participant_count} participants
            </span>
          )}
        </div>

        {/* Participant avatars */}
        <div className="flex items-center gap-1 mt-3">
          {MOCK_SPEAKERS.map((sp, i) => (
            <div key={sp.id} title={sp.displayName}
              className="w-7 h-7 rounded-full border-2 border-[var(--surface-1)] flex items-center justify-center text-[10px] font-bold text-white"
              style={{ background: speakerColor(sp.label), marginLeft: i > 0 ? "-8px" : 0, zIndex: 10 - i }}
            >{sp.initials}</div>
          ))}
          {(meeting.participant_count ?? 0) > 3 && (
            <span className="ml-2 text-[10px] text-[var(--muted)]">+{(meeting.participant_count ?? 0) - 3} more</span>
          )}
        </div>

        {/* ── Tab Bar ── */}
        <div className="flex items-center gap-1 mt-5 pt-4 border-t border-[var(--border)]">
          {TABS.map((tab) => (
            <button key={tab.id} onClick={() => setTab(tab.id)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2 rounded-[var(--radius-sm)] text-[13px] font-medium transition-all duration-150",
                activeTab === tab.id
                  ? "bg-[var(--primary-muted)] text-[var(--primary)] border border-[rgba(79,124,255,0.25)]"
                  : "text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]"
              )}>
              {tab.label}
              {tab.badge && (
                <span className={cn(
                  "text-[9px] font-bold px-1.5 py-0.5 rounded-full border",
                  tab.id === "actions"
                    ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                    : "bg-amber-500/10 text-amber-400 border-amber-500/20"
                )}>{tab.badge}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      {/* ── Tab Content ── */}
      {activeTab === "recap"      && <RecapTab />}
      {activeTab === "transcript" && <TranscriptTab />}
      {activeTab === "decisions"  && <DecisionsTab />}
      {activeTab === "actions"    && <ActionsTab />}
    </div>
  );
}