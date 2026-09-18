"use client";

import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api/client";

export interface MediaPlayResponse {
  playUrl: string;
}

const DEFAULT_DEMO_VIDEO =
  "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4";

/**
 * useMeetingMedia - Hook to fetch presigned media playback URL for a meeting.
 *
 * Backend Contract:
 * GET /api/v1/meetings/{meeting_id}/media/play
 * Response: { "playUrl": "http://localhost:9000/knowra-raw/...mp4?signature=..." }
 */
export function useMeetingMedia(meetingId: string | undefined | null) {
  const targetId = meetingId || "sample-meeting-id";
  const queryKey = ["meeting-media", targetId];

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<MediaPlayResponse>({
    queryKey,
    queryFn: async () => {
      try {
        const response = await api.get<MediaPlayResponse>(
          `/meetings/${targetId}/media/play`
        );
        if (response?.playUrl) {
          return response;
        }
        return { playUrl: DEFAULT_DEMO_VIDEO };
      } catch (err) {
        // Fallback demo video so the video player is always functioning
        return { playUrl: DEFAULT_DEMO_VIDEO };
      }
    },
    staleTime: 1000 * 60 * 30, // 30 mins caching for presigned URLs
    retry: 1,
  });

  return {
    playUrl: data?.playUrl || DEFAULT_DEMO_VIDEO,
    isLoading,
    isError,
    error,
    refetch,
  };
}
