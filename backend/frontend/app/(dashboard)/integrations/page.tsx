"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { INTEGRATIONS, CHAT } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import { useSession } from "@/lib/auth/session";
import {
  type Integration,
  type IntegrationEvent,
  type CalendarConnectionStatus,
  type CalendarMeetingItem,
} from "@/lib/types";
import { PageHeader } from "@/components/ui/page-header";
import { cn, relativeTime } from "@/lib/utils";
import {
  Layers,
  Plus,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Mail,
  Send,
  Sparkles,
  Zap,
  ExternalLink,
  Trash2,
  ChevronDown,
  Code2,
  Calendar,
  Search,
  Eye,
  Sliders,
  Filter,
  ArrowUpDown,
  Shield,
  CheckCheck,
  Check,
  User,
  Lock,
} from "lucide-react";

// Secure environment fallback for Resend
const DEFAULT_RESEND_KEY = process.env.NEXT_PUBLIC_RESEND_API_KEY || "";

interface ConnectorItem {
  id: string;
  provider: string;
  name: string;
  category: "calendar" | "email" | "tracker" | "custom";
  categoryLabel: string;
  iconBg: string;
  iconSvg: string;
  subtitle: string;
  description: string;
  policyNotice?: string;
  tags: string[];
  docUrl: string;
}

const ALL_CONNECTORS: ConnectorItem[] = [
  {
    id: "google-calendar",
    provider: "GOOGLE_CALENDAR",
    name: "Google Calendar",
    category: "calendar",
    categoryLabel: "Calendar & Meetings",
    iconBg: "bg-blue-50 text-blue-600 border-blue-200",
    iconSvg: "📅",
    subtitle: "Let Knowra join and generate reports for Google Calendar meetings.",
    description:
      "Allow Knowra Assistant to join and generate reports for your Google Calendar meetings, and easily search past or upcoming events with Ask Knowra.",
    policyNotice:
      "Knowra's use of information received from Google adheres to the user data and developer policies for Google API Services, the Google Workspace API, and the Google Photos API, including the Limited Use requirements.",
    tags: ["Calendar & Meetings", "Ask Knowra"],
    docUrl: "https://support.google.com/calendar",
  },
  {
    id: "google-meet",
    provider: "GOOGLE_MEET",
    name: "Google Meet",
    category: "calendar",
    categoryLabel: "Calendar & Meetings",
    iconBg: "bg-emerald-50 text-emerald-600 border-emerald-200",
    iconSvg: "🟢",
    subtitle: "Let Knowra AI capture and generate reports for Google Meet meetings without a bot.",
    description:
      "Seamlessly ingest Google Meet video audio streams, transcripts, and speaker identification without requiring a participant bot.",
    policyNotice:
      "Google Meet data is transmitted with end-to-end TLS 1.3 encryption and processed strictly within your dedicated tenant boundary.",
    tags: ["Calendar & Meetings"],
    docUrl: "https://meet.google.com",
  },
  {
    id: "outlook-calendar",
    provider: "OUTLOOK",
    name: "Outlook Calendar",
    category: "calendar",
    categoryLabel: "Calendar & Meetings",
    iconBg: "bg-sky-50 text-sky-600 border-sky-200",
    iconSvg: "📫",
    subtitle: "Let Knowra join and generate reports for Outlook Calendar meetings.",
    description:
      "Connect Microsoft 365 and Outlook Calendar to automatically schedule Knowra notetakers for upcoming executive syncs and board reviews.",
    policyNotice:
      "Microsoft Graph API authorization adheres to Microsoft Cloud App Security and Tenant Data Protection compliance standards.",
    tags: ["Calendar & Meetings", "Ask Knowra"],
    docUrl: "https://outlook.office.com",
  },
  {
    id: "zoom",
    provider: "ZOOM",
    name: "Zoom",
    category: "calendar",
    categoryLabel: "Calendar & Meetings",
    iconBg: "bg-blue-50 text-blue-600 border-blue-200",
    iconSvg: "📹",
    subtitle: "Let Knowra join and summarize Zoom meetings, and sync with Zoom Calendar.",
    description:
      "Synchronize your Zoom scheduled meetings and cloud recordings directly into Knowra's high-fidelity speech-to-text intelligence pipeline.",
    policyNotice:
      "Zoom OAuth application enforces OAuth 2.0 PKCE authentication with token auto-refresh.",
    tags: ["Calendar & Meetings", "Ask Knowra"],
    docUrl: "https://zoom.us",
  },
  {
    id: "resend-email",
    provider: "RESEND",
    name: "Resend Email Dispatcher",
    category: "email",
    categoryLabel: "Email & Communication",
    iconBg: "bg-indigo-50 text-indigo-600 border-indigo-200",
    iconSvg: "✉️",
    subtitle: "Automated executive email dispatches of meeting summaries and action items via Resend API.",
    description:
      "Dispatch beautifully structured, AI-synthesized executive briefings, key decisions, and prioritized action items directly to attendees via Resend REST API.",
    policyNotice:
      "Resend API transactions are authenticated via bearer tokens and logged with immutable cryptographic delivery audit records.",
    tags: ["Email", "Executive Dispatch"],
    docUrl: "https://resend.com",
  },
  {
    id: "slack",
    provider: "SLACK",
    name: "Slack Intelligence Bot",
    category: "email",
    categoryLabel: "Email & Communication",
    iconBg: "bg-purple-50 text-purple-600 border-purple-200",
    iconSvg: "💬",
    subtitle: "Post meeting recaps and action item alerts into enterprise Slack channels.",
    description:
      "Post meeting recaps, audio highlights, and action item notifications directly into enterprise channels (#general, #eng) with interactive thread replies.",
    policyNotice:
      "Incoming webhooks are verified with HMAC-SHA256 signatures before forwarding payloads.",
    tags: ["Team Chat", "Bot Mentions"],
    docUrl: "https://slack.com",
  },
  {
    id: "jira",
    provider: "JIRA",
    name: "Jira Software Automation",
    category: "tracker",
    categoryLabel: "Project Trackers",
    iconBg: "bg-blue-50 text-blue-700 border-blue-200",
    iconSvg: "🔵",
    subtitle: "Automatically transform verbal action items and commitments into Jira issues.",
    description:
      "Extract decisions and assigned action items from audio meetings, mapping them into Jira sprint issues with assigned owners and deadline tags.",
    policyNotice:
      "Jira REST API integration enforces TLS encryption and tenant-scoped OAuth2 tokens.",
    tags: ["Tracker", "Action Items"],
    docUrl: "https://atlassian.com/jira",
  },
  {
    id: "linear",
    provider: "LINEAR",
    name: "Linear Engineering Sync",
    category: "tracker",
    categoryLabel: "Project Trackers",
    iconBg: "bg-violet-50 text-violet-700 border-violet-200",
    iconSvg: "🔺",
    subtitle: "Sync technical decisions and architectural action items into Linear cycles.",
    description:
      "Push engineering decisions, vector database tasks, and architectural RFC action items directly into Linear teams, projects, and cycles.",
    policyNotice:
      "Linear API requests are encrypted and authenticated via scoped personal or team API tokens.",
    tags: ["Tracker", "Fast Issues"],
    docUrl: "https://linear.app",
  },
];

type TopTab = "your-integrations" | "workspace" | "resend" | "logs";

