"use client";

import React, { useState, useMemo, useEffect, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search, RefreshCw, Upload, Calendar, ArrowUpDown, Users, Sparkles,
  MoreHorizontal, SendHorizontal, Video, Clock, CheckCircle2, AlertCircle,
  Download, Trash2, Loader2, Radio, FileText, X, FileSearch, ExternalLink
} from "lucide-react";
import { format, parseISO, startOfWeek, endOfWeek, differenceInMinutes } from "date-fns";
import { UploadMeetingModal } from "@/components/meetings/UploadMeetingModal";
import { LiveMeetingModal } from "@/components/meetings/LiveMeetingModal";
import { DeleteMeetingModal } from "@/components/meetings/DeleteMeetingModal";
import { MeetingThumbnail } from "@/components/meetings/MeetingThumbnail";
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "@/components/ui/toast";
import { api } from "@/lib/api/client";

// ============================================================================
// 1. DOMAIN MODELS & TYPES
// ============================================================================

export type MeetingSource = "ZOOM" | "TEAMS" | "GOOGLE_MEET" | "UPLOAD" | "TRANSCRIPT_IMPORT";
export type ProcessingStatus = "COMPLETED" | "PROCESSING" | "FAILED" | "PENDING";

export interface MeetingFolder { id: string; name: string; }
export interface MeetingOwner { id: string; name: string; email: string; initials: string; }
export interface IntelligenceMetrics { decisionsCount: number; actionItemsCount: number; intelligenceScore: number; }

export interface MockMeeting {
  id: string; title: string; status: ProcessingStatus; source: MeetingSource;
  scheduledStartTime: string; scheduledEndTime: string; participantCount: number;
  metrics: IntelligenceMetrics; folder: MeetingFolder; owner: MeetingOwner;
  thumbnailGradient: string; thumbnailFaceInitial: string; weekGroupKey: string;
}

export interface ApiMeeting {
  id: string; title: string; status: string; owner_id: string; created_at: string;
  media_filename?: string | null; media_status?: string | null; source?: string | null;
}

const THUMBNAIL_GRADIENTS = [
  "from-indigo-900 via-slate-900 to-stone-900",
  "from-blue-900 via-indigo-950 to-slate-950",
  "from-emerald-950 via-teal-900 to-slate-900",
  "from-amber-900 via-stone-800 to-stone-950",
  "from-violet-950 via-slate-900 to-stone-900",
  "from-stone-600 via-stone-700 to-slate-900"
];

function getWeekGroupKey(dateStr: string): string {
  try {
    const d = parseISO(dateStr);
    const weekStart = startOfWeek(d, { weekStartsOn: 1 });
    const weekEnd = endOfWeek(d, { weekStartsOn: 1 });
    return `WEEK OF ${format(weekStart, "MMM d")}–${format(weekEnd, "MMM d, yyyy")}`.toUpperCase();
  } catch { return "RECENT MEETINGS"; }
}

function getDuration(start: string, end: string): string {
  try {
    const mins = differenceInMinutes(parseISO(end), parseISO(start));
    if (mins <= 0) return "—";
    if (mins < 60) return `${mins}m`;
    const h = Math.floor(mins / 60); const m = mins % 60;
    return m > 0 ? `${h}h ${m}m` : `${h}h`;
  } catch { return "—"; }
}

function transformApiMeeting(m: ApiMeeting): MockMeeting {
  let status: ProcessingStatus = "PENDING";
  if (m.status === "COMPLETED" || m.media_status === "READY") status = "COMPLETED";
  else if (m.status === "FAILED" || m.media_status === "FAILED" || m.media_status === "QUARANTINED") status = "FAILED";
  else if (m.status === "PROCESSING" || ["UPLOADED","SCANNING","VALIDATED","METADATA_EXTRACTING","PROCESSING_QUEUED","PROCESSING"].includes(m.media_status ?? "")) status = "PROCESSING";
  const hash = m.id.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0);
  const grad = THUMBNAIL_GRADIENTS[hash % THUMBNAIL_GRADIENTS.length];
  const weekKey = getWeekGroupKey(m.created_at);
  return {
    id: m.id,
    title: m.title || (m.media_filename ? m.media_filename.replace(/\.[^/.]+$/, "") : "Untitled Meeting"),
    status, source: (m.source as MeetingSource) || (m.media_filename ? "UPLOAD" : "ZOOM"),
    scheduledStartTime: m.created_at, scheduledEndTime: m.created_at, participantCount: 1,
    metrics: { decisionsCount: status === "COMPLETED" ? 3 : 0, actionItemsCount: status === "COMPLETED" ? 5 : 0, intelligenceScore: status === "COMPLETED" ? 92 : 0 },
    folder: { id: "f-uploads", name: "Uploaded Meetings" },
    owner: { id: m.owner_id, name: "Host (You)", email: "host@knowra.ai", initials: "YO" },
    thumbnailGradient: grad,
    thumbnailFaceInitial: m.source === "TRANSCRIPT_IMPORT" ? "📄" : (m.source === "UPLOAD" || m.media_filename ? "🎬" : "👩‍💼"),
    weekGroupKey: weekKey
  };
}

