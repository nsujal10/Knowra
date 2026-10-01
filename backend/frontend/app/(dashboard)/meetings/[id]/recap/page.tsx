"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn, formatDuration, speakerColor } from "@/lib/utils";
import {
  MOCK_SUMMARY,
  MOCK_ACTION_ITEMS,
  MOCK_DECISIONS,
  MOCK_CHAPTERS,
  MOCK_SPEAKERS,
} from "@/lib/data/mock";
import {
  Play,
  Pause,
  Volume2,
  Maximize2,
  CheckCircle2,
  Gavel,
  Sparkles,
  ArrowRight,
  Mic,
  LayoutList,
  TrendingUp,
  Smile,
} from "lucide-react";

function TsPill({ seconds }: { seconds: number }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-indigo-50 border border-indigo-100 text-[10px] font-mono font-semibold text-indigo-700 shrink-0 tabular-nums">
      {formatDuration(seconds)}
    </span>
  );
}

function VideoPlayer() {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<"1x" | "1.25x" | "1.5x">("1x");

  return (
    <div className="relative rounded-xl overflow-hidden bg-slate-950 border border-slate-800 aspect-video flex flex-col justify-between p-4 shadow-md group">
      <div className="flex items-center justify-between z-10">
        <div className="px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-[10px] font-mono text-white/80 border border-white/10">
          HD 1080p · AI Sync Active
        </div>
        <button
          onClick={() => {
            const next = speed === "1x" ? "1.25x" : speed === "1.25x" ? "1.5x" : "1x";
            setSpeed(next);
          }}
          className="px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-[10px] font-bold text-indigo-400 hover:text-white border border-white/10 transition-colors cursor-pointer"
        >
          {speed}
        </button>
      </div>

      {/* Play/Pause Center Trigger */}
      <div className="flex items-center justify-center">
        <button
          onClick={() => setPlaying((p) => !p)}
          className="w-13 h-13 rounded-full bg-indigo-600/90 hover:bg-indigo-600 text-white flex items-center justify-center shadow-lg transition-all hover:scale-105 cursor-pointer"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
        </button>
      </div>

      {/* Scrubber & Controls */}
      <div className="space-y-2 z-10">
        <div className="h-1 bg-white/20 rounded-full overflow-hidden cursor-pointer relative">
          <div className="h-full w-1/3 bg-indigo-500 rounded-full" />
        </div>
        <div className="flex items-center justify-between text-[10px] text-white/70 font-mono">
          <span>03:14</span>
          <div className="flex items-center gap-3">
            <Volume2 size={13} className="hover:text-white cursor-pointer" />
            <Maximize2 size={13} className="hover:text-white cursor-pointer" />
            <span>1:02:00</span>
          </div>
        </div>
      </div>
    </div>
  );
}

type RightTab = "chapters" | "speakers";

