"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import {
  Search,
  Globe,
  ChevronDown,
  RefreshCw,
  Upload,
  Calendar,
  Layers,
  ArrowUpDown,
  Users,
  Sparkles,
  Folder as FolderIcon,
  MoreHorizontal,
  SendHorizontal,
  Video,
  Clock
} from "lucide-react";
import { format, parseISO } from "date-fns";
import { UploadMeetingModal } from "@/components/meetings/UploadMeetingModal";

// ============================================================================
// 1. DOMAIN MODELS & TYPES
// ============================================================================

export type MeetingSource = "ZOOM" | "TEAMS" | "GOOGLE_MEET" | "UPLOAD";
export type ProcessingStatus = "COMPLETED" | "PROCESSING" | "FAILED" | "PENDING";

export interface MeetingFolder {
  id: string;
  name: string;
}

export interface MeetingOwner {
  id: string;
  name: string;
  email: string;
  initials: string;
}

export interface IntelligenceMetrics {
  decisionsCount: number;
  actionItemsCount: number;
  intelligenceScore: number;
}

export interface MockMeeting {
  id: string;
  title: string;
  status: ProcessingStatus;
  source: MeetingSource;
  scheduledStartTime: string;
  scheduledEndTime: string;
  participantCount: number;
  metrics: IntelligenceMetrics;
  folder: MeetingFolder;
  owner: MeetingOwner;
  thumbnailGradient: string;
  thumbnailFaceInitial: string;
  weekGroupKey: string;
}

// ============================================================================
// 2. MOCK DATA
// ============================================================================

