"use client";

import React, { useState } from "react";
import { useParams } from "next/navigation";
import {
  Search,
  Copy,
  Layers,
  ChevronDown,
  Lock,
  Edit3,
  Check,
  AlertCircle,
  RefreshCw,
  Loader2,
  Sparkles,
} from "lucide-react";
import {
  useRealIntelligence,
  ActionItem,
  Topic,
} from "@/hooks/useRealIntelligence";

interface IntelligenceFeedProps {
  meetingId?: string;
  onSeek: (seconds: number) => void;
  activeTimestamp?: number;
  intelligence?: any;
}

/**
 * Format timestamp seconds into MM:SS format (e.g., 480 -> "8:00", 0 -> "0:00")
 */
function formatTime(seconds?: number): string {
  if (seconds === undefined || seconds === null || isNaN(seconds)) return "0:00";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s < 10 ? "0" : ""}${s}`;
}

export function IntelligenceFeed({
  meetingId: propMeetingId,
  onSeek,
  activeTimestamp,
}: IntelligenceFeedProps) {
  const params = useParams();
  const meetingId = propMeetingId || (params?.id as string) || "";

  // ── 1. REAL DATA FETCHING & POLLING VIA CUSTOM HOOK ───────────────────────
  const {
    intelligence,
    isLoading,
    isProcessing,
    isFailed,
    error,
    refetch,
  } = useRealIntelligence(meetingId);

  // ── 2. LOCAL UI STATE ─────────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState("Knowra AI Recap");
  const [showTemplateDropdown, setShowTemplateDropdown] = useState(false);
  const [isCopied, setIsCopied] = useState(false);
  const [noteContent, setNoteContent] = useState("");
  const [isEditingNote, setIsEditingNote] = useState(false);

  // ── 3. COPY FULL RECAP TO CLIPBOARD ───────────────────────────────────────
  const handleCopyRecap = () => {
    if (!intelligence) return;

    const summaryText = intelligence.summary?.executive || "No summary available.";
    const actionItemsText = intelligence.actionItems?.length
      ? intelligence.actionItems
          .map(
            (a) =>
              `[${formatTime(a.evidence?.[0]?.timestampStart)}] ${a.owner}: ${a.task}`
          )
          .join("\n")
      : "No action items.";
    const topicsText = intelligence.topics?.length
      ? intelligence.topics
          .map(
            (t) =>
              `[${formatTime(t.evidence?.[0]?.timestampStart)}] ${t.title}\n${t.description}`
          )
          .join("\n\n")
      : "No discussion points.";

    const fullText = [
      `KNOWRA MEETING INTELLIGENCE RECAP`,
      `==================================`,
      `EXECUTIVE SUMMARY:`,
      summaryText,
      ``,
      `ACTION ITEMS:`,
      actionItemsText,
      ``,
      `KEY DISCUSSION POINTS:`,
      topicsText,
    ].join("\n");

    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(fullText);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  // ── 4. FILTERING DATA BY SEARCH QUERY ─────────────────────────────────────
  const filteredTopics = (intelligence?.topics || []).filter((topic: Topic) => {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      topic.title?.toLowerCase().includes(q) ||
      topic.description?.toLowerCase().includes(q)
    );
  });

  const filteredActionItems = (intelligence?.actionItems || []).filter(
    (item: ActionItem) => {
      if (!searchQuery.trim()) return true;
      const q = searchQuery.toLowerCase();
      return (
        item.owner?.toLowerCase().includes(q) ||
        item.task?.toLowerCase().includes(q)
      );
    }
  );

  return (
    <div className="w-full pb-16">
      {/* ── TOP CONTROLS: SEARCH & TEMPLATE SELECTOR ───────────────────────── */}
      <div className="flex items-center justify-between gap-4 pt-1 mb-6">
        {/* Search Recap Input */}
        <div className="relative w-72">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search recap..."
            disabled={isProcessing}
            className="w-full pl-9 pr-3 py-1.5 text-sm bg-white border border-slate-200 rounded-lg text-slate-700 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 shadow-2xs transition-all disabled:opacity-60"
          />
        </div>

        {/* Template Selector + Copy Button */}
        <div className="flex items-center gap-2">
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowTemplateDropdown(!showTemplateDropdown)}
              disabled={isProcessing}
              className="px-3 py-1.5 text-xs font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs flex items-center gap-2 transition-colors cursor-pointer disabled:opacity-60"
            >
              <Layers className="w-3.5 h-3.5 text-slate-500" />
              <span>Template: {selectedTemplate}</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showTemplateDropdown && (
              <div className="absolute right-0 mt-1 w-52 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-20 animate-in fade-in">
                {[
                  "Knowra AI Recap",
                  "Executive Briefing",
                  "Sprint Retrospective",
                  "Architecture RFC",
                ].map((tpl) => (
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
                    {selectedTemplate === tpl && (
                      <Check className="w-3.5 h-3.5 text-indigo-600" />
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleCopyRecap}
            disabled={isProcessing || !intelligence}
            className="p-2 text-slate-500 hover:text-slate-800 bg-white border border-slate-200 hover:bg-slate-50 rounded-lg shadow-2xs transition-colors cursor-pointer disabled:opacity-60"
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

      {/* ── STATE 1: PROCESSING (ENTERPRISE-GRADE SKELETON LOADERS) ────────── */}
      {isProcessing && (
        <div className="space-y-8 animate-pulse">
          {/* Subtle processing banner */}
          <div className="flex items-center gap-2.5 px-3.5 py-2.5 bg-indigo-50/70 border border-indigo-100 rounded-lg text-xs text-indigo-700 font-medium">
            <Loader2 className="w-4 h-4 animate-spin text-indigo-600 shrink-0" />
            <span>
              Extracting meeting intelligence and action items from canonical
              transcript... Polling background worker.
            </span>
          </div>

          {/* Executive Summary Skeleton */}
          <section className="space-y-3">
            <div className="h-5 w-40 bg-slate-200 rounded-md" />
            <div className="space-y-2 pt-1">
              <div className="h-3.5 w-full bg-slate-100 rounded" />
              <div className="h-3.5 w-11/12 bg-slate-100 rounded" />
              <div className="h-3.5 w-4/5 bg-slate-100 rounded" />
            </div>
          </section>

          {/* Action Items Skeleton */}
          <section className="space-y-3 pt-2">
            <div className="h-5 w-32 bg-slate-200 rounded-md" />
            <div className="space-y-3 pt-1">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="h-5 w-12 bg-slate-200 rounded-md shrink-0" />
                  <div className="h-4 w-3/4 bg-slate-100 rounded" />
                </div>
              ))}
            </div>
          </section>

          {/* Key Discussion Points Skeleton */}
          <section className="space-y-4 pt-2">
            <div className="h-5 w-48 bg-slate-200 rounded-md" />
            <div className="space-y-5 pt-1">
              {[1, 2].map((i) => (
                <div key={i} className="space-y-2">
                  <div className="flex items-center gap-3">
                    <div className="h-5 w-12 bg-slate-200 rounded-md shrink-0" />
                    <div className="h-4 w-44 bg-slate-200 rounded" />
                  </div>
                  <div className="h-3.5 w-full bg-slate-100 rounded" />
                  <div className="h-3.5 w-5/6 bg-slate-100 rounded" />
                </div>
              ))}
            </div>
          </section>
        </div>
      )}

      {/* ── STATE 2: FAILED STATE ─────────────────────────────────────────── */}
      {isFailed && !isProcessing && (
        <div className="p-6 bg-red-50/70 border border-red-200 rounded-xl text-center space-y-3 my-4">
          <div className="w-10 h-10 bg-red-100 text-red-600 rounded-full flex items-center justify-center mx-auto">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-slate-900">
              Intelligence Extraction Failed
            </h3>
            <p className="text-xs text-slate-600 mt-1 max-w-md mx-auto">
              {error instanceof Error
                ? error.message
                : "Unable to extract intelligence from the meeting transcript."}
            </p>
          </div>
          <button
            type="button"
            onClick={() => refetch()}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 bg-white border border-slate-200 hover:bg-slate-50 text-xs font-semibold text-slate-700 rounded-lg shadow-2xs transition-colors cursor-pointer"
          >
            <RefreshCw className="w-3.5 h-3.5 text-slate-500" />
            <span>Retry Analysis</span>
          </button>
        </div>
      )}

      {/* ── STATE 3: READY (REAL BACKEND DATA) ─────────────────────────────── */}
      {!isProcessing && !isFailed && intelligence && (
        <div className="space-y-8">
          {/* 1. EXECUTIVE SUMMARY SECTION */}
          <section>
            <h2 className="text-base font-bold text-slate-900 pb-2 border-b border-slate-100">
              Executive Summary
            </h2>
            <div className="mt-3">
              {intelligence.summary?.executive ? (
                <p className="text-sm text-slate-700 leading-relaxed font-normal">
                  {intelligence.summary.executive}
                </p>
              ) : (
                <p className="text-sm text-slate-400 italic">
                  No executive summary available for this meeting.
                </p>
              )}
            </div>
          </section>

          {/* 2. ACTION ITEMS SECTION */}
          <section>
            <h2 className="text-base font-bold text-slate-900 pb-2 border-b border-slate-100">
              Action Items
            </h2>
            <div className="mt-3">
              {filteredActionItems.length > 0 ? (
                <div className="space-y-4">
                  {filteredActionItems.map((item: ActionItem) => {
                    const timestamp = item.evidence?.[0]?.timestampStart ?? 0;
                    return (
                      <div
                        key={item.id}
                        className="flex items-start gap-3 group"
                      >
                        <button
                          type="button"
                          onClick={() => onSeek(timestamp)}
                          className="shrink-0 mt-0.5 bg-indigo-50 text-indigo-700 text-[11px] font-mono px-2 py-0.5 rounded-md hover:bg-indigo-100 transition-colors cursor-pointer"
                          title={`Jump video to ${formatTime(timestamp)}`}
                        >
                          {formatTime(timestamp)}
                        </button>
                        <div className="flex-1 text-sm text-slate-700 leading-relaxed">
                          <span className="font-semibold text-slate-900 mr-1.5">
                            {item.owner}:
                          </span>
                          <span>{item.task}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-lg text-sm text-slate-500 italic">
                  {searchQuery
                    ? "No action items matching your search query."
                    : "No action items detected in this meeting."}
                </div>
              )}
            </div>
          </section>

          {/* 3. KEY DISCUSSION POINTS SECTION */}
          <section>
            <h2 className="text-base font-bold text-slate-900 pb-2 border-b border-slate-100">
              Key Discussion Points
            </h2>
            <div className="mt-4">
              {filteredTopics.length > 0 ? (
                <div className="space-y-6">
                  {filteredTopics.map((topic: Topic) => {
                    const timestamp = topic.evidence?.[0]?.timestampStart ?? 0;
                    return (
                      <div
                        key={topic.id}
                        className="flex flex-col gap-2 group"
                      >
                        <div className="flex items-center gap-2.5">
                          <button
                            type="button"
                            onClick={() => onSeek(timestamp)}
                            className="shrink-0 bg-indigo-50 text-indigo-700 text-[11px] font-mono px-2 py-0.5 rounded-md hover:bg-indigo-100 transition-colors cursor-pointer"
                            title={`Jump video to ${formatTime(timestamp)}`}
                          >
                            {formatTime(timestamp)}
                          </button>
                          <h3 className="text-lg font-semibold text-slate-900 tracking-tight">
                            {topic.title}
                          </h3>
                        </div>
                        <p className="text-sm text-slate-600 leading-relaxed font-normal pl-0.5">
                          {topic.description}
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-4 bg-slate-50 border border-slate-200/80 rounded-lg text-sm text-slate-500 italic">
                  {searchQuery
                    ? "No discussion points matching your search query."
                    : "No discussion points detected in this meeting."}
                </div>
              )}
            </div>
          </section>

          {/* 4. YOUR NOTES SECTION (PRIVATE ENTERPRISE NOTES) */}
          <section className="pt-2">
            <div className="flex items-center justify-between pb-2 mb-4 border-b border-slate-100">
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900 tracking-tight">
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
                  placeholder="Type your private notes here..."
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
                    You did not take any notes in this meeting
                  </span>
                )}
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