export default function MeetingRecapPage() {
  const params = useParams();
  const id = (params?.id as string) ?? "m-001";
  const [rightTab, setRightTab] = useState<RightTab>("chapters");

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
      {/* ── LEFT COLUMN: INTELLIGENCE SUMMARY & ACTIONABLES (2 Cols) ── */}
      <div className="lg:col-span-2 space-y-5">
        {/* Executive Summary Card */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-indigo-600" />
              <h2 className="text-sm font-bold text-slate-900">
                Executive Intelligence Recap
              </h2>
            </div>
            <span className="text-[11px] font-mono text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-full border border-emerald-200 font-semibold">
              98% Confidence
            </span>
          </div>

          <div className="text-xs sm:text-sm text-slate-700 leading-relaxed space-y-2.5 whitespace-pre-line">
            {MOCK_SUMMARY}
          </div>
        </div>

        {/* Action Items & Decisions Preview Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Decisions Preview */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Gavel size={14} className="text-indigo-600" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                  Decisions Reached
                </h3>
              </div>
              <Link
                href={`/meetings/${id}/decisions`}
                className="text-[11px] text-indigo-600 hover:text-indigo-700 hover:underline inline-flex items-center gap-1 font-semibold"
              >
                <span>View all ({MOCK_DECISIONS.length})</span>
                <ArrowRight size={11} />
              </Link>
            </div>

            <div className="space-y-2">
              {MOCK_DECISIONS.slice(0, 2).map((d) => (
                <div
                  key={d.id}
                  className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-slate-900 truncate pr-2">
                      {d.title}
                    </span>
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Approved
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-600 line-clamp-2">
                    {d.summary}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Action Items Preview */}
          <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-600" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                  Action Items
                </h3>
              </div>
              <Link
                href={`/meetings/${id}/actions`}
                className="text-[11px] text-indigo-600 hover:text-indigo-700 hover:underline inline-flex items-center gap-1 font-semibold"
              >
                <span>View all ({MOCK_ACTION_ITEMS.length})</span>
                <ArrowRight size={11} />
              </Link>
            </div>

            <div className="space-y-2">
              {MOCK_ACTION_ITEMS.slice(0, 2).map((a) => (
                <div
                  key={a.id}
                  className="p-3 rounded-lg bg-slate-50 border border-slate-200/80 space-y-1"
                >
                  <p className="text-xs font-semibold text-slate-900 line-clamp-2">
                    {a.title}
                  </p>
                  <div className="flex items-center justify-between text-[11px] text-slate-500">
                    <span>Owner: {a.assignee ?? "Team"}</span>
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-amber-50 text-amber-700 border border-amber-200">
                      {a.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Meeting Dynamics & Engagement Pulse */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-emerald-600" />
              <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wide">
                Meeting Dynamics & Engagement Pulse
              </h3>
            </div>
            <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
              <Smile size={13} />
              Overall Sentiment: Positive (91%)
            </span>
          </div>

          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
              <span className="text-[10px] font-semibold text-slate-500 uppercase">Engagement</span>
              <p className="text-xl font-bold text-slate-900 mt-1">94%</p>
              <span className="text-[10px] text-emerald-600 font-semibold">+8% benchmark</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
              <span className="text-[10px] font-semibold text-slate-500 uppercase">Clarity Score</span>
              <p className="text-xl font-bold text-slate-900 mt-1">8.9/10</p>
              <span className="text-[10px] text-indigo-600 font-semibold">High precision</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-50 border border-slate-200/80">
              <span className="text-[10px] font-semibold text-slate-500 uppercase">Pace / Cadence</span>
              <p className="text-xl font-bold text-slate-900 mt-1">142 wpm</p>
              <span className="text-[10px] text-slate-600 font-semibold">Balanced rhythm</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── RIGHT COLUMN: MEDIA PLAYER, CHAPTERS & SPEAKERS (1 Col) ── */}
      <div className="space-y-4">
        <VideoPlayer />

        {/* Side Panel Tabs (Chapters, Speakers) */}
        <div className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-xs">
          <div className="flex border-b border-slate-100 bg-slate-50/50 p-1">
            <button
              onClick={() => setRightTab("chapters")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer",
                rightTab === "chapters"
                  ? "bg-white text-indigo-700 shadow-2xs"
                  : "text-slate-500 hover:text-slate-800"
              )}
            >
              <LayoutList size={13} />
              <span>Chapters ({MOCK_CHAPTERS.length})</span>
            </button>
            <button
              onClick={() => setRightTab("speakers")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-1.5 text-xs font-semibold rounded-lg transition-all cursor-pointer",
                rightTab === "speakers"
                  ? "bg-white text-indigo-700 shadow-2xs"
                  : "text-slate-500 hover:text-slate-800"
              )}
            >
              <Mic size={13} />
              <span>Speakers ({MOCK_SPEAKERS.length})</span>
            </button>
          </div>

          <div className="max-h-[380px] overflow-y-auto divide-y divide-slate-100">
            {rightTab === "chapters" &&
              MOCK_CHAPTERS.map((ch) => (
                <div
                  key={ch.id}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-slate-50/80 transition-colors text-left group cursor-pointer"
                >
                  <span className="text-base shrink-0">{ch.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-800 group-hover:text-indigo-600 transition-colors truncate">
                      {ch.title}
                    </p>
                    <span className="text-[10px] text-slate-400">Interactive Segment</span>
                  </div>
                  <TsPill seconds={ch.start_time} />
                </div>
              ))}

            {rightTab === "speakers" &&
              MOCK_SPEAKERS.map((sp) => (
                <div key={sp.id} className="flex items-center gap-3 px-4 py-3">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 shadow-2xs"
                    style={{ background: speakerColor(sp.label) }}
                  >
                    {sp.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-semibold text-slate-900 truncate">
                      {sp.displayName}
                    </p>
                    <div className="mt-1.5 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${(sp.talkTime / 145) * 100}%`,
                          background: speakerColor(sp.label),
                        }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-slate-500 font-mono shrink-0">
                    {formatDuration(sp.talkTime)}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  );
}
