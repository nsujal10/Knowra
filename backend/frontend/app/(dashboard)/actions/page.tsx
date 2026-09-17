"use client";

import React, { useState } from "react";
import Link from "next/link";
import { formatDuration } from "@/lib/utils";
import { MOCK_ACTION_ITEMS, getSegmentTimestamp } from "@/lib/data/mock";
import {
  CheckSquare,
  Square,
  Search,
  ArrowRight,
  User,
  Clock,
} from "lucide-react";

export default function GlobalActionsPage() {
  const [items, setItems] = useState(MOCK_ACTION_ITEMS);
  const [filter, setFilter] = useState("ALL");
  const [search, setSearch] = useState("");

  const toggle = (id: string) => {
    setItems((prev) =>
      prev.map((i) =>
        i.id === id
          ? {
              ...i,
              status: i.status === "COMPLETED" ? "OPEN" : "COMPLETED",
            }
          : i
      )
    );
  };

  const filtered = items.filter((i) => {
    const matchesSearch =
      !search || i.title.toLowerCase().includes(search.toLowerCase());
    const matchesStatus =
      filter === "ALL"
        ? true
        : filter === "COMPLETED"
        ? i.status === "COMPLETED"
        : i.status !== "COMPLETED";
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="space-y-6 max-w-7xl mx-auto animate-fade-in pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)] tracking-tight">
            Action Items Tracker
          </h1>
          <p className="text-xs text-[var(--muted-strong)] mt-1">
            Centrally tracked deliverables, owners, and commitments extracted by AI from company meetings.
          </p>
        </div>
      </div>

      {/* Search and Filters */}
      <div className="card p-3 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
          <input
            type="text"
            placeholder="Search action items…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-8 pl-9 pr-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] text-xs text-[var(--foreground)] placeholder-[var(--muted)] outline-none focus:border-[var(--primary)] transition-all"
          />
        </div>

        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setFilter("ALL")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
              filter === "ALL"
                ? "bg-[var(--primary)] text-white font-semibold"
                : "bg-[var(--surface-2)] text-[var(--muted-strong)] hover:text-[var(--foreground)]"
            }`}
          >
            All ({items.length})
          </button>
          <button
            onClick={() => setFilter("OPEN")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
              filter === "OPEN"
                ? "bg-[var(--primary)] text-white font-semibold"
                : "bg-[var(--surface-2)] text-[var(--muted-strong)] hover:text-[var(--foreground)]"
            }`}
          >
            Pending ({items.filter((i) => i.status !== "COMPLETED").length})
          </button>
          <button
            onClick={() => setFilter("COMPLETED")}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer ${
              filter === "COMPLETED"
                ? "bg-[var(--primary)] text-white font-semibold"
                : "bg-[var(--surface-2)] text-[var(--muted-strong)] hover:text-[var(--foreground)]"
            }`}
          >
            Completed ({items.filter((i) => i.status === "COMPLETED").length})
          </button>
        </div>
      </div>

      {/* List */}
      <div className="card divide-y divide-[var(--border)] p-0 overflow-hidden">
        {filtered.map((item) => {
          const isDone = item.status === "COMPLETED";
          const timestamp = getSegmentTimestamp(item.segment_id);
          return (
            <div
              key={item.id}
              className="p-4 hover:bg-[var(--surface-2)] transition-colors flex items-start gap-4 group"
            >
              <button
                onClick={() => toggle(item.id)}
                className="mt-0.5 text-[var(--muted-strong)] hover:text-[var(--primary)] transition-colors cursor-pointer"
              >
                {isDone ? (
                  <CheckSquare size={18} className="text-emerald-400" />
                ) : (
                  <Square size={18} />
                )}
              </button>

              <div className="flex-1 min-w-0 space-y-1">
                <p
                  className={`text-xs font-medium leading-relaxed ${
                    isDone
                      ? "line-through text-[var(--muted)]"
                      : "text-[var(--foreground)]"
                  }`}
                >
                  {item.title}
                </p>
                <div className="flex flex-wrap items-center gap-4 text-[11px] text-[var(--muted)]">
                  <span className="flex items-center gap-1">
                    <User size={11} />
                    Owner: <strong className="text-[var(--foreground)]">{item.assignee ?? "Team"}</strong>
                  </span>
                  {item.due_date && (
                    <span className="flex items-center gap-1">
                      <Clock size={11} />
                      Due: {item.due_date.split("T")[0]}
                    </span>
                  )}
                  <Link
                    href={`/meetings/${item.meeting_id}/actions`}
                    className="text-[var(--primary)] hover:underline inline-flex items-center gap-1"
                  >
                    <span>Source meeting</span>
                    <ArrowRight size={10} />
                  </Link>
                </div>
              </div>

              <span
                className={`px-2 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider shrink-0 ${
                  isDone
                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                    : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                }`}
              >
                {item.status}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
