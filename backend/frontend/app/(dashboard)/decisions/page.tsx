"use client";

import React, { useState } from "react";
import Link from "next/link";
import { formatDuration } from "@/lib/utils";
import { MOCK_DECISIONS, getSegmentTimestamp } from "@/lib/data/mock";
import {
  Gavel,
  Search,
  ArrowRight,
  Sparkles,
} from "lucide-react";

export default function GlobalDecisionsPage() {
  const [search, setSearch] = useState("");

  const filtered = MOCK_DECISIONS.filter((d) => {
    return (
      !search ||
      d.title.toLowerCase().includes(search.toLowerCase()) ||
      d.summary.toLowerCase().includes(search.toLowerCase())
    );
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)] tracking-tight">
            Decisions Registry
          </h1>
          <p className="text-xs text-[var(--muted-strong)] mt-1">
            Enterprise knowledge graph indexing all verified consensus decisions reached across meetings.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            {MOCK_DECISIONS.length} Verified Decisions
          </span>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="card p-3 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
          <input
            type="text"
            placeholder="Search decisions across organization…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-8 pl-9 pr-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] text-xs text-[var(--foreground)] placeholder-[var(--muted)] outline-none focus:border-[var(--primary)] transition-all"
          />
        </div>

        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
          <button
            className="px-3 py-1 rounded-full text-xs font-semibold bg-[var(--primary)] text-white"
          >
            All Decisions ({MOCK_DECISIONS.length})
          </button>
        </div>
      </div>

      {/* Decisions Feed */}
      <div className="space-y-3">
        {filtered.map((d) => {
          const timestamp = getSegmentTimestamp(d.segment_id);
          return (
            <div
              key={d.id}
              className="card p-5 hover:border-[var(--border-strong)] transition-all space-y-3 group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-1 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-blue-500/10 text-blue-400 border border-blue-500/20">
                      Architecture
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      Approved
                    </span>
                  </div>
                  <h2 className="text-sm font-bold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors pt-1">
                    {d.title}
                  </h2>
                </div>
                <Link
                  href={`/meetings/${d.meeting_id}/decisions`}
                  className="text-xs font-medium text-[var(--primary)] hover:underline flex items-center gap-1 shrink-0"
                >
                  <span>View in Meeting</span>
                  <ArrowRight size={12} />
                </Link>
              </div>

              <p className="text-xs text-[var(--muted-strong)] leading-relaxed">
                {d.summary}
              </p>

              <div className="pt-2 border-t border-[var(--border)] flex items-center justify-between text-[11px] text-[var(--muted)]">
                <span>Decided by: <strong className="text-[var(--foreground)]">{d.made_by ?? "Team"}</strong></span>
                <span className="font-mono">Timestamp {formatDuration(timestamp)}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
