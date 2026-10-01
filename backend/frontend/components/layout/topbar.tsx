"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { ChevronLeft, Search } from "lucide-react";
import { CommandPalette } from "./command-palette";
import { NotificationPopover } from "./notification-popover";
import { UploadMeetingModal } from "@/components/meetings/UploadMeetingModal";

const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/meetings": "Meetings",
  "/folders": "Folders",
  "/chat": "Ask Knowra",
  "/decisions": "Decisions",
  "/actions": "Actions",
  "/evaluation": "AI Evaluation",
  "/graph": "Knowledge Graph",
  "/timeline": "Analytics",
  "/integrations": "Integrations",
  "/settings": "Settings",
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

  // Determine active route title matching Image 2 (< Folders, < Meetings, etc.)
  const activeTitle =
    ROUTE_TITLES[pathname] ??
    Object.entries(ROUTE_TITLES)
      .sort(([a], [b]) => b.length - a.length)
      .find(([key]) => pathname.startsWith(key))?.[1] ??
    "Knowra";

  return (
    <>
      <header
        className="fixed top-0 right-0 h-14 z-30 flex items-center justify-between px-6 sm:px-8 bg-[#181640] text-white border-b border-white/[0.08] transition-[left] duration-200 ease-in-out select-none shadow-xs"
        style={{ left: "var(--sidebar-current)" }}
      >
        {/* ── LEFT: CLEAN ENTERPRISE BACK NAVIGATION (MATCHING SIDEBAR THEME) ─── */}
        <div className="flex items-center gap-3 min-w-0">
          {pathname === "/" ? (
            <div className="flex items-center gap-2.5 text-white">
              <span className="font-bold text-base md:text-[17px] tracking-tight text-white leading-tight">
                {activeTitle}
              </span>
            </div>
          ) : (
            <Link
              href="/"
              className="flex items-center gap-2.5 text-white hover:text-slate-200 transition-colors group cursor-pointer"
              title="Back to Dashboard"
            >
              <ChevronLeft className="w-4 h-4 text-slate-300 group-hover:text-white stroke-[2.5] transition-all group-hover:-translate-x-0.5 shrink-0" />
              <span className="font-bold text-base md:text-[17px] tracking-tight text-white leading-tight">
                {activeTitle}
              </span>
            </Link>
          )}
        </div>

        {/* ── RIGHT: SLEEK, UNOBTRUSIVE ENTERPRISE TOOLS ───────────────────── */}
        <div className="flex items-center gap-3 ml-auto shrink-0">
          {/* Subtle Command Palette Trigger */}
          <button
            type="button"
            onClick={() => setCommandPaletteOpen(true)}
            className="flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-white/[0.07] hover:bg-white/[0.12] text-slate-200 hover:text-white text-xs sm:text-[13px] font-medium border border-white/[0.1] transition-all cursor-pointer shadow-2xs hover:border-white/20"
            title="Search workspace (⌘K)"
          >
            <Search size={14} className="text-slate-300 shrink-0" />
            <span className="text-slate-200 font-medium">Search</span>
            <kbd className="hidden sm:inline-flex text-[11px] font-mono font-medium text-slate-300 bg-white/[0.1] px-1.5 py-0.5 rounded border border-white/[0.15]">
              ⌘K
            </kbd>
          </button>

          {/* Notifications */}
          <NotificationPopover variant="dark" />
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