"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSession } from "@/lib/auth/session";
import {
  LayoutDashboard,
  Video,
  MessageSquare,
  GitBranch,
  BarChart3,
  Plug,
  Clock,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Settings,
  User,
  CheckSquare,
  Gavel,
  CalendarPlus,
  Radio,
  Building2,
} from "lucide-react";

const NAV_SECTIONS = [
  {
    label: "Core",
    items: [
      { label: "Dashboard",  href: "/",          icon: LayoutDashboard },
      { label: "Meetings",   href: "/meetings",   icon: Video },
      { label: "Decisions",  href: "/decisions",  icon: Gavel },
      { label: "Actions",    href: "/actions",    icon: CheckSquare },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "AI Chat",         href: "/chat",       icon: MessageSquare },
      { label: "Timeline",        href: "/timeline",   icon: Clock },
      { label: "Knowledge Graph", href: "/graph",      icon: GitBranch },
      { label: "Evaluation",      href: "/evaluation", icon: BarChart3 },
    ],
  },
  {
    label: "Config",
    items: [
      { label: "Integrations", href: "/integrations", icon: Plug },
    ],
  },
] as const;

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const { session, logout } = useSession();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 h-dvh z-40 flex flex-col overflow-hidden",
        "bg-[var(--surface-1)] border-r border-[var(--border)]",
        "transition-[width] duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo + Workspace */}
      <div className="border-b border-[var(--border)] shrink-0">
        <div className="flex items-center h-14 px-4 gap-2">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white font-bold text-xs shrink-0">
            K
          </div>
          {!collapsed && (
            <span className="font-semibold text-[var(--foreground)] tracking-tight animate-fade-in">
              Knowra
            </span>
          )}
        </div>
        {!collapsed && (
          <div className="px-3 pb-3">
            <button className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--border-strong)] transition-all group">
              <Building2 size={12} className="text-[var(--muted)] shrink-0" />
              <span className="flex-1 text-left text-[11px] text-[var(--muted-strong)] truncate">
                {session?.user.email?.split("@")[1] ?? "softude.com"}
              </span>
              <ChevronRight size={10} className="text-[var(--muted)] group-hover:text-[var(--foreground)] transition-colors shrink-0" />
            </button>
          </div>
        )}
      </div>

      {/* Nav Items — scrollable */}
      <nav className="flex-1 py-2 px-2 overflow-y-auto min-h-0">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-3">
            {!collapsed && (
              <p className="px-3 pt-2 pb-1 text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const Icon = item.icon;
                const isActive =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    title={collapsed ? item.label : undefined}
                    className={cn(
                      "flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)]",
                      "transition-all duration-150",
                      isActive
                        ? "bg-[var(--primary-muted)] text-[var(--primary)]"
                        : "text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]"
                    )}
                  >
                    <Icon size={15} className={cn("shrink-0", isActive ? "text-[var(--primary)]" : "text-current")} />
                    {!collapsed && (
                      <span className="truncate text-[13px] font-medium">{item.label}</span>
                    )}
                    {isActive && !collapsed && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[var(--primary)]" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom: CTAs + Settings + User — fixed height, never overflows */}
      <div className="border-t border-[var(--border)] shrink-0">
        {!collapsed && (
          <div className="px-2 pt-2 space-y-0.5">
            <button className="w-full flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius-sm)] text-[11px] font-medium text-[var(--primary)] hover:bg-[var(--primary-muted)] transition-colors">
              <CalendarPlus size={13} className="shrink-0" />
              Smart Scheduler
            </button>
            <button className="w-full flex items-center gap-2 px-3 py-1.5 rounded-[var(--radius-sm)] text-[11px] font-medium text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)] transition-colors">
              <Radio size={12} className="shrink-0 text-[var(--danger)]" />
              Add to Live Meeting
            </button>
          </div>
        )}

        <div className="px-2 pb-2 pt-1 space-y-0.5">
          <Link
            href="/settings"
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-[var(--radius-sm)]",
              "text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]",
              "transition-all duration-150"
            )}
          >
            <Settings size={14} className="shrink-0" />
            {!collapsed && <span className="text-[13px] font-medium">Settings</span>}
          </Link>

          {session && (
            <div className="flex items-center gap-2 px-3 py-2">
              <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white text-[10px] font-semibold shrink-0">
                {session.user.full_name?.charAt(0) ?? <User size={10} />}
              </div>
              {!collapsed && (
                <>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] font-medium text-[var(--foreground)] truncate">{session.user.full_name}</p>
                    <p className="text-[9px] text-[var(--muted)] truncate uppercase tracking-wider">{session.user.role_code}</p>
                  </div>
                  <button onClick={logout} title="Sign out" className="p-1 rounded text-[var(--muted)] hover:text-[var(--danger)] transition-colors shrink-0">
                    <LogOut size={13} />
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={() => setCollapsed((c) => !c)}
        className={cn(
          "absolute top-[50%] -right-3 w-6 h-6 rounded-full",
          "bg-[var(--surface-2)] border border-[var(--border-strong)]",
          "flex items-center justify-center text-[var(--muted-strong)]",
          "hover:bg-[var(--surface-3)] hover:text-[var(--foreground)]",
          "transition-all duration-200 shadow-md z-10"
        )}
        aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        {collapsed ? <ChevronRight size={12} /> : <ChevronLeft size={12} />}
      </button>
    </aside>
  );
}