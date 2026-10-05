"use client";

import React, { useState, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
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
  RotateCcw,
  ArrowRight,
  Sparkles,
  Globe,
  ShieldCheck
} from "lucide-react";
import Link from "next/link";
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

const SUPPORTED_ACCEPT =
  "video/*,audio/*,.mp4,.mov,.mkv,.webm,.mp3,.wav,.m4a,.txt,.srt,.vtt,text/plain";

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
  const [mounted, setMounted] = useState(false);
  const [step, setStep] = useState<ModalStep>("SELECT");
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState("");
  const [meetingDate, setMeetingDate] = useState("");
  const [language, setLanguage] = useState("en");
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

  // Client-side portal mounting check
  useEffect(() => {
    setMounted(true);
  }, []);

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
    setLanguage("en");
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

  const handleClose = useCallback(() => {
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
  }, [step, resetForm, onClose]);

  // Keyboard shortcut: ESC to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && isOpen) {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleClose]);

  // Handle file selection
  const processSelectedFile = (selectedFile: File) => {
    setFile(selectedFile);
    // Suggest title from filename without extension
    const baseName = selectedFile.name.replace(/\.[^/.]+$/, "").replace(/[_-]/g, " ");
    setTitle(baseName.charAt(0).toUpperCase() + baseName.slice(1));
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
      const isTranscript = Boolean(
        file.name.match(/\.(txt|srt|vtt)$/i) || file.type === "text/plain"
      );
      let resultMeetingId: string;

      if (isTranscript) {
        const result = await UploadService.importTranscript(
          file,
          title.trim() || undefined,
          meetingDate || undefined,
          language || "en",
          controller.signal,
          (prog: UploadProgress) => setProgress(prog)
        );
        resultMeetingId = result.meetingId;
      } else {
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
        resultMeetingId = result.meetingId;
      }

      setCreatedMeetingId(resultMeetingId);
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

  if (!isOpen || !mounted) return null;

  const isTranscript = Boolean(
    file?.name.match(/\.(txt|srt|vtt)$/i) || file?.type === "text/plain"
  );
  const isVideo =
    !isTranscript &&
    (file?.type.startsWith("video/") ||
      Boolean(file?.name.match(/\.(mp4|mov|mkv|webm)$/i)));


  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      {/* Background backdrop click handler */}
      <div
        className="fixed inset-0"
        onClick={() => {
          if (step !== "UPLOADING") handleClose();
        }}
        aria-hidden="true"
      />

      <div
        className="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200/80 overflow-hidden flex flex-col z-10 transition-all"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="upload-modal-title"
      >
        {/* ── Modal Header: Standard Enterprise Light Styling ── */}
        <div className="flex items-center justify-between px-6 py-4.5 bg-slate-50/60 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-indigo-50 border border-indigo-100/80 flex items-center justify-center text-indigo-600 shadow-2xs shrink-0">
              <UploadCloud className="w-4.5 h-4.5 stroke-[2.2]" />
            </div>
            <div>
              <h2
                id="upload-modal-title"
                className="text-base font-semibold text-slate-900 tracking-tight leading-tight"
              >
                Upload Meeting
              </h2>
              <p className="text-xs text-slate-500 mt-0.5 leading-normal">
                Upload a recording or transcript to analyze and extract insights
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer shrink-0"
            aria-label="Close modal"
          >
            <X className="w-4.5 h-4.5" />
          </button>
        </div>

        {/* ── Modal Body ────────────────────────────────────────────────────── */}
        {/* =============================================================== */}
        {/* STEP 1: FILE SELECTION / DROPZONE                               */}
        {/* =============================================================== */}
        {step === "SELECT" && (
          <>
            <div className="p-6">
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`relative border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-150 group ${
                  isDragging
                    ? "border-indigo-500 bg-indigo-50/50"
                    : "border-slate-200 bg-slate-50/50 hover:bg-slate-50 hover:border-slate-300"
                }`}
              >
                <input
                  ref={fileInputRef}
                  type="file"
                  accept={SUPPORTED_ACCEPT}
                  onChange={onFileInputChange}
                  className="hidden"
                />

                <div className="w-12 h-12 rounded-xl bg-white border border-slate-200/80 shadow-2xs text-indigo-600 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform">
                  <UploadCloud className="w-6 h-6 stroke-[2]" />
                </div>

                <p className="text-sm font-semibold text-slate-900 tracking-tight">
                  Drop your file here, or{" "}
                  <span className="text-indigo-600 group-hover:text-indigo-700 font-semibold underline underline-offset-2">
                    browse
                  </span>
                </p>

                <p className="text-xs text-slate-500 mt-1 font-normal">
                  MP4, MOV, MP3, WAV, TXT, or SRT (up to 2 GB)
                </p>
              </div>
            </div>

            {/* Step 1 Footer */}
            <div className="flex items-center justify-between px-6 py-3.5 bg-slate-50/60 border-t border-slate-100">
              <span className="flex items-center gap-1.5 text-xs text-slate-500 font-medium">
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                Encrypted & tenant isolated
              </span>
              <button
                type="button"
                onClick={handleClose}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
            </div>
          </>
        )}

        {/* =============================================================== */}
        {/* STEP 2: MEETING DETAILS FORM                                    */}
        {/* =============================================================== */}
        {step === "DETAILS" && file && (
          <>
            <div className="p-6 space-y-4">
              {/* Selected File Pill */}
              <div className="flex items-center justify-between p-3 bg-slate-50/90 rounded-xl border border-slate-200/80">
                <div className="flex items-center gap-2.5 min-w-0">
                  <div
                    className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 shadow-2xs ${
                      isTranscript
                        ? "bg-emerald-100 text-emerald-700"
                        : isVideo
                        ? "bg-blue-100 text-blue-700"
                        : "bg-purple-100 text-purple-700"
                    }`}
                  >
                    {isTranscript ? (
                      <FileText className="w-4.5 h-4.5" />
                    ) : isVideo ? (
                      <FileVideo className="w-4.5 h-4.5" />
                    ) : (
                      <FileAudio className="w-4.5 h-4.5" />
                    )}
                  </div>
                  <div className="min-w-0">
                    <p
                      className="text-xs font-semibold text-slate-900 truncate"
                      title={file.name}
                    >
                      {file.name}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1.5">
                      <span>{formatBytes(file.size)}</span>
                      <span>•</span>
                      <span className={isTranscript ? "text-emerald-700 font-medium" : "text-indigo-700 font-medium"}>
                        {isTranscript ? "Transcript" : isVideo ? "Video" : "Audio"}
                      </span>
                    </p>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => setStep("SELECT")}
                  className="text-xs font-semibold text-indigo-600 hover:text-indigo-800 px-2.5 py-1 rounded-lg hover:bg-indigo-50 transition-colors ml-2 shrink-0 cursor-pointer"
                >
                  Change
                </button>
              </div>

              {/* Title Field */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700">
                    Meeting Title
                  </label>
                  <span className="text-[11px] text-slate-400 font-normal">
                    Optional · Auto-generated
                  </span>
                </div>
                <div className="relative">
                  <FileText className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                  <input
                    type="text"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="e.g. Q4 Product Roadmap & Architecture Sync..."
                    className="w-full text-xs sm:text-sm pl-9 pr-3 h-9.5 border border-slate-200 rounded-xl bg-white shadow-2xs focus:outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-slate-900 transition-all"
                  />
                </div>
              </div>

              {/* Grid: Date & Language */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">
                    Meeting Date
                  </label>
                  <div className="relative">
                    <Calendar className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <input
                      type="date"
                      value={meetingDate}
                      onChange={(e) => setMeetingDate(e.target.value)}
                      className="w-full text-xs sm:text-sm pl-9 pr-3 h-9.5 border border-slate-200 rounded-xl bg-white shadow-2xs focus:outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-slate-900 cursor-pointer transition-all"
                    />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">
                    Spoken Language
                  </label>
                  <div className="relative">
                    <Globe className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 pointer-events-none" />
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                      className="w-full text-xs sm:text-sm pl-9 pr-3 h-9.5 border border-slate-200 rounded-xl bg-white shadow-2xs focus:outline-hidden focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 text-slate-900 cursor-pointer transition-all"
                    >
                      <option value="en">English (US / UK / Global)</option>
                      <option value="hinglish">Hinglish (Hindi + English)</option>
                      <option value="es">Spanish (Español)</option>
                      <option value="fr">French (Français)</option>
                      <option value="de">German (Deutsch)</option>
                      <option value="auto">Auto-detect Language</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            {/* Step 2 Footer */}
            <div className="flex items-center justify-between px-6 py-3.5 bg-slate-50/60 border-t border-slate-100">
              <button
                type="button"
                onClick={handleClose}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleStartUpload}
                className="inline-flex items-center gap-2 h-9 px-4.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs hover:shadow-sm transition-all active:scale-95 cursor-pointer"
              >
                <UploadCloud className="w-3.5 h-3.5" />
                <span>{isTranscript ? "Import Transcript" : "Start Upload"}</span>
              </button>
            </div>
          </>
        )}

        {/* =============================================================== */}
        {/* STEP 3: UPLOAD PROGRESS                                         */}
        {/* =============================================================== */}
        {step === "UPLOADING" && file && (
          <>
            <div className="p-6 space-y-5">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100">
                  <Loader2 className="w-5 h-5 animate-spin" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-semibold text-slate-900 truncate">
                    {file.name}
                  </p>
                  <p className="text-[11px] text-slate-500 mt-0.5">
                    {formatBytes(progress.uploadedBytes)} of {formatBytes(file.size)}
                  </p>
                </div>
                <span className="text-sm font-bold text-indigo-600 font-mono">
                  {progress.percentage}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="space-y-1.5">
                <div className="w-full bg-slate-100 rounded-full h-2.5 overflow-hidden">
                  <div
                    className="bg-indigo-600 h-full rounded-full transition-all duration-300 ease-out"
                    style={{ width: `${progress.percentage}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500 font-medium">
                  {progress.statusText || "Processing and transferring media chunks..."}
                </p>
              </div>
            </div>

            {/* Step 3 Footer */}
            <div className="flex items-center justify-end px-6 py-3.5 bg-slate-50/60 border-t border-slate-100">
              <button
                type="button"
                onClick={handleClose}
                className="text-xs font-semibold text-rose-600 hover:text-rose-700 transition-colors cursor-pointer"
              >
                Cancel Upload
              </button>
            </div>
          </>
        )}

        {/* =============================================================== */}
        {/* STEP 4: SUCCESS                                                 */}
        {/* =============================================================== */}
        {step === "SUCCESS" && (
          <div className="p-8 text-center space-y-4">
            <div className="w-12 h-12 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto border border-emerald-200 shadow-2xs">
              <CheckCircle2 className="w-6 h-6 stroke-[2.2]" />
            </div>

            <div>
              <h3 className="text-base font-bold text-slate-900 tracking-tight">
                {isTranscript ? "Transcript Imported & Processed" : "Upload Complete"}
              </h3>
              <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto leading-relaxed">
                {isTranscript
                  ? "Your transcript has been parsed into structured dialogue, indexed for Copilot search, and queued for recap synthesis."
                  : "Your media was uploaded securely. Audio transcription, speaker clustering, and AI executive recap are running."}
              </p>
            </div>

            <div className="pt-2 flex items-center justify-center gap-2.5">
              <button
                type="button"
                onClick={handleDone}
                className="h-9 px-4 rounded-xl text-xs font-semibold text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors cursor-pointer"
              >
                Done
              </button>
              {createdMeetingId && (
                <Link
                  href={`/meetings/${createdMeetingId}`}
                  onClick={handleClose}
                  className="inline-flex items-center gap-1.5 h-9 px-4 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
                >
                  <span>Open Meeting</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              )}
            </div>
          </div>
        )}

        {/* =============================================================== */}
        {/* ERROR STATE                                                     */}
        {/* =============================================================== */}
        {step === "ERROR" && (
          <>
            <div className="p-6 space-y-4">
              <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />
                <div>
                  <h4 className="text-xs font-bold text-rose-900">Upload Failed</h4>
                  <p className="text-[11px] text-rose-700 mt-0.5 leading-relaxed">
                    {errorMessage || "An unexpected error occurred during direct upload."}
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center justify-between px-6 py-3.5 bg-slate-50/60 border-t border-slate-100">
              <button
                type="button"
                onClick={handleClose}
                className="text-xs font-semibold text-slate-600 hover:text-slate-800 transition-colors cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleStartUpload}
                className="inline-flex items-center gap-1.5 h-9 px-4 rounded-xl text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-xs transition-colors cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Retry Upload</span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
