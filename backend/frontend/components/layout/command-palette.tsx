"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { MEETINGS, ACTIONS, DECISIONS } from "@/lib/api/endpoints";
import {
  Search,
  X,
  LayoutDashboard,
  Sparkles,
  Video,
  CheckSquare,
  ListTodo,
  ShieldCheck,
  GitBranch,
  BarChart3,
  Layers,
  Settings,
  ArrowRight,
  Clock,
  ChevronRight,
  Command,
} from "lucide-react";

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenUpload?: () => void;
}

interface NavItem {
  title: string;
  category: string;
  href: string;
  icon: React.ComponentType<{ className?: string; size?: number }>;
  shortcut?: string;
  description: string;
}

const STATIC_NAV_ITEMS: NavItem[] = [
  {
    title: "Executive Dashboard",
    category: "Navigation",
    href: "/",
    icon: LayoutDashboard,
    shortcut: "G D",
    description: "System overview, cross-meeting KPIs & recent activity",
  },
  {
    title: "Ask Knowra (AI Copilot)",
    category: "Navigation",
    href: "/chat",
    icon: Sparkles,
    shortcut: "G C",
    description: "Multi-meeting generative Q&A with citations",
  },
  {
    title: "Meetings Intelligence",
    category: "Navigation",
    href: "/meetings",
    icon: Video,
    shortcut: "G M",
    description: "Video recordings, transcripts, and intelligence recaps",
  },
  {
    title: "Decisions Registry",
    category: "Navigation",
    href: "/decisions",
    icon: CheckSquare,
    shortcut: "G E",
    description: "Consensus tracking, architectural & executive resolutions",
  },
  {
    title: "Action Items Tracker",
    category: "Navigation",
    href: "/actions",
    icon: ListTodo,
    shortcut: "G A",
    description: "Deliverables, owners, deadlines, and completion status",
  },
  {
    title: "AI Quality & Governance",
    category: "Navigation",
    href: "/evaluation",
    icon: ShieldCheck,
    shortcut: "G Q",
    description: "Faithfulness metrics, hallucination tests & token telemetry",
  },
  {
    title: "Knowledge Graph",
    category: "Navigation",
    href: "/graph",
    icon: GitBranch,
    shortcut: "G K",
    description: "Interactive entity, person, topic & decision network",
  },
  {
    title: "Timeline & Analytics",
    category: "Navigation",
    href: "/timeline",
    icon: BarChart3,
    shortcut: "G T",
    description: "Chronological event audit trail and meeting trends",
  },
  {
    title: "Enterprise Integrations",
    category: "Navigation",
    href: "/integrations",
    icon: Layers,
    shortcut: "G I",
    description: "Slack, Microsoft Teams, Jira & Webhook connectors",
  },
  {
    title: "Workspace Settings & RBAC",
    category: "Navigation",
    href: "/settings",
    icon: Settings,
    shortcut: "G S",
    description: "Organization policies, security, and access control",
  },
];

