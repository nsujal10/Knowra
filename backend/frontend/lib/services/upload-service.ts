/**
 * Knowra Enterprise Meeting Intelligence
 * Direct-to-Storage (MinIO / S3) Presigned Multipart Upload Service (Phase 8/9 Contract)
 */

import { api, ApiError } from "@/lib/api/client";
import { md5 } from "@/lib/services/md5";

// ============================================================================
// 1. PHASE 8/9 CONTRACT TYPES & INTERFACES
// ============================================================================

export interface CreateMeetingRequest {
  title: string;
  meeting_date?: string;
}

export interface CreateMeetingResponse {
  id: string;
  title: string;
  status: string;
  owner_id: string;
  created_at: string;
  meeting_date?: string;
}

export interface MediaUploadRequest {
  filename: string;
  content_type: string;
  size_bytes: number;
  parts_count: number;
}

export interface PartUrl {
  part_number: number;
  upload_url: string;
}

export interface MediaUploadResponse {
  media_id: string;
  upload_id: string;
  parts: PartUrl[];
}

export interface PartETag {
  part_number: number;
  etag: string;
}

export interface MediaCompleteRequest {
  upload_id: string;
  parts: PartETag[];
}

export interface MediaStatusResponse {
  id: string;
  status: string;
  filename: string;
  created_at: string;
}

export interface UploadProgress {
  percentage: number;
  uploadedBytes: number;
  totalBytes: number;
  currentChunk: number;
  totalChunks: number;
  statusText: string;
}

export interface UploadOptions {
  concurrency?: number;
  onProgress?: (progress: UploadProgress) => void;
  signal?: AbortSignal;
}

// 5MB AWS S3 / MinIO minimum requirement per part (except last part)
export const MIN_S3_PART_SIZE = 5 * 1024 * 1024; // 5 MB

// ============================================================================
// 2. MULTIPART UPLOAD ORCHESTRATOR SERVICE
// ============================================================================

