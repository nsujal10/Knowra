"use client";

import React, { useState } from "react";
import { API_BASE } from "@/lib/api/client";

interface MeetingThumbnailProps {
  meetingId: string;
  title?: string;
  fallbackGradient?: string;
  className?: string;
}

/**
 * MeetingThumbnail - Displays the authentic video thumbnail extracted
 * directly from the meeting's video recording via FFmpeg on the backend.
 * Falls back gracefully to the themed gradient if the media stream is audio-only or pending.
 */
export function MeetingThumbnail({
  meetingId,
  title = "Meeting Video",
  fallbackGradient = "from-indigo-900 via-slate-900 to-stone-900",
  className = "",
}: MeetingThumbnailProps) {
  const [hasError, setHasError] = useState(false);
  const [isLoaded, setIsLoaded] = useState(false);

  const thumbnailUrl = `${API_BASE}/meetings/${meetingId}/thumbnail?v=2`;

  if (hasError) {
    return (
      <div
        className={`w-full h-full bg-gradient-to-br ${fallbackGradient} flex items-center justify-center ${className}`}
      >
        <span className="text-xl select-none filter drop-shadow">🎬</span>
      </div>
    );
  }

  return (
    <div className={`w-full h-full relative overflow-hidden bg-slate-950 ${className}`}>
      {/* Loading Skeleton */}
      {!isLoaded && (
        <div className="absolute inset-0 bg-slate-900 animate-pulse flex items-center justify-center">
          <div className="w-4 h-4 rounded-full border border-slate-700 border-t-indigo-500 animate-spin" />
        </div>
      )}

      {/* Real Video Frame Thumbnail */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={thumbnailUrl}
        alt={title}
        loading="lazy"
        onLoad={() => setIsLoaded(true)}
        onError={() => setHasError(true)}
        className={`w-full h-full object-cover transition-opacity duration-300 ${
          isLoaded ? "opacity-100" : "opacity-0"
        }`}
      />
    </div>
  );
}
