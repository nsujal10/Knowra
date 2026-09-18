"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";

// ============================================================================
// 1. DATA MODELS & STRICT BACKEND API CONTRACT (PHASES 11-13)
// ============================================================================

export interface Speaker {
  id: string;
  label: string;
  displayName: string | null;
}

export interface TranscriptSegment {
  id: string;
  start: number;
  end: number;
  speaker: Speaker;
  text: string;
}

export interface CanonicalTranscript {
  transcriptId: string | null;
  status: "READY" | "PROCESSING" | "FAILED" | "UNPROCESSED";
  segments: TranscriptSegment[];
}

export interface TranscribeResponse {
  status: string;
  run_id: string;
  job_id?: string;
  message?: string;
}

// ============================================================================
// 2. USE_REAL_TRANSCRIPT HOOK
// ============================================================================

export function useRealTranscript(meetingId: string) {
  const queryClient = useQueryClient();
  const queryKey = ["meeting-transcript", meetingId];

  // ── Query Logic: Fetch canonical transcript with dynamic 5s polling ────────
  const {
    data: transcript,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<CanonicalTranscript>({
    queryKey,
    queryFn: async () => {
      try {
        const response = await api.get<CanonicalTranscript>(
          `/meetings/${meetingId}/transcript`
        );
        return response;
      } catch (err) {
        // If 404 or not found, check if a transcription job is in progress
        if (err instanceof ApiError && err.status === 404) {
          try {
            const jobStatus = await api.get<{ status: string }>(
              `/meetings/${meetingId}/transcription`
            );
            if (
              jobStatus?.status === "PENDING" ||
              jobStatus?.status === "PROCESSING" ||
              jobStatus?.status === "IN_PROGRESS"
            ) {
              return {
                transcriptId: null,
                status: "PROCESSING",
                segments: [],
              };
            }
            if (jobStatus?.status === "FAILED") {
              return {
                transcriptId: null,
                status: "FAILED",
                segments: [],
              };
            }
          } catch {
            // No transcription job exists yet
          }

          return {
            transcriptId: null,
            status: "UNPROCESSED",
            segments: [],
          };
        }
        throw err;
      }
    },
    // Poll every 3000ms while status is PROCESSING
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      if (currentStatus === "PROCESSING") {
        return 3000;
      }
      return false;
    },
    enabled: Boolean(meetingId),
  });

  // ── Mutation Logic: Trigger real backend Celery transcription pipeline ─────
  const {
    mutate: generateTranscript,
    isPending: isGenerating,
    error: mutationError,
  } = useMutation({
    mutationFn: async () => {
      return await api.post<TranscribeResponse>(
        `/meetings/${meetingId}/transcribe`
      );
    },
    onMutate: async () => {
      // Cancel ongoing queries to avoid race conditions
      await queryClient.cancelQueries({ queryKey });

      // Optimistically transition state to PROCESSING immediately
      queryClient.setQueryData<CanonicalTranscript>(queryKey, {
        transcriptId: null,
        status: "PROCESSING",
        segments: [],
      });
    },
    onSuccess: (res) => {
      // Invalidate and immediately trigger polling
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (err) => {
      console.error("Failed to trigger transcription:", err);
      queryClient.setQueryData<CanonicalTranscript>(queryKey, {
        transcriptId: null,
        status: "FAILED",
        segments: [],
      });
    },
  });

  return {
    transcript: transcript ?? {
      transcriptId: null,
      status: "UNPROCESSED",
      segments: [],
    },
    status: transcript?.status ?? "UNPROCESSED",
    segments: transcript?.segments ?? [],
    isLoading,
    isGenerating,
    isError: isError || Boolean(mutationError),
    error: error || mutationError,
    generateTranscript,
    refetch,
  };
}