const MOCK_MEETINGS: MockMeeting[] = [
  {
    id: "m-001",
    title: "Onboarding to Knowra Platform - Enterprise Architecture Deep Dive",
    status: "COMPLETED",
    source: "ZOOM",
    scheduledStartTime: "2026-01-02T02:30:00Z",
    scheduledEndTime: "2026-01-02T02:38:00Z",
    participantCount: 4,
    metrics: { decisionsCount: 5, actionItemsCount: 8, intelligenceScore: 89 },
    folder: { id: "f-1", name: "Sample Reports - Knowra" },
    owner: { id: "u-1", name: "Sujal Nage", email: "sujal.nage@softude.com", initials: "SN" },
    thumbnailGradient: "from-amber-700 via-stone-800 to-stone-900",
    thumbnailFaceInitial: "👩‍💼",
    weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026"
  },
  {
    id: "m-002",
    title: "Using a Meeting Intelligence Report - Executive Briefing",
    status: "COMPLETED",
    source: "ZOOM",
    scheduledStartTime: "2026-01-02T01:30:00Z",
    scheduledEndTime: "2026-01-02T01:34:00Z",
    participantCount: 4,
    metrics: { decisionsCount: 3, actionItemsCount: 6, intelligenceScore: 89 },
    folder: { id: "f-1", name: "Sample Reports - Knowra" },
    owner: { id: "u-2", name: "Elena Rostova", email: "elena.r@enterprise.io", initials: "ER" },
    thumbnailGradient: "from-stone-600 via-stone-700 to-slate-900",
    thumbnailFaceInitial: "👩",
    weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026"
  },
  {
    id: "m-003",
    title: "Try Out Ask Knowra - Natural Language Context Retrieval QA",
    status: "COMPLETED",
    source: "ZOOM",
    scheduledStartTime: "2026-01-02T00:30:00Z",
    scheduledEndTime: "2026-01-02T00:37:00Z",
    participantCount: 4,
    metrics: { decisionsCount: 7, actionItemsCount: 11, intelligenceScore: 88 },
    folder: { id: "f-1", name: "Sample Reports - Knowra" },
    owner: { id: "u-3", name: "Sarah Chen", email: "sarah.c@enterprise.io", initials: "SC" },
    thumbnailGradient: "from-amber-900 via-stone-800 to-stone-950",
    thumbnailFaceInitial: "👩‍🦰",
    weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026"
  },
  {
    id: "m-004",
    title: "Desktop and Mobile App Walkthrough - Multi-tenant Audio Ingestion",
    status: "COMPLETED",
    source: "TEAMS",
    scheduledStartTime: "2026-01-01T23:30:00Z",
    scheduledEndTime: "2026-01-01T23:34:00Z",
    participantCount: 4,
    metrics: { decisionsCount: 6, actionItemsCount: 4, intelligenceScore: 92 },
    folder: { id: "f-1", name: "Sample Reports - Knowra" },
    owner: { id: "u-4", name: "David Sterling", email: "david.s@enterprise.io", initials: "DS" },
    thumbnailGradient: "from-slate-700 via-indigo-950 to-stone-900",
    thumbnailFaceInitial: "👩‍💼",
    weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026"
  },
  {
    id: "m-005",
    title: "Explore Real World Use Cases - High-Concurrency Diarization Run",
    status: "COMPLETED",
    source: "ZOOM",
    scheduledStartTime: "2026-01-01T22:30:00Z",
    scheduledEndTime: "2026-01-01T22:38:00Z",
    participantCount: 4,
    metrics: { decisionsCount: 9, actionItemsCount: 14, intelligenceScore: 87 },
    folder: { id: "f-1", name: "Sample Reports - Knowra" },
    owner: { id: "u-1", name: "Sujal Nage", email: "sujal.nage@softude.com", initials: "SN" },
    thumbnailGradient: "from-emerald-950 via-teal-900 to-slate-900",
    thumbnailFaceInitial: "👩‍💻",
    weekGroupKey: "WEEK OF DEC 29–JAN 4, 2026"
  },
  {
    id: "m-006",
    title: "Cross-Department Alignment on Data Isolation & Tenant Partitioning",
    status: "PROCESSING",
    source: "TEAMS",
    scheduledStartTime: "2026-01-08T14:00:00Z",
    scheduledEndTime: "2026-01-08T14:45:00Z",
    participantCount: 8,
    metrics: { decisionsCount: 2, actionItemsCount: 5, intelligenceScore: 94 },
    folder: { id: "f-2", name: "Core Architecture" },
    owner: { id: "u-2", name: "Elena Rostova", email: "elena.r@enterprise.io", initials: "ER" },
    thumbnailGradient: "from-blue-900 via-indigo-950 to-slate-950",
    thumbnailFaceInitial: "👨‍💻",
    weekGroupKey: "WEEK OF JAN 5–JAN 11, 2026"
  },
  {
    id: "m-007",
    title: "Security Review: Ephemeral MinIO Token Rotation & Keycloak SSO",
    status: "PROCESSING",
    source: "GOOGLE_MEET",
    scheduledStartTime: "2026-01-07T11:00:00Z",
    scheduledEndTime: "2026-01-07T11:30:00Z",
    participantCount: 5,
    metrics: { decisionsCount: 4, actionItemsCount: 7, intelligenceScore: 91 },
    folder: { id: "f-3", name: "Infra & Security" },
    owner: { id: "u-3", name: "Sarah Chen", email: "sarah.c@enterprise.io", initials: "SC" },
    thumbnailGradient: "from-violet-950 via-slate-900 to-stone-900",
    thumbnailFaceInitial: "👩‍🔬",
    weekGroupKey: "WEEK OF JAN 5–JAN 11, 2026"
  }
];

// ============================================================================
// 3. SOURCE BADGE COMPONENT
// ============================================================================

