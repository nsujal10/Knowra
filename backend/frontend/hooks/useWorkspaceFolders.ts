"use client";

import { useState, useEffect, useCallback } from "react";
import { WorkspaceFolder, DEFAULT_WORKSPACE_FOLDERS } from "@/lib/data/folders";

const STORAGE_KEY = "knowra_workspace_folders_v1";

// Legacy seed folder IDs that should be purged from localStorage
const SEED_FOLDER_IDS = new Set([
  "f-engineering",
  "f-executive",
  "f-product",
  "f-sales",
  "f-uploads",
  "f-confidential",
]);

export interface FolderMeetingItem {
  id: string;
  title: string;
  date: string;
  duration: string;
  status: "COMPLETED" | "PROCESSING" | "RECORDING";
}

export function useWorkspaceFolders() {
  const [folders, setFolders] = useState<WorkspaceFolder[]>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem(STORAGE_KEY);
        if (saved) {
          const parsed = JSON.parse(saved);
          if (Array.isArray(parsed)) {
            // Filter out any legacy seed/mock folders
            const cleanUserFolders = parsed.filter((f) => !SEED_FOLDER_IDS.has(f.id));
            return cleanUserFolders;
          }
        }
      } catch {
        // fallback
      }
    }
    return DEFAULT_WORKSPACE_FOLDERS;
  });

  // Sync to localStorage and broadcast event
  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(folders));
        window.dispatchEvent(new CustomEvent("knowra-folders-updated", { detail: folders }));
      } catch {
        // ignore
      }
    }
  }, [folders]);

  // Listen to cross-component updates (e.g. sidebar and page sync)
  useEffect(() => {
    const handleUpdate = (e: Event) => {
      const customEvent = e as CustomEvent<WorkspaceFolder[]>;
      if (customEvent.detail && Array.isArray(customEvent.detail)) {
        setFolders(customEvent.detail);
      }
    };
    window.addEventListener("knowra-folders-updated", handleUpdate);
    return () => window.removeEventListener("knowra-folders-updated", handleUpdate);
  }, []);

  const addFolder = useCallback(
    (newFolder: Omit<WorkspaceFolder, "id" | "updatedAt" | "meetingCount" | "decisionsCount" | "actionsCount" | "recentMeetings">) => {
      const folder: WorkspaceFolder = {
        ...newFolder,
        id: `f-${Date.now()}`,
        meetingCount: 0,
        decisionsCount: 0,
        actionsCount: 0,
        updatedAt: "Just now",
        recentMeetings: [],
      };
      setFolders((prev) => [folder, ...prev]);
      return folder;
    },
    []
  );

  const deleteFolder = useCallback((folderId: string) => {
    setFolders((prev) => prev.filter((f) => f.id !== folderId));
  }, []);

  const updateFolder = useCallback((folderId: string, updates: Partial<WorkspaceFolder>) => {
    setFolders((prev) =>
      prev.map((f) => (f.id === folderId ? { ...f, ...updates, updatedAt: "Just now" } : f))
    );
  }, []);

  // Add multiple meetings into a specific folder
  const addMeetingsToFolder = useCallback((folderId: string, newMeetings: FolderMeetingItem[]) => {
    setFolders((prev) =>
      prev.map((f) => {
        if (f.id !== folderId) return f;
        const existingIds = new Set(f.recentMeetings.map((m) => m.id));
        const filteredNew = newMeetings.filter((m) => !existingIds.has(m.id));
        const updatedList = [...filteredNew, ...f.recentMeetings];
        return {
          ...f,
          recentMeetings: updatedList,
          meetingCount: updatedList.length,
          updatedAt: "Just now",
        };
      })
    );
  }, []);

  // Add single meeting to folder
  const addMeetingToFolder = useCallback((folderId: string, meeting: FolderMeetingItem) => {
    addMeetingsToFolder(folderId, [meeting]);
  }, [addMeetingsToFolder]);

  // Remove meeting from a folder
  const removeMeetingFromFolder = useCallback((folderId: string, meetingId: string) => {
    setFolders((prev) =>
      prev.map((f) => {
        if (f.id !== folderId) return f;
        const updatedList = f.recentMeetings.filter((m) => m.id !== meetingId);
        return {
          ...f,
          recentMeetings: updatedList,
          meetingCount: updatedList.length,
          updatedAt: "Just now",
        };
      })
    );
  }, []);

  return {
    folders,
    addFolder,
    deleteFolder,
    updateFolder,
    addMeetingToFolder,
    addMeetingsToFolder,
    removeMeetingFromFolder,
  };
}
