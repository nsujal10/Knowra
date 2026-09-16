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
      { label: "Dashboard",  href: "/",          icon: LayoutDashboard, description: "Overview & metrics" },
      { label: "Meetings",   href: "/meetings",   icon: Video,           description: "All meetings" },
      { label: "Decisions",  href: "/decisions",  icon: Gavel,           description: "Key decisions" },
      { label: "Actions",    href: "/actions",    icon: CheckSquare,     description: "Action items" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { label: "AI Chat",         href: "/chat",       icon: MessageSquare, description: "RAG-powered chat" },
      { label: "Timeline",        href: "/timeline",   icon: Clock,         description: "Cross-meeting events" },
      { label: "Knowledge Graph", href: "/graph",      icon: GitBranch,     description: "Org intelligence" },
      { label: "Evaluation",      href: "/evaluation", icon: BarChart3,     description: "AI quality metrics" },
    ],
  },
  {
    label: "Config",
    items: [
      { label: "Integrations", href: "/integrations", icon: Plug, description: "Slack, Jira, Webhooks" },
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
        "fixed left-0 top-0 h-dvh z-40 flex flex-col",
        "bg-[var(--surface-1)] border-r border-[var(--border)]",
        "transition-[width] duration-300 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo + Workspace */}
      <div className="border-b border-[var(--border)] shrink-0">
        <div className="flex items-center h-14 px-4">
          {!collapsed && (
            <div className="flex items-center gap-2 animate-fade-in flex-1 min-w-0">
              <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white font-bold text-xs shrink-0">
                K
              </div>
              <span className="font-semibold text-[var(--foreground)] tracking-tight">Knowra</span>
            </div>
          )}
          {collapsed && (
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white font-bold text-xs mx-auto">
              K
            </div>
          )}
        </div>
        {!collapsed && (
          <div className="px-3 pb-3">
            <button className="w-full flex items-center gap-2 px-2.5 py-2 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--border-strong)] transition-all group">
              <Building2 size={13} className="text-[var(--muted)] shrink-0" />
              <span className="flex-1 text-left text-xs text-[var(--muted-strong)] truncate">
                {session?.user.email?.split("@")[1] ?? "softude.com"}
              </span>
              <ChevronRight size={11} className="text-[var(--muted)] group-hover:text-[var(--foreground)] transition-colors" />
            </button>
          </div>
        )}
      </div>

      {/* Nav Items */}
      <nav className="flex-1 py-3 px-2 overflow-y-auto space-y-4">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label}>
            {!collapsed && (
              <p className="px-3 pb-1 text-[9px] font-semibold uppercase tracking-widest text-[var(--muted)]">
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
                      "flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-sm)]",
                      "text-sm transition-all duration-150 group",
                      isActive
                        ? "bg-[var(--primary-muted)] text-[var(--primary)]"
                        : "text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]"
                    )}
                  >
                    <Icon size={15} className={cn("shrink-0 transition-colors", isActive ? "text-[var(--primary)]" : "text-current")} />
                    {!collapsed && <span className="truncate font-medium text-[13px]">{item.label}</span>}
                    {isActive && !collapsed && <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[var(--primary)]" />}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Bottom CTA + User Section */}
      <div className="border-t border-[var(--border)] p-2 space-y-1 shrink-0">
        {!collapsed && (
          <>
            <button className="w-full flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] text-xs font-medium text-[var(--primary)] hover:bg-[var(--primary-muted)] transition-colors">
              <CalendarPlus size={13} className="shrink-0" />
              Smart Scheduler
            </button>
            <button className="w-full flex items-center gap-2 px-3 py-2 rounded-[var(--radius-sm)] text-xs font-medium text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)] transition-colors">
              <Radio size={13} className="shrink-0 text-[var(--danger)]" />
              Add to Live Meeting
            </button>
          </>
        )}

        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-sm)]",
            "text-sm text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]",
            "transition-all duration-150"
          )}
        >
          <Settings size={15} className="shrink-0" />
          {!collapsed && <span className="font-medium text-[13px]">Settings</span>}
        </Link>

        {session && !collapsed && (
          <div className="flex items-center gap-2 px-3 py-2 mt-1">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white text-[10px] font-semibold shrink-0">
              {session.user.full_name?.charAt(0) ?? <User size={10} />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--foreground)] truncate">{session.user.full_name}</p>
              <p className="text-[10px] text-[var(--muted)] truncate">{session.user.role_code}</p>
            </div>
            <button onClick={logout} title="Sign out" className="p-1 rounded text-[var(--muted)] hover:text-[var(--danger)] transition-colors">
              <LogOut size={14} />
            </button>
          </div>
        )}
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
