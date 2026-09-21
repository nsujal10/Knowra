"use client";

import React from "react";
import { AskKnowraPanel } from "./AskKnowraPanel";

interface RagChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  meetingId: string;
  meetingTitle: string;
  onSeek?: (seconds: number) => void;
}

export function RagChatDrawer({
  isOpen,
  onClose,
  meetingId,
  meetingTitle,
  onSeek,
}: RagChatDrawerProps) {
  return (
    <div
      className={`fixed inset-0 z-50 flex justify-end transition-opacity duration-300 ${
        isOpen
          ? "bg-slate-900/30 backdrop-blur-2xs opacity-100 pointer-events-auto"
          : "bg-transparent opacity-0 pointer-events-none"
      }`}
      onClick={onClose}
    >
      <div
        className={`w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 overflow-hidden transition-transform duration-300 ease-in-out transform ${
          isOpen ? "translate-x-0" : "translate-x-full"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <AskKnowraPanel
          meetingId={meetingId}
          meetingTitle={meetingTitle}
          onClose={onClose}
          onSeek={onSeek}
        />
      </div>
    </div>
  );
}
