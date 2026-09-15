"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, apiStream } from "@/lib/api/client";
import { CHAT } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { type ChatSession, type ChatMessage, type Citation } from "@/lib/types";
import { Card, CardContent, Spinner } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import { cn, relativeTime, truncate } from "@/lib/utils";
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
} from "lucide-react";
import Link from "next/link";

export default function ChatPage() {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [streamingContent, setStreamingContent] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [openCitation, setOpenCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const qc = useQueryClient();

  // Sessions list
  const { data: sessions, isLoading: sessionsLoading } = useQuery({
    queryKey: queryKeys.chat.sessions(),
    queryFn: () => api.get<ChatSession[]>(CHAT.sessions()),
    initialData: [],
  });

  // Messages for active session
  const { data: messages = [] } = useQuery({
    queryKey: queryKeys.chat.messages(activeSessionId ?? ""),
    queryFn: () =>
      api.get<ChatMessage[]>(CHAT.messages(activeSessionId!)),
    enabled: !!activeSessionId,
  });

  // Create session
  const createSession = useMutation({
    mutationFn: () => api.post<ChatSession>(CHAT.sessions(), { title: "New Chat" }),
    onSuccess: (session) => {
      qc.invalidateQueries({ queryKey: queryKeys.chat.sessions() });
      setActiveSessionId(session.id);
    },
  });

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      const session = await createSession.mutateAsync();
      sessionId = session.id;
    }

    const userMessage = input.trim();
    setInput("");
    setIsStreaming(true);
    setStreamingContent("");

    // Optimistically add user message to cache
    qc.setQueryData<ChatMessage[]>(
      queryKeys.chat.messages(sessionId),
      (prev = []) => [
        ...prev,
        {
          id: `tmp-${Date.now()}`,
          role: "user",
          content: userMessage,
          created_at: new Date().toISOString(),
        },
      ]
    );

    try {
      let fullContent = "";
      for await (const chunk of apiStream(CHAT.stream(sessionId), {
        content: userMessage,
      })) {
        try {
          const parsed = JSON.parse(chunk);
          if (parsed.delta) {
            fullContent += parsed.delta;
            setStreamingContent(fullContent);
          }
        } catch {
          // plain text chunk
          fullContent += chunk;
          setStreamingContent(fullContent);
        }
      }
    } catch {
      // Fallback to non-streaming query
      try {
        const res = await api.post<{ answer: string; citations: Citation[] }>(
          CHAT.query(),
          { session_id: sessionId, content: userMessage }
        );
        setStreamingContent(res.answer);
      } catch {
        setStreamingContent("I encountered an error processing your request.");
      }
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
      qc.invalidateQueries({ queryKey: queryKeys.chat.messages(sessionId!) });
    }
  }, [input, activeSessionId, isStreaming, qc, createSession]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex gap-4 h-[calc(100vh-56px-48px)] animate-fade-in">
      {/* Sessions Sidebar */}
      <div className="w-56 shrink-0 flex flex-col gap-2">
        <Button
          variant="primary"
          size="sm"
          className="w-full"
          onClick={() => createSession.mutate()}
          isLoading={createSession.isPending}
          id="new-chat-btn"
        >
          <Plus size={14} />
          New Chat
        </Button>
        <div className="flex-1 overflow-y-auto space-y-0.5">
          {sessionsLoading ? (
            <div className="flex justify-center py-4">
              <Spinner size={16} />
            </div>
          ) : sessions.length === 0 ? (
            <p className="text-xs text-[var(--muted)] text-center py-4 px-2">
              Start a conversation with your meeting data
            </p>
          ) : (
            sessions.map((session) => (
              <button
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={cn(
                  "w-full text-left px-3 py-2.5 rounded-[var(--radius-sm)] text-xs transition-all",
                  activeSessionId === session.id
                    ? "bg-[var(--primary-muted)] text-[var(--primary)]"
                    : "text-[var(--muted-strong)] hover:bg-[var(--surface-2)]"
                )}
              >
                <p className="font-medium truncate">{session.title ?? "Chat"}</p>
                <p className="text-[10px] text-[var(--muted)] mt-0.5">
                  {relativeTime(session.updated_at)}
                </p>
              </button>
            ))
          )}
        </div>
      </div>

      {/* Chat Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <Card className="flex-1 flex flex-col overflow-hidden p-0">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-5 space-y-5">
            {!activeSessionId ? (
              <WelcomeScreen onNewChat={() => createSession.mutate()} />
            ) : messages.length === 0 && !isStreaming ? (
              <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
                <MessageSquare size={32} className="text-[var(--muted)]" />
                <p className="text-sm text-[var(--muted)]">
                  Ask anything about your meetings…
                </p>
              </div>
            ) : (
              <>
                {messages.map((msg) => (
                  <ChatBubble
                    key={msg.id}
                    message={msg}
                    onCitationClick={setOpenCitation}
                  />
                ))}
                {isStreaming && streamingContent && (
                  <StreamingBubble content={streamingContent} />
                )}
                {isStreaming && !streamingContent && (
                  <div className="flex gap-2.5">
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center shrink-0">
                      <Bot size={14} className="text-white" />
                    </div>
                    <div className="flex items-center gap-1 py-2">
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                      <span className="typing-dot" />
                    </div>
                  </div>
                )}
              </>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-[var(--border)] p-4">
            <div className="flex gap-2 items-end">
              <textarea
                id="chat-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about meetings, decisions, action items… (Enter to send)"
                rows={1}
                disabled={isStreaming}
                className={cn(
                  "flex-1 resize-none bg-[var(--surface-2)] border border-[var(--border)]",
                  "rounded-[var(--radius-sm)] px-3 py-2.5 text-sm text-[var(--foreground)]",
                  "placeholder:text-[var(--muted)] focus:outline-none focus:border-[var(--primary)]",
                  "transition-colors max-h-32 overflow-y-auto",
                  isStreaming && "opacity-60 cursor-not-allowed"
                )}
                style={{ lineHeight: "1.5" }}
              />
              <Button
                variant="primary"
                size="icon"
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                id="chat-send-btn"
                aria-label="Send message"
              >
                <Send size={15} />
              </Button>
            </div>
            <p className="text-[10px] text-[var(--muted)] mt-2 text-center">
              Answers are grounded in your meeting transcripts with verified citations.
            </p>
          </div>
        </Card>
      </div>

      {/* Citation Drawer */}
      {openCitation && (
        <CitationDrawer
          citation={openCitation}
          onClose={() => setOpenCitation(null)}
        />
      )}
    </div>
  );
}

