"use client";

import React, { useState } from "react";
import {
  Search,
  Copy,
  Layers,
  ChevronDown,
  Lock,
  Edit3,
  Check
} from "lucide-react";
import { MeetingIntelligence, Metric } from "./types";

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

const WAVE_MEETING_SCORE = {
  stroke: "M 0,22 C 30,24 60,18 90,14 C 120,10 150,18 180,12 C 190,10 195,11 200,8",
  fill: "M 0,22 C 30,24 60,18 90,14 C 120,10 150,18 180,12 C 190,10 195,11 200,8 L 200,40 L 0,40 Z"
};

const WAVE_ENGAGEMENT = {
  stroke: "M 0,26 C 25,28 55,20 85,22 C 115,24 145,12 175,15 C 185,16 195,14 200,10",
  fill: "M 0,26 C 25,28 55,20 85,22 C 115,24 145,12 175,15 C 185,16 195,14 200,10 L 200,40 L 0,40 Z"
};

const WAVE_SENTIMENT = {
  stroke: "M 0,24 C 30,22 60,25 90,18 C 120,11 150,20 180,14 C 190,12 195,13 200,9",
  fill: "M 0,24 C 30,22 60,25 90,18 C 120,11 150,20 180,14 C 190,12 195,13 200,9 L 200,40 L 0,40 Z"
};

