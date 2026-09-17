"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Sparkles, ArrowUp } from "lucide-react";
import { DetailHeader } from "@/components/meetings/DetailHeader";
import { IntelligenceFeed } from "@/components/meetings/IntelligenceFeed";
import { MediaSidebar } from "@/components/meetings/MediaSidebar";
import { RagChatDrawer } from "@/components/meetings/RagChatDrawer";
import { MeetingIntelligence } from "@/components/meetings/types";
import { api } from "@/lib/api/client";

// ============================================================================
// PRODUCTION-GRADE MOCK PAYLOAD (MATCHING REFERENCE IMAGE & CONTRACT)
// ============================================================================

const DEFAULT_MEETING_DATA: MeetingIntelligence = {
  title: "Onboarding to Read AI - Sample Report",
  date: "Jan 2, 2026",
  timeRange: "2:30 AM - 4:15 AM",
  source: "Google Meet",
  participants: [
    "Alison Barker",
    "Eliab Sisay",
    "Kelcey Hawthorne",
    "Sujal Nage",
    "David Sterling"
  ],
  metrics: {
    report: {
      score: 89,
      label: "Report Score",
      status: "GOOD",
      trend: [72, 78, 83, 87, 89]
    },
    engagement: {
      score: 84,
      label: "Engagement",
      status: "GOOD",
      trend: [68, 74, 80, 81, 84]
    },
    sentiment: {
      score: 91,
      label: "Sentiment",
      status: "GOOD",
      trend: [80, 83, 86, 89, 91]
    }
  },
  summary:
    "Alison and the team introduced Read AI's onboarding process, covering how to connect calendars, access account settings, and manage integrations. They explained join and distribution settings: Read AI can auto-join all calendar events by default, with options to toggle per meeting and to limit automatic sharing of notes to internal participants. The team demonstrated how to connect additional platforms (notably CRM like HubSpot or Salesforce) to enable Search Copilot and auto-push meeting notes. They showed where to find meeting reports, organize them in folders, and how to share or restrict access during testing.",
  actionItems: [
    {
      id: "act-1",
      owner: "Alison Barker",
      text: "Configure default calendar auto-join parameters to internal-only participants for all standard engineering syncs.",
      timestampSeconds: 0
    },
    {
      id: "act-2",
      owner: "Eliab Sisay",
      text: "Authenticate the HubSpot CRM webhook pipeline to automate sales transcript and note push.",
      timestampSeconds: 200
    },
    {
      id: "act-3",
      owner: "Kelcey Hawthorne",
      text: "Circulate Search Copilot permission boundary and cross-platform citation documentation to IT and Compliance.",
      timestampSeconds: 363
    }
  ],
  discussionPoints: [
    {
      id: "dp-1",
      title: "Read AI Onboarding Essentials",
      summary:
        "Alison and the team introduced Read AI's onboarding process, covering how to connect calendars, access account settings, and manage integrations. They explained join and distribution settings: Read AI can auto-join all calendar events by default, with options to toggle per meeting and to limit automatic sharing of notes to internal participants. The team demonstrated how to connect additional platforms (notably CRM like HubSpot or Salesforce) to enable Search Copilot and auto-push meeting notes. They showed where to find meeting reports, organize them in folders, and how to share or restrict access during testing.",
      timestampSeconds: 0
    },
    {
      id: "dp-2",
      title: "Exploring Search Copilot Capabilities",
      summary:
        "Kelcey and Alison demonstrate Search Copilot, highlighting how it can search across meetings, emails, Slack, Drive, and Teams to surface insights, with citations to trace back results. They note that results respect permissions and only search content the user has access to. The team discusses practical use cases, such as summarizing customer interviews and drafting follow-up communications, and how to share findings with teammates through folders. They point attendees to account settings and the support widget, with promises of sending follow-up documentation.",
      timestampSeconds: 363
    }
  ],
  chapters: [
    {
      id: "ch-1",
      title: "Read AI Onboarding Essentials",
      timestampSeconds: 0,
      durationStr: "6m"
    },
    {
      id: "ch-2",
      title: "Exploring Search Copilot Capabilities",
      timestampSeconds: 363,
      durationStr: "3m"
    }
  ]
};

// ============================================================================
// MAIN PAGE COMPONENT
// ============================================================================

