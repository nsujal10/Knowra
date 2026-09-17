"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Maximize2,
  Minimize2,
  Sparkles,
  Users
} from "lucide-react";
import { Chapter } from "./types";

interface MediaSidebarProps {
  chapters: Chapter[];
  currentTime: number;
  duration?: number;
  isPlaying: boolean;
  onSeek: (seconds: number) => void;
  onTogglePlay: () => void;
  videoUrl?: string;
}

function formatDurationStr(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

export function MediaSidebar({
  chapters,
  currentTime,
  duration = 529, // default 8:49
  isPlaying,
  onSeek,
  onTogglePlay,
  videoUrl
}: MediaSidebarProps) {
  const [activeTab, setActiveTab] = useState<"Chapters" | "Highlights" | "Speakers">("Chapters");
  const [isMuted, setIsMuted] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState<number>(1);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const playerContainerRef = useRef<HTMLDivElement | null>(null);

  // Sync HTML5 video currentTime when parent onSeek fires
  useEffect(() => {
    if (videoRef.current && Math.abs(videoRef.current.currentTime - currentTime) > 1) {
      videoRef.current.currentTime = currentTime;
    }
  }, [currentTime]);

  // Sync play/pause
  useEffect(() => {
    if (videoRef.current) {
      if (isPlaying && videoRef.current.paused) {
        videoRef.current.play().catch(() => {});
      } else if (!isPlaying && !videoRef.current.paused) {
        videoRef.current.pause();
      }
    }
  }, [isPlaying]);

  const toggleFullscreen = () => {
    if (!playerContainerRef.current) return;
    if (!document.fullscreenElement) {
      playerContainerRef.current.requestFullscreen().catch(() => {});
      setIsFullscreen(true);
    } else {
      document.exitFullscreen().catch(() => {});
      setIsFullscreen(false);
    }
  };

  const progressPercent = Math.min(100, (currentTime / (duration || 1)) * 100);

  // Key marker dots on timeline
  const timelineMarkers = [
    { time: 0, color: "bg-pink-500", label: "Intro" },
    { time: 72, color: "bg-amber-400", label: "Calendar Sync" },
    { time: 160, color: "bg-indigo-400", label: "Settings" },
    { time: 255, color: "bg-emerald-400", label: "CRM Integration" },
    { time: 363, color: "bg-cyan-400", label: "Search Copilot" },
    { time: 450, color: "bg-purple-400", label: "Q&A" }
  ];

  return (
    <aside className="w-full lg:w-[420px] shrink-0 lg:sticky lg:top-6 lg:h-[calc(100vh-80px)] flex flex-col lg:border-l border-slate-200 lg:pl-6 pb-6 select-none">
      {/* ── 1. STICKY DARK VIDEO PLAYER ───────────────────────────────────── */}
      <div
        ref={playerContainerRef}
        className="w-full aspect-video bg-[#11131a] rounded-xl overflow-hidden relative shadow-lg flex flex-col justify-end"
      >
        {/* Actual Video Element or Visual Canvas */}
        {videoUrl ? (
          <video
            ref={videoRef}
            src={videoUrl}
            className="w-full h-full object-cover absolute inset-0"
            onTimeUpdate={() => {
              if (videoRef.current) {
                onSeek(videoRef.current.currentTime);
              }
            }}
          />
        ) : (
          <div className="absolute inset-0 flex flex-col items-center justify-center p-4">
            <div className="w-16 h-16 rounded-full bg-indigo-950/80 border border-indigo-500/30 flex items-center justify-center shadow-inner mb-2">
              <span className="text-2xl select-none filter drop-shadow">👩‍💼</span>
            </div>
            <div className="text-center">
              <p className="text-xs font-semibold text-slate-200 tracking-wide">
                Alison Barker · Presenting Screen
              </p>
            </div>
          </div>
        )}

        {/* Bottom Overlay: Timeline Scrubber + Controls Bar */}
        <div className="relative z-20 w-full bg-gradient-to-t from-black/95 via-black/75 to-transparent px-3 pb-2 pt-5 flex flex-col gap-2">
          {/* Timeline / Scrubber Track (Dots INSIDE the track) */}
          <div
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const clickX = e.clientX - rect.left;
              const ratio = Math.max(0, Math.min(1, clickX / rect.width));
              onSeek(ratio * (duration || 529));
            }}
            className="w-full h-1.5 bg-slate-700/80 rounded-full relative cursor-pointer hover:h-2 transition-all flex items-center"
          >
            {/* Scrubber Progress Fill */}
            <div
              className="h-full bg-indigo-500 rounded-full transition-all"
              style={{ width: `${progressPercent}%` }}
            />

            {/* Diarization Dots directly inside the scrubber track */}
            {timelineMarkers.map((marker, idx) => (
              <div
                key={idx}
                className={`absolute top-1/2 -translate-y-1/2 -translate-x-1/2 w-2 h-2 rounded-full ${marker.color} ring-1 ring-black/70 shadow-xs cursor-pointer hover:scale-150 transition-transform`}
                style={{ left: `${(marker.time / (duration || 529)) * 100}%` }}
                title={`${marker.label} (${formatDurationStr(marker.time)})`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSeek(marker.time);
                }}
              />
            ))}
          </div>

          {/* Controls Bar Row */}
          <div className="w-full flex items-center justify-between text-white text-xs pt-0.5">
            {/* Left Controls: Play/Pause, Rewind, Time */}
            <div className="flex items-center gap-2.5 min-w-0">
              <button
                type="button"
                onClick={onTogglePlay}
                className="hover:text-indigo-400 transition-colors cursor-pointer p-0.5"
                title={isPlaying ? "Pause" : "Play"}
              >
                {isPlaying ? <Pause className="w-3.5 h-3.5 fill-white" /> : <Play className="w-3.5 h-3.5 fill-white" />}
              </button>

              <button
                type="button"
                onClick={() => onSeek(Math.max(0, currentTime - 10))}
                className="hover:text-indigo-400 transition-colors cursor-pointer p-0.5"
                title="Rewind 10 seconds"
              >
                <RotateCcw className="w-3.5 h-3.5" />
              </button>

              <span className="font-mono text-[11px] text-slate-300 shrink-0">
                {formatDurationStr(currentTime)} / {formatDurationStr(duration)}
              </span>

              <span className="text-slate-400 text-xs truncate max-w-[130px] hidden sm:inline">
                • {chapters[0]?.title || "Knowra AI..."}
              </span>
            </div>

            {/* Right Controls: Volume, Speed, Fullscreen */}
            <div className="flex items-center gap-2 shrink-0">
              <button
                type="button"
                onClick={() => setIsMuted(!isMuted)}
                className="hover:text-indigo-400 transition-colors cursor-pointer"
                title={isMuted ? "Unmute" : "Mute"}
              >
                {isMuted ? <VolumeX className="w-3.5 h-3.5 text-slate-400" /> : <Volume2 className="w-3.5 h-3.5" />}
              </button>

              <div className="relative">
                <button
                  type="button"
                  onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                  className="hover:text-indigo-400 text-[11px] font-bold transition-colors cursor-pointer px-1 py-0.5 rounded"
                  title="Playback Speed"
                >
                  {playbackSpeed}x
                </button>

                {showSpeedMenu && (
                  <div className="absolute bottom-6 right-0 bg-[#21232d] border border-slate-700 rounded-md py-1 shadow-lg text-[10px] w-16 z-30">
                    {[0.75, 1, 1.25, 1.5, 2].map((spd) => (
                      <button
                        key={spd}
                        type="button"
                        onClick={() => {
                          setPlaybackSpeed(spd);
                          if (videoRef.current) videoRef.current.playbackRate = spd;
                          setShowSpeedMenu(false);
                        }}
                        className={`w-full py-1 text-center hover:bg-indigo-600/30 ${
                          playbackSpeed === spd ? "text-indigo-400 font-bold" : "text-slate-300"
                        }`}
                      >
                        {spd}x
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <button
                type="button"
                onClick={toggleFullscreen}
                className="hover:text-indigo-400 transition-colors cursor-pointer"
                title="Fullscreen"
              >
                {isFullscreen ? <Minimize2 className="w-3.5 h-3.5" /> : <Maximize2 className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>
        </div>
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
                  ? "border border-indigo-600 text-indigo-700 bg-white shadow-2xs"
                  : "border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 bg-white"
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* ── 3. CHAPTERS LIST (WITH SLEEK THUMBNAIL BADGES) ────────────────── */}
      <div className="flex-1 overflow-y-auto space-y-2 mt-1 pr-1 custom-scrollbar">
        {activeTab === "Chapters" && (
          <div className="space-y-2">
            {chapters.map((chapter, idx) => {
              const isActiveChapter = idx === 0;
              return (
                <div
                  key={chapter.id}
                  onClick={() => onSeek(chapter.timestampSeconds)}
                  className={`flex items-center justify-between p-2.5 rounded-lg transition-colors cursor-pointer group ${
                    isActiveChapter
                      ? "border-l-2 border-indigo-600 bg-slate-50/60 pl-3"
                      : "hover:bg-slate-50/80"
                  }`}
                >
                  {/* Left: Timestamp pill + Chapter Title */}
                  <div className="flex items-start gap-2.5 min-w-0 pr-3">
                    <span
                      className={`font-mono text-[11px] px-2 py-0.5 rounded font-medium shrink-0 ${
                        isActiveChapter
                          ? "bg-indigo-600 text-white"
                          : "bg-slate-100 text-slate-600 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors"
                      }`}
                    >
                      {formatDurationStr(chapter.timestampSeconds)}
                    </span>
                    <p
                      className={`text-sm font-semibold line-clamp-2 leading-relaxed transition-colors ${
                        isActiveChapter
                          ? "text-indigo-700"
                          : "text-slate-800 group-hover:text-indigo-600"
                      }`}
                    >
                      {chapter.title}
                    </p>
                  </div>

                  {/* Right: Thumbnail with sleek absolute duration badge */}
                  <div className="w-24 aspect-video bg-slate-200 rounded-md relative shrink-0 overflow-hidden">
                    <div className="w-full h-full bg-gradient-to-br from-stone-700 via-slate-800 to-indigo-950 flex items-center justify-center">
                      <span className="text-base select-none filter drop-shadow">👩‍💼</span>
                    </div>
                    <div className="absolute bottom-1 right-1 bg-black/80 text-white text-[9px] font-medium px-1.5 py-0.5 rounded backdrop-blur-sm">
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
              { name: "Kelcey Hawthorne", role: "Compliance", duration: "1m 40s", percent: 18 }
            ].map((speaker, idx) => (
              <div key={idx} className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-900">{speaker.name}</span>
                  <span className="text-slate-500 font-mono text-[11px]">{speaker.duration}</span>
                </div>
                <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
                  <div className="bg-indigo-600 h-full rounded-full" style={{ width: `${speaker.percent}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
