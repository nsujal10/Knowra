"use client";

import React, { useRef, useEffect } from "react";
import { X, Sparkles, Bot, User, CornerDownLeft, Clock, RotateCcw } from "lucide-react";
import { useMeetingChat, Citation } from "@/hooks/useMeetingChat";

export interface AskKnowraPanelProps {
  meetingId: string;
  meetingTitle: string;
  onClose?: () => void;
  onSeek?: (seconds: number) => void;
}

const SUGGESTIONS = [
  "Key decisions",
  "Action items",
  "Was pricing discussed?",
  "Search Copilot overview",
];

export function AskKnowraPanel({
  meetingId,
  meetingTitle,
  onClose,
  onSeek,
}: AskKnowraPanelProps) {
  const { messages, input, setInput, sendMessage, clearHistory, isTyping } = useMeetingChat({
    meetingId,
    meetingTitle,
  });

  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  // Auto-scroll to bottom on new messages or typing state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full w-full bg-white select-none">
      {/* ── 1. HEADER ──────────────────────────────────────────────────────── */}
      <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/80 shrink-0">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-xs shrink-0">
            <Sparkles className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-bold text-slate-900 leading-snug">Ask Knowra AI</h3>
            <p
              className="text-[11px] text-slate-500 truncate max-w-[260px]"
              title={meetingTitle}
            >
              Scoped to: {meetingTitle}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            type="button"
            onClick={clearHistory}
            className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
            title="Reset Chat History"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors cursor-pointer"
              title="Close Assistant"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>

      {/* ── 2. MESSAGE HISTORY ─────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((msg, idx) => (
          <div
            key={msg.id || idx}
            className={`flex items-start gap-2.5 w-full ${
              msg.role === "user" ? "flex-row-reverse" : "flex-row"
            }`}
          >
            {/* Avatar */}
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 shadow-xs ${
                msg.role === "user"
                  ? "bg-indigo-50 border border-indigo-200 text-indigo-600 font-semibold"
                  : "bg-indigo-600 text-white"
              }`}
            >
              {msg.role === "user" ? (
                <User className="w-3.5 h-3.5" />
              ) : (
                <Bot className="w-3.5 h-3.5" />
              )}
            </div>

            {/* Bubble & Citations Wrapper */}
            <div
              className={`max-w-[82%] flex flex-col gap-1.5 ${
                msg.role === "user" ? "items-end" : "items-start"
              }`}
            >
              {/* Message Bubble */}
              <div
                className={`text-[13px] leading-relaxed break-words shadow-2xs select-text ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-xs min-w-[54px] text-left border border-indigo-500/80 shadow-xs"
                    : "bg-slate-50 border border-slate-200/90 px-4 py-3 rounded-2xl rounded-tl-xs text-left"
                }`}
              >
                <div
                  className="whitespace-pre-wrap select-text leading-relaxed font-normal"
                  style={{
                    color: msg.role === "user" ? "#ffffff" : "#0f172a",
                  }}
                >
                  {msg.content}
                </div>
              </div>

              {/* Interactive Citation Pills Container (Assistant only) */}
              {msg.role === "assistant" && msg.citations && msg.citations.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-0.5">
                  {msg.citations.map((citation: Citation, cIdx: number) => (
                    <button
                      key={cIdx}
                      type="button"
                      onClick={() => onSeek?.(citation.timestamp_seconds)}
                      className="border border-indigo-200/90 bg-white hover:bg-indigo-50/80 text-indigo-700 text-xs px-2.5 py-1 rounded-md flex items-center gap-1.5 cursor-pointer font-mono font-medium shadow-2xs transition-all active:scale-95"
                      title={`Jump to ${citation.label} in video`}
                    >
                      <Clock className="w-3 h-3 text-indigo-500 shrink-0" />
                      <span>{citation.label}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Loading Indicator */}
        {isTyping && (
          <div className="flex items-start gap-2.5 w-full">
            <div className="w-7 h-7 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs shrink-0 shadow-xs">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-slate-50 border border-slate-200/80 rounded-2xl rounded-tl-xs px-4 py-2.5 text-xs text-slate-600 flex items-center gap-2 shadow-2xs">
              <div className="w-3.5 h-3.5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin shrink-0" />
              <span className="font-medium animate-pulse">Knowra is searching meeting context...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── 3. SUGGESTIONS & INPUT FOOTER ───────────────────────────────────── */}
      <div className="border-t border-slate-200 bg-white shrink-0">
        {/* Quick prompt suggestions */}
        <div className="px-3 pt-2.5 pb-1.5 flex items-center gap-1.5 overflow-x-auto no-scrollbar">
          {SUGGESTIONS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              disabled={isTyping}
              onClick={() => sendMessage(prompt)}
              className="shrink-0 text-[11px] px-2.5 py-1 rounded-full bg-slate-100 hover:bg-indigo-50 text-slate-600 hover:text-indigo-600 border border-slate-200/80 hover:border-indigo-200 transition-colors cursor-pointer disabled:opacity-50"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input box */}
        <div className="p-3 pt-1">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isTyping}
              placeholder="Ask anything about this meeting..."
              className="w-full pl-3.5 pr-10 py-2.5 text-xs sm:text-[13px] bg-slate-50 border border-slate-200 rounded-lg text-slate-900 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors disabled:opacity-60"
            />
            <button
              type="button"
              onClick={() => sendMessage()}
              disabled={!input.trim() || isTyping}
              className="absolute right-1.5 p-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white transition-colors cursor-pointer shadow-xs"
              title="Send Message"
            >
              <CornerDownLeft className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
