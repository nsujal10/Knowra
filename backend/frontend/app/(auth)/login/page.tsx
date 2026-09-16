"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { z } from "zod";
import { useSession } from "@/lib/auth/session";
import type { User as AuthUser } from "@/lib/types";
import {
  Eye,
  EyeOff,
  ArrowRight,
  Brain,
  Shield,
  Mic2,
  GitBranch,
  BarChart3,
  CheckCircle2,
  Lock,
  Building2,
  User,
  Mail,
  Sparkles,
} from "lucide-react";

// ─── Validation Schemas ───────────────────────────────────────────────────────
const SignInSchema = z.object({
  email: z.string().email("Enter a valid work email address"),
  password: z.string().min(1, "Password is required"),
});

const SignUpSchema = z.object({
  fullName: z.string().min(2, "Full name must be at least 2 characters"),
  organizationName: z.string().min(2, "Company or workspace name is required"),
  email: z.string().email("Enter a valid business email address"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});

// ─── Right-panel Capabilities ─────────────────────────────────────────────────
const CAPABILITIES = [
  {
    icon: Mic2,
    color: "#3b82f6",
    title: "Enterprise Transcription",
    desc: "Speaker-diarized Whisper with >95% accuracy and custom vocabularies.",
  },
  {
    icon: Brain,
    color: "#6366f1",
    title: "Permission-Aware RAG",
    desc: "Cited answers from company meetings with strict RBAC enforcement.",
  },
  {
    icon: GitBranch,
    color: "#10b981",
    title: "Knowledge Graph",
    desc: "Map interconnections between decisions, action items, and team owners.",
  },
  {
    icon: BarChart3,
    color: "#f59e0b",
    title: "AI Observability",
    desc: "Track WER, context faithfulness, latency, and token economics.",
  },
];

// ─── Interactive Chat Preview Data ────────────────────────────────────────────
const CHAT_EXCHANGE = [
  {
    role: "user",
    text: "What were the key blockers and commitments from yesterday's product sync?",
  },
  {
    role: "assistant",
    text: "DevOps confirmed the Kubernetes autoscaling migration is scheduled for Thursday night. Sarah owns the SOC 2 compliance sign-off by EOD Wednesday.",
    cite: "Q3 Engineering Sync · 18:42",
  },
];

function LoginFormContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login, isAuthenticated, isLoading } = useSession();

  const rawRedirect = searchParams.get("redirect");
  const redirectTarget =
    rawRedirect && rawRedirect.startsWith("/") && !rawRedirect.startsWith("//")
      ? rawRedirect
      : "/";

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(redirectTarget);
    }
  }, [isLoading, isAuthenticated, redirectTarget, router]);

  const [tab, setTab] = useState<"signin" | "signup">("signin");

  // Sign In form state
  const [signInEmail, setSignInEmail] = useState("");
  const [signInPassword, setSignInPassword] = useState("");
  const [showSignInPw, setShowSignInPw] = useState(false);

  // Sign Up form state
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [signUpEmail, setSignUpEmail] = useState("");
  const [signUpPassword, setSignUpPassword] = useState("");
  const [showSignUpPw, setShowSignUpPw] = useState(false);

  // Status & Feedback
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [apiError, setApiError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const clearErrors = () => {
    setErrors({});
    setApiError("");
    setSuccessMessage("");
  };

  const switchTab = (nextTab: "signin" | "signup") => {
    clearErrors();
    setTab(nextTab);
  };

  // ─── Handle Sign In ──────────────────────────────────────────────────────────
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    clearErrors();

    const parseResult = SignInSchema.safeParse({
      email: signInEmail,
      password: signInPassword,
    });

    if (!parseResult.success) {
      const fieldErrors: Record<string, string> = {};
      parseResult.error.issues.forEach((issue) => {
        if (issue.path[0]) fieldErrors[issue.path[0].toString()] = issue.message;
      });
      setErrors(fieldErrors);
      return;
    }

    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

    try {
      const res = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: signInEmail,
          password: signInPassword,
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? "Invalid email or password. Please try again.");
      }

      const tokens = await res.json();
      const meRes = await fetch(`${apiUrl}/auth/me`, {
        headers: { Authorization: `Bearer ${tokens.access_token}` },
      });
      const userProfile = meRes.ok ? await meRes.json() : null;

      const mappedUser: AuthUser = {
        id: String(userProfile?.user_id ?? "unknown"),
        email: userProfile?.email ?? signInEmail,
        full_name: userProfile?.full_name ?? "User",
        role_code: userProfile?.role_code ?? "ADMIN",
        tenant_id: String(userProfile?.organization_id ?? "default"),
        is_active: userProfile?.is_active ?? true,
      };

      login(tokens.access_token, tokens.refresh_token ?? "", mappedUser);
      router.push(redirectTarget);
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Sign in failed. Please check your credentials.");
    } finally {
      setLoading(false);
    }
  };

  // ─── Handle Sign Up (Create Account) ─────────────────────────────────────────
  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    clearErrors();

    const parseResult = SignUpSchema.safeParse({
      fullName,
      organizationName,
      email: signUpEmail,
      password: signUpPassword,
    });

    if (!parseResult.success) {
      const fieldErrors: Record<string, string> = {};
      parseResult.error.issues.forEach((issue) => {
        if (issue.path[0]) fieldErrors[issue.path[0].toString()] = issue.message;
      });
      setErrors(fieldErrors);
      return;
    }

    setLoading(true);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

    try {
      // 1. Register new user & workspace
      const registerRes = await fetch(`${apiUrl}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: signUpEmail,
          password: signUpPassword,
          full_name: fullName,
          organization_name: organizationName,
        }),
      });

      if (!registerRes.ok) {
        const data = await registerRes.json().catch(() => ({}));
        throw new Error(data.detail ?? "Registration failed. An account with this email may already exist.");
      }

      // 2. Automatically log in the user
      const loginRes = await fetch(`${apiUrl}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: signUpEmail,
          password: signUpPassword,
        }),
      });

      if (loginRes.ok) {
        const tokens = await loginRes.json();
        const meRes = await fetch(`${apiUrl}/auth/me`, {
          headers: { Authorization: `Bearer ${tokens.access_token}` },
        });
        const userProfile = meRes.ok ? await meRes.json() : null;

        const mappedUser: AuthUser = {
          id: String(userProfile?.user_id ?? "unknown"),
          email: userProfile?.email ?? signUpEmail,
          full_name: userProfile?.full_name ?? fullName,
          role_code: userProfile?.role_code ?? "ADMIN",
          tenant_id: String(userProfile?.organization_id ?? "default"),
          is_active: userProfile?.is_active ?? true,
        };

        login(tokens.access_token, tokens.refresh_token ?? "", mappedUser);
        router.push(redirectTarget);
      } else {
        // Registration worked, prompt user to sign in
        setSuccessMessage("Account created successfully! Please sign in with your credentials.");
        setSignInEmail(signUpEmail);
        setTab("signin");
      }
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Account creation failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        display: "flex",
        minHeight: "100dvh",
        background: "#ffffff",
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
      }}
    >
      {/* ── LEFT PANEL: AUTH FORM ─────────────────────────────────────────── */}
      <div
        style={{
          width: 480,
          minWidth: 480,
          maxWidth: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "space-between",
          padding: "32px 44px 24px 44px",
          background: "#ffffff",
          borderRight: "1px solid #e5e7eb",
          boxSizing: "border-box",
          overflowY: "auto",
        }}
      >
        {/* Top Header & Forms */}
        <div>
          {/* Brand Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
            <div
              style={{
                width: 34,
                height: 34,
                borderRadius: 8,
                background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 3px 10px rgba(37, 99, 235, 0.25)",
              }}
            >
              <Brain size={18} color="white" />
            </div>
            <div>
              <span
                style={{
                  fontSize: 18,
                  fontWeight: 700,
                  color: "#0f172a",
                  letterSpacing: "-0.3px",
                }}
              >
                Knowra
              </span>
              <span
                style={{
                  display: "block",
                  fontSize: 11,
                  color: "#64748b",
                  fontWeight: 500,
                  marginTop: -2,
                }}
              >
                Enterprise Meeting Intelligence
              </span>
            </div>
          </div>

          {/* Tab Switcher: Sign in | Create account */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid #e2e8f0",
              marginBottom: 20,
              gap: 20,
            }}
          >
            <button
              type="button"
              onClick={() => switchTab("signin")}
              style={{
                paddingBottom: 10,
                fontSize: 14,
                fontWeight: tab === "signin" ? 600 : 500,
                color: tab === "signin" ? "#2563eb" : "#64748b",
                border: "none",
                background: "transparent",
                cursor: "pointer",
                position: "relative",
                borderBottom: tab === "signin" ? "2px solid #2563eb" : "2px solid transparent",
                marginBottom: -1,
                transition: "all 0.15s ease",
              }}
            >
              Sign in
            </button>
            <button
              type="button"
              onClick={() => switchTab("signup")}
              style={{
                paddingBottom: 10,
                fontSize: 14,
                fontWeight: tab === "signup" ? 600 : 500,
                color: tab === "signup" ? "#2563eb" : "#64748b",
                border: "none",
                background: "transparent",
                cursor: "pointer",
                position: "relative",
                borderBottom: tab === "signup" ? "2px solid #2563eb" : "2px solid transparent",
                marginBottom: -1,
                transition: "all 0.15s ease",
              }}
            >
              Create account
            </button>
          </div>

          {/* Heading */}
          <div style={{ marginBottom: 18 }}>
            <h1
              style={{
                fontSize: 20,
                fontWeight: 700,
                color: "#0f172a",
                letterSpacing: "-0.3px",
                margin: "0 0 4px 0",
              }}
            >
              {tab === "signin" ? "Welcome back" : "Get started with Knowra"}
            </h1>
            <p style={{ fontSize: 13, color: "#64748b", margin: 0, lineHeight: 1.45 }}>
              {tab === "signin"
                ? "Enter your credentials to access your meetings and organizational knowledge."
                : "Create your organization workspace and start turning conversations into intelligence."}
            </p>
          </div>

          {/* Global Notifications */}
          {apiError && (
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 7,
                background: "#fef2f2",
                border: "1px solid #fecaca",
                color: "#dc2626",
                fontSize: 12.5,
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <div
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: "50%",
                  background: "#dc2626",
                  flexShrink: 0,
                }}
              />
              <span>{apiError}</span>
            </div>
          )}

          {successMessage && (
            <div
              style={{
                padding: "8px 12px",
                borderRadius: 7,
                background: "#f0fdf4",
                border: "1px solid #bbf7d0",
                color: "#16a34a",
                fontSize: 12.5,
                marginBottom: 16,
                display: "flex",
                alignItems: "center",
                gap: 8,
              }}
            >
              <CheckCircle2 size={15} color="#16a34a" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Side-by-Side SSO Action Buttons */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 16 }}>
            <button
              type="button"
              style={{
                height: 38,
                borderRadius: 7,
                border: "1.5px solid #e2e8f0",
                background: "#ffffff",
                color: "#1e293b",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                transition: "all 0.15s ease",
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.borderColor = "#cbd5e1";
                e.currentTarget.style.background = "#f8fafc";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.borderColor = "#e2e8f0";
                e.currentTarget.style.background = "#ffffff";
              }}
            >
              {/* Google SVG */}
              <svg width="16" height="16" viewBox="0 0 24 24">
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
              <span>Google</span>
            </button>

            <button
              type="button"
              style={{
                height: 38,
                borderRadius: 7,
                border: "1.5px solid #e2e8f0",
                background: "#ffffff",
                color: "#1e293b",
                fontSize: 13,
                fontWeight: 500,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 8,
                transition: "all 0.15s ease",
              }}
              onMouseOver={(e) => {
                e.currentTarget.style.borderColor = "#cbd5e1";
                e.currentTarget.style.background = "#f8fafc";
              }}
              onMouseOut={(e) => {
                e.currentTarget.style.borderColor = "#e2e8f0";
                e.currentTarget.style.background = "#ffffff";
              }}
            >
              {/* Microsoft SVG */}
              <svg width="16" height="16" viewBox="0 0 23 23">
                <rect width="10" height="10" fill="#f25022" />
                <rect x="12" width="10" height="10" fill="#7fba00" />
                <rect y="12" width="10" height="10" fill="#00a4ef" />
                <rect x="12" y="12" width="10" height="10" fill="#ffb900" />
              </svg>
              <span>Microsoft</span>
            </button>
          </div>

          {/* Divider */}
          <div style={{ display: "flex", alignItems: "center", gap: 10, margin: "14px 0" }}>
            <div style={{ flex: 1, height: 1, background: "#e2e8f0" }} />
            <span style={{ fontSize: 11.5, color: "#94a3b8", fontWeight: 500, textTransform: "uppercase" }}>
              or continue with email
            </span>
            <div style={{ flex: 1, height: 1, background: "#e2e8f0" }} />
          </div>

          {/* ─── TAB: SIGN IN ──────────────────────────────────────────────── */}
          {tab === "signin" ? (
            <form onSubmit={handleSignIn} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              {/* Email */}
              <div>
                <label
                  htmlFor="signin-email"
                  style={{ display: "block", fontSize: 12.5, fontWeight: 500, color: "#334155", marginBottom: 5 }}
                >
                  Work Email
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    id="signin-email"
                    type="email"
                    autoComplete="email"
                    placeholder="name@company.com"
                    value={signInEmail}
                    onChange={(e) => {
                      setSignInEmail(e.target.value);
                      if (errors.email) setErrors((prev) => ({ ...prev, email: "" }));
                    }}
                    style={{
                      width: "100%",
                      height: 40,
                      padding: "0 14px 0 36px",
                      borderRadius: 7,
                      border: errors.email ? "1.5px solid #ef4444" : "1.5px solid #cbd5e1",
                      fontSize: 13.5,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                      boxSizing: "border-box",
                      transition: "border-color 0.15s ease",
                    }}
                    onFocus={(e) => !errors.email && (e.target.style.borderColor = "#2563eb")}
                    onBlur={(e) => !errors.email && (e.target.style.borderColor = "#cbd5e1")}
                  />
                  <Mail
                    size={15}
                    color="#94a3b8"
                    style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)" }}
                  />
                </div>
                {errors.email && (
                  <p style={{ margin: "3px 0 0 0", fontSize: 11.5, color: "#ef4444" }}>{errors.email}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                  <label
                    htmlFor="signin-password"
                    style={{ fontSize: 12.5, fontWeight: 500, color: "#334155" }}
                  >
                    Password
                  </label>
                  <a
                    href="#"
                    onClick={(e) => {
                      e.preventDefault();
                      alert("Password reset instructions have been dispatched if the account exists.");
                    }}
                    style={{ fontSize: 11.5, color: "#2563eb", textDecoration: "none", fontWeight: 500 }}
                  >
                    Forgot password?
                  </a>
                </div>
                <div style={{ position: "relative" }}>
                  <input
                    id="signin-password"
                    type={showSignInPw ? "text" : "password"}
                    autoComplete="current-password"
                    placeholder="••••••••"
                    value={signInPassword}
                    onChange={(e) => {
                      setSignInPassword(e.target.value);
                      if (errors.password) setErrors((prev) => ({ ...prev, password: "" }));
                    }}
                    style={{
                      width: "100%",
                      height: 40,
                      padding: "0 38px 0 36px",
                      borderRadius: 7,
                      border: errors.password ? "1.5px solid #ef4444" : "1.5px solid #cbd5e1",
                      fontSize: 13.5,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                      boxSizing: "border-box",
                      transition: "border-color 0.15s ease",
                    }}
                    onFocus={(e) => !errors.password && (e.target.style.borderColor = "#2563eb")}
                    onBlur={(e) => !errors.password && (e.target.style.borderColor = "#cbd5e1")}
                  />
                  <Lock
                    size={15}
                    color="#94a3b8"
                    style={{ position: "absolute", left: 11, top: "50%", transform: "translateY(-50%)" }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowSignInPw((v) => !v)}
                    style={{
                      position: "absolute",
                      right: 11,
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "#94a3b8",
                      display: "flex",
                      alignItems: "center",
                      padding: 0,
                    }}
                  >
                    {showSignInPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {errors.password && (
                  <p style={{ margin: "3px 0 0 0", fontSize: 11.5, color: "#ef4444" }}>{errors.password}</p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                style={{
                  height: 40,
                  borderRadius: 7,
                  border: "none",
                  background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
                  color: "white",
                  fontSize: 13.5,
                  fontWeight: 600,
                  cursor: loading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  marginTop: 4,
                  boxShadow: "0 2px 8px rgba(37, 99, 235, 0.25)",
                  transition: "all 0.15s ease",
                  opacity: loading ? 0.75 : 1,
                }}
                onMouseOver={(e) => !loading && (e.currentTarget.style.opacity = "0.92")}
                onMouseOut={(e) => !loading && (e.currentTarget.style.opacity = "1")}
              >
                {loading ? (
                  <>
                    <span
                      style={{
                        width: 15,
                        height: 15,
                        borderRadius: "50%",
                        border: "2px solid rgba(255,255,255,0.4)",
                        borderTopColor: "white",
                        display: "inline-block",
                        animation: "spin 0.8s linear infinite",
                      }}
                    />
                    <span>Signing in…</span>
                  </>
                ) : (
                  <>
                    <span>Sign in to Knowra</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>

              {/* Prompt to switch */}
              <p style={{ textAlign: "center", fontSize: 12.5, color: "#64748b", margin: "4px 0 0 0" }}>
                Don&apos;t have an account?{" "}
                <button
                  type="button"
                  onClick={() => switchTab("signup")}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#2563eb",
                    fontWeight: 600,
                    cursor: "pointer",
                    padding: 0,
                    fontSize: 12.5,
                  }}
                >
                  Create account
                </button>
              </p>
            </form>
          ) : (
            /* ─── TAB: CREATE ACCOUNT ───────────────────────────────────────── */
            <form onSubmit={handleSignUp} style={{ display: "flex", flexDirection: "column", gap: 11 }}>
              {/* Full Name */}
              <div>
                <label
                  htmlFor="signup-name"
                  style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#334155", marginBottom: 4 }}
                >
                  Full Name
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    id="signup-name"
                    type="text"
                    autoComplete="name"
                    placeholder="Alex Morgan"
                    value={fullName}
                    onChange={(e) => {
                      setFullName(e.target.value);
                      if (errors.fullName) setErrors((prev) => ({ ...prev, fullName: "" }));
                    }}
                    style={{
                      width: "100%",
                      height: 36,
                      padding: "0 12px 0 34px",
                      borderRadius: 7,
                      border: errors.fullName ? "1.5px solid #ef4444" : "1.5px solid #cbd5e1",
                      fontSize: 13,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                    onFocus={(e) => !errors.fullName && (e.target.style.borderColor = "#2563eb")}
                    onBlur={(e) => !errors.fullName && (e.target.style.borderColor = "#cbd5e1")}
                  />
                  <User
                    size={14}
                    color="#94a3b8"
                    style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }}
                  />
                </div>
                {errors.fullName && (
                  <p style={{ margin: "2px 0 0 0", fontSize: 11, color: "#ef4444" }}>{errors.fullName}</p>
                )}
              </div>

              {/* Organization / Workspace */}
              <div>
                <label
                  htmlFor="signup-org"
                  style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#334155", marginBottom: 4 }}
                >
                  Organization / Team Name
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    id="signup-org"
                    type="text"
                    placeholder="Acme Corp"
                    value={organizationName}
                    onChange={(e) => {
                      setOrganizationName(e.target.value);
                      if (errors.organizationName) setErrors((prev) => ({ ...prev, organizationName: "" }));
                    }}
                    style={{
                      width: "100%",
                      height: 36,
                      padding: "0 12px 0 34px",
                      borderRadius: 7,
                      border: errors.organizationName ? "1.5px solid #ef4444" : "1.5px solid #cbd5e1",
                      fontSize: 13,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                    onFocus={(e) => !errors.organizationName && (e.target.style.borderColor = "#2563eb")}
                    onBlur={(e) => !errors.organizationName && (e.target.style.borderColor = "#cbd5e1")}
                  />
                  <Building2
                    size={14}
                    color="#94a3b8"
                    style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }}
                  />
                </div>
                {errors.organizationName && (
                  <p style={{ margin: "2px 0 0 0", fontSize: 11, color: "#ef4444" }}>{errors.organizationName}</p>
                )}
              </div>

              {/* Email */}
              <div>
                <label
                  htmlFor="signup-email"
                  style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#334155", marginBottom: 4 }}
                >
                  Work Email
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    id="signup-email"
                    type="email"
                    autoComplete="email"
                    placeholder="name@company.com"
                    value={signUpEmail}
                    onChange={(e) => {
                      setSignUpEmail(e.target.value);
                      if (errors.email) setErrors((prev) => ({ ...prev, email: "" }));
                    }}
                    style={{
                      width: "100%",
                      height: 36,
                      padding: "0 12px 0 34px",
                      borderRadius: 7,
                      border: errors.email ? "1.5px solid #ef4444" : "1.5px solid #cbd5e1",
                      fontSize: 13,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                    onFocus={(e) => !errors.email && (e.target.style.borderColor = "#2563eb")}
                    onBlur={(e) => !errors.email && (e.target.style.borderColor = "#cbd5e1")}
                  />
                  <Mail
                    size={14}
                    color="#94a3b8"
                    style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }}
                  />
                </div>
                {errors.email && (
                  <p style={{ margin: "2px 0 0 0", fontSize: 11, color: "#ef4444" }}>{errors.email}</p>
                )}
              </div>

              {/* Password */}
              <div>
                <label
                  htmlFor="signup-password"
                  style={{ display: "block", fontSize: 12, fontWeight: 500, color: "#334155", marginBottom: 4 }}
                >
                  Password (min 8 characters)
                </label>
                <div style={{ position: "relative" }}>
                  <input
                    id="signup-password"
                    type={showSignUpPw ? "text" : "password"}
                    autoComplete="new-password"
                    placeholder="••••••••"
                    value={signUpPassword}
                    onChange={(e) => {
                      setSignUpPassword(e.target.value);
                      if (errors.password) setErrors((prev) => ({ ...prev, password: "" }));
                    }}
                    style={{
                      width: "100%",
                      height: 36,
                      padding: "0 36px 0 34px",
                      borderRadius: 7,
                      border: errors.password ? "1.5px solid #ef4444" : "1.5px solid #cbd5e1",
                      fontSize: 13,
                      color: "#0f172a",
                      background: "#ffffff",
                      outline: "none",
                      boxSizing: "border-box",
                    }}
                    onFocus={(e) => !errors.password && (e.target.style.borderColor = "#2563eb")}
                    onBlur={(e) => !errors.password && (e.target.style.borderColor = "#cbd5e1")}
                  />
                  <Lock
                    size={14}
                    color="#94a3b8"
                    style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowSignUpPw((v) => !v)}
                    style={{
                      position: "absolute",
                      right: 10,
                      top: "50%",
                      transform: "translateY(-50%)",
                      background: "none",
                      border: "none",
                      cursor: "pointer",
                      color: "#94a3b8",
                      display: "flex",
                      alignItems: "center",
                      padding: 0,
                    }}
                  >
                    {showSignUpPw ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                {errors.password && (
                  <p style={{ margin: "2px 0 0 0", fontSize: 11, color: "#ef4444" }}>{errors.password}</p>
                )}
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading}
                style={{
                  height: 40,
                  borderRadius: 7,
                  border: "none",
                  background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
                  color: "white",
                  fontSize: 13.5,
                  fontWeight: 600,
                  cursor: loading ? "not-allowed" : "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  gap: 8,
                  marginTop: 4,
                  boxShadow: "0 2px 8px rgba(37, 99, 235, 0.25)",
                  transition: "all 0.15s ease",
                  opacity: loading ? 0.75 : 1,
                }}
                onMouseOver={(e) => !loading && (e.currentTarget.style.opacity = "0.92")}
                onMouseOut={(e) => !loading && (e.currentTarget.style.opacity = "1")}
              >
                {loading ? (
                  <>
                    <span
                      style={{
                        width: 15,
                        height: 15,
                        borderRadius: "50%",
                        border: "2px solid rgba(255,255,255,0.4)",
                        borderTopColor: "white",
                        display: "inline-block",
                        animation: "spin 0.8s linear infinite",
                      }}
                    />
                    <span>Creating workspace…</span>
                  </>
                ) : (
                  <>
                    <span>Create account</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>

              {/* Terms disclaimer */}
              <p
                style={{
                  textAlign: "center",
                  fontSize: 11,
                  color: "#94a3b8",
                  lineHeight: 1.35,
                  margin: "2px 0 0 0",
                }}
              >
                By creating an account, you agree to Knowra&apos;s{" "}
                <a href="#" style={{ color: "#64748b", textDecoration: "underline" }}>
                  Terms of Service
                </a>{" "}
                and{" "}
                <a href="#" style={{ color: "#64748b", textDecoration: "underline" }}>
                  Privacy Policy
                </a>
                .
              </p>

              {/* Switch to Sign In */}
              <p style={{ textAlign: "center", fontSize: 12.5, color: "#64748b", margin: "2px 0 0 0" }}>
                Already have an account?{" "}
                <button
                  type="button"
                  onClick={() => switchTab("signin")}
                  style={{
                    background: "none",
                    border: "none",
                    color: "#2563eb",
                    fontWeight: 600,
                    cursor: "pointer",
                    padding: 0,
                    fontSize: 12.5,
                  }}
                >
                  Sign in
                </button>
              </p>
            </form>
          )}
        </div>

        {/* Footer Security Badges */}
        <div
          style={{
            paddingTop: 16,
            marginTop: 16,
            borderTop: "1px solid #f1f5f9",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 14,
            color: "#94a3b8",
            fontSize: 11,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <Shield size={12} color="#64748b" />
            <span>SOC 2 Type II Certified</span>
          </div>
          <div style={{ width: 3, height: 3, borderRadius: "50%", background: "#cbd5e1" }} />
          <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
            <Lock size={12} color="#64748b" />
            <span>256-bit AES Encryption</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT PANEL: PRODUCT INTELLIGENCE SHOWCASE ─────────────────────── */}
      <div
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          alignItems: "center",
          padding: "40px 48px",
          background: "linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #0f172a 100%)",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {/* Glow Spheres */}
        <div
          style={{
            position: "absolute",
            top: -100,
            right: -100,
            width: 450,
            height: 450,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(99,102,241,0.2) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />
        <div
          style={{
            position: "absolute",
            bottom: -80,
            left: -80,
            width: 380,
            height: 380,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(37,99,235,0.18) 0%, transparent 70%)",
            pointerEvents: "none",
          }}
        />

        <div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 520 }}>
          {/* ── Chat Intelligence Card ── */}
          <div
            style={{
              background: "rgba(15, 23, 42, 0.75)",
              backdropFilter: "blur(16px)",
              border: "1px solid rgba(255, 255, 255, 0.12)",
              borderRadius: 14,
              overflow: "hidden",
              boxShadow: "0 20px 50px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.06)",
              marginBottom: 26,
            }}
          >
            {/* Window Title Bar */}
            <div
              style={{
                background: "rgba(30, 41, 59, 0.8)",
                padding: "10px 16px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
              }}
            >
              <div style={{ display: "flex", gap: 6 }}>
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#ef4444", opacity: 0.85 }} />
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#f59e0b", opacity: 0.85 }} />
                <div style={{ width: 9, height: 9, borderRadius: "50%", background: "#10b981", opacity: 0.85 }} />
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                  fontSize: 11,
                  color: "#94a3b8",
                  fontWeight: 500,
                }}
              >
                <Sparkles size={12} color="#818cf8" />
                <span>Ask Knowra · Multi-Meeting RAG</span>
              </div>
              <div style={{ width: 30 }} />
            </div>

            {/* Chat Body */}
            <div style={{ padding: "16px 18px 14px 18px" }}>
              {/* Search Bar Input Simulation */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: "rgba(255, 255, 255, 0.05)",
                  border: "1px solid rgba(255, 255, 255, 0.1)",
                  borderRadius: 8,
                  padding: "8px 12px",
                  marginBottom: 14,
                }}
              >
                <div
                  style={{
                    fontSize: 9,
                    fontWeight: 700,
                    background: "linear-gradient(135deg, #3b82f6, #6366f1)",
                    color: "white",
                    padding: "2px 6px",
                    borderRadius: 4,
                    letterSpacing: "0.03em",
                  }}
                >
                  AI
                </div>
                <span style={{ fontSize: 12, color: "#64748b", flex: 1 }}>
                  Ask anything across meetings, transcripts, and action items…
                </span>
                <div
                  style={{
                    width: 20,
                    height: 20,
                    borderRadius: "50%",
                    background: "rgba(99, 102, 241, 0.2)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  <ArrowRight size={11} color="#818cf8" />
                </div>
              </div>

              {/* Chat Messages */}
              {CHAT_EXCHANGE.map((msg, idx) => (
                <div key={idx} style={{ marginBottom: 10 }}>
                  <div
                    style={{
                      display: "flex",
                      justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                    }}
                  >
                    <div
                      style={{
                        maxWidth: "88%",
                        padding: "9px 13px",
                        borderRadius:
                          msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                        background:
                          msg.role === "user"
                            ? "linear-gradient(135deg, #2563eb, #4f46e5)"
                            : "rgba(255, 255, 255, 0.08)",
                        color: msg.role === "user" ? "#ffffff" : "#f1f5f9",
                        fontSize: 12,
                        lineHeight: 1.55,
                        border: msg.role === "assistant" ? "1px solid rgba(255, 255, 255, 0.08)" : "none",
                      }}
                    >
                      {msg.text}
                    </div>
                  </div>

                  {msg.role === "assistant" && msg.cite && (
                    <div
                      style={{
                        marginTop: 5,
                        marginLeft: 4,
                        display: "inline-flex",
                        alignItems: "center",
                        gap: 5,
                        background: "rgba(99, 102, 241, 0.12)",
                        border: "1px solid rgba(99, 102, 241, 0.3)",
                        borderRadius: 20,
                        padding: "2px 8px",
                        fontSize: 10.5,
                        color: "#a5b4fc",
                      }}
                    >
                      <CheckCircle2 size={10} color="#818cf8" />
                      <span>
                        Verified citation:{" "}
                        <strong style={{ color: "#c7d2fe", fontWeight: 600 }}>{msg.cite}</strong>
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* ── Headline & Copy ── */}
          <div style={{ textAlign: "center", marginBottom: 22 }}>
            <h2
              style={{
                fontSize: 22,
                fontWeight: 700,
                color: "#f8fafc",
                letterSpacing: "-0.4px",
                margin: "0 0 8px 0",
              }}
            >
              Every conversation. Verifiable intelligence.
            </h2>
            <p
              style={{
                fontSize: 13.5,
                color: "#94a3b8",
                lineHeight: 1.55,
                maxWidth: 420,
                margin: "0 auto",
              }}
            >
              Connect your calendar and team channels. Search transcripts, extract action items,
              and query collective organization memory with high precision.
            </p>
          </div>

          {/* ── 2x2 Feature Cards ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {CAPABILITIES.map((cap, i) => {
              const Icon = cap.icon;
              return (
                <div
                  key={i}
                  style={{
                    background: "rgba(255, 255, 255, 0.04)",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                    borderRadius: 10,
                    padding: "12px",
                    display: "flex",
                    alignItems: "flex-start",
                    gap: 10,
                    backdropFilter: "blur(8px)",
                  }}
                >
                  <div
                    style={{
                      width: 28,
                      height: 28,
                      borderRadius: 7,
                      flexShrink: 0,
                      background: `${cap.color}20`,
                      border: `1px solid ${cap.color}40`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                    }}
                  >
                    <Icon size={14} color={cap.color} />
                  </div>
                  <div>
                    <h3
                      style={{
                        fontSize: 12,
                        fontWeight: 600,
                        color: "#f1f5f9",
                        margin: "0 0 2px 0",
                      }}
                    >
                      {cap.title}
                    </h3>
                    <p style={{ fontSize: 11, color: "#94a3b8", lineHeight: 1.4, margin: 0 }}>
                      {cap.desc}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={null}>
      <LoginFormContent />
    </Suspense>
  );
}
