"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useParams } from "next/navigation";
import { format, parseISO } from "date-fns";
import { cn, formatDuration } from "@/lib/utils";
import {
  MOCK_MEETINGS,
  MEETING_SOURCE,
  MOCK_ACTION_ITEMS,
  MOCK_DECISIONS,
} from "@/lib/data/mock";
import {
  ArrowLeft,
  Share2,
  Download,
  Sparkles,
  Users,
  Clock,
  Calendar,
  Search,
} from "lucide-react";

export default function MeetingDetailLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const id = (params?.id as string) ?? "m-001";

  const meeting =
    MOCK_MEETINGS.find((m) => m.id === id) ?? {
      ...MOCK_MEETINGS[0],
      id,
      title: "Q4 Product Roadmap Planning",
    };

  const tabs = [
    { id: "recap", label: "Recap", href: `/meetings/${id}/recap` },
    { id: "transcript", label: "Transcript", href: `/meetings/${id}/transcript` },
    { id: "decisions", label: "Decisions", href: `/meetings/${id}/decisions`, count: MOCK_DECISIONS.length },
    { id: "actions", label: "Action Items", href: `/meetings/${id}/actions`, count: MOCK_ACTION_ITEMS.length },
  ];

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16 font-sans animate-fade-in">
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
              {meeting.title}
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
            const isActive = pathname.startsWith(tab.href);
            return (
              <Link
                key={tab.id}
                href={tab.href}
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
              </Link>
            );
          })}
        </div>
      </div>

      {/* Children Tab Content */}
      <div className="pt-2">
        {children}
      </div>
    </div>
  );
}
