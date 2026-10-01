"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { DECISIONS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import type { EnterpriseDecisionsResponse, EnterpriseDecisionItem } from "@/lib/types";
import {
  CheckSquare,
  CheckCircle2,
  Clock,
  Share2,
  Search,
  Video,
  ArrowRight,
  Sparkles,
  Quote,
  Check,
  RefreshCw,
  Filter,
  X,
  SendHorizontal,
  Layers,
  AlertCircle,
} from "lucide-react";
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "@/components/ui/toast";

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
  const router = useRouter();
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
    ai_verified: "Verified",
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

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;
    router.push(`/chat?q=${encodeURIComponent(search.trim())}`);
  };

  const handleShare = async (decision: EnterpriseDecisionItem) => {
    const textToCopy = `📌 Decision: ${decision.title}\n💬 Summary: ${decision.description}\n👤 Decided by: ${decision.decided_by || "Team"}\n📍 Meeting: ${decision.meeting_title || "Enterprise Sync"}\n⏱️ Time: ${decision.timestamp || "0:00"}`;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(textToCopy);
      }
      setCopiedId(decision.id);
      toast.success("Decision summary copied to clipboard");
      setTimeout(() => setCopiedId(null), 2500);
    } catch {
      setCopiedId(decision.id);
      toast.info("Decision copied");
      setTimeout(() => setCopiedId(null), 2500);
    }
  };

  const getCategoryBadgeClass = (category: string) => {
    switch (category?.toUpperCase()) {
      case "ARCHITECTURE":
        return "bg-blue-50 text-blue-700 border-blue-200/80";
      case "ENGINEERING":
        return "bg-indigo-50 text-indigo-700 border-indigo-200/80";
      case "PRODUCT":
        return "bg-purple-50 text-purple-700 border-purple-200/80";
      case "SECURITY":
        return "bg-amber-50 text-amber-700 border-amber-200/80";
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  const getStatusBadgeClass = (status: string) => {
    if (status === "APPROVED" || status === "CONFIRMED") {
      return "bg-emerald-50 text-emerald-700 border-emerald-200/80";
    }
    if (status === "SUPERSEDED") {
      return "bg-rose-50 text-rose-700 border-rose-200/80";
    }
    return "bg-sky-50 text-sky-700 border-sky-200/80";
  };

  return (
    <div className="w-full min-w-0 flex-1 overflow-x-hidden">
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-5 pb-16">
        {/* ── 1. ENTERPRISE PAGE HEADER ────────────────────────────────────────── */}
        <PageHeader
          title="Decisions"
          subtitle={`${metrics.confirmed_count} confirmed · ${metrics.total_decisions} total · Audited consensus & architectural resolutions`}
          icon={CheckSquare}
          statusDot={isFetching}
          badge={
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              {metrics.total_decisions} Decisions
            </span>
          }
          actions={
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 shadow-xs transition-all cursor-pointer disabled:opacity-50"
              title="Refresh decisions from database"
            >
              <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
              <span>Sync Decisions</span>
            </button>
          }
        />

        {/* ── 2. METRIC KPI CARDS ───────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Total Decisions */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Total Decisions
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-3xl font-bold text-slate-900 tracking-tight">
                  {isLoading ? "—" : metrics.total_decisions}
                </span>
                <p className="text-[11px] text-slate-500 font-medium">
                  Across {meetingsList.length} meeting{meetingsList.length === 1 ? "" : "s"}
                </p>
              </div>
              <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
                <CheckSquare size={18} />
              </div>
            </div>
          </div>

          {/* Confirmed Consensus */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Confirmed Consensus
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-3xl font-bold text-emerald-600 tracking-tight">
                  {isLoading ? "—" : metrics.confirmed_count}
                </span>
                <p className="text-[11px] text-emerald-600 font-medium">
                  {metrics.consensus_level}
                </p>
              </div>
              <div className="bg-emerald-50 text-emerald-600 p-2 rounded-lg shrink-0">
                <CheckCircle2 size={18} />
              </div>
            </div>
          </div>

          {/* Review / Superseded */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Superseded / Updated
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-3xl font-bold text-slate-900 tracking-tight">
                  {isLoading ? "—" : metrics.superseded_count}
                </span>
                <p className="text-[11px] text-slate-500 font-medium">Archived revisions</p>
              </div>
              <div className="bg-slate-100 text-slate-600 p-2 rounded-lg shrink-0">
                <Clock size={18} />
              </div>
            </div>
          </div>

          {/* Categories */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Governance Domains
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-3xl font-bold text-slate-900 tracking-tight">
                  {CATEGORIES.length - 1}
                </span>
                <p className="text-[11px] text-indigo-600 font-medium">Arch, Eng, Security</p>
              </div>
              <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
                <Layers size={18} />
              </div>
            </div>
          </div>
        </div>

        {/* ── 3. UNIFIED SEARCH BAR ─────────────────────────────────────────── */}
        <form
          onSubmit={handleSearchSubmit}
          className="relative w-full border border-slate-200 hover:border-slate-300 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-500/10 rounded-xl flex items-center px-4 py-2.5 bg-white shrink-0 transition-all shadow-xs"
        >
          <Search className="w-4 h-4 text-slate-400 mr-3 shrink-0 pointer-events-none" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search decisions by keyword, stakeholder, or architectural topic..."
            className="flex-1 text-sm text-slate-800 placeholder:text-slate-400 bg-transparent border-0 outline-none ring-0 focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0 min-w-0"
            style={{ outline: "none", boxShadow: "none" }}
          />
          {search && (
            <button
              type="button"
              onClick={() => setSearch("")}
              className="text-slate-400 hover:text-slate-600 p-1 mr-2 rounded-full hover:bg-slate-100 transition-colors cursor-pointer shrink-0"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
          {!search && (
            <span className="hidden sm:flex items-center gap-1 text-[11px] text-slate-400 mr-3 shrink-0 select-none">
              <kbd className="px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200 text-[10px] font-mono">⌘K</kbd>
            </span>
          )}
          <button
            type="submit"
            disabled={!search.trim()}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
              search.trim()
                ? "bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs cursor-pointer active:scale-95"
                : "bg-slate-100 text-slate-400 cursor-default"
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Ask AI</span>
            <SendHorizontal className="w-3.5 h-3.5" />
          </button>
        </form>

        {/* ── 4. FILTER CONTROLS & TABS ─────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
          {/* Status Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto">
            {STATUS_FILTERS.map((status) => {
              const active = selectedStatus === status;
              return (
                <button
                  key={status}
                  type="button"
                  onClick={() => setSelectedStatus(status)}
                  className={`cursor-pointer transition-all px-3 py-1.5 rounded-lg text-xs font-semibold flex items-center gap-1.5 ${
                    active
                      ? "bg-indigo-50 text-indigo-700"
                      : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                  }`}
                >
                  <span>{status === "ALL" ? "All Decisions" : status === "APPROVED" ? "Confirmed" : "Superseded"}</span>
                </button>
              );
            })}
          </div>

          {/* Meeting Scoping Selector */}
          <div className="flex items-center gap-2 shrink-0">
            <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 text-xs text-slate-600">
              <Video size={13} className="text-slate-400 shrink-0" />
              <select
                value={selectedMeeting}
                onChange={(e) => setSelectedMeeting(e.target.value)}
                className="bg-transparent border-none text-xs font-medium text-slate-800 outline-none cursor-pointer max-w-[210px] truncate"
              >
                <option value="ALL">All Meetings ({metrics.total_decisions})</option>
                {meetingsList.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.title} ({m.decision_count})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Category Pills Row */}
        <div className="flex items-center gap-1.5 overflow-x-auto pb-1">
          <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mr-1 shrink-0">
            Category:
          </span>
          {CATEGORIES.map((cat) => {
            const active = selectedCategory === cat;
            return (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className={`px-3 py-1 rounded-full text-xs font-medium transition-all cursor-pointer whitespace-nowrap ${
                  active
                    ? "bg-slate-900 text-white shadow-2xs font-semibold"
                    : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"
                }`}
              >
                {cat === "ALL" ? "All Categories" : cat}
              </button>
            );
          })}
        </div>

        {/* ── 5. DECISIONS LIST ─────────────────────────────────────────────── */}
        {isLoading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((n) => (
              <div
                key={n}
                className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs animate-pulse space-y-3"
              >
                <div className="flex justify-between items-center">
                  <div className="flex gap-2">
                    <div className="h-5 w-24 bg-slate-200 rounded"></div>
                    <div className="h-5 w-20 bg-slate-200 rounded"></div>
                  </div>
                  <div className="h-4 w-12 bg-slate-200 rounded"></div>
                </div>
                <div className="h-6 w-3/4 bg-slate-200 rounded"></div>
                <div className="h-10 w-full bg-slate-100 rounded"></div>
              </div>
            ))}
          </div>
        ) : filteredDecisions.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-xs">
            <div className="bg-slate-50 text-slate-400 w-12 h-12 rounded-xl flex items-center justify-center mx-auto border border-slate-200">
              <CheckSquare size={22} />
            </div>
            <h3 className="text-base font-semibold text-slate-900">
              No decisions match your search
            </h3>
            <p className="text-xs text-slate-500 max-w-md mx-auto">
              {search
                ? `No decisions matching "${search}". Try adjusting your keywords or clearing the category and meeting filters.`
                : "No consensus decisions recorded for the selected criteria."}
            </p>
            {(search || selectedCategory !== "ALL" || selectedMeeting !== "ALL" || selectedStatus !== "ALL") && (
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  setSelectedCategory("ALL");
                  setSelectedMeeting("ALL");
                  setSelectedStatus("ALL");
                }}
                className="mt-2 inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors cursor-pointer"
              >
                <span>Reset all filters</span>
              </button>
            )}
          </div>
        ) : (
          <div className="space-y-3.5">
            {filteredDecisions.map((decision) => (
              <div
                key={decision.id}
                className="bg-white border border-slate-200 shadow-xs rounded-xl p-5 flex flex-col gap-3 hover:border-slate-300 hover:shadow-sm transition-all group"
              >
                {/* Header row with tags */}
                <div className="flex flex-wrap items-center justify-between gap-2.5">
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
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold text-slate-500 bg-slate-100 uppercase tracking-wider">
                        {decision.impact_level} IMPACT
                      </span>
                    )}

                    {decision.meeting_title && (
                      <Link
                        href={`/meetings/${decision.meeting_id}?tab=recap`}
                        className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-md text-[11px] font-medium bg-slate-50 text-slate-600 border border-slate-200 hover:text-indigo-600 hover:border-indigo-200 transition-colors"
                      >
                        <Video size={11} className="text-slate-400" />
                        <span className="max-w-[220px] truncate">{decision.meeting_title}</span>
                      </Link>
                    )}
                  </div>

                  <div className="text-slate-400 text-xs flex items-center gap-1 font-mono shrink-0">
                    <Clock size={12} />
                    <span>{decision.timestamp || "0:00"}</span>
                  </div>
                </div>

                {/* Title & Description */}
                <div className="space-y-1">
                  <h3 className="text-base font-semibold text-slate-900 tracking-tight group-hover:text-indigo-600 transition-colors">
                    {decision.title}
                  </h3>
                  <p className="text-slate-600 text-xs sm:text-sm leading-relaxed">
                    {decision.description}
                  </p>

                  {decision.rationale && (
                    <div className="mt-2 p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs text-slate-600 flex items-start gap-2">
                      <Sparkles size={13} className="text-indigo-500 shrink-0 mt-0.5" />
                      <div>
                        <strong className="font-semibold text-slate-700">Rationale: </strong>
                        <span>{decision.rationale}</span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Evidence Quote */}
                {decision.evidence_snippet && (
                  <div className="p-3 rounded-lg bg-indigo-50/40 border border-indigo-100 text-xs text-slate-700 space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-indigo-700 font-medium">
                      <span className="flex items-center gap-1">
                        <Quote size={11} className="rotate-180" />
                        <span>Transcript Anchor ({decision.timestamp})</span>
                      </span>
                      <span className="text-[10px] text-indigo-500 font-mono">
                        Provenanced
                      </span>
                    </div>
                    <p className="italic text-slate-700 font-sans pl-2.5 border-l-2 border-indigo-300">
                      &ldquo;{decision.evidence_snippet.trim()}&rdquo;
                    </p>
                  </div>
                )}

                {/* Card Footer */}
                <div className="border-t border-slate-100 pt-2.5 flex flex-wrap justify-between items-center gap-2 text-xs">
                  <div className="flex items-center gap-2 text-slate-500">
                    <div className="w-5 h-5 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-[10px]">
                      {(decision.decided_by || "T").charAt(0).toUpperCase()}
                    </div>
                    <span>
                      Decided by:{" "}
                      <strong className="text-slate-800 font-medium">
                        {decision.decided_by || "Leadership Team"}
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
                          <span className="text-emerald-600 font-semibold">Copied!</span>
                        </>
                      ) : (
                        <>
                          <Share2 size={13} />
                          <span>Share</span>
                        </>
                      )}
                    </button>

                    <Link
                      href={`/meetings/${decision.meeting_id}?tab=recap`}
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
    </div>
  );
}
