"use client";

import React, { useState } from "react";
import { X, Send, Sparkles, Bot, User, CornerDownLeft } from "lucide-react";

interface RagChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  meetingId: string;
  meetingTitle: string;
}

interface Message {
  id: string;
  sender: "user" | "knowra";
  text: string;
  citations?: string[];
}

export function RagChatDrawer({
  isOpen,
  onClose,
  meetingId,
  meetingTitle
}: RagChatDrawerProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "m-1",
      sender: "knowra",
      text: `Hello! I'm Knowra AI. I have indexed the entire audio, transcript, decisions, and action items for "${meetingTitle}". How can I assist you?`,
      citations: []
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);

  if (!isOpen) return null;

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg: Message = {
      id: `u-${Date.now()}`,
      sender: "user",
      text: input.trim()
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsTyping(true);

    // Simulate RAG response grounded in meeting context
    setTimeout(() => {
      let reply = "Based on the discussion, ";
      const lower = userMsg.text.toLowerCase();
      if (lower.includes("action") || lower.includes("task") || lower.includes("who")) {
        reply += "Kelcey Hawthorne was tasked with coordinating follow-up documentation on Search Copilot, while Alison Barker verified calendar auto-join policies.";
      } else if (lower.includes("crm") || lower.includes("hubspot") || lower.includes("salesforce")) {
        reply += "the team demonstrated that Search Copilot can connect to CRM systems like HubSpot or Salesforce to automatically push meeting notes and extract key objections.";
      } else if (lower.includes("summary") || lower.includes("about")) {
        reply += "the meeting covered Read AI's onboarding process, calendar integration, account permission boundaries, and Search Copilot cross-platform indexing.";
      } else {
        reply += `Search Copilot respects permissions and only surfaces meeting moments the user is authorized to view. Citations trace back to [0:00] and [6:03].`;
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `k-${Date.now()}`,
          sender: "knowra",
          text: reply,
          citations: ["0:00 Read AI Onboarding Essentials", "6:03 Exploring Search Copilot"]
        }
      ]);
      setIsTyping(false);
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-slate-900/30 backdrop-blur-2xs animate-in fade-in duration-200">
      <div
        className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between bg-slate-50/70">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shadow-xs">
              <Sparkles className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-900">Ask Knowra AI</h3>
              <p className="text-[11px] text-slate-500 truncate max-w-[260px]" title={meetingTitle}>
                Scoped to: {meetingTitle}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex items-start gap-2.5 ${msg.sender === "user" ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`w-7 h-7 rounded-full flex items-center justify-center text-xs shrink-0 ${
                  msg.sender === "user"
                    ? "bg-indigo-100 text-indigo-700 font-bold"
                    : "bg-indigo-600 text-white"
                }`}
              >
                {msg.sender === "user" ? <User className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
              </div>

              <div
                className={`max-w-[82%] rounded-xl p-3 text-xs leading-relaxed ${
                  msg.sender === "user"
                    ? "bg-indigo-600 text-white font-normal shadow-xs"
                    : "bg-slate-100 text-slate-800 border border-slate-200/80"
                }`}
              >
                <p>{msg.text}</p>
                {msg.citations && msg.citations.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-slate-200/60 flex flex-wrap gap-1">
                    {msg.citations.map((c, i) => (
                      <span
                        key={i}
                        className="text-[10px] bg-white text-indigo-600 px-1.5 py-0.5 rounded border border-indigo-200/70 font-mono"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {isTyping && (
            <div className="flex items-center gap-2 text-xs text-slate-400 pl-9">
              <span className="animate-pulse font-medium">Knowra is searching meeting context...</span>
            </div>
          )}
        </div>

        {/* Input Bar */}
        <div className="p-3 border-t border-slate-200 bg-white">
          <div className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSend();
              }}
              placeholder="Ask anything about this meeting..."
              className="w-full pl-3 pr-10 py-2.5 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder:text-slate-400 focus:outline-none focus:bg-white focus:ring-1 focus:ring-indigo-500"
            />
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim()}
              className="absolute right-1.5 p-1.5 rounded-md bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white transition-colors cursor-pointer"
            >
              <CornerDownLeft className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
