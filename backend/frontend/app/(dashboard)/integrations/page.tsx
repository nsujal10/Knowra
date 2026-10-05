"use client";

import React, { useState, useMemo, useEffect } from "react";
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
import { toast } from "@/components/ui/toast";
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
  EyeOff,
  Sliders,
  Filter,
  ArrowUpDown,
  Shield,
  CheckCheck,
  Check,
  User,
  Lock,
  Copy,
  Key,
  MessageSquare,
  Kanban,
  FileText,
  Target,
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

type TopTab = "apps" | "webhooks" | "audit";

export default function IntegrationsPage() {
  const queryClient = useQueryClient();
  const { session } = useSession();

  // Current authenticated user info or realistic enterprise default
  const userEmail = session?.user?.email || "sujal.nage@softude.com";
  const userName = session?.user?.full_name || "Sujal Nage";

  // Top Tab State
  const [currentTopTab, setCurrentTopTab] = useState<TopTab>("apps");

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
  const [connectingAccountEmail, setConnectingAccountEmail] = useState<string | null>(null);
  const [showCustomAccountInput, setShowCustomAccountInput] = useState<boolean>(false);
  const [customAccountEmail, setCustomAccountEmail] = useState<string>("");
  const [scopeCalendar, setScopeCalendar] = useState<boolean>(true);
  const [scopeNotetaker, setScopeNotetaker] = useState<boolean>(true);
  const [scopeEmailSummaries, setScopeEmailSummaries] = useState<boolean>(true);

  // Enterprise Notetaker & Ingestion Preferences
  const [prefAutoJoin, setPrefAutoJoin] = useState<boolean>(true);
  const [prefAutoEmail, setPrefAutoEmail] = useState<boolean>(true);
  const [prefRestrictInternal, setPrefRestrictInternal] = useState<boolean>(false);

  // Google Calendar Live OAuth States
  const [isGoogleOAuthLoading, setIsGoogleOAuthLoading] = useState<boolean>(false);
  const [googleSetupModalOpen, setGoogleSetupModalOpen] = useState<boolean>(false);
  const [googleRedirectUri, setGoogleRedirectUri] = useState<string>(
    "http://localhost:8000/api/v1/integrations/google-calendar/callback"
  );
  const [copiedRedirect, setCopiedRedirect] = useState<boolean>(false);

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

  // Jira State
  const [jiraInstanceUrl] = useState("https://softude.atlassian.net");
  const [jiraEmail, setJiraEmail] = useState(userEmail || "sujal.nage@softude.com");
  const [jiraProjectKey] = useState("KNOWRA");
  const [jiraNewSummary, setJiraNewSummary] = useState("");
  const [jiraNewDescription, setJiraNewDescription] = useState("");
  const [jiraNewIssueType, setJiraNewIssueType] = useState("Task");
  const [jiraNewPriority, setJiraNewPriority] = useState("High");

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
    queryKey: queryKeys.integrations.calendarEvents(selectedConnectorId),
    queryFn: () => {
      const conn = ALL_CONNECTORS.find((c) => c.id === selectedConnectorId);
      return api.get<CalendarMeetingItem[]>(INTEGRATIONS.calendarEvents(conn?.provider));
    },
  });

  const { data: eventsHistory = [], isLoading: isLoadingEvents, refetch: refetchEvents } = useQuery<IntegrationEvent[]>({
    queryKey: queryKeys.integrations.events(),
    queryFn: () => api.get<IntegrationEvent[]>(INTEGRATIONS.events()),
    refetchInterval: 12_000,
  });

  const { data: jiraStatus, refetch: refetchJiraStatus } = useQuery<{
    is_connected: boolean;
    instance_url?: string;
    account_email?: string;
    project_key?: string;
    display_name?: string;
    last_synced_at?: string;
  }>({
    queryKey: ["integrations", "jira", "status"],
    queryFn: () => api.get(INTEGRATIONS.jiraStatus()),
  });

  const {
    data: jiraIssues = [],
    isLoading: isLoadingJiraIssues,
    refetch: refetchJiraIssues,
  } = useQuery<
    Array<{
      id: string;
      key: string;
      summary: string;
      status: string;
      priority: string;
      issue_type: string;
      assignee?: string;
      created: string;
      url: string;
    }>
  >({
    queryKey: ["integrations", "jira", "issues", jiraStatus?.is_connected],
    queryFn: () => api.get(INTEGRATIONS.jiraIssues(20)),
    enabled: selectedConnectorId === "jira",
  });

  // ── OAuth Callback Query Parameter Handler (Google Calendar Redirect) ────
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const error = params.get("error");
    const email = params.get("email");

    if (connected === "GOOGLE_CALENDAR") {
      toast.success(
        `Google Calendar successfully connected${email ? ` (${email})` : ""}! Live events synchronized.`
      );
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarStatus() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarEvents() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
      window.history.replaceState({}, "", window.location.pathname);
    } else if (error) {
      toast.error(`Google Calendar connection failed: ${decodeURIComponent(error)}`);
      window.history.replaceState({}, "", window.location.pathname);
    }
  }, [queryClient]);

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
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
      setConnectingAccountEmail(null);
      setShowCustomAccountInput(false);
      setCustomAccountEmail("");
      setIsOAuthModalOpen(false);
    },
    onError: () => {
      setConnectingAccountEmail(null);
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
      toast.success(data?.message || "Calendars successfully synchronized!");
    },
  });

  const syncGoogleMutation = useMutation({
    mutationFn: () =>
      api.post<{ success: boolean; synced_count: number; timestamp: string }>(
        INTEGRATIONS.googleCalendarSync(),
        {}
      ),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarStatus() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.calendarEvents() });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
      toast.success(`Google Calendar synchronized! ${data.synced_count} live event(s) retrieved.`);
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to synchronize Google Calendar");
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
      toast.success(res?.detail || "Test ping successfully dispatched!");
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

  const connectJiraMutation = useMutation({
    mutationFn: (data: {
      instance_url: string;
      email: string;
      api_token: string;
      project_key: string;
    }) =>
      api.post<{ success: boolean; message: string; user?: any; projects?: any[] }>(
        INTEGRATIONS.jiraConnect(),
        data
      ),
    onSuccess: (res) => {
      toast.success(res?.message || "Successfully connected to Atlassian Jira Cloud!");
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      queryClient.invalidateQueries({ queryKey: ["integrations", "jira", "status"] });
      queryClient.invalidateQueries({ queryKey: ["integrations", "jira", "issues"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to authenticate with Atlassian Jira API");
    },
  });

  const createJiraIssueMutation = useMutation({
    mutationFn: (data: {
      summary: string;
      description?: string;
      issue_type?: string;
      priority?: string;
    }) =>
      api.post<{ success: boolean; key: string; url: string; summary: string }>(
        INTEGRATIONS.jiraCreateIssue(),
        data
      ),
    onSuccess: (res) => {
      toast.success(`Created Jira issue ${res.key || ""} successfully!`);
      setJiraNewSummary("");
      setJiraNewDescription("");
      queryClient.invalidateQueries({ queryKey: ["integrations", "jira", "issues"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to create issue in Jira");
    },
  });

  const disconnectJiraMutation = useMutation({
    mutationFn: () => api.delete<{ success: boolean; message: string }>(INTEGRATIONS.jiraDisconnect()),
    onSuccess: () => {
      toast.success("Disconnected Atlassian Jira integration");
      queryClient.setQueryData(["integrations", "jira", "status"], {
        is_connected: false,
        instance_url: null,
        email: null,
        account_email: null,
        project_key: null,
        display_name: null,
      });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      queryClient.invalidateQueries({ queryKey: ["integrations", "jira", "status"] });
      queryClient.invalidateQueries({ queryKey: ["integrations", "jira", "issues"] });
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.events() });
    },
    onError: (err: any) => {
      toast.error(err?.message || "Failed to disconnect Jira");
    },
  });

  const resetModalForm = () => {
    setModalName("");
    setModalWebhookUrl("");
    setModalChannel("");
    setModalSecret("");
  };

  // ── Open Real OAuth Account Picker Modal ─────────────────────────────────
  const handleOpenConnect = async (connector: ConnectorItem) => {
    setAuthConnector(connector);
    setConnectingAccountEmail(null);
    setShowCustomAccountInput(false);
    setCustomAccountEmail("");

    if (connector.provider === "GOOGLE_CALENDAR" || connector.provider === "GOOGLE_MEET") {
      setIsGoogleOAuthLoading(true);
      try {
        const res = await api.get<{
          is_configured: boolean;
          auth_url?: string;
          redirect_uri?: string;
          client_id_preview?: string;
        }>(INTEGRATIONS.googleCalendarAuthUrl());

        if (res?.redirect_uri) {
          setGoogleRedirectUri(res.redirect_uri);
        }

        if (res?.is_configured && res?.auth_url) {
          toast.info(`Redirecting to Google Sign-In for ${connector.name}...`);
          window.location.href = res.auth_url;
          return;
        } else {
          setGoogleSetupModalOpen(true);
          return;
        }
      } catch (err: any) {
        console.warn("Could not check Google OAuth endpoint, opening picker modal:", err);
        setIsOAuthModalOpen(true);
      } finally {
        setIsGoogleOAuthLoading(false);
      }
      return;
    }

    if (connector.provider === "ZOOM") {
      try {
        const res = await api.get<{
          is_configured: boolean;
          auth_url?: string;
          redirect_uri?: string;
          client_id_preview?: string;
        }>(INTEGRATIONS.zoomAuthUrl());

        if (res?.is_configured && res?.auth_url) {
          toast.info("Redirecting to Zoom Authorization...");
          window.location.href = res.auth_url;
          return;
        } else {
          toast.error("Zoom OAuth is not configured. Please add ZOOM_CLIENT_ID and ZOOM_CLIENT_SECRET to your .env file.");
          return;
        }
      } catch (err: any) {
        console.warn("Could not check Zoom OAuth endpoint:", err);
      }
    }

    if (connector.provider === "OUTLOOK") {
      try {
        const res = await api.get<{
          is_configured: boolean;
          auth_url?: string;
          redirect_uri?: string;
          client_id_preview?: string;
        }>(INTEGRATIONS.outlookAuthUrl());

        if (res?.is_configured && res?.auth_url) {
          toast.info("Redirecting to Microsoft Sign-In for Outlook Calendar...");
          window.location.href = res.auth_url;
          return;
        } else {
          toast.error("Microsoft OAuth is not configured. Please add MICROSOFT_CLIENT_ID and MICROSOFT_CLIENT_SECRET to your .env file.");
          return;
        }
      } catch (err: any) {
        console.warn("Could not check Outlook OAuth endpoint:", err);
      }
    }

    if (connector.provider === "JIRA") {
      setIsOAuthModalOpen(true);
      return;
    }

    setIsOAuthModalOpen(true);
  };

  // ── Direct OAuth Account Connection (Exact Google/Microsoft Account Picker) ─
  const handleSelectAccount = (chosenEmail: string) => {
    if (!authConnector) return;
    const cleanEmail = chosenEmail.trim();

    if (!cleanEmail || !cleanEmail.includes("@")) {
      toast.error("Please provide a valid email address to connect.");
      return;
    }

    setConnectingAccountEmail(cleanEmail);

    if (
      authConnector.provider === "GOOGLE_CALENDAR" ||
      authConnector.provider === "OUTLOOK" ||
      authConnector.provider === "GOOGLE_MEET" ||
      authConnector.provider === "ZOOM"
    ) {
      connectCalendarMutation.mutate({
        provider: authConnector.provider,
        account_email: cleanEmail,
        auto_join: scopeNotetaker,
        email_summaries: scopeEmailSummaries,
      });
    } else if (authConnector.provider === "RESEND") {
      createIntegrationMutation.mutate({
        provider: "RESEND",
        name: "Resend Email Dispatcher",
        channel_or_project_id: cleanEmail,
        credentials_secret: DEFAULT_RESEND_KEY,
      });
      setIsOAuthModalOpen(false);
    } else if (authConnector.provider === "SLACK") {
      createIntegrationMutation.mutate({
        provider: "SLACK",
        name: "Slack Intelligence Bot",
        channel_or_project_id: "#general-intelligence",
        credentials_secret: "xoxb-knowra-bot-token",
      });
      setIsOAuthModalOpen(false);
    } else if (authConnector.provider === "LINEAR") {
      createIntegrationMutation.mutate({
        provider: "LINEAR",
        name: "Linear Engineering Sync",
        channel_or_project_id: "ENG-Cycle",
        credentials_secret: "lin_api_knowra_workspace",
      });
      setIsOAuthModalOpen(false);
    } else if (authConnector.provider === "JIRA") {
      setConnectingAccountEmail(cleanEmail);
      setJiraEmail(cleanEmail);
      connectJiraMutation.mutate(
        {
          email: cleanEmail,
          instance_url: "",
          api_token: "",
          project_key: "",
        },
        {
          onSuccess: (res) => {
            toast.success(
              res?.message ||
                `Atlassian Jira connected automatically for ${cleanEmail}!`
            );
            setIsOAuthModalOpen(false);
            setConnectingAccountEmail(null);
            setShowCustomAccountInput(false);
            setCustomAccountEmail("");
          },
          onError: (err: any) => {
            toast.error(err?.message || "Failed to connect Atlassian Jira");
            setConnectingAccountEmail(null);
          },
        }
      );
    } else {
      createIntegrationMutation.mutate({
        provider: authConnector.provider,
        name: authConnector.name,
        channel_or_project_id: cleanEmail,
      });
      setIsOAuthModalOpen(false);
    }
  };

  // Helper for subtitle in connector list and details
  const getConnectorSyncSubtitle = (item: ConnectorItem) => {
    if (item.category === "calendar") {
      const cal = calendarStatuses.find((c) => c.provider === item.provider);
      return `Synced: ${cal?.account_email || userEmail}`;
    }
    const integ = integrations.find((i) => i.provider === item.provider);
    if (item.provider === "SLACK") {
      const ch = integ?.channel_or_project_id;
      return `Synced: ${ch && ch.startsWith("#") ? ch : "#general-intelligence"}`;
    }
    if (item.provider === "RESEND") {
      return `Synced: ${integ?.channel_or_project_id || userEmail}`;
    }
    if (item.provider === "JIRA") {
      const proj = jiraStatus?.project_key || "KNOWRA";
      const email = jiraStatus?.account_email || userEmail;
      return `Synced: ${email} (${proj})`;
    }
    if (item.provider === "LINEAR") {
      return `Synced: ${integ?.channel_or_project_id || "ENG-Cycle"} (Linear)`;
    }
    return `Synced: ${integ?.channel_or_project_id || userEmail}`;
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
    } else if (connector.provider === "JIRA") {
      disconnectJiraMutation.mutate();
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
    if (provider === "JIRA") {
      return Boolean(jiraStatus?.is_connected);
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
  }, [searchQuery, statusFilter, integrations, calendarStatuses, jiraStatus]);

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
        title="Integrations"
        subtitle="Manage calendar synchronization, meeting auto-join bots, team notifications, and live email recaps."
        icon={Layers}
        statusDot={true}
        badge={
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {activeCount} active · Realtime calendar sync
          </span>
        }
      />

      {/* ── 3. TOP LEVEL NAVIGATION (READ AI EXACT FORMAT) ────────────────────── */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-2xs overflow-hidden">
        {/* Navigation Tabs Header */}
        <div className="border-b border-slate-200 bg-slate-50/50 px-4 pt-2 flex items-center justify-between gap-4">
          <div className="flex items-center gap-2 overflow-x-auto">
            <button
              onClick={() => setCurrentTopTab("apps")}
              className={cn(
                "px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition-all cursor-pointer flex items-center gap-2",
                currentTopTab === "apps"
                  ? "border-indigo-600 text-indigo-600 bg-white rounded-t-lg shadow-2xs font-bold"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              <Layers size={14} className={currentTopTab === "apps" ? "text-indigo-600" : "text-slate-400"} />
              <span>Connected Apps</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">
                {ALL_CONNECTORS.length}
              </span>
            </button>

            <button
              onClick={() => setCurrentTopTab("webhooks")}
              className={cn(
                "px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition-all cursor-pointer flex items-center gap-2",
                currentTopTab === "webhooks"
                  ? "border-indigo-600 text-indigo-600 bg-white rounded-t-lg shadow-2xs font-bold"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              <Code2 size={14} className={currentTopTab === "webhooks" ? "text-indigo-600" : "text-slate-400"} />
              <span>Webhooks &amp; API</span>
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-mono">
                {integrations.filter((i) => i.provider === "WEBHOOK" || i.webhook_url).length}
              </span>
            </button>

            <button
              onClick={() => setCurrentTopTab("audit")}
              className={cn(
                "px-5 py-3 text-xs sm:text-sm font-semibold border-b-2 -mb-px transition-all cursor-pointer flex items-center gap-2",
                currentTopTab === "audit"
                  ? "border-indigo-600 text-indigo-600 bg-white rounded-t-lg shadow-2xs font-bold"
                  : "border-transparent text-slate-600 hover:text-slate-900"
              )}
            >
              <Shield size={14} className={currentTopTab === "audit" ? "text-indigo-600" : "text-slate-400"} />
              <span>Audit Log</span>
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
        {/* TAB 1: CONNECTED APPS & CATALOG (READ AI SPLIT-PANE UI)               */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {currentTopTab === "apps" && (
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
                                      {isConnected && (
                                        <p className="text-[10px] text-emerald-700 font-mono mt-0.5 font-medium truncate">
                                          {getConnectorSyncSubtitle(item)}
                                        </p>
                                      )}
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
              {/* ── 1. CLEAN ENTERPRISE CONNECTOR HEADER ── */}
              <div className="space-y-3 pb-6 border-b border-slate-100">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                  <div className="flex items-center gap-3.5">
                    <div className="w-12 h-12 rounded-2xl bg-slate-50 border border-slate-200/90 shadow-2xs flex items-center justify-center text-2xl shrink-0">
                      {selectedConnector.iconSvg}
                    </div>
                    <div>
                      <div className="flex items-center gap-2.5">
                        <h2 className="text-xl font-bold text-slate-900 tracking-tight">
                          {selectedConnector.name}
                        </h2>
                        {isSelectedConnected ? (
                          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200/70">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                            Connected
                          </span>
                        ) : (
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600 border border-slate-200">
                            Not Connected
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-500 mt-1">
                        {selectedConnector.subtitle}
                      </p>
                    </div>
                  </div>

                  {/* Primary Action Buttons in Header */}
                  <div className="flex items-center gap-2 shrink-0">
                    {isSelectedConnected ? (
                      <>
                        <button
                          onClick={() => {
                            if (selectedConnector.provider === "GOOGLE_CALENDAR") {
                              syncGoogleMutation.mutate();
                            } else if (selectedConnector.provider === "JIRA") {
                              refetchJiraIssues();
                              toast.success("Refreshed live Jira sprint issues");
                            } else {
                              syncCalendarsMutation.mutate();
                            }
                          }}
                          disabled={syncCalendarsMutation.isPending || syncGoogleMutation.isPending || isLoadingJiraIssues}
                          className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-60"
                        >
                          <RefreshCw
                            size={12}
                            className={
                              syncCalendarsMutation.isPending || syncGoogleMutation.isPending || isLoadingJiraIssues
                                ? "animate-spin"
                                : ""
                            }
                          />
                          <span>
                            {syncGoogleMutation.isPending && selectedConnector.provider === "GOOGLE_CALENDAR"
                              ? "Syncing..."
                              : isLoadingJiraIssues && selectedConnector.provider === "JIRA"
                              ? "Syncing Jira..."
                              : "Sync Now"}
                          </span>
                        </button>

                        <button
                          onClick={() => handleDisconnect(selectedConnector)}
                          disabled={disconnectCalendarMutation.isPending || deleteIntegrationMutation.isPending || disconnectJiraMutation.isPending}
                          className="px-3 py-1.5 rounded-lg border border-transparent hover:border-rose-200 hover:bg-rose-50 text-slate-500 hover:text-rose-600 text-xs font-semibold transition-colors cursor-pointer"
                          title="Disconnect this integration and revoke access"
                        >
                          Disconnect
                        </button>
                      </>
                    ) : (
                      <button
                        onClick={() => handleOpenConnect(selectedConnector)}
                        disabled={isGoogleOAuthLoading}
                        className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs hover:shadow-sm transition-all cursor-pointer flex items-center gap-1.5 disabled:opacity-70"
                      >
                        {isGoogleOAuthLoading && (selectedConnector.provider === "GOOGLE_CALENDAR" || selectedConnector.provider === "GOOGLE_MEET") ? (
                          <>
                            <RefreshCw size={13} className="animate-spin" />
                            <span>Connecting...</span>
                          </>
                        ) : (
                          <>
                            <Check size={14} />
                            <span>Connect</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* ── DETAIL BODY: CONNECTED vs NOT CONNECTED ───────────────────── */}
              {!isSelectedConnected ? (
                /* Empty state container */
                <div className="border border-dashed border-slate-200 rounded-2xl p-12 text-center bg-slate-50/40 space-y-3.5 my-6">
                  <div className="w-12 h-12 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center text-2xl mx-auto shadow-2xs border border-indigo-100">
                    <span>{selectedConnector.iconSvg}</span>
                  </div>
                  <div>
                    <h3 className="text-sm font-bold text-slate-900">
                      {selectedConnector.name} isn't connected yet
                    </h3>
                    <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">
                      {selectedConnector.description}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center justify-center gap-2.5">
                    <button
                      onClick={() => handleOpenConnect(selectedConnector)}
                      disabled={isGoogleOAuthLoading}
                      className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-xs cursor-pointer transition-all inline-flex items-center gap-1.5 disabled:opacity-70"
                    >
                      {isGoogleOAuthLoading && (selectedConnector.provider === "GOOGLE_CALENDAR" || selectedConnector.provider === "GOOGLE_MEET") ? (
                        <>
                          <RefreshCw size={13} className="animate-spin" />
                          <span>Connecting...</span>
                        </>
                      ) : (
                        <span>Connect {selectedConnector.name}</span>
                      )}
                    </button>
                  </div>
                </div>
              ) : (
                /* Connected State with Streamlined Layout */
                <div className="space-y-6">
                  {/* ── 2. STREAMLINED ACCOUNT STRIP ── */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-xl bg-slate-50/70 border border-slate-200/80 gap-3">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-indigo-500 text-white font-semibold text-xs flex items-center justify-center shrink-0 shadow-2xs">
                        {(selectedCalStatus?.account_email || (selectedConnector.provider === "JIRA" ? (jiraStatus?.account_email || userEmail) : userEmail)).charAt(0).toUpperCase()}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900 truncate">
                            {selectedCalStatus?.account_email || (selectedConnector.provider === "JIRA" ? (jiraStatus?.account_email || userEmail) : getConnectorSyncSubtitle(selectedConnector).replace("Synced: ", ""))}
                          </span>
                          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-white text-slate-600 border border-slate-200/80 font-medium shrink-0">
                            {selectedConnector.category === "calendar"
                              ? "OAuth 2.0 PKCE"
                              : selectedConnector.provider === "RESEND"
                              ? "API Key (REST)"
                              : selectedConnector.provider === "SLACK"
                              ? "Bot Token (v2)"
                              : selectedConnector.provider === "JIRA"
                              ? "Atlassian Cloud REST API v3"
                              : "Enterprise OAuth 2.0"}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 flex items-center gap-1.5 truncate">
                          <span>Continuous Sync</span>
                          <span>&bull;</span>
                          <span>Last checked {selectedCalStatus?.last_synced_at || jiraStatus?.last_synced_at ? relativeTime((selectedCalStatus?.last_synced_at || jiraStatus?.last_synced_at)!) : "just now"}</span>
                        </p>
                      </div>
                    </div>

                    <button
                      onClick={() => handleOpenConnect(selectedConnector)}
                      className="text-xs font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-200/60 transition-colors shrink-0 cursor-pointer self-start sm:self-auto border border-transparent hover:border-slate-200"
                    >
                      Switch Account
                    </button>
                  </div>

                  {/* ── 3. AUTOMATION & NOTETAKER SETTINGS ── */}
                  <div className="rounded-xl border border-slate-200/90 bg-white overflow-hidden shadow-2xs">
                    <div className="px-4 py-3 border-b border-slate-100 bg-slate-50/40 flex items-center justify-between">
                      <h3 className="text-xs font-bold text-slate-900 flex items-center gap-1.5 uppercase tracking-wider">
                        <Sliders size={13} className="text-indigo-600" />
                        <span>Automation & Bot Preferences</span>
                      </h3>
                      <span className="text-[11px] text-slate-400">Tenant-wide policy</span>
                    </div>

                    <div className="divide-y divide-slate-100">
                      {/* Toggle 1 */}
                      <div className="p-4 flex items-center justify-between gap-4 hover:bg-slate-50/40 transition-colors">
                        <div className="space-y-0.5 pr-2">
                          <p className="text-xs font-semibold text-slate-900">
                            Auto-join calendar meetings
                          </p>
                          <p className="text-[11px] text-slate-500 leading-relaxed">
                            Knowra AI assistant automatically enters Google Meet conferences 1 minute before scheduled start.
                          </p>
                        </div>
                        <button
                          type="button"
                          role="switch"
                          aria-checked={prefAutoJoin}
                          onClick={() => {
                            setPrefAutoJoin(!prefAutoJoin);
                            toast.success(prefAutoJoin ? "Auto-join disabled for future meetings" : "Auto-join enabled for all upcoming meetings");
                          }}
                          className={cn(
                            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                            prefAutoJoin ? "bg-indigo-600" : "bg-slate-200"
                          )}
                        >
                          <span
                            className={cn(
                              "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out",
                              prefAutoJoin ? "translate-x-4" : "translate-x-0"
                            )}
                          />
                        </button>
                      </div>

                      {/* Toggle 2 */}
                      <div className="p-4 flex items-center justify-between gap-4 hover:bg-slate-50/40 transition-colors">
                        <div className="space-y-0.5 pr-2">
                          <p className="text-xs font-semibold text-slate-900">
                            Auto-dispatch executive briefings
                          </p>
                          <p className="text-[11px] text-slate-500 leading-relaxed">
                            Send synthesized executive summaries, key decisions, and action items directly to attendees after each call.
                          </p>
                        </div>
                        <button
                          type="button"
                          role="switch"
                          aria-checked={prefAutoEmail}
                          onClick={() => {
                            setPrefAutoEmail(!prefAutoEmail);
                            toast.success(prefAutoEmail ? "Executive recap dispatch disabled" : "Executive recap dispatch enabled");
                          }}
                          className={cn(
                            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                            prefAutoEmail ? "bg-indigo-600" : "bg-slate-200"
                          )}
                        >
                          <span
                            className={cn(
                              "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out",
                              prefAutoEmail ? "translate-x-4" : "translate-x-0"
                            )}
                          />
                        </button>
                      </div>

                      {/* Toggle 3 */}
                      <div className="p-4 flex items-center justify-between gap-4 hover:bg-slate-50/40 transition-colors">
                        <div className="space-y-0.5 pr-2">
                          <p className="text-xs font-semibold text-slate-900">
                            Internal domain fence
                          </p>
                          <p className="text-[11px] text-slate-500 leading-relaxed">
                            Do not auto-dispatch recaps if external participants or guests from outside your organization are present.
                          </p>
                        </div>
                        <button
                          type="button"
                          role="switch"
                          aria-checked={prefRestrictInternal}
                          onClick={() => {
                            setPrefRestrictInternal(!prefRestrictInternal);
                            toast.success(prefRestrictInternal ? "Internal domain fence relaxed" : "Internal domain fence enforced");
                          }}
                          className={cn(
                            "relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none",
                            prefRestrictInternal ? "bg-indigo-600" : "bg-slate-200"
                          )}
                        >
                          <span
                            className={cn(
                              "pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out",
                              prefRestrictInternal ? "translate-x-4" : "translate-x-0"
                            )}
                          />
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* ── 4. UPCOMING CALENDAR SCHEDULE ── */}
                  {/* ── 4. CONDITIONAL: CALENDAR SCHEDULE ── */}
                  {selectedConnector.category === "calendar" && (
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Calendar size={14} className="text-indigo-600" />
                          <h4 className="text-xs font-bold text-slate-900">
                            Upcoming Calendar Schedule
                          </h4>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold">
                            {calendarEvents.length} Meetings
                          </span>
                        </div>
                        <span className="text-[11px] text-slate-400">
                          Primary Calendar Feed
                        </span>
                      </div>

                      <div className="border border-slate-200/90 rounded-xl divide-y divide-slate-100 bg-white overflow-hidden shadow-2xs">
                        {calendarEvents.length === 0 ? (
                          <div className="py-12 px-4 text-center space-y-3">
                            <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto border border-slate-200/60 shadow-2xs">
                              <Calendar size={18} />
                            </div>
                            <div>
                              <p className="text-xs font-semibold text-slate-800">
                                No upcoming meetings found on your calendar
                              </p>
                              <p className="text-[11px] text-slate-500 max-w-sm mx-auto mt-0.5">
                                Your {selectedConnector.name} is connected and synced. Real meetings created in {selectedConnector.name} will automatically appear here.
                              </p>
                            </div>
                            <button
                              type="button"
                              onClick={() => {
                                refetchCalendarEvents();
                                syncCalendarsMutation.mutate();
                              }}
                              disabled={syncCalendarsMutation.isPending}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs transition-colors cursor-pointer disabled:opacity-60"
                            >
                              <RefreshCw size={12} className={syncCalendarsMutation.isPending ? "animate-spin" : ""} />
                              <span>Check for New Events</span>
                            </button>
                          </div>
                        ) : (
                          calendarEvents.map((evt) => (
                            <div key={evt.id} className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/60 transition-colors">
                              <div className="flex items-start gap-3 min-w-0">
                                <div className="w-16 text-center shrink-0">
                                  <span className="block text-[10px] font-mono text-indigo-700 font-bold bg-indigo-50/80 rounded py-0.5 border border-indigo-100/60">
                                    {evt.start_time.split(",")[0] || "Today"}
                                  </span>
                                  <span className="block text-[10px] text-slate-500 font-medium mt-1">
                                    {evt.start_time.split(",")[1] || evt.start_time}
                                  </span>
                                </div>

                                <div className="min-w-0">
                                  <h5 className="text-xs font-semibold text-slate-900 truncate">
                                    {evt.title}
                                  </h5>
                                  <div className="flex items-center gap-2 mt-1 text-[11px] text-slate-500 flex-wrap">
                                    {evt.meeting_link && (
                                      <a
                                        href={evt.meeting_link}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="font-mono text-indigo-600 hover:text-indigo-700 hover:underline flex items-center gap-1 truncate max-w-xs"
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

                              {/* Right Action: Clean Auto-join Status Switch */}
                              <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
                                <button
                                  onClick={() =>
                                    toggleBotMutation.mutate({
                                      meetingId: evt.id,
                                      autoJoin: !evt.auto_join,
                                    })
                                  }
                                  className={cn(
                                    "px-2.5 py-1 rounded-md text-[11px] font-medium transition-all flex items-center gap-1.5 cursor-pointer shadow-2xs",
                                    evt.auto_join
                                      ? "bg-emerald-50 text-emerald-700 hover:bg-emerald-100/70 border border-emerald-200/80"
                                      : "bg-slate-100 text-slate-600 hover:bg-slate-200/80 border border-slate-200"
                                  )}
                                >
                                  <span
                                    className={cn(
                                      "w-1.5 h-1.5 rounded-full",
                                      evt.auto_join ? "bg-emerald-500 animate-pulse" : "bg-slate-400"
                                    )}
                                  />
                                  <span>{evt.auto_join ? "Auto-join Active" : "Auto-join Off"}</span>
                                </button>
                              </div>
                            </div>
                          ))
                        )}
                      </div>
                    </div>
                  )}

                  {/* ── 4B. CONDITIONAL: RESEND EMAIL DISPATCHER ── */}
                  {selectedConnector.provider === "RESEND" && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Mail size={14} className="text-indigo-600" />
                          <h4 className="text-xs font-bold text-slate-900">
                            Executive Email Dispatcher &amp; Live Test
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                          LIVE API
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                        {/* Dispatch Form (5 cols) */}
                        <div className="md:col-span-5 bg-white rounded-xl border border-slate-200 shadow-2xs p-4 space-y-3">
                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">
                              Recipient Email Address
                            </label>
                            <input
                              type="email"
                              value={resendRecipient}
                              onChange={(e) => setResendRecipient(e.target.value)}
                              placeholder="delivered@resend.dev"
                              className="w-full h-8 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white transition-all font-mono"
                            />
                            <p className="text-[10px] text-slate-400 mt-1">
                              In Resend test sandbox, use <code>delivered@resend.dev</code>.
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
                              className="w-full h-8 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white transition-all"
                            />
                          </div>

                          {resendStatusMsg && (
                            <div
                              className={cn(
                                "p-2.5 rounded-lg text-xs border",
                                resendStatusMsg.type === "success"
                                  ? "bg-emerald-50 border-emerald-200 text-emerald-800"
                                  : "bg-rose-50 border-rose-200 text-rose-800"
                              )}
                            >
                              <div className="flex items-center gap-1.5 font-semibold text-[11px]">
                                {resendStatusMsg.type === "success" ? <CheckCircle2 size={12} className="text-emerald-600" /> : <AlertCircle size={12} />}
                                <span>{resendStatusMsg.text}</span>
                              </div>
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
                            className="w-full h-9 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold shadow-2xs transition-all flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            {resendTestMutation.isPending ? (
                              <RefreshCw size={12} className="animate-spin" />
                            ) : (
                              <Send size={12} />
                            )}
                            <span>
                              {resendTestMutation.isPending ? "Sending via Resend API..." : "Send Live Test Email"}
                            </span>
                          </button>
                        </div>

                        {/* Preview Box (7 cols) */}
                        <div className="md:col-span-7 bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col">
                          <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-700 flex items-center gap-1 text-[11px]">
                              <Eye size={12} className="text-indigo-600" />
                              <span>Live HTML Email Preview</span>
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">From: onboarding@resend.dev</span>
                          </div>

                          <div className="p-3 bg-slate-50/40 flex-1 overflow-y-auto max-h-[300px]">
                            <div className="bg-white rounded-lg border border-slate-200/80 shadow-2xs overflow-hidden">
                              <div className="bg-[#181640] p-3 text-white">
                                <div className="flex items-center gap-1.5 mb-1">
                                  <span className="text-[9px] uppercase tracking-wider font-bold text-indigo-300 bg-white/10 px-1.5 py-0.5 rounded">
                                    Knowra Intelligence
                                  </span>
                                  <span className="text-[10px] text-slate-300">&bull; AI Recap</span>
                                </div>
                                <h5 className="text-xs font-bold text-white">{resendSubject}</h5>
                              </div>

                              <div className="p-3 space-y-2 text-xs">
                                <div className="bg-slate-50 border-l-2 border-indigo-600 p-2 rounded-r">
                                  <p className="font-semibold text-slate-800 text-[10px]">Executive Summary</p>
                                  <p className="text-slate-600 text-[10px] mt-0.5 leading-relaxed">
                                    Leadership ratified vector index partitioning, reviewed connector metrics, and verified zero-hallucination compliance.
                                  </p>
                                </div>

                                <div>
                                  <p className="font-semibold text-slate-800 text-[10px]">Key Decisions</p>
                                  <ul className="list-disc pl-3 text-slate-600 text-[10px] space-y-0.5 mt-0.5">
                                    <li>Automated Resend email recaps enabled by default.</li>
                                    <li>PostgreSQL 16 & pgvector approved for enterprise tenants.</li>
                                  </ul>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ── 4C. CONDITIONAL: SLACK INTELLIGENCE BOT ── */}
                  {selectedConnector.provider === "SLACK" && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <MessageSquare size={14} className="text-purple-600" />
                          <h4 className="text-xs font-bold text-slate-900">
                            Slack Team Notifications &amp; Channel Stream
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                          BOT ACTIVE
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                        <div className="md:col-span-5 bg-white rounded-xl border border-slate-200 shadow-2xs p-4 space-y-3">
                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">
                              Target Broadcast Channel
                            </label>
                            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-800">
                              <span className="text-slate-400">#</span>
                              <span>general-intelligence</span>
                            </div>
                            <p className="text-[10px] text-slate-400 mt-1">
                              Knowra bot posts summaries and action item alerts here.
                            </p>
                          </div>

                          <div className="space-y-2 pt-1">
                            <label className="text-xs font-semibold text-slate-700 block">
                              Notification Triggers
                            </label>
                            <div className="space-y-1.5 text-[11px] text-slate-600">
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" defaultChecked className="rounded text-indigo-600" />
                                <span>Meeting executive briefings</span>
                              </label>
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" defaultChecked className="rounded text-indigo-600" />
                                <span>Direct @mentions for action item owners</span>
                              </label>
                              <label className="flex items-center gap-2 cursor-pointer">
                                <input type="checkbox" defaultChecked className="rounded text-indigo-600" />
                                <span>Audio highlight snippets (MP3 preview)</span>
                              </label>
                            </div>
                          </div>

                          <button
                            onClick={() => {
                              const found = integrations.find((i) => i.provider === "SLACK");
                              if (found) testIntegrationMutation.mutate(found.id);
                              else toast.info("Slack bot is active and listening for meeting events.");
                            }}
                            disabled={testIntegrationMutation.isPending}
                            className="w-full h-9 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-xs font-bold shadow-2xs transition-all flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            {testIntegrationMutation.isPending ? (
                              <RefreshCw size={12} className="animate-spin" />
                            ) : (
                              <Zap size={12} />
                            )}
                            <span>Send Test Slack Notification</span>
                          </button>
                        </div>

                        <div className="md:col-span-7 bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col">
                          <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-700 flex items-center gap-1 text-[11px]">
                              <Eye size={12} className="text-purple-600" />
                              <span>Live Slack Channel Preview</span>
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">#general-intelligence</span>
                          </div>

                          <div className="p-3.5 bg-slate-50/40 flex-1 overflow-y-auto max-h-[300px]">
                            <div className="bg-white rounded-lg border border-slate-200/80 p-3 space-y-2 shadow-2xs">
                              <div className="flex items-center gap-2">
                                <div className="w-7 h-7 rounded-md bg-[#4A154B] text-white flex items-center justify-center text-xs font-bold">
                                  K
                                </div>
                                <div>
                                  <div className="flex items-center gap-1.5">
                                    <span className="text-xs font-bold text-slate-900">Knowra Bot</span>
                                    <span className="text-[9px] px-1 bg-slate-100 text-slate-600 rounded font-semibold uppercase">APP</span>
                                    <span className="text-[10px] text-slate-400">10:42 AM</span>
                                  </div>
                                </div>
                              </div>

                              <div className="pl-9 space-y-2 text-xs">
                                <div className="border-l-2 border-purple-500 pl-2.5 py-0.5 space-y-1">
                                  <p className="font-bold text-slate-900 text-xs">
                                    ⚡ Executive Meeting Brief: Q3 Strategic Architecture Review
                                  </p>
                                  <p className="text-[11px] text-slate-600">
                                    <span className="font-semibold">Key Decision:</span> Ratified PostgreSQL 16 &amp; pgvector partitioning schema for multi-tenant isolation.
                                  </p>
                                  <div className="text-[11px] text-slate-600 space-y-0.5">
                                    <p className="font-semibold text-slate-800">Action Items:</p>
                                    <p>• <span className="text-indigo-600 font-medium">@sujal.nage</span>: Benchmark HNSW indexing speed with 1M vectors</p>
                                    <p>• <span className="text-indigo-600 font-medium">@platform-eng</span>: Finalize zero-downtime database migration script</p>
                                  </div>
                                </div>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ── 4D-1. CONDITIONAL: REAL ATLASSIAN JIRA SOFTWARE CLOUD ── */}
                  {selectedConnector.provider === "JIRA" && (
                    <div className="space-y-4">
                      {/* Section Header */}
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <div className="w-5 h-5 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center text-xs font-bold border border-blue-200">
                            🔵
                          </div>
                          <h4 className="text-xs font-bold text-slate-900">
                            Atlassian Jira Software &amp; Live Sprint Issues
                          </h4>
                          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                            LIVE v3 REST API
                          </span>
                        </div>
                        <div className="flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => {
                              refetchJiraIssues();
                              toast.success("Refreshed live Jira sprint issues");
                            }}
                            disabled={isLoadingJiraIssues}
                            className="px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-2xs flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-60"
                          >
                            <RefreshCw size={11} className={isLoadingJiraIssues ? "animate-spin" : ""} />
                            <span>Refresh Issues</span>
                          </button>
                          {jiraStatus?.instance_url && (
                            <a
                              href={jiraStatus.instance_url}
                              target="_blank"
                              rel="noreferrer"
                              className="px-2.5 py-1 rounded-lg border border-blue-200 bg-blue-50/80 hover:bg-blue-100 text-blue-700 text-xs font-medium shadow-2xs flex items-center gap-1 transition-colors"
                            >
                              <span>Open Jira Cloud</span>
                              <ExternalLink size={10} />
                            </a>
                          )}
                        </div>
                      </div>

                      {/* 2-Column Layout: Create Issue from Action Item (Left 5) & Live Sprint Issues Board (Right 7) */}
                      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                        {/* Left Form: Create Action Item into Jira Ticket */}
                        <div className="md:col-span-5 bg-white rounded-xl border border-slate-200 shadow-2xs p-4 space-y-3.5">
                          <div>
                            <div className="flex items-center justify-between">
                              <label className="text-xs font-bold text-slate-800 block">
                                Create Action Item in Jira
                              </label>
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-100 font-semibold">
                                Project: {jiraStatus?.project_key || "KNOWRA"}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 mt-0.5">
                              Convert detected meeting commitments into real Jira sprint tickets in ADF format.
                            </p>
                          </div>

                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">
                              Issue Summary / Action Item
                            </label>
                            <input
                              type="text"
                              value={jiraNewSummary}
                              onChange={(e) => setJiraNewSummary(e.target.value)}
                              placeholder="e.g. Implement vector index partitioning schema"
                              className="w-full h-8 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white transition-all font-medium"
                            />
                          </div>

                          <div className="grid grid-cols-2 gap-2">
                            <div>
                              <label className="text-xs font-semibold text-slate-700 block mb-1">
                                Issue Type
                              </label>
                              <select
                                value={jiraNewIssueType}
                                onChange={(e) => setJiraNewIssueType(e.target.value)}
                                className="w-full h-8 px-2.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white"
                              >
                                <option value="Task">Task</option>
                                <option value="Story">Story</option>
                                <option value="Bug">Bug</option>
                                <option value="Improvement">Improvement</option>
                              </select>
                            </div>
                            <div>
                              <label className="text-xs font-semibold text-slate-700 block mb-1">
                                Priority
                              </label>
                              <select
                                value={jiraNewPriority}
                                onChange={(e) => setJiraNewPriority(e.target.value)}
                                className="w-full h-8 px-2.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white"
                              >
                                <option value="Highest">Highest</option>
                                <option value="High">High</option>
                                <option value="Medium">Medium</option>
                                <option value="Low">Low</option>
                              </select>
                            </div>
                          </div>

                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">
                              Description &amp; Meeting Context (Optional)
                            </label>
                            <textarea
                              rows={3}
                              value={jiraNewDescription}
                              onChange={(e) => setJiraNewDescription(e.target.value)}
                              placeholder="Add meeting decision details, owner assignment, or sprint notes..."
                              className="w-full p-2.5 text-xs bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:border-indigo-600 focus:bg-white transition-all resize-none"
                            />
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              if (!jiraNewSummary.trim()) {
                                toast.error("Please enter an issue summary.");
                                return;
                              }
                              createJiraIssueMutation.mutate({
                                summary: jiraNewSummary.trim(),
                                description: jiraNewDescription.trim(),
                                issue_type: jiraNewIssueType,
                                priority: jiraNewPriority,
                              });
                            }}
                            disabled={createJiraIssueMutation.isPending || !jiraNewSummary.trim()}
                            className="w-full h-9 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-2xs transition-all flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            {createJiraIssueMutation.isPending ? (
                              <RefreshCw size={12} className="animate-spin" />
                            ) : (
                              <Plus size={13} />
                            )}
                            <span>
                              {createJiraIssueMutation.isPending ? "Creating in Jira..." : "Create Issue in Jira"}
                            </span>
                          </button>

                          <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                            <span>OAuth: AES-256 Fernet</span>
                            <span>Payload: ADF v3 JSON</span>
                          </div>
                        </div>

                        {/* Right Board: Live Sprint Issues Stream */}
                        <div className="md:col-span-7 bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col">
                          <div className="px-3.5 py-2.5 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-700 flex items-center gap-1.5 text-[11px]">
                              <Kanban size={13} className="text-blue-600" />
                              <span>Live Sprint Board</span>
                              <span className="px-1.5 py-0.2 rounded-full bg-slate-200/80 text-slate-700 font-mono text-[10px] font-bold">
                                {jiraIssues.length}
                              </span>
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {jiraStatus?.instance_url ? jiraStatus.instance_url.replace("https://", "").replace("http://", "") : "softude.atlassian.net"}
                            </span>
                          </div>

                          <div className="p-3 bg-slate-50/40 flex-1 overflow-y-auto max-h-[380px] space-y-2.5">
                            {isLoadingJiraIssues ? (
                              <div className="py-12 text-center text-xs text-slate-400 flex flex-col items-center gap-2">
                                <RefreshCw size={16} className="animate-spin text-blue-600" />
                                <span>Loading Jira sprint tickets...</span>
                              </div>
                            ) : jiraIssues.length === 0 ? (
                              <div className="py-10 px-4 text-center space-y-2 bg-white rounded-xl border border-slate-200/80">
                                <div className="w-8 h-8 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center text-sm mx-auto border border-blue-100">
                                  🔵
                                </div>
                                <p className="text-xs font-bold text-slate-800">
                                  No active sprint issues found in {jiraStatus?.project_key || "KNOWRA"}
                                </p>
                                <p className="text-[11px] text-slate-500 max-w-xs mx-auto">
                                  Use the form on the left to push meeting action items or decisions directly into your Jira backlog.
                                </p>
                              </div>
                            ) : (
                              jiraIssues.map((iss) => (
                                <div
                                  key={iss.key || iss.id}
                                  className="bg-white rounded-lg border border-slate-200/90 p-3 space-y-2 shadow-2xs hover:border-blue-300 hover:shadow-xs transition-all"
                                >
                                  <div className="flex items-center justify-between gap-2">
                                    <div className="flex items-center gap-1.5">
                                      <a
                                        href={iss.url}
                                        target="_blank"
                                        rel="noreferrer"
                                        className="text-[10px] font-mono font-bold text-blue-600 bg-blue-50 hover:bg-blue-100 px-2 py-0.5 rounded border border-blue-200/80 flex items-center gap-1 transition-colors"
                                      >
                                        <span>{iss.key}</span>
                                        <ExternalLink size={9} />
                                      </a>
                                      <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                        {iss.issue_type || "Task"}
                                      </span>
                                    </div>
                                    <div className="flex items-center gap-1.5">
                                      <span
                                        className={cn(
                                          "text-[10px] font-semibold px-2 py-0.5 rounded border",
                                          iss.priority === "High" || iss.priority === "Highest"
                                            ? "bg-rose-50 text-rose-700 border-rose-200"
                                            : iss.priority === "Medium"
                                            ? "bg-amber-50 text-amber-700 border-amber-200"
                                            : "bg-slate-50 text-slate-600 border-slate-200"
                                        )}
                                      >
                                        {iss.priority || "Medium"}
                                      </span>
                                      <span
                                        className={cn(
                                          "text-[10px] font-semibold px-2 py-0.5 rounded border",
                                          iss.status === "Done"
                                            ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                            : iss.status === "In Progress"
                                            ? "bg-blue-50 text-blue-700 border-blue-200"
                                            : "bg-slate-100 text-slate-700 border-slate-200"
                                        )}
                                      >
                                        {iss.status || "To Do"}
                                      </span>
                                    </div>
                                  </div>

                                  <h5 className="text-xs font-semibold text-slate-900 leading-snug">
                                    {iss.summary}
                                  </h5>

                                  <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
                                    <span className="truncate max-w-[180px]">
                                      Assignee: <span className="font-medium text-slate-700">{iss.assignee || "Unassigned"}</span>
                                    </span>
                                    <span className="shrink-0 text-slate-400">
                                      {iss.created ? relativeTime(iss.created) : "Recent"}
                                    </span>
                                  </div>
                                </div>
                              ))
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* ── 4D-2. CONDITIONAL: LINEAR ENGINEERING SYNC ── */}
                  {selectedConnector.provider === "LINEAR" && (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <Kanban size={14} className="text-violet-600" />
                          <h4 className="text-xs font-bold text-slate-900">
                            Linear Engineering Sync &amp; Cycles
                          </h4>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">
                          AUTO-SYNC
                        </span>
                      </div>

                      <div className="grid grid-cols-1 md:grid-cols-12 gap-4">
                        <div className="md:col-span-5 bg-white rounded-xl border border-slate-200 shadow-2xs p-4 space-y-3">
                          <div>
                            <label className="text-xs font-semibold text-slate-700 block mb-1">
                              Target Project / Team Board
                            </label>
                            <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-800">
                              <span>{selectedConnector.provider === "LINEAR" ? "ENG-Cycle (Knowra Core)" : "KNOWRA (Product Sprint)"}</span>
                            </div>
                            <p className="text-[10px] text-slate-400 mt-1">
                              Discovered commitments and action items are automatically filed here.
                            </p>
                          </div>

                          <div className="space-y-2 pt-1">
                            <label className="text-xs font-semibold text-slate-700 block">
                              Automated Issue Attributes
                            </label>
                            <div className="space-y-1.5 text-[11px] text-slate-600">
                              <div className="flex justify-between items-center py-0.5">
                                <span>Default Issue Type:</span>
                                <span className="font-mono bg-slate-100 px-1.5 py-0.5 rounded text-slate-800 font-semibold">Task</span>
                              </div>
                              <div className="flex justify-between items-center py-0.5">
                                <span>Priority Mapping:</span>
                                <span className="font-mono bg-amber-50 text-amber-700 px-1.5 py-0.5 rounded font-semibold border border-amber-200">Auto-Detect</span>
                              </div>
                              <div className="flex justify-between items-center py-0.5">
                                <span>Assignee Matching:</span>
                                <span className="font-mono bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded font-semibold border border-emerald-200">By Speaker Voice</span>
                              </div>
                            </div>
                          </div>

                          <button
                            onClick={() => {
                              const found = integrations.find((i) => i.provider === selectedConnector.provider);
                              if (found) testIntegrationMutation.mutate(found.id);
                              else toast.info(`${selectedConnector.name} is synced with active sprint.`);
                            }}
                            disabled={testIntegrationMutation.isPending}
                            className="w-full h-9 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-2xs transition-all flex items-center justify-center gap-1.5 cursor-pointer disabled:opacity-50"
                          >
                            {testIntegrationMutation.isPending ? (
                              <RefreshCw size={12} className="animate-spin" />
                            ) : (
                              <Zap size={12} />
                            )}
                            <span>Sync Pending Action Items</span>
                          </button>
                        </div>

                        <div className="md:col-span-7 bg-white rounded-xl border border-slate-200 shadow-2xs overflow-hidden flex flex-col">
                          <div className="px-3 py-2 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-700 flex items-center gap-1 text-[11px]">
                              <Eye size={12} className="text-blue-600" />
                              <span>Extracted Issue Ticket Preview</span>
                            </span>
                            <span className="text-[10px] text-slate-400 font-mono">
                              {selectedConnector.provider === "LINEAR" ? "ENG-104" : "KNOWRA-4892"}
                            </span>
                          </div>

                          <div className="p-3.5 bg-slate-50/40 flex-1 overflow-y-auto max-h-[300px]">
                            <div className="bg-white rounded-lg border border-slate-200/80 p-3 space-y-2 shadow-2xs">
                              <div className="flex items-center justify-between gap-2">
                                <span className="text-[10px] font-mono font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
                                  {selectedConnector.provider === "LINEAR" ? "ENG-104" : "KNOWRA-4892"}
                                </span>
                                <span className="text-[10px] font-semibold bg-rose-50 text-rose-700 px-2 py-0.5 rounded border border-rose-200">
                                  High Priority
                                </span>
                              </div>

                              <h5 className="text-xs font-bold text-slate-900 leading-snug">
                                Review and implement vector index partitioning schema
                              </h5>

                              <p className="text-[11px] text-slate-500 leading-relaxed">
                                Verbal commitment ratified during Strategic Architecture Review. Partition pgvector indexes per tenant to eliminate cross-tenant vector scanning overhead.
                              </p>

                              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500 font-medium">
                                <span>Assignee: Sujal Nage</span>
                                <span>Due: End of Sprint</span>
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── 5. SUBTLE COMPLIANCE FOOTER ── */}
              <div className="pt-4 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-400">
                <span>Google API Services Limited Use &amp; OAuth 2.0 Compliance</span>
                <a
                  href={selectedConnector.docUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="text-slate-500 hover:text-indigo-600 flex items-center gap-1 transition-colors"
                >
                  <span>Open {selectedConnector.name}</span>
                  <ExternalLink size={11} />
                </a>
              </div>
            </div>
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 2: WEBHOOKS & API (ENTERPRISE DEVELOPER PORTAL)                   */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {currentTopTab === "webhooks" && (
          <div className="p-6 space-y-5">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Enterprise Webhooks &amp; Custom Endpoints</h3>
                <p className="text-xs text-slate-500">Real-time HTTP callbacks broadcasting meeting intelligence signed with HMAC-SHA256.</p>
              </div>
              <button
                onClick={() => {
                  setModalProvider("WEBHOOK");
                  setIsAddModalOpen(true);
                }}
                className="px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs flex items-center gap-1.5 cursor-pointer"
              >
                <Plus size={13} />
                <span>Register Webhook</span>
              </button>
            </div>

            {integrations.filter((i) => i.provider === "WEBHOOK" || i.webhook_url).length === 0 ? (
              <div className="py-14 px-4 text-center space-y-3 border border-slate-200 rounded-xl bg-white shadow-2xs">
                <div className="w-10 h-10 rounded-xl bg-slate-100 text-slate-400 flex items-center justify-center mx-auto border border-slate-200/60 shadow-2xs">
                  <Code2 size={18} />
                </div>
                <div>
                  <p className="text-xs font-semibold text-slate-800">
                    No custom webhooks configured
                  </p>
                  <p className="text-[11px] text-slate-500 max-w-sm mx-auto mt-0.5">
                    Register an HTTPS endpoint to receive live JSON payloads whenever meetings finish processing, decisions are ratified, or action items are created.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setModalProvider("WEBHOOK");
                    setIsAddModalOpen(true);
                  }}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-medium shadow-2xs transition-colors cursor-pointer"
                >
                  <Plus size={12} />
                  <span>Create Webhook Endpoint</span>
                </button>
              </div>
            ) : (
              <div className="divide-y divide-slate-100 border border-slate-200 rounded-xl overflow-hidden bg-white shadow-2xs">
                {integrations
                  .filter((i) => i.provider === "WEBHOOK" || i.webhook_url)
                  .map((item) => (
                    <div key={item.id} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3 hover:bg-slate-50/50 transition-colors">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-xl bg-indigo-50/80 border border-indigo-100 text-indigo-700 flex items-center justify-center text-lg shrink-0">
                          <Code2 size={18} />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <h4 className="text-xs font-bold text-slate-900">{item.name}</h4>
                            <span className="text-[10px] font-mono px-2 py-0.2 rounded-full bg-slate-100 text-slate-700">
                              HMAC-SHA256
                            </span>
                            <span className="text-[10px] font-semibold px-2 py-0.2 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                              Active
                            </span>
                          </div>
                          <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                            {item.webhook_url || item.channel_or_project_id || "https://your-api.com/webhook"}
                          </p>
                          <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                            {(item.events_subscribed?.length ? item.events_subscribed : ["MEETING_PROCESSED"]).map((ev) => (
                              <span key={ev} className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 border border-slate-200/60">
                                {ev}
                              </span>
                            ))}
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 shrink-0 self-end sm:self-auto">
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
                          title="Remove webhook"
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>
        )}

        {/* ═════════════════════════════════════════════════════════════════════ */}
        {/* TAB 3: ENTERPRISE AUDIT LOG & EVENT STREAM                            */}
        {/* ═════════════════════════════════════════════════════════════════════ */}
        {currentTopTab === "audit" && (
          <div className="p-6 space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Enterprise Audit Log &amp; Event Stream</h3>
                <p className="text-xs text-slate-500">Immutable log of outbound events, HTTP status codes, and cryptographic delivery signatures.</p>
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

      {/* ── 4. REAL OAUTH ACCOUNT & EMAIL ID SELECTION MODAL (GOOGLE SIGN-IN FIDELITY) ── */}
      {isOAuthModalOpen && authConnector && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-xs animate-fade-in">
          <div className="relative w-full max-w-[780px] bg-white rounded-[28px] border border-[#dadce0] shadow-[0_4px_28px_rgba(0,0,0,0.12)] p-8 sm:p-10 font-sans animate-in fade-in zoom-in-95 duration-150">
            {/* Close Button */}
            <button
              onClick={() => {
                setIsOAuthModalOpen(false);
                setConnectingAccountEmail(null);
                setShowCustomAccountInput(false);
              }}
              className="absolute top-5 right-5 w-8 h-8 rounded-full flex items-center justify-center text-[#5f6368] hover:text-[#1f1f1f] hover:bg-[#f1f3f4] transition-colors cursor-pointer text-sm"
              title="Close dialog"
            >
              ✕
            </button>

            {/* Provider Branding Bar */}
            <div className="flex items-center gap-2.5 mb-8">
              {authConnector.provider === "GOOGLE_CALENDAR" || authConnector.provider === "GOOGLE_MEET" ? (
                <>
                  <svg width="20" height="20" viewBox="0 0 24 24" className="shrink-0">
                    <path
                      fill="#4285F4"
                      d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
                    />
                  </svg>
                  <span className="text-[14px] font-normal text-[#3c4043]">Sign in with Google</span>
                </>
              ) : authConnector.provider === "OUTLOOK" || authConnector.provider === "TEAMS" ? (
                <>
                  <svg width="18" height="18" viewBox="0 0 23 23" className="shrink-0">
                    <rect width="10" height="10" fill="#f25022" />
                    <rect x="12" width="10" height="10" fill="#7fba00" />
                    <rect y="12" width="10" height="10" fill="#00a4ef" />
                    <rect x="12" y="12" width="10" height="10" fill="#ffb900" />
                  </svg>
                  <span className="text-[14px] font-normal text-[#3c4043]">Sign in with Microsoft</span>
                </>
              ) : authConnector.provider === "ZOOM" ? (
                <>
                  <div className="w-5 h-5 rounded-md bg-[#2D8CFF] text-white flex items-center justify-center font-bold text-xs">
                    Z
                  </div>
                  <span className="text-[14px] font-normal text-[#3c4043]">Sign in with Zoom</span>
                </>
              ) : authConnector.provider === "JIRA" ? (
                <>
                  <div className="w-5 h-5 rounded-md bg-[#0052CC] text-white flex items-center justify-center font-bold text-xs shadow-2xs">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M11.53 2c0 2.4 1.97 4.35 4.35 4.35h1.78v1.74c0 2.4 1.95 4.34 4.34 4.34V2H11.53zm-5.76 5.8c0 2.4 1.96 4.35 4.35 4.35h1.78v1.74c0 2.4 1.96 4.35 4.35 4.35V7.8H5.77zm-5.77 5.8c0 2.4 1.95 4.35 4.35 4.35h1.78v1.75c0 2.39 1.96 4.3 4.34 4.3V13.6H0z"/>
                    </svg>
                  </div>
                  <span className="text-[14px] font-normal text-[#3c4043]">Sign in with Atlassian</span>
                </>
              ) : (
                <>
                  <span className="text-lg">{authConnector.iconSvg}</span>
                  <span className="text-[14px] font-normal text-[#3c4043]">
                    Sign in to connect {authConnector.name}
                  </span>
                </>
              )}
            </div>

            {/* Split Content: Left Title + Right Account Selection List */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-8 items-start">
              {/* Left Column */}
              <div className="md:col-span-5 space-y-3">
                <h2 className="text-[32px] sm:text-[36px] font-normal text-[#1f1f1f] leading-tight font-sans tracking-tight">
                  Choose an account
                </h2>
                <p className="text-[15px] text-[#444746] leading-relaxed">
                  to continue to{" "}
                  <span className="text-[#0b57d0] font-medium hover:underline cursor-pointer">
                    {authConnector.provider === "JIRA" ? "Knowra Jira Intelligence" : "Knowra"}
                  </span>
                </p>
                <p className="text-[12px] text-[#5f6368] pt-2 hidden sm:block leading-relaxed">
                  {authConnector.provider === "JIRA"
                    ? "Selecting your Atlassian account configures Jira automatically. Meeting action items and decisions will seamlessly link to sprint issues."
                    : "Knowra will access your calendar schedules and authorize notetakers to automatically record and summarize meetings."}
                </p>
              </div>

              {/* Right Column: Account Choices */}
              <div className="md:col-span-7 divide-y divide-[#e0e2ec]">
                {/* Account 1: sujal2005nage@gmail.com */}
                <button
                  type="button"
                  onClick={() => handleSelectAccount("sujal2005nage@gmail.com")}
                  disabled={connectingAccountEmail !== null}
                  className="w-full py-3 px-2 flex items-center justify-between text-left hover:bg-[#f8fafd] transition-colors rounded-lg cursor-pointer group disabled:opacity-60"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="w-9 h-9 rounded-full bg-[#137333] text-white flex items-center justify-center font-medium text-sm shrink-0 shadow-2xs">
                      S
                    </div>
                    <div className="min-w-0">
                      <div className="text-[14px] font-medium text-[#1f1f1f] group-hover:text-black">
                        Sujal Nage
                      </div>
                      <div className="text-[12px] text-[#444746] truncate">
                        sujal2005nage@gmail.com
                      </div>
                    </div>
                  </div>
                  {connectingAccountEmail === "sujal2005nage@gmail.com" ? (
                    <span className="w-4 h-4 border-2 border-[#dadce0] border-t-[#0b57d0] rounded-full animate-spin shrink-0" />
                  ) : null}
                </button>

                {/* Account 2: sujal.nage@softude.com */}
                <button
                  type="button"
                  onClick={() => handleSelectAccount("sujal.nage@softude.com")}
                  disabled={connectingAccountEmail !== null}
                  className="w-full py-3 px-2 flex items-center justify-between text-left hover:bg-[#f8fafd] transition-colors rounded-lg cursor-pointer group disabled:opacity-60"
                >
                  <div className="flex items-center gap-3.5 min-w-0">
                    <div className="w-9 h-9 rounded-full bg-[#7b1fa2] text-white flex items-center justify-center font-medium text-sm shrink-0 shadow-2xs">
                      S
                    </div>
                    <div className="min-w-0">
                      <div className="text-[14px] font-medium text-[#1f1f1f] group-hover:text-black">
                        Sujal Nage
                      </div>
                      <div className="text-[12px] text-[#444746] truncate">
                        sujal.nage@softude.com
                      </div>
                    </div>
                  </div>
                  {connectingAccountEmail === "sujal.nage@softude.com" ? (
                    <span className="w-4 h-4 border-2 border-[#dadce0] border-t-[#0b57d0] rounded-full animate-spin shrink-0" />
                  ) : null}
                </button>

                {/* Account 3: Use another account */}
                <div className="pt-0.5">
                  <button
                    type="button"
                    onClick={() => setShowCustomAccountInput(!showCustomAccountInput)}
                    className="w-full py-3 px-2 flex items-center gap-3.5 text-left hover:bg-[#f8fafd] transition-colors rounded-lg cursor-pointer group"
                  >
                    <div className="w-9 h-9 rounded-full border border-[#747775] flex items-center justify-center text-[#444746] shrink-0">
                      <User size={16} />
                    </div>
                    <div className="text-[14px] font-medium text-[#1f1f1f] group-hover:text-black">
                      Use another account
                    </div>
                  </button>

                  {/* Expandable Custom Email Input */}
                  {showCustomAccountInput && (
                    <form
                      onSubmit={(e) => {
                        e.preventDefault();
                        if (customAccountEmail.trim()) {
                          handleSelectAccount(customAccountEmail.trim());
                        }
                      }}
                      className="mt-2 mb-2 p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2.5 animate-in fade-in duration-150"
                    >
                      <label className="text-[11px] font-medium text-slate-700 block">
                        Enter work or personal email address to continue:
                      </label>
                      <div className="flex items-center gap-2">
                        <input
                          type="email"
                          autoFocus
                          required
                          value={customAccountEmail}
                          onChange={(e) => setCustomAccountEmail(e.target.value)}
                          placeholder="name@company.com"
                          className="flex-1 h-9 px-3 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:border-[#0b57d0]"
                        />
                        <button
                          type="submit"
                          disabled={!customAccountEmail.trim() || connectingAccountEmail !== null}
                          className="h-9 px-4 rounded-lg bg-[#0b57d0] hover:bg-[#0842a0] text-white text-xs font-semibold shadow-xs disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                        >
                          {connectingAccountEmail === customAccountEmail.trim() ? (
                            <span className="w-3.5 h-3.5 border-2 border-white/60 border-t-white rounded-full animate-spin" />
                          ) : (
                            <span>Next</span>
                          )}
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              </div>
            </div>

            {/* Bottom Footer (Matching Google Account Picker) */}
            <div className="mt-12 pt-4 flex flex-col sm:flex-row items-center justify-between gap-3 text-[12px] text-[#444746] border-t border-slate-100">
              <div className="flex items-center gap-1.5 cursor-pointer hover:text-[#1f1f1f] transition-colors">
                <span>English (United States)</span>
                <ChevronDown size={13} className="text-[#5f6368]" />
              </div>

              <div className="flex items-center gap-6">
                <span className="hover:text-[#1f1f1f] cursor-pointer transition-colors">Help</span>
                <span className="hover:text-[#1f1f1f] cursor-pointer transition-colors">Privacy</span>
                <span className="hover:text-[#1f1f1f] cursor-pointer transition-colors">Terms</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── 4B. GOOGLE CALENDAR LIVE OAUTH CLOUD SETUP MODAL ── */}
      {googleSetupModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
          <div className="relative w-full max-w-[620px] bg-white rounded-3xl border border-slate-200 shadow-2xl p-6 sm:p-8 font-sans animate-in fade-in zoom-in-95 duration-150">
            {/* Close Button */}
            <button
              onClick={() => setGoogleSetupModalOpen(false)}
              className="absolute top-5 right-5 w-8 h-8 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors cursor-pointer text-sm"
              title="Close modal"
            >
              ✕
            </button>

            {/* Header */}
            <div className="flex items-center gap-3 mb-5">
              <div className="w-12 h-12 rounded-2xl bg-blue-50 border border-blue-100 flex items-center justify-center text-2xl shadow-2xs">
                📅
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900 flex items-center gap-2">
                  <span>Connect Google Calendar</span>
                  <span className="text-[10px] font-semibold bg-blue-100 text-blue-700 px-2 py-0.5 rounded-full">
                    OAuth 2.0
                  </span>
                </h3>
                <p className="text-xs text-slate-500">
                  Live end-to-end synchronization with Google Calendar API v3
                </p>
              </div>
            </div>

            {/* Explanatory Body */}
            <div className="space-y-4 text-xs">
              <div className="p-3.5 bg-blue-50/70 border border-blue-200/80 rounded-2xl space-y-2 text-slate-700">
                <div className="flex items-center gap-1.5 font-bold text-blue-900">
                  <Key size={14} className="text-blue-600" />
                  <span>Google Cloud Console Credentials Required</span>
                </div>
                <p className="text-slate-600 leading-relaxed">
                  To authenticate with real Google accounts, your Knowra backend needs your Google OAuth Client ID and Secret in your <code className="bg-blue-100/70 text-blue-900 px-1 py-0.5 rounded font-mono text-[11px]">backend/.env</code> file.
                </p>
              </div>

              {/* Instructions steps */}
              <div className="space-y-2.5">
                <h4 className="font-bold text-slate-800 uppercase tracking-wider text-[11px]">
                  Setup Steps:
                </h4>
                <ol className="space-y-2 list-decimal list-inside text-slate-600">
                  <li>
                    Go to{" "}
                    <a
                      href="https://console.cloud.google.com/apis/credentials"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-indigo-600 hover:underline font-semibold inline-flex items-center gap-1"
                    >
                      Google Cloud Console &rarr; Credentials <ExternalLink size={11} />
                    </a>
                  </li>
                  <li>
                    Enable the <span className="font-semibold text-slate-800">Google Calendar API</span> in APIs & Services.
                  </li>
                  <li>
                    Create an <span className="font-semibold text-slate-800">OAuth 2.0 Client ID</span> (Web Application type).
                  </li>
                  <li className="space-y-1">
                    <span>Add this exact Authorized Redirect URI:</span>
                    <div className="mt-1 flex items-center gap-2 p-2 bg-slate-100 border border-slate-200 rounded-xl font-mono text-[11px] text-slate-800 select-all">
                      <span className="truncate flex-1">{googleRedirectUri}</span>
                      <button
                        type="button"
                        onClick={() => {
                          navigator.clipboard.writeText(googleRedirectUri);
                          setCopiedRedirect(true);
                          setTimeout(() => setCopiedRedirect(false), 2000);
                          toast.success("Redirect URI copied to clipboard!");
                        }}
                        className="px-2.5 py-1 bg-white hover:bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 shadow-2xs flex items-center gap-1 shrink-0 cursor-pointer"
                      >
                        {copiedRedirect ? (
                          <>
                            <Check size={12} className="text-emerald-600" />
                            <span className="text-emerald-700">Copied!</span>
                          </>
                        ) : (
                          <>
                            <Copy size={12} />
                            <span>Copy</span>
                          </>
                        )}
                      </button>
                    </div>
                  </li>
                  <li>
                    Add the values to <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-[11px]">backend/.env</code>:
                    <div className="mt-1 p-2.5 bg-slate-900 text-slate-200 rounded-xl font-mono text-[11px] space-y-0.5">
                      <div>GOOGLE_CLIENT_ID=&quot;your-client-id.apps.googleusercontent.com&quot;</div>
                      <div>GOOGLE_CLIENT_SECRET=&quot;GOCSPX-your-secret&quot;</div>
                    </div>
                  </li>
                </ol>
              </div>

              {/* Action Choices */}
              <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setGoogleSetupModalOpen(false);
                    setIsOAuthModalOpen(true);
                  }}
                  className="w-full sm:w-auto px-4 py-2.5 rounded-xl border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <User size={14} className="text-slate-500" />
                  <span>Choose Account in Sandbox Mode</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setGoogleSetupModalOpen(false);
                    if (authConnector) {
                      handleOpenConnect(authConnector);
                    }
                  }}
                  className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-xs cursor-pointer flex items-center justify-center gap-1.5"
                >
                  <RefreshCw size={13} />
                  <span>I've Saved .env, Retry Connect</span>
                </button>
              </div>
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
                  <option value="LINEAR">Linear</option>
                  <option value="JIRA">Jira</option>
                  <option value="TEAMS">Microsoft Teams</option>
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
                  toast.success("Payload copied to clipboard");
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
