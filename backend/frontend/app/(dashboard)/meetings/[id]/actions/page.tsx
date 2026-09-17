"use client";

import React, { useState } from "react";
import { formatDuration } from "@/lib/utils";
import { MOCK_ACTION_ITEMS, getSegmentTimestamp } from "@/lib/data/mock";
import {
  CheckSquare,
  Square,
  Clock,
  User,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";

export default function MeetingActionsPage() {
  const [items, setItems] = useState(MOCK_ACTION_ITEMS);

  const toggleItem = (id: string) => {
    setItems((prev) =>
      prev.map((item) =>
        item.id === id
          ? {
              ...item,
              status: item.status === "COMPLETED" ? "OPEN" : "COMPLETED",
            }
          : item
      )
    );
  };

  const completedCount = items.filter((i) => i.status === "COMPLETED").length;

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="card p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-[var(--muted)] uppercase font-semibold">Total Action Items</span>
            <p className="text-2xl font-bold text-[var(--foreground)] mt-1">{items.length}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center">
            <CheckSquare size={20} />
          </div>
        </div>

        <div className="card p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-[var(--muted)] uppercase font-semibold">Completed</span>
            <p className="text-2xl font-bold text-emerald-400 mt-1">{completedCount} of {items.length}</p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <CheckCircle2 size={20} />
          </div>
        </div>

        <div className="card p-4 flex items-center justify-between">
          <div>
            <span className="text-xs text-[var(--muted)] uppercase font-semibold">Pending Review</span>
            <p className="text-2xl font-bold text-amber-400 mt-1">
              {items.filter((i) => i.status !== "COMPLETED").length}
            </p>
          </div>
          <div className="w-10 h-10 rounded-lg bg-amber-500/10 text-amber-400 flex items-center justify-center">
            <AlertCircle size={20} />
          </div>
        </div>
      </div>

      {/* Action Items List */}
      <div className="card divide-y divide-[var(--border)] p-0 overflow-hidden">
        {items.map((item) => {
          const isDone = item.status === "COMPLETED";
          const timestamp = getSegmentTimestamp(item.segment_id);
          return (
            <div
              key={item.id}
              className="p-4 hover:bg-[var(--surface-2)] transition-colors flex items-start gap-4 group"
            >
              <button
                onClick={() => toggleItem(item.id)}
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
                  className={`text-xs font-medium leading-relaxed transition-all ${
                    isDone
                      ? "line-through text-[var(--muted)]"
                      : "text-[var(--foreground)]"
                  }`}
                >
                  {item.title}
                </p>
                <div className="flex flex-wrap items-center gap-3 text-[11px] text-[var(--muted)]">
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
                  <span className="font-mono text-[10px]">
                    Recorded @ {formatDuration(timestamp)}
                  </span>
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
