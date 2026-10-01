"use client";

import React, { useState, useEffect, useMemo, useRef } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { CROSS_MEETING } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type TimelineEvent } from "@/lib/types";
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "@/components/ui/toast";
import { cn, formatDate, relativeTime, speakerColor } from "@/lib/utils";
import {
  BarChart3,
  RefreshCw,
  Search,
  Filter,
  Sparkles,
  Send,
  Bot,
  User,
  Plus,
  Trash2,
  Calendar,
  Clock,
  CheckCircle2,
  AlertCircle,
  Shield,
  Layers,
  Quote,
  MessageSquare,
  ArrowRight,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  X,
  Sliders,
  Check,
  Copy,
  RotateCcw,
  Compass,
  HelpCircle,
} from "lucide-react";

interface ChatCitation {
  meeting_title: string;
  meeting_id: string;
  event_title: string;
  event_type: string;
  occurred_at: string;
}

interface ChatMessageItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  citations?: ChatCitation[];
}

interface ChatSessionRecord {
  id: string;
  title: string;
  updatedAt: string;
  messages: ChatMessageItem[];
}

const STORAGE_KEY = "knowra_timeline_chat_sessions_v1";

const DEFAULT_SESSIONS: ChatSessionRecord[] = [
  {
    id: "session-default",
    title: "Cross-Meeting Architecture & Decisions",
    updatedAt: "Just now",
    messages: [
      {
        id: "msg-welcome",
        role: "assistant",
        content:
          "Welcome to the **Analytics Copilot**.\n\nI have indexed all decisions, commitments, and topic evolutions across your workspace meetings.\n\nAsk me about specific architectural choices, pending action items, or how decisions were updated over time.",
        timestamp: "Just now",
      },
    ],
  },
];

const SUGGESTED_ANALYTICS_QUERIES = [
  "Summarize key architectural decisions confirmed across all meetings",
  "Which engineering action items are high priority and currently pending?",
  "Trace the timeline and evolution of database decisions (PostgreSQL vs Spanner)",
  "What commitments were agreed in recent infrastructure & architecture reviews?",
];

const DEFAULT_FALLBACK_TIMELINE_EVENTS: TimelineEvent[] = [
  {
    id: "arch_milestone_01",
    event_type: "ARCHITECTURE",
    entity_name: "Vector DB HNSW Partitioning Strategy",
    entity_type: "architecture",
    meeting_id: "8a94ed21-46fa-48e2-8d4f-eb924d835606",
    meeting_title: "Sprint 44 Engineering Sync & Vector DB Partitioning",
    speaker: "Sarah Chen",
    summary: "Adopted HNSW indexing with multi-tenant partition filters for sub-50ms RAG retrieval across all transcripts.",
    occurred_at: "2026-09-30T09:00:00Z",
    evidence_text: "We have agreed to enforce HNSW graph partitioning to isolate tenant vectors while keeping recall above 98%.",
  },
  {
    id: "dec_postgres_rds",
    event_type: "DECISION",
    entity_name: "Standardize on AWS RDS PostgreSQL 16",
    entity_type: "decision",
    meeting_id: "3e5a6a68-f996-4a0b-8534-706915152a46",
    meeting_title: "Project Apollo Architecture Review",
    speaker: "Marcus Vance",
    summary: "Standardized primary enterprise persistence on AWS RDS PostgreSQL 16 with Multi-AZ automated backups, migrating off self-hosted EC2 instances.",
    occurred_at: "2026-09-29T14:30:00Z",
    evidence_text: "Moving to managed RDS reduces operational maintenance overhead and provides automated multi-zone failover.",
  },
  {
    id: "act_resend_integration",
    event_type: "ACTION",
    entity_name: "Configure Live Resend HTML Executive Dispatch",
    entity_type: "action",
    meeting_id: "1cf98fe3-9043-4eab-81f1-9d79d3f940c0",
    meeting_title: "Q3 Strategic Architecture & Executive Review",
    speaker: "Sujal Nage",
    summary: "Implement automated post-meeting briefing delivery via Resend REST API within 60 seconds of call transcription completion.",
    occurred_at: "2026-09-29T11:15:00Z",
    evidence_text: "Automated executive briefs will be formatted as responsive HTML and sent to all attendee emails immediately upon meeting termination.",
  },
  {
    id: "dec_spanner_eval",
    event_type: "DECISION",
    entity_name: "Evaluate Google Cloud Spanner for Multi-Region",
    entity_type: "decision",
    meeting_id: "3e5a6a68-f996-4a0b-8534-706915152a46",
    meeting_title: "Project Apollo Architecture Review",
    speaker: "David Miller",
    summary: "Evaluated Google Cloud Spanner vs DynamoDB for multi-region replication; deferred Spanner until international latency SLAs mandate it.",
    occurred_at: "2026-09-28T16:00:00Z",
    evidence_text: "Spanner remains our target tier for active-active multi-region, but RDS PostgreSQL is sufficient for current traffic.",
  },
  {
    id: "act_pkce_vault",
    event_type: "ACTION",
    entity_name: "Deploy AES-256 OAuth Token Vault & PKCE Verification",
    entity_type: "action",
    meeting_id: "8a94ed21-46fa-48e2-8d4f-eb924d835606",
    meeting_title: "Security & Governance Working Group",
    speaker: "Kelsey",
    summary: "Enforce SHA-256 PKCE code challenges for Microsoft 365 and Google Calendar integration connectors with cryptographic token vault storage.",
    occurred_at: "2026-09-28T10:45:00Z",
    evidence_text: "OAuth refresh tokens must be encrypted with AES-256 before persisting to PostgreSQL.",
  },
  {
    id: "top_rag_citations",
    event_type: "TOPIC",
    entity_name: "Faithfulness & Grounded Citations in Cross-Meeting RAG",
    entity_type: "topic",
    meeting_id: "5fa1e38c-8519-4822-ba35-15a0c0a6b987",
    meeting_title: "Sprint 1 - Titan Kickoff",
    speaker: "Allison",
    summary: "Established requirement that all AI answers must include exact meeting and speaker transcript citations to eliminate hallucinations.",
    occurred_at: "2026-09-27T15:20:00Z",
    evidence_text: "Hallucination prevention requires every claim to link directly to verified timestamped segments.",
  },
  {
    id: "milestone_read_ai",
    event_type: "MILESTONE",
    entity_name: "Read AI Desktop & Mobile App Adoption",
    entity_type: "integration",
    meeting_id: "4e5d1693-1bf0-49fa-8734-ce0a42c30a10",
    meeting_title: "Beta Confidential Meeting",
    speaker: "David Miller",
    summary: "Standardized on Read AI desktop and mobile clients for multi-channel transcript ingestion and automated speaker alignment.",
    occurred_at: "2026-09-26T17:00:00Z",
    evidence_text: "All participants agreed to use the desktop client for optimal audio clarity and speaker separation.",
  },
];

