"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";

// ============================================================================
// 1. STRICT BACKEND API CONTRACT (PHASE 15 & 16 MAPPING)
// ============================================================================

export interface EvidenceAnchor {
  timestampStart: number;
}

export interface IntelligenceActionItem {
  id: string;
  owner: string;
  task: string;
  evidence: EvidenceAnchor[];
}

export interface IntelligenceTopic {
  id: string;
  title: string;
  description: string;
  evidence: EvidenceAnchor[];
}

export interface IntelligenceSummary {
  executive: string;
}

export interface IntelligenceResponse {
  meetingId: string;
  status: "READY" | "PROCESSING" | "FAILED" | "UNPROCESSED";
  summary: IntelligenceSummary;
  actionItems: IntelligenceActionItem[];
  topics: IntelligenceTopic[];
}

// ============================================================================
// 2. USE_MEETING_INTELLIGENCE HOOK
// ============================================================================

export function useMeetingIntelligence(propMeetingId?: string) {
  const params = useParams();
  const routeMeetingId = typeof params?.id === "string" ? params.id : "";
  const meetingId = propMeetingId || routeMeetingId;

  const queryKey = ["meeting-intelligence", meetingId];

  const query = useQuery<IntelligenceResponse>({
    queryKey,
    queryFn: async () => {
      if (!meetingId) {
        throw new Error("Meeting ID is required to fetch intelligence.");
      }

      try {
        const response = await api.get<IntelligenceResponse>(
          `/meetings/${meetingId}/intelligence`
        );
        return response;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          // If the backend has not generated intelligence yet, return UNPROCESSED status
          return {
            meetingId,
            status: "UNPROCESSED",
            summary: { executive: "" },
            actionItems: [],
            topics: [],
          };
        }
        throw err;
      }
    },
    enabled: Boolean(meetingId),
    refetchInterval: (queryState) => {
      const data = queryState.state.data;
      // If the backend is currently generating intelligence in Celery, poll every 4s
      if (data?.status === "PROCESSING") {
        return 4000;
      }
      return false;
    },
    refetchIntervalInBackground: true,
  });

  const { data, isLoading, isError, error, refetch } = query;

  return {
    data,
    isLoading: isLoading && !data,
    isError,
    error,
    refetch,
    isProcessing: data?.status === "PROCESSING" || (isLoading && !data),
    isReady: data?.status === "READY",
    isFailed: data?.status === "FAILED",
    isUnprocessed: data?.status === "UNPROCESSED",
  };
}
