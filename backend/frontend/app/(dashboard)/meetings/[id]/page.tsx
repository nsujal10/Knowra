"use client";

import React, { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { Sparkles } from "lucide-react";
import { DetailHeader } from "@/components/meetings/DetailHeader";
import { IntelligenceFeed } from "@/components/meetings/IntelligenceFeed";
import { MediaSidebar } from "@/components/meetings/MediaSidebar";
import { RagChatDrawer } from "@/components/meetings/RagChatDrawer";
import { TranscriptTab } from "@/components/meetings/TranscriptTab";
import { api } from "@/lib/api/client";

// ============================================================================
// 1. DOMAIN MODELS (PHASE 13, 15, 16 ARCHITECTURE MAPPING)
// ============================================================================

export interface ActionItem {
  id: string;
  owner: string;
  text: string;
  timestampSeconds: number;
}

export interface DiscussionPoint {
  id: string;
  title: string;
  summary: string;
  timestampSeconds: number;
}

export interface Chapter {
  id: string;
  title: string;
  timestampSeconds: number;
  durationStr: string;
}

export interface Metric {
  score: number;
  label: string;
  status: "GOOD" | "NEUTRAL" | "WARNING" | "CRITICAL";
  trend: number[];
}

export interface MeetingIntelligence {
  title: string;
  date: string;
  timeRange: string;
  source: "Zoom" | "Teams" | "Google Meet" | "Upload";
  participants: string[];
  metrics: {
    report: Metric;
    engagement: Metric;
    sentiment: Metric;
  };
  summary: string;
  actionItems: ActionItem[];
  discussionPoints: DiscussionPoint[];
  chapters: Chapter[];
}

// ============================================================================
// 2. PRODUCTION-GRADE MOCK PAYLOAD (MATCHING REFERENCE IMAGE & CONTRACT)
// ============================================================================

const DEFAULT_MEETING_DATA: MeetingIntelligence = {
  title: "Onboarding to Knowra AI - Sample Meeting",
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
      label: "Meeting Score",
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
    "Alison and the team introduced Knowra AI's onboarding process, covering how to connect calendars, access account settings, and manage integrations. They explained join and distribution settings: Knowra AI can auto-join all calendar events by default, with options to toggle per meeting and to limit automatic sharing of notes to internal participants. The team demonstrated how to connect additional platforms (notably CRM like HubSpot or Salesforce) to enable Search Copilot and auto-push meeting notes. They showed where to find meetings, organize them in folders, and how to share or restrict access during testing.",
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
      title: "Knowra AI Onboarding Essentials",
      summary:
        "Alison and the team introduced Knowra AI's onboarding process, covering how to connect calendars, access account settings, and manage integrations. They explained join and distribution settings: Knowra AI can auto-join all calendar events by default, with options to toggle per meeting and to limit automatic sharing of notes to internal participants. The team demonstrated how to connect additional platforms (notably CRM like HubSpot or Salesforce) to enable Search Copilot and auto-push meeting notes. They showed where to find meetings, organize them in folders, and how to share or restrict access during testing.",
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
      title: "Knowra AI Onboarding Essentials",
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
// 3. MAIN PAGE COMPONENT (TWO-COLUMN SCROLLING PHYSICS)
// ============================================================================

export default function MeetingDetailPage() {
  const params = useParams();
  const meetingId = (params?.id as string) || "sample-meeting-id";

  const [activeTab, setActiveTab] = useState<"Recap" | "Transcript">("Recap");
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
          let dateStr = "Jan 2, 2026";
          let timeRangeStr = "2:30 AM - 4:15 AM";
          try {
            const d = new Date(res.created_at);
            dateStr = d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
            timeRangeStr = d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
          } catch {}

          setMeetingData((prev) => ({
            ...prev,
            title: res.title,
            date: dateStr,
            timeRange: timeRangeStr,
            source: (res.source === "GOOGLE_MEET" ? "Google Meet" : res.source === "TEAMS" ? "Teams" : "Zoom") as any
          }));

          // Dynamically populate actual meeting participants from transcript
          try {
            const transRes = await api.get<{
              segments: Array<{
                speaker?: { displayName?: string | null; label?: string | null };
              }>;
            }>(`/meetings/${meetingId}/transcript`);

            if (transRes?.segments && transRes.segments.length > 0) {
              const uniqueSpeakers = Array.from(
                new Set(
                  transRes.segments
                    .map((s) => s.speaker?.displayName || s.speaker?.label)
                    .filter((n): n is string => Boolean(n && !n.startsWith("SPEAKER_")))
                )
              );
              if (uniqueSpeakers.length > 0) {
                setMeetingData((prev) => ({
                  ...prev,
                  participants: uniqueSpeakers,
                }));
              }
            }
          } catch {}
        }
      } catch {
        // Graceful fallback to rich mock data
      }
    }
    const isUuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(meetingId);
    if (isUuid) {
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
    <div className="w-full h-full min-h-0 flex flex-col">
      {/* ── 1. TOP HEADER & NAVIGATION (FIXED SHRINK-0) ─────────────────── */}
      <div className="shrink-0">
        <DetailHeader
          meeting={meetingData}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          folderName="1 Folder"
          meetingId={meetingId}
        />
      </div>

      {/* ── 2. TWO-COLUMN RESPONSIVE LAYOUT (RECAP & TRANSCRIPT VIEWS) ───── */}
      {(activeTab === "Recap" || activeTab === "Transcript") && (
        <div className="flex-1 min-h-0 flex flex-col lg:flex-row gap-6 lg:gap-8 overflow-hidden pt-3">
          {/* LEFT COLUMN: SCROLLABLE FEED */}
          <div className="flex-1 h-full min-w-0 overflow-y-auto pr-6 lg:pr-8 custom-scrollbar">
            {activeTab === "Recap" ? (
              <IntelligenceFeed
                meetingId={meetingId}
                onSeek={handleSeek}
                activeTimestamp={currentTime}
              />
            ) : (
              <TranscriptTab
                meetingId={meetingId}
                onTimeClick={handleSeek}
                activeTimestamp={currentTime}
              />
            )}
          </div>

          {/* RIGHT COLUMN: STICKY MEDIA PLAYER & CHAPTERS (STICKY) */}
          <div className="w-full lg:w-[420px] shrink-0 sticky top-0 lg:h-full flex flex-col">
            <MediaSidebar
              chapters={meetingData.chapters}
              currentTime={currentTime}
              duration={529} // 8:49
              isPlaying={isPlaying}
              onSeek={handleSeek}
              onTogglePlay={handleTogglePlay}
              meetingId={meetingId}
              onOpenChat={() => setIsChatOpen(true)}
            />
          </div>
        </div>
      )}



      {/* ── 5. RAG CHAT SLIDE-OVER DRAWER ────────────────────────────────── */}

      <RagChatDrawer
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        meetingId={meetingId}
        meetingTitle={meetingData.title}
        onSeek={handleSeek}
      />
    </div>
  );
}
