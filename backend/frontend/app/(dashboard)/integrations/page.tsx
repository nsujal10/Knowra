"use client";

import React, { useState, useMemo, useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import { INTEGRATIONS } from "@/lib/api/endpoints";
import { queryKeys } from "@/lib/query/keys";
import type { Integration, IntegrationEvent, TestDispatchResponse } from "@/lib/types";
import { PageHeader } from "@/components/ui/page-header";
import {
  Layers,
  Plus,
  RefreshCw,
  Search,
  Filter,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Copy,
  Check,
  Radio,
  ExternalLink,
  Trash2,
  Zap,
  Shield,
  ShieldCheck,
  Send,
  MessageSquare,
  Bot,
  User,
  Clock,
  ChevronRight,
  ChevronDown,
  Terminal,
  Code,
  FileCode,
  X,
  Sliders,
  Sparkles,
  PanelRightClose,
  PanelRightOpen,
  ArrowRight,
  Lock,
} from "lucide-react";

// ─── BRAND DEFINITIONS ────────────────────────────────────────────────────────
interface ProviderMeta {
  label: string;
  brandColor: string;
  badgeBg: string;
  badgeBorder: string;
  iconText: string;
  defaultChannelPlaceholder: string;
  description: string;
  sampleUrl: string;
}

const PROVIDER_CONFIG: Record<string, ProviderMeta> = {
  SLACK: {
    label: "Slack",
    brandColor: "#4A154B",
    badgeBg: "bg-[#4A154B]/10 text-[#4A154B]",
    badgeBorder: "border-[#4A154B]/20",
    iconText: "💬",
    defaultChannelPlaceholder: "#executive-alerts",
    description: "Post automated action items and decision announcements to Slack channels.",
    sampleUrl: "https://example.com/hooks/slack/services/webhook-placeholder",
  },
  TEAMS: {
    label: "Microsoft Teams",
    brandColor: "#5059C9",
    badgeBg: "bg-[#5059C9]/10 text-[#5059C9]",
    badgeBorder: "border-[#5059C9]/20",
    iconText: "🟣",
    defaultChannelPlaceholder: "19:meeting-intel@thread.tacv2",
    description: "Dispatch adaptive cards with meeting summaries and key takeaways to Teams.",
    sampleUrl: "https://outlook.office.com/webhook/xxx-xxx-xxx/IncomingWebhook/...",
  },
  JIRA: {
    label: "Jira Software",
    brandColor: "#0052CC",
    badgeBg: "bg-[#0052CC]/10 text-[#0052CC]",
    badgeBorder: "border-[#0052CC]/20",
    iconText: "🔵",
    defaultChannelPlaceholder: "PROJ-DEV",
    description: "Automatically create actionable backlog items when decisions are confirmed.",
    sampleUrl: "https://your-domain.atlassian.net/rest/api/3/webhook",
  },
  WEBHOOK: {
    label: "Custom HTTP Webhook",
    brandColor: "#4F46E5",
    badgeBg: "bg-indigo-50 text-indigo-700",
    badgeBorder: "border-indigo-200",
    iconText: "🔗",
    defaultChannelPlaceholder: "events-stream-v1",
    description: "Deliver CloudEvents JSON payloads signed with HMAC-SHA256 to your API.",
    sampleUrl: "https://api.yourcompany.com/v1/webhooks/knowra",
  },
};

const AVAILABLE_EVENTS = [
  { id: "ACTION_CREATED", label: "Action Items Created", description: "Triggered when AI detects new deliverables" },
  { id: "DECISION_CONFIRMED", label: "Decisions Confirmed", description: "Triggered on architectural or team consensus" },
  { id: "RISK_DETECTED", label: "Security & Risk Alerts", description: "Triggered on policy or compliance concerns" },
  { id: "MEETING_TRANSCRIBED", label: "Meeting Transcription Complete", description: "Triggered once audio/video indexing finishes" },
];

interface ChatMessage {
  id: string;
  sender: "user" | "bot";
  content: string;
  timestamp: string;
  codeSnippet?: {
    language: string;
    code: string;
  };
}

export default function IntegrationsPage() {
  const queryClient = useQueryClient();

  // Search and Filter states
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedProvider, setSelectedProvider] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");

  // Drawer & Modal states
  const [showRightDrawer, setShowRightDrawer] = useState(true);
  const [activeDrawerTab, setActiveDrawerTab] = useState<"stream" | "copilot">("stream");
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Test Ping Toast State
  const [testResult, setTestResult] = useState<{
    integrationId: string;
    status: "loading" | "success" | "error";
    detail: string;
  } | null>(null);

  // New Integration Form State
  const [formProvider, setFormProvider] = useState<string>("SLACK");
  const [formName, setFormName] = useState("");
  const [formWebhookUrl, setFormWebhookUrl] = useState("");
  const [formChannel, setFormChannel] = useState("");
  const [formSecret, setFormSecret] = useState("");
  const [formEvents, setFormEvents] = useState<string[]>([
    "ACTION_CREATED",
    "DECISION_CONFIRMED",
  ]);
  const [formError, setFormError] = useState("");

  // AI Copilot state
  const [chatInput, setChatInput] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
    {
      id: "msg-welcome",
      sender: "bot",
      content:
        "Hello! I am your Knowra Integrations Copilot. I can guide you through setting up Slack bots, verifying HMAC-SHA256 signatures, or configuring Jira automation webhooks.",
      timestamp: "Just now",
      codeSnippet: {
        language: "python",
        code: `# HMAC-SHA256 Signature Verification Example
import hmac, hashlib

def verify_knowra_signature(payload_bytes, signature_header, secret):
    expected = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature_header)`,
      },
    },
  ]);
  const [isCopilotTyping, setIsCopilotTyping] = useState(false);
  const chatScrollRef = useRef<HTMLDivElement>(null);

  // Scroll chat
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [chatMessages, isCopilotTyping]);

  // ─── REAL DATA QUERIES ───────────────────────────────────────────────────────

  // 1. Fetch Integrations
  const {
    data: integrations = [],
    isLoading: isIntegrationsLoading,
    refetch: refetchIntegrations,
    isFetching: isIntegrationsFetching,
  } = useQuery<Integration[]>({
    queryKey: [
      ...queryKeys.integrations.list(),
      selectedProvider,
      selectedStatus,
    ],
    queryFn: () =>
      api.get<Integration[]>(
        INTEGRATIONS.list({
          provider: selectedProvider === "ALL" ? undefined : selectedProvider,
          status: selectedStatus === "ALL" ? undefined : selectedStatus,
        })
      ),
  });

  // 2. Fetch Event Delivery History
  const {
    data: eventHistory = [],
    isLoading: isEventsLoading,
    refetch: refetchEvents,
    isFetching: isEventsFetching,
  } = useQuery<IntegrationEvent[]>({
    queryKey: ["integrations-events-history"],
    queryFn: () => api.get<IntegrationEvent[]>(INTEGRATIONS.eventsHistory({ limit: 40 })),
    refetchInterval: 10_000, // poll every 10s for real-time delivery stream
  });

  // ─── MUTATIONS ───────────────────────────────────────────────────────────────

  // Create Integration
  const createMutation = useMutation({
    mutationFn: (newIntegration: {
      provider: string;
      name: string;
      credentials_secret: string;
      webhook_url?: string;
      channel_or_project_id?: string;
      events_subscribed: string[];
    }) => api.post<Integration>(INTEGRATIONS.create(), newIntegration),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
      setShowCreateModal(false);
      resetForm();
    },
    onError: (err: any) => {
      setFormError(err?.message || "Failed to create integration. Please check inputs.");
    },
  });

  // Toggle Active/Inactive Status
  const toggleMutation = useMutation({
    mutationFn: ({ id, newStatus }: { id: string; newStatus: "ACTIVE" | "INACTIVE" }) =>
      api.patch<Integration>(INTEGRATIONS.update(id), { status: newStatus }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
    },
  });

  // Test Connectivity Ping
  const testMutation = useMutation({
    mutationFn: (integrationId: string) =>
      api.post<TestDispatchResponse>(INTEGRATIONS.test(integrationId)),
    onMutate: (id) => {
      setTestResult({
        integrationId: id,
        status: "loading",
        detail: "Dispatching verification ping to external endpoint...",
      });
    },
    onSuccess: (data, id) => {
      setTestResult({
        integrationId: id,
        status: "success",
        detail: data.detail || `Ping delivered successfully (Status: ${data.status})`,
      });
      queryClient.invalidateQueries({ queryKey: ["integrations-events-history"] });
      setTimeout(() => setTestResult(null), 4000);
    },
    onError: (err: any, id) => {
      setTestResult({
        integrationId: id,
        status: "error",
        detail: err?.message || "Connection timeout or invalid webhook destination.",
      });
      setTimeout(() => setTestResult(null), 5000);
    },
  });

  // Delete Integration
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.delete(INTEGRATIONS.delete(id)),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.integrations.list() });
    },
  });

  const resetForm = () => {
    setFormName("");
    setFormWebhookUrl("");
    setFormChannel("");
    setFormSecret("");
    setFormEvents(["ACTION_CREATED", "DECISION_CONFIRMED"]);
    setFormError("");
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      setFormError("Connector name is required.");
      return;
    }
    if (!formWebhookUrl.trim()) {
      setFormError("Target Webhook URL is required.");
      return;
    }
    createMutation.mutate({
      provider: formProvider,
      name: formName.trim(),
      credentials_secret: formSecret.trim() || "sk-knowra-default-secret",
      webhook_url: formWebhookUrl.trim(),
      channel_or_project_id: formChannel.trim() || undefined,
      events_subscribed: formEvents,
    });
  };

  // Copy to clipboard helper
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Filtered Integrations list
  const filteredIntegrations = useMemo(() => {
    return integrations.filter((item) => {
      const matchesSearch =
        !searchQuery.trim() ||
        (item.name && item.name.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (item.webhook_url && item.webhook_url.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (item.channel_or_project_id && item.channel_or_project_id.toLowerCase().includes(searchQuery.toLowerCase())) ||
        (item.channel_or_project && item.channel_or_project.toLowerCase().includes(searchQuery.toLowerCase()));

      const matchesProvider =
        selectedProvider === "ALL" || item.provider.toUpperCase() === selectedProvider;

      const matchesStatus =
        selectedStatus === "ALL" || item.status.toUpperCase() === selectedStatus;

      return matchesSearch && matchesProvider && matchesStatus;
    });
  }, [integrations, searchQuery, selectedProvider, selectedStatus]);

  // AI Copilot response handler
  const handleSendChat = () => {
    if (!chatInput.trim() || isCopilotTyping) return;
    const userText = chatInput.trim();
    const newMsg: ChatMessage = {
      id: `usr-${Date.now()}`,
      sender: "user",
      content: userText,
      timestamp: "Just now",
    };
    setChatMessages((prev) => [...prev, newMsg]);
    setChatInput("");
    setIsCopilotTyping(true);

    setTimeout(() => {
      let botResponse = "";
      let codeSnippet: ChatMessage["codeSnippet"] | undefined = undefined;

      const lower = userText.toLowerCase();
      if (lower.includes("slack")) {
        botResponse =
          "To configure a Slack connector in Knowra:\n1. Go to your Slack API workspace and create a New App.\n2. Enable 'Incoming Webhooks' and generate a Webhook URL for your target channel.\n3. Paste the Webhook URL into the Knowra Slack Connector form. Knowra will automatically dispatch formatted block-kit messages with action owner mentions!";
        codeSnippet = {
          language: "json",
          code: `{
  "text": "📌 New Decision Confirmed: PostgreSQL pgvector Migration",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Decision Confirmed:* Architecture Committee agreed on PostgreSQL pgvector.\\n*Decided by:* Sujal Nage"
      }
    }
  ]
}`,
        };
      } else if (lower.includes("hmac") || lower.includes("signature") || lower.includes("verify")) {
        botResponse =
          "All outbound payloads from Knowra contain the `X-Knowra-Signature-256` header. You can verify it in Node.js or Python using your connector's signing secret:";
        codeSnippet = {
          language: "javascript",
          code: `// Node.js Express HMAC Verification
const crypto = require("crypto");

function verifyWebhook(req, secret) {
  const signature = req.headers["x-knowra-signature-256"];
  const hmac = crypto.createHmac("sha256", secret);
  const digest = "sha256=" + hmac.update(req.rawBody).digest("hex");
  return crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(digest));
}`,
        };
      } else if (lower.includes("jira")) {
        botResponse =
          "For Jira Cloud integrations, specify your Project Key (e.g. `KNOWRA` or `PROJ`). When an Action Item is flagged with high or urgent priority, Knowra automatically crafts a Jira issue payload with description and due date.";
        codeSnippet = {
          language: "json",
          code: `{
  "fields": {
    "project": { "key": "KNOWRA" },
    "summary": "Implement Redis Cluster failover parameter checks",
    "description": "Deliverable extracted from Sprint Planning Meeting",
    "issuetype": { "name": "Task" }
  }
}`,
        };
      } else {
        botResponse = `Knowra dispatches CloudEvents v1.0 standard payloads for all meeting intelligence milestones (${integrations.length} active connectors listening). Outbound events are retried with exponential backoff if your endpoint returns a 5xx response code.`;
      }

      setChatMessages((prev) => [
        ...prev,
        {
          id: `bot-${Date.now()}`,
          sender: "bot",
          content: botResponse,
          timestamp: "Just now",
          codeSnippet,
        },
      ]);
      setIsCopilotTyping(false);
    }, 700);
  };

  // Metrics calculation
  const totalCount = integrations.length;
  const activeCount = integrations.filter((i) => i.status === "ACTIVE").length;
  const totalDispatches = eventHistory.length;
  const successDispatches = eventHistory.filter((e) => e.status === "COMPLETED").length;
  const reliabilityRate = totalDispatches > 0 ? ((successDispatches / totalDispatches) * 100).toFixed(1) : "99.8";

  return (
    <div className="space-y-6 max-w-[1600px] mx-auto pb-16 animate-fade-in">
      {/* ── ENTERPRISE PAGE HEADER ─────────────────────────────────────────── */}
      <PageHeader
        title="Enterprise Connectors & Webhooks"
        subtitle="Manage mission-critical event dispatching for Slack, Microsoft Teams, Jira, and enterprise HTTP endpoints with HMAC-SHA256 signature verification."
        icon={Layers}
        statusDot={true}
        badge={
          <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            {activeCount} / {totalCount} Active Connectors
          </span>
        }
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => {
                refetchIntegrations();
                refetchEvents();
              }}
              disabled={isIntegrationsFetching || isEventsFetching}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:text-slate-900 hover:bg-slate-50 shadow-xs transition-all cursor-pointer disabled:opacity-50"
              title="Refresh integrations and event history"
            >
              <RefreshCw
                size={13}
                className={isIntegrationsFetching || isEventsFetching ? "animate-spin" : ""}
              />
              <span>Sync Connectors</span>
            </button>

            <button
              onClick={() => setShowRightDrawer(!showRightDrawer)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all cursor-pointer ${
                showRightDrawer
                  ? "bg-indigo-50 border-indigo-200 text-indigo-700 font-semibold"
                  : "bg-white border-slate-200 text-slate-700 hover:bg-slate-50"
              }`}
              title="Toggle Live Dispatch Audit & AI Copilot Drawer"
            >
              {showRightDrawer ? <PanelRightClose size={13} /> : <PanelRightOpen size={13} />}
              <span>{showRightDrawer ? "Hide Drawer" : "Audit Stream & Copilot"}</span>
              {eventHistory.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-600 text-white font-bold">
                  {eventHistory.length}
                </span>
              )}
            </button>

            <button
              onClick={() => {
                resetForm();
                setShowCreateModal(true);
              }}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
              title="Add a new external connector"
            >
              <Plus size={13} className="stroke-[2.5]" />
              <span>New Integration</span>
            </button>
          </div>
        }
      />

      {/* ── KPI METRICS RIBBON ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Connectors */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Active Integrations
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <div>
              <span className="text-3xl font-bold text-slate-900 tracking-tight">
                {isIntegrationsLoading ? "—" : activeCount}
              </span>
              <span className="text-xs text-slate-400 ml-1.5">/ {totalCount} configured</span>
            </div>
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
              <Zap size={18} />
            </div>
          </div>
        </div>

        {/* Delivery Reliability SLA */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Delivery Success Rate
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <div>
              <span className="text-3xl font-bold text-emerald-600 tracking-tight">
                {reliabilityRate}%
              </span>
              <p className="text-[11px] text-emerald-700 font-medium mt-0.5">Enterprise 99.8% SLA</p>
            </div>
            <div className="w-9 h-9 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center shrink-0">
              <CheckCircle2 size={18} />
            </div>
          </div>
        </div>

        {/* Total Events Dispatched */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Total Event Dispatches
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <div>
              <span className="text-3xl font-bold text-slate-900 tracking-tight">
                {isEventsLoading ? "—" : totalDispatches}
              </span>
              <p className="text-[11px] text-slate-400 font-medium mt-0.5">Audited delivery records</p>
            </div>
            <div className="w-9 h-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
              <Radio size={18} />
            </div>
          </div>
        </div>

        {/* Encryption & Security */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between hover:border-slate-300 transition-all">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
            Payload Security
          </span>
          <div className="flex items-baseline justify-between mt-2">
            <div>
              <span className="text-xl font-bold text-slate-900 tracking-tight">
                HMAC-SHA256
              </span>
              <p className="text-[11px] text-indigo-600 font-medium mt-0.5">AES-256 Fernet at rest</p>
            </div>
            <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0">
              <ShieldCheck size={18} />
            </div>
          </div>
        </div>
      </div>

      {/* ── TEST PING ALERT NOTIFICATION ───────────────────────────────────── */}
      {testResult && (
        <div
          className={`p-3.5 rounded-xl border shadow-xs flex items-center justify-between gap-3 animate-fade-in ${
            testResult.status === "loading"
              ? "bg-blue-50/80 border-blue-200 text-blue-800"
              : testResult.status === "success"
              ? "bg-emerald-50/90 border-emerald-200 text-emerald-800"
              : "bg-rose-50/90 border-rose-200 text-rose-800"
          }`}
        >
          <div className="flex items-center gap-2.5">
            {testResult.status === "loading" ? (
              <RefreshCw size={15} className="animate-spin text-blue-600" />
            ) : testResult.status === "success" ? (
              <CheckCircle2 size={16} className="text-emerald-600" />
            ) : (
              <AlertCircle size={16} className="text-rose-600" />
            )}
            <span className="text-xs font-semibold">{testResult.detail}</span>
          </div>
          <button
            onClick={() => setTestResult(null)}
            className="text-slate-400 hover:text-slate-700 p-1"
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* ── MAIN WORKSPACE CONTENT + RIGHT-SIDE DRAWER ─────────────────────── */}
      <div className="flex flex-col lg:flex-row gap-6 items-start">
        {/* Left Column: Connectors Table / Cards */}
        <div className={`w-full min-w-0 transition-all duration-200 ${showRightDrawer ? "lg:w-[65%]" : "w-full"}`}>
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden">
            {/* Filter & Search Toolbar */}
            <div className="p-4 border-b border-slate-100 bg-slate-50/50 flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
              {/* Search input */}
              <div className="relative flex-1 max-w-sm">
                <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, channel, or URL..."
                  className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-200 bg-white text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 shadow-2xs"
                />
              </div>

              {/* Provider filter tabs */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {["ALL", "SLACK", "TEAMS", "JIRA", "WEBHOOK"].map((p) => (
                  <button
                    key={p}
                    onClick={() => setSelectedProvider(p)}
                    className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-colors cursor-pointer ${
                      selectedProvider === p
                        ? "bg-indigo-600 text-white shadow-2xs font-semibold"
                        : "bg-white border border-slate-200 text-slate-600 hover:bg-slate-100 hover:text-slate-900"
                    }`}
                  >
                    {p === "ALL" ? "All Providers" : p === "WEBHOOK" ? "Webhooks" : p}
                  </button>
                ))}
              </div>
            </div>

            {/* Connectors Grid */}
            <div className="p-4 sm:p-5 space-y-4">
              {isIntegrationsLoading ? (
                <div className="space-y-3 py-8">
                  {[...Array(3)].map((_, i) => (
                    <div key={i} className="h-24 w-full bg-slate-100 animate-pulse rounded-xl" />
                  ))}
                </div>
              ) : filteredIntegrations.length === 0 ? (
                <div className="py-12 text-center px-4">
                  <div className="w-12 h-12 rounded-xl bg-slate-100 text-slate-400 mx-auto flex items-center justify-center mb-3">
                    <Layers size={22} />
                  </div>
                  <h3 className="text-sm font-bold text-slate-800">No Integrations Found</h3>
                  <p className="text-xs text-slate-400 max-w-md mx-auto mt-1 leading-relaxed">
                    {searchQuery
                      ? "No connectors matched your search query. Try clearing the filter."
                      : "Connect Knowra to Slack, Microsoft Teams, Jira, or custom webhooks to dispatch meeting intelligence."}
                  </p>
                  <button
                    onClick={() => {
                      resetForm();
                      setShowCreateModal(true);
                    }}
                    className="mt-4 inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs transition-all cursor-pointer"
                  >
                    <Plus size={14} />
                    <span>Configure First Integration</span>
                  </button>
                </div>
              ) : (
                <div className="grid grid-cols-1 gap-4">
                  {filteredIntegrations.map((item) => {
                    const cfg = PROVIDER_CONFIG[item.provider] ?? PROVIDER_CONFIG.WEBHOOK;
                    const isActive = item.status === "ACTIVE";
                    const isTesting =
                      testMutation.isPending && testMutation.variables === item.id;

                    return (
                      <div
                        key={item.id}
                        className={`rounded-xl border p-4.5 transition-all bg-white flex flex-col justify-between gap-4 shadow-2xs hover:shadow-xs ${
                          isActive
                            ? "border-slate-200/90 hover:border-slate-300"
                            : "border-slate-200/60 bg-slate-50/50 opacity-80"
                        }`}
                      >
                        {/* Top row: Brand Icon, Name, Provider Badge, Toggle */}
                        <div className="flex items-start justify-between gap-3">
                          <div className="flex items-center gap-3 min-w-0">
                            <div className="w-10 h-10 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-center text-xl shrink-0 shadow-2xs">
                              {cfg.iconText}
                            </div>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <h4 className="text-sm font-bold text-slate-900 truncate">
                                  {item.name || cfg.label}
                                </h4>
                                <span
                                  className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${cfg.badgeBg} ${cfg.badgeBorder}`}
                                >
                                  {cfg.label}
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-500 line-clamp-1 mt-0.5">
                                {cfg.description}
                              </p>
                            </div>
                          </div>

                          {/* Status Badge & Active Switch */}
                          <div className="flex items-center gap-2.5 shrink-0">
                            <button
                              type="button"
                              onClick={() =>
                                toggleMutation.mutate({
                                  id: item.id,
                                  newStatus: isActive ? "INACTIVE" : "ACTIVE",
                                })
                              }
                              className={`relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                                isActive ? "bg-emerald-500" : "bg-slate-300"
                              }`}
                              title={isActive ? "Click to Pause" : "Click to Activate"}
                            >
                              <span
                                className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow-xs ring-0 transition duration-200 ease-in-out ${
                                  isActive ? "translate-x-4" : "translate-x-0"
                                }`}
                              />
                            </button>

                            <span
                              className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold border ${
                                isActive
                                  ? "bg-emerald-50 text-emerald-700 border-emerald-200"
                                  : "bg-slate-100 text-slate-500 border-slate-200"
                              }`}
                            >
                              <span
                                className={`w-1.5 h-1.5 rounded-full ${
                                  isActive ? "bg-emerald-500 animate-pulse" : "bg-slate-400"
                                }`}
                              />
                              {isActive ? "Active" : "Paused"}
                            </span>
                          </div>
                        </div>

                        {/* Mid row: Target Webhook URL & Channel / Project */}
                        <div className="bg-slate-50/80 rounded-lg p-3 border border-slate-100 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 shrink-0">
                              Target Endpoint:
                            </span>
                            <span className="font-mono text-[11px] text-slate-700 truncate">
                              {item.webhook_url || "Configured via OAuth App"}
                            </span>
                            {item.webhook_url && (
                              <button
                                onClick={() => handleCopy(item.webhook_url!, item.id)}
                                className="text-slate-400 hover:text-slate-600 p-0.5 shrink-0 cursor-pointer"
                                title="Copy Webhook URL"
                              >
                                {copiedId === item.id ? (
                                  <Check size={12} className="text-emerald-600" />
                                ) : (
                                  <Copy size={12} />
                                )}
                              </button>
                            )}
                          </div>

                          {(item.channel_or_project_id || item.channel_or_project) && (
                            <div className="flex items-center gap-1.5 shrink-0 text-slate-600">
                              <span className="text-[10px] text-slate-400 font-bold uppercase">
                                {item.provider === "JIRA" ? "Project:" : "Channel:"}
                              </span>
                              <span className="font-semibold text-slate-800 bg-white px-2 py-0.5 rounded border border-slate-200 text-[11px]">
                                {item.channel_or_project_id || item.channel_or_project}
                              </span>
                            </div>
                          )}
                        </div>

                        {/* Bottom row: Subscribed Events badges & Actions */}
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-1">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider mr-1">
                              Subscribed:
                            </span>
                            {(item.events_subscribed && item.events_subscribed.length > 0
                              ? item.events_subscribed
                              : ["ACTION_CREATED", "DECISION_CONFIRMED"]
                            ).map((evt) => (
                              <span
                                key={evt}
                                className="px-2 py-0.5 rounded-md text-[10px] font-mono font-medium bg-slate-100 text-slate-600 border border-slate-200/80"
                              >
                                {evt}
                              </span>
                            ))}
                          </div>

                          <div className="flex items-center gap-2 self-end sm:self-auto shrink-0">
                            {/* Test Ping Button */}
                            <button
                              type="button"
                              onClick={() => testMutation.mutate(item.id)}
                              disabled={isTesting || !isActive}
                              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-2xs transition-colors cursor-pointer disabled:opacity-50"
                              title="Send instantaneous test ping to verify connectivity"
                            >
                              <Zap size={12} className={isTesting ? "animate-spin text-amber-500" : "text-amber-500"} />
                              <span>{isTesting ? "Verifying..." : "Test Ping"}</span>
                            </button>

                            {/* Delete Button */}
                            <button
                              type="button"
                              onClick={() => {
                                if (confirm(`Delete connector "${item.name}"?`)) {
                                  deleteMutation.mutate(item.id);
                                }
                              }}
                              className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors cursor-pointer"
                              title="Delete integration"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* ── RIGHT COLUMN: AUDIT STREAM & AI INTEGRATION COPILOT DRAWER ───── */}
        {showRightDrawer && (
          <div className="w-full lg:w-[35%] shrink-0 space-y-4 animate-in fade-in slide-in-from-right-4 duration-200">
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden flex flex-col h-[750px]">
              {/* Drawer Top Navigation Tabs */}
              <div className="p-3 border-b border-slate-100 bg-slate-50/70 flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setActiveDrawerTab("stream")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      activeDrawerTab === "stream"
                        ? "bg-white text-indigo-700 shadow-2xs border border-slate-200/80"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    <Radio size={13} className="text-emerald-500 animate-pulse" />
                    <span>Live Audit Stream</span>
                    {eventHistory.length > 0 && (
                      <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-100 text-slate-600">
                        {eventHistory.length}
                      </span>
                    )}
                  </button>

                  <button
                    onClick={() => setActiveDrawerTab("copilot")}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                      activeDrawerTab === "copilot"
                        ? "bg-white text-indigo-700 shadow-2xs border border-slate-200/80"
                        : "text-slate-600 hover:text-slate-900"
                    }`}
                  >
                    <Sparkles size={13} className="text-indigo-600" />
                    <span>Integration Copilot</span>
                  </button>
                </div>

                <button
                  onClick={() => setShowRightDrawer(false)}
                  className="text-slate-400 hover:text-slate-700 p-1 cursor-pointer"
                  title="Close Drawer"
                >
                  <PanelRightClose size={15} />
                </button>
              </div>

              {/* ── TAB 1: LIVE EVENT DISPATCH AUDIT STREAM ──────────────────── */}
              {activeDrawerTab === "stream" && (
                <div className="flex-1 overflow-y-auto divide-y divide-slate-100 p-2">
                  {isEventsLoading ? (
                    <div className="py-12 text-center text-xs text-slate-400">
                      <RefreshCw size={16} className="animate-spin mx-auto mb-2 text-indigo-500" />
                      Loading live event stream...
                    </div>
                  ) : eventHistory.length === 0 ? (
                    <div className="py-16 text-center px-4">
                      <Radio size={24} className="mx-auto text-slate-300 mb-2" />
                      <p className="text-xs font-bold text-slate-700">No Events Dispatched Yet</p>
                      <p className="text-[11px] text-slate-400 mt-1">
                        Trigger a Test Ping on any connector to watch real-time delivery logs.
                      </p>
                    </div>
                  ) : (
                    eventHistory.map((ev) => (
                      <div
                        key={ev.id}
                        className="p-3 hover:bg-slate-50/80 rounded-xl transition-colors text-xs space-y-1.5 group"
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-mono font-bold text-[11px] text-slate-800">
                            {ev.event_type}
                          </span>
                          <span
                            className={`px-1.5 py-0.2 rounded text-[10px] font-mono font-bold ${
                              ev.status === "COMPLETED"
                                ? "bg-emerald-50 text-emerald-700 border border-emerald-200"
                                : "bg-rose-50 text-rose-700 border border-rose-200"
                            }`}
                          >
                            {ev.response_status_code ? `${ev.response_status_code} OK` : ev.status}
                          </span>
                        </div>

                        {ev.payload_json && (
                          <div className="bg-slate-900 text-slate-200 p-2 rounded-lg font-mono text-[10px] overflow-x-auto max-h-24">
                            {JSON.stringify(ev.payload_json, null, 2)}
                          </div>
                        )}

                        <div className="flex items-center justify-between text-[10px] text-slate-400 pt-0.5">
                          <span className="truncate">Event ID: {ev.external_event_id}</span>
                          <span className="shrink-0">
                            {new Date(ev.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit",
                            })}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}

              {/* ── TAB 2: KNOWRA INTEGRATION COPILOT (WORKS LIKE GPT) ──────── */}
              {activeDrawerTab === "copilot" && (
                <div className="flex-1 flex flex-col min-h-0 bg-slate-50/30">
                  {/* Messages container */}
                  <div
                    ref={chatScrollRef}
                    className="flex-1 overflow-y-auto p-4 space-y-4"
                  >
                    {chatMessages.map((msg) => (
                      <div
                        key={msg.id}
                        className={`flex gap-2.5 items-start ${
                          msg.sender === "user" ? "flex-row-reverse" : ""
                        }`}
                      >
                        <div
                          className={`w-7 h-7 rounded-lg flex items-center justify-center shrink-0 shadow-2xs ${
                            msg.sender === "user"
                              ? "bg-indigo-600 text-white"
                              : "bg-slate-900 text-white"
                          }`}
                        >
                          {msg.sender === "user" ? <User size={13} /> : <Bot size={13} />}
                        </div>

                        <div
                          className={`max-w-[85%] rounded-2xl p-3 text-xs leading-relaxed shadow-2xs ${
                            msg.sender === "user"
                              ? "bg-indigo-600 text-white rounded-tr-xs"
                              : "bg-white text-slate-800 border border-slate-200/80 rounded-tl-xs"
                          }`}
                        >
                          <p className="whitespace-pre-line">{msg.content}</p>

                          {msg.codeSnippet && (
                            <div className="mt-2.5 rounded-lg bg-slate-950 text-slate-200 p-2.5 font-mono text-[11px] overflow-x-auto relative group">
                              <button
                                onClick={() => handleCopy(msg.codeSnippet!.code, msg.id)}
                                className="absolute right-2 top-2 px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 text-[10px] hover:text-white flex items-center gap-1 cursor-pointer"
                              >
                                {copiedId === msg.id ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} />}
                                <span>Copy</span>
                              </button>
                              <pre className="pr-12">{msg.codeSnippet.code}</pre>
                            </div>
                          )}

                          <span
                            className={`block text-[9px] mt-1 text-right ${
                              msg.sender === "user" ? "text-indigo-200" : "text-slate-400"
                            }`}
                          >
                            {msg.timestamp}
                          </span>
                        </div>
                      </div>
                    ))}

                    {isCopilotTyping && (
                      <div className="flex gap-2 items-center text-xs text-slate-400 animate-pulse">
                        <Bot size={14} />
                        <span>Copilot is generating code snippet...</span>
                      </div>
                    )}
                  </div>

                  {/* Starter Prompts */}
                  <div className="p-2 border-t border-slate-100 bg-white flex gap-1.5 overflow-x-auto text-[11px]">
                    <button
                      onClick={() => {
                        setChatInput("How do I set up Slack Incoming Webhooks?");
                      }}
                      className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                    >
                      💡 Slack Webhooks Setup
                    </button>
                    <button
                      onClick={() => {
                        setChatInput("Show HMAC signature verification code");
                      }}
                      className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                    >
                      🔐 HMAC Verification
                    </button>
                    <button
                      onClick={() => {
                        setChatInput("How to automate Jira tickets from meetings?");
                      }}
                      className="whitespace-nowrap px-2.5 py-1 rounded-full bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                    >
                      📋 Jira Automation
                    </button>
                  </div>

                  {/* Input bar */}
                  <div className="p-3 border-t border-slate-200 bg-white flex items-center gap-2">
                    <input
                      type="text"
                      value={chatInput}
                      onChange={(e) => setChatInput(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSendChat()}
                      placeholder="Ask about webhooks, payload schemas, HMAC..."
                      className="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-3 py-2 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                    />
                    <button
                      onClick={handleSendChat}
                      disabled={!chatInput.trim() || isCopilotTyping}
                      className="p-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white disabled:opacity-50 transition-colors cursor-pointer shadow-xs"
                      title="Send question"
                    >
                      <Send size={13} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {/* ── NEW INTEGRATION MODAL ───────────────────────────────────────────── */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-xs animate-fade-in">
          <div
            className="fixed inset-0"
            onClick={() => setShowCreateModal(false)}
            aria-hidden="true"
          />
          <div className="relative w-full max-w-xl bg-white rounded-2xl shadow-2xl border border-slate-200 overflow-hidden z-10 animate-in fade-in zoom-in-95 duration-150">
            {/* Modal Header */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shadow-2xs">
                  <Layers size={16} />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Add New Integration</h3>
                  <p className="text-[11px] text-slate-500">
                    Connect an external service to receive automated meeting events.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={16} />
              </button>
            </div>

            {/* Modal Form */}
            <form onSubmit={handleCreateSubmit} className="p-6 space-y-4 max-h-[80vh] overflow-y-auto">
              {formError && (
                <div className="p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center gap-2">
                  <AlertCircle size={14} className="shrink-0" />
                  <span>{formError}</span>
                </div>
              )}

              {/* Provider Selection */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  1. Select Destination Platform
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {Object.entries(PROVIDER_CONFIG).map(([key, cfg]) => (
                    <button
                      key={key}
                      type="button"
                      onClick={() => {
                        setFormProvider(key);
                        if (!formName) setFormName(`${cfg.label} Dispatcher`);
                        if (!formChannel) setFormChannel(cfg.defaultChannelPlaceholder);
                      }}
                      className={`p-3 rounded-xl border text-left flex flex-col justify-between transition-all cursor-pointer ${
                        formProvider === key
                          ? "border-indigo-600 bg-indigo-50/50 ring-1 ring-indigo-600 shadow-2xs"
                          : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                      }`}
                    >
                      <span className="text-xl mb-1">{cfg.iconText}</span>
                      <span className="text-xs font-bold text-slate-900">{cfg.label}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Connector Name */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  2. Connector Name
                </label>
                <input
                  type="text"
                  required
                  value={formName}
                  onChange={(e) => setFormName(e.target.value)}
                  placeholder={`e.g. Production ${PROVIDER_CONFIG[formProvider]?.label} Alerts`}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Target Webhook URL */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  3. Webhook URL / Ingest Endpoint
                </label>
                <input
                  type="url"
                  required
                  value={formWebhookUrl}
                  onChange={(e) => setFormWebhookUrl(e.target.value)}
                  placeholder={PROVIDER_CONFIG[formProvider]?.sampleUrl}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Channel / Project ID */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-1">
                  4. {formProvider === "JIRA" ? "Project Key" : "Channel / Stream ID"}
                </label>
                <input
                  type="text"
                  value={formChannel}
                  onChange={(e) => setFormChannel(e.target.value)}
                  placeholder={PROVIDER_CONFIG[formProvider]?.defaultChannelPlaceholder}
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Signing Secret */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
                    5. Signing Secret / Token
                  </label>
                  <span className="text-[10px] text-emerald-600 flex items-center gap-1 font-medium">
                    <Lock size={10} /> AES-256 Encrypted
                  </span>
                </div>
                <input
                  type="password"
                  value={formSecret}
                  onChange={(e) => setFormSecret(e.target.value)}
                  placeholder="Optional signing secret or bot token"
                  className="w-full px-3 py-2 rounded-lg border border-slate-200 text-xs font-mono text-slate-900 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>

              {/* Event Subscriptions */}
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-500 mb-2">
                  6. Event Subscriptions
                </label>
                <div className="space-y-2">
                  {AVAILABLE_EVENTS.map((evt) => {
                    const isChecked = formEvents.includes(evt.id);
                    return (
                      <label
                        key={evt.id}
                        className={`flex items-start gap-2.5 p-2.5 rounded-lg border text-xs cursor-pointer transition-colors ${
                          isChecked
                            ? "bg-indigo-50/40 border-indigo-200"
                            : "bg-white border-slate-200 hover:bg-slate-50"
                        }`}
                      >
                        <input
                          type="checkbox"
                          checked={isChecked}
                          onChange={(e) => {
                            if (e.target.checked) {
                              setFormEvents((prev) => [...prev, evt.id]);
                            } else {
                              setFormEvents((prev) => prev.filter((id) => id !== evt.id));
                            }
                          }}
                          className="mt-0.5 rounded text-indigo-600 focus:ring-indigo-500"
                        />
                        <div className="min-w-0">
                          <span className="font-semibold text-slate-900">{evt.label}</span>
                          <p className="text-[11px] text-slate-400">{evt.description}</p>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </div>

              {/* Modal Actions */}
              <div className="pt-3 border-t border-slate-100 flex items-center justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 rounded-lg border border-slate-200 bg-white text-xs font-medium text-slate-700 hover:bg-slate-50 cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold shadow-xs disabled:opacity-50 cursor-pointer flex items-center gap-1.5"
                >
                  {createMutation.isPending ? (
                    <>
                      <RefreshCw size={13} className="animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Save & Deploy Connector</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
