"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search,
  ChevronRight,
  Plus,
  Sparkles,
  Video,
  CheckSquare,
  ListTodo,
  LayoutDashboard,
  ShieldCheck,
  GitBranch,
  BarChart3,
  Layers,
  Settings,
  Folder,
  Command,
  Building2,
} from "lucide-react";
import { CommandPalette } from "./command-palette";
import { NotificationPopover } from "./notification-popover";
import { UserMenu } from "./user-menu";
import { UploadMeetingModal } from "@/components/meetings/UploadMeetingModal";

interface RouteConfig {
  title: string;
  subtitle: string;
  category: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
}

const ROUTE_CONFIG: Record<string, RouteConfig> = {
  "/": {
    title: "Executive Dashboard",
    subtitle: "Overview & Intelligence",
    category: "Workspace",
    icon: LayoutDashboard,
  },
  "/chat": {
    title: "Ask Knowra",
    subtitle: "AI Copilot & Synthesis",
    category: "Intelligence",
    icon: Sparkles,
  },
  "/meetings": {
    title: "Meetings Intelligence",
    subtitle: "Recordings & Transcripts",
    category: "Recordings",
    icon: Video,
  },
  "/decisions": {
    title: "Decisions Registry",
    subtitle: "Consensus & Resolutions",
    category: "Governance",
    icon: CheckSquare,
  },
  "/actions": {
    title: "Action Items",
    subtitle: "Deliverables & Commitments",
    category: "Execution",
    icon: ListTodo,
  },
  "/evaluation": {
    title: "AI Quality & Governance",
    subtitle: "Evaluation & Benchmarks",
    category: "Governance",
    icon: ShieldCheck,
  },
  "/graph": {
    title: "Knowledge Graph",
    subtitle: "Entity & Topic Network",
    category: "Intelligence",
    icon: GitBranch,
  },
  "/timeline": {
    title: "Timeline & Analytics",
    subtitle: "Cross-Meeting Trends",
    category: "Analytics",
    icon: BarChart3,
  },
  "/integrations": {
    title: "Enterprise Connectors",
    subtitle: "Webhooks & Sync",
    category: "Workspace",
    icon: Layers,
  },
  "/settings": {
    title: "Settings & RBAC",
    subtitle: "Organization & Policies",
    category: "Administration",
    icon: Settings,
  },
  "/folders": {
    title: "Workspace Folders",
    subtitle: "Collections & Archives",
    category: "Workspace",
    icon: Folder,
  },
};