function SourceBadge({ source }: { source: MeetingSource }) {
  if (source === "ZOOM") {
    return (
      <div
        className="w-5 h-5 rounded-full bg-white shadow-sm flex items-center justify-center p-0.5 border border-slate-100"
        title="Zoom Video"
      >
        <div className="w-3.5 h-3.5 bg-blue-500 rounded-sm flex items-center justify-center text-white">
          <Video className="w-2.5 h-2.5 text-white" />
        </div>
      </div>
    );
  }
  if (source === "TEAMS") {
    return (
      <div
        className="w-5 h-5 rounded-full bg-white shadow-sm flex items-center justify-center p-0.5 border border-slate-100"
        title="Microsoft Teams"
      >
        <div className="w-3.5 h-3.5 bg-[#4B53BC] rounded-sm flex items-center justify-center text-[7.5px] text-white font-bold">
          T
        </div>
      </div>
    );
  }
  if (source === "GOOGLE_MEET") {
    return (
      <div
        className="w-5 h-5 rounded-full bg-white shadow-sm flex items-center justify-center p-0.5 border border-slate-100"
        title="Google Meet"
      >
        <div className="w-3.5 h-3.5 bg-emerald-600 rounded-sm flex items-center justify-center text-[7.5px] text-white font-bold">
          M
        </div>
      </div>
    );
  }
  return (
    <div
      className="w-5 h-5 rounded-full bg-white shadow-sm flex items-center justify-center p-0.5 border border-slate-100"
      title="Uploaded Audio/Video"
    >
      <Upload className="w-2.5 h-2.5 text-slate-500" />
    </div>
  );
}

// ============================================================================
// 4. MAIN PAGE COMPONENT
// ============================================================================

