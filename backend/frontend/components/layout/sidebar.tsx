"use client";

import React, { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSession } from "@/lib/auth/session";
import {
  BrainCircuit,
  Sparkles,
  Video,
  CheckSquare,
  ListTodo,
  AlertTriangle,
  Folder,
  Plus,
  Layers,
  GitBranch,
  BarChart3,
  ShieldCheck,
  PlusCircle,
  ChevronRight,
  ChevronLeft,
  ChevronDown,
  LogOut,
  Languages,
} from "lucide-react";
import { useWorkspaceFolders } from "@/hooks/useWorkspaceFolders";
import { CreateFolderModal } from "@/components/meetings/CreateFolderModal";

export interface NavItem {
  label: string;
  href: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  hasPlus?: boolean;
}

// ─── Primary Domain Routes ───────────────────────────────────────────────────
const PRIMARY_NAV_ITEMS: NavItem[] = [
  { label: "Ask Knowra",    href: "/chat",         icon: Sparkles },
  { label: "Meetings",      href: "/meetings",     icon: Video },
  { label: "Decisions",     href: "/decisions",    icon: CheckSquare },
  { label: "Actions",       href: "/actions",      icon: ListTodo },
  { label: "Risks",         href: "/evaluation",   icon: AlertTriangle },
  { label: "Folders",       href: "/folders",      icon: Folder, hasPlus: true },
  { label: "Integrations",  href: "/integrations", icon: Layers },
];

