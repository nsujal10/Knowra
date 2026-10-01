"use client";

import React, { useState } from "react";
import { useSession } from "@/lib/auth/session";
import { PageHeader } from "@/components/ui/page-header";
import { toast } from "@/components/ui/toast";
import {
  User,
  Building,
  Cpu,
  ShieldCheck,
  Bell,
  Key,
  Copy,
  Check,
  Plus,
  Trash2,
  Lock,
  RefreshCw,
  Sliders,
  Globe,
  Sparkles,
  Clock,
  Settings,
  Save,
  Layers,
  Eye,
  EyeOff,
  Sun,
  Moon,
  Laptop,
  Users,
  CheckCircle2,
  AlertCircle,
  ExternalLink,
  Shield,
  Zap,
} from "lucide-react";

type SettingsTab = "general" | "workspace" | "transcription" | "security" | "notifications";

const TABS: { id: SettingsTab; label: string; icon: React.ElementType }[] = [
  { id: "general", label: "Profile & Identity", icon: User },
  { id: "workspace", label: "Workspace & Team", icon: Building },
  { id: "transcription", label: "AI & Speech Engine", icon: Cpu },
  { id: "security", label: "Security & RBAC", icon: ShieldCheck },
  { id: "notifications", label: "Notifications & Bots", icon: Bell },
];