export default function MeetingsPage() {
  const [activeTab, setActiveTab] = useState<"meetings" | "processing">("meetings");
  const [globalAskInput, setGlobalAskInput] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [sortDirection, setSortDirection] = useState<"desc" | "asc">("desc");
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  // Tab counts
  const completedCount = useMemo(
    () => MOCK_MEETINGS.filter((m) => m.status === "COMPLETED").length,
    []
  );
  const processingCount = useMemo(
    () => MOCK_MEETINGS.filter((m) => m.status === "PROCESSING").length,
    []
  );

  const handleRefresh = () => {
    setIsRefreshing(true);
    setTimeout(() => setIsRefreshing(false), 600);
  };

  // Filter meetings by active tab and search query
  const filteredMeetings = useMemo(() => {
    return MOCK_MEETINGS.filter((item) => {
      if (activeTab === "meetings" && item.status === "PROCESSING") return false;
      if (activeTab === "processing" && item.status === "COMPLETED") return false;

      if (searchQuery.trim() !== "") {
        const query = searchQuery.toLowerCase();
        const matchesTitle = item.title.toLowerCase().includes(query);
        const matchesOwner = item.owner.name.toLowerCase().includes(query);
        const matchesFolder = item.folder.name.toLowerCase().includes(query);
        if (!matchesTitle && !matchesOwner && !matchesFolder) return false;
      }
      return true;
    }).sort((a, b) => {
      const timeA = new Date(a.scheduledStartTime).getTime();
      const timeB = new Date(b.scheduledStartTime).getTime();
      return sortDirection === "desc" ? timeB - timeA : timeA - timeB;
    });
  }, [activeTab, searchQuery, sortDirection]);

  // Group by weekly header key
  const groupedMeetings = useMemo(() => {
    const groups: { [key: string]: MockMeeting[] } = {};
    for (const meeting of filteredMeetings) {
      if (!groups[meeting.weekGroupKey]) {
        groups[meeting.weekGroupKey] = [];
      }
      groups[meeting.weekGroupKey].push(meeting);
    }
    return groups;
  }, [filteredMeetings]);

  return (
    <div className="w-full min-w-0 flex-1 overflow-x-hidden">
      {/* Container with flex-col and gap-6 to enforce vertical rhythm */}
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-6">
        
        {/* ================================================================= */}
        {/* 1. TOP GLOBAL SEARCH BAR (Ask Knowra Anything)                    */}
        {/* ================================================================= */}
        <div className="w-full border border-slate-200 rounded-lg shadow-sm flex items-center px-4 py-3 bg-white shrink-0 focus-within:ring-2 focus-within:ring-indigo-500/20 focus-within:border-indigo-500 transition-all">
          {/* Left: Global / Workspace Selector */}
          <div className="flex items-center gap-1.5 text-slate-500 hover:text-slate-700 cursor-pointer pr-1 select-none shrink-0">
            <Globe className="w-4 h-4 text-slate-500" />
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </div>

          {/* Vertical divider */}
          <div className="h-5 w-px bg-slate-200 mx-3 shrink-0" />

          {/* Center: Search / Question Input */}
          <input
            type="text"
            value={globalAskInput}
            onChange={(e) => setGlobalAskInput(e.target.value)}
            placeholder="Ask Knowra anything..."
            className="w-full text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none bg-transparent"
          />

          {/* Right: Submit Button */}
          <button
            type="button"
            className="bg-slate-100 hover:bg-slate-200 text-slate-500 hover:text-slate-700 p-1.5 rounded-md transition-colors flex items-center justify-center ml-2 cursor-pointer shrink-0"
            title="Ask Knowra AI"
          >
            <SendHorizontal className="w-4 h-4" />
          </button>
        </div>

        {/* ================================================================= */}
        {/* 2. TABS & PAGE ACTIONS ROW                                        */}
        {/* ================================================================= */}
        <div className="flex items-center justify-between border-b border-slate-200 w-full shrink-0">
          {/* Tabs Group (Left) with explicit gap-6 */}
          <div className="flex items-center gap-6 -mb-px">
            <button
              type="button"
              onClick={() => setActiveTab("meetings")}
              className={`cursor-pointer transition-colors pb-3 px-1 text-sm font-semibold flex items-center gap-2 ${
                activeTab === "meetings"
                  ? "border-b-2 border-indigo-600 text-indigo-700"
                  : "border-b-2 border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 font-medium"
              }`}
            >
              <span>Meetings</span>
            </button>

            <button
              type="button"
              onClick={() => setActiveTab("processing")}
              className={`cursor-pointer transition-colors pb-3 px-1 text-sm flex items-center gap-2 ${
                activeTab === "processing"
                  ? "border-b-2 border-indigo-600 text-indigo-700 font-semibold"
                  : "border-b-2 border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300 font-medium"
              }`}
            >
              <span>Processing</span>
              {processingCount > 0 && (
                <span className="text-[11px] px-1.5 py-0.5 rounded-full font-medium bg-amber-50 text-amber-700 border border-amber-200">
                  {processingCount}
                </span>
              )}
            </button>
          </div>

          {/* Actions (Right) */}
          <div className="flex items-center gap-4 pb-2">
            <div className="text-xs text-slate-500 flex items-center gap-1.5 select-none">
              <button
                type="button"
                onClick={handleRefresh}
                className="hover:text-slate-700 transition-colors p-1 cursor-pointer"
                title="Refresh meetings"
              >
                <RefreshCw
                  className={`w-3.5 h-3.5 ${isRefreshing ? "animate-spin text-indigo-600" : ""}`}
                />
              </button>
              <span>Last refreshed at 6:57 PM</span>
            </div>

            <button
              type="button"
              onClick={() => setIsUploadModalOpen(true)}
              className="bg-indigo-600 hover:bg-indigo-700 text-white flex items-center gap-2 px-4 py-2 rounded-md font-medium text-sm shadow-sm transition-colors cursor-pointer shrink-0"
            >
              <Upload className="w-4 h-4" />
              <span>Upload</span>
            </button>
          </div>
        </div>

        {/* ================================================================= */}
        {/* 3. THE FILTER BAR                                                 */}
        {/* ================================================================= */}
        <div className="flex flex-wrap items-center gap-3 w-full shrink-0">
          {/* Title Search Input */}
          <div className="border border-slate-200 rounded-md px-3 py-2 text-sm w-64 shadow-sm bg-white flex items-center gap-2 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500">
            <Search className="w-4 h-4 text-slate-400 shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by meeting title..."
              className="w-full text-sm text-slate-700 placeholder:text-slate-400 focus:outline-none bg-transparent"
            />
          </div>

          {/* Discrete Dropdown Buttons */}
          <button
            type="button"
            className="bg-white border border-slate-200 hover:bg-slate-50 shadow-sm rounded-md px-3 py-2 text-sm font-medium text-slate-700 flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Layers className="w-3.5 h-3.5 text-slate-500" />
            <span>All Meetings</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          <button
            type="button"
            className="bg-white border border-slate-200 hover:bg-slate-50 shadow-sm rounded-md px-3 py-2 text-sm font-medium text-slate-700 flex items-center gap-2 transition-colors cursor-pointer"
          >
            <Calendar className="w-3.5 h-3.5 text-slate-500" />
            <span>Anytime</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          <button
            type="button"
            className="bg-white border border-slate-200 hover:bg-slate-50 shadow-sm rounded-md px-3 py-2 text-sm font-medium text-slate-700 flex items-center gap-2 transition-colors cursor-pointer"
          >
            <span>Type</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          <button
            type="button"
            className="bg-white border border-slate-200 hover:bg-slate-50 shadow-sm rounded-md px-3 py-2 text-sm font-medium text-slate-700 flex items-center gap-2 transition-colors cursor-pointer"
          >
            <span>Source</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          <button
            type="button"
            className="bg-white border border-slate-200 hover:bg-slate-50 shadow-sm rounded-md px-3 py-2 text-sm font-medium text-slate-700 flex items-center gap-2 transition-colors cursor-pointer"
          >
            <span>Folder</span>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {/* Sort Direction Action */}
          <button
            type="button"
            onClick={() => setSortDirection((prev) => (prev === "desc" ? "asc" : "desc"))}
            className="ml-auto border border-slate-200 bg-white hover:bg-slate-50 shadow-sm rounded-md p-2 text-slate-600 transition-colors cursor-pointer flex items-center gap-1 text-xs font-medium"
            title={`Sort Date: ${sortDirection.toUpperCase()}`}
          >
            <ArrowUpDown className="w-3.5 h-3.5 text-slate-500" />
          </button>
        </div>

        {/* ================================================================= */}
        {/* 4. DATA TABLE (STRICT CSS GRID TEMPLATE)                          */}
        {/* ================================================================= */}
        <div className="w-full bg-white border border-slate-200 rounded-lg shadow-sm overflow-hidden">
          {/* Table Header Row: Locked to exact grid template */}
          <div className="grid grid-cols-[100px_minmax(300px,_1fr)_180px_200px_80px] gap-4 items-center border-b border-slate-200 py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider bg-white select-none">
            {/* Col 1: Source */}
            <div>Source</div>

            {/* Col 2: Meeting */}
            <div>Meeting</div>

            {/* Col 3: Date & Time */}
            <div
              className="flex items-center gap-1 cursor-pointer hover:text-slate-800 transition-colors"
              onClick={() => setSortDirection((prev) => (prev === "desc" ? "asc" : "desc"))}
            >
              <span>Date &amp; Time</span>
              <span className="text-indigo-600 font-bold lowercase">↓</span>
            </div>

            {/* Col 4: Folders */}
            <div>Folders</div>

            {/* Col 5: Owner */}
            <div className="text-right pr-2">Owner</div>
          </div>

          {/* Body Groups */}
          {Object.keys(groupedMeetings).length === 0 ? (
            <div className="py-16 text-center text-slate-500 text-sm bg-slate-50/50">
              No meetings found matching your current filter criteria.
            </div>
          ) : (
            Object.entries(groupedMeetings).map(([groupKey, meetingsInGroup]) => (
              <div key={groupKey} className="w-full">
                {/* Group Header */}
                <div className="bg-slate-50/80 text-[10px] uppercase tracking-wider font-semibold text-indigo-700 py-2 px-4 border-b border-slate-200">
                  {groupKey}
                </div>

                {/* Rows with identical grid definition */}
                <div className="divide-y divide-slate-100">
                  {meetingsInGroup.map((meeting) => {
                    const startDate = parseISO(meeting.scheduledStartTime);
                    const endDate = parseISO(meeting.scheduledEndTime);
                    const formattedDate = format(startDate, "EEE, MMM d, yyyy");
                    const formattedTimeRange = `${format(startDate, "h:mm a")} - ${format(endDate, "h:mm a")}`;

                    return (
                      <div
                        key={meeting.id}
                        className="grid grid-cols-[100px_minmax(300px,_1fr)_180px_200px_80px] gap-4 items-center border-b border-slate-100 py-3 px-4 hover:bg-slate-50 transition-colors bg-white w-full group"
                      >
                        {/* Col 1: Source / Thumbnail */}
                        <div className="w-24 h-14 bg-slate-200 rounded-md overflow-hidden relative shrink-0 border border-slate-200 shadow-xs">
                          <div
                            className={`w-full h-full bg-gradient-to-br ${meeting.thumbnailGradient} flex items-center justify-center`}
                          >
                            <span className="text-xl select-none filter drop-shadow">
                              {meeting.thumbnailFaceInitial}
                            </span>
                          </div>

                          {/* Source Badge */}
                          <div className="absolute bottom-1 right-1">
                            <SourceBadge source={meeting.source} />
                          </div>
                        </div>

                        {/* Col 2: Meeting Title & Metadata */}
                        <div className="flex flex-col gap-1 min-w-0 overflow-hidden">
                          <Link
                            href={`/meetings/${meeting.id}`}
                            className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors truncate"
                            title={meeting.title}
                          >
                            {meeting.title}
                          </Link>

                          {/* Metadata row */}
                          <div className="flex items-center gap-3 text-xs text-slate-500">
                            <div
                              className="flex items-center gap-1 font-medium"
                              title={`${meeting.participantCount} Participants`}
                            >
                              <Users className="w-3.5 h-3.5 text-slate-400" />
                              <span>{meeting.participantCount}</span>
                            </div>

                            <div
                              className="flex items-center gap-1 text-[11px] font-semibold text-teal-700 bg-teal-50 border border-teal-200/70 px-1.5 py-0.5 rounded cursor-pointer"
                              title={`Knowra Intelligence Score: ${meeting.metrics.intelligenceScore}/100`}
                            >
                              <Sparkles className="w-3 h-3 text-teal-600" />
                              <span>{meeting.metrics.intelligenceScore}</span>
                            </div>

                            {meeting.status === "PROCESSING" && (
                              <div className="flex items-center gap-1 text-[11px] font-medium text-amber-700 bg-amber-50 border border-amber-200 px-1.5 py-0.5 rounded">
                                <Clock className="w-3 h-3 animate-spin text-amber-600" />
                                <span>Processing...</span>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Col 3: Date & Time */}
                        <div className="flex flex-col justify-center select-none">
                          <span className="text-sm font-medium text-slate-800">
                            {formattedDate}
                          </span>
                          <span className="text-xs text-slate-500 mt-0.5">
                            {formattedTimeRange}
                          </span>
                        </div>

                        {/* Col 4: Folders */}
                        <div className="flex items-center min-w-0">
                          <div
                            className="bg-slate-100 hover:bg-slate-200/70 text-slate-600 border border-slate-200 px-2.5 py-1 rounded-md text-xs font-medium w-max max-w-full flex items-center gap-1.5 truncate transition-colors cursor-pointer"
                            title={`Folder: ${meeting.folder.name}`}
                          >
                            <FolderIcon className="w-3 h-3 text-slate-400 shrink-0" />
                            <span className="truncate">{meeting.folder.name}</span>
                          </div>
                        </div>

                        {/* Col 5: Owner & Menu */}
                        <div className="flex items-center justify-end gap-3 pr-2">
                          <div
                            className="w-8 h-8 rounded-md bg-indigo-100 text-indigo-700 flex items-center justify-center text-xs font-bold shrink-0 border border-indigo-200/60 shadow-xs relative cursor-pointer"
                            title={`${meeting.owner.name} (${meeting.owner.email})`}
                          >
                            {meeting.owner.initials}
                            <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 bg-indigo-600 rounded-full border border-white" />
                          </div>

                          <button
                            type="button"
                            className="text-slate-400 hover:text-slate-700 cursor-pointer p-1 rounded hover:bg-slate-100 transition-colors"
                            title="More options"
                          >
                            <MoreHorizontal className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Direct-to-Storage Presigned Upload Modal (Phase 8/9 Contract) */}
      <UploadMeetingModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadComplete={() => {
          handleRefresh();
          setActiveTab("processing");
        }}
      />
    </div>
  );
}