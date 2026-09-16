"use client";

import { usePathname } from "next/navigation";
import { Bell, Search } from "lucide-react";
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

  // Only show title for top-level routes, not deep routes like /meetings/m-001
  const segments = pathname.split("/").filter(Boolean);
  const isDeepRoute = segments.length > 1;

  const title = isDeepRoute
    ? null
    : ROUTE_TITLES[pathname] ??
      Object.entries(ROUTE_TITLES)
        .sort(([a], [b]) => b.length - a.length)
        .find(([key]) => pathname.startsWith(key))?.[1] ??
      "Knowra";

  return (
    <header
      className="fixed top-0 left-64 right-0 h-14 z-30 flex items-center justify-between px-6"
      style={{
        background: "linear-gradient(to bottom, var(--surface-1), rgba(17,19,24,0.95))",
        backdropFilter: "blur(12px)",
        borderBottom: "1px solid var(--border)",
      }}
    >
      {/* Page Title - only show for top-level pages */}
      <div>
        {title && (
          <h1 className="text-base font-semibold text-[var(--foreground)] tracking-tight">
            {title}
          </h1>
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