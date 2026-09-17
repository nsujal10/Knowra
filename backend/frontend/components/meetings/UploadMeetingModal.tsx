"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import {
  UploadCloud,
  X,
  FileVideo,
  FileAudio,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Calendar,
  FileText,
  RotateCcw
} from "lucide-react";
import { UploadService, UploadProgress } from "@/lib/services/upload-service";

// ============================================================================
// COMPONENT PROPS
// ============================================================================

export interface UploadMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadComplete?: (meetingId: string) => void;
}

type ModalStep = "SELECT" | "DETAILS" | "UPLOADING" | "SUCCESS" | "ERROR";

// Helper to format byte sizes cleanly
function formatBytes(bytes: number, decimals: number = 1): string {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

export function UploadMeetingModal({
  isOpen,
  onClose,
  onUploadComplete
}: UploadMeetingModalProps) {
  const [step, setStep] = useState<ModalStep>("SELECT");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [createdMeetingId, setCreatedMeetingId] = useState<string | null>(null);

  const [progress, setProgress] = useState<UploadProgress>({
    percentage: 0,
    uploadedBytes: 0,
    totalBytes: 0,
    currentChunk: 0,
    totalChunks: 0,
    statusText: ""
  });

  const abortControllerRef = useRef<AbortController | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Initialize today's date in YYYY-MM-DD
  useEffect(() => {
    if (isOpen) {
      const today = new Date().toISOString().split("T")[0];
      setMeetingDate(today);
    }
  }, [isOpen]);

  // Reset state when opening/closing
  const resetForm = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setStep("SELECT");
    setFile(null);
    setTitle("");
    setErrorMessage("");
    setCreatedMeetingId(null);
    setProgress({
      percentage: 0,
      uploadedBytes: 0,
      totalBytes: 0,
      currentChunk: 0,
      totalChunks: 0,
      statusText: ""
    });
  }, []);

  const handleClose = () => {
    if (step === "UPLOADING") {
      const confirmAbort = window.confirm(
        "An upload is currently in progress. Are you sure you want to cancel?"
      );
      if (!confirmAbort) return;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    }
    resetForm();
    onClose();
  };

  // Keyboard shortcut: ESC to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, step]);

  // Handle file selection
  const processSelectedFile = (selectedFile: File) => {
    // Derive meeting title by removing extension
    const cleanTitle = selectedFile.name.replace(/\.[^/.]+$/, "");
    setFile(selectedFile);
    setTitle(cleanTitle);
    setStep("DETAILS");
    setErrorMessage("");
  };

  const onFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processSelectedFile(e.target.files[0]);
    }
  };

  // Drag and drop handlers
  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processSelectedFile(e.dataTransfer.files[0]);
    }
  };

  // Start multipart upload orchestration
  const handleStartUpload = async () => {
    if (!file) return;

    setStep("UPLOADING");
    setErrorMessage("");
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const result = await UploadService.uploadMeetingMedia(
        file,
        {
          title: title.trim() || file.name,
          meetingDate: meetingDate || undefined
        },
        {
          signal: controller.signal,
          onProgress: (prog) => {
            setProgress(prog);
          }
        }
      );

      setCreatedMeetingId(result.meetingId);
      setStep("SUCCESS");
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === "AbortError") {
        setStep("SELECT");
        return;
      }
      setErrorMessage(
        err instanceof Error
          ? err.message
          : "Failed to complete media upload. Please check network connection."
      );
      setStep("ERROR");
    } finally {
      abortControllerRef.current = null;
    }
  };

  const handleDone = () => {
    if (createdMeetingId && onUploadComplete) {
      onUploadComplete(createdMeetingId);
    }
    handleClose();
  };

  if (!isOpen) return null;

  const isVideo = file?.type.startsWith("video/") || file?.name.match(/\.(mp4|mov|mkv|webm)$/i);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/45 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="w-full max-w-xl bg-white rounded-xl shadow-xl border border-slate-200 overflow-hidden flex flex-col transition-all"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-white">
          <div>
            <h2 id="upload-modal-title" className="text-base font-semibold text-slate-900">
              Upload Meeting Recording
            </h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Direct-to-storage presigned upload with automatic AI speech processing
            </p>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="text-slate-400 hover:text-slate-700 p-1.5 rounded-md hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6">
          {/* =============================================================== */}
          {/* STEP 1: FILE SELECTION / DROPZONE                               */}
          {/* =============================================================== */}
          {step === "SELECT" && (
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-150 ${
                isDragging
                  ? "border-indigo-500 bg-indigo-50/50"
                  : "border-slate-300 bg-slate-50 hover:bg-slate-100/70 hover:border-indigo-400"
              }`}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="video/*,audio/*,.mp4,.mov,.mkv,.webm,.mp3,.wav,.m4a"
                onChange={onFileInputChange}
                className="hidden"
              />

              <div className="w-12 h-12 rounded-full bg-indigo-50 text-indigo-600 flex items-center justify-center mb-3">
                <UploadCloud className="w-6 h-6" />
              </div>

              <p className="text-sm font-semibold text-slate-800">
                Drag and drop your recording here, or{" "}
                <span className="text-indigo-600 underline">browse</span>
              </p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                Supported formats: MP4, MOV, MKV, WEBM, MP3, WAV, M4A (Up to 2GB)
              </p>
            </div>
          )}

          {/* =============================================================== */}
          {/* STEP 2: MEETING DETAILS FORM                                    */}
          {/* =============================================================== */}
          {step === "DETAILS" && file && (
            <div className="space-y-5">
              {/* Selected File Card */}
              <div className="flex items-center justify-between p-3.5 bg-slate-50 rounded-lg border border-slate-200">
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-md bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
                    {isVideo ? (
                      <FileVideo className="w-5 h-5" />
                    ) : (
                      <FileAudio className="w-5 h-5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p className="text-xs font-semibold text-slate-900 truncate" title={file.name}>
                      {file.name}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">
                      {formatBytes(file.size)} • {file.type || "media"}
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setStep("SELECT")}
                  className="text-xs font-medium text-slate-500 hover:text-slate-800 hover:underline ml-3 shrink-0"
                >
                  Change
                </button>
              </div>

              {/* Title Field */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Meeting Title
                </label>
                <div className="relative">
                  <FileText className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Enter meeting title..."
                    className="w-full text-sm pl-9 pr-3 py-2 border border-slate-200 rounded-lg bg-white shadow-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Date Field */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1.5">
                  Meeting Date
                </label>
                <div className="relative">
                  <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="date"
                    value={meetingDate}
                    onChange={(e) => setMeetingDate(e.target.value)}
                    className="w-full text-sm pl-9 pr-3 py-2 border border-slate-200 rounded-lg bg-white shadow-xs focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleStartUpload}
                  className="px-5 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors flex items-center gap-2"
                >
                  <span>Start Upload</span>
                </button>
              </div>
            </div>
          )}

          {/* =============================================================== */}
          {/* STEP 3: UPLOAD PROGRESS (Direct-to-Storage Presigned PUTs)       */}
          {/* =============================================================== */}
          {step === "UPLOADING" && file && (
            <div className="space-y-6 py-2">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-md bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-slate-900 truncate">{file.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {formatBytes(progress.uploadedBytes)} of {formatBytes(file.size)}
                  </p>
                </div>
                <span className="text-base font-bold text-indigo-700">
                  {progress.percentage}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-full rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress.percentage}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500 font-medium">
                  {progress.statusText || "Uploading chunks directly to storage..."}
                </p>
              </div>

              {/* Cancel Upload Button */}
              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-xs font-semibold text-red-600 hover:bg-red-50 rounded-lg transition-colors border border-red-200"
                >
                  Cancel Upload
                </button>
              </div>
            </div>
          )}

          {/* =============================================================== */}
          {/* STEP 4: SUCCESS / QUEUED PROCESSING                             */}
          {/* =============================================================== */}
          {step === "SUCCESS" && (
            <div className="text-center py-4 space-y-4">
              <div className="w-14 h-14 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200">
                <CheckCircle2 className="w-8 h-8" />
              </div>

              <div>
                <h3 className="text-base font-semibold text-slate-900">
                  Upload Complete!
                </h3>
                <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto leading-relaxed">
                  Your meeting media was uploaded directly to secure object storage.
                  The backend intelligence pipeline has been triggered for Whisper transcription,
                  speaker diarization, and LLM structured extraction.
                </p>
              </div>

              <div className="pt-2">
                <button
                  type="button"
                  onClick={handleDone}
                  className="px-6 py-2.5 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-sm transition-colors cursor-pointer"
                >
                  Done
                </button>
              </div>
            </div>
          )}

          {/* =============================================================== */}
          {/* ERROR STATE                                                     */}
          {/* =============================================================== */}
          {step === "ERROR" && (
            <div className="space-y-4 py-2">
              <div className="p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-red-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-sm font-semibold text-red-800">Upload Failed</h4>
                  <p className="text-xs text-red-600 mt-1">
                    {errorMessage || "An unexpected error occurred during direct upload."}
                  </p>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-4 py-2 text-sm font-medium text-slate-600 hover:text-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleStartUpload}
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg shadow-xs transition-colors flex items-center gap-1.5"
                >
                  <RotateCcw className="w-4 h-4" />
                  <span>Retry Upload</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
