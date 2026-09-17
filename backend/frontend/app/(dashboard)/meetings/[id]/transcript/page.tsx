"use client";

import React, { useState } from "react";
import { formatDuration, speakerColor } from "@/lib/utils";
import {
  MOCK_TRANSCRIPT,
  MOCK_SPEAKERS,
} from "@/lib/data/mock";
import {
  Search,
  Copy,
  Bookmark,
  Check,
} from "lucide-react";

export default function MeetingTranscriptPage() {
  const [search, setSearch] = useState("");
  const [selectedSpeaker, setSelectedSpeaker] = useState<string>("ALL");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredSegments = MOCK_TRANSCRIPT.segments.filter((seg) => {
    const matchesSearch =
      !search || seg.text.toLowerCase().includes(search.toLowerCase());
    const matchesSpeaker =
      selectedSpeaker === "ALL" ||
      seg.speaker_label === selectedSpeaker ||
      seg.speaker_name === selectedSpeaker;
    return matchesSearch && matchesSpeaker;
  });

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="card p-3 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
          <input
            type="text"
            placeholder="Search within transcript…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-8 pl-9 pr-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] text-xs text-[var(--foreground)] placeholder-[var(--muted)] outline-none focus:border-[var(--primary)] transition-all"
          />
        </div>

        {/* Speaker Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          <button
            onClick={() => setSelectedSpeaker("ALL")}
            className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
              selectedSpeaker === "ALL"
                ? "bg-[var(--primary)] text-white"
                : "bg-[var(--surface-2)] text-[var(--muted-strong)] hover:text-[var(--foreground)]"
            }`}
          >
            All Speakers
          </button>
          {MOCK_SPEAKERS.map((sp) => (
            <button
              key={sp.id}
              onClick={() => setSelectedSpeaker(sp.label)}
              className={`px-2.5 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
                selectedSpeaker === sp.label
                  ? "bg-[var(--primary)] text-white"
                  : "bg-[var(--surface-2)] text-[var(--muted-strong)] hover:text-[var(--foreground)]"
              }`}
            >
              {sp.displayName}
            </button>
          ))}
        </div>
      </div>

      {/* Transcript List */}
      <div className="card divide-y divide-[var(--border)] p-0 overflow-hidden">
        {filteredSegments.length === 0 ? (
          <div className="py-12 text-center text-xs text-[var(--muted)]">
            No matching transcript segments found.
          </div>
        ) : (
          filteredSegments.map((seg) => {
            const speakerInfo =
              MOCK_SPEAKERS.find((s) => s.label === seg.speaker_label) ?? {
                displayName: seg.speaker_name ?? "Speaker",
                initials: seg.speaker_name?.[0] ?? "S",
                label: seg.speaker_label ?? "SPEAKER_00",
              };

            return (
              <div
                key={seg.id}
                className="p-4 hover:bg-[var(--surface-2)] transition-colors flex items-start gap-4 group"
              >
                {/* Speaker Avatar */}
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5"
                  style={{ background: speakerColor(speakerInfo.label) }}
                >
                  {speakerInfo.initials}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2.5">
                    <span className="text-xs font-bold text-[var(--foreground)]">
                      {speakerInfo.displayName}
                    </span>
                    <button className="px-1.5 py-0.2 rounded bg-[var(--primary-muted)] text-[10px] font-mono font-semibold text-[var(--primary)] hover:bg-[var(--primary)] hover:text-white transition-all cursor-pointer">
                      {formatDuration(seg.start_time)}
                    </button>
                  </div>
                  <p className="text-xs text-[var(--foreground)] leading-relaxed">
                    {seg.text}
                  </p>
                </div>

                {/* Actions */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => handleCopy(seg.id, seg.text)}
                    title="Copy transcript segment"
                    className="p-1.5 rounded hover:bg-[var(--surface-3)] text-[var(--muted-strong)] hover:text-[var(--foreground)] transition-colors cursor-pointer"
                  >
                    {copiedId === seg.id ? (
                      <Check size={13} className="text-emerald-400" />
                    ) : (
                      <Copy size={13} />
                    )}
                  </button>
                  <button
                    title="Bookmark segment"
                    className="p-1.5 rounded hover:bg-[var(--surface-3)] text-[var(--muted-strong)] hover:text-[var(--foreground)] transition-colors cursor-pointer"
                  >
                    <Bookmark size={13} />
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
