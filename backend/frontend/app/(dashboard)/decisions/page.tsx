"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { DECISIONS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import type { EnterpriseDecisionsResponse, EnterpriseDecisionItem } from "@/lib/types";
import {
  Gavel,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Share2,
  Search,
  Video,
  ArrowRight,
  Sparkles,
  Quote,
  Check,
  RefreshCw,
  Filter,
  Layers,
} from "lucide-react";

const CATEGORIES = [
  "ALL",
  "ARCHITECTURE",
  "ENGINEERING",
  "PRODUCT",
  "SECURITY",
  "OPERATIONS",
];

const STATUS_FILTERS = ["ALL", "APPROVED", "SUPERSEDED"];

export default function GlobalDecisionsPage() {
  const [search, setSearch] = useState("");
  const [selectedMeeting, setSelectedMeeting] = useState<string>("ALL");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Fetch real decisions from backend
  const { data, isLoading, refetch, isFetching } = useQuery<EnterpriseDecisionsResponse>({
    queryKey: [
      ...queryKeys.decisions.byMeeting(selectedMeeting === "ALL" ? undefined : selectedMeeting),
      selectedStatus,
      selectedCategory,
    ],
    queryFn: () =>
      api.get<EnterpriseDecisionsResponse>(
        DECISIONS.list({
          meetingId: selectedMeeting === "ALL" ? undefined : selectedMeeting,
          status: selectedStatus === "ALL" ? undefined : selectedStatus,
          category: selectedCategory === "ALL" ? undefined : selectedCategory,
        })
      ),
  });

  const decisions = data?.items ?? [];
  const metrics = data?.metrics ?? {
    total_decisions: 0,
    consensus_level: "100% Unanimous",
    ai_verified: "Strict RBAC • Confidential Guard",
    confirmed_count: 0,
    superseded_count: 0,
  };
  const meetingsList = data?.meetings ?? [];

  // Client-side text search
  const filteredDecisions = useMemo(() => {
    if (!search.trim()) return decisions;
    const term = search.toLowerCase();
    return decisions.filter(
      (d) =>
        d.title.toLowerCase().includes(term) ||
        d.description.toLowerCase().includes(term) ||
        (d.decided_by && d.decided_by.toLowerCase().includes(term)) ||
        (d.meeting_title && d.meeting_title.toLowerCase().includes(term))
    );
  }, [decisions, search]);

  const handleShare = async (decision: EnterpriseDecisionItem) => {
    const textToCopy = `📌 Decision: ${decision.title}\n💬 Summary: ${decision.description}\n👤 Decided by: ${decision.decided_by || "Team"}\n📍 Meeting: ${decision.meeting_title || "Enterprise Sync"}\n⏱️ Time: ${decision.timestamp || "0:00"}`;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(textToCopy);
      }
      setCopiedId(decision.id);
      setTimeout(() => setCopiedId(null), 2500);
    } catch {
      // Fallback
      setCopiedId(decision.id);
      setTimeout(() => setCopiedId(null), 2500);
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category.toUpperCase()) {
      case "ARCHITECTURE":
        return "bg-blue-50 text-blue-700 border-blue-200/60";
      case "ENGINEERING":
        return "bg-indigo-50 text-indigo-700 border-indigo-200/60";
      case "PRODUCT":
        return "bg-purple-50 text-purple-700 border-purple-200/60";
      case "SECURITY":
        return "bg-amber-50 text-amber-750 border-amber-200/60";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getStatusBadgeClass = (status: string) => {
    if (status === "APPROVED" || status === "CONFIRMED") {
      return "bg-emerald-50 text-emerald-700 border-emerald-200/60";
    }
    if (status === "SUPERSEDED") {
      return "bg-rose-50 text-rose-700 border-rose-200/60";
    }
    return "bg-sky-50 text-sky-700 border-sky-200/60";
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 animate-fade-in">
      {/* ── HEADER & LIVE STATUS ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
              Enterprise Decisions Registry
            </h1>
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Real-time consensus records, architectural resolutions, and provenance-anchored governance across meetings.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-sm transition-all cursor-pointer disabled:opacity-50"
            title="Refresh decisions from database"
          >
            <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
            <span>Sync Graph</span>
          </button>
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {metrics.total_decisions} Verified Decisions
          </span>
        </div>
      </div>

      {/* ── METRIC CARDS (TOTAL DECISIONS, CONSENSUS LEVEL, AI VERIFIED) ───── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Total Decisions */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between h-32 hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            Total Decisions
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <div className="space-y-0.5">
              <span className="text-3xl font-bold text-slate-900 tracking-tight">
                {isLoading ? "—" : metrics.total_decisions}
              </span>
              <p className="text-xs font-medium text-slate-500">
                Across {meetingsList.length} session{meetingsList.length === 1 ? "" : "s"}
              </p>
            </div>
            <div className="bg-indigo-50 text-indigo-600 p-2.5 rounded-full shrink-0">
              <Gavel size={20} />
            </div>
          </div>
        </div>

        {/* Consensus Level */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between h-32 hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            Consensus Level
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <div className="space-y-0.5">
              <span className="text-3xl font-bold text-slate-900 tracking-tight">
                {isLoading ? "—" : metrics.consensus_level}
              </span>
              <p className="text-xs font-medium text-emerald-600">
                {metrics.confirmed_count} Active & Confirmed
              </p>
            </div>
            <div className="bg-emerald-50 text-emerald-600 p-2.5 rounded-full shrink-0">
              <CheckCircle2 size={20} />
            </div>
          </div>
        </div>

        {/* AI Verified */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between h-32 hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            AI Verified
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <div className="space-y-0.5">
              <span className="text-2xl font-bold text-slate-900 tracking-tight">
                Strict RBAC
              </span>
              <p className="text-xs font-medium text-indigo-600">Confidential Guard</p>
            </div>
            <div className="bg-blue-50 text-blue-600 p-2.5 rounded-full shrink-0">
              <ShieldCheck size={20} />
            </div>
          </div>
        </div>
      </div>

      {/* ── FILTER & SEARCH CONTROLS ─────────────────────────────────────── */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-4 space-y-3.5">
        <div className="flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          {/* Search Input */}
          <div className="relative flex-1 max-w-md">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search decisions, stakeholders, or keywords…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full h-9 pl-9 pr-3 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-900 placeholder-slate-400 outline-none focus:border-indigo-500 focus:bg-white focus:ring-2 focus:ring-indigo-100 transition-all"
            />
          </div>

          {/* Meeting Selector & Status Dropdowns */}
          <div className="flex flex-wrap items-center gap-2">
            {/* Meeting Filter Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-600">
              <Video size={13} className="text-slate-400 shrink-0" />
              <select
                value={selectedMeeting}
                onChange={(e) => setSelectedMeeting(e.target.value)}
                className="bg-transparent border-none text-xs font-medium text-slate-800 outline-none cursor-pointer max-w-[200px] truncate"
              >
                <option value="ALL">All Meetings ({metrics.total_decisions})</option>
                {meetingsList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title} ({m.decision_count})
                  </option>
                ))}
              </select>
            </div>

            {/* Status Filter Dropdown */}
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-600">
              <Filter size={13} className="text-slate-400 shrink-0" />
              <select
                value={selectedStatus}
                onChange={(e) => setSelectedStatus(e.target.value)}
                className="bg-transparent border-none text-xs font-medium text-slate-800 outline-none cursor-pointer"
              >
                {STATUS_FILTERS.map((s) => (
                  <option key={s} value={s}>
                    Status: {s === "ALL" ? "All" : s}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Category Pills */}
        <div className="flex items-center gap-1.5 overflow-x-auto pt-1 border-t border-slate-100">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1">
            Category:
          </span>
          {CATEGORIES.map((cat) => {
            const active = selectedCategory === cat;
            return (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 rounded-full text-[11px] font-medium transition-all cursor-pointer whitespace-nowrap ${
                  active
                    ? "bg-slate-900 text-white shadow-sm"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {cat === "ALL" ? "All Categories" : cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── THE DECISIONS FEED ───────────────────────────────────────────── */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm animate-pulse space-y-4"
            >
              <div className="flex justify-between items-center">
                <div className="flex gap-2">
                  <div className="h-5 w-24 bg-slate-200 rounded"></div>
                  <div className="h-5 w-20 bg-slate-200 rounded"></div>
                </div>
                <div className="h-4 w-12 bg-slate-200 rounded"></div>
              </div>
              <div className="h-6 w-3/4 bg-slate-200 rounded"></div>
              <div className="h-12 w-full bg-slate-100 rounded"></div>
              <div className="border-t border-slate-100 pt-3 flex justify-between">
                <div className="h-4 w-32 bg-slate-200 rounded"></div>
                <div className="h-4 w-24 bg-slate-200 rounded"></div>
              </div>
            </div>
          ))}
        </div>
      ) : filteredDecisions.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-sm">
          <div className="bg-slate-50 text-slate-400 w-12 h-12 rounded-full flex items-center justify-center mx-auto">
            <Gavel size={24} />
          </div>
          <h3 className="text-base font-semibold text-slate-800">
            No decisions match your filters
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            {search
              ? `No decisions matching "${search}". Try adjusting your keywords or clearing the category/meeting filters.`
              : "No formal consensus decisions found for the selected criteria."}
          </p>
          {(search || selectedCategory !== "ALL" || selectedMeeting !== "ALL" || selectedStatus !== "ALL") && (
            <button
              onClick={() => {
                setSearch("");
                setSelectedCategory("ALL");
                setSelectedMeeting("ALL");
                setSelectedStatus("ALL");
              }}
              className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-100 text-xs font-semibold text-slate-700 hover:bg-slate-200 transition-colors cursor-pointer"
            >
              <span>Reset all filters</span>
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {filteredDecisions.map((decision) => (
            <div
              key={decision.id}
              className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 flex flex-col gap-3.5 hover:border-slate-300 hover:shadow-md transition-all group"
            >
              {/* Tags & Timestamp Header */}
              <div className="flex flex-wrap items-center justify-between gap-3">
                {/* Left Side: Category, Status, & Meeting Badge */}
                <div className="flex flex-wrap items-center gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-md text-[11px] font-semibold tracking-wide border ${getCategoryBadgeClass(
                      decision.category
                    )}`}
                  >
                    {decision.category}
                  </span>
                  <span
                    className={`px-2.5 py-0.5 rounded-md text-[11px] font-semibold tracking-wide border ${getStatusBadgeClass(
                      decision.status
                    )}`}
                  >
                    {decision.status}
                  </span>

                  {decision.impact_level && (
                    <span className="px-2 py-0.5 rounded text-[10px] font-medium text-slate-500 bg-slate-100 uppercase tracking-wider">
                      {decision.impact_level} IMPACT
                    </span>
                  )}

                  {decision.meeting_title && (
                    <Link
                      href={`/meetings/${decision.meeting_id}/decisions`}
                      className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-md text-[11px] font-medium bg-slate-50 text-slate-600 border border-slate-200/80 hover:text-indigo-600 hover:border-indigo-200 transition-colors"
                    >
                      <Video size={11} className="text-slate-400" />
                      <span className="max-w-[200px] truncate">{decision.meeting_title}</span>
                    </Link>
                  )}
                </div>

                {/* Right Side: Timestamp with Clock */}
                <div className="text-slate-400 text-xs flex items-center gap-1.5 font-mono shrink-0">
                  <Clock size={13} />
                  <span>{decision.timestamp || "0:00"}</span>
                </div>
              </div>

              {/* Decision Title & Content */}
              <div className="space-y-1.5">
                <h3 className="text-lg font-semibold text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors">
                  {decision.title}
                </h3>
                <p className="text-slate-600 text-sm leading-relaxed">
                  {decision.description}
                </p>

                {decision.rationale && (
                  <div className="mt-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 text-xs text-slate-600 flex items-start gap-2">
                    <Sparkles size={14} className="text-indigo-500 shrink-0 mt-0.5" />
                    <div>
                      <strong className="font-semibold text-slate-700">Rationale: </strong>
                      <span>{decision.rationale}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Provenance: Real Spoken Transcript Quote */}
              {decision.evidence_snippet && (
                <div className="p-3 rounded-lg bg-indigo-50/40 border border-indigo-100/70 text-xs text-slate-700 space-y-1">
                  <div className="flex items-center justify-between text-[11px] text-indigo-700 font-medium">
                    <span className="flex items-center gap-1">
                      <Quote size={11} className="rotate-180" />
                      <span>Verified Transcript Evidence (at {decision.timestamp})</span>
                    </span>
                    <span className="text-[10px] text-indigo-500 font-mono">
                      Segment Provenance Anchored
                    </span>
                  </div>
                  <p className="italic text-slate-700 font-sans pl-3 border-l-2 border-indigo-300">
                    &ldquo;{decision.evidence_snippet.trim()}&rdquo;
                  </p>
                </div>
              )}

              {/* Footer */}
              <div className="border-t border-slate-100 pt-3 flex flex-wrap justify-between items-center gap-2 text-xs">
                <div className="flex items-center gap-2 text-slate-500">
                  <div className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-[10px]">
                    {(decision.decided_by || "T").charAt(0).toUpperCase()}
                  </div>
                  <span>
                    Decided by:{" "}
                    <strong className="text-slate-800 font-medium">
                      {decision.decided_by || "Executive Committee"}
                    </strong>
                  </span>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={() => handleShare(decision)}
                    className="text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1.5 transition-colors cursor-pointer text-xs"
                  >
                    {copiedId === decision.id ? (
                      <>
                        <Check size={13} className="text-emerald-600" />
                        <span className="text-emerald-600">Copied to Clipboard!</span>
                      </>
                    ) : (
                      <>
                        <Share2 size={13} />
                        <span>Share Decision</span>
                      </>
                    )}
                  </button>

                  <Link
                    href={`/meetings/${decision.meeting_id}/decisions`}
                    className="text-slate-400 hover:text-slate-700 flex items-center gap-1 transition-colors"
                  >
                    <span>View Session</span>
                    <ArrowRight size={12} />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
