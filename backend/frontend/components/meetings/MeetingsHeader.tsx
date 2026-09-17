"use client";

import React from "react";
import { Search, ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

export type StatusOption = "All Meetings" | "Completed" | "Processing" | "Pending";

interface MeetingsHeaderProps {
  search: string;
  onSearchChange: (value: string) => void;
  statusFilter: StatusOption;
  onStatusFilterChange: (status: StatusOption) => void;
  sourceFilter: string;
  onSourceFilterChange: (source: string) => void;
  timeFilter: string;
  onTimeFilterChange: (time: string) => void;
  meetingCount: number;
}

const STATUS_OPTIONS: StatusOption[] = [
  "All Meetings",
  "Completed",
  "Processing",
  "Pending",
];

const SOURCE_OPTIONS = ["All Sources", "Google Meet", "Zoom", "Microsoft Teams"];
const TIME_OPTIONS = ["Anytime", "Past 7 days", "Past 30 days", "Past 3 months"];

export function MeetingsHeader({
  search,
  onSearchChange,
  statusFilter,
  onStatusFilterChange,
  sourceFilter,
  onSourceFilterChange,
  timeFilter,
  onTimeFilterChange,
  meetingCount,
}: MeetingsHeaderProps) {
  return (
    <div className="flex items-center justify-between gap-4 flex-wrap pb-1">
      {/* Left: Clean Search Input & Discrete Status Filter Pills */}
      <div className="flex items-center gap-3.5 flex-wrap">
        {/* Search Input */}
        <div className="relative">
          <Search
            size={14}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
          />
          <input
            id="meeting-filter-input"
            type="text"
            placeholder="Filter by meeting title..."
            value={search}
            onChange={(e) => onSearchChange(e.target.value)}
            className={cn(
              "h-9 w-60 pl-8.5 pr-3 rounded-lg bg-white border border-slate-200 shadow-2xs",
              "text-xs text-slate-900 placeholder:text-slate-400",
              "focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100",
              "transition-all duration-150"
            )}
          />
        </div>

        {/* Discrete Status Filter Pills with independent padding and borders */}
        <div className="flex items-center gap-2">
          {STATUS_OPTIONS.map((status) => {
            const active = statusFilter === status;
            return (
              <button
                key={status}
                type="button"
                onClick={() => onStatusFilterChange(status)}
                className={cn(
                  "px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 cursor-pointer whitespace-nowrap",
                  active
                    ? "bg-indigo-600 text-white border border-indigo-600 shadow-xs font-semibold"
                    : "bg-white text-slate-600 border border-slate-200 hover:bg-slate-50 hover:text-slate-900"
                )}
              >
                {status}
              </button>
            );
          })}
        </div>
      </div>

      {/* Right Controls: Source, Time Dropdowns and Meeting Count */}
      <div className="flex items-center gap-2.5">
        {/* All Sources Dropdown */}
        <div className="relative">
          <select
            aria-label="Filter by source"
            value={sourceFilter}
            onChange={(e) => onSourceFilterChange(e.target.value)}
            className={cn(
              "h-9 pl-3 pr-7 rounded-lg bg-white border border-slate-200 shadow-2xs text-xs font-medium text-slate-700",
              "appearance-none cursor-pointer focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 transition-colors"
            )}
          >
            {SOURCE_OPTIONS.map((src) => (
              <option key={src} value={src}>
                {src}
              </option>
            ))}
          </select>
          <ChevronDown
            size={13}
            className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400"
          />
        </div>

        {/* Anytime Dropdown */}
        <div className="relative">
          <select
            aria-label="Filter by time range"
            value={timeFilter}
            onChange={(e) => onTimeFilterChange(e.target.value)}
            className={cn(
              "h-9 pl-3 pr-7 rounded-lg bg-white border border-slate-200 shadow-2xs text-xs font-medium text-slate-700",
              "appearance-none cursor-pointer focus:outline-none focus:border-indigo-600 focus:ring-2 focus:ring-indigo-100 transition-colors"
            )}
          >
            {TIME_OPTIONS.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <ChevronDown
            size={13}
            className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400"
          />
        </div>

        {/* Meeting Count Indicator */}
        <span className="text-xs font-medium text-slate-500 pl-1">
          {meetingCount} {meetingCount === 1 ? "meeting" : "meetings"}
        </span>
      </div>
    </div>
  );
}
