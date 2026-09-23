"use client";

import React, { useState, useRef, useEffect } from "react";
import {
  Radio,
  Mic,
  Volume2,
  X,
  Play,
  Square,
  Copy,
  Check,
  Sparkles,
  Terminal,
  Loader2,
  Laptop,
  MessageSquare
} from "lucide-react";
import { useRouter } from "next/navigation";
import { api, getWebSocketUrl } from "@/lib/api/client";
import { useSession } from "@/lib/auth/session";

export interface LiveMeetingModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLiveStarted?: (meetingId: string) => void;
}

interface LiveTranscriptItem {
  speaker: string;
  text: string;
  channel: number;
  time: string;
}

export function LiveMeetingModal({ isOpen, onClose, onLiveStarted }: LiveMeetingModalProps) {
  const router = useRouter();
  const { session } = useSession();
  const [meetingTitle, setMeetingTitle] = useState("");
  const [hostName, setHostName] = useState(session?.user?.full_name || "Sujal Nage");
  const [attendees, setAttendees] = useState("");
  const [mode, setMode] = useState<"browser" | "desktop">("browser");
  const [language, setLanguage] = useState<"hi-IN" | "en-IN" | "en-US">("hi-IN");
  const [isStarting, setIsStarting] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [liveMeetingId, setLiveMeetingId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // Live Transcripts feed in the modal
  const [liveTranscripts, setLiveTranscripts] = useState<LiveTranscriptItem[]>([]);
  const [interimSpeech, setInterimSpeech] = useState<string>("");
  const [agentStatus, setAgentStatus] = useState<"checking" | "detected" | "not_running">("checking");
  const [agentAutoLaunched, setAgentAutoLaunched] = useState(false);

  // Audio & Stream References
  const isRecordingRef = useRef(false);
  const micStreamRef = useRef<MediaStream | null>(null);
  const tabStreamRef = useRef<MediaStream | null>(null);
  const micRecorderRef = useRef<MediaRecorder | null>(null);
  const tabRecorderRef = useRef<MediaRecorder | null>(null);
  const recognitionRef = useRef<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const transcriptFeedRef = useRef<HTMLDivElement | null>(null);

  const [micActive, setMicActive] = useState(false);
  const [tabAudioActive, setTabAudioActive] = useState(false);

  useEffect(() => {
    if (session?.user?.full_name) {
      setHostName(session.user.full_name);
    }
  }, [session?.user?.full_name]);

  // Check if Knowra Desktop Agent daemon is running on port 9876
  useEffect(() => {
    let active = true;
    const checkAgent = async () => {
      try {
        const ctrl = new AbortController();
        const tid = setTimeout(() => ctrl.abort(), 1200);
        const res = await fetch("http://127.0.0.1:9876/status", { signal: ctrl.signal });
        clearTimeout(tid);
        if (res.ok) {
          if (active) setAgentStatus("detected");
        } else {
          if (active) setAgentStatus("not_running");
        }
      } catch {
        if (active) setAgentStatus("not_running");
      }
    };
    if (isOpen) {
      checkAgent();
      const interval = setInterval(checkAgent, 3500);
      return () => {
        active = false;
        clearInterval(interval);
      };
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen) {
      const now = new Date();
      setMeetingTitle(`Live Sync • ${now.toLocaleDateString([], { month: "short", day: "numeric" })}`);
      if (session?.user?.full_name) {
        setHostName(session.user.full_name);
      }
      setAgentAutoLaunched(false);
    } else {
      stopAllAudio();
      setIsRecording(false);
      isRecordingRef.current = false;
      setLiveMeetingId(null);
      setElapsedSeconds(0);
      setLiveTranscripts([]);
      setInterimSpeech("");
      setAgentAutoLaunched(false);
    }
  }, [isOpen]);

  // Elapsed timer
  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setElapsedSeconds((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  // Auto-scroll live transcript preview
  useEffect(() => {
    if (transcriptFeedRef.current) {
      transcriptFeedRef.current.scrollTop = transcriptFeedRef.current.scrollHeight;
    }
  }, [liveTranscripts, interimSpeech]);

  const stopAllAudio = () => {
    isRecordingRef.current = false;

    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      recognitionRef.current = null;
    }

    if (micRecorderRef.current && micRecorderRef.current.state !== "inactive") {
      try {
        micRecorderRef.current.stop();
      } catch {}
      micRecorderRef.current = null;
    }

    if (tabRecorderRef.current && tabRecorderRef.current.state !== "inactive") {
      try {
        tabRecorderRef.current.stop();
      } catch {}
      tabRecorderRef.current = null;
    }

    if (micStreamRef.current) {
      micStreamRef.current.getTracks().forEach((t) => t.stop());
      micStreamRef.current = null;
    }
    if (tabStreamRef.current) {
      tabStreamRef.current.getTracks().forEach((t) => t.stop());
      tabStreamRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }
    setMicActive(false);
    setTabAudioActive(false);
  };

  const handleStartBrowserCapture = async () => {
    setIsStarting(true);
    setLiveTranscripts([]);
    setInterimSpeech("");

    try {
      // 1. Create live meeting in backend with selected language
      const res = await api.post<{ meetingId: string; liveStreamWsUrl: string }>(
        "/meetings/live/start",
        {
          title: meetingTitle || "Live Meeting",
          hostName: hostName || "You (Host)",
          attendees: attendees.trim() || undefined,
          language: language.startsWith("hi") ? "hi" : "en",
        }
      );
      const mId = res.meetingId;
      setLiveMeetingId(mId);

      // 2. Request host microphone (Channel 1)
      let micStream: MediaStream | null = null;
      try {
        micStream = await navigator.mediaDevices.getUserMedia({
          audio: {
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          },
        });
        micStreamRef.current = micStream;
        setMicActive(true);
      } catch (err) {
        console.warn("Microphone access declined, continuing:", err);
      }

      // 3. Request tab or desktop audio (Channel 2)
      try {
        const displayStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });
        tabStreamRef.current = displayStream;
        setTabAudioActive(true);
      } catch (err) {
        console.warn("Display capture skipped:", err);
      }

      // 4. Connect WebSocket to live stream endpoint on backend (Port 8000)
      const wsUrl = getWebSocketUrl(`/meetings/${mId}/live-stream`);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        setIsRecording(true);
        isRecordingRef.current = true;
        setIsStarting(false);
        if (onLiveStarted) onLiveStarted(mId);

        // ── A. START CONTINUOUS SPEECH RECOGNITION (MIC -> LIVE HINDI/ENGLISH TRANSCRIPT) ──
        const SpeechRecognition =
          (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

        if (SpeechRecognition) {
          try {
            const recognition = new SpeechRecognition();
            recognition.continuous = true;
            recognition.interimResults = true;
            // Native Hindi (hi-IN), Hinglish (en-IN), or English (en-US)
            recognition.lang = language;

            recognition.onresult = (event: any) => {
              for (let i = event.resultIndex; i < event.results.length; ++i) {
                const speechChunk = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                  const finalTxt = speechChunk.trim();
                  if (finalTxt.length > 0) {
                    // Send to backend via WebSocket
                    if (ws.readyState === WebSocket.OPEN) {
                      ws.send(
                        JSON.stringify({
                          channel: 1,
                          speaker_hint: hostName || "You (Host)",
                          text_hint: finalTxt,
                          language: language.startsWith("hi") ? "hi" : "en",
                        })
                      );
                    }

                    // Add to live visual feed in modal
                    setLiveTranscripts((prev) => [
                      ...prev,
                      {
                        speaker: hostName || "You (Host)",
                        text: finalTxt,
                        channel: 1,
                        time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
                      },
                    ]);
                    setInterimSpeech("");
                  }
                } else {
                  setInterimSpeech(speechChunk);
                }
              }
            };

            recognition.onerror = (e: any) => {
              console.warn("Speech recognition warning:", e.error);
            };

            recognition.onend = () => {
              // Automatically restart recognition if still recording
              if (isRecordingRef.current) {
                try {
                  recognition.start();
                } catch {}
              }
            };

            recognition.start();
            recognitionRef.current = recognition;
          } catch (e) {
            console.warn("Could not start Web Speech Recognition:", e);
          }
        }

        // ── B. START MEDIARECORDER FOR AUDIO CHUNK TRANSMISSION ──
        if (micStream && typeof MediaRecorder !== "undefined") {
          try {
            const recorder = new MediaRecorder(micStream);
            recorder.ondataavailable = async (e) => {
              if (e.data && e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                const buffer = await e.data.arrayBuffer();
                const bytes = new Uint8Array(buffer);
                let binary = "";
                for (let i = 0; i < bytes.byteLength; i++) {
                  binary += String.fromCharCode(bytes[i]);
                }
                const base64Audio = window.btoa(binary);

                ws.send(
                  JSON.stringify({
                    channel: 1,
                    speaker_hint: hostName || "You (Host)",
                    audio_base64: base64Audio,
                  })
                );
              }
            };
            recorder.start(2500); // Send audio every 2.5 seconds
            micRecorderRef.current = recorder;
          } catch (e) {
            console.warn("MediaRecorder mic start error:", e);
          }
        }

        // ── C. ATTACH RECORDER TO TAB STREAM (CHANNEL 2) IF SHARED ──
        if (tabStreamRef.current && typeof MediaRecorder !== "undefined") {
          const audioTracks = tabStreamRef.current.getAudioTracks();
          if (audioTracks.length > 0) {
            try {
              const tabAudioOnly = new MediaStream(audioTracks);
              const tabRec = new MediaRecorder(tabAudioOnly);
              tabRec.ondataavailable = async (e) => {
                if (e.data && e.data.size > 0 && ws.readyState === WebSocket.OPEN) {
                  const buffer = await e.data.arrayBuffer();
                  const bytes = new Uint8Array(buffer);
                  let binary = "";
                  for (let i = 0; i < bytes.byteLength; i++) {
                    binary += String.fromCharCode(bytes[i]);
                  }
                  const base64Audio = window.btoa(binary);

                  ws.send(
                    JSON.stringify({
                      channel: 2,
                      speaker_hint: "Remote Attendee",
                      audio_base64: base64Audio,
                    })
                  );
                }
              };
              tabRec.start(2500);
              tabRecorderRef.current = tabRec;
            } catch (e) {
              console.warn("MediaRecorder tab start error:", e);
            }
          }
        }
      };

      ws.onerror = (e) => {
        console.error("Live stream WebSocket error:", e);
        setIsStarting(false);
      };
    } catch (err) {
      console.error("Failed to start live meeting:", err);
      setIsStarting(false);
      alert("Could not start live meeting session. Please ensure backend is running.");
    }
  };

  const handleStartDesktopMode = async () => {
    setIsStarting(true);
    setLiveTranscripts([]);
    setInterimSpeech("");
    try {
      const res = await api.post<{ meetingId: string }>("/meetings/live/start", {
        title: meetingTitle || "Live Meeting",
        hostName: hostName || "You (Host)",
        attendees: attendees.trim() || undefined,
        language: language.startsWith("hi") ? "hi" : "en",
      });
      const mId = res.meetingId;
      setLiveMeetingId(mId);
      setIsRecording(true);
      isRecordingRef.current = true;
      setIsStarting(false);
      if (onLiveStarted) onLiveStarted(mId);

      // ── 1-CLICK AUTO-LAUNCH COMPANION (ZERO TERMINAL COMMANDS) ──
      let launched = false;
      // Step A: Attempt trigger via Local Agent daemon on port 9876
      try {
        const agentRes = await fetch("http://127.0.0.1:9876/start", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            meetingId: mId,
            hostName: hostName || "Sujal Nage",
            attendees: attendees.trim(),
            language: language.startsWith("hi") ? "hi" : "en",
          }),
        });
        if (agentRes.ok) {
          launched = true;
          setAgentAutoLaunched(true);
        }
      } catch (err) {
        console.warn("Local agent on 9876 not responding:", err);
      }

      // Step B: Fallback to backend 1-click companion launcher if local agent isn't running
      if (!launched) {
        try {
          await api.post(`/meetings/${mId}/companion/launch`, {
            hostName: hostName || "Sujal Nage",
            attendees: attendees.trim(),
            language: language.startsWith("hi") ? "hi" : "en",
          });
          setAgentAutoLaunched(true);
          launched = true;
        } catch (backendErr) {
          console.warn("Backend 1-click launch fallback skipped:", backendErr);
        }
      }

      // Connect to live transcript WebSocket so the modal live stream feed renders turns in real time!
      const wsUrl = getWebSocketUrl(`/meetings/${mId}/live-transcript`);
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "TRANSCRIPT_SEGMENT" && data.segment) {
            const seg = data.segment;
            setLiveTranscripts((prev) => [
              ...prev,
              {
                speaker: seg.speaker?.displayName || seg.speaker?.label || "Speaker",
                text: seg.text,
                channel: seg.channel || 1,
                time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              },
            ]);
          } else if (data.type === "SPEAKER_RENAME" && data.oldName && data.newName) {
            setLiveTranscripts((prev) =>
              prev.map((item) =>
                item.speaker === data.oldName ? { ...item, speaker: data.newName } : item
              )
            );
          }
        } catch (e) {
          console.error("Error parsing live transcript message:", e);
        }
      };
    } catch (err) {
      console.error("Failed to init desktop companion meeting:", err);
      setIsStarting(false);
    }
  };

  const handleEndMeeting = async () => {
    if (!liveMeetingId) {
      onClose();
      return;
    }
    stopAllAudio();
    setIsRecording(false);
    isRecordingRef.current = false;

    // Send stop signal to desktop agent and backend companion
    try {
      fetch("http://127.0.0.1:9876/stop", { method: "POST" }).catch(() => {});
    } catch {}
    try {
      api.post(`/meetings/${liveMeetingId}/companion/stop`, {}).catch(() => {});
    } catch {}

    try {
      await api.post(`/meetings/${liveMeetingId}/live/end`, {});
    } catch (e) {
      console.warn("Error finalizing live meeting:", e);
    }
    onClose();
    router.push(`/meetings/${liveMeetingId}`);
  };

  const copyCommand = (simulate: boolean = false) => {
    if (!liveMeetingId) return;
    const attendeesFlag = attendees.trim() ? ` --attendees "${attendees.trim()}"` : "";
    const effectiveHost = hostName.trim() || session?.user?.full_name || "Sujal Nage";
    const hostFlag = ` --host-name "${effectiveHost}"`;
    const langFlag = language.startsWith("hi") ? (simulate ? " --hindi" : " --language hi") : "";

    const cmd = simulate
      ? `python scripts/desktop_meeting_companion.py --meeting-id ${liveMeetingId}${langFlag || " --simulate"}${attendeesFlag}${hostFlag}`
      : `python scripts/desktop_meeting_companion.py --meeting-id ${liveMeetingId}${langFlag}${attendeesFlag}${hostFlag}`;
    navigator.clipboard.writeText(cmd);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatTimer = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div
        className="w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-100 overflow-hidden flex flex-col"
        role="dialog"
      >
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4.5 border-b border-slate-100 bg-slate-50/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-[#5345dc]">
              <Radio className="w-4 h-4 animate-pulse" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900 flex items-center gap-2">
                <span>Connect Live Meeting</span>
                {isRecording && (
                  <span className="flex items-center gap-1 text-[11px] font-medium text-rose-600 bg-rose-50 border border-rose-200/60 px-2 py-0.5 rounded-full animate-pulse">
                    <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
                    LIVE • {formatTimer(elapsedSeconds)}
                  </span>
                )}
              </h2>
              <p className="text-xs text-slate-500">
                Multi-track speaker separation for Teams, Zoom, & Meet
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-4">
          {!isRecording ? (
            <>
              {/* Meeting Meta Inputs */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1 col-span-2">
                  <label className="text-xs font-medium text-slate-700">Meeting Title</label>
                  <input
                    type="text"
                    value={meetingTitle}
                    onChange={(e) => setMeetingTitle(e.target.value)}
                    placeholder="e.g. Weekly Product Architecture Review"
                    className="w-full text-xs h-9 px-3 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1 col-span-2">
                  <label className="text-xs font-medium text-slate-700">Host Identifier (Channel 1 - Your Mic)</label>
                  <input
                    type="text"
                    value={hostName}
                    onChange={(e) => setHostName(e.target.value)}
                    placeholder={session?.user?.full_name || "Host"}
                    className="w-full text-xs h-9 px-3 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                </div>
                <div className="space-y-1 col-span-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-700">Meeting Attendees (Channel 2 - Teams)</label>
                    <span className="text-[10px] text-slate-400">Optional</span>
                  </div>
                  <input
                    type="text"
                    value={attendees}
                    onChange={(e) => setAttendees(e.target.value)}
                    placeholder="e.g. Harshita, Yash Lade, Rahul Sharma"
                    className="w-full text-xs h-9 px-3 rounded-lg border border-slate-200 focus:outline-hidden focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
                  />
                  <p className="text-[10.5px] text-slate-400">
                    Names of attendees (separated by commas). Acoustic voice clustering automatically separates and attributes 3+ participants on the call.
                  </p>
                </div>

                {/* Language Selector */}
                <div className="space-y-1.5 col-span-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-700">Speech & Analysis Language</label>
                    <span className="text-[10px] text-indigo-600 font-medium">Deep Hindi Extraction</span>
                  </div>
                  <div className="grid grid-cols-3 gap-2">
                    <button
                      type="button"
                      onClick={() => setLanguage("hi-IN")}
                      className={`px-2 py-1.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        language === "hi-IN"
                          ? "border-indigo-600 bg-indigo-50 text-indigo-900 font-semibold shadow-2xs"
                          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <span>🇮🇳</span>
                      <span>Hindi (हिंदी)</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setLanguage("en-IN")}
                      className={`px-2 py-1.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        language === "en-IN"
                          ? "border-indigo-600 bg-indigo-50 text-indigo-900 font-semibold shadow-2xs"
                          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <span>🇮🇳</span>
                      <span>Hinglish</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setLanguage("en-US")}
                      className={`px-2 py-1.5 rounded-lg border text-xs font-medium flex items-center justify-center gap-1.5 transition-all cursor-pointer ${
                        language === "en-US"
                          ? "border-indigo-600 bg-indigo-50 text-indigo-900 font-semibold shadow-2xs"
                          : "border-slate-200 bg-white text-slate-600 hover:bg-slate-50"
                      }`}
                    >
                      <span>🌐</span>
                      <span>English</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Mode Switcher */}
              <div className="flex rounded-xl bg-slate-100/80 p-1">
                <button
                  type="button"
                  onClick={() => setMode("browser")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-medium rounded-lg transition-all cursor-pointer ${
                    mode === "browser"
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <Volume2 className="w-3.5 h-3.5 text-[#5345dc]" />
                  <span>In-Browser Capture (Free)</span>
                </button>
                <button
                  type="button"
                  onClick={() => setMode("desktop")}
                  className={`flex-1 flex items-center justify-center gap-2 py-2 text-xs font-medium rounded-lg transition-all cursor-pointer ${
                    mode === "desktop"
                      ? "bg-white text-slate-900 shadow-xs"
                      : "text-slate-600 hover:text-slate-900"
                  }`}
                >
                  <Laptop className="w-3.5 h-3.5 text-[#5345dc]" />
                  <span>Desktop Companion (Teams.exe)</span>
                </button>
              </div>

              {/* Mode Descriptions */}
              {mode === "browser" ? (
                <div className="rounded-xl border border-indigo-100/80 bg-indigo-50/40 p-3.5 space-y-2">
                  <div className="flex items-center gap-2 text-xs font-medium text-indigo-950">
                    <Sparkles className="w-4 h-4 text-[#5345dc]" />
                    <span>Zero-Bot Dual-Track Separation</span>
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Knowra will capture your <strong>Microphone (Host Channel 1)</strong> and prompt you to select your <strong>Meeting Tab / Window Audio (Remote Channel 2)</strong>. There is no bot waiting in the lobby!
                  </p>
                </div>
              ) : (
                <div className="rounded-xl border border-slate-200 bg-slate-50 p-3.5 space-y-2">
                  <div className="flex items-center justify-between text-xs font-medium text-slate-900">
                    <div className="flex items-center gap-2">
                      <Terminal className="w-4 h-4 text-slate-700" />
                      <span>Desktop 1-Click Auto-Launch Agent</span>
                    </div>
                    {agentStatus === "detected" ? (
                      <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                        Agent Connected (1-Click Ready)
                      </span>
                    ) : (
                      <span className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-800 text-[10px] font-semibold">
                        <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse" />
                        Direct 1-Click Launch Ready
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-600 leading-relaxed">
                    Automatically captures <strong>Host Mic</strong> and <strong>Teams.exe system audio</strong> with real-time acoustic voice separation for 2+ attendees. No terminal commands needed!
                  </p>
                </div>
              )}
            </>
          ) : (
            /* Active Live State */
            <div className="space-y-4">
              {/* Channel Indicators */}
              <div className="grid grid-cols-2 gap-2 text-left">
                <div className="p-2.5 rounded-xl border border-emerald-200 bg-emerald-50/50 flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                  <Mic className="w-4 h-4 text-emerald-600 shrink-0" />
                  <div className="truncate">
                    <div className="text-[11px] font-semibold text-emerald-950 truncate">Channel 1 (Host)</div>
                    <div className="text-[10px] text-emerald-700 truncate">{hostName} • Active</div>
                  </div>
                </div>

                <div className="p-2.5 rounded-xl border border-indigo-200 bg-indigo-50/50 flex items-center gap-2">
                  <Volume2 className="w-4 h-4 text-indigo-600 shrink-0" />
                  <div className="truncate">
                    <div className="text-[11px] font-semibold text-indigo-950 truncate">Channel 2 (Remote)</div>
                    <div className="text-[10px] text-indigo-700 truncate">{tabAudioActive ? "Tab Audio On" : "Listening"}</div>
                  </div>
                </div>
              </div>

              {/* Real-time Transcription Stream Feed */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-[11px] text-slate-500 font-medium">
                  <span className="flex items-center gap-1.5">
                    <MessageSquare className="w-3.5 h-3.5 text-indigo-600" />
                    <span>Live Transcribed Speech</span>
                  </span>
                  <span className="text-[10px] text-emerald-600 font-mono">Listening to mic...</span>
                </div>

                <div
                  ref={transcriptFeedRef}
                  className="h-44 rounded-xl border border-slate-200 bg-slate-50/60 p-3 overflow-y-auto space-y-2 text-left text-xs"
                >
                  {liveTranscripts.length === 0 && !interimSpeech && (
                    <div className="h-full flex flex-col items-center justify-center text-center text-slate-400">
                      <Mic className="w-5 h-5 mb-1 text-slate-300 animate-bounce" />
                      <p className="text-[11px]">Speak into your microphone...</p>
                      <p className="text-[10px] text-slate-400">Your words will appear here in real time.</p>
                    </div>
                  )}

                  {liveTranscripts.map((t, idx) => (
                    <div key={idx} className="bg-white p-2 rounded-lg border border-slate-100 shadow-2xs space-y-0.5">
                      <div className="flex items-center justify-between text-[10px]">
                        <span className="font-semibold text-indigo-950">{t.speaker}</span>
                        <span className="text-slate-400 font-mono">{t.time}</span>
                      </div>
                      <p className="text-slate-800 text-[11.5px] leading-relaxed">{t.text}</p>
                    </div>
                  ))}

                  {interimSpeech && (
                    <div className="bg-indigo-50/50 p-2 rounded-lg border border-indigo-100/60 space-y-0.5 animate-pulse">
                      <div className="text-[10px] font-semibold text-indigo-600">{hostName} (speaking...)</div>
                      <p className="text-slate-600 text-[11.5px] italic leading-relaxed">{interimSpeech}</p>
                    </div>
                  )}
                </div>
              </div>

              {mode === "desktop" && liveMeetingId && (
                <div className="space-y-2 mt-2">
                  <div className="p-3 rounded-xl border border-emerald-200 bg-emerald-50/70 flex items-center justify-between gap-3 text-left">
                    <div className="flex items-center gap-2.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-ping shrink-0" />
                      <div>
                        <div className="text-[11.5px] font-semibold text-emerald-950 flex items-center gap-1.5">
                          <span>🚀 Desktop Companion Auto-Capturing Live</span>
                        </div>
                        <div className="text-[10px] text-emerald-800 leading-relaxed">
                          Streaming Host Mic (Ch 1) + Teams.exe Audio (Ch 2) with multi-speaker acoustic voice clustering.
                        </div>
                      </div>
                    </div>
                    <span className="px-2 py-1 rounded-lg bg-emerald-600 text-white font-mono text-[10px] font-semibold shrink-0">
                      LIVE
                    </span>
                  </div>

                  {/* Collapsible / Optional Manual Terminal Command fallback */}
                  <details className="text-left text-[11px] text-slate-500">
                    <summary className="cursor-pointer hover:text-slate-800 font-medium">
                      Optional: View manual CLI command
                    </summary>
                    <div className="p-2.5 bg-slate-900 rounded-xl text-left text-slate-200 font-mono text-[10.5px] flex items-center justify-between gap-2 border border-slate-800 mt-1.5">
                      <span className="truncate">
                        python scripts/desktop_meeting_companion.py --meeting-id {liveMeetingId}
                        {language.startsWith("hi") ? " --language hi" : ""}
                        {attendees.trim() ? ` --attendees "${attendees.trim()}"` : ""}
                        {` --host-name "${hostName.trim() || session?.user?.full_name || "Sujal Nage"}"`}
                      </span>
                      <button
                        type="button"
                        onClick={() => copyCommand(false)}
                        className="px-2 py-1 rounded-md bg-[#5345dc] hover:bg-[#4638cb] text-white transition-colors shrink-0 cursor-pointer flex items-center gap-1 text-[10px]"
                      >
                        {copied ? <Check className="w-3 h-3 text-emerald-300" /> : <Copy className="w-3 h-3" />}
                        <span>Copy</span>
                      </button>
                    </div>
                  </details>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 bg-slate-50/80 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            className="text-xs font-medium text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
          >
            {isRecording ? "Keep in Background" : "Cancel"}
          </button>

          {!isRecording ? (
            <button
              type="button"
              disabled={isStarting}
              onClick={mode === "browser" ? handleStartBrowserCapture : handleStartDesktopMode}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-[#5345dc] hover:bg-[#4638cb] text-white shadow-xs transition-all disabled:opacity-50 cursor-pointer"
            >
              {isStarting ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Connecting...</span>
                </>
              ) : (
                <>
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Start Live Session</span>
                </>
              )}
            </button>
          ) : (
            <button
              type="button"
              onClick={handleEndMeeting}
              className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold bg-rose-600 hover:bg-rose-700 text-white shadow-xs transition-all cursor-pointer"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>End & View Transcript</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
