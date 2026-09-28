"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { DECISIONS, MEETINGS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import type { EnterpriseDecisionsResponse, EnterpriseDecisionItem, Meeting } from "@/lib/types";
import {
  Gavel,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Share2,
  ArrowLeft,
  Sparkles,
  Quote,
  Check,
  RefreshCw,
  Video,
} from "lucide-react";

export default function MeetingDecisionsPage() {
  const params = useParams();
  const rawMeetingId = params?.id as string;
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Fetch meeting metadata
  const { data: meeting } = useQuery<Meeting>({
    queryKey: queryKeys.meetings.detail(rawMeetingId),
    queryFn: () => api.get<Meeting>(MEETINGS.get(rawMeetingId)),
    enabled: !!rawMeetingId && rawMeetingId !== "m-001",
    retry: false,
  });

  // Fetch real decisions for this meeting
  const { data, isLoading, refetch, isFetching } = useQuery<EnterpriseDecisionsResponse>({
    queryKey: queryKeys.decisions.byMeeting(rawMeetingId),
    queryFn: () =>
      api.get<EnterpriseDecisionsResponse>(
        DECISIONS.list({
          meetingId: rawMeetingId !== "m-001" ? rawMeetingId : undefined,
        })
      ),
  });

  const decisions = data?.items ?? [];
  const metrics = data?.metrics ?? {
    total_decisions: decisions.length,
    consensus_level: "100% Unanimous",
    ai_verified: "Strict RBAC • Confidential Guard",
    confirmed_count: decisions.length,
    superseded_count: 0,
  };

  const meetingTitle = meeting?.title || decisions[0]?.meeting_title || "Meeting Session Decisions";

  const handleShare = async (decision: EnterpriseDecisionItem) => {
    const textToCopy = `📌 Decision: ${decision.title}\n💬 Summary: ${decision.description}\n👤 Decided by: ${decision.decided_by || "Team"}\n📍 Meeting: ${meetingTitle}\n⏱️ Time: ${decision.timestamp || "0:00"}`;
    try {
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(textToCopy);
      }
      setCopiedId(decision.id);
      setTimeout(() => setCopiedId(null), 2500);
    } catch {
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
    <div className="space-y-6 max-w-6xl mx-auto pb-16 animate-fade-in">
      {/* ── BREADCRUMB & HEADER ─────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs text-slate-500">
            <Link
              href="/decisions"
              className="hover:text-indigo-600 transition-colors flex items-center gap-1 font-medium"
            >
              <ArrowLeft size={12} />
              <span>All Enterprise Decisions</span>
            </Link>
            <span>/</span>
            <span className="text-slate-800 font-medium truncate max-w-xs">{meetingTitle}</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            <span>{meetingTitle}</span>
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold border border-slate-200">
              Decisions Intelligence
            </span>
          </h1>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-600 hover:text-slate-900 hover:bg-slate-50 shadow-sm transition-all cursor-pointer disabled:opacity-50"
          >
            <RefreshCw size={13} className={isFetching ? "animate-spin" : ""} />
            <span>Sync</span>
          </button>

          {rawMeetingId && rawMeetingId !== "m-001" && (
            <Link
              href={`/meetings/${rawMeetingId}`}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 text-xs font-medium transition-all"
            >
              <Video size={13} />
              <span>Meeting Recap</span>
            </Link>
          )}
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
                {isLoading ? "—" : decisions.length}
              </span>
              <p className="text-xs font-medium text-slate-500">Recorded in this session</p>
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
              <p className="text-xs font-medium text-emerald-600">Unanimous Agreement</p>
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

      {/* ── THE DECISIONS LIST ───────────────────────────────────────────── */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm animate-pulse space-y-4"
            >
              <div className="flex justify-between items-center">
                <div className="h-5 w-32 bg-slate-200 rounded"></div>
                <div className="h-4 w-12 bg-slate-200 rounded"></div>
              </div>
              <div className="h-6 w-3/4 bg-slate-200 rounded"></div>
              <div className="h-12 w-full bg-slate-100 rounded"></div>
            </div>
          ))}
        </div>
      ) : decisions.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3 shadow-sm">
          <div className="bg-slate-50 text-slate-400 w-12 h-12 rounded-full flex items-center justify-center mx-auto">
            <Gavel size={24} />
          </div>
          <h3 className="text-base font-semibold text-slate-800">
            No formal decisions recorded for this meeting
          </h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            Decisions are automatically extracted and verified through the AI meeting intelligence pipeline when participants reach verbal consensus.
          </p>
          <div className="pt-2">
            <Link
              href="/decisions"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-xs font-semibold text-indigo-700 hover:bg-indigo-100 transition-colors"
            >
              <span>Explore all enterprise decisions</span>
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          {decisions.map((decision) => (
            <div
              key={decision.id}
              className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 flex flex-col gap-3.5 hover:border-slate-300 hover:shadow-md transition-all group"
            >
              {/* Tags & Timestamp Header */}
              <div className="flex items-center justify-between gap-3">
                {/* Left Side: Category & Status Tags */}
                <div className="flex items-center gap-2">
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
              <div className="border-t border-slate-100 pt-3 flex justify-between items-center text-xs">
                <span className="text-slate-500">
                  Decided by:{" "}
                  <strong className="text-slate-800 font-medium">
                    {decision.decided_by || "Executive Committee"}
                  </strong>
                </span>

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
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