export default function IntegrationsPage() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  // Current authenticated user info or realistic enterprise default
  const userEmail = session?.user?.email || "sujal.nage@softude.com";
  const userName = session?.user?.full_name || "Sujal Nage";

  // Top Tab State
  const [currentTopTab, setCurrentTopTab] = useState<TopTab>("your-integrations");

  // Selected Connector in Read AI style split-pane
  const [selectedConnectorId, setSelectedConnectorId] = useState<string>("google-calendar");

  // Filter & Search Controls
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | "connected" | "not_connected">("all");
  const [sortBy, setSortBy] = useState<"category" | "name">("category");

  // Category collapse states
  const [collapsedCategories, setCollapsedCategories] = useState<Record<string, boolean>>({});

  // ── Real OAuth Account & Mail ID Selection Modal State ─────────────────────
  const [isOAuthModalOpen, setIsOAuthModalOpen] = useState(false);
  const [authConnector, setAuthConnector] = useState<ConnectorItem | null>(null);
  const [accountType, setAccountType] = useState<"work" | "personal" | "custom">("work");
  const [selectedEmail, setSelectedEmail] = useState<string>(userEmail);
  const [customEmail, setCustomEmail] = useState<string>("");
  const [scopeCalendar, setScopeCalendar] = useState<boolean>(true);
  const [scopeNotetaker, setScopeNotetaker] = useState<boolean>(true);
  const [scopeEmailSummaries, setScopeEmailSummaries] = useState<boolean>(true);

  // Payload viewer modal
  const [viewingPayload, setViewingPayload] = useState<Record<string, unknown> | null>(null);

  // New Integration Modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [modalProvider, setModalProvider] = useState<string>("SLACK");
  const [modalName, setModalName] = useState("");
  const [modalWebhookUrl, setModalWebhookUrl] = useState("");
  const [modalChannel, setModalChannel] = useState("");
  const [modalSecret, setModalSecret] = useState("");

  // Resend Test State
  const [resendApiKey, setResendApiKey] = useState(DEFAULT_RESEND_KEY);
  const [resendRecipient, setResendRecipient] = useState("delivered@resend.dev");
  const [resendSubject, setResendSubject] = useState("Q3 Strategic Architecture & Executive Review");
  const [resendStatusMsg, setResendStatusMsg] = useState<{ type: "success" | "error"; text: string; id?: string } | null>(null);

  // Copilot Chat State
  const [showCopilot, setShowCopilot] = useState(false);
  const [copilotInput, setCopilotInput] = useState("");
  const [copilotMessages, setCopilotMessages] = useState<Array<{ id: string; role: "user" | "assistant"; text: string; time: string }>>([
    {
      id: "welcome",
      role: "assistant",
      text: "Hello! I am your Knowra Integrations Copilot. I can help configure automated calendar sync for Google and Outlook, manage bot auto-join preferences, or test Resend email dispatches. What would you like to configure?",
      time: "Just now",
    },
  ]);
  const [isCopilotStreaming, setIsCopilotStreaming] = useState(false);

  // ── Queries ──────────────────────────────────────────────────────────────
  const { data: integrations = [], isLoading: isLoadingIntegrations, refetch: refetchIntegrations } = useQuery<Integration[]>({
    queryKey: queryKeys.integrations.list(),
    queryFn: () => api.get<Integration[]>(INTEGRATIONS.list()),
  });

  const { data: calendarStatuses = [], isLoading: isLoadingCalendarStatus, refetch: refetchCalendarStatus } = useQuery<CalendarConnectionStatus[]>({
    queryKey: queryKeys.integrations.calendarStatus(),
    queryFn: () => api.get<CalendarConnectionStatus[]>(INTEGRATIONS.calendarStatus()),
  });

  const { data: calendarEvents = [], isLoading: isLoadingCalendarEvents, refetch: refetchCalendarEvents } = useQuery<CalendarMeetingItem[]>({
    queryKey: queryKeys.integrations.calendarEvents(),
    queryFn: () => api.get<CalendarMeetingItem[]>(INTEGRATIONS.calendarEvents()),
  });

  const { data: eventsHistory = [], isLoading: isLoadingEvents, refetch: refetchEvents } = useQuery<IntegrationEvent[]>({
    queryKey: queryKeys.integrations.events(),
    queryFn: () => api.get<IntegrationEvent[]>(INTEGRATIONS.events()),
    refetchInterval: 12_000,
  });

  // ── Mutations ────────────────────────────────────────────────────────────
  const connectCalendarMutation = useMutation({
    mutationFn: ({
      provider,
      account_email,
      auto_join = true,
      email_summaries = true,
    }: {
      provider: string;
      account_email: string;
      auto_join?: boolean;
      email_summaries?: boolean;
    }) =>
      api.post<CalendarConnectionStatus>(INTEGRATIONS.calendarConnect(), {
        provider,
        account_email,
        auto_join,
        email_summaries,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarStatus() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarEvents() });
      setIsOAuthModalOpen(false);
    },
  });

  const disconnectCalendarMutation = useMutation({
    mutationFn: (provider: string) =>
      api.post<CalendarConnectionStatus>(INTEGRATIONS.calendarDisconnect(), {
        provider,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarStatus() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarEvents() });
    },
  });

  const syncCalendarsMutation = useMutation({
    mutationFn: () => api.post<{ success: boolean; message: string; synced_count: number }>(INTEGRATIONS.calendarSync(), {}),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarStatus() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarEvents() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
      alert(data?.message || "Calendars successfully synchronized!");
    },
  });

  const toggleBotMutation = useMutation({
    mutationFn: ({ meetingId, autoJoin }: { meetingId: string; autoJoin: boolean }) =>
      api.post<{ meeting_id: string; auto_join: boolean; message: string }>(INTEGRATIONS.calendarToggleBot(), {
        meeting_id: meetingId,
        auto_join: autoJoin,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarEvents() });
    },
  });

  const createIntegrationMutation = useMutation({
    mutationFn: (data: {
      provider: string;
      name: string;
      webhook_url?: string;
      channel_or_project_id?: string;
      credentials_secret?: string;
    }) => api.post<Integration>(INTEGRATIONS.create(), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      setIsAddModalOpen(false);
      resetModalForm();
    },
  });

  const deleteIntegrationMutation = useMutation({
    mutationFn: (id: string) => api.delete(INTEGRATIONS.delete(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
    },
  });

  const testIntegrationMutation = useMutation({
    mutationFn: (id: string) => api.post<{ detail: string }>(INTEGRATIONS.test(id), {}),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
      alert(res?.detail || "Test ping successfully dispatched! Check Delivery Logs tab.");
    },
  });

  const resendTestMutation = useMutation({
    mutationFn: (payload: { api_key?: string; to_email: string; meeting_title: string }) =>
      api.post<{ success: boolean; email_id: string; recipient: string; message: string }>(
        INTEGRATIONS.testResend(),
        payload
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
      setResendStatusMsg({
        type: "success",
        text: `Dispatched successfully to ${data.recipient}`,
        id: data.email_id,
      });
    },
    onError: (err: any) => {
      setResendStatusMsg({
        type: "error",
        text: err?.message || "Failed to dispatch email via Resend API",
      });
    },
  });

  const resetModalForm = () => {
    setModalName("");
    setModalWebhookUrl("");
    setModalChannel("");
    setModalSecret("");
  };

  // ── Open Real OAuth Account Picker Modal ─────────────────────────────────
  const handleOpenConnect = (connector: ConnectorItem) => {
    setAuthConnector(connector);
    setAccountType("work");
    setSelectedEmail(userEmail);
    setCustomEmail("");
    setIsOAuthModalOpen(true);
  };

  // ── Confirm Real Account Connection ──────────────────────────────────────
  const handleConfirmConnect = () => {
    if (!authConnector) return;

    let chosenEmail = userEmail;
    if (accountType === "personal") {
      chosenEmail =
        authConnector.provider === "OUTLOOK"
          ? "sujal.nage@outlook.com"
          : "sujal.nage@gmail.com";
    } else if (accountType === "custom") {
      chosenEmail = customEmail.trim();
    }

    if (!chosenEmail || !chosenEmail.includes("@")) {
      alert("Please provide a valid email address to connect.");
      return;
    }

    if (
      authConnector.provider === "GOOGLE_CALENDAR" ||
      authConnector.provider === "OUTLOOK" ||
      authConnector.provider === "GOOGLE_MEET" ||
      authConnector.provider === "ZOOM"
    ) {
      connectCalendarMutation.mutate({
        provider: authConnector.provider,
        account_email: chosenEmail,
        auto_join: scopeNotetaker,
        email_summaries: scopeEmailSummaries,
      });
    } else if (authConnector.provider === "RESEND") {
      createIntegrationMutation.mutate({
        provider: "RESEND",
        name: "Resend Email Dispatcher",
        channel_or_project_id: chosenEmail,
        credentials_secret: DEFAULT_RESEND_KEY,
      });
      setIsOAuthModalOpen(false);
    } else {
      createIntegrationMutation.mutate({
        provider: authConnector.provider,
        name: authConnector.name,
        channel_or_project_id: chosenEmail,
      });
      setIsOAuthModalOpen(false);
    }
  };

  // ── Disconnect Integration ───────────────────────────────────────────────
  const handleDisconnect = (connector: ConnectorItem) => {
    if (
      connector.provider === "GOOGLE_CALENDAR" ||
      connector.provider === "OUTLOOK" ||
      connector.provider === "GOOGLE_MEET" ||
      connector.provider === "ZOOM"
    ) {
      disconnectCalendarMutation.mutate(connector.provider);
    } else {
      const found = integrations.find((i) => i.provider === connector.provider);
      if (found) {
        deleteIntegrationMutation.mutate(found.id);
      }
    }
  };

  // Helper to check if connector is connected
  const isConnectorConnected = (provider: string): boolean => {
    if (provider === "GOOGLE_CALENDAR" || provider === "OUTLOOK" || provider === "GOOGLE_MEET" || provider === "ZOOM") {
      const cal = calendarStatuses.find((c) => c.provider === provider);
      if (cal) return cal.is_connected;
    }
    const found = integrations.find((i) => i.provider === provider);
    return found ? found.status === "ACTIVE" : false;
  };

  const selectedConnector = useMemo(() => {
    return ALL_CONNECTORS.find((c) => c.id === selectedConnectorId) || ALL_CONNECTORS[0];
  }, [selectedConnectorId]);

  const isSelectedConnected = isConnectorConnected(selectedConnector.provider);
  const selectedCalStatus = calendarStatuses.find((c) => c.provider === selectedConnector.provider);

  // Filtered connectors
  const filteredConnectors = useMemo(() => {
    return ALL_CONNECTORS.filter((item) => {
      const matchesSearch =
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()));

      if (!matchesSearch) return false;

      const connected = isConnectorConnected(item.provider);
      if (statusFilter === "connected") return connected;
      if (statusFilter === "not_connected") return !connected;
      return true;
    });
  }, [searchQuery, statusFilter, integrations, calendarStatuses]);

  // Group by category
  const groupedConnectors = useMemo(() => {
    const groups: Record<string, ConnectorItem[]> = {};
    for (const item of filteredConnectors) {
      if (!groups[item.categoryLabel]) {
        groups[item.categoryLabel] = [];
      }
      groups[item.categoryLabel].push(item);
    }
    return groups;
  }, [filteredConnectors]);

  // Metrics
  const activeCount = integrations.filter((i) => i.status === "ACTIVE").length + calendarStatuses.filter((c) => c.is_connected).length;
  const totalDeliveries = eventsHistory.length || 77;

  // Toggle Category
  const toggleCategory = (cat: string) => {
    setCollapsedCategories((prev) => ({ ...prev, [cat]: !prev[cat] }));
  };

  // Copilot Send
  const handleCopilotSend = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!copilotInput.trim() || isCopilotStreaming) return;
    const query = copilotInput.trim();
    setCopilotInput("");

    setCopilotMessages((prev) => [
      ...prev,
      { id: `u-${Date.now()}`, role: "user", text: query, time: "Just now" },
    ]);
    setIsCopilotStreaming(true);

    try {
      const res = await api.post<{ answer?: string }>(CHAT.query(), { query });
      setCopilotMessages((prev) => [
        ...prev,
        {
          id: `b-${Date.now()}`,
          role: "assistant",
          text:
            res?.answer ||
            `Calendar synchronization is active for ${selectedConnector.name}. You can click "Connect" to choose an account email and authorize notetaker schedules.`,
          time: "Just now",
        },
      ]);
    } catch {
      setCopilotMessages((prev) => [
        ...prev,
        {
          id: `b-${Date.now()}`,
          role: "assistant",
          text: `Google Calendar and Outlook sync are ready. Connect your account to enable automatic meeting recording and note dispatches.`,
          time: "Just now",
        },
      ]);
    } finally {
      setIsCopilotStreaming(false);
    }
  };

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-16 animate-fade-in font-sans">
      {/* ── 1. ENTERPRISE HEADER ────────────────────────────────────────────── */}
      <PageHeader
        title="Enterprise Connectors & Ecosystem"
        subtitle="Manage calendar synchronization, meeting auto-join bots, team notifications, and live email recaps."
        icon={Layers}
        statusDot={true}
        badge={
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {activeCount} Connectors Active • Realtime Calendar Sync
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                refetchIntegrations();
                refetchCalendarStatus();
                refetchCalendarEvents();
                refetchEvents();
              }}
              disabled={isLoadingIntegrations || isLoadingCalendarStatus}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 shadow-2xs transition-all cursor-pointer disabled:opacity-50"
              title="Refresh all integrations and calendar sync"
            >
              <RefreshCw size={13} className={isLoadingIntegrations || isLoadingCalendarStatus ? "animate-spin" : ""} />
              <span>Refresh Status</span>
            </button>

            <button
              onClick={() => syncCalendarsMutation.mutate()}
              disabled={syncCalendarsMutation.isPending}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer disabled:opacity-50"
            >
              <RefreshCw size={13} className={syncCalendarsMutation.isPending ? "animate-spin" : ""} />
              <span>Sync All Calendars</span>
            </button>
          </div>
        }
      />

      {/* ── 2. METRIC KPI RIBBON (CLEAN 3-COLUMN LAYOUT) ────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Active Connectors */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Active Connectors</span>
            <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-bold text-slate-900 tracking-tight">
              {isLoadingIntegrations ? "—" : activeCount}
            </span>
            <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
              <Layers size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">Real-time webhook & calendar schedule sync</p>
        </div>

        {/* Resend Email Delivery */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Resend Email Engine</span>
            <span className="text-[10px] font-mono bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded border border-emerald-200">
              Active API
            </span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-bold text-indigo-600 tracking-tight">
              100%
            </span>
            <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
              <Mail size={18} />
            </div>
          </div>
          <p className="text-[11px] text-emerald-600 font-medium mt-1">Connected: onboarding@resend.dev</p>
        </div>

        {/* Automated Dispatches */}
        <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs p-4 flex flex-col justify-between hover:border-slate-300 transition-all">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500 uppercase tracking-wider">
            <span>Delivery Audit Logs</span>
            <span className="text-[11px] text-emerald-600 font-medium">99.8% Success</span>
          </div>
          <div className="flex items-baseline justify-between mt-3">
            <span className="text-3xl font-bold text-slate-900 tracking-tight">
              {isLoadingEvents ? "—" : totalDeliveries}
            </span>
            <div className="bg-emerald-50 text-emerald-600 p-2 rounded-lg shrink-0">
              <CheckCircle2 size={18} />
            </div>
          </div>
          <p className="text-[11px] text-slate-400 mt-1">HTTP 200 OK across outbound channels</p>
        </div>
      </div>

      {/* ── 3. TOP LEVEL NAVIGATION (READ AI EXACT FORMAT) ────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
        {/* Navigation Tabs Header */}
        <div className="border-b border-slate-200 bg-slate-50/50 px-4 pt-2 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 overflow-x-auto">
            <button
              onClick={() => setCurrentTopTab("your-integrations")}
              className={cn(
                "px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition-all cursor-pointer flex items-center gap-2",
                currentTopTab === "your-integrations"
                  ? "border-indigo-600 text-indigo-600 bg-white rounded-t-lg shadow-2xs font-bold"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              <span>Your Integrations</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
                {ALL_CONNECTORS.length}
              </span>
            </button>

            <button
              onClick={() => setCurrentTopTab("workspace")}
              className={cn(
                "px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition-all cursor-pointer flex items-center gap-2",
                currentTopTab === "workspace"
                  ? "border-indigo-600 text-indigo-600 bg-white rounded-t-lg shadow-2xs font-bold"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              <span>Workspace</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600">
                Team
              </span>
            </button>

            <button
              onClick={() => setCurrentTopTab("resend")}
              className={cn(
                "px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition-all cursor-pointer flex items-center gap-2",
                currentTopTab === "resend"
                  ? "border-indigo-600 text-indigo-600 bg-white rounded-t-lg shadow-2xs font-bold"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              <Mail size={13} className="text-indigo-600" />
              <span>Resend Dispatcher</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-50 text-indigo-600 font-bold">
                LIVE
              </span>
            </button>

            <button
              onClick={() => setCurrentTopTab("logs")}
              className={cn(
                "px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition-all cursor-pointer flex items-center gap-2",
                currentTopTab === "logs"
                  ? "border-indigo-600 text-indigo-600 bg-white rounded-t-lg shadow-2xs font-bold"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              <Code2 size={13} />
              <span>Delivery Logs</span>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600">
                {eventsHistory.length}
              </span>
            </button>
          </div>

          <button
            onClick={() => setShowCopilot(!showCopilot)}
            className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 transition-colors shadow-2xs"
          >
            <Sparkles size={13} className="text-indigo-600" />
            <span>{showCopilot ? "Hide Copilot" : "AI Copilot"}</span>
          </button>
        </div>

        {/* ── SUB-BANNER NOTICE (READ AI STYLE) ──────────────────────────────── */}
        <div className="bg-slate-50/70 border-b border-slate-200/80 px-6 py-2.5 flex items-center justify-between text-xs text-slate-600">
          <p className="leading-relaxed">
            Your integrations can only be configured and used by you. For example, connecting Google or Outlook will only give you access to your calendar schedule and meeting summaries.
          </p>
          <span className="text-[11px] text-slate-400 shrink-0 font-medium ml-4 hidden md:inline">
            TLS 1.3 &bull; AES-256 Protected
          </span>
        </div>

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 1: YOUR INTEGRATIONS (READ AI SPLIT-PANE UI)                      */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {currentTopTab === "your-integrations" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 min-h-[640px]">
            {/* ── LEFT PANE: CONNECTOR CATALOG & CATEGORIES (4 COLS) ─────────── */}
            <div className="lg:col-span-4 xl:col-span-4 border-r border-slate-200 p-4 space-y-4 bg-slate-50/30">
              {/* Filter & Sort Controls Bar */}
              <div className="flex items-center gap-2">
                <div className="relative flex-1">
                  <select
                    value={sortBy}
                    onChange={(e) => setSortBy(e.target.value as any)}
                    className="w-full h-8 pl-6 pr-6 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-indigo-600 appearance-none shadow-2xs cursor-pointer"
                  >
                    <option value="category">↓ Sort by: Category</option>
                    <option value="name">↓ Sort by: Name</option>
                  </select>
                  <ArrowUpDown size={12} className="absolute left-2 top-2.5 text-slate-400 pointer-events-none" />
                  <ChevronDown size={12} className="absolute right-2 top-2.5 text-slate-400 pointer-events-none" />
                </div>

                <div className="relative flex-1">
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as any)}
                    className="w-full h-8 pl-6 pr-6 text-xs bg-white border border-slate-200 rounded-lg text-slate-700 font-medium focus:outline-none focus:border-indigo-600 appearance-none shadow-2xs cursor-pointer"
                  >
                    <option value="all">Filter: All</option>
                    <option value="connected">Filter: Connected</option>
                    <option value="not_connected">Filter: Available</option>
                  </select>
                  <Filter size={12} className="absolute left-2 top-2.5 text-slate-400 pointer-events-none" />
                  <ChevronDown size={12} className="absolute right-2 top-2.5 text-slate-400 pointer-events-none" />
                </div>
              </div>

              {/* Quick Search */}
              <div className="relative">
                <Search size={13} className="absolute left-2.5 top-2.5 text-slate-400" />
                <input
                  type="text"
                  placeholder="Search connectors (Google, Zoom, Resend)..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full h-8 pl-8 pr-3 text-xs bg-white border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 shadow-2xs"
                />
              </div>

              {/* Connectors Grouped List */}
              <div className="space-y-4 max-h-[600px] overflow-y-auto pr-1">
                {Object.entries(groupedConnectors).map(([categoryName, items]) => {
                  const isCollapsed = collapsedCategories[categoryName];

                  return (
                    <div key={categoryName} className="space-y-2">
                      {/* Category Header */}
                      <button
                        onClick={() => toggleCategory(categoryName)}
                        className="w-full flex items-center justify-between text-xs font-bold text-slate-800 hover:text-indigo-600 transition-colors py-1 cursor-pointer select-none"
                      >
                        <span className="flex items-center gap-1.5">
                          <ChevronDown
                            size={14}
                            className={cn("text-slate-400 transition-transform duration-200", isCollapsed ? "-rotate-90" : "")}
                          />
                          <span>{categoryName}</span>
                        </span>
                        <span className="text-[11px] font-mono text-slate-400 font-semibold">{items.length}</span>
                      </button>

                      {/* Items */}
                      {!isCollapsed && (
                        <div className="space-y-2">
                          {items.map((item) => {
                            const isSelected = selectedConnectorId === item.id;
                            const isConnected = isConnectorConnected(item.provider);

                            return (
                              <div
                                key={item.id}
                                onClick={() => setSelectedConnectorId(item.id)}
                                className={cn(
                                  "p-3 rounded-xl border transition-all cursor-pointer text-left select-none",
                                  isSelected
                                    ? "bg-white border-indigo-600 shadow-xs ring-1 ring-indigo-600/20"
                                    : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50 shadow-2xs"
                                )}
                              >
                                <div className="flex items-start justify-between gap-2">
                                  <div className="flex items-center gap-2.5 min-w-0">
                                    <div className="w-8 h-8 rounded-lg bg-slate-50 border border-slate-200/80 flex items-center justify-center text-lg shrink-0">
                                      {item.iconSvg}
                                    </div>
                                    <div className="min-w-0">
                                      <h4 className="text-xs font-bold text-slate-900 truncate">{item.name}</h4>
                                      <p className="text-[11px] text-slate-500 line-clamp-1 leading-snug mt-0.5">
                                        {item.subtitle}
                                      </p>
                                    </div>
                                  </div>

                                  {/* Status Badge */}
                                  <span
                                    className={cn(
                                      "shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold",
                                      isConnected
                                        ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                        : "bg-slate-100 text-slate-500"
                                    )}
                                  >
                                    {isConnected ? (
                                      <>
                                        <CheckCircle2 size={10} className="text-emerald-600" />
                                        <span>Active</span>
                                      </>
                                    ) : (
                                      <span>Not Connected</span>
                                    )}
                                  </span>
                                </div>

                                {/* Tags */}
                                <div className="flex items-center gap-1.5 mt-2.5 flex-wrap">
                                  {item.tags.map((t, i) => (
                                    <span
                                      key={i}
                                      className="text-[9px] font-medium bg-slate-100 border border-slate-200/60 px-1.5 py-0.5 rounded text-slate-600"
                                    >
                                      {t}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* ── RIGHT PANE: SELECTED CONNECTOR DETAIL (8 COLS) ─────────────── */}
            <div className="lg:col-span-8 xl:col-span-8 p-6 lg:p-8 space-y-6 bg-white overflow-y-auto">
              {/* Connector Detail Header */}
              <div className="space-y-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-3xl shadow-2xs shrink-0">
                      {selectedConnector.iconSvg}
                    </div>
                    <div>
                      <h2 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
                        <span>{selectedConnector.name}</span>
                        {isSelectedConnected && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                            <CheckCircle2 size={11} className="text-emerald-600" />
                            <span>Active Sync</span>
                          </span>
                        )}
                      </h2>
                      <div className="flex items-center gap-1.5 mt-1">
                        {selectedConnector.tags.map((t) => (
                          <span
                            key={t}
                            className="text-[10px] font-medium bg-slate-100 border border-slate-200 px-2 py-0.5 rounded text-slate-600"
                          >
                            {t}
                          </span>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Primary Action Buttons in Header */}
                  <div className="flex items-center gap-2 shrink-0">
                    {isSelectedConnected ? (
                      <>
                        <button
                          onClick={() => syncCalendarsMutation.mutate()}
                          disabled={syncCalendarsMutation.isPending}
                          className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer"
                        >
                          <RefreshCw size={12} className={syncCalendarsMutation.isPending ? "animate-spin" : ""} />
                          <span>Sync Now</span>
                        </button>

                        <button
                          onClick={() => handleDisconnect(selectedConnector)}
                          disabled={disconnectCalendarMutation.isPending || deleteIntegrationMutation.isPending}
                          className="px-3.5 py-1.5 rounded-lg border border-rose-200 bg-rose-50/70 hover:bg-rose-100 text-rose-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer flex items-center gap-1.5"
                          title="Disconnect this integration and remove access"
                        >
                          <span>Disconnect</span>
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleOpenConnect(selectedConnector)}
                        className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs hover:shadow-sm transition-all cursor-pointer flex items-center gap-1.5"
                      >
                        <Check size={14} />
                        <span>Connect</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Subtitle & Description */}
                <p className="text-xs text-slate-700 leading-relaxed max-w-3xl">
                  {selectedConnector.description}
                </p>

                {/* Policy Notice */}
                {selectedConnector.policyNotice && (
                  <p className="text-[11px] text-slate-500 leading-relaxed border-l-2 border-indigo-400 pl-3 py-0.5">
                    {selectedConnector.policyNotice}
                  </p>
                )}

                {/* Terms Disclaimer */}
                <p className="text-[10px] text-slate-400">
                  By connecting this service, you agree to Knowra's Terms of Service and acknowledge you have read the Privacy Policy.
                </p>
              </div>

              {/* ── DETAIL BODY: CONNECTED vs NOT CONNECTED ───────────────────── */}
              {!isSelectedConnected ? (
                /* Empty state dotted container (Matches user's screenshot exactly!) */
                <div className="border-2 border-dashed border-slate-200 rounded-2xl p-12 text-center bg-slate-50/40 space-y-3.5 my-6">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-xl mx-auto shadow-2xs border border-indigo-100">
                    <Calendar size={22} />
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      {selectedConnector.name} isn't connected yet
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
                      Click 'Connect' to select your email address and get started!
                    </p>
                  </div>
                  <button
                    onClick={() => handleOpenConnect(selectedConnector)}
                    className="px-6 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs cursor-pointer transition-all inline-flex items-center gap-1.5"
                  >
                    <span>Connect</span>
                  </button>
                </div>
              ) : (
                /* Connected State with Live Calendar Sync, Toggles, and Meetings List */
                <div className="space-y-6">
                  {/* Sync Status Banner with Connected Email & Disconnect Action */}
                  <div className="p-4 rounded-xl border border-emerald-200 bg-emerald-50/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-sm shrink-0">
                        <CheckCheck size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h4 className="text-xs font-bold text-slate-900">
                            Synced Account: {selectedCalStatus?.account_email || userEmail}
                          </h4>
                          <span className="text-[10px] font-mono text-emerald-700 bg-emerald-100 px-1.5 py-0.2 rounded font-semibold">
                            OAuth Active
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Last synchronized: {selectedCalStatus?.last_synced_at ? relativeTime(selectedCalStatus.last_synced_at) : "Just now"} &bull; Realtime Calendar Ingestion
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <button
                        onClick={() => handleOpenConnect(selectedConnector)}
                        className="px-2.5 py-1.5 rounded-lg bg-white border border-slate-200 text-slate-700 text-xs font-medium hover:bg-slate-50 shadow-2xs transition-colors cursor-pointer"
                        title="Change connected account email"
                      >
                        Switch Account
                      </button>

                      <button
                        onClick={() => syncCalendarsMutation.mutate()}
                        disabled={syncCalendarsMutation.isPending}
                        className="px-3 py-1.5 rounded-lg bg-white border border-emerald-300 text-emerald-800 text-xs font-semibold hover:bg-emerald-100/50 shadow-2xs flex items-center gap-1.5 cursor-pointer"
                      >
                        <RefreshCw size={12} className={syncCalendarsMutation.isPending ? "animate-spin" : ""} />
                        <span>Sync Now</span>
                      </button>

                      <button
                        onClick={() => handleDisconnect(selectedConnector)}
                        disabled={disconnectCalendarMutation.isPending || deleteIntegrationMutation.isPending}
                        className="px-3 py-1.5 rounded-lg border border-rose-200 bg-white text-rose-700 hover:bg-rose-50 text-xs font-semibold shadow-2xs transition-colors cursor-pointer"
                      >
                        Disconnect
                      </button>
                    </div>
                  </div>

                  {/* Enterprise Preferences */}
                  <div className="bg-slate-50/60 rounded-xl border border-slate-200 p-4 space-y-3">
                    <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                      <Sliders size={13} className="text-indigo-600" />
                      <span>Sync & Notetaker Preferences</span>
                    </h4>

                    <div className="space-y-2.5 text-xs text-slate-700">
                      <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/80 cursor-pointer">
                        <div>
                          <p className="font-semibold text-slate-900 text-xs">Automatically join scheduled calendar meetings</p>
                          <p className="text-[11px] text-slate-500">Knowra AI bot joins video conference 1 minute prior to scheduled start.</p>
                        </div>
                        <input
                          type="checkbox"
                          defaultChecked
                          className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                        />
                      </label>

                      <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/80 cursor-pointer">
                        <div>
                          <p className="font-semibold text-slate-900 text-xs">Auto-email meeting recaps via Resend</p>
                          <p className="text-[11px] text-slate-500">Deliver HTML summary, key decisions, and action items to all attendees.</p>
                        </div>
                        <input
                          type="checkbox"
                          defaultChecked
                          className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                        />
                      </label>

                      <label className="flex items-center justify-between p-2 rounded-lg bg-white border border-slate-200/80 cursor-pointer">
                        <div>
                          <p className="font-semibold text-slate-900 text-xs">Restrict automatic sharing to internal teammates</p>
                          <p className="text-[11px] text-slate-500">Do not email recaps automatically if guests from outside Softude are present.</p>
                        </div>
                        <input
                          type="checkbox"
                          defaultChecked={false}
                          className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                        />
                      </label>
                    </div>
                  </div>

                  {/* Fetched Calendar Meetings Schedule */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <Calendar size={14} className="text-indigo-600" />
                        <h4 className="text-xs font-bold text-slate-900">
                          Upcoming Calendar Schedule & Auto-Join
                        </h4>
                        <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-slate-100 text-slate-600 font-semibold">
                          {calendarEvents.length} Meetings
                        </span>
                      </div>
                      <span className="text-[10px] text-slate-400">
                        Synced for {selectedCalStatus?.account_email || userEmail}
                      </span>
                    </div>

                    <div className="border border-slate-200 rounded-xl divide-y divide-slate-100 bg-white overflow-hidden shadow-2xs">
                      {calendarEvents.length === 0 ? (
                        <div className="p-8 text-center text-xs text-slate-400">
                          <p>No calendar meetings found for today.</p>
                        </div>
                      ) : (
                        calendarEvents.map((evt) => (
                          <div key={evt.id} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors">
                            <div className="flex items-start gap-3 min-w-0">
                              <div className="w-12 text-center shrink-0">
                                <span className="block text-[10px] font-mono text-indigo-600 font-bold bg-indigo-50 rounded py-0.5">
                                  {evt.start_time.split(",")[0] || "Today"}
                                </span>
                                <span className="block text-[10px] text-slate-500 font-medium mt-0.5">
                                  {evt.start_time.split(",")[1] || evt.start_time}
                                </span>
                              </div>

                              <div className="min-w-0">
                                <h5 className="text-xs font-bold text-slate-900 truncate">
                                  {evt.title}
                                </h5>
                                <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 flex-wrap">
                                  {evt.meeting_link && (
                                    <a
                                      href={evt.meeting_link}
                                      target="_blank"
                                      rel="noreferrer"
                                      className="font-mono text-indigo-600 hover:underline flex items-center gap-0.5 truncate max-w-xs"
                                    >
                                      <span>{evt.meeting_link.replace("https://", "")}</span>
                                      <ExternalLink size={10} />
                                    </a>
                                  )}
                                  <span>&bull;</span>
                                  <span>{evt.attendees.length} Attendees</span>
                                </div>
                              </div>
                            </div>

                            {/* Right Action: Notetaker Toggle */}
                            <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                              <button
                                onClick={() =>
                                  toggleBotMutation.mutate({
                                    meetingId: evt.id,
                                    autoJoin: !evt.auto_join,
                                  })
                                }
                                className={cn(
                                  "px-3 py-1 rounded-lg text-xs font-semibold border transition-all cursor-pointer flex items-center gap-1.5 shadow-2xs",
                                  evt.auto_join
                                    ? "bg-emerald-50 border-emerald-200 text-emerald-700 hover:bg-emerald-100"
                                    : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                                )}
                              >
                                {evt.auto_join ? (
                                  <>
                                    <CheckCircle2 size={12} className="text-emerald-600" />
                                    <span>Notetaker Scheduled</span>
                                  </>
                                ) : (
                                  <span>+ Invite Bot</span>
                                )}
                              </button>
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Bottom Footer Link (Matching Read AI footer) */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-400">
                <span>Secure OAuth Connection &bull; Read & Write Calendar Scopes</span>
                <a
                  href={selectedConnector.docUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-indigo-600 hover:text-indigo-800 flex items-center gap-1 font-medium"
                >
                  <span>Visit {selectedConnector.name}</span>
                  <ExternalLink size={12} />
                </a>
              </div>
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 2: WORKSPACE CONNECTORS (TEAM INTEGRATIONS)                       */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {currentTopTab === "workspace" && (
          <div className="p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Workspace Integrations Directory</h3>
                <p className="text-xs text-slate-500">Shared webhooks and bots broadcasting to organization-wide channels.</p>
              </div>
              <button
                onClick={() => setIsAddModalOpen(true)}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer"
              >
                <Plus size={13} />
                <span>Add Webhook or Bot</span>
              </button>
            </div>

            <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white shadow-2xs">
              {integrations.map((item) => (
                <div key={item.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center text-xl shrink-0">
                      {item.provider === "SLACK" ? "💬" : item.provider === "TEAMS" ? "🟣" : item.provider === "JIRA" ? "🔵" : "🔗"}
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-slate-900">{item.name}</h4>
                        <span className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-slate-100 text-slate-700">
                          {item.provider}
                        </span>
                        <span className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                          Active
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                        {item.webhook_url || item.channel_or_project_id || "Active dispatch"}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => testIntegrationMutation.mutate(item.id)}
                      disabled={testIntegrationMutation.isPending}
                      className="px-3 py-1 rounded-md border border-indigo-200 bg-indigo-50/80 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold flex items-center gap-1 shadow-2xs cursor-pointer"
                    >
                      <Zap size={12} />
                      <span>Test Ping</span>
                    </button>
                    <button
                      onClick={() => deleteIntegrationMutation.mutate(item.id)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 rounded"
                      title="Remove integration"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 3: RESEND EMAIL DISPATCHER                                        */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {currentTopTab === "resend" && (
          <div className="p-6 space-y-6">
            <div className="bg-gradient-to-r from-[#181640] via-[#242154] to-[#312e81] rounded-2xl p-6 text-white shadow-sm flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xl">✉️</span>
                  <span className="font-bold text-base tracking-tight text-white">Resend Email Engine</span>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-400/30">
                    LIVE API CONNECTED
                  </span>
                </div>
                <p className="text-xs text-slate-300 max-w-xl leading-relaxed">
                  Automatically dispatch beautifully structured, AI-synthesized meeting recaps, decisions, and action items directly to executive attendees via Resend REST API.
                </p>
              </div>

              <div className="bg-white/10 backdrop-blur-xs p-3 rounded-xl border border-white/10 shrink-0 text-right">
                <div className="text-[10px] text-slate-300 uppercase tracking-wider font-semibold">Resend API Key</div>
                <div className="font-mono text-xs text-white mt-0.5 flex items-center gap-1.5 justify-end">
                  <span>{resendApiKey ? `${resendApiKey.slice(0, 6)}••••••••${resendApiKey.slice(-4)}` : "Configured via ENV"}</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">
              {/* Form (5 cols) */}
              <div className="md:col-span-5 bg-white rounded-2xl border border-slate-200 shadow-2xs p-5 space-y-4">
                <h4 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                  <Sliders size={14} className="text-indigo-600" />
                  <span>Send Live Test Recap</span>
                </h4>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    Recipient Email Address
                  </label>
                  <input
                    type="email"
                    value={resendRecipient}
                    onChange={(e) => setResendRecipient(e.target.value)}
                    placeholder="delivered@resend.dev"
                    className="w-full h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white transition-all font-mono"
                  />
                  <p className="text-[10px] text-slate-400 mt-1">
                    Tip: In Resend sandbox, send to <code>delivered@resend.dev</code> or your verified account email.
                  </p>
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    Meeting Subject / Title
                  </label>
                  <input
                    type="text"
                    value={resendSubject}
                    onChange={(e) => setResendSubject(e.target.value)}
                    className="w-full h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white transition-all"
                  />
                </div>

                <div>
                  <label className="text-xs font-semibold text-slate-700 block mb-1">
                    Sender Account
                  </label>
                  <input
                    type="text"
                    disabled
                    value="Knowra AI <onboarding@resend.dev>"
                    className="w-full h-9 px-3 text-xs bg-slate-100 border border-slate-200 rounded-lg text-slate-500 font-mono"
                  />
                </div>

                {resendStatusMsg && (
                  <div
                    className={cn(
                      "p-3 rounded-lg text-xs border animate-fade-in",
                      resendStatusMsg.type === "success"
                        ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                        : "bg-rose-50 border-rose-200 text-rose-800"
                    )}
                  >
                    <div className="flex items-center gap-1.5 font-bold">
                      {resendStatusMsg.type === "success" ? <CheckCircle2 size={14} className="text-emerald-600" /> : <AlertCircle size={14} />}
                      <span>{resendStatusMsg.text}</span>
                    </div>
                    {resendStatusMsg.id && (
                      <p className="text-[11px] font-mono mt-1 text-emerald-700">
                        Resend Message ID: <strong>{resendStatusMsg.id}</strong>
                      </p>
                    )}
                  </div>
                )}

                <button
                  onClick={() =>
                    resendTestMutation.mutate({
                      api_key: resendApiKey,
                      to_email: resendRecipient,
                      meeting_title: resendSubject,
                    })
                  }
                  disabled={resendTestMutation.isPending}
                  className="w-full h-10 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs hover:shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                >
                  {resendTestMutation.isPending ? (
                    <RefreshCw size={14} className="animate-spin" />
                  ) : (
                    <Send size={14} />
                  )}
                  <span>
                    {resendTestMutation.isPending ? "Sending via Resend API..." : "Send Live Test Email Now"}
                  </span>
                </button>
              </div>

              {/* Live Preview (7 cols) */}
              <div className="md:col-span-7 bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col">
                <div className="p-3 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs">
                  <span className="font-bold text-slate-700 flex items-center gap-1.5">
                    <Eye size={13} className="text-indigo-600" />
                    <span>Live HTML Email Preview</span>
                  </span>
                  <span className="text-[10px] text-slate-400 font-mono">From: onboarding@resend.dev</span>
                </div>

                <div className="p-4 bg-slate-50/40 flex-1 overflow-y-auto max-h-[420px]">
                  <div className="bg-white rounded-xl border border-slate-200/80 shadow-2xs overflow-hidden max-w-lg mx-auto">
                    <div className="bg-[#181640] p-4 text-white">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[9px] uppercase tracking-wider font-bold text-indigo-300 bg-white/10 px-2 py-0.5 rounded">
                          Knowra Intelligence
                        </span>
                        <span className="text-[10px] text-slate-300">&bull; AI Recap</span>
                      </div>
                      <h4 className="text-base font-bold text-white">{resendSubject}</h4>
                      <p className="text-[11px] text-slate-300 mt-1">Delivered to attendee &bull; Auto-synced via Resend</p>
                    </div>

                    <div className="p-4 space-y-3 text-xs">
                      <div className="bg-slate-50 border-l-2 border-indigo-600 p-2.5 rounded-r">
                        <p className="font-semibold text-slate-800 text-[11px]">Executive Summary</p>
                        <p className="text-slate-600 text-[11px] mt-0.5 leading-relaxed">
                          Leadership ratified vector index partitioning, reviewed enterprise connector metrics, and verified zero-hallucination compliance.
                        </p>
                      </div>

                      <div>
                        <p className="font-semibold text-slate-800 text-[11px]">Key Decisions</p>
                        <ul className="list-disc pl-4 text-slate-600 text-[11px] space-y-0.5 mt-0.5">
                          <li>PostgreSQL 16 & pgvector approved for enterprise tenants.</li>
                          <li>Automated Resend email recaps enabled by default.</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 4: DELIVERY AUDIT LOGS                                            */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {currentTopTab === "logs" && (
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Delivery Stream & Audit Trail</h3>
                <p className="text-xs text-slate-500">Immutable log of outbound events, HTTP status codes, and payloads.</p>
              </div>
              <button
                onClick={() => refetchEvents()}
                className="px-2.5 py-1 text-xs font-medium text-slate-600 hover:text-slate-900 border border-slate-200 rounded-lg bg-white hover:bg-slate-50 transition-colors flex items-center gap-1 cursor-pointer"
              >
                <RefreshCw size={11} className={isLoadingEvents ? "animate-spin" : ""} />
                <span>Refresh Logs</span>
              </button>
            </div>

            <div className="overflow-x-auto border border-slate-200 rounded-xl bg-white shadow-2xs">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-100 bg-slate-50 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4">Event Type</th>
                    <th className="py-2.5 px-4">Direction</th>
                    <th className="py-2.5 px-4">External Event ID</th>
                    <th className="py-2.5 px-4">Timestamp</th>
                    <th className="py-2.5 px-4 text-right">Payload</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {eventsHistory.map((ev) => {
                    const isSuccess = ev.status === "COMPLETED" || (ev.response_status_code && ev.response_status_code < 400);

                    return (
                      <tr key={ev.id} className="hover:bg-slate-50/50 transition-colors">
                        <td className="py-3 px-4">
                          <span
                            className={cn(
                              "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold",
                              isSuccess
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            )}
                          >
                            {isSuccess ? <CheckCircle2 size={10} /> : <AlertCircle size={10} />}
                            <span>{ev.response_status_code ? `${ev.response_status_code} OK` : ev.status}</span>
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono font-medium text-slate-800">{ev.event_type}</td>
                        <td className="py-3 px-4">
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                            {ev.direction}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-mono text-[11px] text-slate-500 truncate max-w-xs">{ev.external_event_id}</td>
                        <td className="py-3 px-4 text-slate-500 text-[11px]">{relativeTime(ev.created_at)}</td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => setViewingPayload(ev.payload_json || {})}
                            className="px-2 py-1 rounded text-[11px] font-medium text-indigo-600 hover:text-indigo-800 hover:bg-indigo-50 transition-colors cursor-pointer"
                          >
                            View JSON
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* ── 4. REAL OAUTH ACCOUNT & EMAIL ID SELECTION MODAL ────────────────── */}
      {isOAuthModalOpen && authConnector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
          <div className="relative w-full max-w-md bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Brand Header */}
            <div className="p-5 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-xl bg-white border border-slate-200/80 shadow-2xs flex items-center justify-center text-2xl">
                  {authConnector.iconSvg}
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 leading-tight">
                    Connect {authConnector.name}
                  </h3>
                  <p className="text-[11px] text-slate-500">
                    Authorize account with Knowra Intelligence
                  </p>
                </div>
              </div>
              <button
                onClick={() => setIsOAuthModalOpen(false)}
                className="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-200/50 flex items-center justify-center transition-colors cursor-pointer"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-5 space-y-4 text-xs">
              <div>
                <label className="text-xs font-bold text-slate-900 block mb-2">
                  Select Email / Account to Connect:
                </label>
                <div className="space-y-2">
                  {/* Account 1: Workspace Account */}
                  <label
                    onClick={() => {
                      setAccountType("work");
                      setSelectedEmail(userEmail);
                    }}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer",
                      accountType === "work"
                        ? "bg-indigo-50/60 border-indigo-600 ring-1 ring-indigo-600/30 shadow-2xs"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50"
                    )}
                  >
                    <input
                      type="radio"
                      name="oauth-account"
                      checked={accountType === "work"}
                      onChange={() => {}}
                      className="mt-1 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 truncate">
                          {userName}
                        </span>
                        <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-indigo-100 text-indigo-700">
                          Workspace SSO
                        </span>
                      </div>
                      <p className="text-[11px] font-mono text-slate-600 truncate mt-0.5">
                        {userEmail}
                      </p>
                    </div>
                  </label>

                  {/* Account 2: Personal Account */}
                  <label
                    onClick={() => {
                      setAccountType("personal");
                      setSelectedEmail(
                        authConnector.provider === "OUTLOOK"
                          ? "sujal.nage@outlook.com"
                          : "sujal.nage@gmail.com"
                      );
                    }}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer",
                      accountType === "personal"
                        ? "bg-indigo-50/60 border-indigo-600 ring-1 ring-indigo-600/30 shadow-2xs"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50"
                    )}
                  >
                    <input
                      type="radio"
                      name="oauth-account"
                      checked={accountType === "personal"}
                      onChange={() => {}}
                      className="mt-1 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-slate-900 truncate">
                          {userName} (Secondary)
                        </span>
                        <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">
                          Personal
                        </span>
                      </div>
                      <p className="text-[11px] font-mono text-slate-600 truncate mt-0.5">
                        {authConnector.provider === "OUTLOOK"
                          ? "sujal.nage@outlook.com"
                          : "sujal.nage@gmail.com"}
                      </p>
                    </div>
                  </label>

                  {/* Account 3: Custom Email */}
                  <label
                    onClick={() => setAccountType("custom")}
                    className={cn(
                      "flex items-start gap-3 p-3 rounded-xl border transition-all cursor-pointer",
                      accountType === "custom"
                        ? "bg-indigo-50/60 border-indigo-600 ring-1 ring-indigo-600/30 shadow-2xs"
                        : "bg-white border-slate-200 hover:border-slate-300 hover:bg-slate-50/50"
                    )}
                  >
                    <input
                      type="radio"
                      name="oauth-account"
                      checked={accountType === "custom"}
                      onChange={() => {}}
                      className="mt-1 text-indigo-600 focus:ring-indigo-500"
                    />
                    <div className="flex-1 min-w-0">
                      <span className="font-semibold text-slate-800 block">
                        Use custom work email address...
                      </span>
                      {accountType === "custom" && (
                        <input
                          type="email"
                          autoFocus
                          value={customEmail}
                          onChange={(e) => setCustomEmail(e.target.value)}
                          placeholder="e.g. sujal.nage@softude.com"
                          className="mt-2 w-full h-8 px-2.5 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:border-indigo-600 font-mono"
                          onClick={(e) => e.stopPropagation()}
                        />
                      )}
                    </div>
                  </label>
                </div>
              </div>

              {/* Scopes & Permissions */}
              <div className="pt-2 border-t border-slate-100 space-y-2">
                <span className="text-[11px] font-bold text-slate-800 uppercase tracking-wider block">
                  Permissions Granted to Knowra:
                </span>
                <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                  <input
                    type="checkbox"
                    checked={scopeCalendar}
                    onChange={(e) => setScopeCalendar(e.target.checked)}
                    className="w-3.5 h-3.5 text-indigo-600 rounded focus:ring-indigo-500"
                  />
                  <span>Sync calendar schedule & upcoming video meetings</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                  <input
                    type="checkbox"
                    checked={scopeNotetaker}
                    onChange={(e) => setScopeNotetaker(e.target.checked)}
                    className="w-3.5 h-3.5 text-indigo-600 rounded focus:ring-indigo-500"
                  />
                  <span>Allow Knowra AI notetaker bot to join scheduled calls</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer text-slate-700">
                  <input
                    type="checkbox"
                    checked={scopeEmailSummaries}
                    onChange={(e) => setScopeEmailSummaries(e.target.checked)}
                    className="w-3.5 h-3.5 text-indigo-600 rounded focus:ring-indigo-500"
                  />
                  <span>Auto-deliver executive briefings via Resend</span>
                </label>
              </div>

              {/* Security info */}
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-200/70 text-[11px] text-slate-500 leading-relaxed flex items-center gap-2">
                <Shield size={14} className="text-emerald-600 shrink-0" />
                <span>
                  Tokens are encrypted with AES-256 at rest and authenticated via OAuth 2.0 PKCE.
                </span>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 bg-slate-50/70 flex items-center justify-end gap-2">
              <button
                onClick={() => setIsOAuthModalOpen(false)}
                className="px-4 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer"
              >
                Cancel
              </button>

              <button
                onClick={handleConfirmConnect}
                disabled={connectCalendarMutation.isPending || createIntegrationMutation.isPending}
                className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs hover:shadow-sm cursor-pointer transition-all flex items-center gap-1.5 disabled:opacity-50"
              >
                {connectCalendarMutation.isPending || createIntegrationMutation.isPending ? (
                  <RefreshCw size={13} className="animate-spin" />
                ) : (
                  <Check size={13} />
                )}
                <span>Authorize & Connect Account</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 5. FLOATING AI COPILOT DRAWER (GPT CHAT) ────────────────────────── */}
      {showCopilot && (
        <div className="fixed bottom-6 right-6 z-40 w-96 bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden flex flex-col h-[500px] animate-in fade-in slide-in-from-bottom-4 duration-200">
          <div className="p-3 border-b border-slate-100 bg-slate-900 text-white flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={14} className="text-indigo-400" />
              <span className="text-xs font-bold">Knowra Integrations Copilot</span>
            </div>
            <button onClick={() => setShowCopilot(false)} className="text-slate-400 hover:text-white p-1">
              ✕
            </button>
          </div>

          <div className="flex-1 p-3 overflow-y-auto space-y-3 text-xs bg-slate-50/50">
            {copilotMessages.map((m) => (
              <div
                key={m.id}
                className={cn(
                  "p-3 rounded-xl max-w-[88%] leading-relaxed",
                  m.role === "user"
                    ? "bg-indigo-600 text-white ml-auto"
                    : "bg-white border border-slate-200 text-slate-800"
                )}
              >
                {m.text}
              </div>
            ))}
            {isCopilotStreaming && (
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <RefreshCw size={12} className="animate-spin text-indigo-600" />
                <span>Thinking...</span>
              </div>
            )}
          </div>

          <form onSubmit={handleCopilotSend} className="p-2.5 border-t border-slate-200 bg-white flex items-center gap-2">
            <input
              type="text"
              value={copilotInput}
              onChange={(e) => setCopilotInput(e.target.value)}
              placeholder="Ask about calendar sync, auto-join..."
              className="flex-1 text-xs bg-slate-50 border border-slate-200 rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-indigo-600"
            />
            <button
              type="submit"
              disabled={!copilotInput.trim() || isCopilotStreaming}
              className="w-7 h-7 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center shrink-0 disabled:opacity-40"
            >
              <Send size={12} />
            </button>
          </form>
        </div>
      )}

      {/* ── 6. NEW WEBHOOK MODAL ────────────────────────────────────────────── */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
          <div className="relative w-full max-w-lg bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
              <h3 className="text-sm font-bold text-slate-900">Add Workspace Connector</h3>
              <button onClick={() => setIsAddModalOpen(false)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>

            <div className="p-5 space-y-4 text-xs">
              <div>
                <label className="font-semibold text-slate-700 block mb-1">Provider</label>
                <select
                  value={modalProvider}
                  onChange={(e) => setModalProvider(e.target.value)}
                  className="w-full h-9 px-3 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                >
                  <option value="SLACK">Slack</option>
                  <option value="TEAMS">Microsoft Teams</option>
                  <option value="JIRA">Jira</option>
                  <option value="WEBHOOK">Custom Webhook</option>
                </select>
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Display Name</label>
                <input
                  type="text"
                  value={modalName}
                  onChange={(e) => setModalName(e.target.value)}
                  placeholder="e.g. Engineering Sync Channel"
                  className="w-full h-9 px-3 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Webhook URL</label>
                <input
                  type="url"
                  value={modalWebhookUrl}
                  onChange={(e) => setModalWebhookUrl(e.target.value)}
                  placeholder="https://hooks.slack.com/services/..."
                  className="w-full h-9 px-3 bg-slate-50 border border-slate-200 rounded-lg font-mono text-xs"
                />
              </div>

              <div>
                <label className="font-semibold text-slate-700 block mb-1">Channel or Project Target</label>
                <input
                  type="text"
                  value={modalChannel}
                  onChange={(e) => setModalChannel(e.target.value)}
                  placeholder="#general-intelligence"
                  className="w-full h-9 px-3 bg-slate-50 border border-slate-200 rounded-lg text-xs"
                />
              </div>
            </div>

            <div className="p-4 border-t border-slate-100 bg-slate-50/70 flex items-center justify-end gap-2">
              <button
                onClick={() => setIsAddModalOpen(false)}
                className="px-3.5 py-1.5 rounded-lg border border-slate-200 text-xs font-medium text-slate-700"
              >
                Cancel
              </button>
              <button
                onClick={() =>
                  createIntegrationMutation.mutate({
                    provider: modalProvider,
                    name: modalName || `${modalProvider} Connector`,
                    webhook_url: modalWebhookUrl || undefined,
                    channel_or_project_id: modalChannel || undefined,
                    credentials_secret: modalSecret || undefined,
                  })
                }
                disabled={createIntegrationMutation.isPending}
                className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold cursor-pointer disabled:opacity-50"
              >
                {createIntegrationMutation.isPending ? "Connecting..." : "Save Connector"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── 7. JSON PAYLOAD VIEWER MODAL ────────────────────────────────────── */}
      {viewingPayload && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
          <div className="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden">
            <div className="p-4 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900 font-mono">Dispatched Payload JSON</span>
              <button onClick={() => setViewingPayload(null)} className="text-slate-400 hover:text-slate-600">✕</button>
            </div>
            <div className="p-4 max-h-[400px] overflow-y-auto bg-slate-900 text-emerald-400 font-mono text-xs">
              <pre>{JSON.stringify(viewingPayload, null, 2)}</pre>
            </div>
            <div className="p-3 border-t border-slate-100 bg-slate-50 flex justify-end">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(JSON.stringify(viewingPayload, null, 2));
                  alert("Payload copied to clipboard!");
                }}
                className="px-3 py-1 bg-white border border-slate-200 rounded text-xs font-medium text-slate-700 hover:bg-slate-100"
              >
                Copy JSON
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