export default function MeetingDetailPage() {
  const params = useParams();
  const meetingId = (params?.id as string) || "sample-meeting-id";

  const [activeTab, setActiveTab] = useState<"Recap" | "Transcript" | "Deep Dive">("Recap");
  const [meetingData, setMeetingData] = useState<MeetingIntelligence>(DEFAULT_MEETING_DATA);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isChatOpen, setIsChatOpen] = useState<boolean>(false);

  // Fetch live meeting metadata if available from backend
  useEffect(() => {
    async function loadBackendData() {
      try {
        const res = await api.get<{
          id: string;
          title: string;
          created_at: string;
          media_filename?: string;
          source?: string;
        }>(`/meetings/${meetingId}`);

        if (res && res.title) {
          setMeetingData((prev) => ({
            ...prev,
            title: res.title,
            source: (res.source === "GOOGLE_MEET" ? "Google Meet" : res.source === "TEAMS" ? "Teams" : "Zoom") as any
          }));
        }
      } catch {
        // Graceful fallback to rich mock data
      }
    }
    if (meetingId && meetingId !== "sample-meeting-id") {
      loadBackendData();
    }
  }, [meetingId]);

  // Phase 13 Canonical Transcript & Action Seeking handler
  const handleSeek = useCallback((seconds: number) => {
    setCurrentTime(seconds);
    setIsPlaying(true);
  }, []);

  const handleTogglePlay = useCallback(() => {
    setIsPlaying((prev) => !prev);
  }, []);

  const scrollToTop = () => {
    if (typeof window !== "undefined") {
      window.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  return (
    <div className="w-full min-w-0 bg-white rounded-xl border border-slate-200 shadow-xs px-6 py-4 flex flex-col gap-5">
      {/* ── 1. TOP HEADER & NAVIGATION ──────────────────────────────────── */}
      <DetailHeader
        meeting={meetingData}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        folderName="1 Folder"
      />

      {/* ── 2. TWO-COLUMN RESPONSIVE LAYOUT (RECAP VIEW) ─────────────────── */}
      {activeTab === "Recap" && (
        <div className="flex flex-col lg:flex-row gap-6 w-full pt-1">
          {/* LEFT COLUMN: LLM-EXTRACTED INTELLIGENCE FEED */}
          <IntelligenceFeed
            intelligence={meetingData}
            onSeek={handleSeek}
            activeTimestamp={currentTime}
          />

          {/* RIGHT COLUMN: STICKY MEDIA PLAYER & CHAPTERS */}
          <MediaSidebar
            chapters={meetingData.chapters}
            currentTime={currentTime}
            duration={529} // 8:49
            isPlaying={isPlaying}
            onSeek={handleSeek}
            onTogglePlay={handleTogglePlay}
          />
        </div>
      )}

      {/* ── 3. TRANSCRIPT VIEW TAB ───────────────────────────────────────── */}
      {activeTab === "Transcript" && (
        <div className="py-8 text-center text-slate-500 text-sm bg-slate-50 rounded-xl border border-slate-200">
          <p className="font-semibold text-slate-700">Canonical Speaker-Diarized Transcript</p>
          <p className="text-xs text-slate-500 mt-1">
            Audio transcript is synchronized with the video player. Click any timestamp to seek.
          </p>
          <button
            type="button"
            onClick={() => setActiveTab("Recap")}
            className="mt-4 px-4 py-1.5 text-xs font-semibold bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
          >
            Switch to Recap View
          </button>
        </div>
      )}

      {/* ── 4. DEEP DIVE VIEW TAB ────────────────────────────────────────── */}
      {activeTab === "Deep Dive" && (
        <div className="py-8 text-center text-slate-500 text-sm bg-slate-50 rounded-xl border border-slate-200">
          <p className="font-semibold text-slate-700">Intelligence Deep Dive &amp; Analytics</p>
          <p className="text-xs text-slate-500 mt-1">
            Cross-meeting correlation, knowledge graph extraction, and sentiment trends.
          </p>
          <button
            type="button"
            onClick={() => setActiveTab("Recap")}
            className="mt-4 px-4 py-1.5 text-xs font-semibold bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
          >
            Switch to Recap View
          </button>
        </div>
      )}

      {/* ── 5. FLOATING BACK-TO-TOP BUTTON ──────────────────────────────── */}
      <button
        type="button"
        onClick={scrollToTop}
        className="fixed bottom-20 right-6 w-9 h-9 rounded-full bg-white border border-slate-200 shadow-md flex items-center justify-center text-slate-500 hover:text-slate-800 hover:bg-slate-50 cursor-pointer z-40 transition-colors"
        title="Scroll to top"
      >
        <ArrowUp className="w-4 h-4" />
      </button>

      {/* ── 6. RAG CHAT FLOATING ACTION BUTTON (PHASE 22) ────────────────── */}
      <button
        type="button"
        onClick={() => setIsChatOpen(true)}
        className="fixed bottom-6 right-6 bg-indigo-600 hover:bg-indigo-700 text-white shadow-xl rounded-full px-5 py-3 flex items-center gap-2 font-medium text-sm transition-all hover:scale-105 cursor-pointer z-40"
        title="Ask Knowra about this meeting"
      >
        <Sparkles className="w-4 h-4" />
        <span>Ask Knowra</span>
      </button>

      {/* ── 7. RAG CHAT SLIDE-OVER DRAWER ────────────────────────────────── */}
      <RagChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        meetingId={meetingId}
        meetingTitle={meetingData.title}
      />
    </div>
  );
}
