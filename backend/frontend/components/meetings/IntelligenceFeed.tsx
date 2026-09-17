"use client";

import React, { useState } from "react";
import {
  Search,
  Copy,
  Layers,
  ChevronDown,
  CheckCircle2,
  Lock,
  Edit3,
  TrendingUp,
  Sparkles,
  Check
} from "lucide-react";
import { MeetingIntelligence, Metric } from "./types";
import { ResponsiveContainer, LineChart, Line } from "recharts";

interface IntelligenceFeedProps {
  intelligence: MeetingIntelligence;
  onSeek: (seconds: number) => void;
  activeTimestamp?: number;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

// Minimal Sparkline Card for Metrics
function MetricCard({
  metric,
  color = "#4f46e5"
}: {
  metric: Metric;
  color?: string;
}) {
  const data = metric.trend.map((val, idx) => ({ index: idx, value: val }));

  return (
    <div className="bg-white border border-slate-200/80 rounded-xl p-4 shadow-xs flex items-center justify-between hover:border-slate-300 transition-colors">
      <div className="space-y-1">
        <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
          {metric.label}
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 tracking-tight">
            {metric.score}
          </span>
          <span
            className={`text-[11px] font-semibold px-1.5 py-0.5 rounded-full ${
              metric.status === "GOOD"
                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                : metric.status === "WARNING"
                ? "bg-amber-50 text-amber-700 border border-amber-200"
                : "bg-slate-100 text-slate-600 border border-slate-200"
            }`}
          >
            {metric.status}
          </span>
        </div>
      </div>

      {/* Sparkline Visual */}
      <div className="w-20 h-9">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <Line
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function IntelligenceFeed({
  intelligence,
  onSeek,
  activeTimestamp
}: IntelligenceFeedProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("Read AI Recap");
  const [showTemplateDropdown, setShowTemplateDropdown] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [noteContent, setNoteContent] = useState("");
  const [isEditingNote, setIsEditingNote] = useState(false);

  const handleCopyRecap = () => {
    const text = `
Meeting: ${intelligence.title}
Date: ${intelligence.date} (${intelligence.timeRange})
Source: ${intelligence.source}

EXECUTIVE SUMMARY:
${intelligence.summary}

ACTION ITEMS:
${intelligence.actionItems.map((a) => `[${formatTime(a.timestampSeconds)}] ${a.owner}: ${a.text}`).join("\n")}

KEY DISCUSSION POINTS:
${intelligence.discussionPoints.map((d) => `[${formatTime(d.timestampSeconds)}] ${d.title}\n${d.summary}`).join("\n\n")}
`.trim();

    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(text);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  // Filter discussion points by search query
  const filteredDiscussionPoints = intelligence.discussionPoints.filter(
    (dp) =>
      dp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dp.summary.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-full space-y-7 pb-16">
      {/* ── 1. SEARCH & TEMPLATE CONTROLS ROW ─────────────────────────────── */}
      <div className="flex items-center justify-between gap-4 pt-4">
        {/* Search Recap Input */}
        <div className="relative w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search recap..."
            className="w-full pl-9 pr-3 py-1.5 text-sm bg-white border border-slate-200 rounded-lg text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 shadow-2xs transition-all"
          />
        </div>

        {/* Template Selector + Copy Button */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowTemplateDropdown(!showTemplateDropdown)}
              className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs flex items-center gap-2 transition-colors cursor-pointer"
            >
              <Layers className="w-3.5 h-3.5 text-slate-500" />
              <span>Template: {selectedTemplate}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showTemplateDropdown && (
              <div className="absolute right-0 mt-1 w-52 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-20 animate-in fade-in">
                {["Read AI Recap", "Executive Briefing", "Sprint Retrospective", "Architecture RFC"].map((tpl) => (
                  <button
                    key={tpl}
                    type="button"
                    onClick={() => {
                      setSelectedTemplate(tpl);
                      setShowTemplateDropdown(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs transition-colors flex items-center justify-between ${
                      selectedTemplate === tpl
                        ? "text-indigo-600 bg-indigo-50 font-semibold"
                        : "text-slate-700 hover:bg-slate-50"
                    }`}
                  >
                    <span>{tpl}</span>
                    {selectedTemplate === tpl && <Check className="w-3.5 h-3.5 text-indigo-600" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleCopyRecap}
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs transition-colors cursor-pointer"
            title="Copy full recap to clipboard"
          >
            {isCopied ? (
              <Check className="w-3.5 h-3.5 text-emerald-600" />
            ) : (
              <Copy className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      </div>

      {/* ── 2. METRICS ROW (REPORT SCORE, ENGAGEMENT, SENTIMENT) ───────────── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <MetricCard metric={intelligence.metrics.report} color="#4f46e5" />
        <MetricCard metric={intelligence.metrics.engagement} color="#059669" />
        <MetricCard metric={intelligence.metrics.sentiment} color="#0284c7" />
      </div>

      {/* ── 3. EXECUTIVE SUMMARY ──────────────────────────────────────────── */}
      <section className="space-y-3">
        <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-indigo-600" />
          <span>Executive Summary</span>
        </h2>
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs">
          <p className="text-slate-700 text-sm leading-relaxed font-normal">
            {intelligence.summary}
          </p>
        </div>
      </section>

      {/* ── 4. ACTION ITEMS (PHASE 15 & 16 ACTION RESOLUTION) ─────────────── */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>Action Items</span>
            <span className="text-xs font-semibold px-2 py-0.5 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full">
              {intelligence.actionItems.length}
            </span>
          </h2>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100 shadow-xs overflow-hidden">
          {intelligence.actionItems.map((action) => (
            <div
              key={action.id}
              className="p-3.5 flex items-start gap-3 hover:bg-slate-50/70 transition-colors group"
            >
              {/* Clickable Seeking Pill (Phase 13 Canonical Timestamp) */}
              <button
                type="button"
                onClick={() => onSeek(action.timestampSeconds)}
                className="mt-0.5 rounded-md bg-slate-100 text-slate-500 text-[11px] font-medium font-mono px-2 py-0.5 cursor-pointer hover:bg-indigo-100 hover:text-indigo-700 transition-colors shrink-0"
                title={`Jump to ${formatTime(action.timestampSeconds)}`}
              >
                {formatTime(action.timestampSeconds)}
              </button>

              <div className="flex-1 text-sm text-slate-700 leading-snug">
                <span className="font-semibold text-slate-900 mr-1.5">
                  {action.owner}:
                </span>
                <span>{action.text}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 5. KEY DISCUSSION POINTS (PHASE 15 MAPPING) ───────────────────── */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-slate-900 tracking-tight">
          Key Discussion Points
        </h2>

        <div className="space-y-4">
          {filteredDiscussionPoints.map((point) => (
            <article
              key={point.id}
              className="flex flex-col gap-2 group p-3.5 -mx-3.5 rounded-xl hover:bg-slate-50/70 transition-colors mb-2"
            >
              {/* Timestamp + Topic Header */}
              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => onSeek(point.timestampSeconds)}
                  className="rounded-md bg-slate-100 text-slate-500 text-[11px] font-medium font-mono px-2 py-0.5 cursor-pointer hover:bg-indigo-100 hover:text-indigo-700 transition-colors shrink-0"
                  title={`Jump to ${formatTime(point.timestampSeconds)}`}
                >
                  {formatTime(point.timestampSeconds)}
                </button>

                <h3 className="text-sm font-semibold text-slate-900 tracking-tight group-hover:text-indigo-950 transition-colors">
                  {point.title}
                </h3>
              </div>

              {/* Discussion Narrative Body */}
              <p className="text-sm text-slate-600 leading-relaxed font-normal">
                {point.summary}
              </p>
            </article>
          ))}
        </div>
      </section>

      {/* ── 6. YOUR NOTES ─────────────────────────────────────────────────── */}
      <section className="space-y-3 pt-2 pb-12">
        <div className="flex items-center gap-2">
          <h2 className="text-lg font-bold text-slate-900 tracking-tight">
            Your Notes
          </h2>
          <div className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-md">
            <Lock className="w-3 h-3 text-slate-400" />
            <span>Private to you</span>
          </div>
          <span className="text-[11px] font-medium text-slate-400 bg-slate-50 border border-slate-200 px-1.5 py-0.5 rounded">
            Edited
          </span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-xs">
          {isEditingNote ? (
            <div className="space-y-2">
              <textarea
                value={noteContent}
                onChange={(e) => setNoteContent(e.target.value)}
                placeholder="Type your personal notes here..."
                rows={3}
                className="w-full p-2.5 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800"
                autoFocus
              />
              <div className="flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsEditingNote(false)}
                  className="px-3 py-1.5 text-xs font-semibold text-slate-600 hover:bg-slate-100 rounded-md"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => setIsEditingNote(false)}
                  className="px-3 py-1.5 text-xs font-semibold bg-indigo-600 text-white hover:bg-indigo-700 rounded-md"
                >
                  Save Note
                </button>
              </div>
            </div>
          ) : (
            <div
              onClick={() => setIsEditingNote(true)}
              className="text-sm text-slate-500 cursor-pointer hover:text-slate-700 flex items-center justify-between"
            >
              <span>
                {noteContent.trim() ? noteContent : "You did not take any notes in this meeting"}
              </span>
              <Edit3 className="w-3.5 h-3.5 text-slate-400 hover:text-indigo-600" />
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
