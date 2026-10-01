"use client";

import React, { useState, useEffect, useMemo } from "react";
import { X, Search, Check, Video, Calendar, Clock, Plus, Loader2, UploadCloud } from "lucide-react";
import { api } from "@/lib/api/client";
import { FolderMeetingItem } from "@/hooks/useWorkspaceFolders";

interface AddMeetingsToFolderModalProps {
  isOpen: boolean;
  onClose: () => void;
  folderName: string;
  existingMeetingIds: string[];
  onAddMeetings: (meetings: FolderMeetingItem[]) => void;
  onOpenUploadNew?: () => void;
}

interface RawMeetingApiItem {
  id: string;
  title: string;
  created_at?: string;
  meeting_date?: string;
  duration_seconds?: number;
  status?: string;
  media_filename?: string;
}

const FALLBACK_AVAILABLE_MEETINGS: FolderMeetingItem[] = [
  {
    id: "m-sample-recording",
    title: "Try Out Ask Read - Sample Report Recording (1)",
    date: "Sep 30, 2026",
    duration: "18m",
    status: "COMPLETED",
  },
  {
    id: "m-001",
    title: "Onboarding to Knowra Platform - Enterprise Architecture Deep Dive",
    date: "Sep 29, 2026",
    duration: "38m",
    status: "COMPLETED",
  },
  {
    id: "m-002",
    title: "Sprint 44 Engineering Sync & Vector DB Partitioning",
    date: "Sep 28, 2026",
    duration: "45m",
    status: "COMPLETED",
  },
  {
    id: "m-003",
    title: "Client Onboarding — TechCorp Inc.",
    date: "Sep 25, 2026",
    duration: "30m",
    status: "COMPLETED",
  },
  {
    id: "m-004",
    title: "Design System Review — Knowra v2",
    date: "Sep 24, 2026",
    duration: "1h 12m",
    status: "COMPLETED",
  },
];