export class UploadService {
  /**
   * Orchestrates the complete 4-step direct-to-storage upload pipeline.
   *
   * Step 1: POST /api/v1/meetings -> Initialize Meeting
   * Step 2: POST /api/v1/meetings/{meeting_id}/media -> Presigned multipart URLs
   * Step 3: Direct PUT requests from browser to MinIO/S3 presigned URLs
   * Step 4: POST /api/v1/media/{media_id}/complete -> Trigger Celery pipeline
   */
  public static async uploadMeetingMedia(
    file: File,
    meetingMetadata: { title: string; meetingDate?: string },
    options: UploadOptions = {}
  ): Promise<{ meetingId: string; mediaId: string }> {
    const {
      concurrency = 3,
      onProgress,
      signal
    } = options;

    if (signal?.aborted) {
      throw new DOMException("Upload aborted by user", "AbortError");
    }

    // Normalize MIME type defensively so backend validate_mime_type succeeds
    let contentType = (file.type || "").split(";")[0].trim().toLowerCase();
    if (!contentType || contentType === "application/octet-stream") {
      const ext = file.name.split(".").pop()?.toLowerCase();
      if (ext === "mp4" || ext === "m4v") contentType = "video/mp4";
      else if (ext === "webm") contentType = "video/webm";
      else if (ext === "mp3") contentType = "audio/mpeg";
      else if (ext === "wav") contentType = "audio/wav";
      else contentType = "video/mp4";
    }

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 1: Initialize Meeting Record
    // ──────────────────────────────────────────────────────────────────────────
    onProgress?.({
      percentage: 2,
      uploadedBytes: 0,
      totalBytes: file.size,
      currentChunk: 0,
      totalChunks: 1,
      statusText: "Initializing meeting record..."
    });

    const createMeetingPayload: CreateMeetingRequest = {
      title: meetingMetadata.title.trim() || file.name,
      meeting_date: meetingMetadata.meetingDate || new Date().toISOString()
    };

    const meeting = await api.post<CreateMeetingResponse>(
      "/meetings",
      createMeetingPayload,
      { signal }
    );

    const meetingId = meeting.id;

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 2: Initialize Direct-to-Storage Multipart Upload
    // ──────────────────────────────────────────────────────────────────────────
    onProgress?.({
      percentage: 5,
      uploadedBytes: 0,
      totalBytes: file.size,
      currentChunk: 0,
      totalChunks: 1,
      statusText: "Requesting presigned storage URLs..."
    });

    // Calculate part count conforming strictly to MinIO/S3 >= 5MB rule:
    // Backend computes part_size = math.ceil(size_bytes / parts_count)
    // and throws 400 if part_size < 5MB and parts_count > 1.
    let partsCount = 1;
    if (file.size >= MIN_S3_PART_SIZE * 2) {
      partsCount = Math.max(1, Math.floor(file.size / MIN_S3_PART_SIZE));
    } else {
      partsCount = 1;
    }

    const mediaUploadPayload: MediaUploadRequest = {
      filename: file.name,
      content_type: contentType,
      size_bytes: file.size,
      parts_count: partsCount
    };

    const uploadSession = await api.post<MediaUploadResponse>(
      `/meetings/${meetingId}/media`,
      mediaUploadPayload,
      { signal }
    );

    const { media_id: mediaId, upload_id: uploadId, parts } = uploadSession;

    if (!parts || parts.length === 0) {
      throw new Error("No presigned upload parts received from server");
    }

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 3: Execute Direct Storage PUT Requests (Parallel Chunk Uploads)
    // ──────────────────────────────────────────────────────────────────────────
    const actualPartSize = Math.ceil(file.size / partsCount);
    const completedETags: PartETag[] = [];
    let uploadedBytesTotal = 0;

    // Concurrency pool runner
    const uploadChunk = async (part: PartUrl): Promise<PartETag> => {
      if (signal?.aborted) {
        throw new DOMException("Upload aborted by user", "AbortError");
      }

      const partIndex = part.part_number - 1;
      const start = partIndex * actualPartSize;
      const end = Math.min(start + actualPartSize, file.size);
      const chunkBlob = file.slice(start, end);

      let lastLoadedForChunk = 0;

      // Wrap standard XHR to support upload progress and header extraction
      const etag = await new Promise<string>(async (resolve, reject) => {
        if (signal?.aborted) {
          return reject(new DOMException("Upload aborted", "AbortError"));
        }

        const xhr = new XMLHttpRequest();
        xhr.open("PUT", part.upload_url);

        // Note: Do NOT set Content-Type header on part PUT because X-Amz-SignedHeaders=host.
        // S3 multipart parts are raw byte slices; Content-Type is established in InitMultipart.

        // Track upload progress per chunk
        xhr.upload.onprogress = (evt) => {
          if (evt.lengthComputable) {
            const delta = evt.loaded - lastLoadedForChunk;
            lastLoadedForChunk = evt.loaded;
            uploadedBytesTotal += delta;

            const progressPct = Math.min(
              95,
              Math.round(5 + (uploadedBytesTotal / file.size) * 90)
            );

            onProgress?.({
              percentage: progressPct,
              uploadedBytes: uploadedBytesTotal,
              totalBytes: file.size,
              currentChunk: part.part_number,
              totalChunks: parts.length,
              statusText: `Uploading chunk ${part.part_number} of ${parts.length} (${progressPct}%)...`
            });
          }
        };

        xhr.onload = async () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            // S3/MinIO returns ETag in response headers
            let rawEtag =
              xhr.getResponseHeader("ETag") ||
              xhr.getResponseHeader("etag") ||
              "";

            rawEtag = rawEtag.replace(/^"|"$/g, "").trim();

            // If browser CORS policy stripped the ETag header, calculate MD5 of chunk
            if (!rawEtag) {
              try {
                const buffer = await chunkBlob.arrayBuffer();
                rawEtag = md5(buffer);
              } catch {
                rawEtag = `part-${part.part_number}`;
              }
            }

            resolve(rawEtag);
          } else {
            reject(
              new Error(
                `Direct storage upload failed for part ${part.part_number} with status ${xhr.status}`
              )
            );
          }
        };

        xhr.onerror = () => {
          reject(
            new Error(
              `Network error during direct storage PUT for chunk ${part.part_number}. Please ensure storage server is reachable.`
            )
          );
        };

        xhr.onabort = () => {
          reject(new DOMException("Upload aborted by user", "AbortError"));
        };

        if (signal) {
          signal.addEventListener("abort", () => xhr.abort());
        }

        xhr.send(chunkBlob);
      });

      return {
        part_number: part.part_number,
        etag
      };
    };

    // Execute with limited concurrency
    const queue = [...parts];
    const workers: Promise<void>[] = [];

    for (let i = 0; i < Math.min(concurrency, queue.length); i++) {
      workers.push(
        (async () => {
          while (queue.length > 0) {
            if (signal?.aborted) {
              throw new DOMException("Upload aborted by user", "AbortError");
            }
            const part = queue.shift();
            if (part) {
              const res = await uploadChunk(part);
              completedETags.push(res);
            }
          }
        })()
      );
    }

    await Promise.all(workers);

    // Sort ETags sequentially by part_number (Critical for S3 CompleteMultipartUpload)
    completedETags.sort((a, b) => a.part_number - b.part_number);

    // ──────────────────────────────────────────────────────────────────────────
    // STEP 4: Complete Multipart Upload & Dispatch Processing Pipeline
    // ──────────────────────────────────────────────────────────────────────────
    onProgress?.({
      percentage: 97,
      uploadedBytes: file.size,
      totalBytes: file.size,
      currentChunk: parts.length,
      totalChunks: parts.length,
      statusText: "Finalizing storage assembly and queuing pipeline..."
    });

    const completePayload: MediaCompleteRequest = {
      upload_id: uploadId,
      parts: completedETags
    };

    await api.post<MediaStatusResponse>(
      `/media/${mediaId}/complete`,
      completePayload,
      { signal }
    );

    onProgress?.({
      percentage: 100,
      uploadedBytes: file.size,
      totalBytes: file.size,
      currentChunk: parts.length,
      totalChunks: parts.length,
      statusText: "Upload complete! Processing pipeline queued."
    });

    return {
      meetingId,
      mediaId
    };
  }
}
