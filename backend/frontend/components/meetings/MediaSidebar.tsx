"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Play,
  Pause,
  RotateCcw,
  Volume2,
  VolumeX,
  Settings,
  Maximize2,
  Minimize2,
  PictureInPicture2,
  Clock,
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
    <aside className="w-full lg:w-[420px] shrink-0 lg:sticky lg:top-6 lg:h-[calc(100vh-100px)] flex flex-col lg:border-l border-slate-200 lg:pl-6 pb-6 select-none">
      {/* ── 1. STICKY DARK VIDEO PLAYER ───────────────────────────────────── */}
      <div
        ref={playerContainerRef}
        className="w-full bg-[#16181f] rounded-xl overflow-hidden aspect-video relative shadow-md flex flex-col justify-between group border border-slate-800"
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
            onEnded={() => onTogglePlay()}
          />
        ) : (
          <div className="absolute inset-0 bg-gradient-to-br from-slate-900 via-[#1a1c24] to-[#12141a] flex items-center justify-center overflow-hidden">
            {/* Ambient UI Simulation */}
            <div className="relative w-full h-full flex flex-col items-center justify-center p-4">
              <div className="w-24 h-24 rounded-full bg-indigo-600/10 border border-indigo-500/20 flex items-center justify-center filter backdrop-blur-xs">
                <div className="w-16 h-16 rounded-full bg-indigo-600/20 flex items-center justify-center text-white text-2xl font-bold">
                  👩‍💼
                </div>
              </div>
              <div className="text-[11px] text-slate-400 font-medium mt-3 bg-black/40 px-2.5 py-0.5 rounded-full border border-white/5">
                Alison Barker · Presenting Screen
              </div>
            </div>
          </div>
        )}

        {/* Top Overlay: Speaker / Event Dots Bar */}
        <div className="relative z-10 w-full px-3 pt-2.5">
          <div className="relative w-full h-1 bg-white/20 rounded-full cursor-pointer">
            {/* Progress Bar Fill */}
            <div
              className="h-full bg-indigo-500 rounded-full transition-all"
              style={{ width: `${progressPercent}%` }}
            />

            {/* Colored Speaker Event Dots */}
            {timelineMarkers.map((marker, idx) => {
              const leftPercent = (marker.time / duration) * 100;
              return (
                <div
                  key={idx}
                  onClick={(e) => {
                    e.stopPropagation();
                    onSeek(marker.time);
                  }}
                  title={`${marker.label} (${formatDurationStr(marker.time)})`}
                  className={`w-2 h-2 rounded-full absolute top-1/2 -translate-y-1/2 -translate-x-1/2 ${marker.color} ring-1 ring-black shadow-xs cursor-pointer hover:scale-150 transition-transform`}
                  style={{ left: `${leftPercent}%` }}
                />
              );
            })}
          </div>
        </div>

        {/* Center Play/Pause click overlay */}
        <div
          onClick={onTogglePlay}
          className="absolute inset-0 z-0 flex items-center justify-center cursor-pointer"
        />

        {/* Bottom Control Bar */}
        <div className="relative z-10 w-full bg-gradient-to-t from-black/90 via-black/60 to-transparent px-3 pb-2.5 pt-4 flex items-center justify-between text-white text-xs">
          {/* Left Controls: Play, Rewind, Time */}
          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={onTogglePlay}
              className="hover:text-indigo-400 transition-colors cursor-pointer p-0.5"
              title={isPlaying ? "Pause (Space)" : "Play (Space)"}
            >
              {isPlaying ? <Pause className="w-4 h-4 fill-white" /> : <Play className="w-4 h-4 fill-white" />}
            </button>

            <button
              type="button"
              onClick={() => onSeek(Math.max(0, currentTime - 10))}
              className="hover:text-indigo-400 transition-colors cursor-pointer p-0.5"
              title="Rewind 10 seconds"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>

            <span className="font-mono text-[11px] text-slate-300">
              {formatDurationStr(currentTime)} / {formatDurationStr(duration)}
            </span>
          </div>

          {/* Right Controls: Volume, Speed, PIP, Fullscreen */}
          <div className="flex items-center gap-2">
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

      {/* ── 2. PILL-BASED TABS (CHAPTERS, HIGHLIGHTS, SPEAKERS) ────────────── */}
      <div className="flex items-center gap-2 pt-4 pb-2">
        {(["Chapters", "Highlights", "Speakers"] as const).map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all cursor-pointer ${
                isActive
                  ? "border border-indigo-600 text-indigo-700 bg-indigo-50/80 shadow-2xs"
                  : "border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 bg-white"
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>

      {/* ── 3. TAB CONTENT LIST ───────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto space-y-2 mt-2 pr-1 custom-scrollbar">
        {activeTab === "Chapters" && (
          <div className="divide-y divide-slate-100">
            {chapters.map((chapter) => (
              <div
                key={chapter.id}
                onClick={() => onSeek(chapter.timestampSeconds)}
                className="flex items-center justify-between py-3 px-2 rounded-lg hover:bg-slate-50/80 transition-colors cursor-pointer group"
              >
                {/* Left: Timestamp pill + Chapter Title */}
                <div className="flex items-start gap-2.5 min-w-0 pr-3">
                  <span className="mt-0.5 px-2 py-0.5 rounded text-xs font-mono font-medium bg-slate-100 text-slate-600 group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors shrink-0 border border-slate-200/70">
                    {formatDurationStr(chapter.timestampSeconds)}
                  </span>
                  <p className="text-xs font-semibold text-slate-800 line-clamp-2 leading-relaxed group-hover:text-indigo-950 transition-colors">
                    {chapter.title}
                  </p>
                </div>

                {/* Right: Video Thumbnail with duration overlay */}
                <div className="w-16 h-10 rounded-md overflow-hidden relative shrink-0 border border-slate-200 bg-slate-800 shadow-2xs">
                  <div className="w-full h-full bg-gradient-to-br from-stone-700 via-slate-800 to-indigo-950 flex items-center justify-center">
                    <span className="text-xs select-none filter drop-shadow">
                      👩
                    </span>
                  </div>
                  <span className="bg-black/75 text-white text-[9px] font-mono px-1 py-0.5 rounded absolute bottom-0.5 right-0.5 flex items-center gap-0.5">
                    ▶ {chapter.durationStr}
                  </span>
                </div>
              </div>
            ))}
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
                className="mt-1 text-[11px] font-semibold text-indigo-600 hover:underline"
              >
                Jump to 6:03 →
              </button>
            </div>
          </div>
        )}

        {activeTab === "Speakers" && (
          <div className="p-2 space-y-2.5">
            {[
              { name: "Alison Barker", role: "Host / Product Lead", talkTime: "62%" },
              { name: "Kelcey Hawthorne", role: "Solutions Architect", talkTime: "28%" },
              { name: "Eliab Sisay", role: "Enterprise Integrations", talkTime: "10%" }
            ].map((spk, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 bg-white border border-slate-200 rounded-lg text-xs"
              >
                <div className="flex items-center gap-2.5">
                  <div className="w-7 h-7 rounded-full bg-indigo-100 text-indigo-700 font-bold flex items-center justify-center text-[10px]">
                    {spk.name.charAt(0)}
                  </div>
                  <div>
                    <div className="font-semibold text-slate-900">{spk.name}</div>
                    <div className="text-[11px] text-slate-500">{spk.role}</div>
                  </div>
                </div>
                <span className="font-mono text-xs font-semibold text-indigo-600">
                  {spk.talkTime}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}
