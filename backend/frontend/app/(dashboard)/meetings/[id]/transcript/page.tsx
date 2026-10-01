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
  X,
} from "lucide-react";
import { toast } from "@/components/ui/toast";

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
    toast.success("Transcript segment copied to clipboard");
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="bg-white rounded-xl border border-slate-200 p-3 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search within transcript…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-8 pl-9 pr-8 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder:text-slate-400 outline-none focus:border-indigo-500 focus:bg-white transition-all"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 cursor-pointer"
            >
              <X size={13} />
            </button>
          )}
        </div>

        {/* Speaker Filters */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          <button
            onClick={() => setSelectedSpeaker("ALL")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
              selectedSpeaker === "ALL"
                ? "bg-slate-900 text-white font-semibold shadow-2xs"
                : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
            }`}
          >
            All Speakers
          </button>
          {MOCK_SPEAKERS.map((sp) => (
            <button
              key={sp.id}
              onClick={() => setSelectedSpeaker(sp.label)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                selectedSpeaker === sp.label
                  ? "bg-slate-900 text-white font-semibold shadow-2xs"
                  : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50"
              }`}
            >
              {sp.displayName}
            </button>
          ))}
        </div>
      </div>

      {/* Transcript List */}
      <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100 p-0 overflow-hidden shadow-xs">
        {filteredSegments.length === 0 ? (
          <div className="py-12 text-center text-xs text-slate-400">
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
                className="p-4 hover:bg-slate-50/80 transition-colors flex items-start gap-4 group"
              >
                {/* Speaker Avatar */}
                <div
                  className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0 mt-0.5 shadow-2xs"
                  style={{ background: speakerColor(speakerInfo.label) }}
                >
                  {speakerInfo.initials}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 space-y-1">
                  <div className="flex items-center gap-2.5">
                    <span className="text-xs font-bold text-slate-900">
                      {speakerInfo.displayName}
                    </span>
                    <span className="px-2 py-0.5 rounded bg-indigo-50 text-[10px] font-mono font-semibold text-indigo-700">
                      {formatDuration(seg.start_time)}
                    </span>
                  </div>
                  <p className="text-xs text-slate-700 leading-relaxed">
                    {seg.text}
                  </p>
                </div>

                {/* Actions */}
                <div className="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => handleCopy(seg.id, seg.text)}
                    title="Copy transcript segment"
                    className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
                  >
                    {copiedId === seg.id ? (
                      <Check size={13} className="text-emerald-600" />
                    ) : (
                      <Copy size={13} />
                    )}
                  </button>
                  <button
                    onClick={() => toast.info("Segment bookmarked")}
                    title="Bookmark segment"
                    className="p-1.5 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-700 transition-colors cursor-pointer"
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
