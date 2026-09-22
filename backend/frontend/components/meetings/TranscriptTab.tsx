"use client";

import React, { useState, useMemo } from "react";
import {
  Sparkles,
  Loader2,
  AlertCircle,
  Search,
  Copy,
  Check,
  RefreshCw,
  FileText,
  Pencil,
  X,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { useRealTranscript, TranscriptSegment } from "@/hooks/useRealTranscript";

interface TranscriptTabProps {
  meetingId: string;
  onTimeClick?: (seconds: number) => void;
  activeTimestamp?: number;
}

function formatSeconds(seconds: number): string {
  const totalSeconds = Math.max(0, Math.floor(seconds));
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

function highlightMatch(text?: string, query?: string): React.ReactNode {
  if (!text) return "";
  if (!query || !query.trim()) return text;

  const trimmed = query.trim();
  const escaped = trimmed.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escaped})`, "gi");
  const parts = text.split(regex);

  return parts.map((part, i) => {
    if (part.toLowerCase() === trimmed.toLowerCase()) {
      return (
        <mark
          key={i}
          className="bg-[#FDE047] text-slate-900 font-medium px-0.5 rounded-[2px]"
        >
          {part}
        </mark>
      );
    }
    return part;
  });
}

export function TranscriptTab({
  meetingId,
  onTimeClick,
  activeTimestamp = 0,
}: TranscriptTabProps) {
  const {
    transcript,
    status,
    segments,
    isGenerating,
    error,
    generateTranscript,
    refetch,
  } = useRealTranscript(meetingId);

  const [searchQuery, setSearchQuery] = useState("");
  const [matchIndex, setMatchIndex] = useState(0);
  const [copied, setCopied] = useState(false);
  const [editingSpeakerId, setEditingSpeakerId] = useState<string | null>(null);
  const [editSpeakerName, setEditSpeakerName] = useState("");
  const [isSavingSpeaker, setIsSavingSpeaker] = useState(false);
  const queryClient = useQueryClient();

  const handleSaveSpeakerName = async (speakerId: string) => {
    if (!editSpeakerName.trim()) return;
    try {
      setIsSavingSpeaker(true);
      await api.patch(`/speakers/${speakerId}`, {
        display_name: editSpeakerName.trim(),
      });
      await queryClient.invalidateQueries({ queryKey: ["meeting-transcript", meetingId] });
      await queryClient.invalidateQueries({ queryKey: ["meeting-speakers", meetingId] });
      setEditingSpeakerId(null);
    } catch (err) {
      console.error("Failed to update speaker name:", err);
    } finally {
      setIsSavingSpeaker(false);
    }
  };

  // Filter real segments by search query (speaker name or text)
  const filteredSegments = useMemo(() => {
    if (!searchQuery.trim()) return segments;
    const q = searchQuery.toLowerCase();
    return segments.filter(
      (seg) =>
        seg.text.toLowerCase().includes(q) ||
        seg.speaker.label.toLowerCase().includes(q) ||
        (seg.speaker.displayName && seg.speaker.displayName.toLowerCase().includes(q))
    );
  }, [segments, searchQuery]);

  const totalMatches = searchQuery.trim() ? filteredSegments.length : 0;

  const handlePrevMatch = () => {
    if (totalMatches === 0) return;
    setMatchIndex((prev) => (prev - 1 + totalMatches) % totalMatches);
  };

  const handleNextMatch = () => {
    if (totalMatches === 0) return;
    setMatchIndex((prev) => (prev + 1) % totalMatches);
  };

  const handleClearSearch = () => {
    setSearchQuery("");
    setMatchIndex(0);
  };

  const handleCopyTranscript = () => {
    const text = segments
      .map(
        (s) =>
          `[${formatSeconds(s.start)}] ${s.speaker.displayName || s.speaker.label}: ${s.text}`
      )
      .join("\n\n");
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // ── 1. UNPROCESSED STATE (NO TRANSCRIPT GENERATED YET) ──────────────────────
  if (status === "UNPROCESSED") {
    return (
      <div className="w-full py-8">
        <div className="border border-slate-200 bg-slate-50/50 rounded-xl p-12 flex flex-col items-center justify-center text-center max-w-2xl mx-auto shadow-xs">
          <div className="w-12 h-12 rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center mb-4 text-indigo-600">
            <FileText className="w-6 h-6 stroke-[1.8]" />
          </div>

          <h2 className="text-lg font-semibold text-slate-900 tracking-tight">
            Canonical Speaker-Diarized Transcript
          </h2>

          <p className="text-xs text-slate-500 mt-2 max-w-md leading-relaxed">
            Extract speech, identify unique speakers, and align words with timecodes directly from the uploaded meeting recording.
          </p>

          <button
            type="button"
            onClick={() => generateTranscript()}
            disabled={isGenerating}
            className="mt-6 px-5 py-2.5 rounded-lg text-sm font-semibold bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white shadow-xs flex items-center gap-2 transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {isGenerating ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Queuing Pipeline...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-indigo-200" />
                <span>Generate Transcript from Video</span>
              </>
            )}
          </button>
        </div>
      </div>
    );
  }

  // ── 2. PROCESSING STATE (ENTERPRISE LOADER & SKELETON) ──────────────────────
  if (status === "PROCESSING") {
    return (
      <div className="w-full py-8 space-y-6">
        <div className="border border-slate-200 bg-white rounded-xl p-10 flex flex-col items-center justify-center text-center max-w-2xl mx-auto shadow-xs">
          <div className="relative w-14 h-14 flex items-center justify-center mb-4">
            <div className="absolute inset-0 rounded-full border-4 border-indigo-100 animate-pulse" />
            <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          </div>

          <h2 className="text-lg font-semibold text-slate-900 tracking-tight">
            Extracting Audio & Running Diarization
          </h2>

          <p className="text-xs text-slate-600 mt-2 max-w-md leading-relaxed">
            Extracting audio and running speaker diarization... This may take a few minutes depending on the meeting length.
          </p>

          <div className="w-64 bg-slate-100 h-1.5 rounded-full overflow-hidden mt-6">
            <div className="bg-indigo-600 h-full rounded-full w-3/4 animate-[pulse_1.5s_ease-in-out_infinite]" />
          </div>
        </div>

        {/* Pulsing Skeleton Placeholder Lines */}
        <div className="max-w-3xl mx-auto space-y-3 pt-2">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="flex items-start gap-4 p-3 bg-slate-50/60 rounded-lg animate-pulse"
            >
              <div className="w-12 h-6 bg-slate-200 rounded shrink-0" />
              <div className="w-24 h-6 bg-slate-200 rounded shrink-0" />
              <div className="flex-1 space-y-2 py-1">
                <div className="h-3 bg-slate-200 rounded w-full" />
                <div className="h-3 bg-slate-200 rounded w-4/5" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // ── 3. FAILED ERROR STATE ──────────────────────────────────────────────────
  if (status === "FAILED") {
    return (
      <div className="w-full py-8">
        <div className="border border-red-200 bg-red-50 text-red-700 rounded-xl p-8 flex flex-col items-center justify-center text-center max-w-2xl mx-auto shadow-xs">
          <div className="w-12 h-12 rounded-full bg-red-100 text-red-600 flex items-center justify-center mb-3">
            <AlertCircle className="w-6 h-6" />
          </div>

          <h2 className="text-base font-semibold text-red-900 tracking-tight">
            Transcription Pipeline Failed
          </h2>

          <p className="text-xs text-red-700 mt-1.5 max-w-md leading-relaxed">
            {error instanceof Error
              ? error.message
              : "An error occurred while decoding audio or processing speaker diarization. Please ensure the video has an audio track and retry."}
          </p>

          <button
            type="button"
            onClick={() => generateTranscript()}
            disabled={isGenerating}
            className="mt-5 px-4 py-2 text-xs font-semibold bg-red-600 hover:bg-red-700 active:bg-red-800 text-white rounded-lg shadow-xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-60"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Retry Transcription</span>
          </button>
        </div>
      </div>
    );
  }

  // ── 4. READY STATE (REAL SPEAKER-DIARIZED SEGMENTS) ─────────────────────────
  return (
    <div className="w-full pb-16">
      {/* Search & Actions Header */}
      <div className="flex items-center justify-between gap-4 pt-4 mb-6">
        {/* Search Transcript Input Widget */}
        <div
          className={`relative flex items-center bg-white rounded-xl px-3 py-1.5 transition-all w-full max-w-sm border-2 ${
            searchQuery.trim()
              ? "border-indigo-600 ring-2 ring-indigo-500/15 shadow-xs"
              : "border-indigo-500/80 hover:border-indigo-600 focus-within:border-indigo-600 focus-within:ring-2 focus-within:ring-indigo-500/15 shadow-2xs"
          }`}
        >
          <Search className="w-4 h-4 text-slate-500 shrink-0 mr-2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => {
              setSearchQuery(e.target.value);
              setMatchIndex(0);
            }}
            placeholder="Search transcript & speakers..."
            style={{ outline: "none", boxShadow: "none" }}
            className="w-full text-xs sm:text-[13px] text-slate-900 placeholder:text-slate-400 bg-transparent border-none outline-none focus:outline-none focus-visible:outline-none ring-0 focus:ring-0 focus-visible:ring-0 p-0 font-normal shadow-none"
          />

          {/* Vertical Divider */}
          <div className="h-4 w-px bg-slate-200 mx-2.5 shrink-0" />

          {/* Match Navigation & Counter */}
          <div className="flex items-center gap-1 shrink-0 select-none">
            <button
              type="button"
              onClick={handlePrevMatch}
              disabled={totalMatches === 0}
              style={{ outline: "none" }}
              className="text-slate-400 hover:text-slate-700 disabled:opacity-30 disabled:cursor-not-allowed p-0.5 rounded cursor-pointer transition-colors focus:outline-none focus-visible:outline-none"
              title="Previous match"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>
            <span className="text-xs text-slate-600 font-sans tracking-tight min-w-[36px] text-center">
              {totalMatches > 0 ? `${matchIndex + 1} of ${totalMatches}` : "0 of 0"}
            </span>
            <button
              type="button"
              onClick={handleNextMatch}
              disabled={totalMatches === 0}
              style={{ outline: "none" }}
              className="text-slate-400 hover:text-slate-700 disabled:opacity-30 disabled:cursor-not-allowed p-0.5 rounded cursor-pointer transition-colors focus:outline-none focus-visible:outline-none"
              title="Next match"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Vertical Divider */}
          <div className="h-4 w-px bg-slate-200 mx-2.5 shrink-0" />

          {/* Clear Search X Button */}
          <button
            type="button"
            onClick={handleClearSearch}
            style={{ outline: "none" }}
            className="text-slate-400 hover:text-slate-700 p-0.5 rounded cursor-pointer shrink-0 transition-colors focus:outline-none focus-visible:outline-none"
            title="Clear search"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleCopyTranscript}
            className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Copy entire transcript to clipboard"
          >
            {copied ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-600" />
                <span className="text-emerald-600 font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Copy className="w-3.5 h-3.5 text-slate-500" />
                <span>Copy Transcript</span>
              </>
            )}
          </button>

          {transcript?.transcriptId === "live-transcript" && (
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-600 text-[11px] font-semibold animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
              <span>LIVE FEED</span>
            </div>
          )}

          <button
            type="button"
            onClick={() => refetch()}
            className="p-1.5 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs transition-colors cursor-pointer"
            title="Refresh transcript"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Real Segments List */}
      <div className="space-y-1">
        {filteredSegments.length === 0 ? (
          <div className="py-12 text-center text-slate-400 text-sm bg-slate-50/50 rounded-xl border border-dashed border-slate-200">
            {segments.length === 0
              ? "Transcript is ready, but no spoken segments were detected in the audio track."
              : "No matching transcript segments found."}
          </div>
        ) : (
          filteredSegments.map((segment: TranscriptSegment) => {
            const isCurrent =
              activeTimestamp >= segment.start && activeTimestamp < segment.end;

            return (
              <div
                key={segment.id}
                className={`flex items-start gap-4 py-3 px-2 rounded-lg transition-colors group ${
                  isCurrent
                    ? "bg-indigo-50/70 border-l-2 border-indigo-600 pl-3"
                    : "hover:bg-slate-50"
                }`}
              >
                {/* Left Column (Metadata): Clickable Timestamp Pill + Speaker Label */}
                <div className="flex items-center shrink-0 min-w-[240px]">
                  <button
                    type="button"
                    onClick={() => onTimeClick?.(segment.start)}
                    className="bg-slate-100 hover:bg-indigo-50 text-slate-600 hover:text-indigo-600 font-mono text-xs px-2 py-1 rounded cursor-pointer transition-colors shrink-0"
                    title={`Seek video to ${formatSeconds(segment.start)}`}
                  >
                    {formatSeconds(segment.start)}
                  </button>

                  {editingSpeakerId === segment.speaker.id ? (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        handleSaveSpeakerName(segment.speaker.id);
                      }}
                      className="flex items-center gap-1 ml-2 shrink-0 z-10"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        type="text"
                        value={editSpeakerName}
                        onChange={(e) => setEditSpeakerName(e.target.value)}
                        className="text-xs font-semibold px-2 py-0.5 border border-indigo-400 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500 bg-white w-36 text-slate-900 shadow-2xs"
                        autoFocus
                      />
                      <button
                        type="submit"
                        disabled={isSavingSpeaker}
                        className="p-1 hover:bg-emerald-50 text-emerald-600 rounded transition-colors"
                        title="Save name"
                      >
                        {isSavingSpeaker ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        ) : (
                          <Check className="w-3.5 h-3.5" />
                        )}
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingSpeakerId(null)}
                        className="p-1 hover:bg-rose-50 text-rose-500 rounded transition-colors"
                        title="Cancel"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </form>
                  ) : (
                    <div className="flex items-center gap-1.5 ml-3 group/speaker">
                      <span
                        className="text-sm font-semibold text-slate-900 truncate max-w-[170px]"
                        title={segment.speaker.displayName || segment.speaker.label}
                      >
                        {highlightMatch(
                          segment.speaker.displayName || segment.speaker.label,
                          searchQuery
                        )}
                      </span>
                      {segment.speaker.id && segment.speaker.id !== "unknown" && (
                        <button
                          type="button"
                          onClick={() => {
                            setEditingSpeakerId(segment.speaker.id);
                            setEditSpeakerName(
                              segment.speaker.displayName || segment.speaker.label
                            );
                          }}
                          className="opacity-0 group-hover/speaker:opacity-100 hover:text-indigo-600 text-slate-400 p-0.5 rounded transition-all cursor-pointer"
                          title="Click to rename speaker"
                        >
                          <Pencil className="w-3 h-3" />
                        </button>
                      )}
                    </div>
                  )}
                </div>

                {/* Right Column (Content): Spoken Text */}
                <div className="text-sm text-slate-700 leading-relaxed flex-1 pt-0.5">
                  {highlightMatch(segment.text, searchQuery)}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
