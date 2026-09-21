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
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-slate-900/30 backdrop-blur-2xs animate-in fade-in duration-200"
      onClick={onClose}
    >
      <div
        className="w-full max-w-md bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-300 overflow-hidden"
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
