"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { useSession } from "@/lib/auth/session";
import { Eye, EyeOff, ArrowRight, CheckCircle2, Brain, Mic2, GitBranch, BarChart3 } from "lucide-react";

// ─── Validation ───────────────────────────────────────────────────────────────
const EmailSchema = z.string().email("Enter a valid email address");
const PasswordSchema = z.string().min(6, "Password must be at least 6 characters");

type Step = "email" | "password";

// ─── Feature highlights for right panel ──────────────────────────────────────
const FEATURES = [
  {
    icon: Mic2,
    color: "#4f7cff",
    title: "Enterprise Transcription",
    desc: "Speaker-diarized transcripts with >95% accuracy across 50+ languages.",
  },
  {
    icon: Brain,
    color: "#7c5cfc",
    title: "Permission-Aware RAG Chat",
    desc: "Ask anything across meetings. Every answer cites the exact source segment.",
  },
  {
    icon: GitBranch,
    color: "#10b981",
    title: "Organizational Knowledge Graph",
    desc: "Visualize relationships between people, topics, and decisions over time.",
  },
  {
    icon: BarChart3,
    color: "#f59e0b",
    title: "AI Quality Observability",
    desc: "Track WER, faithfulness, and hallucination rate across every pipeline run.",
  },
];

// ─── Mock chat messages for product preview ───────────────────────────────────
const PREVIEW_MESSAGES = [
  { role: "user",      text: "What tasks are at risk or overdue?" },
  { role: "assistant", text: "From the Q3 Planning session (Sep 12), Alice flagged the mobile onboarding flow as blocked — no design handoff. Also, the API rate-limit fix assigned to Dev team is 3 days past due." },
  { role: "user",      text: "Which decision was made about the pricing model?" },
  { role: "assistant", text: "In the Board Review (Sep 10), the team decided to move to usage-based pricing starting Q4, replacing the flat-rate tier. Confirmed by CEO and CFO." },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LoginPage() {
  const router = useRouter();
  const { login } = useSession();

  const [tab, setTab]           = useState<"signup" | "signin">("signin");
  const [step, setStep]         = useState<Step>("email");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [emailErr, setEmailErr] = useState("");
  const [pwErr, setPwErr]       = useState("");
  const [apiErr, setApiErr]     = useState("");
  const [loading, setLoading]   = useState(false);

  const handleEmailContinue = () => {
    const result = EmailSchema.safeParse(email);
    if (!result.success) {
      setEmailErr(result.error.issues[0].message);
      return;
    }
    setEmailErr("");
    setStep("password");
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    const pwResult = PasswordSchema.safeParse(password);
    if (!pwResult.success) {
      setPwErr(pwResult.error.issues[0].message);
      return;
    }
    setPwErr("");
    setApiErr("");
    setLoading(true);

    try {
      const formData = new URLSearchParams();
      formData.set("username", email);
      formData.set("password", password);

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/login`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: formData.toString(),
        }
      );

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Invalid email or password.");
      }

      const tokens = await res.json();
      const meRes = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/me`,
        { headers: { Authorization: `Bearer ${tokens.access_token}` } }
      );
      const user = await meRes.json();
      login(tokens.access_token, tokens.refresh_token ?? "", user);
      router.push("/");
    } catch (err: unknown) {
      setApiErr(err instanceof Error ? err.message : "Sign in failed.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex">
      {/* ── LEFT PANEL ─────────────────────────────────────────────────────── */}
      <div className="flex flex-col justify-center items-start w-full max-w-[460px] px-12 py-12 bg-white shrink-0">
        {/* Logo */}
        <div className="flex items-center gap-2.5 mb-10">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#4f7cff] to-[#7c5cfc] flex items-center justify-center shadow-lg">
            <Brain size={18} className="text-white" />
          </div>
          <span className="text-xl font-bold text-gray-900 tracking-tight">Knowra</span>
        </div>

        {/* Tabs */}
        <div className="flex gap-0 border-b border-gray-200 w-full mb-8">
          {(["signup", "signin"] as const).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setStep("email"); setApiErr(""); }}
              className="relative pb-3 pr-6 text-sm font-medium transition-colors"
              style={{
                color: tab === t ? "#4f7cff" : "#6b7280",
              }}
            >
              {t === "signup" ? "Create account" : "Sign in"}
              {tab === t && (
                <span
                  className="absolute bottom-0 left-0 right-6 h-0.5 rounded-full"
                  style={{ background: "#4f7cff" }}
                />
              )}
            </button>
          ))}
        </div>

        {/* Form */}
        <div className="w-full">
          {tab === "signup" ? (
            <SignUpPanel />
          ) : (
            <SignInPanel
              step={step}
              email={email}
              password={password}
              showPw={showPw}
              emailErr={emailErr}
              pwErr={pwErr}
              apiErr={apiErr}
              loading={loading}
              onEmailChange={(v) => { setEmail(v); setEmailErr(""); }}
              onPasswordChange={(v) => { setPassword(v); setPwErr(""); }}
              onTogglePw={() => setShowPw((p) => !p)}
              onEmailContinue={handleEmailContinue}
              onBack={() => setStep("email")}
              onSubmit={handleSignIn}
            />
          )}
        </div>

        {/* Legal */}
        <p className="text-xs text-gray-400 mt-8 text-center w-full leading-relaxed">
          By {tab === "signin" ? "signing in" : "creating an account"}, I agree to Knowra&apos;s{" "}
          <a href="#" className="text-[#4f7cff] hover:underline">Terms of Service</a> and acknowledge I
          have read the{" "}
          <a href="#" className="text-[#4f7cff] hover:underline">Privacy Policy</a>.
        </p>
      </div>

      {/* ── RIGHT PANEL ────────────────────────────────────────────────────── */}
      <div
        className="flex-1 flex flex-col justify-center items-center px-12 py-12 relative overflow-hidden"
        style={{
          background: "linear-gradient(135deg, #f0f4ff 0%, #f5f0ff 50%, #f0f7ff 100%)",
        }}
      >
        {/* Decorative circles */}
        <div className="absolute top-[-80px] right-[-80px] w-[360px] h-[360px] rounded-full opacity-20"
          style={{ background: "radial-gradient(circle, #4f7cff 0%, transparent 70%)" }} />
        <div className="absolute bottom-[-60px] left-[-60px] w-[280px] h-[280px] rounded-full opacity-15"
          style={{ background: "radial-gradient(circle, #7c5cfc 0%, transparent 70%)" }} />

        <div className="relative z-10 w-full max-w-[480px]">
          {/* Preview Card */}
          <div
            className="rounded-2xl overflow-hidden mb-8"
            style={{
              background: "white",
              boxShadow: "0 20px 60px rgba(79,124,255,0.15), 0 4px 16px rgba(0,0,0,0.08)",
            }}
          >
            {/* Card Header */}
            <div
              className="px-4 py-3 flex items-center gap-2"
              style={{
                background: "linear-gradient(135deg, #1a1f35 0%, #2d1b69 100%)",
              }}
            >
              <div className="flex gap-1.5">
                <span className="w-3 h-3 rounded-full bg-red-400 opacity-80" />
                <span className="w-3 h-3 rounded-full bg-yellow-400 opacity-80" />
                <span className="w-3 h-3 rounded-full bg-green-400 opacity-80" />
              </div>
              {/* Integration icons */}
              <div className="flex items-center gap-2 ml-3">
                {["🎯","🎙️","💬","📋","🔗"].map((icon, i) => (
                  <div
                    key={i}
                    className="w-7 h-7 rounded-lg bg-white bg-opacity-10 flex items-center justify-center text-sm"
                  >
                    {icon}
                  </div>
                ))}
              </div>
            </div>

            {/* Chat Preview */}
            <div className="px-5 py-4 space-y-3 bg-gray-50">
              {/* Search bar */}
              <div className="flex items-center gap-2 bg-white rounded-lg border border-gray-200 px-3 py-2">
                <span className="text-[10px] font-bold text-white bg-[#4f7cff] px-1.5 py-0.5 rounded text-center">AI</span>
                <span className="text-xs text-gray-400 flex-1">Ask anything about your meetings…</span>
                <div className="w-6 h-6 rounded-full bg-[#4f7cff] flex items-center justify-center">
                  <ArrowRight size={11} className="text-white" />
                </div>
              </div>

              {/* Messages */}
              <div className="space-y-2.5">
                {PREVIEW_MESSAGES.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className="rounded-xl px-3 py-2 max-w-[85%]"
                      style={{
                        background: msg.role === "user" ? "#4f7cff" : "white",
                        color: msg.role === "user" ? "white" : "#374151",
                        fontSize: "10.5px",
                        lineHeight: "1.5",
                        boxShadow: msg.role === "assistant" ? "0 1px 4px rgba(0,0,0,0.08)" : "none",
                        border: msg.role === "assistant" ? "1px solid #f0f0f0" : "none",
                      }}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>

              {/* Source citation pill */}
              <div className="flex items-center gap-1.5 bg-white rounded-lg border border-[#4f7cff20] px-3 py-1.5 w-fit">
                <CheckCircle2 size={11} className="text-[#4f7cff]" />
                <span className="text-[10px] text-gray-500">
                  Cited from <span className="text-[#4f7cff] font-medium">Board Review · Sep 10 · CEO</span>
                </span>
              </div>
            </div>
          </div>

          {/* Tagline */}
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              Meetings + Ask Knowra
            </h2>
            <p className="text-sm text-gray-500 leading-relaxed max-w-[360px] mx-auto">
              AI-powered meeting intelligence with verifiable citations.
              Connect your calendar, get instant answers from every conversation.
            </p>
          </div>

          {/* Feature List */}
          <div className="grid grid-cols-2 gap-3">
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <div
                  key={i}
                  className="flex items-start gap-2.5 bg-white bg-opacity-70 rounded-xl p-3 border border-white"
                  style={{ boxShadow: "0 2px 8px rgba(0,0,0,0.05)" }}
                >
                  <div
                    className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                    style={{ background: `${f.color}18` }}
                  >
                    <Icon size={14} style={{ color: f.color }} />
                  </div>
                  <div>
                    <p className="text-xs font-semibold text-gray-800">{f.title}</p>
                    <p className="text-[10px] text-gray-400 mt-0.5 leading-relaxed">{f.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Sign-In Sub-Component ────────────────────────────────────────────────────
function SignInPanel({
  step,
  email,
  password,
  showPw,
  emailErr,
  pwErr,
  apiErr,
  loading,
  onEmailChange,
  onPasswordChange,
  onTogglePw,
  onEmailContinue,
  onBack,
  onSubmit,
}: {
  step: Step;
  email: string;
  password: string;
  showPw: boolean;
  emailErr: string;
  pwErr: string;
  apiErr: string;
  loading: boolean;
  onEmailChange: (v: string) => void;
  onPasswordChange: (v: string) => void;
  onTogglePw: () => void;
  onEmailContinue: () => void;
  onBack: () => void;
  onSubmit: (e: React.FormEvent) => void;
}) {
  return (
    <div className="w-full space-y-4">
      {step === "email" ? (
        <>
          {/* Email step */}
          <div>
            <label className="block text-sm text-gray-600 mb-1.5 font-medium" htmlFor="signin-email">
              Email address
            </label>
            <input
              id="signin-email"
              type="email"
              autoComplete="email"
              autoFocus
              value={email}
              onChange={(e) => onEmailChange(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onEmailContinue()}
              placeholder="you@company.com"
              className="w-full h-11 px-4 rounded-lg border border-gray-300 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-[#4f7cff] focus:ring-2 focus:ring-[#4f7cff20] transition-all"
            />
            {emailErr && <p className="text-xs text-red-500 mt-1">{emailErr}</p>}
          </div>

          <button
            type="button"
            onClick={onEmailContinue}
            id="signin-continue-btn"
            className="w-full h-11 rounded-lg text-sm font-semibold text-white transition-all active:scale-[0.98]"
            style={{ background: "linear-gradient(135deg, #4f7cff, #7c5cfc)" }}
          >
            Continue
          </button>

          <div className="relative flex items-center">
            <div className="flex-1 h-px bg-gray-200" />
            <span className="px-3 text-xs text-gray-400">or</span>
            <div className="flex-1 h-px bg-gray-200" />
          </div>

          {/* SSO Options */}
          {[
            { icon: "🔷", label: "Continue with Microsoft" },
            { icon: "💬", label: "Continue with Slack" },
            { icon: "🏢", label: "Continue with your organization" },
          ].map((opt, i) => (
            <button
              key={i}
              type="button"
              className="w-full h-11 flex items-center gap-3 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-all"
            >
              <span className="text-lg">{opt.icon}</span>
              {opt.label}
            </button>
          ))}
        </>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          {/* Back + email display */}
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onBack}
              className="text-sm text-[#4f7cff] hover:underline"
            >
              ← Back
            </button>
            <span className="text-sm text-gray-400 truncate">{email}</span>
          </div>

          {/* Password */}
          <div>
            <label className="block text-sm text-gray-600 mb-1.5 font-medium" htmlFor="signin-password">
              Password
            </label>
            <div className="relative">
              <input
                id="signin-password"
                type={showPw ? "text" : "password"}
                autoFocus
                autoComplete="current-password"
                value={password}
                onChange={(e) => onPasswordChange(e.target.value)}
                placeholder="••••••••"
                className="w-full h-11 px-4 pr-11 rounded-lg border border-gray-300 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:border-[#4f7cff] focus:ring-2 focus:ring-[#4f7cff20] transition-all"
              />
              <button
                type="button"
                onClick={onTogglePw}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {pwErr && <p className="text-xs text-red-500 mt-1">{pwErr}</p>}
          </div>

          <div className="flex justify-end">
            <a href="#" className="text-xs text-[#4f7cff] hover:underline">
              Forgot password?
            </a>
          </div>

          {apiErr && (
            <div className="px-3 py-2.5 rounded-lg bg-red-50 border border-red-200">
              <p className="text-xs text-red-600">{apiErr}</p>
            </div>
          )}

          <button
            type="submit"
            id="signin-submit-btn"
            disabled={loading}
            className="w-full h-11 rounded-lg text-sm font-semibold text-white transition-all active:scale-[0.98] flex items-center justify-center gap-2 disabled:opacity-60"
            style={{ background: "linear-gradient(135deg, #4f7cff, #7c5cfc)" }}
          >
            {loading ? (
              <span className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
            ) : (
              <>Sign In <ArrowRight size={15} /></>
            )}
          </button>
        </form>
      )}
    </div>
  );
}

// ─── Sign-Up Sub-Component ────────────────────────────────────────────────────
function SignUpPanel() {
  return (
    <div className="w-full space-y-3">
      {/* SSO Buttons */}
      {[
        { icon: "🔵", label: "Continue with Google", color: "#4285F4" },
        { icon: "🟦", label: "Continue with Microsoft", color: "#00A4EF" },
        { icon: "💬", label: "Continue with Slack", color: "#4A154B" },
        { icon: "🏢", label: "Continue with your organization", color: "#374151" },
      ].map((opt, i) => (
        <button
          key={i}
          type="button"
          className="w-full h-11 flex items-center gap-3 px-4 rounded-lg border border-gray-200 text-sm font-medium text-gray-700 hover:border-gray-300 hover:bg-gray-50 transition-all"
        >
          <span className="text-lg">{opt.icon}</span>
          {opt.label}
        </button>
      ))}

      <div className="relative flex items-center py-1">
        <div className="flex-1 h-px bg-gray-200" />
        <span className="px-3 text-xs text-gray-400">or</span>
        <div className="flex-1 h-px bg-gray-200" />
      </div>

      <button
        type="button"
        className="w-full text-sm text-[#4f7cff] hover:underline font-medium py-1"
      >
        Continue with email and password
      </button>
    </div>
  );
}
