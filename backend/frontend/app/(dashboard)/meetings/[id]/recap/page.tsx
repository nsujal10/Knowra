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
  getSegmentTimestamp,
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
  Bookmark,
  Mic,
  LayoutList,
  TrendingUp,
  Smile,
} from "lucide-react";

function TsPill({ seconds }: { seconds: number }) {
  return (
    <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-[var(--primary-muted)] border border-[rgba(59,130,246,0.25)] text-[10px] font-mono font-semibold text-[var(--primary)] shrink-0 tabular-nums">
      {formatDuration(seconds)}
    </span>
  );
}

function VideoPlayer() {
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState<"1x" | "1.25x" | "1.5x">("1x");

  return (
    <div className="relative rounded-[var(--radius-md)] overflow-hidden bg-[#05080e] border border-[var(--border)] aspect-video flex flex-col justify-between p-4 shadow-lg group">
      <div className="flex items-center justify-between z-10">
        <div className="px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md text-[10px] font-mono text-white/80 border border-white/10">
          HD 1080p · AI Sync Active
        </div>
        <button
          onClick={() => {
            const next = speed === "1x" ? "1.25x" : speed === "1.25x" ? "1.5x" : "1x";
            setSpeed(next);
          }}
          className="px-2 py-0.5 rounded bg-black/60 backdrop-blur-md text-[10px] font-bold text-blue-400 hover:text-white border border-white/10 transition-colors cursor-pointer"
        >
          {speed}
        </button>
      </div>

      {/* Play/Pause Center Trigger */}
      <div className="flex items-center justify-center">
        <button
          onClick={() => setPlaying((p) => !p)}
          className="w-14 h-14 rounded-full bg-blue-600/90 hover:bg-blue-600 text-white flex items-center justify-center shadow-glow transition-all hover:scale-105 cursor-pointer"
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? <Pause size={20} /> : <Play size={20} className="ml-1" />}
        </button>
      </div>

      {/* Scrubber & Controls */}
      <div className="space-y-2 z-10">
        <div className="h-1 bg-white/20 rounded-full overflow-hidden cursor-pointer relative">
          <div className="h-full w-1/3 bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full" />
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
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* ── LEFT COLUMN: INTELLIGENCE SUMMARY & ACTIONABLES (2 Cols) ── */}
      <div className="lg:col-span-2 space-y-6">
        {/* Executive Summary Card */}
        <div className="card space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={16} className="text-[var(--primary)]" />
              <h2 className="text-base font-bold text-[var(--foreground)]">
                Executive Intelligence Recap
              </h2>
            </div>
            <span className="text-[11px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
              98% Confidence
            </span>
          </div>

          <div className="text-sm text-[var(--foreground)] leading-relaxed space-y-3 whitespace-pre-line">
            {MOCK_SUMMARY}
          </div>
        </div>

        {/* Action Items & Decisions Preview Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Decisions Preview */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Gavel size={14} className="text-indigo-400" />
                <h3 className="text-xs font-bold text-[var(--foreground)] uppercase tracking-wide">
                  Decisions Reached
                </h3>
              </div>
              <Link
                href={`/meetings/${id}/decisions`}
                className="text-[11px] text-[var(--primary)] hover:underline inline-flex items-center gap-1 font-medium"
              >
                <span>View all ({MOCK_DECISIONS.length})</span>
                <ArrowRight size={11} />
              </Link>
            </div>

            <div className="space-y-2.5">
              {MOCK_DECISIONS.slice(0, 2).map((d) => (
                <div
                  key={d.id}
                  className="p-2.5 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] space-y-1"
                >
                  <div className="flex items-center justify-between text-[11px]">
                    <span className="font-semibold text-[var(--foreground)] truncate pr-2">
                      {d.title}
                    </span>
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold uppercase bg-emerald-500/15 text-emerald-400">
                      Approved
                    </span>
                  </div>
                  <p className="text-[11px] text-[var(--muted-strong)] line-clamp-2">
                    {d.summary}
                  </p>
                </div>
              ))}
            </div>
          </div>

          {/* Action Items Preview */}
          <div className="card space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <CheckCircle2 size={14} className="text-emerald-400" />
                <h3 className="text-xs font-bold text-[var(--foreground)] uppercase tracking-wide">
                  Action Items
                </h3>
              </div>
              <Link
                href={`/meetings/${id}/actions`}
                className="text-[11px] text-[var(--primary)] hover:underline inline-flex items-center gap-1 font-medium"
              >
                <span>View all ({MOCK_ACTION_ITEMS.length})</span>
                <ArrowRight size={11} />
              </Link>
            </div>

            <div className="space-y-2.5">
              {MOCK_ACTION_ITEMS.slice(0, 2).map((a) => (
                <div
                  key={a.id}
                  className="p-2.5 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] space-y-1"
                >
                  <p className="text-[11px] font-medium text-[var(--foreground)] line-clamp-2">
                    {a.title}
                  </p>
                  <div className="flex items-center justify-between text-[10px] text-[var(--muted)]">
                    <span>Owner: {a.assignee ?? "Team"}</span>
                    <span className="px-1.5 py-0.2 rounded font-bold uppercase bg-amber-500/15 text-amber-400">
                      {a.status}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Read AI Meeting Sentiment & Engagement Scorecard */}
        <div className="card p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <TrendingUp size={16} className="text-emerald-400" />
              <h3 className="text-xs font-bold text-[var(--foreground)] uppercase tracking-wide">
                Meeting Dynamics & Engagement Pulse
              </h3>
            </div>
            <span className="text-[11px] font-medium text-emerald-400 flex items-center gap-1">
              <Smile size={13} />
              Overall Sentiment: High Positive (91%)
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)]">
              <span className="text-[10px] font-medium text-[var(--muted)] uppercase">Engagement</span>
              <p className="text-xl font-bold text-[var(--foreground)] mt-1">94%</p>
              <span className="text-[9px] text-emerald-400 font-semibold">+8% above benchmark</span>
            </div>
            <div className="p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)]">
              <span className="text-[10px] font-medium text-[var(--muted)] uppercase">Clarity Score</span>
              <p className="text-xl font-bold text-[var(--foreground)] mt-1">8.9/10</p>
              <span className="text-[9px] text-blue-400 font-semibold">Zero ambiguous topics</span>
            </div>
            <div className="p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)]">
              <span className="text-[10px] font-medium text-[var(--muted)] uppercase">Pace / Cadence</span>
              <p className="text-xl font-bold text-[var(--foreground)] mt-1">142 wpm</p>
              <span className="text-[9px] text-purple-400 font-semibold">Ideal conversational rhythm</span>
            </div>
          </div>
        </div>
      </div>

      {/* ── RIGHT COLUMN: MEDIA PLAYER, CHAPTERS & SPEAKERS (1 Col) ── */}
      <div className="space-y-4">
        <VideoPlayer />

        {/* Side Panel Tabs (Chapters, Speakers) */}
        <div className="rounded-[var(--radius-md)] border border-[var(--border)] bg-[var(--surface-1)] overflow-hidden shadow-sm">
          <div className="flex border-b border-[var(--border)]">
            <button
              onClick={() => setRightTab("chapters")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-all cursor-pointer",
                rightTab === "chapters"
                  ? "text-[var(--primary)] bg-[var(--primary-muted)] border-b-2 border-[var(--primary)] font-semibold"
                  : "text-[var(--muted-strong)] hover:text-[var(--foreground)] hover:bg-[var(--surface-2)]"
              )}
            >
              <LayoutList size={13} />
              <span>Chapters ({MOCK_CHAPTERS.length})</span>
            </button>
            <button
              onClick={() => setRightTab("speakers")}
              className={cn(
                "flex-1 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium transition-all cursor-pointer",
                rightTab === "speakers"
                  ? "text-[var(--primary)] bg-[var(--primary-muted)] border-b-2 border-[var(--primary)] font-semibold"
                  : "text-[var(--muted-strong)] hover:text-[var(--foreground)] hover:bg-[var(--surface-2)]"
              )}
            >
              <Mic size={13} />
              <span>Speakers ({MOCK_SPEAKERS.length})</span>
            </button>
          </div>

          <div className="max-h-[380px] overflow-y-auto scrollable divide-y divide-[var(--border)]">
            {rightTab === "chapters" &&
              MOCK_CHAPTERS.map((ch) => (
                <div
                  key={ch.id}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[var(--surface-2)] transition-colors text-left group cursor-pointer"
                >
                  <span className="text-base shrink-0">{ch.emoji}</span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors truncate">
                      {ch.title}
                    </p>
                    <span className="text-[10px] text-[var(--muted)]">Interactive Segment</span>
                  </div>
                  <TsPill seconds={ch.start_time} />
                </div>
              ))}

            {rightTab === "speakers" &&
              MOCK_SPEAKERS.map((sp) => (
                <div key={sp.id} className="flex items-center gap-3 px-4 py-3">
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0"
                    style={{ background: speakerColor(sp.label) }}
                  >
                    {sp.initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium text-[var(--foreground)] truncate">
                      {sp.displayName}
                    </p>
                    <div className="mt-1.5 h-1.5 bg-[var(--surface-3)] rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${(sp.talkTime / 145) * 100}%`,
                          background: speakerColor(sp.label),
                        }}
                      />
                    </div>
                  </div>
                  <span className="text-xs text-[var(--muted-strong)] font-mono shrink-0">
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
