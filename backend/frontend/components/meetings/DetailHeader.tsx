"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
  Check,
  MoreHorizontal,
  Trash2,
  Loader2,
  FileText
} from "lucide-react";
import { MeetingIntelligence } from "./types";
import { DeleteMeetingModal } from "./DeleteMeetingModal";
import { api } from "@/lib/api/client";

interface DetailHeaderProps {
  meeting: MeetingIntelligence;
  activeTab: "Recap" | "Transcript";
  onTabChange: (tab: "Recap" | "Transcript") => void;
  folderName?: string;
  meetingId?: string;
}

export function DetailHeader({
  meeting,
  activeTab,
  onTabChange,
  folderName = "1 Folder",
  meetingId,
}: DetailHeaderProps) {
  const router = useRouter();
  const [showParticipantsDropdown, setShowParticipantsDropdown] = useState(false);
  const [showPushDropdown, setShowPushDropdown] = useState(false);
  const [showDownloadDropdown, setShowDownloadDropdown] = useState(false);
  const [showMoreDropdown, setShowMoreDropdown] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [isDownloadingVideo, setIsDownloadingVideo] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isCopied, setIsCopied] = useState(false);

  const handleShare = () => {
    if (typeof window !== "undefined") {
      navigator.clipboard.writeText(window.location.href);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  const handleDownloadRecap = () => {
    const blob = new Blob([meeting.summary], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${meeting.title.replace(/\s+/g, "_")}_Recap.txt`;
    a.click();
    URL.revokeObjectURL(url);
    setShowDownloadDropdown(false);
  };

  const handleDownloadVideo = async () => {
    setIsDownloadingVideo(true);
    const id = meetingId || "sample-meeting-id";
    try {
      const res = await api.get<{ downloadUrl: string; filename?: string }>(
        `/meetings/${id}/media/download`
      );
      if (res?.downloadUrl) {
        const a = document.createElement("a");
        a.href = res.downloadUrl;
        a.download = res.filename || `${meeting.title.replace(/\s+/g, "_")}.mp4`;
        a.target = "_blank";
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
      } else {
        alert("Video stream is currently unavailable for this meeting.");
      }
    } catch (err) {
      console.error("Failed to download video:", err);
      alert("Could not generate video download link. Please try again.");
    } finally {
      setIsDownloadingVideo(false);
      setShowDownloadDropdown(false);
    }
  };

  const handleConfirmDelete = async () => {
    setIsDeleting(true);
    const id = meetingId || "sample-meeting-id";
    try {
      await api.delete(`/meetings/${id}`);
    } catch (err) {
      console.warn("Backend delete request finished:", err);
    } finally {
      setIsDeleting(false);
      setIsDeleteModalOpen(false);
      router.push("/meetings");
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
          {/* Download Dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowDownloadDropdown(!showDownloadDropdown)}
              className="h-9 px-3.5 rounded-lg text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
            >
              <Download className="w-4 h-4 text-slate-500" />
              <span>Download</span>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
            </button>

            {showDownloadDropdown && (
              <div className="absolute right-0 mt-1.5 w-52 bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-30 animate-in fade-in zoom-in-95">
                <button
                  type="button"
                  disabled={isDownloadingVideo}
                  onClick={handleDownloadVideo}
                  className="w-full px-3.5 py-2 text-left text-xs font-medium text-slate-700 hover:bg-indigo-50/70 hover:text-indigo-600 flex items-center gap-2.5 transition-colors cursor-pointer disabled:opacity-50"
                >
                  {isDownloadingVideo ? (
                    <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-600" />
                  ) : (
                    <Video className="w-3.5 h-3.5 text-slate-500" />
                  )}
                  <span>{isDownloadingVideo ? "Preparing download..." : "Download Video (.mp4)"}</span>
                </button>

                <button
                  type="button"
                  onClick={handleDownloadRecap}
                  className="w-full px-3.5 py-2 text-left text-xs font-medium text-slate-700 hover:bg-indigo-50/70 hover:text-indigo-600 flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <FileText className="w-3.5 h-3.5 text-slate-500" />
                  <span>Download Summary (.txt)</span>
                </button>
              </div>
            )}
          </div>

          {/* Push to... Dropdown */}
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
              <div className="absolute right-0 mt-1.5 w-48 bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-30 animate-in fade-in zoom-in-95">
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

          {/* Share Button */}
          <button
            type="button"
            onClick={handleShare}
            className="h-9 px-3.5 rounded-lg text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
            title="Copy link to meeting"
          >
            {isCopied ? (
              <>
                <Check className="w-4 h-4 text-emerald-600" />
                <span className="text-emerald-600 font-semibold">Copied!</span>
              </>
            ) : (
              <>
                <Share2 className="w-4 h-4 text-slate-500" />
                <span>Share</span>
              </>
            )}
          </button>

          {/* 3-Dot More Menu (Delete Meeting) */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowMoreDropdown(!showMoreDropdown)}
              className="h-9 px-2.5 rounded-lg text-sm font-medium border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 shadow-2xs flex items-center justify-center transition-colors cursor-pointer"
              title="More actions"
            >
              <MoreHorizontal className="w-4 h-4 text-slate-600" />
            </button>

            {showMoreDropdown && (
              <div className="absolute right-0 mt-1.5 w-48 bg-white border border-slate-200 rounded-xl shadow-xl py-1.5 z-30 animate-in fade-in zoom-in-95">
                <button
                  type="button"
                  onClick={() => {
                    setIsDeleteModalOpen(true);
                    setShowMoreDropdown(false);
                  }}
                  className="w-full px-3.5 py-2 text-left text-xs font-medium text-rose-600 hover:bg-rose-50 flex items-center gap-2.5 transition-colors cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5 text-rose-500" />
                  <span>Delete Meeting</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── BOTTOM ROW: METADATA CHIPS & PILL TABS ───────────────────────── */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 pb-3 pt-1">
        {/* Left: Metadata Badges (Date, Time, Source, Participants) */}
        <div className="flex items-center gap-4 text-xs text-slate-500 flex-wrap">
          <div className="flex items-center gap-1.5 font-medium">
            <Calendar className="w-3.5 h-3.5 text-slate-400" />
            <span>{meeting.date}</span>
          </div>

          <div className="flex items-center gap-1.5 font-medium">
            <Clock className="w-3.5 h-3.5 text-slate-400" />
            <span>{meeting.timeRange}</span>
          </div>

          <div className="flex items-center gap-1.5 font-medium">
            <Video className="w-3.5 h-3.5 text-slate-400" />
            <span>{meeting.source}</span>
          </div>

          {/* Interactive Participants Pill */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowParticipantsDropdown(!showParticipantsDropdown)}
              className="flex items-center gap-1.5 font-medium text-slate-700 hover:text-indigo-600 bg-slate-100 hover:bg-indigo-50 px-2 py-0.5 rounded-full transition-colors cursor-pointer"
            >
              <Users className="w-3.5 h-3.5 text-slate-500" />
              <span>{meeting.participants.length} Participants</span>
              <ChevronDown className="w-3 h-3 text-slate-400" />
            </button>

            {showParticipantsDropdown && (
              <div className="absolute left-0 mt-1 w-56 bg-white border border-slate-200 rounded-lg shadow-lg p-2 z-30 animate-in fade-in">
                <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider px-2 py-1">
                  Attendees
                </p>
                <div className="divide-y divide-slate-100">
                  {meeting.participants.map((p, idx) => (
                    <div key={idx} className="flex items-center gap-2 py-1.5 px-2 text-xs text-slate-800">
                      <div className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-700 flex items-center justify-center font-bold text-[10px]">
                        {p.split(" ").map((n) => n[0]).join("")}
                      </div>
                      <span>{p}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Right: Pill-Based Navigation Tabs */}
        <div className="flex items-center gap-1 bg-slate-100/90 p-1 rounded-lg border border-slate-200/80 self-start md:self-auto">
          {(["Recap", "Transcript"] as const).map((tab) => {
            const isActive = activeTab === tab;
            return (
              <button
                key={tab}
                type="button"
                onClick={() => onTabChange(tab)}
                className={`px-3.5 py-1 text-xs font-semibold rounded-md transition-all cursor-pointer ${
                  isActive
                    ? "bg-white text-indigo-700 shadow-2xs font-bold"
                    : "text-slate-600 hover:text-slate-900 hover:bg-slate-200/50"
                }`}
              >
                {tab}
              </button>
            );
          })}
        </div>
      </div>

      {/* Confirmation Modal for Delete Meeting */}
      <DeleteMeetingModal
        isOpen={isDeleteModalOpen}
        meetingTitle={meeting.title}
        isDeleting={isDeleting}
        onClose={() => setIsDeleteModalOpen(false)}
        onConfirm={handleConfirmDelete}
      />
    </header>
  );
}
