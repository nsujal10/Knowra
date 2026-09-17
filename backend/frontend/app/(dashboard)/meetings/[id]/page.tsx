"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  Download,
  Share2,
  Sparkles,
  Search,
  Users,
  Clock,
  Calendar,
  CheckCircle2,
  Gavel,
  ShieldCheck,
  Tag,
} from "lucide-react";

interface DecisionItem {
  id: string;
  title: string;
  description: string;
  category: string;
  status: "APPROVED" | "PENDING" | "REJECTED";
  timestamp: string;
  decidedBy: string;
}

const MOCK_DECISIONS_DATA: DecisionItem[] = [
  {
    id: "dec-1",
    title: "Pinecone confirmed as vector database for Q4",
    description: "After brief re-evaluation of Weaviate, the team locked Pinecone for Q4 to avoid roadmap disruption. A Q1 architectural review will be scheduled with proper load data.",
    category: "ARCHITECTURE",
    status: "APPROVED",
    timestamp: "2:40",
    decidedBy: "Sujal Nage",
  },
  {
    id: "dec-2",
    title: "Mobile experience to be showcased at October summit",
    description: "The React Native offline-first prototype is ready for a summit showcase. This feature will be highlighted as a key enterprise differentiator.",
    category: "ARCHITECTURE",
    status: "APPROVED",
    timestamp: "3:57",
    decidedBy: "Sujal Nage",
  },
  {
    id: "dec-3",
    title: "LLM provider risk review before October go-live",
    description: "A dedicated risk assessment session will be held before the new LLM provider goes live in October, ensuring strict compliance and zero data leakage.",
    category: "ARCHITECTURE",
    status: "APPROVED",
    timestamp: "4:52",
    decidedBy: "Sujal Nage",
  },
];

