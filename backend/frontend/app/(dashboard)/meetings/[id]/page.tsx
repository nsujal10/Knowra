"use client";

import { use, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import { format, parseISO } from "date-fns";
import { cn, formatDuration, speakerColor } from "@/lib/utils";
import {
  MOCK_MEETINGS,
  MOCK_TRANSCRIPT,
  MOCK_ACTION_ITEMS,
  MOCK_DECISIONS,
  MOCK_CHAPTERS,
  MOCK_SPEAKERS,
  MOCK_SUMMARY,
  MEETING_SOURCE,
  getSegmentTimestamp,
} from "@/lib/data/mock";
import { Badge } from "@/components/ui/card";
import {
  ArrowLeft,
  Download,
  Share2,
  FolderPlus,
  Users,
  Clock,
  Play,
  Pause,
  Volume2,
  Maximize2,
  CheckSquare,
  Gavel,
  Mic,
  Bookmark,
  LayoutList,
} from "lucide-react";

const STATUS_BADGE: Record<string, "success" | "warning" | "default" | "danger"> = {
  COMPLETED: "success",
  PROCESSING: "warning",
  PENDING: "default",
  FAILED: "danger",
};

const SOURCE_STYLE: Record<string, { label: string; color: string }> = {
  Teams: { label: "Teams", color: "text-violet-400" },
  Zoom:  { label: "Zoom",  color: "text-blue-400" },
  Meet:  { label: "Meet",  color: "text-green-400" },
};

function TimestampPill({ seconds }: { seconds: number }) {
  return (
    <button className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[var(--primary-muted)] border border-[rgba(79,124,255,0.2)] text-[10px] font-mono font-semibold text-[var(--primary)] hover:bg-[var(--primary)] hover:text-white transition-all duration-150 cursor-pointer shrink-0">
      <Clock size={9} />
      {formatDuration(seconds)}
    </button>
  );
}

function VideoPlayer() {
  const [playing, setPlaying] = useState(false);
  return (
    <div className="relative rounded-[var(--radius-md)] overflow-hidden bg-[#060709] border border-[var(--border)] aspect-video flex items-center justify-center">
      <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/20" />
      <button
        onClick={() => setPlaying((p) => !p)}
        className="relative z-10 w-14 h-14 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 flex items-center justify-center hover:bg-white/20 transition-all duration-200 hover:scale-105"
        aria-label={playing ? "Pause" : "Play"}
      >
        {playing ? <Pause size={22} className="text-white" /> : <Play size={22} className="text-white ml-0.5" />}
      </button>
      <div className="absolute bottom-0 left-0 right-0 p-3 flex items-center gap-2 z-10">
        <div className="flex-1 h-1 bg-white/20 rounded-full">
          <div className="h-full w-1/3 bg-[var(--primary)] rounded-full" />
        </div>
        <button className="text-white/70 hover:text-white transition-colors"><Volume2 size={13} /></button>
        <button className="text-white/70 hover:text-white transition-colors"><Maximize2 size={13} /></button>
      </div>
      <div className="absolute top-3 right-3 px-2 py-0.5 rounded-md bg-black/60 text-[10px] font-mono text-white/80 z-10">
        1:02:00
      </div>
    </div>
  );
}

type RightTab = "chapters" | "highlights" | "speakers";

function RightPanel() {
  const [activeTab, setActiveTab] = useState<RightTab>("chapters");
  const tabs = [
    { id: "chapters" as RightTab, label: "Chapters", icon: <LayoutList size={13} /> },
    { id: "highlights" as RightTab, label: "Highlights", icon: <Bookmark size={13} /> },
    { id: "speakers" as RightTab, label: "Speakers", icon: <Mic size={13} /> },
  ];
  return (
    <div className="flex flex-col gap-4">
      <VideoPlayer />
      <div className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] overflow-hidden">
        <div className="flex border-b border-[var(--border)]">
          {tabs.map((t) => (
            <button key={t.id} onClick={() => setActiveTab(t.id)}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-all duration-150",
                activeTab === t.id ? "text-[var(--primary)] border-b-2 border-[var(--primary)] bg-[var(--primary-muted)]"
                  : "text-[var(--muted-strong)] hover:text-[var(--foreground)] hover:bg-[var(--surface-2)]"
              )}>{t.icon}{t.label}</button>
          ))}
        </div>
        <div className="divide-y divide-[var(--border)]">
          {activeTab === "chapters" && MOCK_CHAPTERS.map((ch) => (
            <button key={ch.id} className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[var(--surface-2)] transition-colors duration-150 text-left group">
              <span className="text-base leading-none shrink-0">{ch.emoji}</span>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors truncate">{ch.title}</p>
              </div>
              <TimestampPill seconds={ch.start_time} />
            </button>
          ))}
          {activeTab === "highlights" && (
            <div className="px-4 py-8 text-center"><p className="text-xs text-[var(--muted)]">AI highlights coming soon</p></div>
          )}
          {activeTab === "speakers" && MOCK_SPEAKERS.map((sp) => (
            <div key={sp.id} className="flex items-center gap-3 px-4 py-3">
              <div className="w-7 h-7 rounded-full flex items-center justify-center text-white text-[10px] font-bold shrink-0" style={{ background: speakerColor(sp.label) }}>{sp.initials}</div>
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-[var(--foreground)] truncate">{sp.displayName}</p>
                <div className="mt-1 h-1 bg-[var(--surface-3)] rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all" style={{ width: `${(sp.talkTime / 145) * 100}%`, background: speakerColor(sp.label) }} />
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

function RecapTab() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-5">
        <div className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-5">
          <div className="flex items-center gap-2 mb-4">
            <div className="w-1 h-5 rounded-full bg-gradient-to-b from-[var(--primary)] to-[var(--secondary)]" />
            <h3 className="text-sm font-semibold text-[var(--foreground)]">AI Summary</h3>
            <span className="ml-auto text-[10px] text-[var(--muted)] px-2 py-0.5 rounded-full bg-[var(--surface-2)] border border-[var(--border)]">GPT-4o</span>
          </div>
          <div className="space-y-3">
            {MOCK_SUMMARY.split("\n\n").filter(Boolean).map((para, i) => {
              const boldMatch = para.match(/^\*\*(.+?)\*\*([\s\S]*)$/);
              if (boldMatch) {
                return (
                  <p key={i} className="text-sm text-[var(--muted-strong)] leading-relaxed">
                    <span className="font-semibold text-[var(--foreground)]">{boldMatch[1]}</span>{boldMatch[2]}
                  </p>
                );
              }
              return <p key={i} className="text-sm text-[var(--muted-strong)] leading-relaxed">{para}</p>;
            })}
          </div>
        </div>

        <div className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-5">
          <div className="flex items-center gap-2 mb-4">
            <CheckSquare size={14} className="text-[var(--success)]" />
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Action Items</h3>
            <span className="ml-auto w-5 h-5 rounded-full bg-[var(--success-muted)] text-[var(--success)] text-[10px] font-bold flex items-center justify-center">{MOCK_ACTION_ITEMS.length}</span>
          </div>
          <div className="space-y-2">
            {MOCK_ACTION_ITEMS.map((a) => (
              <div key={a.id} className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] transition-colors">
                <div className="w-1.5 h-1.5 rounded-full bg-[var(--success)] mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-[var(--foreground)] leading-snug">{a.title}</p>
                  {a.assignee && <p className="text-[10px] text-[var(--muted)] mt-0.5">to {a.assignee}</p>}
                </div>
                <div className="flex items-center gap-1.5 shrink-0">
                  <Badge variant={a.status === "IN_PROGRESS" ? "warning" : "default"} className="text-[9px]">{a.status.replace("_", " ")}</Badge>
                  <TimestampPill seconds={getSegmentTimestamp(a.segment_id)} />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-5">
          <div className="flex items-center gap-2 mb-4">
            <Gavel size={14} className="text-[var(--warning)]" />
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Key Decisions</h3>
            <span className="ml-auto w-5 h-5 rounded-full bg-[var(--warning-muted)] text-[var(--warning)] text-[10px] font-bold flex items-center justify-center">{MOCK_DECISIONS.length}</span>
          </div>
          <div className="space-y-2">
            {MOCK_DECISIONS.map((d) => (
              <div key={d.id} className="flex items-start gap-3 p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] hover:bg-[var(--surface-3)] transition-colors">
                <div className="w-1.5 h-1.5 rounded-full bg-[var(--warning)] mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-[var(--foreground)] leading-snug">{d.title}</p>
                  <p className="text-[10px] text-[var(--muted)] mt-0.5 line-clamp-2">{d.summary}</p>
                  {d.made_by && <p className="text-[10px] text-[var(--muted)] mt-0.5">by {d.made_by}</p>}
                </div>
                <TimestampPill seconds={getSegmentTimestamp(d.segment_id)} />
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="lg:col-span-2"><RightPanel /></div>
    </div>
  );
}

function TranscriptTab() {
  const segments = MOCK_TRANSCRIPT.segments;
  const getSpeakerName = (label: string) => MOCK_SPEAKERS.find((s) => s.label === label)?.displayName ?? label;
  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3">
        <div className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-5">
          <div className="flex items-center gap-2 mb-5">
            <div className="w-1 h-5 rounded-full bg-gradient-to-b from-[var(--secondary)] to-[var(--primary)]" />
            <h3 className="text-sm font-semibold text-[var(--foreground)]">Full Transcript</h3>
            <span className="ml-auto text-[10px] text-[var(--muted)]">{segments.length} segments</span>
          </div>
          <div className="space-y-5 max-h-[680px] overflow-y-auto pr-1 scrollable">
            {segments.map((seg) => {
              const color = speakerColor(seg.speaker_label ?? "");
              const name = getSpeakerName(seg.speaker_label ?? "");
              return (
                <div key={seg.id} className="flex gap-3 group cursor-pointer" title="Click to seek">
                  <div className="flex flex-col items-start gap-1.5 shrink-0 pt-0.5 w-16">
                    <span className="inline-flex items-center px-1.5 py-0.5 rounded-md bg-[var(--surface-3)] border border-[var(--border)] text-[10px] font-mono text-[var(--muted-strong)] whitespace-nowrap">
                      {formatDuration(seg.start_time)}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1.5">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold text-white" style={{ background: color + "cc" }}>
                        <span className="w-1.5 h-1.5 rounded-full bg-white/80 shrink-0" />{name}
                      </span>
                    </div>
                    <p className="text-sm text-[var(--muted-strong)] leading-relaxed group-hover:text-[var(--foreground)] transition-colors duration-150">{seg.text}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
      <div className="lg:col-span-2"><RightPanel /></div>
    </div>
  );
}

function DecisionsTab() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-3">
        {MOCK_DECISIONS.map((d, idx) => (
          <div key={d.id} className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-5 hover:border-[var(--border-strong)] transition-colors">
            <div className="flex items-start gap-3">
              <div className="w-8 h-8 rounded-lg bg-[var(--warning-muted)] border border-[rgba(245,158,11,0.2)] flex items-center justify-center shrink-0 text-sm font-bold text-[var(--warning)]">{idx + 1}</div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-[var(--foreground)]">{d.title}</p>
                <p className="text-xs text-[var(--muted-strong)] mt-1.5 leading-relaxed">{d.summary}</p>
                <div className="flex items-center gap-2 mt-3 flex-wrap">
                  {d.made_by && <span className="text-[10px] text-[var(--muted)]">Made by {d.made_by}</span>}
                  {d.confidence && <span className="text-[10px] text-[var(--success)]">{Math.round(d.confidence * 100)}% confidence</span>}
                  <TimestampPill seconds={getSegmentTimestamp(d.segment_id)} />
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="lg:col-span-2"><RightPanel /></div>
    </div>
  );
}

function ActionsTab() {
  const statusColors: Record<string, string> = {
    OPEN: "text-[var(--muted-strong)]",
    IN_PROGRESS: "text-[var(--warning)]",
    COMPLETED: "text-[var(--success)]",
    CANCELLED: "text-[var(--muted)]",
  };
  return (
    <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
      <div className="lg:col-span-3 space-y-3">
        {MOCK_ACTION_ITEMS.map((a) => (
          <div key={a.id} className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-4 hover:border-[var(--border-strong)] transition-colors flex items-start gap-3">
            <div className="w-5 h-5 rounded border-2 border-[var(--border-strong)] mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm font-medium text-[var(--foreground)]">{a.title}</p>
              <div className="flex items-center gap-3 mt-1.5 flex-wrap">
                {a.assignee && <span className="text-[10px] text-[var(--muted)]">to {a.assignee}</span>}
                {a.due_date && <span className="text-[10px] text-[var(--muted)]">Due {format(parseISO(a.due_date), "MMM d")}</span>}
                <span className={cn("text-[10px] font-medium", statusColors[a.status])}>{a.status.replace("_", " ")}</span>
                <TimestampPill seconds={getSegmentTimestamp(a.segment_id)} />
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="lg:col-span-2"><RightPanel /></div>
    </div>
  );
}

type TabId = "recap" | "transcript" | "decisions" | "actions";
const TABS: { id: TabId; label: string }[] = [
  { id: "recap",      label: "Recap" },
  { id: "transcript", label: "Transcript" },
  { id: "decisions",  label: "Decisions" },
  { id: "actions",    label: "Actions" },
];

interface Props {
  params: Promise<{ id: string }>;
}

export default function MeetingDetailPage({ params }: Props) {
  const { id } = use(params);
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = (searchParams.get("tab") ?? "recap") as TabId;

  const meeting = MOCK_MEETINGS.find((m) => m.id === id) ?? MOCK_MEETINGS[0];
  const source   = MEETING_SOURCE[meeting.id] ?? "Teams";
  const srcStyle = SOURCE_STYLE[source] ?? SOURCE_STYLE.Teams;

  const setTab = (tab: TabId) => {
    router.push(`/meetings/${id}?tab=${tab}`, { scroll: false });
  };

  return (
    <div className="animate-fade-in max-w-6xl mx-auto pb-12">
      <div className="mb-4">
        <Link href="/meetings" className="inline-flex items-center gap-1.5 text-xs text-[var(--muted)] hover:text-[var(--foreground)] transition-colors">
          <ArrowLeft size={12} />All Meetings
        </Link>
      </div>

      <div className="bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-6 mb-6">
        <div className="flex items-start gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <Badge variant={STATUS_BADGE[meeting.status]}>{meeting.status}</Badge>
              <span className={cn("text-xs font-medium", srcStyle.color)}>{srcStyle.label}</span>
            </div>
            <h1 className="text-xl font-bold text-[var(--foreground)] leading-tight">{meeting.title}</h1>
            <div className="flex items-center gap-4 mt-2 flex-wrap">
              <span className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
                <Clock size={12} />
                {format(parseISO(meeting.created_at), "EEEE, MMMM d, yyyy · h:mm a")}
              </span>
              {meeting.duration_seconds && (
                <span className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
                  <Clock size={12} />{formatDuration(meeting.duration_seconds)}
                </span>
              )}
              {meeting.participant_count && (
                <span className="flex items-center gap-1.5 text-xs text-[var(--muted)]">
                  <Users size={12} />{meeting.participant_count} participants
                </span>
              )}
            </div>
            <div className="flex items-center gap-1 mt-3">
              {["SN", "AS", "RM", "PK"].map((init, i) => (
                <div key={i} className="w-6 h-6 rounded-full border-2 border-[var(--surface-1)] flex items-center justify-center text-[9px] font-bold text-white"
                  style={{ background: `hsl(${i * 67 + 200}, 70%, 50%)`, marginLeft: i > 0 ? "-6px" : 0 }}>
                  {init}
                </div>
              ))}
              {meeting.participant_count && meeting.participant_count > 4 && (
                <span className="ml-1.5 text-[10px] text-[var(--muted)]">+{meeting.participant_count - 4} more</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)] transition-all">
              <FolderPlus size={13} />Add to Folder
            </button>
            <button aria-label="Download" className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)] transition-all">
              <Download size={14} />
            </button>
            <button aria-label="Share" className="p-2 rounded-lg border border-[var(--border)] bg-[var(--surface-2)] text-[var(--muted-strong)] hover:border-[var(--border-strong)] hover:text-[var(--foreground)] transition-all">
              <Share2 size={14} />
            </button>
          </div>
        </div>

        <div className="flex items-center gap-1 mt-6 border-t border-[var(--border)] pt-4">
          {TABS.map((tab) => (
            <button key={tab.id} onClick={() => setTab(tab.id)}
              className={cn(
                "px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150",
                activeTab === tab.id
                  ? "bg-[var(--primary-muted)] text-[var(--primary)] border border-[rgba(79,124,255,0.25)]"
                  : "text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]"
              )}>
              {tab.label}
              {tab.id === "actions" && (
                <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--success-muted)] text-[var(--success)]">{MOCK_ACTION_ITEMS.length}</span>
              )}
              {tab.id === "decisions" && (
                <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded-full bg-[var(--warning-muted)] text-[var(--warning)]">{MOCK_DECISIONS.length}</span>
              )}
            </button>
          ))}
        </div>
      </div>

      <div>
        {activeTab === "recap"      && <RecapTab />}
        {activeTab === "transcript" && <TranscriptTab />}
        {activeTab === "decisions"  && <DecisionsTab />}
        {activeTab === "actions"    && <ActionsTab />}
      </div>
    </div>
  );
}