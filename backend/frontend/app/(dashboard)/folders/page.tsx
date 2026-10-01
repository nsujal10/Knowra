"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
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
} from "lucide-react";
import { useWorkspaceFolders } from "@/hooks/useWorkspaceFolders";
import { CreateFolderModal } from "@/components/meetings/CreateFolderModal";
import { AddMeetingsToFolderModal } from "@/components/meetings/AddMeetingsToFolderModal";
import { UploadMeetingModal } from "@/components/meetings/UploadMeetingModal";

export default function WorkspaceFoldersPage() {
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

  return (
    <div className="flex-1 flex flex-col min-h-screen bg-[#f8fafc] text-slate-800 font-sans pb-16">
      {/* ── TOP HEADER & ACTIONS ────────────────────────────────────────────── */}
      <div className="bg-white border-b border-slate-200/80 px-6 py-6 sm:px-8">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-indigo-600 mb-1">
              <Folder size={14} />
              <span>Workspace Collections</span>
            </div>
            <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
              Workspace Folders
            </h1>
            <p className="text-xs sm:text-sm text-slate-500 mt-1 max-w-2xl">
              Organize meetings, access permissions, and automated intelligence routing across your enterprise teams.
            </p>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => setIsCreateModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-700 hover:to-indigo-800 text-white font-semibold text-xs sm:text-sm shadow-md hover:shadow-lg transition-all active:scale-95 cursor-pointer"
            >
              <FolderPlus size={16} />
              <span>New Folder</span>
            </button>
          </div>
        </div>

        {/* ── KPI STATS RIBBON ──────────────────────────────────────────────── */}
        <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4 mt-6">
          {/* Stat 1 */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
              <Folder size={18} />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Active Folders</p>
              <p className="text-lg font-bold text-slate-900 leading-tight">{folders.length}</p>
            </div>
          </div>

          {/* Stat 2 */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0">
              <Video size={18} />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Organized Calls</p>
              <p className="text-lg font-bold text-slate-900 leading-tight">{totalMeetings} Sessions</p>
            </div>
          </div>

          {/* Stat 3 */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
              <Globe size={18} />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Workspace Shared</p>
              <p className="text-lg font-bold text-slate-900 leading-tight">{sharedCount} Public</p>
            </div>
          </div>

          {/* Stat 4 */}
          <div className="bg-slate-50 border border-slate-200/80 rounded-xl p-3.5 flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-purple-100 text-purple-700 flex items-center justify-center shrink-0">
              <Sparkles size={18} />
            </div>
            <div>
              <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Decisions Tracked</p>
              <p className="text-lg font-bold text-slate-900 leading-tight">{totalDecisions} Recorded</p>
            </div>
          </div>
        </div>
      </div>

      {/* ── MAIN CONTENT AREA ──────────────────────────────────────────────── */}
      <div className="max-w-7xl mx-auto px-6 sm:px-8 mt-6 w-full flex-1">
        {/* If a folder is drilled-down into */}
        {activeFolder ? (
          <div className="space-y-6">
            {/* Prominent Back Button & Quick Actions Header */}
            <div className="flex flex-wrap items-center justify-between gap-3">
              <button
                type="button"
                onClick={() => setActiveFolderId(null)}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 hover:border-slate-300 text-slate-700 font-semibold text-xs shadow-xs transition-all active:scale-95 cursor-pointer"
              >
                <ArrowLeft size={16} className="text-slate-500" />
                <span>Back to All Folders</span>
              </button>

              <div className="flex items-center gap-2.5">
                <button
                  type="button"
                  onClick={() => setIsAddMeetingsModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs shadow-xs transition-all active:scale-95 cursor-pointer"
                >
                  <Plus size={15} />
                  <span>Add Videos to Folder</span>
                </button>

                <button
                  type="button"
                  onClick={() => setIsUploadModalOpen(true)}
                  className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-xs shadow-xs transition-all cursor-pointer"
                >
                  <UploadCloud size={15} className="text-slate-500" />
                  <span>Upload Recording</span>
                </button>

                <Link
                  href="/meetings"
                  className="text-xs font-medium text-slate-600 hover:text-indigo-600 flex items-center gap-1 bg-white border border-slate-200 px-3 py-2 rounded-xl shadow-xs"
                >
                  <ExternalLink size={13} />
                  <span>Open in Meetings Table</span>
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
                <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
                  Meetings in this Collection ({activeFolder.recentMeetings.length})
                </h3>
                {activeFolder.recentMeetings.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setIsAddMeetingsModalOpen(true)}
                    className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors cursor-pointer"
                  >
                    <Plus size={13} />
                    <span>Add more videos</span>
                  </button>
                )}
              </div>

              {activeFolder.recentMeetings.length === 0 ? (
                <div className="p-10 text-center bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col items-center justify-center">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
                    <Video size={24} />
                  </div>
                  <h4 className="text-sm font-bold text-slate-900">No meetings in this folder yet</h4>
                  <p className="text-xs text-slate-500 mt-1 max-w-md">
                    Choose existing recordings from your workspace or upload a new video to add it directly to this folder.
                  </p>

                  <div className="flex flex-wrap items-center justify-center gap-3 mt-5">
                    <button
                      type="button"
                      onClick={() => setIsAddMeetingsModalOpen(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-all active:scale-95 cursor-pointer"
                    >
                      <Plus size={15} />
                      <span>Select Videos to Add</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setIsUploadModalOpen(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-xs font-bold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 shadow-xs transition-all cursor-pointer"
                    >
                      <UploadCloud size={15} className="text-slate-500" />
                      <span>Upload Video File</span>
                    </button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                  {activeFolder.recentMeetings.map((m) => (
                    <div
                      key={m.id}
                      className="p-4 rounded-xl bg-white border border-slate-200 hover:border-indigo-300 hover:shadow-md transition-all group flex flex-col justify-between"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div className="min-w-0 flex-1">
                          <Link href={`/meetings/${m.id}`}>
                            <h4 className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
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
                            }}
                            className="p-1 text-slate-300 hover:text-rose-600 hover:bg-rose-50 rounded transition-colors"
                            title="Remove video from this folder"
                          >
                            <X size={14} />
                          </button>
                        </div>
                      </div>

                      <div className="mt-4 pt-2.5 border-t border-slate-100 flex items-center justify-between text-xs text-indigo-600 font-semibold">
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
          <div className="space-y-6">
            {/* Filters & Search Toolbar */}
            <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
              {/* Search */}
              <div className="relative flex-1 max-w-md">
                <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search folders by title, keyword, or team..."
                  className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all"
                />
              </div>

              {/* Categories, Sort, View */}
              <div className="flex flex-wrap items-center gap-2.5">
                {/* Category Pills */}
                <div className="flex items-center bg-slate-100 p-1 rounded-xl">
                  {["ALL", "ENGINEERING", "EXECUTIVE", "PRODUCT", "SALES"].map((cat) => (
                    <button
                      key={cat}
                      type="button"
                      onClick={() => setSelectedCategory(cat)}
                      className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                        selectedCategory === cat
                          ? "bg-white text-indigo-700 shadow-xs"
                          : "text-slate-600 hover:text-slate-900"
                      }`}
                    >
                      {cat === "ALL" ? "All" : cat.charAt(0) + cat.slice(1).toLowerCase()}
                    </button>
                  ))}
                </div>

                {/* Sort */}
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as "updated" | "meetings" | "alpha")}
                  className="px-3 py-1.5 rounded-xl border border-slate-200 bg-white text-xs font-medium text-slate-700 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20"
                >
                  <option value="updated">Recently Updated</option>
                  <option value="meetings">Most Meetings</option>
                  <option value="alpha">Alphabetical</option>
                </select>

                {/* Grid / List View Toggle */}
                <div className="flex items-center border border-slate-200 rounded-xl bg-white p-0.5">
                  <button
                    type="button"
                    onClick={() => setViewMode("grid")}
                    className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                      viewMode === "grid" ? "bg-slate-100 text-indigo-700" : "text-slate-400 hover:text-slate-700"
                    }`}
                    title="Grid View"
                  >
                    <LayoutGrid size={15} />
                  </button>
                  <button
                    type="button"
                    onClick={() => setViewMode("list")}
                    className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                      viewMode === "list" ? "bg-slate-100 text-indigo-700" : "text-slate-400 hover:text-slate-700"
                    }`}
                    title="List View"
                  >
                    <List size={15} />
                  </button>
                </div>
              </div>
            </div>

            {/* If 0 folders exist */}
            {folders.length === 0 ? (
              <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 shadow-xs flex flex-col items-center justify-center">
                <div className="w-14 h-14 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4">
                  <FolderPlus size={28} />
                </div>
                <h3 className="text-base font-bold text-slate-900">No workspace folders created yet</h3>
                <p className="text-xs sm:text-sm text-slate-500 mt-1.5 max-w-md">
                  Create your first folder to organize meetings, set custom permissions, and route video transcripts.
                </p>
                <button
                  type="button"
                  onClick={() => setIsCreateModalOpen(true)}
                  className="mt-5 inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs sm:text-sm shadow-md transition-all active:scale-95 cursor-pointer"
                >
                  <Plus size={16} />
                  <span>Create First Folder</span>
                </button>
              </div>
            ) : filteredFolders.length === 0 ? (
              <div className="p-12 text-center bg-white rounded-2xl border border-slate-200 text-slate-500 text-sm">
                No folders match &quot;{search}&quot;.
              </div>
            ) : viewMode === "grid" ? (
              /* Folder Grid View */
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                {filteredFolders.map((f) => (
                  <div
                    key={f.id}
                    className={`bg-white rounded-2xl border ${f.borderClass} shadow-xs hover:shadow-md transition-all flex flex-col justify-between overflow-hidden group`}
                  >
                    {/* Card Header & Body */}
                    <div className="p-5 space-y-4">
                      {/* Top Bar with Icon & Actions */}
                      <div className="flex items-start justify-between gap-3">
                        <div
                          onClick={() => setActiveFolderId(f.id)}
                          className="w-11 h-11 rounded-xl flex items-center justify-center text-white shadow-xs transition-transform group-hover:scale-105 cursor-pointer"
                          style={{ backgroundColor: f.color }}
                        >
                          <Folder size={22} />
                        </div>

                        <div className="flex items-center gap-1.5">
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${f.tagColor}`}>
                            {f.visibility}
                          </span>
                          <button
                            type="button"
                            onClick={() => deleteFolder(f.id)}
                            className="p-1.5 text-slate-300 hover:text-rose-600 rounded-md hover:bg-rose-50 transition-colors cursor-pointer"
                            title="Delete Folder"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>

                      {/* Title & Description */}
                      <div className="cursor-pointer" onClick={() => setActiveFolderId(f.id)}>
                        <h3 className="text-base font-bold text-slate-900 group-hover:text-indigo-600 transition-colors line-clamp-1">
                          {f.name}
                        </h3>
                        <p className="text-xs text-slate-500 mt-1 line-clamp-2 leading-relaxed">
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
                    <div className="px-5 py-3 bg-slate-50/80 border-t border-slate-100 flex items-center justify-between">
                      <div className="flex items-center gap-1 text-xs text-slate-400 font-medium">
                        <span>Updated {f.updatedAt}</span>
                      </div>

                      <button
                        type="button"
                        onClick={() => setActiveFolderId(f.id)}
                        className="text-xs font-bold text-indigo-600 hover:text-indigo-800 flex items-center gap-1 transition-colors cursor-pointer"
                      >
                        <span>Open Folder</span>
                        <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              /* Folder List / Table View */
              <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-xs">
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
                        <td className="py-3.5 px-4 font-semibold text-slate-900 flex items-center gap-3">
                          <div
                            className="w-7 h-7 rounded-lg flex items-center justify-center text-white shrink-0"
                            style={{ backgroundColor: f.color }}
                          >
                            <Folder size={14} />
                          </div>
                          <div>
                            <p className="font-bold text-slate-900 hover:text-indigo-600 transition-colors">{f.name}</p>
                            <p className="text-[11px] text-slate-400 font-normal line-clamp-1">{f.description}</p>
                          </div>
                        </td>
                        <td className="py-3.5 px-4">
                          <span className={`px-2 py-0.5 rounded-md text-[10px] font-bold uppercase tracking-wider border ${f.tagColor}`}>
                            {f.visibility}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 font-medium text-slate-700">
                          {f.meetingCount} Sessions
                        </td>
                        <td className="py-3.5 px-4 font-medium text-emerald-700">
                          {f.decisionsCount} Logged
                        </td>
                        <td className="py-3.5 px-4 text-slate-400 text-[11px]">
                          {f.updatedAt}
                        </td>
                        <td className="py-3.5 px-4 text-right" onClick={(e) => e.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => deleteFolder(f.id)}
                            className="p-1.5 text-slate-300 hover:text-rose-600 rounded-md hover:bg-rose-50 transition-colors cursor-pointer"
                            title="Delete Folder"
                          >
                            <Trash2 size={14} />
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

      {/* ── CREATE FOLDER MODAL ─────────────────────────────────────────────── */}
      <CreateFolderModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreated={(newF) => {
          const created = addFolder(newF);
          if (created?.id) setActiveFolderId(created.id);
        }}
      />

      {/* ── ADD MEETINGS TO FOLDER MODAL ────────────────────────────────────── */}
      {activeFolder && (
        <AddMeetingsToFolderModal
          isOpen={isAddMeetingsModalOpen}
          onClose={() => setIsAddMeetingsModalOpen(false)}
          folderName={activeFolder.name}
          existingMeetingIds={activeFolder.recentMeetings.map((m) => m.id)}
          onAddMeetings={(newMeetings) => {
            addMeetingsToFolder(activeFolder.id, newMeetings);
          }}
          onOpenUploadNew={() => setIsUploadModalOpen(true)}
        />
      )}

      {/* ── UPLOAD MEETING MODAL ────────────────────────────────────────────── */}
      <UploadMeetingModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onUploadComplete={(meetingId) => {
          if (activeFolder) {
            addMeetingToFolder(activeFolder.id, {
              id: meetingId,
              title: "Uploaded Recording",
              date: "Just now",
              duration: "Processing",
              status: "PROCESSING",
            });
          }
          setIsUploadModalOpen(false);
        }}
      />
    </div>
  );
}