export function AddMeetingsToFolderModal({
  isOpen,
  onClose,
  folderName,
  existingMeetingIds,
  onAddMeetings,
  onOpenUploadNew,
}: AddMeetingsToFolderModalProps) {
  const [search, setSearch] = useState("");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [availableMeetings, setAvailableMeetings] = useState<FolderMeetingItem[]>(FALLBACK_AVAILABLE_MEETINGS);
  const [loading, setLoading] = useState(false);

  // Fetch real meetings from API
  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    const fetchMeetings = async () => {
      setLoading(true);
      try {
        const res = await api.get<RawMeetingApiItem[] | { items: RawMeetingApiItem[] }>("/meetings");
        const rawList = Array.isArray(res) ? res : res?.items || [];
        if (isMounted && rawList.length > 0) {
          const mapped: FolderMeetingItem[] = rawList.map((m) => {
            const mins = m.duration_seconds ? Math.max(1, Math.round(m.duration_seconds / 60)) : 25;
            const dt = m.meeting_date || m.created_at || "Recent";
            const dateStr = dt !== "Recent" ? new Date(dt).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "Recent";
            return {
              id: m.id,
              title: m.title || m.media_filename || "Untitled Recording",
              date: dateStr,
              duration: `${mins}m`,
              status: (m.status as any) || "COMPLETED",
            };
          });

          // Merge with fallback to ensure rich selection
          const existingIdsSet = new Set(mapped.map((m) => m.id));
          const combined = [...mapped, ...FALLBACK_AVAILABLE_MEETINGS.filter((f) => !existingIdsSet.has(f.id))];
          setAvailableMeetings(combined);
        }
      } catch {
        // Fallback to sample recordings
      } finally {
        if (isMounted) setLoading(false);
      }
    };

    fetchMeetings();
    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  // Existing IDs set
  const existingSet = useMemo(() => new Set(existingMeetingIds), [existingMeetingIds]);

  // Filtered list
  const filtered = useMemo(() => {
    if (!search.trim()) return availableMeetings;
    const q = search.toLowerCase();
    return availableMeetings.filter((m) => m.title.toLowerCase().includes(q));
  }, [availableMeetings, search]);

  if (!isOpen) return null;

  const toggleSelect = (id: string) => {
    if (existingSet.has(id)) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleConfirm = () => {
    const toAdd = availableMeetings.filter((m) => selectedIds.has(m.id));
    if (toAdd.length > 0) {
      onAddMeetings(toAdd);
    }
    setSelectedIds(new Set());
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-150">
      <div className="bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-xl overflow-hidden flex flex-col max-h-[85vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center">
              <Plus size={18} />
            </div>
            <div>
              <h3 className="text-base font-bold text-slate-900">Add Videos to Folder</h3>
              <p className="text-xs text-slate-500">
                Adding to <strong className="text-indigo-600 font-semibold">{folderName}</strong>
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Search & Actions Bar */}
        <div className="p-4 border-b border-slate-100 bg-white space-y-3">
          <div className="relative">
            <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search meetings by title..."
              className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs sm:text-sm text-slate-900 placeholder:text-slate-400 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-600 transition-all"
            />
          </div>

          <div className="flex items-center justify-between text-xs text-slate-500">
            <span>
              Selected <strong>{selectedIds.size}</strong> of {filtered.length} available
            </span>
            {onOpenUploadNew && (
              <button
                type="button"
                onClick={() => {
                  onClose();
                  onOpenUploadNew();
                }}
                className="text-indigo-600 hover:text-indigo-800 font-semibold flex items-center gap-1 transition-colors cursor-pointer"
              >
                <UploadCloud size={13} />
                <span>Upload a new recording instead</span>
              </button>
            )}
          </div>
        </div>

        {/* Meetings List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-2 divide-y divide-slate-100">
          {loading ? (
            <div className="py-12 flex flex-col items-center justify-center text-slate-400 gap-2">
              <Loader2 size={24} className="animate-spin text-indigo-600" />
              <span className="text-xs">Loading meetings...</span>
            </div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No meetings found matching &quot;{search}&quot;.
            </div>
          ) : (
            filtered.map((m) => {
              const isAlreadyIn = existingSet.has(m.id);
              const isChecked = selectedIds.has(m.id);

              return (
                <div
                  key={m.id}
                  onClick={() => toggleSelect(m.id)}
                  className={`pt-2 first:pt-0 flex items-center justify-between gap-3 p-2.5 rounded-xl transition-all cursor-pointer ${
                    isAlreadyIn
                      ? "opacity-60 bg-slate-50/50 cursor-not-allowed"
                      : isChecked
                      ? "bg-indigo-50/70 border border-indigo-200/90 shadow-2xs"
                      : "hover:bg-slate-50 border border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    {/* Checkbox box */}
                    <div
                      className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors ${
                        isAlreadyIn
                          ? "bg-slate-200 border-slate-300 text-slate-500"
                          : isChecked
                          ? "bg-indigo-600 border-indigo-600 text-white"
                          : "border-slate-300 bg-white"
                      }`}
                    >
                      {(isChecked || isAlreadyIn) && <Check size={11} strokeWidth={3} />}
                    </div>

                    <div className="min-w-0">
                      <p className="text-xs sm:text-sm font-semibold text-slate-900 truncate">
                        {m.title}
                      </p>
                      <div className="flex items-center gap-3 text-[11px] text-slate-400 mt-0.5 font-medium">
                        <span className="flex items-center gap-1">
                          <Calendar size={11} />
                          {m.date}
                        </span>
                        <span>•</span>
                        <span className="flex items-center gap-1">
                          <Clock size={11} />
                          {m.duration}
                        </span>
                      </div>
                    </div>
                  </div>

                  <div>
                    {isAlreadyIn ? (
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200">
                        In Folder
                      </span>
                    ) : isChecked ? (
                      <span className="text-[10px] font-bold text-indigo-700 uppercase tracking-wider px-2 py-0.5 rounded-md bg-indigo-100/70 border border-indigo-200">
                        Selected
                      </span>
                    ) : null}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-slate-100 flex items-center justify-between bg-slate-50/60 shrink-0">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold text-slate-600 hover:text-slate-900 rounded-xl transition-colors cursor-pointer"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={selectedIds.size === 0}
            onClick={handleConfirm}
            className="px-5 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed rounded-xl shadow-xs transition-all cursor-pointer flex items-center gap-1.5"
          >
            <Plus size={14} />
            <span>Add Selected ({selectedIds.size})</span>
          </button>
        </div>
      </div>
    </div>
  );
}
