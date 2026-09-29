"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import {
  Bell,
  Check,
  CheckCheck,
  Video,
  ListTodo,
  CheckSquare,
  ShieldCheck,
  Sparkles,
  ExternalLink,
  Clock,
  X,
} from "lucide-react";

export interface NotificationItem {
  id: string;
  title: string;
  description: string;
  timestamp: string;
  isRead: boolean;
  type: "meeting" | "action" | "decision" | "system";
  link: string;
}

const INITIAL_NOTIFICATIONS: NotificationItem[] = [
  {
    id: "notif-1",
    title: "AI Indexing & Transcription Complete",
    description: "Enterprise Q3 Strategy & OKRs meeting audio fully transcribed with 98.4% accuracy.",
    timestamp: "10m ago",
    isRead: false,
    type: "meeting",
    link: "/meetings",
  },
  {
    id: "notif-2",
    title: "High-Priority Action Item Assigned",
    description: "You have been tagged on 'Finalize PostgreSQL connection pool parameters for multi-region'.",
    timestamp: "45m ago",
    isRead: false,
    type: "action",
    link: "/actions",
  },
  {
    id: "notif-3",
    title: "Architectural Decision Approved",
    description: "Sprint Review consensus reached: 'Deploy FastEmbed ONNX runtime for local embeddings'.",
    timestamp: "2h ago",
    isRead: false,
    type: "decision",
    link: "/decisions",
  },
  {
    id: "notif-4",
    title: "Enterprise Safety & RBAC Audit Passed",
    description: "All tenant isolation filters and SQL predicates verified without security anomalies.",
    timestamp: "Yesterday",
    isRead: true,
    type: "system",
    link: "/evaluation",
  },
];

export function NotificationPopover() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState<NotificationItem[]>(INITIAL_NOTIFICATIONS);
  const [activeFilter, setActiveFilter] = useState<"all" | "unread">("all");
  const popoverRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter((n) => !n.isRead).length;

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  const markAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
  };

  const markAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, isRead: true } : n))
    );
  };

  const filtered = notifications.filter((n) =>
    activeFilter === "unread" ? !n.isRead : true
  );

  const getIcon = (type: NotificationItem["type"]) => {
    switch (type) {
      case "meeting":
        return <Video size={14} className="text-blue-600" />;
      case "action":
        return <ListTodo size={14} className="text-amber-600" />;
      case "decision":
        return <CheckSquare size={14} className="text-emerald-600" />;
      default:
        return <ShieldCheck size={14} className="text-indigo-600" />;
    }
  };

  return (
    <div className="relative" ref={popoverRef}>
      {/* Bell Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`relative p-2 rounded-lg transition-colors cursor-pointer ${
          isOpen
            ? "bg-slate-100 text-slate-900"
            : "text-slate-500 hover:bg-slate-100 hover:text-slate-900"
        }`}
        aria-label="Enterprise Notifications"
        id="topbar-notifications-btn"
      >
        <Bell size={17} />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-600"></span>
          </span>
        )}
      </button>

      {/* Popover Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white rounded-2xl shadow-xl border border-slate-200/90 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-100">
          {/* Header */}
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
            <div className="flex items-center gap-2">
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Notifications
              </span>
              {unreadCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] font-semibold bg-indigo-50 text-indigo-600 border border-indigo-200/60">
                  {unreadCount} new
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="text-[11px] font-medium text-indigo-600 hover:text-indigo-800 transition-colors flex items-center gap-1 cursor-pointer"
                >
                  <CheckCheck size={12} />
                  <span>Mark all read</span>
                </button>
              )}
            </div>
          </div>

          {/* Filter Bar */}
          <div className="px-4 py-1.5 border-b border-slate-100 flex items-center gap-2 text-xs bg-white">
            <button
              onClick={() => setActiveFilter("all")}
              className={`px-2 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer ${
                activeFilter === "all"
                  ? "bg-slate-100 text-slate-900 font-semibold"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              All ({notifications.length})
            </button>
            <button
              onClick={() => setActiveFilter("unread")}
              className={`px-2 py-1 rounded-md text-[11px] font-medium transition-colors cursor-pointer ${
                activeFilter === "unread"
                  ? "bg-indigo-50 text-indigo-700 font-semibold"
                  : "text-slate-500 hover:text-slate-900"
              }`}
            >
              Unread ({unreadCount})
            </button>
          </div>

          {/* List */}
          <div className="max-h-80 overflow-y-auto divide-y divide-slate-50">
            {filtered.length === 0 ? (
              <div className="py-8 text-center px-4">
                <Check className="mx-auto text-emerald-500 mb-1" size={20} />
                <p className="text-xs font-medium text-slate-700">All caught up</p>
                <p className="text-[11px] text-slate-400 mt-0.5">
                  No unread enterprise notifications right now.
                </p>
              </div>
            ) : (
              filtered.map((item) => (
                <div
                  key={item.id}
                  onClick={() => markAsRead(item.id)}
                  className={`p-3.5 flex items-start gap-3 hover:bg-slate-50/80 transition-colors cursor-pointer ${
                    !item.isRead ? "bg-indigo-50/20" : ""
                  }`}
                >
                  <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 mt-0.5">
                    {getIcon(item.type)}
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between gap-1">
                      <p className={`text-xs font-semibold truncate ${!item.isRead ? "text-slate-900 font-bold" : "text-slate-700"}`}>
                        {item.title}
                      </p>
                      <span className="text-[10px] text-slate-400 shrink-0">
                        {item.timestamp}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-500 line-clamp-2 mt-0.5 leading-relaxed">
                      {item.description}
                    </p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <Link
                        href={item.link}
                        onClick={() => setIsOpen(false)}
                        className="text-[10px] font-medium text-indigo-600 hover:text-indigo-800 flex items-center gap-1"
                      >
                        <span>View details</span>
                        <ExternalLink size={10} />
                      </Link>
                    </div>
                  </div>

                  {!item.isRead && (
                    <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 shrink-0 mt-2" />
                  )}
                </div>
              ))
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-slate-100 bg-slate-50/70 text-center">
            <Link
              href="/settings"
              onClick={() => setIsOpen(false)}
              className="text-[11px] text-slate-500 hover:text-slate-900 font-medium"
            >
              Notification preferences
            </Link>
          </div>
        </div>
      )}
    </div>
  );
}
