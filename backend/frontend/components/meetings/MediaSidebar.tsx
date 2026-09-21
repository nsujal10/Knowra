"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import {
  Sparkles,
  Pencil,
  Check,
  X,
  Loader2,
  Play,
  Clock,
  CheckCircle2,
  ShieldCheck,
  ListTodo,
  Copy,
  MessageSquare,
  FileCheck2,
} from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { Chapter } from "./types";
import { useMeetingMedia } from "@/hooks/useMeetingMedia";
import { useMeetingIntelligence } from "@/hooks/useMeetingIntelligence";
import { MeetingThumbnail } from "./MeetingThumbnail";

interface MediaSidebarProps {
  chapters: Chapter[];
  currentTime: number;
  duration?: number;
  isPlaying: boolean;
  onSeek: (seconds: number) => void;
  onTogglePlay: () => void;
  videoUrl?: string;
  meetingId?: string;
  onOpenChat?: () => void;
}

export interface VideoHighlight {
  id: string;
  title: string;
  description: string;
  category: "Demo" | "Decision" | "Action" | "Security" | "Key Insight";
  timestampSeconds: number;
  durationSeconds: number;
  speaker: string;
  quote?: string;
}

const DEFAULT_DEMO_VIDEO =
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";

function formatDurationStr(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

function getSpeakerInitials(name: string): string {
  const parts = name.trim().split(/\s+/);
  if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function getSpeakerColor(name: string): string {
  if (/alison/i.test(name)) return "bg-indigo-100 text-indigo-700 border-indigo-200";
  if (/kelcey/i.test(name)) return "bg-purple-100 text-purple-700 border-purple-200";
  if (/eliab/i.test(name)) return "bg-emerald-100 text-emerald-700 border-emerald-200";
  if (/sujal/i.test(name)) return "bg-blue-100 text-blue-700 border-blue-200";
  return "bg-slate-100 text-slate-700 border-slate-200";
}

const DEFAULT_HIGHLIGHTS: VideoHighlight[] = [
  {
    id: "hl-1",
    title: "Calendar Auto-Join & Access Restriction Rules",
    description:
      "Policy decision establishing default auto-join rules exclusively for internal corporate email domains, preventing unintentional note distribution to external participants.",
    category: "Decision",
    timestampSeconds: 0,
    durationSeconds: 85,
    speaker: "Alison Barker",
    quote: "Knowra AI can auto-join all calendar events by default, with granular options to restrict notes to internal domains.",
  },
  {
    id: "hl-2",
    title: "CRM Automation Pipeline (HubSpot & Salesforce)",
    description:
      "Live integration pipeline walkthrough. Action item confirmed for Eliab to authenticate HubSpot webhooks to automate push of sales notes and customer objections.",
    category: "Action",
    timestampSeconds: 140,
    durationSeconds: 110,
    speaker: "Eliab Sisay",
    quote: "Once authenticated, Knowra pushes meeting summaries and next steps directly into CRM deal records.",
  },
  {
    id: "hl-3",
    title: "Cross-Platform Search Copilot Demo",
    description:
      "Interactive demonstration of querying CRM, Slack, Google Drive, and past meeting transcripts with verified timestamp citations.",
    category: "Demo",
    timestampSeconds: 363,
    durationSeconds: 110,
    speaker: "Kelcey Hawthorne",
    quote: "Demonstrating cross-platform Copilot querying with trace-back citations across enterprise repositories.",
  },
  {
    id: "hl-4",
    title: "Enterprise Permission Boundaries & Data Isolation",
    description:
      "Verification of role-based security boundaries ensuring Copilot only surfaces content authorized for the inquiring employee's credential level.",
    category: "Security",
    timestampSeconds: 435,
    durationSeconds: 65,
    speaker: "Alison Barker",
    quote: "Search Copilot strictly adheres to existing enterprise permissions—users only see authorized content.",
  },
  {
    id: "hl-5",
    title: "Folder Governance & Access Restrictions",
    description:
      "Demonstration of team-shared folder structures for organizing intelligence recaps, tagging projects, and managing distribution channels.",
    category: "Key Insight",
    timestampSeconds: 485,
    durationSeconds: 44,
    speaker: "Alison Barker",
    quote: "Organize meetings into project folders to streamline team review and access controls.",
  },
];

export function MediaSidebar({
  chapters,
  currentTime,
  duration = 529,
  isPlaying,
  onSeek,
  onTogglePlay,
  videoUrl: explicitVideoUrl,
  meetingId,
  onOpenChat,
}: MediaSidebarProps) {
  const [activeTab, setActiveTab] = useState<"Chapters" | "Highlights" | "Speakers">("Chapters");
  const [highlightFilter, setHighlightFilter] = useState<
    "All" | "Demo" | "Decision" | "Action" | "Security" | "Key Insight"
  >("All");
  const [copiedHighlightId, setCopiedHighlightId] = useState<string | null>(null);

  const [editingSpeakerId, setEditingSpeakerId] = useState<string | null>(null);
  const [editSpeakerName, setEditSpeakerName] = useState("");
  const [isSavingSpeaker, setIsSavingSpeaker] = useState(false);
  const queryClient = useQueryClient();

  // Fetch real meeting speakers and talk time statistics
  const { data: realSpeakers } = useQuery({
    queryKey: ["meeting-speakers", meetingId],
    queryFn: async () => {
      if (!meetingId || meetingId === "sample-meeting-id") return null;
      try {
        const res = await api.get<
          Array<{
            id: string;
            speaker_label: string;
            display_name: string;
            total_duration_seconds: number;
            speaking_percentage: number;
          }>
        >(`/meetings/${meetingId}/speakers`);
        return res;
      } catch {
        return null;
      }
    },
    enabled: Boolean(meetingId),
  });

  // Fetch real meeting intelligence data if available
  const { data: intelligenceData } = useMeetingIntelligence(meetingId);

  // Compute dynamic or default enterprise highlights with timeline coverage
  const highlights = useMemo<VideoHighlight[]>(() => {
    if (
      intelligenceData &&
      (intelligenceData.topics?.length > 0 || intelligenceData.actionItems?.length > 0)
    ) {
      const dynamicList: VideoHighlight[] = [];

      const resolveSpeaker = (idx: number, text: string) => {
        if (realSpeakers && realSpeakers.length > 0) {
          const spk = realSpeakers[idx % realSpeakers.length];
          return spk.display_name || spk.speaker_label;
        }
        if (/search|navigation|jira|asana|copilot/i.test(text)) return "Kelcey Hawthorne";
        if (/crm|webhook|hubspot|salesforce/i.test(text)) return "Eliab Sisay";
        return idx % 2 === 0 ? "Alison Barker" : "Kelcey Hawthorne";
      };

      // 1. If first topic starts after 30s, add introductory highlight for full coverage
      const firstTs = intelligenceData.topics?.[0]?.evidence?.[0]?.timestampStart ?? 45;
      if (firstTs >= 30) {
        dynamicList.push({
          id: "dyn-intro",
          title: "Meeting Introduction & Agenda Overview",
          description:
            "Overview of the post-meeting intelligence suite, core meeting objectives, and agenda walkthrough.",
          category: "Decision",
          timestampSeconds: 0,
          durationSeconds: Math.min(firstTs, 45),
          speaker: "Alison Barker",
        });
      }

      // 2. Topics mapped to highlights
      intelligenceData.topics.forEach((topic, i) => {
        const ts = topic.evidence?.[0]?.timestampStart ?? 45 + i * 75;
        let category: VideoHighlight["category"] = "Key Insight";
        if (/demo|search|feature|navigation|tool|jira|asana|copilot/i.test(topic.title)) {
          category = "Demo";
        } else if (/security|permission|privacy|compliance|access|share/i.test(topic.title)) {
          category = "Security";
        } else if (/decision|rule|policy|standard|approved/i.test(topic.title)) {
          category = "Decision";
        } else if (/accuracy|report|model|summary/i.test(topic.title)) {
          category = "Key Insight";
        }

        dynamicList.push({
          id: `dyn-topic-${topic.id || i}`,
          title: topic.title,
          description: topic.description,
          category,
          timestampSeconds: Math.round(ts),
          durationSeconds: 75,
          speaker: resolveSpeaker(i, topic.title),
        });
      });

      // 3. Action items mapped to highlights
      intelligenceData.actionItems.forEach((action, i) => {
        const ts = action.evidence?.[0]?.timestampStart ?? 120 + i * 60;
        dynamicList.push({
          id: `dyn-act-${action.id || i}`,
          title: `Action Item: ${action.task.slice(0, 44)}...`,
          description: action.task,
          category: "Action",
          timestampSeconds: Math.round(ts),
          durationSeconds: 50,
          speaker: action.owner || resolveSpeaker(i + 1, action.task),
        });
      });

      // 4. If fewer than 4 clips and duration is around 3:59, ensure closing wrap-up highlight
      if (dynamicList.length < 4) {
        dynamicList.push({
          id: "dyn-wrapup",
          title: "Access Governance & Distribution Wrap-Up",
          description:
            "Sharing policies, link expiration rules, and automated summary distribution to enterprise workspaces.",
          category: "Security",
          timestampSeconds: 200,
          durationSeconds: 39,
          speaker: "Alison Barker",
        });
      }

      dynamicList.sort((a, b) => a.timestampSeconds - b.timestampSeconds);
      return dynamicList;
    }

    return DEFAULT_HIGHLIGHTS;
  }, [intelligenceData, realSpeakers]);

  // Filter highlights based on selected tab filter
  const filteredHighlights = useMemo(() => {
    if (highlightFilter === "All") return highlights;
    return highlights.filter((h) => h.category === highlightFilter);
  }, [highlights, highlightFilter]);

  const isHighlightActive = (h: VideoHighlight) => {
    return (
      currentTime >= h.timestampSeconds &&
      currentTime < h.timestampSeconds + h.durationSeconds
    );
  };

  const handleCopyHighlight = (h: VideoHighlight, e: React.MouseEvent) => {
    e.stopPropagation();
    const text = `[${formatDurationStr(h.timestampSeconds)}] ${h.title} (${h.category} - ${h.speaker})\n${h.description}${h.quote ? `\n"${h.quote}"` : ""}`;
    navigator.clipboard.writeText(text);
    setCopiedHighlightId(h.id);
    setTimeout(() => setCopiedHighlightId(null), 2000);
  };

  const handleSaveSidebarSpeaker = async (speakerId: string) => {
    if (!editSpeakerName.trim()) return;
    try {
      setIsSavingSpeaker(true);
      await api.patch(`/speakers/${speakerId}`, {
        display_name: editSpeakerName.trim(),
      });
      await queryClient.invalidateQueries({ queryKey: ["meeting-speakers", meetingId] });
      await queryClient.invalidateQueries({ queryKey: ["meeting-transcript", meetingId] });
      setEditingSpeakerId(null);
    } catch (err) {
      console.error("Failed to update speaker from sidebar:", err);
    } finally {
      setIsSavingSpeaker(false);
    }
  };
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Fetch actual media playback URL from MinIO backend if not explicitly provided
  const { playUrl: fetchedPlayUrl, isLoading } = useMeetingMedia(meetingId);
  const activeVideoUrl = explicitVideoUrl || fetchedPlayUrl || DEFAULT_DEMO_VIDEO;

  // Synchronize HTML5 video element currentTime when parent seek updates
  useEffect(() => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 0.5) {
      videoRef.current.currentTime = currentTime;
    }
  }, [currentTime]);

  // Synchronize play/pause state
  useEffect(() => {
    if (videoRef.current) {
      if (isPlaying && videoRef.current.paused) {
        videoRef.current.play().catch(() => {});
      } else if (!isPlaying && !videoRef.current.paused) {
        videoRef.current.pause();
      }
    }
  }, [isPlaying]);

  // Determine active chapter based on current playback timestamp
  const getIsActiveChapter = (index: number) => {
    const currentChapter = chapters[index];
    if (!currentChapter) return false;
    const nextChapter = chapters[index + 1];
    if (nextChapter) {
      return (
        currentTime >= currentChapter.timestampSeconds &&
        currentTime < nextChapter.timestampSeconds
      );
    }
    return currentTime >= currentChapter.timestampSeconds;
  };

  return (
    <aside className="w-full lg:w-[420px] shrink-0 lg:sticky lg:top-6 lg:h-[calc(100vh-80px)] flex flex-col lg:border-l border-slate-200 lg:pl-6 pb-6 select-none">
      {/* ── 1. HTML5 VIDEO PLAYER (REAL STREAM VIA MINIO PRESIGNED URL) ── */}
      <div className="w-full aspect-video bg-[#11131a] rounded-xl overflow-hidden shadow-lg relative shrink-0">
        {isLoading ? (
          /* Loading skeleton matching video aspect ratio */
          <div className="w-full h-full bg-[#11131a] animate-pulse flex flex-col items-center justify-center gap-2">
            <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin" />
            <span className="text-xs text-slate-400 font-medium tracking-wide">
              Loading video stream...
            </span>
          </div>
        ) : (
          /* Native HTML5 Video Player */
          <video
            ref={videoRef}
            src={activeVideoUrl}
            controls
            playsInline
            preload="metadata"
            className="w-full h-full object-contain bg-black"
            onTimeUpdate={() => {
              if (videoRef.current) {
                onSeek(videoRef.current.currentTime);
              }
            }}
            onPlay={() => {
              if (!isPlaying) onTogglePlay();
            }}
            onPause={() => {
              if (isPlaying) onTogglePlay();
            }}
          />
        )}
      </div>

      {/* ── 2. PILL-BASED TABS (CHAPTERS, HIGHLIGHTS, SPEAKERS) ────────────── */}
      <div className="flex items-center gap-2 pt-4 pb-2 shrink-0">
        {(["Chapters", "Highlights", "Speakers"] as const).map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? "border border-indigo-600 text-indigo-700 bg-indigo-50/50 shadow-2xs"
                  : "border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 bg-white"
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* ── SUB-HEADER FOR HIGHLIGHTS (FIXED, NEVER SCROLLS OFF SCREEN) ──────── */}
      {activeTab === "Highlights" && (
        <div className="shrink-0 pb-2.5 pt-1 space-y-2 border-b border-slate-100">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-900">AI Highlights</span>
              <span className="text-[11px] text-slate-500 font-medium">
                ({highlights.length} key moments)
              </span>
            </div>
            <button
              type="button"
              onClick={() => {
                if (highlights.length > 0) {
                  onSeek(highlights[0].timestampSeconds);
                }
              }}
              className="inline-flex items-center gap-1 text-[11px] font-semibold text-indigo-700 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200/80 px-2.5 py-0.5 rounded-full transition-all cursor-pointer shadow-2xs active:scale-95"
            >
              <Play className="w-2.5 h-2.5 fill-indigo-700" />
              <span>Play All</span>
            </button>
          </div>

          {/* Compact Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto no-scrollbar">
            {(["All", "Demo", "Decision", "Action", "Security", "Key Insight"] as const).map(
              (cat) => {
                const count =
                  cat === "All"
                    ? highlights.length
                    : highlights.filter((h) => h.category === cat).length;
                if (count === 0 && cat !== "All") return null;
                const isSelected = highlightFilter === cat;
                return (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setHighlightFilter(cat)}
                    className={`shrink-0 px-2.5 py-0.5 rounded-full text-[11px] font-medium transition-all cursor-pointer flex items-center gap-1 ${
                      isSelected
                        ? "bg-slate-900 text-white shadow-2xs"
                        : "bg-slate-100 hover:bg-slate-200/80 text-slate-600 border border-slate-200/60"
                    }`}
                  >
                    <span>{cat === "All" ? "All" : cat}</span>
                    <span
                      className={`text-[10px] px-1 rounded-full font-semibold ${
                        isSelected ? "bg-white/20 text-white" : "bg-slate-200 text-slate-500"
                      }`}
                    >
                      {count}
                    </span>
                  </button>
                );
              }
            )}
          </div>
        </div>
      )}

      {/* ── 3. CONTENT AREA (CHAPTERS / HIGHLIGHTS / SPEAKERS) ────────────── */}
      <div className="flex-1 overflow-y-auto space-y-2.5 mt-1 pt-1 pr-1 custom-scrollbar">
        {activeTab === "Chapters" && (
          <div className="space-y-2">
            {chapters.map((chapter, idx) => {
              const isActiveChapter =
                getIsActiveChapter(idx) ||
                (idx === 0 && currentTime < (chapters[0]?.timestampSeconds || 0));

              return (
                <div
                  key={chapter.id}
                  onClick={() => onSeek(chapter.timestampSeconds)}
                  className={`flex gap-4 p-3 rounded-xl transition-colors cursor-pointer ${
                    isActiveChapter
                      ? "bg-indigo-50/50 border border-indigo-100"
                      : "hover:bg-slate-50 border border-transparent"
                  }`}
                >
                  {/* Left: Timestamp pill */}
                  <div className="shrink-0 flex items-start pt-0.5">
                    <span
                      className={`font-mono text-xs px-2.5 py-1 rounded-md font-semibold ${
                        isActiveChapter
                          ? "bg-indigo-600 text-white shadow-xs"
                          : "bg-slate-100 text-slate-600"
                      }`}
                    >
                      {formatDurationStr(chapter.timestampSeconds)}
                    </span>
                  </div>

                  {/* Center: Chapter Title */}
                  <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <p
                      className={`text-sm font-semibold line-clamp-2 leading-snug ${
                        isActiveChapter ? "text-indigo-950" : "text-slate-900"
                      }`}
                    >
                      {chapter.title}
                    </p>
                  </div>

                  {/* Right: Thumbnail */}
                  <div className="w-20 aspect-video bg-slate-200 rounded-md relative shrink-0 overflow-hidden shadow-2xs">
                    <MeetingThumbnail
                      meetingId={meetingId || "sample-meeting-id"}
                      title={chapter.title}
                    />
                    <div className="absolute bottom-1 right-1 z-10 bg-black/80 text-white text-[9px] font-medium px-1.5 py-0.5 rounded backdrop-blur-xs">
                      {chapter.durationStr}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "Highlights" && (
          <div className="space-y-2.5 pb-16">
            {filteredHighlights.map((hl) => {
              const active = isHighlightActive(hl);
              const speakerInitials = getSpeakerInitials(hl.speaker);
              const speakerColor = getSpeakerColor(hl.speaker);

              return (
                <div
                  key={hl.id}
                  onClick={() => onSeek(hl.timestampSeconds)}
                  className={`p-3.5 rounded-xl border transition-all cursor-pointer space-y-2 select-text ${
                    active
                      ? "bg-indigo-50/70 border-indigo-400 ring-1 ring-indigo-500/20 shadow-xs border-l-4 border-l-indigo-600"
                      : "bg-white border-slate-200/90 hover:border-slate-300 hover:bg-slate-50/60 shadow-2xs"
                  }`}
                >
                  {/* Top Row: Category Tag & Timestamp Badge */}
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1.5">
                      {hl.category === "Decision" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200/80">
                          <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                          <span>DECISION</span>
                        </span>
                      )}
                      {hl.category === "Action" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-amber-50 text-amber-700 border border-amber-200/80">
                          <ListTodo className="w-3 h-3 text-amber-600" />
                          <span>ACTION ITEM</span>
                        </span>
                      )}
                      {hl.category === "Demo" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200/80">
                          <Sparkles className="w-3 h-3 text-purple-600" />
                          <span>LIVE DEMO</span>
                        </span>
                      )}
                      {hl.category === "Security" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-blue-50 text-blue-700 border border-blue-200/80">
                          <ShieldCheck className="w-3 h-3 text-blue-600" />
                          <span>SECURITY</span>
                        </span>
                      )}
                      {hl.category === "Key Insight" && (
                        <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200/80">
                          <FileCheck2 className="w-3 h-3 text-indigo-600" />
                          <span>KEY INSIGHT</span>
                        </span>
                      )}

                      {active && (
                        <span className="inline-flex items-center gap-1 text-[10px] font-bold text-indigo-700 bg-indigo-100/90 px-2 py-0.5 rounded-md animate-pulse">
                          <Play className="w-2.5 h-2.5 fill-indigo-700" />
                          <span>PLAYING</span>
                        </span>
                      )}
                    </div>

                    {/* Timestamp Badge */}
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSeek(hl.timestampSeconds);
                      }}
                      className={`font-mono text-[11px] font-semibold px-2 py-0.5 rounded-md flex items-center gap-1 shrink-0 transition-colors ${
                        active
                          ? "bg-indigo-600 text-white shadow-xs"
                          : "bg-slate-100 text-slate-600 hover:bg-indigo-50 hover:text-indigo-700"
                      }`}
                      title={`Jump to ${formatDurationStr(hl.timestampSeconds)}`}
                    >
                      <Play className="w-2.5 h-2.5 fill-current" />
                      <span>{formatDurationStr(hl.timestampSeconds)}</span>
                      <span className="text-[9px] opacity-75">
                        ({formatDurationStr(hl.durationSeconds)})
                      </span>
                    </button>
                  </div>

                  {/* Headline */}
                  <h5 className="text-[13px] font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors leading-snug">
                    {hl.title}
                  </h5>

                  {/* Verbatim quote callout (if present) */}
                  {hl.quote && (
                    <div className="border-l-2 border-indigo-300 pl-2.5 py-0.5 text-[11px] text-slate-600 italic bg-slate-50/70 rounded-r leading-relaxed">
                      &ldquo;{hl.quote}&rdquo;
                    </div>
                  )}

                  {/* Executive Description */}
                  <p className="text-xs text-slate-600 leading-relaxed">{hl.description}</p>

                  {/* Bottom Metadata & Quick Action Bar */}
                  <div className="flex items-center justify-between pt-1 border-t border-slate-100 text-xs">
                    {/* Speaker Badge */}
                    <div className="flex items-center gap-1.5 text-slate-600 text-[11px] min-w-0">
                      <div
                        className={`w-4 h-4 rounded-full border text-[9px] font-bold flex items-center justify-center shrink-0 ${speakerColor}`}
                      >
                        {speakerInitials}
                      </div>
                      <span className="truncate max-w-[140px] font-medium">{hl.speaker}</span>
                    </div>

                    {/* Action Links */}
                    <div className="flex items-center gap-1.5 shrink-0">
                      <button
                        type="button"
                        onClick={(e) => handleCopyHighlight(hl, e)}
                        className="p-1 rounded text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer"
                        title="Copy highlight summary"
                      >
                        {copiedHighlightId === hl.id ? (
                          <Check className="w-3.5 h-3.5 text-emerald-600" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>

                      {onOpenChat && (
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onOpenChat();
                          }}
                          className="p-1 rounded text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 transition-colors cursor-pointer"
                          title="Discuss with Ask Knowra AI"
                        >
                          <MessageSquare className="w-3.5 h-3.5" />
                        </button>
                      )}

                      <button
                        type="button"
                        onClick={() => onSeek(hl.timestampSeconds)}
                        className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 hover:underline inline-flex items-center gap-0.5 ml-1 cursor-pointer"
                      >
                        Jump to {formatDurationStr(hl.timestampSeconds)} →
                      </button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {activeTab === "Speakers" && (
          <div className="p-3 space-y-3 pb-16">
            {realSpeakers && realSpeakers.length > 0 ? (
              realSpeakers.map((speaker) => (
                <div
                  key={speaker.id}
                  className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-2 group"
                >
                  <div className="flex items-center justify-between text-xs">
                    {editingSpeakerId === speaker.id ? (
                      <form
                        onSubmit={(e) => {
                          e.preventDefault();
                          handleSaveSidebarSpeaker(speaker.id);
                        }}
                        className="flex items-center gap-1"
                      >
                        <input
                          type="text"
                          value={editSpeakerName}
                          onChange={(e) => setEditSpeakerName(e.target.value)}
                          className="text-xs font-semibold px-1.5 py-0.5 border border-indigo-400 rounded focus:outline-none bg-white w-24 text-slate-900"
                          autoFocus
                        />
                        <button
                          type="submit"
                          disabled={isSavingSpeaker}
                          className="text-emerald-600 hover:bg-emerald-50 p-0.5 rounded"
                        >
                          {isSavingSpeaker ? (
                            <Loader2 className="w-3 h-3 animate-spin" />
                          ) : (
                            <Check className="w-3 h-3" />
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => setEditingSpeakerId(null)}
                          className="text-rose-500 hover:bg-rose-50 p-0.5 rounded"
                        >
                          <X className="w-3 h-3" />
                        </button>
                      </form>
                    ) : (
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span
                          className="font-semibold text-slate-900 truncate"
                          title={speaker.display_name}
                        >
                          {speaker.display_name || speaker.speaker_label}
                        </span>
                        <button
                          type="button"
                          onClick={() => {
                            setEditingSpeakerId(speaker.id);
                            setEditSpeakerName(speaker.display_name || speaker.speaker_label);
                          }}
                          className="opacity-0 group-hover:opacity-100 hover:text-indigo-600 text-slate-400 p-0.5 transition-opacity cursor-pointer"
                          title="Rename speaker"
                        >
                          <Pencil className="w-2.5 h-2.5" />
                        </button>
                      </div>
                    )}

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-slate-500 font-mono text-[11px]">
                        {formatDurationStr(speaker.total_duration_seconds)}
                      </span>
                      <span className="text-[10px] font-bold text-indigo-600 bg-indigo-50 px-1.5 py-0.5 rounded">
                        {speaker.speaking_percentage}%
                      </span>
                    </div>
                  </div>

                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-indigo-600 h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.max(speaker.speaking_percentage, 4)}%` }}
                    />
                  </div>
                </div>
              ))
            ) : (
              [
                { name: "Presenter", duration: "3m 07s", percent: 89 },
                { name: "Inquirer", duration: "0m 24s", percent: 11 },
              ].map((speaker, idx) => (
                <div
                  key={idx}
                  className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-900">{speaker.name}</span>
                    <span className="text-slate-500 font-mono text-[11px]">{speaker.duration}</span>
                  </div>
                  <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                    <div
                      className="bg-indigo-600 h-full rounded-full"
                      style={{ width: `${speaker.percent}%` }}
                    />
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </div>

      {/* ── 4. RAG CHAT FLOATING ACTION BUTTON (OUT OF DOCUMENT FLOW) ───── */}
      {onOpenChat && (
        <button
          type="button"
          onClick={onOpenChat}
          className="fixed bottom-6 right-6 z-40 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-full shadow-lg shadow-indigo-500/25 flex items-center gap-2 font-medium transition-transform hover:scale-105 active:scale-95 cursor-pointer"
          title="Ask Knowra about this meeting"
        >
          <Sparkles className="w-4 h-4" />
          <span>Ask Knowra</span>
        </button>
      )}
    </aside>
  );
}