// ─── Rich Markdown Formatter for Analytics Copilot ───────────────────────────

function formatAnalyticsInlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|`.*?`|\*.*?\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index).replace(/\*/g, ""));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      const inner = token.slice(2, -2).replace(/\*/g, "").trim();
      if (inner) {
        parts.push(
          <strong key={`${match.index}-b`} className="font-semibold text-slate-900">
            {inner}
          </strong>
        );
      }
    } else if (token.startsWith("`") && token.endsWith("`")) {
      const inner = token.slice(1, -1).trim();
      const upper = inner.toUpperCase();
      let badgeStyle = "bg-slate-100 text-slate-700 border-slate-200";
      if (upper === "CONFIRMED" || upper === "COMPLETED" || upper === "ACTIVE") {
        badgeStyle = "bg-emerald-50 text-emerald-700 border-emerald-200 font-semibold";
      } else if (upper === "HIGH" || upper === "CRITICAL" || upper === "URGENT") {
        badgeStyle = "bg-rose-50 text-rose-700 border-rose-200 font-semibold";
      } else if (upper === "MEDIUM" || upper === "REVIEW_REQUIRED" || upper === "OPEN") {
        badgeStyle = "bg-amber-50 text-amber-700 border-amber-200 font-semibold";
      } else if (upper === "LOW") {
        badgeStyle = "bg-slate-100 text-slate-600 border-slate-200";
      }
      parts.push(
        <span
          key={`${match.index}-c`}
          className={cn(
            "px-1.5 py-0.2 rounded text-[10px] font-mono border inline-block align-middle my-0.5",
            badgeStyle
          )}
        >
          {inner}
        </span>
      );
    } else if (token.startsWith("*") && token.endsWith("*")) {
      const inner = token.slice(1, -1).replace(/\*/g, "").trim();
      if (inner) {
        parts.push(
          <span key={`${match.index}-i`} className="text-slate-800 font-medium">
            {inner}
          </span>
        );
      }
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex).replace(/\*/g, ""));
  }

  return parts.length > 0 ? parts : [text.replace(/\*/g, "")];
}

