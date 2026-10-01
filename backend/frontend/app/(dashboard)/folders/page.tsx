"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Folder,
  FolderPlus,
  Search,
  CheckCircle2,
  Video,
  Clock,
  Sparkles,
  ArrowRight,
  Globe,
  Tag,
  LayoutGrid,
  List,
  ChevronRight,
  Trash2,
  ExternalLink,
  Plus,
  ArrowLeft,
  Calendar,
  UploadCloud,
  X,
  SendHorizontal,
} from "lucide-react";
import { useWorkspaceFolders } from "@/hooks/useWorkspaceFolders";
import { CreateFolderModal } from "@/components/meetings/CreateFolderModal";
import { AddMeetingsToFolderModal } from "@/components/meetings/AddMeetingsToFolderModal";
import { UploadMeetingModal } from "@/components/meetings/UploadMeetingModal";
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "@/components/ui/toast";

export default function WorkspaceFoldersPage() {
  const router = useRouter();
  const {
    folders,
    addFolder,
    deleteFolder,
    addMeetingsToFolder,
    addMeetingToFolder,
    removeMeetingFromFolder,
  } = useWorkspaceFolders();

  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");
  const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
  const [sortBy, setSortBy] = useState<"updated" | "meetings" | "alpha">("updated");
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isAddMeetingsModalOpen, setIsAddMeetingsModalOpen] = useState(false);
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);
  const [activeFolderId, setActiveFolderId] = useState<string | null>(null);

  // Stats calculation
  const totalMeetings = useMemo(() => folders.reduce((sum, f) => sum + f.meetingCount, 0), [folders]);
  const totalDecisions = useMemo(() => folders.reduce((sum, f) => sum + f.decisionsCount, 0), [folders]);
  const sharedCount = useMemo(() => folders.filter((f) => f.visibility === "WORKSPACE").length, [folders]);

  // Filtering & Sorting
  const filteredFolders = useMemo(() => {
    let list = folders;
    if (selectedCategory !== "ALL") {
      list = list.filter((f) => f.category === selectedCategory);
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        (f) =>
          f.name.toLowerCase().includes(q) ||
          f.description.toLowerCase().includes(q) ||
          f.autoRouteTags.some((t) => t.toLowerCase().includes(q))
      );
    }

    return [...list].sort((a, b) => {
      if (sortBy === "meetings") return b.meetingCount - a.meetingCount;
      if (sortBy === "alpha") return a.name.localeCompare(b.name);
      return 0; // Default recent
    });
  }, [folders, selectedCategory, search, sortBy]);

  const activeFolder = useMemo(() => {
    if (!activeFolderId) return null;
    return folders.find((f) => f.id === activeFolderId) || null;
  }, [folders, activeFolderId]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;
    router.push(`/chat?q=${encodeURIComponent(search.trim())}`);
  };

  const handleDeleteFolder = (folderId: string) => {
    deleteFolder(folderId);
    toast.success("Folder deleted");
    if (activeFolderId === folderId) {
      setActiveFolderId(null);
    }
  };

  return (
    <div className="w-full min-w-0 flex-1 overflow-x-hidden">
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-5 pb-16">
        {/* ── 1. ENTERPRISE PAGE HEADER ────────────────────────────────────────── */}
        <PageHeader
          title="Folders"
          subtitle={`${folders.length} collections · ${totalMeetings} sessions organized · Automated intelligence routing`}
          icon={Folder}
          badge={
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              {folders.length} Collections
            </span>
          }
          actions={
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-1.5 h-9 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold shadow-xs hover:shadow-sm transition-all active:scale-95 cursor-pointer"
            >
              <Plus size={15} className="stroke-[2.5]" />
              <span>New Folder</span>
            </button>
          }
        />

        {/* ── 2. METRIC KPI CARDS ───────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Active Folders */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Active Folders
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <span className="text-3xl font-bold text-slate-900 tracking-tight">
                {folders.length}
              </span>
              <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
                <Folder size={18} />
              </div>
            </div>
          </div>

          {/* Organized Calls */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Organized Calls
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-3xl font-bold text-slate-900 tracking-tight">
                  {totalMeetings}
                </span>
                <p className="text-[11px] text-indigo-600 font-medium">Mapped to folders</p>
              </div>
              <div className="bg-blue-50 text-blue-600 p-2 rounded-lg shrink-0">
                <Video size={18} />
              </div>
            </div>
          </div>

          {/* Shared Collections */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Workspace Shared
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-3xl font-bold text-emerald-600 tracking-tight">
                  {sharedCount}
                </span>
                <p className="text-[11px] text-emerald-600 font-medium">Team visibility</p>
              </div>
              <div className="bg-emerald-50 text-emerald-600 p-2 rounded-lg shrink-0">
                <Globe size={18} />
              </div>
            </div>
          </div>

          {/* Decisions Tracked */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Decisions Tracked
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-3xl font-bold text-slate-900 tracking-tight">
                  {totalDecisions}
                </span>
                <p className="text-[11px] text-slate-500 font-medium">Across collections</p>
              </div>
              <div className="bg-purple-50 text-purple-600 p-2 rounded-lg shrink-0">
                <Sparkles size={18} />
              </div>
            </div>
          </div>
        </div>

        {/* If a folder is drilled-down into */}
        {activeFolder ? (
          <div className="space-y-5">
            {/* Prominent Back Button & Quick Actions Header */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setActiveFolderId(null)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 hover:border-slate-300 text-slate-700 font-semibold text-xs shadow-xs transition-all active:scale-95 cursor-pointer"
              >
                <ArrowLeft size={15} className="text-slate-500" />
                <span>Back to All Folders</span>
              </button>

              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsAddMeetingsModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-xs transition-all active:scale-95 cursor-pointer"
                >
                  <Plus size={14} />
                  <span>Add Videos to Folder</span>
                </button>

                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs shadow-xs transition-all cursor-pointer"
                >
                  <UploadCloud size={14} className="text-slate-500" />
                  <span>Upload Recording</span>
                </button>

                <Link
                  href="/meetings"
                  className="text-xs font-semibold text-slate-600 hover:text-indigo-600 flex items-center gap-1.5 bg-white border border-slate-200 px-3.5 py-2 rounded-xl shadow-xs transition-all"
                >
                  <ExternalLink size={13} />
                  <span>Open in Meetings</span>
                </Link>
              </div>
            </div>

            {/* Folder Hero Banner */}
            <div
              className={`p-6 rounded-2xl border bg-gradient-to-br ${activeFolder.bgGradient} bg-white shadow-xs space-y-4`}
              style={{ borderColor: activeFolder.color + "40" }}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-center gap-3.5">
                  <div
                    className="w-12 h-12 rounded-xl flex items-center justify-center text-white shadow-xs"
                    style={{ backgroundColor: activeFolder.color }}
                  >
                    <Folder size={24} />
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h2 className="text-xl font-bold text-slate-900">{activeFolder.name}</h2>
                      <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${activeFolder.tagColor}`}>
                        {activeFolder.visibility}
                      </span>
                    </div>
                    <p className="text-xs text-slate-600 mt-0.5">{activeFolder.description}</p>
                  </div>
                </div>

                <div className="flex items-center gap-3 text-xs text-slate-500 font-medium">
                  <span className="flex items-center gap-1">
                    <Video size={13} className="text-indigo-600" />
                    <strong>{activeFolder.meetingCount}</strong> Meetings
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <CheckCircle2 size={13} className="text-emerald-600" />
                    <strong>{activeFolder.decisionsCount}</strong> Decisions
                  </span>
                </div>
              </div>

              {/* Auto-route tags */}
              {activeFolder.autoRouteTags.length > 0 && (
                <div className="flex items-center gap-2 pt-2 border-t border-slate-100/80">
                  <Tag size={13} className="text-slate-400" />
                  <span className="text-xs text-slate-500">Auto-routes matching:</span>
                  <div className="flex flex-wrap gap-1.5">
                    {activeFolder.autoRouteTags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 rounded-md text-[10px] font-mono bg-white border border-slate-200 text-slate-700 shadow-2xs"
                      >
                        #{tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Meetings inside this folder */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Meetings in Collection ({activeFolder.recentMeetings.length})
                </h3>
                {activeFolder.recentMeetings.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setIsAddMeetingsModalOpen(true)}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <Plus size={13} />
                    <span>Add videos</span>
                  </button>
                )}
              </div>

              {activeFolder.recentMeetings.length === 0 ? (
                <div className="p-10 text-center bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col items-center justify-center">
                  <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3 border border-indigo-100">
                    <Video size={22} />
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">No meetings in this folder yet</h4>
                  <p className="text-xs text-slate-500 mt-1 max-w-md">
                    Choose existing recordings from your workspace or upload a new video to add it directly to this folder.
                  </p>

                  <div className="flex flex-wrap items-center justify-center gap-3 mt-5">
                    <button
                      type="button"
                      onClick={() => setIsAddMeetingsModalOpen(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-all active:scale-95 cursor-pointer"
                    >
                      <Plus size={14} />
                      <span>Select Videos to Add</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsUploadModalOpen(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-bold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-xs transition-all cursor-pointer"
                    >
                      <UploadCloud size={14} className="text-slate-500" />
                      <span>Upload Video File</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {activeFolder.recentMeetings.map((m) => (
                    <div
                      key={m.id}
                      className="p-4 rounded-xl bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-xs transition-all group flex flex-col justify-between"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <Link href={`/meetings/${m.id}`}>
                            <h4 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                              {m.title}
                            </h4>
                          </Link>
                          <div className="flex items-center gap-3 text-xs text-slate-400 mt-1 font-medium">
                            <span className="flex items-center gap-1">
                              <Calendar size={12} />
                              {m.date}
                            </span>
                            <span className="flex items-center gap-1">
                              <Clock size={12} />
                              {m.duration}
                            </span>
                          </div>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0">
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            {m.status}
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              removeMeetingFromFolder(activeFolder.id, m.id);
                              toast.info("Meeting removed from folder");
                            }}
                            className="p-1 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors cursor-pointer"
                            title="Remove video from this folder"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      </div>

                      <div className="mt-3.5 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-indigo-600 font-semibold">
                        <Link href={`/meetings/${m.id}`} className="hover:underline flex items-center gap-1">
                          <span>Review Transcript &amp; Intelligence</span>
                          <ArrowRight size={13} className="transition-transform group-hover:translate-x-1" />
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Normal List / Grid of All Folders */
          <div className="space-y-4">
            {/* ── 3. UNIFIED SEARCH BAR ─────────────────────────────────────── */}
            <form
              onSubmit={handleSearchSubmit}
              className="relative w-full border border-slate-200 hover:border-slate-300 focus-within:border-indigo-400 focus-within:ring-2 focus-within:ring-indigo-500/10 rounded-xl flex items-center px-4 py-2.5 bg-white shrink-0 transition-all shadow-xs"
            >
              <Search className="w-4 h-4 text-slate-400 mr-3 shrink-0 pointer-events-none" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search collections by title, description, or routing tag..."
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

            {/* ── 4. CATEGORIES & VIEW TOOLBAR ──────────────────────────────── */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 bg-white p-3 rounded-xl border border-slate-200 shadow-xs">
              {/* Category Pills */}
              <div className="flex items-center gap-1 overflow-x-auto">
                {["ALL", "ENGINEERING", "EXECUTIVE", "PRODUCT", "SALES"].map((cat) => (
                  <button
                    key={cat}
                    type="button"
                    onClick={() => setSelectedCategory(cat)}
                    className={`cursor-pointer transition-all px-3 py-1.5 rounded-lg text-xs font-semibold ${
                      selectedCategory === cat
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                    }`}
                  >
                    {cat === "ALL" ? "All Collections" : cat.charAt(0) + cat.slice(1).toLowerCase()}
                  </button>
                ))}
              </div>

              {/* Sort & Grid / List View Toggle */}
              <div className="flex items-center gap-2 shrink-0">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as "updated" | "meetings" | "alpha")}
                  className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 outline-none cursor-pointer"
                >
                  <option value="updated">Recently Updated</option>
                  <option value="meetings">Most Meetings</option>
                  <option value="alpha">Alphabetical</option>
                </select>

                <div className="flex items-center border border-slate-200 rounded-lg bg-white p-0.5">
                  <button
                    type="button"
                    onClick={() => setViewMode("grid")}
                    className={`p-1.5 rounded-md transition-colors cursor-pointer ${
                      viewMode === "grid" ? "bg-slate-100 text-indigo-700" : "text-slate-400 hover:text-slate-700"
                    }`}
                    title="Grid View"
                  >
                    <LayoutGrid size={14} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("list")}
                    className={`p-1.5 rounded-md transition-colors cursor-pointer ${
                      viewMode === "list" ? "bg-slate-100 text-indigo-700" : "text-slate-400 hover:text-slate-700"
                    }`}
                    title="List View"
                  >
                    <List size={14} />
                  </button>
                </div>
              </div>
            </div>

            {/* If 0 folders exist */}
            {folders.length === 0 ? (
              <div className="p-12 text-center bg-white rounded-xl border border-slate-200 shadow-xs flex flex-col items-center justify-center">
                <div className="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3 border border-indigo-100">
                  <FolderPlus size={22} />
                </div>
                <h3 className="text-base font-semibold text-slate-900">No workspace folders created yet</h3>
                <p className="text-xs text-slate-500 mt-1 max-w-md">
                  Create your first folder to organize meetings, set custom permissions, and route video transcripts.
                </p>
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(true)}
                  className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-xs transition-all active:scale-95 cursor-pointer"
                >
                  <Plus size={14} />
                  <span>Create First Folder</span>
                </button>
              </div>
            ) : filteredFolders.length === 0 ? (
              <div className="p-12 text-center bg-white rounded-xl border border-slate-200 shadow-xs text-slate-500 text-xs">
                No collections match &quot;{search}&quot;. Try adjusting your keywords or clearing the category filter.
              </div>
            ) : viewMode === "grid" ? (
              /* Folder Grid View */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredFolders.map((f) => (
                  <div
                    key={f.id}
                    className={`bg-white rounded-xl border ${f.borderClass} shadow-xs hover:shadow-sm hover:border-slate-300 transition-all flex flex-col justify-between overflow-hidden group`}
                  >
                    {/* Card Body */}
                    <div className="p-4.5 space-y-3.5">
                      {/* Top Bar with Icon & Actions */}
                      <div className="flex items-start justify-between gap-3">
                        <div
                          onClick={() => setActiveFolderId(f.id)}
                          className="w-10 h-10 rounded-xl flex items-center justify-center text-white shadow-2xs transition-transform group-hover:scale-105 cursor-pointer"
                          style={{ backgroundColor: f.color }}
                        >
                          <Folder size={20} />
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${f.tagColor}`}>
                            {f.visibility}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleDeleteFolder(f.id)}
                            className="p-1 text-slate-300 hover:text-rose-600 rounded-md hover:bg-rose-50 transition-colors cursor-pointer"
                            title="Delete Folder"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>

                      {/* Title & Description */}
                      <div className="cursor-pointer" onClick={() => setActiveFolderId(f.id)}>
                        <h3 className="text-sm font-semibold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                          {f.name}
                        </h3>
                        <p className="text-xs text-slate-500 mt-0.5 line-clamp-2 leading-relaxed">
                          {f.description}
                        </p>
                      </div>

                      {/* Metrics Badges */}
                      <div className="flex items-center gap-2 pt-2 border-t border-slate-100 text-xs text-slate-600">
                        <span className="flex items-center gap-1 font-semibold text-slate-800">
                          <Video size={13} className="text-indigo-600" />
                          {f.meetingCount} Calls
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1 font-semibold text-slate-800">
                          <CheckCircle2 size={13} className="text-emerald-600" />
                          {f.decisionsCount} Decisions
                        </span>
                      </div>

                      {/* Recent Meetings Snippets */}
                      {f.recentMeetings.length > 0 && (
                        <div className="space-y-1.5 pt-1">
                          <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                            Recent Recordings
                          </p>
                          {f.recentMeetings.slice(0, 2).map((rm) => (
                            <Link
                              key={rm.id}
                              href={`/meetings/${rm.id}`}
                              className="flex items-center justify-between text-xs px-2.5 py-1.5 rounded-lg bg-slate-50 hover:bg-indigo-50/80 border border-slate-200/60 hover:border-indigo-200 transition-all text-slate-700 hover:text-indigo-900"
                            >
                              <span className="truncate pr-2 font-medium">{rm.title}</span>
                              <span className="text-[10px] text-slate-400 font-mono shrink-0">{rm.duration}</span>
                            </Link>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Card Footer */}
                    <div className="px-4.5 py-2.5 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between">
                      <div className="flex items-center gap-1 text-[11px] text-slate-400 font-medium">
                        <span>Updated {f.updatedAt}</span>
                      </div>

                      <button
                        type="button"
                        onClick={() => setActiveFolderId(f.id)}
                        className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <span>Open Folder</span>
                        <ChevronRight size={13} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Folder List / Table View */
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50/80 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Folder Name</th>
                      <th className="py-3 px-4">Access</th>
                      <th className="py-3 px-4">Meetings</th>
                      <th className="py-3 px-4">Decisions</th>
                      <th className="py-3 px-4">Updated</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredFolders.map((f) => (
                      <tr
                        key={f.id}
                        className="hover:bg-slate-50/60 transition-colors cursor-pointer"
                        onClick={() => setActiveFolderId(f.id)}
                      >
                        <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-3">
                          <div
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-white shrink-0"
                            style={{ backgroundColor: f.color }}
                          >
                            <Folder size={14} />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-900 hover:text-indigo-600 transition-colors">{f.name}</p>
                            <p className="text-[11px] text-slate-400 font-normal line-clamp-1">{f.description}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${f.tagColor}`}>
                            {f.visibility}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-medium text-slate-700">
                          {f.meetingCount} Sessions
                        </td>
                        <td className="py-3 px-4 font-medium text-slate-700">
                          {f.decisionsCount} Decisions
                        </td>
                        <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                          {f.updatedAt}
                        </td>
                        <td className="py-3 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => handleDeleteFolder(f.id)}
                            className="p-1 text-slate-300 hover:text-rose-600 rounded transition-colors cursor-pointer"
                            title="Delete"
                          >
                            <Trash2 size={13} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── MODALS ───────────────────────────────────────────────────────────── */}
      <CreateFolderModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={(fData) => {
          addFolder(fData);
          toast.success(`Folder "${fData.name}" created`);
        }}
      />

      {activeFolder && (
        <AddMeetingsToFolderModal
          isOpen={isAddMeetingsModalOpen}
          onClose={() => setIsAddMeetingsModalOpen(false)}
          folderName={activeFolder.name}
          existingMeetingIds={activeFolder.recentMeetings.map((m) => m.id)}
          onAddMeetings={(mList) => {
            addMeetingsToFolder(activeFolder.id, mList);
            toast.success(`Added ${mList.length} meetings to ${activeFolder.name}`);
          }}
        />
      )}

      <UploadMeetingModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadComplete={() => {
          toast.success("Meeting uploaded and queued for processing");
          setIsUploadModalOpen(false);
        }}
      />
    </div>
  );
}