function MetricCard({
  metric,
  color,
  gradientId,
  wave
}: {
  metric: Metric;
  color: string;
  gradientId: string;
  wave: { stroke: string; fill: string };
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 flex flex-col justify-between shadow-sm hover:border-slate-300 transition-colors">
      {/* Top Row: Title */}
      <div className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
        {metric.label}
      </div>

      {/* Value Row: Large Number + Status Pill */}
      <div className="flex items-baseline gap-2 mt-2">
        <span className="text-2xl font-bold text-slate-900 tracking-tight">
          {metric.score}
        </span>
        <span
          className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
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

      {/* SVG Wave Chart with Soft Gradient Fill */}
      <div className="mt-3 h-8 w-full overflow-hidden">
        <svg viewBox="0 0 200 40" className="w-full h-full" preserveAspectRatio="none">
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.3" />
              <stop offset="100%" stopColor={color} stopOpacity="0.0" />
            </linearGradient>
          </defs>
          <path d={wave.fill} fill={`url(#${gradientId})`} />
          <path d={wave.stroke} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" />
        </svg>
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
  const [selectedTemplate, setSelectedTemplate] = useState("Knowra AI Recap");
  const [showTemplateDropdown, setShowTemplateDropdown] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [noteContent, setNoteContent] = useState("");
  const [isEditingNote, setIsEditingNote] = useState(false);

  const handleCopyRecap = () => {
    const text = `
Meeting: ${intelligence.title}
Date: ${intelligence.date} (${intelligence.timeRange})
Source: ${intelligence.source}

SUMMARY:
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

  const filteredDiscussionPoints = intelligence.discussionPoints.filter(
    (dp) =>
      dp.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      dp.summary.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="w-full pb-16">
      {/* ── 1. SEARCH & TEMPLATE CONTROLS ROW ─────────────────────────────── */}
      <div className="flex items-center justify-between gap-4 pt-4 mb-6">
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
                {["Knowra AI Recap", "Executive Briefing", "Sprint Retrospective", "Architecture RFC"].map((tpl) => (
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

      {/* ── 2. METRIC CARDS (LEFT COLUMN) ─────────────────────────────────── */}
      <div className="grid grid-cols-3 gap-4 mb-8">
        <MetricCard
          metric={intelligence.metrics.report}
          color="#5345dc"
          gradientId="grad-score"
          wave={WAVE_MEETING_SCORE}
        />
        <MetricCard
          metric={intelligence.metrics.engagement}
          color="#059669"
          gradientId="grad-engagement"
          wave={WAVE_ENGAGEMENT}
        />
        <MetricCard
          metric={intelligence.metrics.sentiment}
          color="#0284c7"
          gradientId="grad-sentiment"
          wave={WAVE_SENTIMENT}
        />
      </div>

      {/* ── 3. EXECUTIVE SUMMARY SECTION ─────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="text-lg font-bold text-slate-900 mt-10 mb-4 pb-2 border-b border-slate-100">
          Executive Summary
        </h2>
        <p className="text-sm text-slate-700 leading-relaxed font-normal">
          {intelligence.summary}
        </p>
      </section>

      {/* ── 4. ACTION ITEMS (FIXING THE FLEX) ─────────────────────────────── */}
      <section className="mb-8">
        <h2 className="text-lg font-bold text-slate-900 mt-10 mb-4 pb-2 border-b border-slate-100">
          Action Items
        </h2>

        <div>
          {intelligence.actionItems.map((action) => (
            <div
              key={action.id}
              className="flex items-start gap-4 mb-5 group cursor-pointer"
              onClick={() => onSeek(action.timestampSeconds)}
            >
              <div className="shrink-0 mt-0.5">
                <span className="bg-slate-100 text-slate-600 font-mono text-[11px] px-2 py-1 rounded-md font-medium group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors">
                  {formatTime(action.timestampSeconds)}
                </span>
              </div>
              <div className="flex-1 text-sm text-slate-700 leading-relaxed">
                <span className="font-semibold text-slate-900 mr-1.5">
                  {action.owner}:
                </span>
                <span>{action.text}</span>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ── 5. KEY DISCUSSION POINTS ──────────────────────────────────────── */}
      <section className="mb-8">
        <h2 className="text-lg font-bold text-slate-900 mt-10 mb-4 pb-2 border-b border-slate-100">
          Key Discussion Points
        </h2>

        <div className="space-y-6">
          {filteredDiscussionPoints.map((point) => (
            <div key={point.id} className="flex flex-col gap-2 mb-6 group">
              <div className="flex items-center gap-3">
                <div className="shrink-0">
                  <span
                    onClick={() => onSeek(point.timestampSeconds)}
                    className="bg-slate-100 text-slate-600 font-mono text-[11px] px-2 py-1 rounded-md font-medium cursor-pointer group-hover:bg-indigo-50 group-hover:text-indigo-600 transition-colors"
                  >
                    {formatTime(point.timestampSeconds)}
                  </span>
                </div>
                <h3 className="text-sm font-semibold text-slate-900 tracking-tight">
                  {point.title}
                </h3>
              </div>
              <p className="text-sm text-slate-600 leading-relaxed pl-1 font-normal">
                {point.summary}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── 6. YOUR NOTES ─────────────────────────────────────────────────── */}
      <section className="pt-2 pb-8">
        <div className="flex items-center justify-between pb-2 mb-4 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-slate-900 tracking-tight">
              Your Notes
            </h2>
            <div className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500 bg-slate-100 border border-slate-200 px-2 py-0.5 rounded-md">
              <Lock className="w-3 h-3 text-slate-400" />
              <span>Private to you</span>
            </div>
          </div>
          <button
            type="button"
            onClick={() => setIsEditingNote(!isEditingNote)}
            className="text-xs font-semibold text-indigo-600 hover:text-indigo-700 flex items-center gap-1 cursor-pointer"
          >
            <Edit3 className="w-3.5 h-3.5" />
            <span>{isEditingNote ? "Done" : "Edit Notes"}</span>
          </button>
        </div>

        {isEditingNote ? (
          <div className="space-y-2">
            <textarea
              value={noteContent}
              onChange={(e) => setNoteContent(e.target.value)}
              placeholder="Type your personal notes here..."
              rows={4}
              className="w-full p-3 text-sm border border-slate-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 text-slate-800 bg-white shadow-2xs"
              autoFocus
            />
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setIsEditingNote(false)}
                className="px-3.5 py-1.5 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-md shadow-xs transition-colors"
              >
                Save Notes
              </button>
            </div>
          </div>
        ) : (
          <div
            onClick={() => setIsEditingNote(true)}
            className="p-3.5 bg-slate-50 border border-slate-200/80 rounded-lg text-sm text-slate-600 cursor-pointer hover:bg-slate-100/70 transition-colors"
          >
            {noteContent || (
              <span className="text-slate-400 italic">
                Click here to add private notes about this meeting...
              </span>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
