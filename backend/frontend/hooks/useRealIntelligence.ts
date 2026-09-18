"use client";

import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";

// ============================================================================
// 1. DATA MODELS & STRICT BACKEND API CONTRACT (PHASES 15 & 16)
// ============================================================================

export interface EvidenceAnchor {
  timestampStart: number;
}

export interface ActionItem {
  id: string;
  owner: string;
  task: string;
  evidence: EvidenceAnchor[];
}

export interface Topic {
  id: string;
  title: string;
  description: string;
  evidence: EvidenceAnchor[];
}

export interface IntelligenceSummary {
  executive: string;
}

export interface MeetingIntelligence {
  meetingId: string;
  status: "READY" | "PROCESSING" | "FAILED";
  summary: IntelligenceSummary;
  actionItems: ActionItem[];
  topics: Topic[];
}

// ============================================================================
// 2. USE_REAL_INTELLIGENCE HOOK
// ============================================================================

export function useRealIntelligence(meetingId: string) {
  const queryKey = ["meeting-intelligence", meetingId];

  const {
    data: intelligence,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<MeetingIntelligence>({
    queryKey,
    queryFn: async () => {
      try {
        const response = await api.get<MeetingIntelligence>(
          `/meetings/${meetingId}/intelligence`
        );
        return response;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          // If not yet generated, represent as PROCESSING to poll or show loader
          return {
            meetingId,
            status: "PROCESSING",
            summary: { executive: "" },
            actionItems: [],
            topics: [],
          };
        }
        throw err;
      }
    },
    enabled: Boolean(meetingId) && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(meetingId),
    refetchInterval: (query) => {
      const current = query.state.data;
      // If the status is "PROCESSING", poll every 5s until "READY" or "FAILED"
      if (current?.status === "PROCESSING") {
        return 5000;
      }
      return false;
    },
    refetchIntervalInBackground: true,
  });

  return {
    intelligence,
    isLoading,
    isError,
    error,
    refetch,
    isProcessing: intelligence?.status === "PROCESSING" || (isLoading && !intelligence),
    isReady: intelligence?.status === "READY",
    isFailed: intelligence?.status === "FAILED",
  };
}