// ─── Sub-components ────────────────────────────────────────────────────────────

function WelcomeScreen({ onNewChat }: { onNewChat: () => void }) {
  const suggestions = [
    "What decisions were made in last week's meetings?",
    "What action items are assigned to the product team?",
    "Summarize the key topics from Q3 planning sessions.",
    "Which meetings discussed the mobile app launch?",
  ];
  return (
    <div className="flex flex-col items-center justify-center h-full gap-6 text-center px-4">
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center shadow-[var(--shadow-glow)]">
        <Bot size={24} className="text-white" />
      </div>
      <div>
        <h3 className="text-lg font-semibold text-[var(--foreground)]">Knowra AI Chat</h3>
        <p className="text-sm text-[var(--muted)] mt-1 max-w-sm">
          Ask questions across all your meetings. Every answer is grounded in your transcripts with verifiable citations.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {suggestions.map((s, i) => (
          <button
            key={i}
            onClick={onNewChat}
            className="text-left text-xs p-3 rounded-[var(--radius-sm)] bg-[var(--surface-2)] border border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--primary)] hover:text-[var(--foreground)] transition-all"
          >
            &ldquo;{s}&rdquo;
          </button>
        ))}
      </div>
    </div>
  );
}

function ChatBubble({
  message,
  onCitationClick,
}: {
  message: ChatMessage;
  onCitationClick: (c: Citation) => void;
}) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-2.5", isUser && "flex-row-reverse")}>
      <div
        className={cn(
          "w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-0.5",
          isUser
            ? "bg-[var(--surface-3)] text-[var(--muted-strong)]"
            : "bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] text-white"
        )}
      >
        {isUser ? <User size={14} /> : <Bot size={14} />}
      </div>
      <div className={cn("max-w-[75%] space-y-2", isUser && "items-end")}>
        <div
          className={cn(
            "rounded-[var(--radius-md)] px-4 py-3 text-sm leading-relaxed",
            isUser
              ? "bg-[var(--primary)] text-white rounded-tr-[4px]"
              : "bg-[var(--surface-2)] text-[var(--foreground)] border border-[var(--border)] rounded-tl-[4px]"
          )}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.citations && message.citations.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {message.citations.map((c, i) => (
              <button
                key={c.chunk_id ?? i}
                onClick={() => onCitationClick(c)}
                className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded-full bg-[var(--surface-2)] border border-[var(--border)] text-[var(--muted-strong)] hover:border-[var(--primary)] hover:text-[var(--primary)] transition-all"
              >
                <FileText size={9} />
                {truncate(c.meeting_title ?? c.meeting_id, 22)}
                <ChevronRight size={8} />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StreamingBubble({ content }: { content: string }) {
  return (
    <div className="flex gap-2.5">
      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center shrink-0 mt-0.5">
        <Bot size={14} className="text-white" />
      </div>
      <div className="max-w-[75%]">
        <div className="bg-[var(--surface-2)] border border-[var(--border)] rounded-[var(--radius-md)] rounded-tl-[4px] px-4 py-3 text-sm leading-relaxed text-[var(--foreground)]">
          <p className="whitespace-pre-wrap">{content}</p>
          <span className="inline-block w-0.5 h-4 bg-[var(--primary)] ml-0.5 animate-pulse align-middle" />
        </div>
      </div>
    </div>
  );
}

function CitationDrawer({
  citation,
  onClose,
}: {
  citation: Citation;
  onClose: () => void;
}) {
  return (
    <div className="w-72 shrink-0 animate-slide-in-right">
      <Card className="h-full flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-[var(--foreground)] flex items-center gap-2">
            <FileText size={14} className="text-[var(--primary)]" />
            Source
          </h3>
          <button
            onClick={onClose}
            className="p-1 rounded text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
            aria-label="Close citation"
          >
            <X size={14} />
          </button>
        </div>
        <div className="space-y-4 flex-1 overflow-y-auto">
          <div>
            <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Meeting</p>
            <p className="text-sm text-[var(--foreground)] font-medium">
              {citation.meeting_title ?? citation.meeting_id}
            </p>
          </div>
          {citation.speaker && (
            <div>
              <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Speaker</p>
              <p className="text-sm text-[var(--foreground)]">{citation.speaker}</p>
            </div>
          )}
          {citation.timestamp !== undefined && (
            <div>
              <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Timestamp</p>
              <p className="text-sm text-[var(--foreground)] font-mono">
                {Math.floor(citation.timestamp / 60)}:
                {String(Math.floor(citation.timestamp % 60)).padStart(2, "0")}
              </p>
            </div>
          )}
          <div>
            <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Excerpt</p>
            <blockquote className="text-sm text-[var(--muted-strong)] leading-relaxed bg-[var(--surface-2)] rounded-[var(--radius-sm)] p-3 border-l-2 border-[var(--primary)] italic">
              &ldquo;{citation.text}&rdquo;
            </blockquote>
          </div>
          {citation.relevance_score !== undefined && (
            <div>
              <p className="text-[10px] text-[var(--muted)] uppercase tracking-wider mb-1">Relevance</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 h-1 rounded-full bg-[var(--surface-3)]">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-[var(--primary)] to-[var(--secondary)]"
                    style={{ width: `${citation.relevance_score * 100}%` }}
                  />
                </div>
                <span className="text-xs text-[var(--muted-strong)] font-mono">
                  {(citation.relevance_score * 100).toFixed(0)}%
                </span>
              </div>
            </div>
          )}
          <Link
            href={`/meetings/${citation.meeting_id}`}
            className="flex items-center gap-1.5 text-xs text-[var(--primary)] hover:underline mt-2"
          >
            <ExternalLink size={11} />
            View meeting transcript
          </Link>
        </div>
      </Card>
    </div>
  );
}
