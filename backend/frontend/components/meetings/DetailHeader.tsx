"use client";

import React, { useState } from "react";
import Link from "next/link";
import {
  ChevronLeft,
  Download,
  Send,
  Share2,
  Folder,
  Calendar,
  Clock,
  Video,
  Users,
  ChevronDown,
  Check
} from "lucide-react";
import { MeetingIntelligence } from "./types";

interface DetailHeaderProps {
  meeting: MeetingIntelligence;
  activeTab: "Recap" | "Transcript" | "Deep Dive";
  onTabChange: (tab: "Recap" | "Transcript" | "Deep Dive") => void;
  folderName?: string;
}

export function DetailHeader({
  meeting,
  activeTab,
  onTabChange,
  folderName = "1 Folder"
}: DetailHeaderProps) {
  const [showParticipantsDropdown, setShowParticipantsDropdown] = useState(false);
  const [showPushDropdown, setShowPushDropdown] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  return (
    <header className="w-full bg-white pb-0">
      {/* ── TOP ROW: BACK + TITLE + FOLDER & ACTIONS ──────────────────────── */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 py-4 px-1">
        {/* Left: Back Arrow + Title + Folder Pill */}
        <div className="flex items-center gap-2.5 min-w-0 flex-wrap">
          <Link
            href="/meetings"
            className="text-slate-600 hover:text-slate-900 transition-colors shrink-0 cursor-pointer"
            title="Back to all meetings"
          >
            <ChevronLeft className="w-6 h-6 stroke-[2.2]" />
          </Link>

          <h1 className="text-2xl md:text-3xl font-bold text-slate-900 tracking-tight mb-2 truncate max-w-[750px]">
            {meeting.title}
          </h1>

          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-medium bg-slate-100/90 border border-slate-200 text-slate-600 shrink-0 cursor-pointer hover:bg-slate-200/70 transition-colors mb-2">
            <Folder className="w-3.5 h-3.5 text-slate-500" />
            <span>{folderName}</span>
          </div>
        </div>

        {/* Right: Action Buttons (Standard H-9, Rounded-LG) */}
        <div className="flex items-center gap-2.5 shrink-0">
          <button
            type="button"
            onClick={() => {
              const blob = new Blob([meeting.summary], { type: "text/plain" });
              const url = URL.createObjectURL(blob);
              const a = document.createElement("a");
              a.href = url;
              a.download = `${meeting.title.replace(/\s+/g, "_")}_Recap.txt`;
              a.click();
              URL.revokeObjectURL(url);
            }}
            className="h-9 px-3.5 rounded-lg text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            <Download className="w-4 h-4 text-slate-500" />
            <span>Download</span>
          </button>

          <div className="relative">
            <button
              type="button"
              onClick={() => setShowPushDropdown(!showPushDropdown)}
              className="h-9 px-3.5 rounded-lg text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Send className="w-3.5 h-3.5 text-slate-500" />
              <span>Push to...</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {showPushDropdown && (
              <div className="absolute right-0 mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-30 animate-in fade-in zoom-in-95">
                <button
                  type="button"
                  onClick={() => {
                    alert("Exporting to Notion...");
                    setShowPushDropdown(false);
                  }}
                  className="w-full px-4 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <span className="w-2 h-2 rounded-full bg-slate-800" />
                  Push to Notion
                </button>
                <button
                  type="button"
                  onClick={() => {
                    alert("Exporting to Slack...");
                    setShowPushDropdown(false);
                  }}
                  className="w-full px-4 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <span className="w-2 h-2 rounded-full bg-emerald-500" />
                  Push to Slack
                </button>
                <button
                  type="button"
                  onClick={() => {
                    alert("Exporting to HubSpot / Salesforce...");
                    setShowPushDropdown(false);
                  }}
                  className="w-full px-4 py-2 text-left text-xs font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2"
                >
                  <span className="w-2 h-2 rounded-full bg-orange-500" />
                  Push to HubSpot CRM
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            onClick={handleShare}
            className="h-9 px-3.5 rounded-lg text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
          >
            {isCopied ? (
              <>
                <Check className="w-4 h-4 text-emerald-600" />
                <span className="text-emerald-700 font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Share2 className="w-4 h-4 text-slate-500" />
                <span>Share</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* ── META ROW: DATE • TIME • SOURCE • PARTICIPANTS ─────────────────── */}
      <div className="flex flex-wrap items-center gap-2 text-sm text-slate-500 pb-4 select-none">
        <span className="flex items-center gap-1.5 text-slate-600 font-medium">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          {meeting.date}
        </span>

        <span className="text-slate-300 mx-1">•</span>

        <span className="flex items-center gap-1.5 text-slate-600">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          {meeting.timeRange}
        </span>

        <span className="text-slate-300 mx-1">•</span>

        <span className="flex items-center gap-1.5 text-slate-600">
          <Video className="w-3.5 h-3.5 text-slate-400" />
          {meeting.source}
        </span>

        <span className="text-slate-300 mx-1">•</span>

        {/* Participants with popup dropdown */}
        <div className="relative inline-block">
          <button
            type="button"
            onClick={() => setShowParticipantsDropdown(!showParticipantsDropdown)}
            className="flex items-center gap-1.5 text-slate-600 hover:text-slate-900 cursor-pointer font-medium"
          >
            <Users className="w-3.5 h-3.5 text-slate-400" />
            <span>
              {meeting.participants.slice(0, 3).join(", ")}
              {meeting.participants.length > 3 && (
                <span className="text-slate-500">
                  , +{meeting.participants.length - 3} more
                </span>
              )}
            </span>
            <ChevronDown className="w-3 h-3 text-slate-400" />
          </button>

          {showParticipantsDropdown && (
            <div className="absolute left-0 mt-1 w-64 bg-white border border-slate-200 rounded-lg shadow-lg p-3 z-30 animate-in fade-in">
              <div className="text-xs font-semibold text-slate-800 uppercase tracking-wider mb-2">
                Participants ({meeting.participants.length})
              </div>
              <div className="space-y-1.5 max-h-48 overflow-y-auto">
                {meeting.participants.map((person, idx) => (
                  <div
                    key={idx}
                    className="flex items-center gap-2 text-xs text-slate-700 py-1 px-1.5 hover:bg-slate-50 rounded"
                  >
                    <div className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center text-[10px] font-bold">
                      {person.charAt(0)}
                    </div>
                    <span>{person}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── TABS ROW: RECAP • TRANSCRIPT • DEEP DIVE ──────────────────────── */}
      <div className="flex border-b border-slate-200 w-full">
        {(["Recap", "Transcript", "Deep Dive"] as const).map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              type="button"
              onClick={() => onTabChange(tab)}
              className={`px-4 py-2 text-sm font-semibold transition-all cursor-pointer ${
                isActive
                  ? "border-b-2 border-indigo-600 text-indigo-700 -mb-[1px]"
                  : "text-slate-500 hover:text-slate-800 bg-transparent border-b-2 border-transparent -mb-[1px]"
              }`}
            >
              {tab}
            </button>
          );
        })}
      </div>
    </header>
  );
}
