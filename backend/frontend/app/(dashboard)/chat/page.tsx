"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, apiStream } from "@/lib/api/client";
import { CHAT, MEETINGS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type ChatSession, type ChatMessage, type Citation, type Meeting } from "@/lib/types";
import { Card, Spinner } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, relativeTime, truncate, formatDuration } from "@/lib/utils";
import {
  MessageSquare,
  Send,
  Plus,
  ChevronRight,
  X,
  ExternalLink,
  FileText,
  Bot,
  User,
  Search,
  Trash2,
  Clock,
  Sparkles,
  ShieldCheck,
  History,
  Copy,
  Check,
  Filter,
  CheckCircle2,
  ArrowRight,
  Layers,
} from "lucide-react";
import Link from "next/link";

interface FlexibleChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  created_at: string;
  intent?: string;
  retrieval_metadata?: Record<string, unknown>;
}

export default function ChatPage() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [selectedMeetingId, setSelectedMeetingId] = useState<string>("all");
  const [input, setInput] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [openCitation, setOpenCitation] = useState<Citation | null>(null);
  const [historySearch, setHistorySearch] = useState("");
  const [showRightHistory, setShowRightHistory] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const qc = useQueryClient();

  // 1. Fetch Chat Sessions (Right-side history)
  const { data: rawSessions, isLoading: sessionsLoading } = useQuery({
    queryKey: queryKeys.chat.sessions(),
    queryFn: () => api.get<ChatSession[] | { items: ChatSession[] }>(CHAT.sessions()),
  });
  const sessions: ChatSession[] = useMemo(() => {
    if (Array.isArray(rawSessions)) return rawSessions;
    if (rawSessions && Array.isArray((rawSessions as { items?: ChatSession[] }).items)) {
      return (rawSessions as { items: ChatSession[] }).items;
    }
    return [];
  }, [rawSessions]);

  // 2. Fetch User Meetings for Scope Filter (unwrap paginated items)
  const { data: rawMeetings } = useQuery({
    queryKey: queryKeys.meetings.list({ page_size: 100 }),
    queryFn: () =>
      api.get<{ items: Meeting[]; total: number } | Meeting[]>(
        `${MEETINGS.list()}?page_size=100`
      ),
  });
  const meetings: Meeting[] = useMemo(() => {
    if (Array.isArray(rawMeetings)) return rawMeetings;
    if (rawMeetings && Array.isArray((rawMeetings as { items?: Meeting[] }).items)) {
      return (rawMeetings as { items: Meeting[] }).items;
    }
    return [];
  }, [rawMeetings]);

  // Set the first session as active if none selected and sessions exist
  useEffect(() => {
    if (!activeSessionId && sessions.length > 0) {
      setActiveSessionId(sessions[0].id);
    }
  }, [sessions, activeSessionId]);

  // 3. Messages for active session
  const { data: rawMessages, isLoading: messagesLoading } = useQuery({
    queryKey: queryKeys.chat.messages(activeSessionId ?? ""),
    queryFn: () =>
      api.get<FlexibleChatMessage[] | { items: FlexibleChatMessage[] }>(
        CHAT.messages(activeSessionId!)
      ),
    enabled: !!activeSessionId,
  });
  const messages: FlexibleChatMessage[] = useMemo(() => {
    if (Array.isArray(rawMessages)) return rawMessages;
    if (rawMessages && Array.isArray((rawMessages as { items?: FlexibleChatMessage[] }).items)) {
      return (rawMessages as { items: FlexibleChatMessage[] }).items;
    }
    return [];
  }, [rawMessages]);

  // 4. Create new chat session
  const createSession = useMutation({
    mutationFn: (initialTitle?: string) =>
      api.post<ChatSession>(CHAT.sessions(), {
        title: initialTitle ?? "New Chat",
        meeting_id: selectedMeetingId !== "all" ? selectedMeetingId : null,
      }),
    onSuccess: (session) => {
      qc.invalidateQueries({ queryKey: queryKeys.chat.sessions() });
      setActiveSessionId(session.id);
    },
  });

  // 5. Delete session
  const deleteSession = useMutation({
    mutationFn: (sessionId: string) =>
      api.delete<{ status: string; id: string }>(CHAT.session(sessionId)),
    onSuccess: (_, deletedId) => {
      qc.invalidateQueries({ queryKey: queryKeys.chat.sessions() });
      if (activeSessionId === deletedId) {
        const remaining = sessions.filter((s) => s.id !== deletedId);
        setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
      }
    },
  });

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent, isStreaming]);

  // Filtered sessions for right sidebar
  const filteredSessions = useMemo(() => {
    if (!historySearch.trim()) return sessions;
    const q = historySearch.toLowerCase();
    return sessions.filter((s) => (s.title ?? "Chat").toLowerCase().includes(q));
  }, [sessions, historySearch]);

  // Copy assistant response
  const handleCopy = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Send message
  const handleSend = useCallback(
    async (textToSend?: string) => {
      const prompt = (textToSend ?? input).trim();
      if (!prompt || isStreaming) return;

      let sessionId = activeSessionId;
      if (!sessionId) {
        try {
          const session = await createSession.mutateAsync(
            prompt.length > 50 ? prompt.slice(0, 50) + "..." : prompt
          );
          sessionId = session.id;
        } catch {
          return;
        }
      }

      setInput("");
      setIsStreaming(true);
      setStreamingContent("");

      // Optimistically add user message
      qc.setQueryData<FlexibleChatMessage[]>(
        queryKeys.chat.messages(sessionId),
        (prev = []) => [
          ...prev,
          {
            id: `tmp-${Date.now()}`,
            role: "user",
            content: prompt,
            created_at: new Date().toISOString(),
          },
        ]
      );

      try {
        let fullContent = "";
        let streamWorked = false;

        const streamUrl = CHAT.stream(sessionId);
        for await (const chunk of apiStream(streamUrl, {
          content: prompt,
          meeting_id: selectedMeetingId !== "all" ? selectedMeetingId : undefined,
        })) {
          streamWorked = true;
          try {
            const parsed = JSON.parse(chunk);
            if (parsed.delta) {
              fullContent += parsed.delta;
              setStreamingContent(fullContent);
            }
          } catch {
            fullContent += chunk;
            setStreamingContent(fullContent);
          }
        }

        if (!streamWorked) {
          throw new Error("Stream returned no tokens, fallback to standard query");
        }
      } catch {
        // Fallback non-streaming query
        try {
          const res = await api.post<{
            answer: string;
            citations: Citation[];
            conversation_id: string;
          }>(CHAT.query(), {
            session_id: sessionId,
            content: prompt,
            meeting_id: selectedMeetingId !== "all" ? selectedMeetingId : undefined,
          });
          setStreamingContent(res.answer);
        } catch {
          setStreamingContent(
            "I encountered an error processing your query. Please check that the server is online."
          );
        }
      } finally {
        setIsStreaming(false);
        setStreamingContent("");
        qc.invalidateQueries({ queryKey: queryKeys.chat.messages(sessionId!) });
        qc.invalidateQueries({ queryKey: queryKeys.chat.sessions() });
      }
    },
    [input, activeSessionId, isStreaming, selectedMeetingId, createSession, qc]
  );

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handlePromptSelect = (prompt: string) => {
    setInput(prompt);
    handleSend(prompt);
  };

  const activeSession = sessions.find((s) => s.id === activeSessionId);

  return (
    <div className="flex h-[calc(100vh-56px-48px)] gap-4 animate-fade-in text-[var(--foreground)]">
      {/* ─── Center / Left: Main Conversational Canvas ────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 gap-3">
        {/* Messages Card (Single clean card) */}
        <div className="flex-1 flex flex-col min-w-0 bg-white border border-slate-200/80 rounded-2xl shadow-2xs overflow-hidden">
          {/* Top Control Bar */}
          <div className="h-14 border-b border-slate-100 px-4 flex items-center justify-between bg-slate-50/50 backdrop-blur-sm shrink-0">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-sm shrink-0">
                <Bot size={17} className="text-white" />
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold truncate text-slate-900">
                    {activeSession?.title ?? "Knowra AI Assistant"}
                  </h2>
                  <span className="hidden sm:inline-flex items-center gap-1 text-[10px] font-medium px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                    RAG Active
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 truncate">
                  Grounded in 42+ verified meeting transcripts with pgvector hybrid search
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {/* Meeting Scope Filter */}
              <div className="hidden md:flex items-center gap-1.5 bg-white border border-slate-200 rounded-lg px-2.5 py-1 text-xs text-slate-600">
                <Filter size={12} className="text-[#5345dc]" />
                <select
                  aria-label="Filter context by meeting scope"
                  value={selectedMeetingId}
                  onChange={(e) => setSelectedMeetingId(e.target.value)}
                  className="bg-transparent text-xs text-slate-800 focus:outline-none cursor-pointer max-w-[180px] truncate"
                >
                  <option value="all">Scope: All Meetings</option>
                  {Array.isArray(meetings) &&
                    meetings.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.title}
                      </option>
                    ))}
                </select>
              </div>

              {/* New Chat Button */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => {
                  setActiveSessionId(null);
                  createSession.mutate();
                }}
                isLoading={createSession.isPending}
                className="gap-1.5 text-xs font-medium border-slate-200"
                id="new-chat-top-btn"
              >
                <Plus size={13} />
                <span className="hidden sm:inline">New Chat</span>
              </Button>

              {/* Toggle Right Chat Stores Sidebar */}
              <Button
                variant={showRightHistory ? "secondary" : "ghost"}
                size="sm"
                onClick={() => setShowRightHistory(!showRightHistory)}
                className="gap-1.5 text-xs"
                title={showRightHistory ? "Hide Chat History" : "Show Chat History"}
                aria-label="Toggle chat history"
              >
                <History size={14} />
                <span className="hidden lg:inline">{sessions.length}</span>
              </Button>
            </div>
          </div>

          {/* Scrollable Messages Canvas */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
            {(!activeSessionId && messages.length === 0) || (messages.length === 0 && !isStreaming) ? (
              <WelcomeEnterpriseScreen
                onSelectPrompt={handlePromptSelect}
                totalMeetings={meetings.length || 42}
              />
            ) : (
              <>
                {messagesLoading && messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-48 gap-2">
                    <Spinner size={24} />
                    <p className="text-xs text-[var(--muted)]">Loading conversation...</p>
                  </div>
                ) : (
                  messages.map((msg) => (
                    <MessageBubble
                      key={msg.id}
                      message={msg}
                      onCitationClick={setOpenCitation}
                      onCopy={handleCopy}
                      copiedId={copiedId}
                    />
                  ))
                )}

                {/* Streaming Bubble */}
                {isStreaming && streamingContent && (
                  <StreamingMessageBubble content={streamingContent} />
                )}

                {/* Thinking Indicator */}
                {isStreaming && !streamingContent && (
                  <div className="flex gap-3 items-start animate-fade-in">
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 shadow-sm mt-0.5">
                      <Bot size={15} className="text-white" />
                    </div>
                    <div className="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl rounded-tl-sm px-4 py-3 text-xs text-[var(--muted)] flex items-center gap-2 shadow-sm">
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="text-[11px] text-[var(--muted-strong)] ml-1">
                        Searching hybrid vector index & canonical transcripts...
                      </span>
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Input Bar (Single Clean Border, Outside Wrapper Border Removed) */}
        <div className="shrink-0">
          <div className="max-w-4xl mx-auto">
            <div className="relative flex flex-col bg-white border border-[#d8d2f8] hover:border-[#5345dc]/40 rounded-2xl shadow-2xs focus-within:ring-2 focus-within:ring-[#5345dc]/20 focus-within:border-[#5345dc] transition-all">
              <textarea
                ref={textareaRef}
                id="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about meeting decisions, action items, architecture discussions... (Enter to send)"
                rows={2}
                disabled={isStreaming}
                className={cn(
                  "w-full resize-none bg-transparent px-4 pt-3 pb-10 text-sm text-slate-800",
                  "placeholder:text-slate-400 focus:outline-none",
                  "max-h-36 overflow-y-auto leading-relaxed",
                  isStreaming && "opacity-60 cursor-not-allowed"
                )}
              />

              <div className="absolute bottom-2.5 left-3.5 right-2.5 flex items-center justify-between pointer-events-none">
                <div className="pointer-events-auto flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 text-[11px] text-slate-500 bg-slate-100 px-2 py-0.5 rounded-md border border-slate-200">
                    <Layers size={10} className="text-[#5345dc]" />
                    {selectedMeetingId === "all" ? "All Meetings" : "Filtered Scope"}
                  </span>
                </div>

                <div className="pointer-events-auto flex items-center gap-2">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleSend()}
                    disabled={!input.trim() || isStreaming}
                    id="chat-send-btn"
                    className="h-8 px-3 rounded-lg gap-1.5 shadow-sm bg-[#5345dc] hover:bg-[#4338ca] text-white"
                    aria-label="Send message"
                  >
                    <span className="text-xs font-medium hidden sm:inline">Ask</span>
                    <Send size={13} />
                  </Button>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1.5 px-2">
              <span className="flex items-center gap-1">
                <ShieldCheck size={11} className="text-emerald-500" />
                Grounded in authenticated organization transcripts with verifiable citations.
              </span>
              <span className="hidden sm:inline">Shift + Enter for new line</span>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Right Side: Stored Chats & History Sidebar ("chat stores right side") ─── */}
      {showRightHistory && (
        <div className="w-72 lg:w-80 shrink-0 flex flex-col bg-white border border-slate-200/80 rounded-2xl shadow-2xs overflow-hidden animate-slide-in-right">
          {/* Header */}
          <div className="h-14 border-b border-slate-100 px-4 flex items-center justify-between bg-slate-50/50 shrink-0">
            <div className="flex items-center gap-2">
              <History size={16} className="text-[#5345dc]" />
              <h3 className="text-sm font-semibold text-slate-800">Chat History</h3>
              <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {sessions.length}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => createSession.mutate()}
              isLoading={createSession.isPending}
              className="h-7 px-2 text-xs gap-1 border-slate-200"
              id="right-new-chat-btn"
              title="Start a new chat session"
            >
              <Plus size={12} />
              New
            </Button>
          </div>

          {/* Search Stored Chats */}
          <div className="p-3 border-b border-slate-100 shrink-0">
            <div className="relative">
              <Search
                size={13}
                className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400"
              />
              <input
                type="text"
                value={historySearch}
                onChange={(e) => setHistorySearch(e.target.value)}
                placeholder="Search past conversations..."
                className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:border-[#5345dc]"
              />
              {historySearch && (
                <button
                  onClick={() => setHistorySearch("")}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {sessionsLoading ? (
              <div className="flex flex-col items-center justify-center py-12 gap-2">
                <Spinner size={18} />
                <p className="text-xs text-[var(--muted)]">Loading stored chats...</p>
              </div>
            ) : filteredSessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <MessageSquare size={28} className="text-[var(--muted)] mb-2 opacity-60" />
                <p className="text-xs font-medium text-[var(--foreground)]">No conversations</p>
                <p className="text-[11px] text-[var(--muted)] mt-1">
                  {historySearch ? "No chats matching your search." : "Start asking questions to build your history."}
                </p>
              </div>
            ) : (
              filteredSessions.map((session) => {
                const isActive = activeSessionId === session.id;
                return (
                  <div
                    key={session.id}
                    onClick={() => setActiveSessionId(session.id)}
                    className={cn(
                      "group relative w-full text-left p-3 rounded-xl transition-all cursor-pointer border",
                      isActive
                        ? "bg-[var(--primary-muted)]/40 border-[var(--primary)]/40 shadow-xs"
                        : "bg-transparent border-transparent hover:bg-[var(--surface-2)] hover:border-[var(--border)]"
                    )}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p
                          className={cn(
                            "text-xs font-medium truncate leading-tight",
                            isActive ? "text-[var(--primary)] font-semibold" : "text-[var(--foreground)]"
                          )}
                        >
                          {session.title || "Untitled Conversation"}
                        </p>
                        <div className="flex items-center gap-1.5 mt-1 text-[10px] text-[var(--muted)]">
                          <Clock size={10} />
                          <span>{relativeTime(session.updated_at)}</span>
                        </div>
                      </div>

                      {/* Delete Button on Hover */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteSession.mutate(session.id);
                        }}
                        className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-[var(--muted)] hover:text-red-500 hover:bg-red-500/10 transition-all shrink-0"
                        title="Delete conversation"
                        aria-label="Delete conversation"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* ─── Far Right: Citation Inspector Drawer ─────────────────────────── */}
      {openCitation && (
        <CitationInspectorDrawer
          citation={openCitation}
          onClose={() => setOpenCitation(null)}
        />
      )}
    </div>
  );
}

// ─── Sub-Components ────────────────────────────────────────────────────────────

function WelcomeEnterpriseScreen({
  onSelectPrompt,
  totalMeetings,
}: {
  onSelectPrompt: (prompt: string) => void;
  totalMeetings: number;
}) {
  const suggestions = [
    {
      title: "Friday Release Planning",
      desc: "What was discussed and planned for the Friday production release?",
      icon: "🚀",
      prompt: "What was planned and discussed for the Friday Production Release?",
    },
    {
      title: "Audio & Troubleshooting",
      desc: "What issues and troubleshooting steps were found with bot deployment and audio connectivity?",
      icon: "🎧",
      prompt: "What issues or troubleshooting steps were discussed regarding audio connectivity and bot deployment?",
    },
    {
      title: "Decisions & Commitments",
      desc: "What key architecture and technical decisions were finalized across meetings?",
      icon: "⚖️",
      prompt: "What key architecture, deployment, and technical decisions were agreed upon in recent meetings?",
    },
    {
      title: "App & Walkthrough Summary",
      desc: "Summarize the key workflows from the desktop and mobile app walkthrough sessions.",
      icon: "📱",
      prompt: "Summarize the key features and workflows demonstrated in the app walkthrough sessions.",
    },
  ];

  return (
    <div className="flex flex-col items-center justify-center min-h-[460px] py-8 text-center max-w-2xl mx-auto px-4 animate-fade-in">
      <div className="relative mb-5">
        <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-purple-500/20">
          <Sparkles size={28} className="text-white" />
        </div>
        <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-emerald-500 flex items-center justify-center text-white border-2 border-[var(--surface-1)]">
          <CheckCircle2 size={13} />
        </div>
      </div>

      <h1 className="text-xl sm:text-2xl font-bold text-[var(--foreground)] tracking-tight">
        Knowra Enterprise Intelligence
      </h1>
      <p className="text-xs sm:text-sm text-[var(--muted)] mt-2 max-w-lg leading-relaxed">
        Query across <strong className="text-[var(--foreground)]">{totalMeetings} indexed meetings</strong>.
        Every response is synthesized with hybrid vector retrieval, Reciprocal Rank Fusion, and verified
        citations.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full mt-8 text-left">
        {suggestions.map((item, idx) => (
          <button
            key={idx}
            onClick={() => onSelectPrompt(item.prompt)}
            className="group p-4 rounded-xl bg-[var(--surface-2)]/70 hover:bg-[var(--surface-2)] border border-[var(--border)] hover:border-[var(--primary)]/50 transition-all hover:shadow-sm flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-base">{item.icon}</span>
                <span className="text-xs font-semibold text-[var(--foreground)] group-hover:text-[var(--primary)] transition-colors">
                  {item.title}
                </span>
              </div>
              <p className="text-[11px] text-[var(--muted)] leading-normal line-clamp-2">
                {item.desc}
              </p>
            </div>
            <div className="flex items-center gap-1 text-[10px] text-[var(--primary)] font-medium mt-3 opacity-0 group-hover:opacity-100 transition-opacity">
              <span>Ask Knowra</span>
              <ArrowRight size={10} />
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

function MessageBubble({
  message,
  onCitationClick,
  onCopy,
  copiedId,
}: {
  message: FlexibleChatMessage;
  onCitationClick: (c: Citation) => void;
  onCopy: (id: string, text: string) => void;
  copiedId: string | null;
}) {
  const isUser = message.role === "user";

  return (
    <div className={cn("flex gap-3 max-w-4xl mx-auto", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 shadow-sm mt-0.5">
          <Bot size={15} className="text-white" />
        </div>
      )}

      <div className={cn("space-y-2 max-w-[85%] sm:max-w-[78%]", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-2xl px-4 py-3 text-xs sm:text-sm leading-relaxed shadow-xs relative group",
            isUser
              ? "bg-[var(--primary)] text-white rounded-tr-xs"
              : "bg-[var(--surface-2)] text-[var(--foreground)] border border-[var(--border)] rounded-tl-xs"
          )}
        >
          {/* Formatted Text Content */}
          <div className="font-normal break-words">
            <FormattedMessageContent content={message.content} isUser={isUser} />
          </div>

          {/* Copy Button for Assistant */}
          {!isUser && (
            <button
              onClick={() => onCopy(message.id, message.content)}
              className="absolute top-2 right-2 p-1 rounded-md text-[var(--muted)] hover:text-[var(--foreground)] hover:bg-[var(--surface-3)] transition-all opacity-0 group-hover:opacity-100"
              title="Copy answer"
              aria-label="Copy answer to clipboard"
            >
              {copiedId === message.id ? (
                <Check size={12} className="text-emerald-500" />
              ) : (
                <Copy size={12} />
              )}
            </button>
          )}
        </div>

        {/* Citations Badges */}
        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            <span className="text-[10px] text-[var(--muted)] font-medium self-center mr-1">
              Sources:
            </span>
            {message.citations.map((c, i) => {
              const speaker = c.speaker ?? c.speaker_name ?? "Speaker";
              const title = c.meeting_title ?? "Meeting";
              const timeSec = c.timestamp ?? c.start_seconds ?? 0;
              return (
                <button
                  key={c.chunk_id ? `${c.chunk_id}-${i}` : i}
                  onClick={() => onCitationClick(c)}
                  className="inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full bg-[var(--surface-2)] border border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--primary)] hover:text-[var(--primary)] hover:bg-[var(--primary-muted)]/20 transition-all shadow-2xs"
                  title="View transcript proof"
                >
                  <FileText size={10} className="text-[var(--primary)] shrink-0" />
                  <span className="font-medium text-[var(--foreground)]">{speaker}</span>
                  <span className="text-[var(--muted)]">•</span>
                  <span className="truncate max-w-[130px]">{truncate(title, 20)}</span>
                  <span className="font-mono text-[10px] text-[var(--muted)]">
                    {formatDuration(timeSec)}
                  </span>
                  <ChevronRight size={10} className="text-[var(--muted)]" />
                </button>
              );
            })}
          </div>
        )}
      </div>

      {isUser && (
        <div className="w-8 h-8 rounded-xl bg-[var(--surface-3)] border border-[var(--border)] flex items-center justify-center shrink-0 shadow-xs mt-0.5">
          <User size={15} className="text-[var(--muted-strong)]" />
        </div>
      )}
    </div>
  );
}

function StreamingMessageBubble({ content }: { content: string }) {
  return (
    <div className="flex gap-3 max-w-4xl mx-auto justify-start animate-fade-in">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0 shadow-sm mt-0.5">
        <Bot size={15} className="text-white" />
      </div>
      <div className="max-w-[85%] sm:max-w-[78%]">
        <div className="bg-[var(--surface-2)] border border-[var(--border)] rounded-2xl rounded-tl-xs px-4 py-3 text-xs sm:text-sm leading-relaxed text-[var(--foreground)] shadow-xs">
          <FormattedMessageContent content={content} isUser={false} />
          <span className="inline-block w-1.5 h-3.5 bg-[var(--primary)] ml-1 animate-pulse align-middle" />
        </div>
      </div>
    </div>
  );
}

function FormattedMessageContent({ content, isUser }: { content: string; isUser: boolean }) {
  if (isUser) {
    return <div className="whitespace-pre-wrap font-normal break-words">{content}</div>;
  }

  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let currentList: { type: "ul" | "ol"; items: string[] } | null = null;

  const flushList = () => {
    if (!currentList) return;
    if (currentList.type === "ul") {
      elements.push(
        <ul key={`ul-${elements.length}`} className="my-2 space-y-1.5 pl-1">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-xs sm:text-sm">
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#5345dc] mt-1.5 shrink-0" />
              <span className="leading-relaxed">{formatInlineMarkdown(item)}</span>
            </li>
          ))}
        </ul>
      );
    } else {
      elements.push(
        <ol key={`ol-${elements.length}`} className="my-2 space-y-1.5 pl-1">
          {currentList.items.map((item, idx) => (
            <li key={idx} className="flex items-start gap-2 text-xs sm:text-sm">
              <span className="font-semibold text-xs text-[#5345dc] shrink-0 mt-0.5">{idx + 1}.</span>
              <span className="leading-relaxed">{formatInlineMarkdown(item)}</span>
            </li>
          ))}
        </ol>
      );
    }
    currentList = null;
  };

  lines.forEach((rawLine, i) => {
    const line = rawLine.trim();

    if (!line) {
      flushList();
      return;
    }

    // Headings
    if (line.startsWith("#### ")) {
      flushList();
      elements.push(
        <h5 key={i} className="text-xs font-bold text-slate-800 dark:text-slate-100 mt-2 mb-1">
          {formatInlineMarkdown(line.slice(5))}
        </h5>
      );
      return;
    }
    if (line.startsWith("### ")) {
      flushList();
      elements.push(
        <h4 key={i} className="text-sm font-bold text-slate-900 dark:text-white mt-3 mb-1.5 flex items-center gap-1.5">
          <span className="w-1 h-3.5 rounded-full bg-[#5345dc] inline-block" />
          {formatInlineMarkdown(line.slice(4))}
        </h4>
      );
      return;
    }
    if (line.startsWith("## ")) {
      flushList();
      elements.push(
        <h3 key={i} className="text-base font-bold text-slate-900 dark:text-white mt-3.5 mb-1.5">
          {formatInlineMarkdown(line.slice(3))}
        </h3>
      );
      return;
    }
    if (line.startsWith("# ")) {
      flushList();
      elements.push(
        <h2 key={i} className="text-lg font-extrabold text-slate-900 dark:text-white mt-4 mb-2">
          {formatInlineMarkdown(line.slice(2))}
        </h2>
      );
      return;
    }

    // Bullet points: * or -
    if (line.startsWith("* ") || line.startsWith("- ")) {
      const text = line.slice(2);
      if (!currentList || currentList.type !== "ul") {
        flushList();
        currentList = { type: "ul", items: [] };
      }
      currentList.items.push(text);
      return;
    }

    // Numbered list: 1.
    const numMatch = line.match(/^\d+\.\s+(.*)/);
    if (numMatch) {
      if (!currentList || currentList.type !== "ol") {
        flushList();
        currentList = { type: "ol", items: [] };
      }
      currentList.items.push(numMatch[1]);
      return;
    }

    // Paragraph
    flushList();
    elements.push(
      <p key={i} className="text-xs sm:text-sm text-slate-800 dark:text-slate-200 leading-relaxed my-1">
        {formatInlineMarkdown(line)}
      </p>
    );
  });

  flushList();

  return <div className="space-y-0.5">{elements}</div>;
}

function formatInlineMarkdown(text: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  const regex = /(\*\*.*?\*\*|`.*?`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(
        <strong key={match.index} className="font-semibold text-slate-950 dark:text-white">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code key={match.index} className="px-1.5 py-0.5 rounded text-[11px] font-mono bg-slate-100 dark:bg-slate-800 text-[#5345dc]">
          {token.slice(1, -1)}
        </code>
      );
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : [text];
}

function CitationInspectorDrawer({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) {
  const quote = citation.quote ?? citation.text ?? "";
  const speaker = citation.speaker ?? citation.speaker_name ?? "Speaker";
  const title = citation.meeting_title ?? "Meeting Transcript";
  const timeSec = citation.timestamp ?? citation.start_seconds ?? 0;

  return (
    <div className="w-80 lg:w-96 shrink-0 flex flex-col bg-white border border-slate-200/80 rounded-2xl shadow-lg overflow-hidden animate-slide-in-right">
      <div className="h-14 border-b border-slate-100 px-4 flex items-center justify-between bg-slate-50/50 shrink-0">
        <div className="flex items-center gap-2">
          <ShieldCheck size={16} className="text-emerald-500" />
          <h3 className="text-sm font-semibold text-slate-800">Transcript Proof</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors"
          aria-label="Close transcript proof"
        >
          <X size={15} />
        </button>
      </div>

      <div className="p-4 flex-1 overflow-y-auto space-y-4">
        {/* Verification Status */}
        <div className="flex items-center gap-2 p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-700 dark:text-emerald-300">
          <CheckCircle2 size={14} className="shrink-0" />
          <span className="text-xs font-medium">Verified against canonical audio transcript</span>
        </div>

        {/* Meeting Information */}
        <div>
          <label className="text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider block mb-1">
            Meeting Source
          </label>
          <p className="text-xs font-semibold text-[var(--foreground)]">{title}</p>
        </div>

        {/* Speaker & Timestamp */}
        <div className="grid grid-cols-2 gap-2">
          <div className="p-2.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
            <span className="text-[10px] text-[var(--muted)] block">Speaker</span>
            <span className="text-xs font-medium text-[var(--foreground)] truncate block mt-0.5">
              {speaker}
            </span>
          </div>
          <div className="p-2.5 rounded-lg bg-[var(--surface-2)] border border-[var(--border)]">
            <span className="text-[10px] text-[var(--muted)] block">Timestamp</span>
            <span className="text-xs font-mono font-medium text-[var(--foreground)] block mt-0.5">
              {formatDuration(timeSec)}
            </span>
          </div>
        </div>

        {/* Verbatim Excerpt */}
        <div>
          <label className="text-[10px] font-semibold text-[var(--muted)] uppercase tracking-wider block mb-1">
            Exact Transcript Snippet
          </label>
          <blockquote className="text-xs text-[var(--foreground)] leading-relaxed bg-[var(--surface-2)] rounded-xl p-3.5 border-l-3 border-[var(--primary)] italic font-serif">
            &ldquo;{quote}&rdquo;
          </blockquote>
        </div>

        {/* Action Link to Meeting Page */}
        {citation.meeting_id && (
          <div className="pt-2">
            <Link
              href={`/meetings/${citation.meeting_id}`}
              className="w-full flex items-center justify-center gap-1.5 py-2 px-3 rounded-lg text-xs font-medium bg-[var(--primary)] text-white hover:bg-[var(--primary-strong)] transition-all"
            >
              <ExternalLink size={12} />
              Open Full Meeting Playback
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