// ─── Secondary Workspace Routes ──────────────────────────────────────────────
const SECONDARY_NAV_ITEMS: NavItem[] = [
  { label: "Knowledge Graph", href: "/graph",      icon: GitBranch },
  { label: "Analytics",       href: "/timeline",   icon: BarChart3 },
  { label: "Meeting Policy",  href: "/settings",   icon: ShieldCheck },
];

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [createFolderOpen, setCreateFolderOpen] = useState(false);
  const [foldersExpanded, setFoldersExpanded] = useState(true);
  const { folders, addFolder } = useWorkspaceFolders();
  const pathname = usePathname();
  const { session, logout } = useSession();

  const userName = session?.user?.full_name || "Sujal Nage";
  const userEmail = session?.user?.email || "sujal.nage@softude.com";

  const isLinkActive = (href: string) => {
    if (href === "/chat") return pathname === "/chat";
    if (href === "/meetings") {
      return (
        pathname === "/meetings" ||
        (pathname.startsWith("/meetings") &&
          !pathname.includes("/decisions") &&
          !pathname.includes("/actions") &&
          !pathname.includes("/folders"))
      );
    }
    return pathname === href || pathname.startsWith(href);
  };

  return (
    <>
    <aside
      className={cn(
        "fixed left-0 top-0 h-screen z-50 flex flex-col justify-between font-sans select-none",
        "bg-[#181640] text-slate-300 border-r border-white/[0.08]",
        "transition-[width] duration-200 ease-in-out",
        collapsed ? "w-16" : "w-64"
      )}
      style={{ width: collapsed ? 64 : 256 }}
    >
      {/* ── TOP: BRAND HEADER (EXACT 56px H-14 MATCHING TOPBAR) ────────────── */}
      <div className="h-14 shrink-0 px-4 flex items-center justify-between border-b border-white/[0.08]">
        <Link href="/" className="flex items-center gap-2.5 min-w-0 group">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-tr from-blue-500 via-indigo-600 to-violet-600 flex items-center justify-center text-white shadow-sm shrink-0 transition-transform group-hover:scale-105">
            <BrainCircuit size={16} className="text-white" />
          </div>

          {!collapsed && (
            <span className="font-bold text-base md:text-[17px] tracking-tight text-white truncate leading-tight">
              Knowra
            </span>
          )}
        </Link>

        {!collapsed ? (
          <div className="flex items-center gap-1 text-slate-400">
            <button
              type="button"
              className="flex items-center gap-1 text-xs font-medium hover:text-white px-1.5 py-1 rounded hover:bg-white/[0.08] transition-colors cursor-pointer"
              title="Language"
            >
              <Languages size={13} />
              <span className="text-[11px] font-semibold">EN</span>
            </button>
            <button
              type="button"
              onClick={() => setCollapsed(true)}
              className="p-1.5 hover:text-white transition-colors cursor-pointer rounded hover:bg-white/[0.08] text-slate-400"
              title="Collapse sidebar"
            >
              <ChevronLeft size={16} />
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => setCollapsed(false)}
            className="w-full flex justify-center text-slate-400 hover:text-white cursor-pointer"
            title="Expand sidebar"
          >
            <ChevronRight size={16} />
          </button>
        )}
      </div>

      {/* ── MIDDLE: NAVIGATION (ENTERPRISE 12px INSET & CLEAN 6px RADIUS PILL) ─── */}
      <nav className="flex-1 overflow-y-auto px-3 py-3 space-y-1 [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
        {/* Primary Domain Routes */}
        <div className="space-y-1">
          {PRIMARY_NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isLinkActive(item.href);
            const isFolders = item.href === "/folders";

            return (
              <React.Fragment key={item.label}>
                <div
                  className={cn(
                    "flex items-center gap-2 px-3 h-9 text-[13px] font-medium transition-all group rounded-md w-full",
                    collapsed && "justify-center px-0",
                    active
                      ? "bg-[#4c47cc] text-white shadow-xs font-semibold"
                      : "text-slate-300 hover:text-white hover:bg-white/[0.06]"
                  )}
                >
                  {/* Left Icon: Dropdown Chevron for Folders when expanded */}
                  {isFolders && !collapsed ? (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setFoldersExpanded((prev) => !prev);
                      }}
                      className="p-1 -ml-1 rounded hover:bg-white/10 text-slate-300 hover:text-white transition-colors cursor-pointer shrink-0"
                      title={foldersExpanded ? "Collapse folders dropdown" : "Expand folders dropdown"}
                    >
                      {foldersExpanded ? (
                        <ChevronDown size={14} strokeWidth={2.5} className="text-slate-200" />
                      ) : (
                        <ChevronRight size={14} strokeWidth={2.5} className="text-slate-200" />
                      )}
                    </button>
                  ) : (
                    <Icon
                      size={16}
                      className={cn(
                        "shrink-0 transition-colors",
                        active ? "text-white" : "text-slate-400 group-hover:text-white"
                      )}
                    />
                  )}

                  {/* Main Link Text */}
                  {!collapsed && (
                    <Link
                      href={item.href}
                      onClick={() => {
                        if (isFolders) setFoldersExpanded(true);
                      }}
                      className="truncate flex-1 leading-none text-inherit hover:text-inherit"
                    >
                      {item.label}
                    </Link>
                  )}

                  {/* Plus Icon Action on Right */}
                  {!collapsed && item.hasPlus && (
                    <button
                      type="button"
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setCreateFolderOpen(true);
                      }}
                      className="p-1 -mr-1 rounded hover:bg-white/[0.15] text-slate-400 hover:text-white transition-colors cursor-pointer shrink-0 ml-auto"
                      title="Create New Folder"
                    >
                      <Plus size={13} strokeWidth={2.5} />
                    </button>
                  )}
                </div>

                {/* Sub-list of workspace folders when expanded */}
                {!collapsed && isFolders && foldersExpanded && (
                  <div className="pl-6 pr-1 py-1 space-y-0.5 animate-in fade-in duration-150">
                    {folders.length === 0 ? (
                      <button
                        type="button"
                        onClick={() => setCreateFolderOpen(true)}
                        className="w-full flex items-center gap-2 px-2 py-1 rounded text-[11px] text-slate-400 hover:text-indigo-300 hover:bg-white/[0.04] transition-colors cursor-pointer"
                      >
                        <Plus size={11} />
                        <span>Create first folder</span>
                      </button>
                    ) : (
                      folders.map((f) => (
                        <Link
                          key={f.id}
                          href="/folders"
                          className="flex items-center justify-between px-2 py-1 rounded text-xs text-slate-400 hover:text-white hover:bg-white/[0.04] transition-colors group/sub"
                          title={f.name}
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span
                              className="w-1.5 h-1.5 rounded-full shrink-0"
                              style={{ backgroundColor: f.color }}
                            />
                            <span className="truncate text-[11px] font-medium">{f.name}</span>
                          </div>
                          <span className="text-[10px] text-slate-500 font-mono group-hover/sub:text-slate-300">
                            {f.meetingCount}
                          </span>
                        </Link>
                      ))
                    )}
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>

        {/* Secondary Workspace Routes */}
        {!collapsed && (
          <div className="pt-3 mt-3 border-t border-white/[0.08] space-y-1">
            <p className="px-3 pb-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              Workspace
            </p>
            {SECONDARY_NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const active = isLinkActive(item.href);

              return (
                <Link
                  key={item.label}
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 h-9 text-[13px] font-medium transition-all group rounded-md w-full",
                    active
                      ? "bg-[#4c47cc] text-white shadow-xs font-semibold"
                      : "text-slate-300 hover:text-white hover:bg-white/[0.06]"
                  )}
                >
                  <Icon
                    size={16}
                    className={cn(
                      "shrink-0 transition-colors",
                      active ? "text-white" : "text-slate-400 group-hover:text-white"
                    )}
                  />
                  <span className="truncate flex-1 leading-none">{item.label}</span>
                </Link>
              );
            })}
          </div>
        )}

        {/* Add to Live Meeting Action */}
        {!collapsed && (
          <div className="pt-2">
            <button
              type="button"
              onClick={() => alert("Knowra AI joining live meeting…")}
              className="w-full flex items-center justify-center gap-2 h-9 text-xs font-medium text-white border border-white/15 hover:border-white/30 hover:bg-white/[0.07] rounded-md transition-all cursor-pointer shadow-2xs"
            >
              <PlusCircle size={15} className="text-[#a594fd] shrink-0" />
              <span>Add to live meeting</span>
            </button>
          </div>
        )}
      </nav>

      {/* ── BOTTOM: PINNED USER PROFILE ────────────────────────────────────── */}
      <div className="shrink-0 p-3 border-t border-white/[0.08]">
        <div className="relative">
          <div
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            className={cn(
              "hover:bg-white/[0.07] px-2.5 py-2 transition-all cursor-pointer flex items-center justify-between h-11 rounded-md",
              collapsed ? "justify-center" : "gap-2.5"
            )}
          >
            {/* Left: Avatar & Info */}
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-7 h-7 rounded-full bg-[#4c47cc] text-white flex items-center justify-center text-[11px] font-bold shadow-xs shrink-0">
                {userName.charAt(0).toUpperCase()}
              </div>
              {!collapsed && (
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-semibold text-white truncate leading-tight">
                    {userName}
                  </p>
                  <p className="text-[11px] text-slate-400 truncate mt-0.5" title={userEmail}>
                    {userEmail}
                  </p>
                </div>
              )}
            </div>

            {/* Right: Chevron */}
            {!collapsed && (
              <ChevronRight size={14} className="text-slate-400 shrink-0" />
            )}
          </div>

          {/* User Signout Menu */}
          {userMenuOpen && (
            <div
              className="absolute bottom-full mb-2 left-0 right-0 bg-[#211f4a] border border-white/10 shadow-2xl p-1.5 z-50 animate-fade-in space-y-1 rounded-lg"
            >
              <div className="px-3 py-1.5 border-b border-white/10 text-xs text-slate-400">
                Signed in as <strong className="text-white block truncate">{userEmail}</strong>
              </div>
              <button
                type="button"
                onClick={() => logout()}
                className="w-full flex items-center gap-2 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/10 transition-colors cursor-pointer rounded-md"
              >
                <LogOut size={13} />
                <span>Sign out</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </aside>

    <CreateFolderModal
      isOpen={createFolderOpen}
      onClose={() => setCreateFolderOpen(false)}
      onCreated={(newF) => addFolder(newF)}
    />
    </>
  );
}
