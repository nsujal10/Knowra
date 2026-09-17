"use client";

import React from "react";
import {
  Gavel,
  CheckCircle2,
  Clock,
  ShieldCheck,
  Share2,
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

export default function MeetingDecisionsPage() {
  return (
    <div className="space-y-6">
      {/* ── METRIC CARDS (TOTAL DECISIONS, CONSENSUS LEVEL, AI VERIFIED) ───── */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
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
      <div className="space-y-4">
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