export default function MeetingDetailPage() {
  const params = useParams();
  const meetingId = (params?.id as string) ?? "m-001";
  const [activeTab, setActiveTab] = useState<string>("decisions");

  const tabs = [
    { id: "recap", label: "Recap" },
    { id: "transcript", label: "Transcript" },
    { id: "decisions", label: "Decisions", count: MOCK_DECISIONS_DATA.length },
    { id: "actions", label: "Action Items", count: 5 },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 font-sans">
      {/* ── TOP NAV / SEARCH ───────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        {/* Breadcrumb Navigation */}
        <Link
          href="/meetings"
          className="text-slate-500 hover:text-slate-900 flex items-center gap-1.5 text-sm font-medium transition-colors group"
        >
          <ArrowLeft size={16} className="group-hover:-translate-x-0.5 transition-transform" />
          <span>Back to all meetings</span>
        </Link>

        {/* Sleek Search Bar */}
        <div className="relative">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            type="text"
            placeholder="Search meetings, decisions…"
            className="bg-slate-50 border border-slate-200 rounded-full pl-9 pr-4 py-2 text-sm text-slate-600 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white w-80 transition-all shadow-2xs"
          />
        </div>
      </div>

      {/* ── MEETING HEADER CARD ────────────────────────────────────────────── */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-3">
            {/* Soft Enterprise Badges */}
            <div className="flex items-center gap-2.5 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 ring-1 ring-indigo-600/20">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
                Microsoft Teams
              </span>
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 ring-1 ring-emerald-600/20">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                AI Processed
              </span>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-100 text-slate-600 ring-1 ring-slate-200">
                <Clock size={12} className="text-slate-400" />
                1:02:00
              </span>
            </div>

            {/* Commanding Title */}
            <h1 className="text-3xl font-bold text-slate-900 tracking-tight mt-2">
              Q4 Product Roadmap Planning
            </h1>

            {/* Clear Metadata Row */}
            <div className="text-sm text-slate-500 flex items-center gap-4 mt-2 flex-wrap">
              <span className="flex items-center gap-1.5">
                <Calendar size={14} className="text-slate-400" />
                Wednesday, September 16, 2026 · 2:30 PM
              </span>
              <span className="text-slate-300">•</span>
              <span className="flex items-center gap-1.5">
                <Users size={14} className="text-slate-400" />
                8 Participants
              </span>
              <span className="text-slate-300">•</span>
              <span>Host: <strong className="text-slate-700 font-medium">Sujal Nage</strong></span>
            </div>
          </div>

          {/* Action Buttons (Uniform Standard Height) */}
          <div className="flex items-center gap-2.5 shrink-0 self-start md:self-auto">
            <button
              type="button"
              className="h-9 px-4 rounded-md text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Download size={14} />
              <span>Export</span>
            </button>
            <button
              type="button"
              className="h-9 px-4 rounded-md text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Share2 size={14} />
              <span>Share</span>
            </button>
            <button
              type="button"
              className="h-9 px-4 rounded-md text-sm font-medium bg-indigo-600 hover:bg-indigo-700 text-white shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Sparkles size={14} />
              <span>Ask AI</span>
            </button>
          </div>
        </div>

        {/* ── TABS ROW ── */}
        <div className="border-b border-slate-200 pt-3 flex items-center gap-8">
          {tabs.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "pb-3 text-sm transition-colors flex items-center gap-1.5 cursor-pointer",
                  isActive
                    ? "border-b-2 border-indigo-600 text-indigo-600 font-semibold -mb-px"
                    : "text-slate-500 hover:text-slate-700 font-medium"
                )}
              >
                <span>{tab.label}</span>
                {tab.count !== undefined && (
                  <span
                    className={cn(
                      "px-1.5 py-0.5 rounded-full text-xs font-semibold",
                      isActive ? "bg-indigo-50 text-indigo-700" : "bg-slate-100 text-slate-500"
                    )}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── METRIC CARDS (TOTAL DECISIONS, CONSENSUS LEVEL, AI VERIFIED) ───── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
        {/* Total Decisions */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between h-32">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            Total Decisions
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <span className="text-3xl font-bold text-slate-900 tracking-tight">
              {MOCK_DECISIONS_DATA.length}
            </span>
            <div className="bg-indigo-50 text-indigo-600 p-2.5 rounded-full shrink-0">
              <Gavel size={20} />
            </div>
          </div>
        </div>

        {/* Consensus Level */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between h-32">
          <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
            Consensus Level
          </span>
          <div className="flex items-baseline justify-between mt-1">
            <div className="space-y-0.5">
              <span className="text-3xl font-bold text-slate-900 tracking-tight">
                100%
              </span>
              <p className="text-xs font-medium text-emerald-600">Unanimous</p>
            </div>
            <div className="bg-emerald-50 text-emerald-600 p-2.5 rounded-full shrink-0">
              <CheckCircle2 size={20} />
            </div>
          </div>
        </div>

        {/* AI Verified */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col justify-between h-32">
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

      {/* ── THE DECISIONS LIST (DOMAIN MODEL INTEGRATION) ──────────────────── */}
      <div className="space-y-4 mt-6">
        {MOCK_DECISIONS_DATA.map((decision) => (
          <div
            key={decision.id}
            className="bg-white border border-slate-200 shadow-sm rounded-xl p-6 mb-4 flex flex-col gap-3 hover:border-slate-300 transition-all"
          >
            {/* Tags & Timestamp Header */}
            <div className="flex items-center justify-between gap-3">
              {/* Left Side: Category & Status Tags */}
              <div className="flex items-center gap-2">
                <span className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-blue-50 text-blue-700 tracking-wide">
                  {decision.category}
                </span>
                <span className="px-2.5 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-50 text-emerald-700 tracking-wide">
                  {decision.status}
                </span>
              </div>

              {/* Right Side: Timestamp with Clock */}
              <div className="text-slate-400 text-sm flex items-center gap-1.5 font-mono">
                <Clock size={14} />
                <span>{decision.timestamp}</span>
              </div>
            </div>

            {/* Decision Content */}
            <div className="space-y-1.5">
              <h3 className="text-lg font-semibold text-slate-900 tracking-tight">
                {decision.title}
              </h3>
              <p className="text-slate-600 text-sm leading-relaxed">
                {decision.description}
              </p>
            </div>

            {/* Footer */}
            <div className="border-t border-slate-100 pt-3 mt-2 flex justify-between items-center text-sm">
              <span className="text-slate-500">
                Decided by: <strong className="text-slate-700 font-medium">{decision.decidedBy}</strong>
              </span>
              <button
                type="button"
                onClick={() => alert(`Sharing decision: ${decision.title}`)}
                className="text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1.5 transition-colors cursor-pointer text-sm"
              >
                <Share2 size={13} />
                <span>Share Decision</span>
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