export function CommandPalette({ isOpen, onClose, onOpenUpload }: CommandPaletteProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto focus input when opened
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  // Fetch quick live results if query has length
  const { data: meetingsData } = useQuery({
    queryKey: ["command-palette-meetings"],
    queryFn: () => api.get<{ items: Array<{ id: string; title: string; scheduled_start?: string }> }>("/meetings?page=1&page_size=20"),
    enabled: isOpen,
    staleTime: 60_000,
  });

  const { data: actionsData } = useQuery({
    queryKey: ["command-palette-actions"],
    queryFn: () => api.get<{ items: Array<{ id: string; title: string; priority: string; assignee?: string }> }>(ACTIONS.list()),
    enabled: isOpen,
    staleTime: 60_000,
  });

  const { data: decisionsData } = useQuery({
    queryKey: ["command-palette-decisions"],
    queryFn: () => api.get<{ items: Array<{ id: string; title: string; category?: string }> }>(DECISIONS.list()),
    enabled: isOpen,
    staleTime: 60_000,
  });

  // Filter items
  const filteredItems = useMemo(() => {
    const q = query.trim().toLowerCase();
    const results: Array<{
      id: string;
      title: string;
      subtitle: string;
      category: string;
      icon: React.ComponentType<{ className?: string; size?: number }>;
      action: () => void;
      badge?: string;
    }> = [];

    // Static Navigation
    STATIC_NAV_ITEMS.forEach((item) => {
      if (!q || item.title.toLowerCase().includes(q) || item.description.toLowerCase().includes(q)) {
        results.push({
          id: `nav-${item.href}`,
          title: item.title,
          subtitle: item.description,
          category: "Navigation",
          icon: item.icon,
          action: () => {
            router.push(item.href);
            onClose();
          },
          badge: item.shortcut,
        });
      }
    });

    // Dynamic Meetings
    if (meetingsData?.items) {
      meetingsData.items.forEach((m) => {
        if (q && m.title.toLowerCase().includes(q)) {
          results.push({
            id: `meeting-${m.id}`,
            title: m.title,
            subtitle: "Meeting Recording & Transcript",
            category: "Meetings",
            icon: Video,
            action: () => {
              router.push(`/meetings/${m.id}`);
              onClose();
            },
          });
        }
      });
    }

    // Dynamic Decisions
    if (decisionsData?.items) {
      decisionsData.items.forEach((d) => {
        if (q && d.title.toLowerCase().includes(q)) {
          results.push({
            id: `decision-${d.id}`,
            title: d.title,
            subtitle: `Decision • ${d.category || "General"}`,
            category: "Decisions",
            icon: CheckSquare,
            action: () => {
              router.push("/decisions");
              onClose();
            },
          });
        }
      });
    }

    // Dynamic Actions
    if (actionsData?.items) {
      actionsData.items.forEach((a) => {
        if (q && (a.title.toLowerCase().includes(q) || (a.assignee && a.assignee.toLowerCase().includes(q)))) {
          results.push({
            id: `action-${a.id}`,
            title: a.title,
            subtitle: `Action Item • ${a.assignee || "Unassigned"} (${a.priority})`,
            category: "Action Items",
            icon: ListTodo,
            action: () => {
              router.push("/actions");
              onClose();
            },
            badge: a.priority,
          });
        }
      });
    }

    return results;
  }, [query, router, onClose, meetingsData, decisionsData, actionsData]);

  // Handle keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filteredItems.length));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % Math.max(1, filteredItems.length));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (filteredItems[selectedIndex]) {
        filteredItems[selectedIndex].action();
      }
    } else if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 px-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
      <div
        className="fixed inset-0"
        onClick={onClose}
        aria-hidden="true"
      />
      <div
        className="relative w-full max-w-2xl bg-white rounded-2xl shadow-2xl border border-slate-200/90 overflow-hidden flex flex-col max-h-[75vh] z-10 animate-in fade-in zoom-in-95 duration-150"
        onKeyDown={handleKeyDown}
      >
        {/* Search Input Bar */}
        <div className="flex items-center px-4.5 py-3.5 border-b border-slate-100 bg-slate-50/50">
          <Search size={18} className="text-slate-400 shrink-0 mr-3" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedIndex(0);
            }}
            placeholder="Type a command or search meetings, decisions, actions..."
            className="w-full bg-transparent text-sm text-slate-800 placeholder:text-slate-400 focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery("")}
              className="text-slate-400 hover:text-slate-600 p-1"
            >
              <X size={15} />
            </button>
          )}
          <div className="ml-2 flex items-center gap-1 shrink-0">
            <kbd className="px-1.5 py-0.5 text-[10px] font-mono bg-white border border-slate-200 rounded text-slate-500 shadow-2xs">
              ESC
            </kbd>
          </div>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-2 divide-y divide-slate-50">
          {filteredItems.length === 0 ? (
            <div className="py-12 text-center">
              <Command size={32} className="mx-auto text-slate-300 mb-2" />
              <p className="text-sm font-medium text-slate-700">No results found</p>
              <p className="text-xs text-slate-400 mt-1">
                Try searching for page titles, meeting topics, or action items.
              </p>
            </div>
          ) : (
            filteredItems.map((item, idx) => {
              const Icon = item.icon;
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={item.id}
                  onClick={() => item.action()}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  className={`flex items-center justify-between px-3.5 py-2.5 rounded-xl cursor-pointer transition-colors ${
                    isSelected ? "bg-indigo-50/80 text-indigo-900" : "hover:bg-slate-50 text-slate-700"
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors ${
                        isSelected
                          ? "bg-indigo-600 text-white shadow-xs"
                          : "bg-slate-100 text-slate-500"
                      }`}
                    >
                      <Icon size={16} />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold truncate text-slate-900">
                          {item.title}
                        </span>
                        <span className="text-[10px] font-medium px-1.5 py-0.2 rounded bg-slate-100 text-slate-500">
                          {item.category}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400 truncate mt-0.5">
                        {item.subtitle}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-3">
                    {item.badge && (
                      <span className="px-1.5 py-0.5 text-[10px] font-mono rounded bg-slate-100 text-slate-500 border border-slate-200">
                        {item.badge}
                      </span>
                    )}
                    <ChevronRight
                      size={14}
                      className={isSelected ? "text-indigo-600" : "text-slate-300"}
                    />
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer info bar */}
        <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/70 flex items-center justify-between text-[11px] text-slate-400">
          <div className="flex items-center gap-3">
            <span>
              <kbd className="font-mono bg-white px-1 py-0.5 border border-slate-200 rounded text-slate-500 shadow-2xs mr-1">
                ↑
              </kbd>
              <kbd className="font-mono bg-white px-1 py-0.5 border border-slate-200 rounded text-slate-500 shadow-2xs mr-1">
                ↓
              </kbd>
              Navigate
            </span>
            <span>
              <kbd className="font-mono bg-white px-1 py-0.5 border border-slate-200 rounded text-slate-500 shadow-2xs mr-1">
                ↵
              </kbd>
              Open
            </span>
          </div>
          <span className="font-medium text-slate-500">Knowra Enterprise Search</span>
        </div>
      </div>
    </div>
  );
}