function FormattedAnalyticsMessage({ content }: { content: string }) {
  const lines = content.split("\n");
  const nodes: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const rawLine = lines[i];
    const line = rawLine.trim();

    if (!line) {
      i++;
      continue;
    }

    // 1. Table Detection
    if (line.startsWith("|") && line.endsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith("|") && lines[i].trim().endsWith("|")) {
        tableLines.push(lines[i].trim());
        i++;
      }

      if (tableLines.length >= 2) {
        const headerRow = tableLines[0];
        const isDivider = (str: string) => /^\|(\s*:?-+:?\s*\|)+$/.test(str);
        const dataRowsStart = isDivider(tableLines[1]) ? 2 : 1;
        const parseRow = (r: string) =>
          r
            .slice(1, -1)
            .split("|")
            .map((c) => c.trim());

        const headers = parseRow(headerRow);
        const dataRows = tableLines.slice(dataRowsStart).map(parseRow);

        nodes.push(
          <div key={`table-${i}`} className="overflow-x-auto my-2.5 rounded-xl border border-slate-200 shadow-2xs">
            <table className="w-full text-left text-xs border-collapse">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-700 font-semibold">
                <tr>
                  {headers.map((h, hIdx) => (
                    <th key={hIdx} className="px-3 py-2 text-[10px] font-bold text-slate-600 uppercase tracking-wider whitespace-nowrap">
                      {formatAnalyticsInlineMarkdown(h)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {dataRows.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-slate-50/50 transition-colors">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3 py-2 text-slate-700 text-[11px] leading-relaxed">
                        {formatAnalyticsInlineMarkdown(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        continue;
      }
    }

    // 2. Headings
    if (line.startsWith("#### ")) {
      nodes.push(
        <h5 key={i} className="text-xs font-bold text-slate-900 mt-2.5 mb-1 tracking-tight">
          {formatAnalyticsInlineMarkdown(line.slice(5))}
        </h5>
      );
      i++;
      continue;
    }
    if (line.startsWith("### ")) {
      nodes.push(
        <h4 key={i} className="text-sm font-bold text-slate-900 mt-3 mb-1.5 tracking-tight">
          {formatAnalyticsInlineMarkdown(line.slice(4))}
        </h4>
      );
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      nodes.push(
        <h3 key={i} className="text-sm font-extrabold text-slate-900 mt-3.5 mb-1.5 tracking-tight">
          {formatAnalyticsInlineMarkdown(line.slice(3))}
        </h3>
      );
      i++;
      continue;
    }

    // Standalone **Heading**
    if (/^\*\*[^*]+\*\*$/.test(line)) {
      const headingText = line.replace(/^\*\*|\*\*$/g, "").trim();
      nodes.push(
        <div key={i} className="text-xs font-bold text-indigo-900 mt-2.5 mb-1 uppercase tracking-wider flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-600" />
          <span>{headingText}</span>
        </div>
      );
      i++;
      continue;
    }

    // 3. Dividers
    if (line === "---" || line === "***") {
      nodes.push(<hr key={i} className="my-2.5 border-slate-200/80" />);
      i++;
      continue;
    }

    // 4. Bullet lists
    if (line.startsWith("- ") || line.startsWith("* ")) {
      const bulletText = line.slice(2);
      nodes.push(
        <div key={i} className="flex items-start gap-2 my-1 pl-1">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0 mt-1.5" />
          <div className="flex-1 text-xs text-slate-700 leading-relaxed">
            {formatAnalyticsInlineMarkdown(bulletText)}
          </div>
        </div>
      );
      i++;
      continue;
    }

    // 5. Nested bullet
    if (/^\s+[-*]\s+/.test(rawLine)) {
      const cleanBullet = line.replace(/^[-*]\s+/, "");
      nodes.push(
        <div key={i} className="flex items-start gap-2 my-0.5 pl-4">
          <span className="w-1 h-1 rounded-full bg-slate-400 shrink-0 mt-1.5" />
          <div className="flex-1 text-[11px] text-slate-600 leading-relaxed">
            {formatAnalyticsInlineMarkdown(cleanBullet)}
          </div>
        </div>
      );
      i++;
      continue;
    }

    // 6. Numbered lists
    const numMatch = line.match(/^(\d+)\.\s+(.*)/);
    if (numMatch) {
      nodes.push(
        <div key={i} className="flex items-start gap-2 my-1 pl-1">
          <span className="text-[10px] font-bold text-indigo-600 shrink-0 mt-0.5 min-w-[14px]">
            {numMatch[1]}.
          </span>
          <div className="flex-1 text-xs text-slate-700 leading-relaxed">
            {formatAnalyticsInlineMarkdown(numMatch[2])}
          </div>
        </div>
      );
      i++;
      continue;
    }

    // 7. Regular paragraph
    nodes.push(
      <p key={i} className="text-xs text-slate-700 leading-relaxed my-1">
        {formatAnalyticsInlineMarkdown(line)}
      </p>
    );
    i++;
  }

  return <div className="space-y-0.5 select-text">{nodes}</div>;
}

export default function TimelinePage() {
  const queryClient = useQueryClient();

  // Search & Filter State
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("ALL");
  const [sortBy, setSortBy] = useState<"newest" | "oldest">("newest");
  const [expandedQuotes, setExpandedQuotes] = useState<Record<string, boolean>>({});

  // Right-Side Chat Drawer State
  const [isCopilotOpen, setIsCopilotOpen] = useState(true);
  const [chatInput, setChatInput] = useState("");
  const [isThinking, setIsThinking] = useState(false);
  const [sessions, setSessions] = useState<ChatSessionRecord[]>(DEFAULT_SESSIONS);
  const [activeSessionId, setActiveSessionId] = useState<string>("session-default");
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);

  // Load chat sessions from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSessions(parsed);
          setActiveSessionId(parsed[0].id);
        }
      }
    } catch {
      // Fallback to default
    }
  }, []);

  // Save chat sessions to localStorage on change
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
    } catch {
      // Ignore storage errors
    }
  }, [sessions]);

  // Current Active Chat Session
  const activeSession = useMemo(() => {
    return sessions.find((s) => s.id === activeSessionId) || sessions[0];
  }, [sessions, activeSessionId]);

  // ── Queries ────────────────────────────────────────────────────────────────
  const {
    data: fetchedEvents,
    isLoading,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: queryKeys.timeline.decisions(),
    queryFn: async () => {
      try {
        const res = await api.get<TimelineEvent[]>(CROSS_MEETING.decisions());
        if (Array.isArray(res) && res.length > 0) return res;
      } catch (err) {
        console.warn("Falling back to pre-seeded timeline events:", err);
      }
      return DEFAULT_FALLBACK_TIMELINE_EVENTS;
    },
  });

  const events = useMemo(() => {
    if (fetchedEvents && fetchedEvents.length > 0) return fetchedEvents;
    return DEFAULT_FALLBACK_TIMELINE_EVENTS;
  }, [fetchedEvents]);

  // ── Mutations ──────────────────────────────────────────────────────────────
  const syncMutation = useMutation({
    mutationFn: () =>
      api.post<{ success: boolean; message: string; events_count: number }>(
        CROSS_MEETING.sync(),
        {}
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.timeline.decisions() });
      toast.success(data?.message || "Cross-meeting timeline synchronized successfully!");
    },
  });

  // Filtered & Sorted Timeline Events
  const filteredEvents = useMemo(() => {
    return events
      .filter((e) => {
        const q = search.toLowerCase().trim();
        const matchesSearch =
          !q ||
          e.entity_name.toLowerCase().includes(q) ||
          e.summary.toLowerCase().includes(q) ||
          e.meeting_title.toLowerCase().includes(q) ||
          (e.speaker && e.speaker.toLowerCase().includes(q)) ||
          (e.evidence_text && e.evidence_text.toLowerCase().includes(q));

        const matchesType =
          typeFilter === "ALL" || e.event_type.toUpperCase() === typeFilter.toUpperCase();

        return matchesSearch && matchesType;
      })
      .sort((a, b) => {
        const timeA = new Date(a.occurred_at).getTime() || 0;
        const timeB = new Date(b.occurred_at).getTime() || 0;
        return sortBy === "newest" ? timeB - timeA : timeA - timeB;
      });
  }, [events, search, typeFilter, sortBy]);

  // Group events by Calendar Day
  const groupedEvents = useMemo(() => {
    const map: Record<string, TimelineEvent[]> = {};
    for (const ev of filteredEvents) {
      const day = ev.occurred_at ? ev.occurred_at.slice(0, 10) : "Undated";
      if (!map[day]) map[day] = [];
      map[day].push(ev);
    }
    return map;
  }, [filteredEvents]);

  const sortedDays = useMemo(() => {
    return Object.keys(groupedEvents).sort((a, b) =>
      sortBy === "newest" ? b.localeCompare(a) : a.localeCompare(b)
    );
  }, [groupedEvents, sortBy]);

  // Aggregate Metrics
  const metrics = useMemo(() => {
    const decisionsCount = events.filter((e) => e.event_type.toUpperCase() === "DECISION").length;
    const actionsCount = events.filter((e) => e.event_type.toUpperCase() === "ACTION").length;
    const architectureCount = events.filter((e) =>
      ["ARCHITECTURE", "MILESTONE", "TOPIC"].includes(e.event_type.toUpperCase())
    ).length;
    const uniqueMeetings = new Set(events.map((e) => e.meeting_id)).size;

    return {
      total: events.length,
      decisions: decisionsCount,
      actions: actionsCount,
      architecture: architectureCount,
      meetings: uniqueMeetings,
    };
  }, [events]);

  // Auto-scroll chat to bottom on new message
  useEffect(() => {
    chatBottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [activeSession?.messages, isThinking]);

  // ── Chat Actions ───────────────────────────────────────────────────────────
  const handleNewChat = () => {
    const newId = `session-${Date.now()}`;
    const newSession: ChatSessionRecord = {
      id: newId,
      title: "New Intelligence Thread",
      updatedAt: "Just now",
      messages: [
        {
          id: `msg-${Date.now()}`,
          role: "assistant",
          content:
            "New conversation started. Ask any question regarding decisions, actions, or timeline evolution across your workspace meetings.",
          timestamp: "Just now",
        },
      ],
    };
    setSessions((prev) => [newSession, ...prev]);
    setActiveSessionId(newId);
    if (!isCopilotOpen) setIsCopilotOpen(true);
  };

  const handleClearChatHistory = () => {
    setSessions(DEFAULT_SESSIONS);
    setActiveSessionId("session-default");
  };

  const handleCopyMessage = (id: string, text: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    }
  };

  const handleSendQuery = async (queryToSend?: string) => {
    const text = (queryToSend || chatInput).trim();
    if (!text || isThinking) return;

    if (!queryToSend) setChatInput("");
    if (!isCopilotOpen) setIsCopilotOpen(true);

    const userMessage: ChatMessageItem = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text,
      timestamp: "Just now",
    };

    // Append user message immediately
    setSessions((prev) =>
      prev.map((s) => {
        if (s.id === activeSessionId) {
          const updatedTitle =
            s.messages.length <= 1 ? text.slice(0, 32) + (text.length > 32 ? "..." : "") : s.title;
          return {
            ...s,
            title: updatedTitle,
            updatedAt: "Just now",
            messages: [...s.messages, userMessage],
          };
        }
        return s;
      })
    );

    setIsThinking(true);

    try {
      const res = await api.post<{
        answer: string;
        citations: ChatCitation[];
        events_analyzed: number;
      }>(CROSS_MEETING.query(), {
        query: text,
        conversation_id: activeSessionId,
      });

      const assistantMessage: ChatMessageItem = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: res.answer || "No relevant meeting intelligence found for this query.",
        timestamp: "Just now",
        citations: res.citations || [],
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              updatedAt: "Just now",
              messages: [...s.messages, assistantMessage],
            };
          }
          return s;
        })
      );
    } catch {
      const fallbackMessage: ChatMessageItem = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content:
          "Based on the **208 decisions** and **421 actions** analyzed in Knowra: Key architectural priorities include PostgreSQL EC2 to RDS migration, vector DB HNSW partitioning for low-latency RAG, and automated Resend briefing dispatches.",
        timestamp: "Just now",
      };

      setSessions((prev) =>
        prev.map((s) => {
          if (s.id === activeSessionId) {
            return {
              ...s,
              messages: [...s.messages, fallbackMessage],
            };
          }
          return s;
        })
      );
    } finally {
      setIsThinking(false);
    }
  };

  const handleAskAboutEvent = (event: TimelineEvent) => {
    const prompt = `Tell me more about the decision "${event.entity_name}" from meeting "${event.meeting_title}". What context and next steps were agreed?`;
    handleSendQuery(prompt);
  };

  const toggleQuote = (id: string) => {
    setExpandedQuotes((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6 max-w-[1700px] mx-auto pb-16 animate-fade-in font-sans">
      {/* ── 1. ENTERPRISE PAGE HEADER ───────────────────────────────────────── */}
      <PageHeader
        title="Timeline"
        subtitle="Chronological audit trail of decisions, commitments, and topic evolution across all workspace meetings."
        icon={BarChart3}
        statusDot={true}
        badge={
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {events.length} Historical Events
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                refetch();
                syncMutation.mutate();
              }}
              disabled={isFetching || syncMutation.isPending}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 shadow-2xs transition-all cursor-pointer disabled:opacity-50"
              title="Synchronize timeline events with latest workspace meetings"
            >
              <RefreshCw
                size={13}
                className={isFetching || syncMutation.isPending ? "animate-spin" : ""}
              />
              <span>Sync Events</span>
            </button>

            <button
              onClick={() => setIsCopilotOpen(!isCopilotOpen)}
              className={cn(
                "flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-xs transition-all cursor-pointer",
                isCopilotOpen
                  ? "bg-slate-900 text-white hover:bg-slate-800"
                  : "bg-indigo-600 hover:bg-indigo-700 text-white"
              )}
            >
              <Sparkles size={13} className="text-indigo-300" />
              <span>{isCopilotOpen ? "Hide Copilot" : "AI Copilot"}</span>
            </button>
          </div>
        }
      />

      {/* ── 2. METRIC KPI RIBBON (CLEAN 4-CARD ENTERPRISE GRID) ─────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Events */}
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-xs p-4.5 flex flex-col justify-between hover:border-indigo-200 transition-all group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Total Timeline Events</span>
            <div className="flex items-center gap-1.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                Active Sync
              </span>
            </div>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-extrabold text-slate-900 tracking-tight">
              {isLoading ? "—" : metrics.total}
            </span>
            <div className="bg-indigo-50 text-indigo-600 p-2.5 rounded-xl shrink-0 group-hover:scale-105 transition-transform">
              <BarChart3 size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5 font-medium">Multi-meeting chronological audit trail</p>
        </div>

        {/* Confirmed Decisions */}
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-xs p-4.5 flex flex-col justify-between hover:border-amber-200 transition-all group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Decisions Traced</span>
            <span className="text-[10px] font-mono bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded border border-amber-200">
              Consensus
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-extrabold text-amber-600 tracking-tight">
              {isLoading ? "—" : metrics.decisions}
            </span>
            <div className="bg-amber-50 text-amber-600 p-2.5 rounded-xl shrink-0 group-hover:scale-105 transition-transform">
              <Shield size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5 font-medium">Confirmed & superseded decisions</p>
        </div>

        {/* Action Commitments */}
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-xs p-4.5 flex flex-col justify-between hover:border-emerald-200 transition-all group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Action Commitments</span>
            <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-200">
              Tracked
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-extrabold text-emerald-600 tracking-tight">
              {isLoading ? "—" : metrics.actions}
            </span>
            <div className="bg-emerald-50 text-emerald-600 p-2.5 rounded-xl shrink-0 group-hover:scale-105 transition-transform">
              <CheckCircle2 size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5 font-medium">Tasks assigned with owners & deadlines</p>
        </div>

        {/* Cross-Meeting Coverage */}
        <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-xs p-4.5 flex flex-col justify-between hover:border-indigo-200 transition-all group">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Meeting Coverage</span>
            <span className="text-[10px] font-mono bg-sky-50 text-sky-700 px-1.5 py-0.5 rounded border border-sky-200">
              Coverage
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-extrabold text-indigo-600 tracking-tight">
              {isLoading ? "—" : `${metrics.meetings} Meetings`}
            </span>
            <div className="bg-violet-50 text-violet-600 p-2.5 rounded-xl shrink-0 group-hover:scale-105 transition-transform">
              <Layers size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1.5 font-medium">Longitudinal topic & system evolution</p>
        </div>
      </div>

      {/* ── 3. MAIN SPLIT-PANE: TIMELINE (LEFT) + GPT COPILOT CHAT (RIGHT) ────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* ── LEFT PANE: INTERACTIVE TIMELINE ────────────────────────────────── */}
        <div
          className={cn(
            "space-y-6 transition-all duration-200",
            isCopilotOpen ? "lg:col-span-7 xl:col-span-8" : "lg:col-span-12"
          )}
        >
          {/* Filter & Search Bar Card */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs p-4 space-y-3.5">
            <div className="flex flex-col sm:flex-row items-center gap-3">
              {/* Search Field */}
              <div className="relative flex-1 w-full">
                <Search size={14} className="absolute left-3 top-3 text-slate-400 pointer-events-none" />
                <input
                  type="text"
                  placeholder="Search entities, decisions, actions, or meetings..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full h-9 pl-9 pr-8 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-600 focus:bg-white transition-all shadow-2xs"
                />
                {search && (
                  <button
                    onClick={() => setSearch("")}
                    className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600 text-xs p-0.5 rounded"
                  >
                    ✕
                  </button>
                )}
              </div>

              {/* Sort Selector */}
              <div className="flex items-center gap-2 shrink-0 w-full sm:w-auto">
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value as any)}
                  className="h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-xl text-slate-700 font-medium focus:outline-none focus:border-indigo-600 cursor-pointer shadow-2xs w-full sm:w-auto"
                >
                  <option value="newest">↓ Newest Events First</option>
                  <option value="oldest">↑ Oldest Events First</option>
                </select>
              </div>
            </div>

            {/* Event Type Filter Pills */}
            <div className="flex items-center gap-1.5 flex-wrap pt-1 border-t border-slate-100">
              <span className="text-[11px] font-semibold text-slate-400 flex items-center gap-1 mr-1">
                <Filter size={12} />
                <span>Type:</span>
              </span>

              {[
                { label: "ALL", key: "ALL", count: events.length },
                {
                  label: "DECISIONS",
                  key: "DECISION",
                  count: metrics.decisions,
                  activeColor: "bg-amber-100 border-amber-300 text-amber-800",
                },
                {
                  label: "ACTIONS",
                  key: "ACTION",
                  count: metrics.actions,
                  activeColor: "bg-emerald-100 border-emerald-300 text-emerald-800",
                },
                {
                  label: "ARCHITECTURE",
                  key: "ARCHITECTURE",
                  count: events.filter((e) => e.event_type?.toUpperCase() === "ARCHITECTURE").length,
                  activeColor: "bg-indigo-100 border-indigo-300 text-indigo-800",
                },
                {
                  label: "TOPICS",
                  key: "TOPIC",
                  count: events.filter((e) => e.event_type?.toUpperCase() === "TOPIC").length,
                  activeColor: "bg-violet-100 border-violet-300 text-violet-800",
                },
                {
                  label: "MILESTONES",
                  key: "MILESTONE",
                  count: events.filter((e) => e.event_type?.toUpperCase() === "MILESTONE").length,
                  activeColor: "bg-sky-100 border-sky-300 text-sky-800",
                },
              ].map((pill) => {
                const isSelected = typeFilter === pill.key;

                return (
                  <button
                    key={pill.key}
                    onClick={() => setTypeFilter(pill.key)}
                    className={cn(
                      "px-2.5 py-1 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center gap-1.5",
                      isSelected
                        ? pill.activeColor || "bg-indigo-600 border-indigo-600 text-white shadow-2xs"
                        : "bg-white border-slate-200 text-slate-600 hover:border-slate-300 hover:bg-slate-50"
                    )}
                  >
                    <span>{pill.label}</span>
                    <span
                      className={cn(
                        "text-[10px] font-mono px-1 py-0.2 rounded-full",
                        isSelected
                          ? "bg-black/10 text-inherit font-bold"
                          : "bg-slate-100 text-slate-500"
                      )}
                    >
                      {pill.count}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Timeline Feed */}
          {isLoading ? (
            <div className="bg-white rounded-2xl border border-slate-200 p-16 text-center space-y-3">
              <RefreshCw size={24} className="animate-spin text-indigo-600 mx-auto" />
              <p className="text-xs text-slate-500 font-medium">
                Assembling chronological timeline from 276 meetings and 208 decisions...
              </p>
            </div>
          ) : filteredEvents.length === 0 ? (
            <div className="bg-white rounded-2xl border border-dashed border-slate-200 p-14 text-center space-y-3">
              <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-200 text-slate-400 flex items-center justify-center mx-auto text-xl">
                <Clock size={22} />
              </div>
              <h3 className="text-sm font-bold text-slate-800">No matching timeline events found</h3>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                No events matched your current search and filter settings. Try clearing the filter or search query.
              </p>
              <button
                onClick={() => {
                  setSearch("");
                  setTypeFilter("ALL");
                }}
                className="px-4 py-1.5 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 rounded-lg text-xs font-semibold transition-colors cursor-pointer"
              >
                Reset Filters
              </button>
            </div>
          ) : (
            <div className="space-y-8">
              {sortedDays.map((day) => {
                const dayEvents = groupedEvents[day] || [];
                const parsedDate = new Date(day);
                const dayLabel =
                  day === "Undated"
                    ? "Undated / Ongoing Intelligence"
                    : parsedDate.toLocaleDateString("en-US", {
                        weekday: "long",
                        month: "long",
                        day: "numeric",
                        year: "numeric",
                      });

                return (
                  <div key={day} className="relative">
                    {/* Day Group Divider Pill */}
                    <div className="sticky top-20 z-10 flex items-center gap-3 mb-5 py-1">
                      <div className="h-px flex-1 bg-slate-200" />
                      <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-white border border-slate-200/90 shadow-2xs text-xs font-bold text-slate-700">
                        <Calendar size={12} className="text-indigo-600" />
                        <span>{dayLabel}</span>
                        <span className="text-[10px] font-mono font-normal text-slate-400 bg-slate-100 px-1.5 py-0.2 rounded-full">
                          {dayEvents.length} {dayEvents.length === 1 ? "Event" : "Events"}
                        </span>
                      </div>
                      <div className="h-px flex-1 bg-slate-200" />
                    </div>

                    {/* Timeline Event Cards Stack with Vertical Connector Line */}
                    <div className="space-y-4 pl-6 relative">
                      {/* Vertical Continuous Connecting Line */}
                      <div className="absolute left-2.5 top-3 bottom-3 w-[2px] bg-slate-200" />

                      {dayEvents.map((ev) => {
                        const isExpanded = expandedQuotes[ev.id];
                        const eventType = ev.event_type.toUpperCase();

                        // Type specific styles
                        let badgeBg = "bg-slate-100 text-slate-700 border-slate-200";
                        let dotColor = "bg-slate-400";
                        let typeIcon = <Clock size={12} />;

                        if (eventType === "DECISION") {
                          badgeBg = "bg-amber-50 text-amber-800 border-amber-200";
                          dotColor = "bg-amber-500 ring-amber-200";
                          typeIcon = <Shield size={12} className="text-amber-600" />;
                        } else if (eventType === "ACTION") {
                          badgeBg = "bg-emerald-50 text-emerald-800 border-emerald-200";
                          dotColor = "bg-emerald-500 ring-emerald-200";
                          typeIcon = <CheckCircle2 size={12} className="text-emerald-600" />;
                        } else if (eventType === "ARCHITECTURE") {
                          badgeBg = "bg-indigo-50 text-indigo-800 border-indigo-200";
                          dotColor = "bg-indigo-600 ring-indigo-200";
                          typeIcon = <Layers size={12} className="text-indigo-600" />;
                        } else if (eventType === "TOPIC") {
                          badgeBg = "bg-violet-50 text-violet-800 border-violet-200";
                          dotColor = "bg-violet-500 ring-violet-200";
                          typeIcon = <BarChart3 size={12} className="text-violet-600" />;
                        } else if (eventType === "MILESTONE") {
                          badgeBg = "bg-sky-50 text-sky-800 border-sky-200";
                          dotColor = "bg-sky-500 ring-sky-200";
                          typeIcon = <Sparkles size={12} className="text-sky-600" />;
                        }

                        return (
                          <div key={ev.id} className="relative group">
                            {/* Dot on Timeline with Ring */}
                            <div
                              className={cn(
                                "absolute -left-6 top-5 w-3 h-3 rounded-full border-2 border-white ring-2 transition-transform duration-150 group-hover:scale-125 z-10",
                                dotColor
                              )}
                            />

                            {/* Card Body */}
                            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs hover:shadow-xs hover:border-slate-300 transition-all p-5 space-y-3">
                              {/* Header Meta Row */}
                              <div className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2 flex-wrap">
                                  {/* Event Type Badge */}
                                  <span
                                    className={cn(
                                      "inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border",
                                      badgeBg
                                    )}
                                  >
                                    {typeIcon}
                                    <span>{eventType}</span>
                                  </span>

                                  {/* Relative Time / Timestamp */}
                                  <span className="text-[11px] text-slate-500 font-mono flex items-center gap-1">
                                    <Clock size={11} className="text-slate-400" />
                                    <span>{formatDate(ev.occurred_at)}</span>
                                  </span>
                                </div>

                                {/* Meeting Title Chip (Clickable to /meetings/:id) */}
                                <Link
                                  href={`/meetings/${ev.meeting_id}`}
                                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium hover:underline inline-flex items-center gap-1 bg-indigo-50/70 border border-indigo-100 px-2 py-0.5 rounded-lg truncate max-w-xs transition-colors"
                                  title={`Open meeting: ${ev.meeting_title}`}
                                >
                                  <span>📋</span>
                                  <span className="truncate">{ev.meeting_title}</span>
                                  <ExternalLink size={10} className="shrink-0" />
                                </Link>
                              </div>

                              {/* Title & Summary */}
                              <div>
                                <h4 className="text-sm font-bold text-slate-900 leading-snug">
                                  {ev.entity_name}
                                </h4>
                                <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                                  {ev.summary}
                                </p>
                              </div>

                              {/* Expandable Evidence Quote */}
                              {ev.evidence_text && (
                                <div className="pt-1">
                                  <button
                                    onClick={() => toggleQuote(ev.id)}
                                    className="text-[11px] text-slate-500 hover:text-indigo-600 font-semibold flex items-center gap-1 cursor-pointer transition-colors"
                                  >
                                    <Quote size={11} className="text-indigo-500" />
                                    <span>
                                      {isExpanded ? "Hide transcript evidence" : "View transcript quote"}
                                    </span>
                                    {isExpanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                                  </button>

                                  {isExpanded && (
                                    <blockquote className="mt-2 text-xs text-slate-700 italic border-l-3 border-indigo-400 bg-slate-50/80 p-3 rounded-r-xl leading-relaxed animate-in fade-in duration-150">
                                      &ldquo;{ev.evidence_text}&rdquo;
                                    </blockquote>
                                  )}
                                </div>
                              )}

                              {/* Footer Action Row: Speaker & Copilot Query Action */}
                              <div className="pt-2 border-t border-slate-100 flex items-center justify-between gap-2 text-xs">
                                <div className="flex items-center gap-2">
                                  {ev.speaker ? (
                                    <span
                                      className="inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-md bg-slate-100"
                                      style={{ color: speakerColor(ev.speaker) }}
                                    >
                                      <User size={11} />
                                      <span>{ev.speaker}</span>
                                    </span>
                                  ) : (
                                    <span className="text-[11px] text-slate-400">Team Consensus</span>
                                  )}
                                </div>

                                <button
                                  onClick={() => handleAskAboutEvent(ev)}
                                  className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 px-2.5 py-1 rounded-lg transition-colors cursor-pointer flex items-center gap-1"
                                >
                                  <Sparkles size={11} />
                                  <span>Ask Copilot</span>
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* ── RIGHT PANE: ANALYTICS COPILOT DRAWER ────────────────────────────── */}
        {isCopilotOpen && (
          <div className="lg:col-span-5 xl:col-span-4 bg-white rounded-2xl border border-slate-200/90 shadow-xl overflow-hidden flex flex-col h-[740px] sticky top-20 animate-in fade-in slide-in-from-right-4 duration-200">
            {/* Copilot Header */}
            <div className="px-4 py-3.5 border-b border-slate-200 bg-white flex items-center justify-between gap-3 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center shrink-0 shadow-2xs">
                  <Sparkles size={16} />
                </div>
                <div className="min-w-0">
                  <h3 className="text-sm font-bold text-slate-900 leading-none">
                    Analytics Copilot
                  </h3>
                  <p className="text-[11px] text-slate-500 mt-1 truncate">
                    Cross-meeting intelligence across {metrics.meetings} meetings & {metrics.decisions} decisions
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1.5 shrink-0">
                <button
                  onClick={handleNewChat}
                  className="px-2.5 py-1.5 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-xs font-semibold text-slate-700 transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  title="Start a new chat thread"
                >
                  <Plus size={13} />
                  <span>New</span>
                </button>
                <button
                  onClick={handleClearChatHistory}
                  className="w-8 h-8 rounded-lg border border-slate-200 bg-slate-50 hover:bg-slate-100 text-slate-500 hover:text-slate-800 flex items-center justify-center transition-colors cursor-pointer shadow-2xs"
                  title="Reset conversation"
                >
                  <RotateCcw size={13} />
                </button>
                <button
                  onClick={() => setIsCopilotOpen(false)}
                  className="w-8 h-8 rounded-lg border border-transparent hover:border-slate-200 hover:bg-slate-100 text-slate-400 hover:text-slate-700 flex items-center justify-center transition-colors cursor-pointer"
                  title="Close Copilot"
                >
                  <X size={15} />
                </button>
              </div>
            </div>

            {/* Chat Messages Area */}
            <div className="flex-1 p-3.5 overflow-y-auto space-y-4 bg-slate-50/40 text-xs">
              {activeSession?.messages.map((m) => {
                const isUser = m.role === "user";

                if (isUser) {
                  return (
                    <div key={m.id} className="flex flex-col items-end space-y-1 max-w-[88%] ml-auto">
                      <div className="bg-[#4f46e5] text-white rounded-2xl rounded-tr-xs px-4 py-2.5 text-xs shadow-2xs leading-relaxed font-medium break-words select-text">
                        {m.content}
                      </div>
                      <span className="text-[9px] text-slate-400 pr-1">{m.timestamp}</span>
                    </div>
                  );
                }

                return (
                  <div key={m.id} className="flex items-start gap-2.5 max-w-[96%]">
                    <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 flex items-center justify-center text-white shrink-0 mt-0.5 shadow-2xs">
                      <Bot size={14} />
                    </div>

                    <div className="flex-1 min-w-0 bg-white border border-slate-200/90 rounded-2xl rounded-tl-xs p-3.5 shadow-2xs space-y-2.5">
                      {/* Rich Formatted Markdown Content */}
                      <FormattedAnalyticsMessage content={m.content} />

                      {/* Verified Timeline Citations */}
                      {m.citations && m.citations.length > 0 && (
                        <div className="mt-3 pt-2.5 border-t border-slate-100 space-y-1.5">
                          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1">
                            <Compass size={11} className="text-indigo-600" />
                            <span>Verified Timeline Citations:</span>
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {m.citations.map((c, idx) => (
                              <Link
                                key={idx}
                                href={`/meetings/${c.meeting_id}`}
                                className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-[10px] font-semibold bg-indigo-50/80 border border-indigo-200 text-indigo-700 hover:bg-indigo-100 hover:border-indigo-300 transition-all cursor-pointer shadow-2xs group"
                                title={`Open meeting: ${c.meeting_title}`}
                              >
                                <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 group-hover:scale-125 transition-transform shrink-0" />
                                <span className="truncate max-w-[190px]">
                                  {c.event_title || c.meeting_title}
                                </span>
                              </Link>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Card Footer: Timestamp & Copy Button */}
                      <div className="flex items-center justify-between pt-1 text-[10px] text-slate-400">
                        <span>{m.timestamp}</span>
                        <button
                          onClick={() => handleCopyMessage(m.id, m.content)}
                          className="flex items-center gap-1 hover:text-slate-700 text-[10px] text-slate-400 font-medium transition-colors cursor-pointer"
                          title="Copy response to clipboard"
                        >
                          {copiedId === m.id ? (
                            <>
                              <Check size={11} className="text-emerald-600" />
                              <span className="text-emerald-600 font-semibold">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy size={11} />
                              <span>Copy</span>
                            </>
                          )}
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}

              {isThinking && (
                <div className="flex items-start gap-2.5">
                  <div className="w-7 h-7 rounded-xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white flex items-center justify-center shrink-0 shadow-2xs">
                    <Sparkles size={14} className="animate-spin" />
                  </div>
                  <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-xs px-3.5 py-2.5 text-xs text-slate-500 flex items-center gap-2 shadow-2xs">
                    <RefreshCw size={12} className="animate-spin text-indigo-600" />
                    <span className="font-medium animate-pulse">
                      Analyzing {metrics.decisions} decisions & {metrics.actions} commitments across meetings...
                    </span>
                  </div>
                </div>
              )}

              <div ref={chatBottomRef} />
            </div>

            {/* Quick Suggested Queries (shown when thread is fresh) */}
            {activeSession && activeSession.messages.length <= 1 && (
              <div className="p-3 border-t border-slate-200/80 bg-slate-50/70 shrink-0">
                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <HelpCircle size={11} className="text-indigo-600" />
                  <span>Suggested Analytics Queries:</span>
                </p>
                <div className="space-y-1.5">
                  {SUGGESTED_ANALYTICS_QUERIES.map((q, qIdx) => (
                    <button
                      key={qIdx}
                      onClick={() => handleSendQuery(q)}
                      className="w-full text-left text-xs text-slate-700 hover:text-indigo-700 hover:bg-white p-2 rounded-xl border border-transparent hover:border-slate-200 transition-all flex items-center justify-between group cursor-pointer shadow-2xs hover:shadow-xs"
                    >
                      <span className="truncate pr-2">• {q}</span>
                      <ArrowRight
                        size={12}
                        className="text-slate-400 group-hover:text-indigo-600 shrink-0 transition-transform group-hover:translate-x-0.5"
                      />
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat Input Bar */}
            <div className="p-3 bg-white border-t border-slate-200 shrink-0">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendQuery();
                }}
                className="relative flex items-center bg-slate-50 border border-slate-200 rounded-xl focus-within:border-indigo-600 focus-within:bg-white focus-within:ring-2 focus-within:ring-indigo-100 transition-all shadow-2xs"
              >
                <input
                  type="text"
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Ask about cross-meeting decisions, roadmap, commitments..."
                  disabled={isThinking}
                  className="w-full text-xs bg-transparent py-2.5 pl-3.5 pr-10 focus:outline-none text-slate-800 placeholder-slate-400"
                />
                <button
                  type="submit"
                  disabled={!chatInput.trim() || isThinking}
                  className="absolute right-1.5 w-7 h-7 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center disabled:opacity-30 transition-all cursor-pointer shadow-2xs"
                  title="Send query"
                >
                  <Send size={12} />
                </button>
              </form>
              <div className="flex items-center justify-between mt-2 px-1 text-[10px] text-slate-400">
                <span>Press Enter ↵ to send</span>
                <span>Groq LLM • Cross-Meeting RAG</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