// ============================================================================
// 2. MOCK DATA (DEMO FALLBACK)
// ============================================================================

const MOCK_MEETINGS: MockMeeting[] = [
  { id: "m-001", title: "Onboarding to Knowra Platform - Enterprise Architecture Deep Dive", status: "COMPLETED", source: "ZOOM", scheduledStartTime: "2026-01-02T02:30:00Z", scheduledEndTime: "2026-01-02T02:38:00Z", participantCount: 4, metrics: { decisionsCount: 5, actionItemsCount: 8, intelligenceScore: 89 }, folder: { id: "f-1", name: "Sample Meetings" }, owner: { id: "u-1", name: "Sujal Nage", email: "sujal.nage@softude.com", initials: "SN" }, thumbnailGradient: "from-amber-700 via-stone-800 to-stone-900", thumbnailFaceInitial: "👩‍💼", weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026" },
  { id: "m-002", title: "Using a Meeting Intelligence Report - Executive Briefing", status: "COMPLETED", source: "ZOOM", scheduledStartTime: "2026-01-02T01:30:00Z", scheduledEndTime: "2026-01-02T01:34:00Z", participantCount: 4, metrics: { decisionsCount: 3, actionItemsCount: 6, intelligenceScore: 89 }, folder: { id: "f-1", name: "Sample Meetings" }, owner: { id: "u-2", name: "Elena Rostova", email: "elena.r@enterprise.io", initials: "ER" }, thumbnailGradient: "from-stone-600 via-stone-700 to-slate-900", thumbnailFaceInitial: "👩", weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026" },
  { id: "m-003", title: "Try Out Ask Knowra - Natural Language Context Retrieval QA", status: "COMPLETED", source: "ZOOM", scheduledStartTime: "2026-01-02T00:30:00Z", scheduledEndTime: "2026-01-02T00:37:00Z", participantCount: 4, metrics: { decisionsCount: 7, actionItemsCount: 11, intelligenceScore: 88 }, folder: { id: "f-1", name: "Sample Meetings" }, owner: { id: "u-3", name: "Sarah Chen", email: "sarah.c@enterprise.io", initials: "SC" }, thumbnailGradient: "from-amber-900 via-stone-800 to-stone-950", thumbnailFaceInitial: "👩‍🦰", weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026" },
  { id: "m-004", title: "Desktop and Mobile App Walkthrough - Multi-tenant Audio Ingestion", status: "COMPLETED", source: "TEAMS", scheduledStartTime: "2026-01-01T23:30:00Z", scheduledEndTime: "2026-01-01T23:34:00Z", participantCount: 4, metrics: { decisionsCount: 6, actionItemsCount: 4, intelligenceScore: 92 }, folder: { id: "f-1", name: "Sample Meetings" }, owner: { id: "u-4", name: "David Sterling", email: "david.s@enterprise.io", initials: "DS" }, thumbnailGradient: "from-slate-700 via-indigo-950 to-stone-900", thumbnailFaceInitial: "👩‍💼", weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026" },
  { id: "m-005", title: "Explore Real World Use Cases - High-Concurrency Diarization Run", status: "COMPLETED", source: "ZOOM", scheduledStartTime: "2026-01-01T22:30:00Z", scheduledEndTime: "2026-01-01T22:38:00Z", participantCount: 4, metrics: { decisionsCount: 9, actionItemsCount: 14, intelligenceScore: 87 }, folder: { id: "f-1", name: "Sample Meetings" }, owner: { id: "u-1", name: "Sujal Nage", email: "sujal.nage@softude.com", initials: "SN" }, thumbnailGradient: "from-emerald-950 via-teal-900 to-slate-900", thumbnailFaceInitial: "👩‍💻", weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026" },
  { id: "m-006", title: "Cross-Department Alignment on Data Isolation & Tenant Partitioning", status: "PROCESSING", source: "TEAMS", scheduledStartTime: "2026-01-08T14:00:00Z", scheduledEndTime: "2026-01-08T14:45:00Z", participantCount: 8, metrics: { decisionsCount: 2, actionItemsCount: 5, intelligenceScore: 94 }, folder: { id: "f-2", name: "Core Architecture" }, owner: { id: "u-2", name: "Elena Rostova", email: "elena.r@enterprise.io", initials: "ER" }, thumbnailGradient: "from-blue-900 via-indigo-950 to-slate-950", thumbnailFaceInitial: "👨‍💻", weekGroupKey: "WEEK OF JAN 5–JAN 11, 2026" },
  { id: "m-007", title: "Security Review: Ephemeral MinIO Token Rotation & Keycloak SSO", status: "PROCESSING", source: "GOOGLE_MEET", scheduledStartTime: "2026-01-07T11:00:00Z", scheduledEndTime: "2026-01-07T11:30:00Z", participantCount: 5, metrics: { decisionsCount: 4, actionItemsCount: 7, intelligenceScore: 91 }, folder: { id: "f-3", name: "Infra & Security" }, owner: { id: "u-3", name: "Sarah Chen", email: "sarah.c@enterprise.io", initials: "SC" }, thumbnailGradient: "from-violet-950 via-slate-900 to-stone-900", thumbnailFaceInitial: "👩‍🔬", weekGroupKey: "WEEK OF JAN 5–JAN 11, 2026" }
];

// ============================================================================
// 3. SOURCE BADGE — letter-style, consistent with filter chips
// ============================================================================

function SourceBadge({ source }: { source: MeetingSource }) {
  const configs: Record<MeetingSource, { bg: string; label: string; title: string }> = {
    ZOOM:              { bg: "bg-blue-500",    label: "Z",  title: "Zoom Recording" },
    TEAMS:             { bg: "bg-[#4B53BC]",   label: "T",  title: "Microsoft Teams" },
    GOOGLE_MEET:       { bg: "bg-emerald-600", label: "M",  title: "Google Meet" },
    TRANSCRIPT_IMPORT: { bg: "bg-slate-500",   label: "TX", title: "Imported Transcript" },
    UPLOAD:            { bg: "bg-indigo-500",  label: "U",  title: "Uploaded Recording" },
  };
  const c = configs[source];
  return (
    <div className={`w-5 h-5 rounded ${c.bg} flex items-center justify-center text-[7px] text-white font-bold shrink-0 shadow-sm`} title={c.title}>
      {c.label}
    </div>
  );
}

// ============================================================================
// 4. MAIN PAGE COMPONENT
// ============================================================================

export default function MeetingsPage() {
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<"meetings" | "processing">("meetings");
  const [searchQuery, setSearchQuery] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sortDirection, setSortDirection] = useState<"desc" | "asc">("desc");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [isLiveModalOpen, setIsLiveModalOpen] = useState(false);
  const [realMeetings, setRealMeetings] = useState<MockMeeting[]>([]);
  const [openMenuMeetingId, setOpenMenuMeetingId] = useState<string | null>(null);
  const [downloadingMeetingId, setDownloadingMeetingId] = useState<string | null>(null);
  const [deletingMeetingId, setDeletingMeetingId] = useState<string | null>(null);
  const [meetingToDelete, setMeetingToDelete] = useState<MockMeeting | null>(null);
  const [deletedMeetingIds, setDeletedMeetingIds] = useState<Set<string>>(new Set());
  const [activeSource, setActiveSource] = useState<MeetingSource | "ALL">("ALL");
  const [activeDateRange, setActiveDateRange] = useState<"all" | "today" | "week" | "month">("all");

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    router.push(`/chat?q=${encodeURIComponent(searchQuery.trim())}`);
  };

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (!(e.target as HTMLElement).closest("[data-meeting-menu]")) setOpenMenuMeetingId(null);
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, []);

  const handleDownloadVideo = async (meeting: MockMeeting, e: React.MouseEvent) => {
    e.stopPropagation();
    setDownloadingMeetingId(meeting.id);
    try {
      const res = await api.get<{ downloadUrl: string; filename?: string }>(`/meetings/${meeting.id}/media/download`);
      if (res?.downloadUrl) {
        const a = document.createElement("a");
        a.href = res.downloadUrl;
        a.download = res.filename || `${meeting.title.replace(/\s+/g, "_")}.mp4`;
        a.target = "_blank";
        document.body.appendChild(a); a.click(); document.body.removeChild(a);
        toast.success("Video download initiated");
      } else { toast.error("Video download stream is currently unavailable for this meeting."); }
    } catch { toast.error("Could not generate video download link. Please try again."); }
    finally { setDownloadingMeetingId(null); setOpenMenuMeetingId(null); }
  };

  const handleConfirmDelete = async () => {
    if (!meetingToDelete) return;
    setDeletingMeetingId(meetingToDelete.id);
    try { await api.delete(`/meetings/${meetingToDelete.id}`); }
    catch (err) { console.warn("Backend delete finished or fallback:", err); }
    finally {
      setDeletedMeetingIds((prev) => new Set([...prev, meetingToDelete.id]));
      setRealMeetings((prev) => prev.filter((m) => m.id !== meetingToDelete.id));
      setDeletingMeetingId(null); setMeetingToDelete(null);
    }
  };

  const fetchMeetings = useCallback(async () => {
    try {
      const res = await api.get<{ items: ApiMeeting[]; total: number }>("/meetings?page=1&page_size=50");
      if (res && Array.isArray(res.items)) setRealMeetings(res.items.map(transformApiMeeting));
    } catch (err) { console.warn("Could not fetch live meetings from backend:", err); }
    finally { setIsRefreshing(false); }
  }, []);

  useEffect(() => { fetchMeetings(); }, [fetchMeetings]);

  useEffect(() => {
    const hasProcessing = realMeetings.some((m) => m.status === "PROCESSING" || m.status === "PENDING");
    if (!hasProcessing && activeTab !== "processing") return;
    const interval = setInterval(() => { fetchMeetings(); }, 10000);
    return () => clearInterval(interval);
  }, [realMeetings, activeTab, fetchMeetings]);

  const handleRefresh = () => { setIsRefreshing(true); fetchMeetings(); };

  const allMeetings = useMemo(() => {
    const base = realMeetings.length > 0 ? realMeetings : MOCK_MEETINGS;
    return base.filter((m) => !deletedMeetingIds.has(m.id));
  }, [realMeetings, deletedMeetingIds]);

  const completedCount = useMemo(() => allMeetings.filter((m) => m.status === "COMPLETED").length, [allMeetings]);
  const processingCount = useMemo(() => allMeetings.filter((m) => m.status === "PROCESSING" || m.status === "PENDING").length, [allMeetings]);

  const sourceCounts = useMemo(() => {
    const counts: Record<string, number> = { ALL: allMeetings.length };
    allMeetings.forEach((m) => { counts[m.source] = (counts[m.source] || 0) + 1; });
    return counts;
  }, [allMeetings]);

  const filteredMeetings = useMemo(() => {
    const now = new Date();
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const weekStart = new Date(todayStart); weekStart.setDate(todayStart.getDate() - 7);
    const monthStart = new Date(todayStart); monthStart.setDate(todayStart.getDate() - 30);
    return allMeetings
      .filter((item) => {
        if (activeTab === "processing" && item.status === "COMPLETED") return false;
        if (activeSource !== "ALL" && item.source !== activeSource) return false;
        if (activeDateRange !== "all") {
          const d = new Date(item.scheduledStartTime);
          if (activeDateRange === "today" && d < todayStart) return false;
          if (activeDateRange === "week" && d < weekStart) return false;
          if (activeDateRange === "month" && d < monthStart) return false;
        }
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          if (!item.title.toLowerCase().includes(q) && !item.owner.name.toLowerCase().includes(q) && !item.folder.name.toLowerCase().includes(q)) return false;
        }
        return true;
      })
      .sort((a, b) => {
        const tA = new Date(a.scheduledStartTime).getTime();
        const tB = new Date(b.scheduledStartTime).getTime();
        return sortDirection === "desc" ? tB - tA : tA - tB;
      });
  }, [allMeetings, activeTab, searchQuery, sortDirection, activeSource, activeDateRange]);

  const groupedMeetings = useMemo(() => {
    const groups: { [key: string]: MockMeeting[] } = {};
    for (const m of filteredMeetings) {
      if (!groups[m.weekGroupKey]) groups[m.weekGroupKey] = [];
      groups[m.weekGroupKey].push(m);
    }
    return groups;
  }, [filteredMeetings]);

  const SOURCE_CHIPS: { value: MeetingSource | "ALL"; label: string; badgeCls: string; badgeLabel: string }[] = [
    { value: "ALL",         label: "All",     badgeCls: "bg-slate-300 text-slate-700", badgeLabel: "★" },
    { value: "ZOOM",        label: "Zoom",    badgeCls: "bg-blue-500 text-white",      badgeLabel: "Z" },
    { value: "TEAMS",       label: "Teams",   badgeCls: "bg-[#4B53BC] text-white",     badgeLabel: "T" },
    { value: "GOOGLE_MEET", label: "Meet",    badgeCls: "bg-emerald-500 text-white",   badgeLabel: "M" },
    { value: "UPLOAD",      label: "Uploads", badgeCls: "bg-indigo-500 text-white",    badgeLabel: "U" },
  ];

  return (
    <div className="w-full min-w-0 flex-1 overflow-x-hidden">
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-5 pb-16">

        {/* PAGE HEADER */}
        <PageHeader
          title="Meetings"
          subtitle={`${completedCount} processed${processingCount > 0 ? ` · ${processingCount} syncing` : ""} · ${allMeetings.length} total`}
          icon={Video}
          statusDot={processingCount > 0}
          badge={
            processingCount > 0 ? (
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200 flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-pulse" />
                {processingCount} Syncing
              </span>
            ) : null
          }
        />

        {/* SEARCH BAR */}
        <form
          onSubmit={handleSearchSubmit}
          className="relative w-full border border-slate-200 hover:border-slate-300 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-500/10 rounded-xl flex items-center px-4 py-2.5 bg-white shrink-0 transition-all shadow-sm"
        >
          <Search className="w-4 h-4 text-slate-400 mr-3 shrink-0 pointer-events-none" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by title, host, or ask AI anything..."
            className="flex-1 text-sm text-slate-800 placeholder:text-slate-400 bg-transparent border-0 outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 min-w-0"
            style={{ outline: "none", boxShadow: "none" }}
          />
          {searchQuery && (
            <button type="button" onClick={() => setSearchQuery("")} className="text-slate-400 hover:text-slate-600 p-1 mr-2 rounded-full hover:bg-slate-100 transition-colors cursor-pointer shrink-0">
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          {!searchQuery && (
            <span className="hidden sm:flex items-center gap-1 text-[11px] text-slate-400 mr-3 shrink-0 select-none">
              <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] font-mono">⌘K</kbd>
            </span>
          )}
          <button
            type="submit"
            disabled={!searchQuery.trim()}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
              searchQuery.trim() ? "bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm cursor-pointer active:scale-95" : "bg-slate-100 text-slate-400 cursor-default"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ask AI</span>
            <SendHorizontal className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* TABS & ACTIONS */}
        <div className="flex items-center justify-between w-full shrink-0">
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setActiveTab("meetings")}
              className={`cursor-pointer transition-all px-4 py-2 rounded-lg text-sm font-semibold flex items-center gap-2 ${
                activeTab === "meetings" ? "bg-indigo-50 text-indigo-700" : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
              }`}
            >
              Meetings
              <span className={`text-[11px] px-1.5 py-0.5 rounded-full font-semibold ${activeTab === "meetings" ? "bg-indigo-100 text-indigo-700" : "bg-slate-100 text-slate-500"}`}>
                {completedCount}
              </span>
            </button>
            {processingCount > 0 && (
              <button
                type="button"
                onClick={() => setActiveTab("processing")}
                className={`cursor-pointer transition-all px-4 py-2 rounded-lg text-sm flex items-center gap-2 ${
                  activeTab === "processing" ? "bg-amber-50 text-amber-700 font-semibold" : "text-slate-500 hover:text-slate-800 hover:bg-slate-100 font-medium"
                }`}
              >
                Processing
                <span className="text-[11px] px-1.5 py-0.5 rounded-full font-semibold bg-amber-100 text-amber-700 animate-pulse">{processingCount}</span>
              </button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={handleRefresh} className="p-2 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer" title="Refresh">
              <RefreshCw className={`w-4 h-4 ${isRefreshing ? "animate-spin text-indigo-600" : ""}`} />
            </button>
            <button type="button" onClick={() => setIsLiveModalOpen(true)} className="flex items-center gap-2 px-3.5 py-2 rounded-lg font-medium text-sm bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm transition-colors cursor-pointer shrink-0">
              <Radio className="w-3.5 h-3.5 animate-pulse" />
              <span>Live</span>
            </button>
            <button type="button" onClick={() => setIsUploadModalOpen(true)} className="flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-colors cursor-pointer shrink-0">
              <Upload className="w-3.5 h-3.5" />
              <span>Upload</span>
            </button>
          </div>
        </div>

        {/* FILTER CHIP BAR */}
        <div className="flex flex-wrap items-center gap-2 w-full shrink-0">
          {SOURCE_CHIPS.map((chip) => {
            const count = sourceCounts[chip.value] ?? 0;
            if (chip.value !== "ALL" && count === 0) return null;
            const isActive = activeSource === chip.value;
            return (
              <button
                key={chip.value}
                type="button"
                onClick={() => setActiveSource(chip.value)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer select-none ${
                  isActive ? "bg-indigo-600 border-indigo-600 text-white shadow-sm" : "bg-white border-slate-200 text-slate-600 hover:border-indigo-300 hover:text-indigo-700 hover:bg-indigo-50/50"
                }`}
              >
                <span className={`w-4 h-4 rounded text-[8px] font-bold flex items-center justify-center ${chip.badgeCls}`}>{chip.badgeLabel}</span>
                {chip.label}
                <span className={`text-[10px] font-mono ${isActive ? "text-indigo-200" : "text-slate-400"}`}>{count}</span>
              </button>
            );
          })}

          <div className="h-5 w-px bg-slate-200 mx-0.5 shrink-0" />

          {(["today", "week", "month"] as const).map((val) => {
            const labels = { today: "Today", week: "This Week", month: "This Month" };
            const isActive = activeDateRange === val;
            return (
              <button
                key={val}
                type="button"
                onClick={() => setActiveDateRange(activeDateRange === val ? "all" : val)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer select-none ${
                  isActive ? "bg-indigo-50 border-indigo-300 text-indigo-700" : "bg-white border-slate-200 text-slate-600 hover:border-indigo-200 hover:text-indigo-600 hover:bg-indigo-50/40"
                }`}
              >
                <Calendar className="w-3 h-3" />
                {labels[val]}
              </button>
            );
          })}

          <div className="ml-auto flex items-center gap-3">
            <span className="text-xs text-slate-500 select-none tabular-nums">
              <span className="font-semibold text-slate-700">{filteredMeetings.length}</span> of {allMeetings.length}
            </span>
            {(activeSource !== "ALL" || activeDateRange !== "all") && (
              <button type="button" onClick={() => { setActiveSource("ALL"); setActiveDateRange("all"); }} className="flex items-center gap-1 text-xs font-medium text-slate-400 hover:text-rose-600 transition-colors cursor-pointer">
                <X className="w-3 h-3" />Clear
              </button>
            )}
            <button
              type="button"
              onClick={() => setSortDirection((p) => (p === "desc" ? "asc" : "desc"))}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs font-semibold border transition-all cursor-pointer select-none ${
                sortDirection === "asc" ? "border-indigo-300 bg-indigo-50 text-indigo-700" : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
              }`}
            >
              <ArrowUpDown className="w-3 h-3" />
              {sortDirection === "desc" ? "Newest" : "Oldest"}
            </button>
          </div>
        </div>

        {/* DATA TABLE */}
        <div className="w-full bg-white border border-slate-200 rounded-xl shadow-sm overflow-hidden">
          {/* Header */}
          <div className="grid grid-cols-[76px_minmax(260px,_1fr)_140px_72px_180px_52px] gap-4 items-center border-b border-slate-100 py-2.5 px-4 text-[11px] font-semibold text-slate-400 uppercase tracking-wider bg-slate-50/80 select-none">
            <div>Source</div>
            <div>Meeting</div>
            <div className="flex items-center gap-1 cursor-pointer hover:text-slate-700 transition-colors" onClick={() => setSortDirection((p) => (p === "desc" ? "asc" : "desc"))}>
              Date & Time <ArrowUpDown className="w-3 h-3" />
            </div>
            <div className="flex items-center gap-1"><Clock className="w-3 h-3" />Dur.</div>
            <div className="flex items-center gap-1"><Users className="w-3 h-3" />Host</div>
            <div />
          </div>

          {Object.keys(groupedMeetings).length === 0 ? (
            <div className="py-20 flex flex-col items-center gap-4 text-center">
              <div className="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center">
                <FileSearch className="w-7 h-7 text-slate-400" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-700">No meetings found</p>
                <p className="text-xs text-slate-400 mt-1">
                  {searchQuery || activeSource !== "ALL" || activeDateRange !== "all"
                    ? "Try adjusting your filters or search query."
                    : "Upload your first meeting or connect a live session to get started."}
                </p>
              </div>
              {(searchQuery || activeSource !== "ALL" || activeDateRange !== "all") ? (
                <button type="button" onClick={() => { setSearchQuery(""); setActiveSource("ALL"); setActiveDateRange("all"); }} className="px-4 py-2 rounded-lg text-sm font-medium bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors cursor-pointer">
                  Clear all filters
                </button>
              ) : (
                <button type="button" onClick={() => setIsUploadModalOpen(true)} className="px-4 py-2 rounded-lg text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm transition-colors cursor-pointer">
                  Upload a meeting
                </button>
              )}
            </div>
          ) : (
            Object.entries(groupedMeetings).map(([groupKey, meetingsInGroup]) => (
              <div key={groupKey} className="w-full">
                <div className="bg-slate-50 text-[10px] uppercase tracking-wider font-bold text-slate-400 py-1.5 px-4 border-b border-slate-100">{groupKey}</div>
                <div className="divide-y divide-slate-50">
                  {meetingsInGroup.map((meeting) => {
                    const startDate = parseISO(meeting.scheduledStartTime);
                    const duration = getDuration(meeting.scheduledStartTime, meeting.scheduledEndTime);
                    return (
                      <div
                        key={meeting.id}
                        className="grid grid-cols-[76px_minmax(260px,_1fr)_140px_72px_180px_52px] gap-4 items-center py-3 px-4 hover:bg-indigo-50/20 transition-colors bg-white w-full group"
                      >
                        {/* Col 1: Thumbnail + source badge */}
                        <div className="relative w-[64px] h-[40px] rounded-lg overflow-hidden border border-slate-200 shadow-sm shrink-0">
                          <MeetingThumbnail meetingId={meeting.id} title={meeting.title} fallbackGradient={meeting.thumbnailGradient} />
                          <div className="absolute bottom-1 right-1 z-10"><SourceBadge source={meeting.source} /></div>
                        </div>

                        {/* Col 2: Title + status + hover actions */}
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <Link href={`/meetings/${meeting.id}`} className="text-sm font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors truncate" title={meeting.title}>
                            {meeting.title}
                          </Link>
                          <div className="flex items-center gap-2 text-xs text-slate-400 flex-wrap">
                            <span className="flex items-center gap-1"><Users className="w-3 h-3" />{meeting.participantCount}</span>
                            {meeting.status === "PROCESSING" && <span className="flex items-center gap-1 text-amber-600 font-medium"><Clock className="w-3 h-3 animate-spin" />Processing…</span>}
                            {meeting.status === "PENDING" && <span className="flex items-center gap-1 text-amber-500 font-medium"><Clock className="w-3 h-3" />Queued</span>}
                            {meeting.status === "FAILED" && <span className="flex items-center gap-1 text-rose-600 font-medium"><AlertCircle className="w-3 h-3" />Failed</span>}
                            {meeting.status === "COMPLETED" && <span className="flex items-center gap-1 text-emerald-600 font-medium"><CheckCircle2 className="w-3 h-3" />Ready</span>}
                            <div className="hidden group-hover:flex items-center gap-2">
                              <span className="text-slate-200">·</span>
                              <Link href={`/meetings/${meeting.id}/recap`} className="flex items-center gap-1 text-indigo-600 hover:text-indigo-800 font-medium transition-colors" onClick={(e) => e.stopPropagation()}>
                                <Sparkles className="w-3 h-3" />Recap
                              </Link>
                              <span className="text-slate-200">·</span>
                              <Link href={`/meetings/${meeting.id}/transcript`} className="flex items-center gap-1 text-slate-500 hover:text-slate-700 font-medium transition-colors" onClick={(e) => e.stopPropagation()}>
                                <FileText className="w-3 h-3" />Transcript
                              </Link>
                              <span className="text-slate-200">·</span>
                              <Link href={`/meetings/${meeting.id}`} className="flex items-center gap-1 text-slate-500 hover:text-slate-700 font-medium transition-colors" onClick={(e) => e.stopPropagation()}>
                                <ExternalLink className="w-3 h-3" />Open
                              </Link>
                            </div>
                          </div>
                        </div>

                        {/* Col 3: Date & Time */}
                        <div className="flex flex-col justify-center select-none">
                          <span className="text-sm font-medium text-slate-700">{format(startDate, "EEE, MMM d")}</span>
                          <span className="text-xs text-slate-400 mt-0.5">{format(startDate, "h:mm a")}</span>
                        </div>

                        {/* Col 4: Duration */}
                        <div className="text-sm font-medium text-slate-600 select-none tabular-nums">{duration}</div>

                        {/* Col 5: Host + folder */}
                        <div className="flex flex-col justify-center gap-0.5 min-w-0">
                          <span className="text-xs font-semibold text-slate-700 truncate" title={meeting.owner.name}>{meeting.owner.name}</span>
                          <Link href="/folders" onClick={(e) => e.stopPropagation()} className="text-[11px] text-slate-400 hover:text-indigo-600 truncate transition-colors" title={meeting.folder.name}>
                            {meeting.folder.name}
                          </Link>
                        </div>

                        {/* Col 6: Context menu */}
                        <div className="flex items-center justify-end relative" data-meeting-menu>
                          <button
                            type="button"
                            onClick={(e) => { e.stopPropagation(); setOpenMenuMeetingId((p) => (p === meeting.id ? null : meeting.id)); }}
                            className={`text-slate-300 hover:text-slate-600 cursor-pointer p-1.5 rounded-lg hover:bg-slate-100 transition-colors ${openMenuMeetingId === meeting.id ? "bg-slate-100 text-slate-700" : ""}`}
                          >
                            <MoreHorizontal className="w-4 h-4" />
                          </button>
                          {openMenuMeetingId === meeting.id && (
                            <div
                              className="absolute right-0 top-full mt-1.5 w-48 bg-white border border-slate-200/90 rounded-xl shadow-xl py-1 z-50 animate-in fade-in zoom-in-95 text-slate-700"
                              onClick={(e) => e.stopPropagation()}
                            >
                              <Link
                                href={`/meetings/${meeting.id}`}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setOpenMenuMeetingId(null);
                                }}
                                className="w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-indigo-600 flex items-center gap-2.5 transition-colors cursor-pointer"
                              >
                                <ExternalLink className="w-3.5 h-3.5 text-slate-400" />
                                <span>Open Meeting</span>
                              </Link>

                              <button
                                type="button"
                                disabled={downloadingMeetingId === meeting.id}
                                onClick={(e) => handleDownloadVideo(meeting, e)}
                                className="w-full px-3 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 hover:text-indigo-600 flex items-center gap-2.5 transition-colors cursor-pointer disabled:opacity-50"
                              >
                                {downloadingMeetingId === meeting.id ? (
                                  <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                                ) : (
                                  <Download className="w-3.5 h-3.5 text-slate-400" />
                                )}
                                <span>{downloadingMeetingId === meeting.id ? "Preparing…" : "Download Video"}</span>
                              </button>

                              <div className="my-1 border-t border-slate-100" />

                              <button
                                type="button"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setMeetingToDelete(meeting);
                                  setOpenMenuMeetingId(null);
                                }}
                                className="w-full px-3 py-2 text-left text-xs font-medium text-rose-600 hover:bg-rose-50 flex items-center gap-2.5 transition-colors cursor-pointer"
                              >
                                <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                                <span>Delete Meeting</span>
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      <UploadMeetingModal isOpen={isUploadModalOpen} onClose={() => setIsUploadModalOpen(false)} onUploadComplete={() => { handleRefresh(); setActiveTab("meetings"); }} />
      <LiveMeetingModal isOpen={isLiveModalOpen} onClose={() => setIsLiveModalOpen(false)} onLiveStarted={() => { handleRefresh(); }} />
      <DeleteMeetingModal isOpen={Boolean(meetingToDelete)} meetingTitle={meetingToDelete?.title || "Meeting"} isDeleting={Boolean(deletingMeetingId)} onClose={() => setMeetingToDelete(null)} onConfirm={handleConfirmDelete} />
    </div>
  );
}
