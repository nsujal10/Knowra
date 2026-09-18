"use client";

import React, { useState, useRef, useEffect } from "react";
import { Sparkles } from "lucide-react";
import { Chapter } from "./types";
import { useMeetingMedia } from "@/hooks/useMeetingMedia";
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

const DEFAULT_DEMO_VIDEO =
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";

function formatDurationStr(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

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
      <div className="flex items-center gap-2 pt-5 pb-3">
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

      {/* ── 3. CONTENT AREA (CHAPTERS / HIGHLIGHTS / SPEAKERS) ────────────── */}
      <div className="flex-1 overflow-y-auto space-y-2 mt-1 pr-1 custom-scrollbar">
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
          <div className="p-3 space-y-3">
            <div className="p-3 bg-amber-50/60 border border-amber-200/70 rounded-lg text-xs text-amber-900 space-y-1">
              <div className="font-semibold flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                <span>Search Copilot Demo Highlight</span>
              </div>
              <p className="text-slate-700 leading-relaxed">
                Live demonstration of querying CRM across meetings with verified citations.
              </p>
              <button
                type="button"
                onClick={() => onSeek(363)}
                className="mt-1 text-[11px] font-semibold text-indigo-600 hover:underline cursor-pointer"
              >
                Jump to 6:03 →
              </button>
            </div>
          </div>
        )}

        {activeTab === "Speakers" && (
          <div className="p-3 space-y-3">
            {[
              { name: "Alison Barker", role: "Meeting Host", duration: "5m 24s", percent: 62 },
              { name: "Eliab Sisay", role: "CRM Lead", duration: "1m 45s", percent: 20 },
              { name: "Kelcey Hawthorne", role: "Compliance", duration: "1m 40s", percent: 18 },
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
            ))}
          </div>
        )}
      </div>

      {/* ── 4. RAG CHAT FLOATING ACTION BUTTON (OUT OF DOCUMENT FLOW) ───── */}
      {onOpenChat && (
        <button
          type="button"
          onClick={onOpenChat}
          className="fixed bottom-6 right-6 z-50 bg-indigo-600 hover:bg-indigo-700 text-white px-5 py-3 rounded-full shadow-xl flex items-center gap-2 font-medium transition-transform hover:scale-105 active:scale-95 cursor-pointer"
          title="Ask Knowra about this meeting"
        >
          <Sparkles className="w-4 h-4" />
          <span>Ask Knowra</span>
        </button>
      )}
    </aside>
  );
}
