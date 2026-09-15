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
} from "lucide-react";

const NAV_ITEMS = [
  {
    label: "Dashboard",
    href: "/",
    icon: LayoutDashboard,
    description: "Overview & metrics",
  },
  {
    label: "Meetings",
    href: "/meetings",
    icon: Video,
    description: "All meetings",
  },
  {
    label: "AI Chat",
    href: "/chat",
    icon: MessageSquare,
    description: "RAG-powered chat",
  },
  {
    label: "Timeline",
    href: "/timeline",
    icon: Clock,
    description: "Cross-meeting events",
  },
  {
    label: "Knowledge Graph",
    href: "/graph",
    icon: GitBranch,
    description: "Org intelligence",
  },
  {
    label: "Evaluation",
    href: "/evaluation",
    icon: BarChart3,
    description: "AI quality metrics",
  },
  {
    label: "Integrations",
    href: "/integrations",
    icon: Plug,
    description: "Slack, Jira, Webhooks",
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
      {/* Logo */}
      <div className="flex items-center h-14 px-4 border-b border-[var(--border)] shrink-0">
        {!collapsed && (
          <div className="flex items-center gap-2 animate-fade-in">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white font-bold text-xs">
              K
            </div>
            <span className="font-semibold text-[var(--foreground)] tracking-tight">
              Knowra
            </span>
            {session?.user.tenant_id && (
              <span className="ml-auto text-[10px] text-[var(--muted)] font-mono truncate max-w-[80px]">
                {session.user.tenant_id.slice(0, 8)}
              </span>
            )}
          </div>
        )}
        {collapsed && (
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white font-bold text-xs mx-auto">
            K
          </div>
        )}
      </div>

      {/* Nav Items */}
      <nav className="flex-1 py-4 px-2 space-y-0.5 overflow-y-auto">
        {NAV_ITEMS.map((item) => {
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
                "text-sm transition-all duration-150 group relative",
                isActive
                  ? "bg-[var(--primary-muted)] text-[var(--primary)]"
                  : "text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]"
              )}
            >
              <Icon
                size={16}
                className={cn(
                  "shrink-0 transition-colors",
                  isActive ? "text-[var(--primary)]" : "text-current"
                )}
              />
              {!collapsed && (
                <span className="truncate font-medium">{item.label}</span>
              )}
              {isActive && !collapsed && (
                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-[var(--primary)]" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* User Section */}
      <div className="border-t border-[var(--border)] p-2 space-y-0.5 shrink-0">
        <Link
          href="/settings"
          className={cn(
            "flex items-center gap-3 px-3 py-2.5 rounded-[var(--radius-sm)]",
            "text-sm text-[var(--muted-strong)] hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]",
            "transition-all duration-150"
          )}
        >
          <Settings size={16} className="shrink-0" />
          {!collapsed && <span className="font-medium">Settings</span>}
        </Link>

        {session && !collapsed && (
          <div className="flex items-center gap-2 px-3 py-2 mt-1">
            <div className="w-6 h-6 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center text-white text-[10px] font-semibold shrink-0">
              {session.user.full_name?.charAt(0) ?? <User size={10} />}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-medium text-[var(--foreground)] truncate">
                {session.user.full_name}
              </p>
              <p className="text-[10px] text-[var(--muted)] truncate">
                {session.user.role_code}
              </p>
            </div>
            <button
              onClick={logout}
              title="Sign out"
              className="p-1 rounded text-[var(--muted)] hover:text-[var(--danger)] transition-colors"
            >
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