export function Topbar() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const isMeetingDetail = pathname.startsWith("/meetings/") && segments.length > 1;

  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Global keyboard shortcut for Command Palette (⌘K / Ctrl+K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // On meeting detail pages, DetailHeader acts as the header directly
  if (isMeetingDetail) {
    return null;
  }

  // Determine active route config
  const activeRoute =
    ROUTE_CONFIG[pathname] ??
    Object.entries(ROUTE_CONFIG)
      .sort(([a], [b]) => b.length - a.length)
      .find(([key]) => pathname.startsWith(key))?.[1] ?? {
      title: "Knowra Workspace",
      subtitle: "Enterprise Intelligence",
      category: "Workspace",
      icon: LayoutDashboard,
    };

  const RouteIcon = activeRoute.icon;

  return (
    <>
      <header
        className="fixed top-0 right-0 h-14 z-30 flex items-center justify-between px-5 sm:px-6 lg:px-8 bg-white/95 backdrop-blur-md border-b border-slate-200/90 transition-[left] duration-200 ease-in-out select-none shadow-2xs"
        style={{ left: "var(--sidebar-current)" }}
      >
        {/* ── LEFT: ENTERPRISE BREADCRUMBS & CONTEXT ───────────────────────── */}
        <div className="flex items-center gap-2.5 min-w-0">
          {/* Workspace Root Pill */}
          <Link
            href="/"
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-100/80 hover:bg-slate-200/70 text-slate-600 hover:text-slate-900 transition-colors text-xs font-semibold shrink-0"
            title="Knowra Enterprise Workspace"
          >
            <Building2 size={13} className="text-slate-500" />
            <span className="tracking-tight">Knowra</span>
          </Link>

          <ChevronRight
            size={13}
            className="text-slate-300 hidden sm:inline-block shrink-0"
          />

          {/* Current Page Identity */}
          <div className="flex items-center gap-2 min-w-0">
            <div className="w-7 h-7 rounded-lg bg-indigo-50 border border-indigo-100/80 flex items-center justify-center text-indigo-600 shrink-0 shadow-2xs">
              <RouteIcon size={14} />
            </div>

            <div className="flex items-center gap-2 min-w-0">
              <span className="text-sm font-bold text-slate-900 tracking-tight truncate">
                {activeRoute.title}
              </span>
              <span className="hidden md:inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-medium bg-slate-100 text-slate-500 border border-slate-200/80">
                {activeRoute.category}
              </span>
            </div>
          </div>
        </div>

        {/* ── CENTER: GLOBAL COMMAND PALETTE SEARCH TRIGGER ───────────────── */}
        <div className="flex-1 max-w-md mx-4 hidden md:block">
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            className="w-full h-8.5 px-3 rounded-xl border border-slate-200/90 bg-slate-50/70 hover:bg-white hover:border-indigo-300/80 hover:shadow-2xs text-left text-xs text-slate-400 flex items-center justify-between transition-all group cursor-pointer"
            title="Press ⌘K or Ctrl+K to search anything"
          >
            <div className="flex items-center gap-2 truncate">
              <Search
                size={13}
                className="text-slate-400 group-hover:text-indigo-600 transition-colors shrink-0"
              />
              <span className="truncate group-hover:text-slate-600">
                Search meetings, decisions, actions...
              </span>
            </div>
            <div className="flex items-center gap-1 shrink-0">
              <kbd className="hidden lg:inline-flex items-center gap-0.5 px-1.5 py-0.5 text-[10px] font-mono font-medium text-slate-400 bg-white border border-slate-200 rounded-md shadow-2xs">
                <Command size={10} />
                <span>K</span>
              </kbd>
            </div>
          </button>
        </div>

        {/* ── RIGHT: ENTERPRISE CONTROLS & USER MENU ──────────────────────── */}
        <div className="flex items-center gap-2 sm:gap-2.5 ml-auto shrink-0">
          {/* Mobile Search Button */}
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            className="md:hidden p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Search"
          >
            <Search size={16} />
          </button>

          {/* Quick Action: New Meeting Upload */}
          <button
            type="button"
            onClick={() => setUploadModalOpen(true)}
            className="hidden sm:inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs hover:shadow-sm transition-all cursor-pointer"
            title="Upload audio/video meeting recording"
          >
            <Plus size={13} className="stroke-[2.5]" />
            <span>New Meeting</span>
          </button>

          {/* Ask Knowra Shortcut Button */}
          <Link
            href="/chat"
            className="hidden xl:inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs transition-colors"
            title="Open AI Copilot"
          >
            <Sparkles size={12} className="text-indigo-600" />
            <span>Ask Knowra</span>
          </Link>

          {/* AI Engine Status Dot */}
          <div
            className="hidden lg:flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-50/80 border border-emerald-200/80 text-[11px] font-medium text-emerald-700"
            title="AI Engine, vector index, and transcription pipeline online"
          >
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="tracking-tight">Online</span>
          </div>

          {/* Divider */}
          <div className="h-5 w-px bg-slate-200/90 mx-0.5 shrink-0" />

          {/* Notifications Popover */}
          <NotificationPopover />

          {/* User Profile Menu */}
          <UserMenu onOpenCommandPalette={() => setCommandPaletteOpen(true)} />
        </div>
      </header>

      {/* Global Command Palette Modal */}
      <CommandPalette
        isOpen={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
        onOpenUpload={() => setUploadModalOpen(true)}
      />

      {/* Global Meeting Upload Modal */}
      <UploadMeetingModal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
      />
    </>
  );
}