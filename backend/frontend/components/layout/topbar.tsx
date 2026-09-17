"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Bell, Search, ChevronLeft } from "lucide-react";
import { Input } from "@/components/ui/card";

const ROUTE_TITLES: Record<string, string> = {
  "/": "Dashboard",
  "/meetings": "Meetings",
  "/chat": "AI Chat",
  "/timeline": "Timeline",
  "/graph": "Knowledge Graph",
  "/evaluation": "AI Evaluation",
  "/integrations": "Integrations",
  "/settings": "Settings",
  "/decisions": "Decisions",
  "/actions": "Actions",
};

export function Topbar() {
  const pathname = usePathname();
  const segments = pathname.split("/").filter(Boolean);
  const isMeetingDetail = pathname.startsWith("/meetings/") && segments.length > 1;

  // On meeting detail pages, DetailHeader acts as the header directly matching reference
  if (isMeetingDetail) {
    return null;
  }

  // On /meetings list page, render the exact dark navy bar matching Image 1 (< Reports)
  if (pathname === "/meetings") {
    return (
      <header
        className="fixed top-0 right-0 h-13 z-30 flex items-center px-6 bg-[#0c0e22] text-white border-b border-slate-800/80 transition-[left] duration-200 ease-in-out select-none shadow-xs"
        style={{ left: "var(--sidebar-current)" }}
      >
        <Link
          href="/"
          className="flex items-center gap-2 text-white hover:text-slate-200 font-bold text-base tracking-tight transition-colors"
        >
          <ChevronLeft className="w-5 h-5 text-white stroke-[2.5]" />
          <span>Reports</span>
        </Link>
      </header>
    );
  }

  const title =
    ROUTE_TITLES[pathname] ??
    Object.entries(ROUTE_TITLES)
      .sort(([a], [b]) => b.length - a.length)
      .find(([key]) => pathname.startsWith(key))?.[1] ??
    "Knowra";

  return (
    <header
      className="fixed top-0 right-0 h-14 z-30 flex items-center justify-between px-8 bg-white/95 backdrop-blur-md border-b border-slate-200 transition-[left] duration-200 ease-in-out"
      style={{ left: "var(--sidebar-current)" }}
    >
      {/* Page Title */}
      <div>
        {title && (
          <span className="text-[15px] font-semibold text-[var(--foreground)] tracking-tight">
            {title}
          </span>
        )}
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3 ml-auto">
        <div className="w-56">
          <Input
            placeholder="Search meetings, decisions…"
            leftIcon={<Search size={13} />}
            className="h-8 text-xs"
          />
        </div>
        <button
          className="relative p-2 rounded-[var(--radius-sm)] text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)] transition-colors"
          aria-label="Notifications"
          id="topbar-notifications-btn"
        >
          <Bell size={16} />
          <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full bg-[var(--primary)]" />
        </button>
      </div>
    </header>
  );
}