export default function SettingsPage() {
  const { session, logout } = useSession();
  const [activeTab, setActiveTab] = useState<SettingsTab>("general");

  // ── General Profile State ──────────────────────────────────────────────────
  const [fullName, setFullName] = useState(session?.user?.full_name || "Sujal Nage");
  const [email, setEmail] = useState(session?.user?.email || "sujal.nage@softude.com");
  const [jobTitle, setJobTitle] = useState("Lead Platform Architect");
  const [department, setDepartment] = useState("Core Engineering");
  const [theme, setTheme] = useState<"light" | "system" | "dark">("light");

  // ── Workspace State ────────────────────────────────────────────────────────
  const [workspaceName, setWorkspaceName] = useState("Softude Enterprise AI");
  const [workspaceDomain, setWorkspaceDomain] = useState("softude.com");
  const [tenantId] = useState(session?.tenantId || "t-98a7-softude-core-us-east-1");
  const [copiedTenant, setCopiedTenant] = useState(false);

  // ── AI & Transcription Engine State ────────────────────────────────────────
  const [sttModel, setSttModel] = useState("whisper-large-v3-gpu");
  const [diarizationSensitivity, setDiarizationSensitivity] = useState(85);
  const [summaryDetail, setSummaryDetail] = useState<"concise" | "balanced" | "comprehensive">("balanced");
  const [glossaryTerms, setGlossaryTerms] = useState<string[]>([
    "MinIO",
    "PostgreSQL",
    "HNSW",
    "Keycloak",
    "FastAPI",
    "LangChain",
    "Kubernetes",
    "Diarization",
  ]);
  const [newGlossaryTerm, setNewGlossaryTerm] = useState("");

  // ── Security & RBAC State ──────────────────────────────────────────────────
  const [sessionTimeout, setSessionTimeout] = useState("8h");
  const [enforce2FA, setEnforce2FA] = useState(true);
  const [apiKeyMasked, setApiKeyMasked] = useState(true);
  const [apiKey] = useState("knw_live_84f923b0a7c41e88d29b0a7f");
  const [copiedKey, setCopiedKey] = useState(false);

  // ── Notifications & Auto-Record State ──────────────────────────────────────
  const [notetakerMode, setNotetakerMode] = useState<"all" | "internal" | "invited">("all");
  const [emailDigest, setEmailDigest] = useState<"instant" | "daily" | "weekly">("instant");
  const [slackAlerts, setSlackAlerts] = useState(true);
  const [autoExportNotion, setAutoExportNotion] = useState(false);

  const handleSave = () => {
    toast.success("Settings saved and propagated across workspace");
  };

  const handleCopyTenant = () => {
    navigator.clipboard?.writeText(tenantId);
    setCopiedTenant(true);
    toast.success("Tenant ID copied to clipboard");
    setTimeout(() => setCopiedTenant(false), 2000);
  };

  const handleCopyApiKey = () => {
    navigator.clipboard?.writeText(apiKey);
    setCopiedKey(true);
    toast.success("API Key copied to clipboard");
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handleAddGlossaryTerm = (e: React.FormEvent) => {
    e.preventDefault();
    const term = newGlossaryTerm.trim();
    if (!term) return;
    if (glossaryTerms.includes(term)) {
      toast.info(`"${term}" is already in your domain glossary`);
      return;
    }
    setGlossaryTerms((prev) => [...prev, term]);
    setNewGlossaryTerm("");
    toast.success(`Added "${term}" to custom speech vocabulary`);
  };

  const handleRemoveGlossaryTerm = (termToRemove: string) => {
    setGlossaryTerms((prev) => prev.filter((t) => t !== termToRemove));
  };

  return (
    <div className="w-full min-w-0 flex-1 overflow-x-hidden">
      <div className="w-full max-w-[1600px] mx-auto flex flex-col gap-5 pb-16">
        {/* ── 1. ENTERPRISE PAGE HEADER ────────────────────────────────────────── */}
        <PageHeader
          title="Settings"
          subtitle="Manage organizational identity, speech transcription engine, security compliance, and team automation."
          icon={Settings}
          statusDot={true}
          badge={
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
              {session?.user?.role_code || "Admin"} Access · Tenant Isolated
            </span>
          }
          actions={
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleSave}
                className="inline-flex items-center gap-1.5 h-9 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold shadow-xs hover:shadow-sm transition-all active:scale-95 cursor-pointer"
              >
                <Save size={14} />
                <span>Save Changes</span>
              </button>
            </div>
          }
        />

        {/* ── 2. METRIC KPI RIBBON ───────────────────────────────────────────── */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Active Plan */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Current Plan
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">Enterprise</span>
                <p className="text-[11px] text-indigo-600 font-medium">Dedicated GPU Cluster</p>
              </div>
              <div className="bg-indigo-50 text-indigo-600 p-2 rounded-lg shrink-0">
                <Zap size={18} />
              </div>
            </div>
          </div>

          {/* Security Compliance */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Security Compliance
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-2xl font-bold text-emerald-600 tracking-tight">SOC2 Type II</span>
                <p className="text-[11px] text-emerald-600 font-medium">100% Policy Pass Rate</p>
              </div>
              <div className="bg-emerald-50 text-emerald-600 p-2 rounded-lg shrink-0">
                <ShieldCheck size={18} />
              </div>
            </div>
          </div>

          {/* Team Seats */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Seat Utilization
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">14 / 25</span>
                <p className="text-[11px] text-slate-500 font-medium">11 seats available</p>
              </div>
              <div className="bg-blue-50 text-blue-600 p-2 rounded-lg shrink-0">
                <Users size={18} />
              </div>
            </div>
          </div>

          {/* Data Partition */}
          <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-4.5 flex flex-col justify-between h-28 hover:border-slate-300 transition-all">
            <span className="text-xs font-semibold text-slate-500 tracking-wider uppercase">
              Data Boundary
            </span>
            <div className="flex items-baseline justify-between mt-1">
              <div className="space-y-0.5">
                <span className="text-2xl font-bold text-slate-900 tracking-tight">US-East</span>
                <p className="text-[11px] text-purple-600 font-medium">AWS KMS Encrypted</p>
              </div>
              <div className="bg-purple-50 text-purple-600 p-2 rounded-lg shrink-0">
                <Globe size={18} />
              </div>
            </div>
          </div>
        </div>

        {/* ── 3. TABS NAVIGATION ─────────────────────────────────────────────── */}
        <div className="flex items-center gap-1.5 overflow-x-auto bg-white p-1.5 rounded-xl border border-slate-200 shadow-xs">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-all cursor-pointer whitespace-nowrap ${
                  active
                    ? "bg-indigo-50 text-indigo-700 shadow-2xs font-bold"
                    : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
                }`}
              >
                <Icon size={14} className={active ? "text-indigo-600" : "text-slate-400"} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* ── 4. TAB CONTENTS ─────────────────────────────────────────────────── */}

        {/* TAB 1: Profile & Identity */}
        {activeTab === "general" && (
          <div className="space-y-5 animate-in fade-in duration-200">
            {/* User Profile Card */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-5">
              <div className="flex items-start justify-between gap-4 pb-4 border-b border-slate-100">
                <div className="flex items-center gap-4">
                  <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white flex items-center justify-center font-bold text-xl shadow-md">
                    {fullName
                      .split(" ")
                      .map((n) => n[0])
                      .slice(0, 2)
                      .join("")}
                  </div>
                  <div>
                    <h2 className="text-base font-bold text-slate-900">{fullName}</h2>
                    <p className="text-xs text-slate-500 mt-0.5">{email}</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-50 text-indigo-700 border border-indigo-200">
                        {session?.user?.role_code || "Admin"}
                      </span>
                      <span className="text-[11px] text-slate-400 font-mono">
                        ID: {session?.user?.id?.slice(0, 12) || "usr-018f92"}...
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => toast.info("Avatar update enabled via Enterprise SSO")}
                  className="px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors cursor-pointer"
                >
                  Change Avatar
                </button>
              </div>

              {/* Form Fields */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Email Address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Job Title / Role</label>
                  <input
                    type="text"
                    value={jobTitle}
                    onChange={(e) => setJobTitle(e.target.value)}
                    className="w-full h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Department</label>
                  <input
                    type="text"
                    value={department}
                    onChange={(e) => setDepartment(e.target.value)}
                    className="w-full h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>
              </div>
            </div>

            {/* Appearance Preferences */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Interface & Theme</h3>
                <p className="text-xs text-slate-500 mt-0.5">Customize your preferred display mode and contrast</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                <button
                  type="button"
                  onClick={() => {
                    setTheme("light");
                    toast.success("Switched to Light theme");
                  }}
                  className={`p-3.5 rounded-xl border text-left flex items-start gap-3 transition-all cursor-pointer ${
                    theme === "light"
                      ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                      : "border-slate-200 hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 text-amber-500 flex items-center justify-center shrink-0">
                    <Sun size={16} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      Light Slate
                      {theme === "light" && <Check size={12} className="text-indigo-600 stroke-[3]" />}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Clean enterprise daylight</p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setTheme("system");
                    toast.info("Using system preferences");
                  }}
                  className={`p-3.5 rounded-xl border text-left flex items-start gap-3 transition-all cursor-pointer ${
                    theme === "system"
                      ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                      : "border-slate-200 hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 text-slate-600 flex items-center justify-center shrink-0">
                    <Laptop size={16} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      System Sync
                      {theme === "system" && <Check size={12} className="text-indigo-600 stroke-[3]" />}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Adapts to OS settings</p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setTheme("dark");
                    toast.info("Dark theme available in next minor release");
                  }}
                  className={`p-3.5 rounded-xl border text-left flex items-start gap-3 transition-all cursor-pointer ${
                    theme === "dark"
                      ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                      : "border-slate-200 hover:border-slate-300 bg-white"
                  }`}
                >
                  <div className="w-8 h-8 rounded-lg bg-white border border-slate-200 text-indigo-500 flex items-center justify-center shrink-0">
                    <Moon size={16} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                      Dark Contrast
                      {theme === "dark" && <Check size={12} className="text-indigo-600 stroke-[3]" />}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-0.5">Low-light palette</p>
                  </div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: Workspace & Team */}
        {activeTab === "workspace" && (
          <div className="space-y-5 animate-in fade-in duration-200">
            {/* Organization Metadata */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-5">
              <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Workspace Details</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Global configuration and team boundary</p>
                </div>
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                  Active & Healthy
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Organization Name</label>
                  <input
                    type="text"
                    value={workspaceName}
                    onChange={(e) => setWorkspaceName(e.target.value)}
                    className="w-full h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-700">Enforced Email Domain</label>
                  <div className="flex items-center gap-1.5 bg-slate-50 border border-slate-200 rounded-lg px-3 h-9 text-xs text-slate-700">
                    <span>@</span>
                    <input
                      type="text"
                      value={workspaceDomain}
                      onChange={(e) => setWorkspaceDomain(e.target.value)}
                      className="bg-transparent border-none outline-none font-medium flex-1 text-slate-900"
                    />
                  </div>
                </div>
              </div>

              {/* Tenant ID Row with Copy */}
              <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div className="space-y-0.5">
                  <span className="text-xs font-bold text-slate-800">Partitioned Tenant Identifier</span>
                  <p className="text-[11px] text-slate-500 font-mono">{tenantId}</p>
                </div>
                <button
                  type="button"
                  onClick={handleCopyTenant}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-100 text-xs font-semibold text-slate-700 transition-colors shrink-0 cursor-pointer"
                >
                  {copiedTenant ? (
                    <>
                      <Check size={13} className="text-emerald-600" />
                      <span className="text-emerald-600 font-bold">Copied</span>
                    </>
                  ) : (
                    <>
                      <Copy size={13} />
                      <span>Copy Tenant ID</span>
                    </>
                  )}
                </button>
              </div>

              {/* Data Storage & Retention Specs */}
              <div className="divide-y divide-slate-100 text-xs pt-1">
                <div className="py-2.5 flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Data Storage Tier</span>
                  <span className="font-semibold text-slate-900">AWS S3 Single-Tenant Bucket (Encrypted)</span>
                </div>
                <div className="py-2.5 flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Transcript Archival Period</span>
                  <span className="font-semibold text-slate-900">Indefinite (Configured for Enterprise Legal Hold)</span>
                </div>
                <div className="py-2.5 flex justify-between items-center">
                  <span className="text-slate-500 font-medium">Raw Audio Stream Retention</span>
                  <span className="font-semibold text-slate-900">90 Days Auto-Purge (PII Compliance)</span>
                </div>
              </div>
            </div>

            {/* Team Members Snapshot */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Active Teammates</h3>
                  <p className="text-xs text-slate-500 mt-0.5">Manage permissions and team seats</p>
                </div>
                <button
                  type="button"
                  onClick={() => toast.info("Team invitation link generated")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-indigo-50 text-indigo-700 hover:bg-indigo-100 text-xs font-semibold border border-indigo-200 transition-colors cursor-pointer"
                >
                  <Plus size={13} />
                  <span>Invite Teammate</span>
                </button>
              </div>

              <div className="divide-y divide-slate-100">
                {[
                  { name: "Sujal Nage", email: "sujal.nage@softude.com", role: "Owner / Admin", status: "Active" },
                  { name: "Alison Barker", email: "alison.b@softude.com", role: "Member", status: "Active" },
                  { name: "Eliab Sisay", email: "eliab.s@softude.com", role: "Member", status: "Active" },
                  { name: "Kelcey Hawthorne", email: "kelcey.h@softude.com", role: "Viewer", status: "Active" },
                ].map((member) => (
                  <div key={member.email} className="py-3 flex items-center justify-between gap-3 text-xs">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 flex items-center justify-center font-bold text-xs">
                        {member.name.split(" ").map((n) => n[0]).join("")}
                      </div>
                      <div>
                        <p className="font-bold text-slate-900">{member.name}</p>
                        <p className="text-slate-500 text-[11px]">{member.email}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                        {member.role}
                      </span>
                      <span className="w-2 h-2 rounded-full bg-emerald-500" title="Online" />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: AI & Speech Models */}
        {activeTab === "transcription" && (
          <div className="space-y-5 animate-in fade-in duration-200">
            {/* Speech-to-Text Model Config */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-5">
              <div className="pb-3 border-b border-slate-100 flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Transcription & Diarization Pipeline</h3>
                  <p className="text-xs text-slate-500 mt-0.5">High-fidelity speech synthesis and speaker identification parameters</p>
                </div>
                <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200">
                  GPU Accelerated
                </span>
              </div>

              {/* Model Choice */}
              <div className="space-y-2">
                <label className="text-xs font-semibold text-slate-700">Speech-to-Text Model</label>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setSttModel("whisper-large-v3-gpu")}
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      sttModel === "whisper-large-v3-gpu"
                        ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-slate-900">Whisper Large-v3 (Dedicated GPU)</span>
                      {sttModel === "whisper-large-v3-gpu" && <Check size={14} className="text-indigo-600 stroke-[3]" />}
                    </div>
                    <p className="text-[11px] text-slate-500">Sub-word accuracy, 99+ languages, zero tenant leakage</p>
                  </button>

                  <button
                    type="button"
                    onClick={() => setSttModel("openai-whisper-api")}
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      sttModel === "openai-whisper-api"
                        ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs font-bold text-slate-900">OpenAI Whisper Cloud API</span>
                      {sttModel === "openai-whisper-api" && <Check size={14} className="text-indigo-600 stroke-[3]" />}
                    </div>
                    <p className="text-[11px] text-slate-500">Cloud-hosted fallback with zero-data-retention agreement</p>
                  </button>
                </div>
              </div>

              {/* Speaker Diarization Sensitivity Slider */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <div className="flex items-center justify-between">
                  <label className="text-xs font-semibold text-slate-700">
                    Speaker Diarization Sensitivity: <strong className="text-indigo-600">{diarizationSensitivity}%</strong>
                  </label>
                  <span className="text-[11px] text-slate-400">PyAnnote v3.1 Neural Clustering</span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="100"
                  value={diarizationSensitivity}
                  onChange={(e) => setDiarizationSensitivity(Number(e.target.value))}
                  className="w-full h-1.5 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-indigo-600"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-medium">
                  <span>Permissive (Group overlap)</span>
                  <span>Balanced</span>
                  <span>Strict (Isolate subtle shifts)</span>
                </div>
              </div>

              {/* Executive Summary Detail Choice */}
              <div className="space-y-2 pt-2 border-t border-slate-100">
                <label className="text-xs font-semibold text-slate-700">Default Recap Synthesis Depth</label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {[
                    { id: "concise", label: "Concise", desc: "Bullet-point key decisions & actions" },
                    { id: "balanced", label: "Balanced", desc: "Contextual narrative with discussion highlights" },
                    { id: "comprehensive", label: "Comprehensive", desc: "Detailed transcript chapter breakdowns" },
                  ].map((lvl) => (
                    <button
                      key={lvl.id}
                      type="button"
                      onClick={() => setSummaryDetail(lvl.id as any)}
                      className={`p-3 rounded-xl border text-left transition-all cursor-pointer ${
                        summaryDetail === lvl.id
                          ? "border-indigo-600 bg-indigo-50/50"
                          : "border-slate-200 hover:border-slate-300 bg-white"
                      }`}
                    >
                      <p className="text-xs font-bold text-slate-900">{lvl.label}</p>
                      <p className="text-[11px] text-slate-500 mt-0.5">{lvl.desc}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Custom Corporate Glossary & Domain Vocabulary */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Custom Domain Vocabulary & Acronyms</h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Boost speech-to-text accuracy for internal company tools, acronyms, and product codenames.
                </p>
              </div>

              {/* Add term input */}
              <form onSubmit={handleAddGlossaryTerm} className="flex gap-2">
                <input
                  type="text"
                  value={newGlossaryTerm}
                  onChange={(e) => setNewGlossaryTerm(e.target.value)}
                  placeholder="e.g. Spanner, MinIO, GraphQL, Apollo..."
                  className="flex-1 h-9 px-3 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-900 font-medium focus:bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 outline-none transition-all"
                />
                <button
                  type="submit"
                  disabled={!newGlossaryTerm.trim()}
                  className="inline-flex items-center gap-1.5 px-3.5 h-9 bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white rounded-lg text-xs font-semibold transition-all cursor-pointer"
                >
                  <Plus size={14} />
                  <span>Add Term</span>
                </button>
              </form>

              {/* Terms chip list */}
              <div className="flex flex-wrap gap-2 pt-1">
                {glossaryTerms.map((term) => (
                  <span
                    key={term}
                    className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-xs font-medium text-slate-800"
                  >
                    <span>{term}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveGlossaryTerm(term)}
                      className="text-slate-400 hover:text-rose-600 cursor-pointer"
                    >
                      <Trash2 size={12} />
                    </button>
                  </span>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 4: Security & RBAC */}
        {activeTab === "security" && (
          <div className="space-y-5 animate-in fade-in duration-200">
            {/* RBAC Role Permissions Matrix */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Role-Based Access Control (RBAC)</h3>
                <p className="text-xs text-slate-500 mt-0.5">Enforced at database SQL predicate and API gateway levels</p>
              </div>

              <div className="border border-slate-200 rounded-xl overflow-hidden shadow-2xs">
                <table className="w-full text-left text-xs border-collapse">
                  <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider text-[10px]">
                    <tr>
                      <th className="py-2.5 px-4">Permission Scope</th>
                      <th className="py-2.5 px-4 text-center">Viewer</th>
                      <th className="py-2.5 px-4 text-center">Member</th>
                      <th className="py-2.5 px-4 text-center">Admin / Owner</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    <tr>
                      <td className="py-2.5 px-4 font-semibold text-slate-900">View Public Transcripts & Summaries</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-4 font-semibold text-slate-900">Upload & Ingest Audio Recordings</td>
                      <td className="py-2.5 px-4 text-center text-slate-300">—</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-4 font-semibold text-slate-900">Toggle Action Deliverable Status</td>
                      <td className="py-2.5 px-4 text-center text-slate-300">—</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-4 font-semibold text-slate-900">Connect Workspace Integrations & Calendars</td>
                      <td className="py-2.5 px-4 text-center text-slate-300">—</td>
                      <td className="py-2.5 px-4 text-center text-slate-300">—</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                    </tr>
                    <tr>
                      <td className="py-2.5 px-4 font-semibold text-slate-900">Delete Meetings & Manage Tenant Billing</td>
                      <td className="py-2.5 px-4 text-center text-slate-300">—</td>
                      <td className="py-2.5 px-4 text-center text-slate-300">—</td>
                      <td className="py-2.5 px-4 text-center text-emerald-600 font-bold">✓</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            {/* Authentication & Session Policy */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Authentication & Session Security</h3>
                <p className="text-xs text-slate-500 mt-0.5">Enforce enterprise MFA and automated session rotation</p>
              </div>

              <div className="space-y-3">
                <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-100 hover:bg-slate-50/70 transition-colors cursor-pointer">
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold text-slate-800">Enforce Two-Factor Authentication (2FA)</span>
                    <p className="text-slate-500 text-[11px]">Require hardware TOTP security keys or authenticator apps for all teammates</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={enforce2FA}
                    onChange={(e) => {
                      setEnforce2FA(e.target.checked);
                      toast.success(e.target.checked ? "2FA policy enforced" : "2FA policy relaxed");
                    }}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer"
                  />
                </label>

                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl border border-slate-100">
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold text-slate-800">Inactivity Session Timeout</span>
                    <p className="text-slate-500 text-[11px]">Automatically terminate idle JWT bearer sessions</p>
                  </div>
                  <select
                    value={sessionTimeout}
                    onChange={(e) => setSessionTimeout(e.target.value)}
                    className="h-8 px-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs font-semibold text-slate-800 outline-none cursor-pointer"
                  >
                    <option value="1h">1 Hour</option>
                    <option value="4h">4 Hours</option>
                    <option value="8h">8 Hours (Standard Workday)</option>
                    <option value="24h">24 Hours</option>
                  </select>
                </div>
              </div>
            </div>

            {/* API Access Tokens */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Enterprise REST API Key</h3>
                  <p className="text-xs text-slate-500 mt-0.5">For custom webhooks, audio ingestion scripts, and CI/CD pipelines</p>
                </div>
                <button
                  type="button"
                  onClick={() => toast.success("New API Token generated and existing key rotated")}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-xs font-semibold text-slate-700 transition-colors cursor-pointer"
                >
                  <RefreshCw size={12} />
                  <span>Rotate Secret</span>
                </button>
              </div>

              <div className="flex items-center gap-2 p-3 bg-slate-50 border border-slate-200 rounded-xl">
                <Key size={15} className="text-slate-400 shrink-0" />
                <span className="font-mono text-xs text-slate-800 flex-1 truncate">
                  {apiKeyMasked ? "knw_live_••••••••••••••••••••••••" : apiKey}
                </span>
                <button
                  type="button"
                  onClick={() => setApiKeyMasked(!apiKeyMasked)}
                  className="p-1 text-slate-400 hover:text-slate-700 cursor-pointer"
                  title={apiKeyMasked ? "Reveal Key" : "Hide Key"}
                >
                  {apiKeyMasked ? <Eye size={14} /> : <EyeOff size={14} />}
                </button>
                <button
                  type="button"
                  onClick={handleCopyApiKey}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded bg-white border border-slate-200 text-xs font-semibold text-slate-700 hover:bg-slate-100 cursor-pointer shadow-2xs"
                >
                  {copiedKey ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  <span>{copiedKey ? "Copied" : "Copy"}</span>
                </button>
              </div>
            </div>

            {/* Danger Zone */}
            <div className="bg-rose-50/40 rounded-xl border border-rose-200/80 p-6 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-bold text-rose-900">Sign Out of All Sessions</h3>
                  <p className="text-xs text-rose-600 mt-0.5">Revoke all active JWT tokens and invalidate cookies on all devices</p>
                </div>
                <button
                  type="button"
                  onClick={logout}
                  className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs transition-all shadow-xs active:scale-95 cursor-pointer"
                >
                  Sign Out
                </button>
              </div>
            </div>
          </div>
        )}

        {/* TAB 5: Notifications & Notetakers */}
        {activeTab === "notifications" && (
          <div className="space-y-5 animate-in fade-in duration-200">
            {/* Calendar Notetaker Bot Behavior */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Knowra Calendar Notetaker Behavior</h3>
                <p className="text-xs text-slate-500 mt-0.5">Control how and when the AI notetaker auto-joins your calendar syncs</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-1">
                {[
                  { id: "all", title: "Join All Meetings", sub: "Auto-joins internal & external scheduled calls" },
                  { id: "internal", title: "Internal Team Only", sub: "Only joins calls where all participants have @softude.com" },
                  { id: "invited", title: "Manual Invite Only", sub: "Only joins when knowra-bot@knowra.ai is explicitly invited" },
                ].map((mode) => (
                  <button
                    key={mode.id}
                    type="button"
                    onClick={() => {
                      setNotetakerMode(mode.id as any);
                      toast.success(`Notetaker set to: ${mode.title}`);
                    }}
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      notetakerMode === mode.id
                        ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <p className="text-xs font-bold text-slate-900 flex items-center justify-between">
                      {mode.title}
                      {notetakerMode === mode.id && <Check size={12} className="text-indigo-600 stroke-[3]" />}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1 leading-snug">{mode.sub}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Email Digests & Dispatches */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-4">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Email Recap Dispatches</h3>
                <p className="text-xs text-slate-500 mt-0.5">Automated executive briefs dispatched directly to your inbox</p>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                {[
                  { id: "instant", title: "Instant Dispatch", sub: "Email sent 2 mins after meeting finishes" },
                  { id: "daily", title: "Daily Morning Digest", sub: "Single summary at 8:00 AM of previous day" },
                  { id: "weekly", title: "Weekly Executive Brief", sub: "Aggregated strategic recap on Friday 5:00 PM" },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => {
                      setEmailDigest(opt.id as any);
                      toast.success(`Email preference set to: ${opt.title}`);
                    }}
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      emailDigest === opt.id
                        ? "border-indigo-600 bg-indigo-50/50 shadow-xs"
                        : "border-slate-200 hover:border-slate-300 bg-white"
                    }`}
                  >
                    <p className="text-xs font-bold text-slate-900 flex items-center justify-between">
                      {opt.title}
                      {emailDigest === opt.id && <Check size={12} className="text-indigo-600 stroke-[3]" />}
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1 leading-snug">{opt.sub}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Slack & Notion Push Toggles */}
            <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6 space-y-3">
              <div>
                <h3 className="text-sm font-bold text-slate-900">Third-Party Automation Channels</h3>
                <p className="text-xs text-slate-500 mt-0.5">Forward meetings directly into your team tools</p>
              </div>

              <div className="space-y-2.5">
                <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-100 hover:bg-slate-50/70 transition-colors cursor-pointer">
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold text-slate-800">Slack High-Priority Commitment Alerts</span>
                    <p className="text-slate-500 text-[11px]">Post extracted action items directly to assigned teammates in Slack</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={slackAlerts}
                    onChange={(e) => {
                      setSlackAlerts(e.target.checked);
                      toast.success(e.target.checked ? "Slack alerts enabled" : "Slack alerts paused");
                    }}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer"
                  />
                </label>

                <label className="flex items-center justify-between p-3.5 rounded-xl border border-slate-100 hover:bg-slate-50/70 transition-colors cursor-pointer">
                  <div className="space-y-0.5">
                    <span className="text-xs font-bold text-slate-800">Auto-Export Completed Recaps to Notion</span>
                    <p className="text-slate-500 text-[11px]">Create a new sub-page in your company Knowledge Base database</p>
                  </div>
                  <input
                    type="checkbox"
                    checked={autoExportNotion}
                    onChange={(e) => {
                      setAutoExportNotion(e.target.checked);
                      toast.success(e.target.checked ? "Notion sync enabled" : "Notion sync paused");
                    }}
                    className="w-4 h-4 rounded text-indigo-600 focus:ring-indigo-500 border-slate-300 cursor-pointer"
                  />
                </label>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
