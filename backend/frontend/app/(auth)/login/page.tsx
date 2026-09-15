"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { useSession } from "@/lib/auth/session";
import {
  Eye, EyeOff, ArrowRight, Brain, Shield,
  Mic2, GitBranch, BarChart3, Lock, Users, HelpCircle,
} from "lucide-react";

// ─── Validation ───────────────────────────────────────────────────────────────
const EmailSchema    = z.string().email("Enter your company email address");
const PasswordSchema = z.string().min(1, "Password is required");
type Step = "email" | "password";

// ─── Internal stats for right panel ──────────────────────────────────────────
const STATS = [
  { value: "12,400+", label: "Meetings Processed" },
  { value: "98.2%",   label: "Transcription Accuracy" },
  { value: "3.4s",    label: "Avg Query Response" },
  { value: "500",     label: "Active Employees" },
];

// ─── Capabilities list ────────────────────────────────────────────────────────
const CAPABILITIES = [
  { icon: Mic2,       label: "Meeting Transcription & Diarization" },
  { icon: Brain,      label: "Permission-Aware RAG Search" },
  { icon: GitBranch,  label: "Organizational Knowledge Graph" },
  { icon: BarChart3,  label: "AI Quality & Cost Observability" },
];

// ─── Page ─────────────────────────────────────────────────────────────────────
export default function LoginPage() {
  const router    = useRouter();
  const { login } = useSession();

  const [step, setStep]         = useState<Step>("email");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [emailErr, setEmailErr] = useState("");
  const [pwErr, setPwErr]       = useState("");
  const [apiErr, setApiErr]     = useState("");
  const [loading, setLoading]   = useState(false);

  const handleEmailContinue = () => {
    const r = EmailSchema.safeParse(email);
    if (!r.success) { setEmailErr(r.error.issues[0].message); return; }
    // Enforce company domain hint (non-blocking, just a warning)
    setEmailErr("");
    setStep("password");
  };

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    const r = PasswordSchema.safeParse(password);
    if (!r.success) { setPwErr(r.error.issues[0].message); return; }
    setPwErr(""); setApiErr(""); setLoading(true);
    try {
      const fd = new URLSearchParams();
      fd.set("username", email); fd.set("password", password);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/login`,
        { method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: fd.toString() }
      );
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail ?? "Invalid credentials. Contact IT if the issue persists.");
      }
      const tokens = await res.json();
      const me = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}/auth/me`,
        { headers: { Authorization: `Bearer ${tokens.access_token}` } }
      );
      login(tokens.access_token, tokens.refresh_token ?? "", await me.json());
      router.push("/");
    } catch (err: unknown) {
      setApiErr(err instanceof Error ? err.message : "Sign in failed.");
    } finally { setLoading(false); }
  };

  return (
    <div style={{
      display: "flex", minHeight: "100dvh",
      fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
    }}>

      {/* ── LEFT: Login Form ────────────────────────────────────────────────── */}
      <div style={{
        width: 480, minWidth: 480,
        display: "flex", flexDirection: "column",
        justifyContent: "space-between",
        padding: "40px 52px",
        background: "#ffffff",
        borderRight: "1px solid #e5e7eb",
      }}>

        {/* Top: Logo + company label */}
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 8 }}>
            <div style={{
              width: 34, height: 34, borderRadius: 9,
              background: "linear-gradient(135deg, #1e3a8a 0%, #4f46e5 100%)",
              display: "flex", alignItems: "center", justifyContent: "center",
              boxShadow: "0 2px 8px rgba(79,70,229,0.3)",
            }}>
              <Brain size={17} color="white" />
            </div>
            <div>
              <p style={{ fontSize: 16, fontWeight: 700, color: "#111827", letterSpacing: "-0.2px", lineHeight: 1 }}>
                Knowra
              </p>
              <p style={{ fontSize: 10, color: "#6b7280", fontWeight: 500, letterSpacing: "0.04em", textTransform: "uppercase", marginTop: 1 }}>
                Internal Platform
              </p>
            </div>
          </div>
        </div>

        {/* Middle: Form */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", paddingTop: 16, paddingBottom: 16 }}>

          <div style={{ marginBottom: 28 }}>
            <h1 style={{ fontSize: 22, fontWeight: 700, color: "#111827", letterSpacing: "-0.3px", marginBottom: 6 }}>
              {step === "email" ? "Sign in to Knowra" : "Enter your password"}
            </h1>
            <p style={{ fontSize: 13, color: "#6b7280", lineHeight: 1.5 }}>
              {step === "email"
                ? "Use your company credentials to access the platform."
                : `Signing in as ${email}`}
            </p>
          </div>

          {/* ── SSO Button (Primary) ── */}
          {step === "email" && (
            <>
              <button
                type="button"
                id="sso-signin-btn"
                style={{
                  height: 44, borderRadius: 8, border: "1.5px solid #e5e7eb",
                  background: "#f8faff", color: "#1e3a8a",
                  fontSize: 14, fontWeight: 600,
                  cursor: "pointer", display: "flex", alignItems: "center",
                  justifyContent: "center", gap: 10,
                  marginBottom: 16,
                  transition: "all 0.15s",
                }}
                onMouseOver={(e) => { e.currentTarget.style.background = "#eff2ff"; e.currentTarget.style.borderColor = "#4f46e5"; }}
                onMouseOut={(e) => { e.currentTarget.style.background = "#f8faff"; e.currentTarget.style.borderColor = "#e5e7eb"; }}
              >
                {/* Microsoft logo */}
                <svg width="18" height="18" viewBox="0 0 21 21" fill="none">
                  <rect x="1" y="1" width="9" height="9" fill="#f25022"/>
                  <rect x="11" y="1" width="9" height="9" fill="#7fba00"/>
                  <rect x="1" y="11" width="9" height="9" fill="#00a4ef"/>
                  <rect x="11" y="11" width="9" height="9" fill="#ffb900"/>
                </svg>
                Sign in with Microsoft
              </button>

              {/* Divider */}
              <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 16 }}>
                <div style={{ flex: 1, height: 1, background: "#e5e7eb" }} />
                <span style={{ fontSize: 11, color: "#9ca3af", fontWeight: 500 }}>or use credentials</span>
                <div style={{ flex: 1, height: 1, background: "#e5e7eb" }} />
              </div>
            </>
          )}

          {/* Email/Password Form */}
          <form
            onSubmit={step === "email" ? (e) => { e.preventDefault(); handleEmailContinue(); } : handleSignIn}
            style={{ display: "flex", flexDirection: "column", gap: 14 }}
          >
            {/* Email field — always visible */}
            <div>
              <label style={{ display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 5, letterSpacing: "0.01em" }}
                htmlFor="email-input">
                Work Email
              </label>
              <input
                id="email-input"
                type="email"
                autoComplete="email"
                autoFocus={step === "email"}
                value={email}
                readOnly={step === "password"}
                onChange={(e) => { setEmail(e.target.value); setEmailErr(""); }}
                placeholder="firstname.lastname@company.com"
                style={{
                  width: "100%", height: 42, padding: "0 12px",
                  borderRadius: 7, fontSize: 13.5, color: "#111827",
                  border: emailErr ? "1.5px solid #ef4444" : "1.5px solid #d1d5db",
                  background: step === "password" ? "#f9fafb" : "#fff",
                  outline: "none", boxSizing: "border-box",
                  cursor: step === "password" ? "default" : "text",
                  transition: "border-color 0.15s",
                }}
                onFocus={(e) => step === "email" && !emailErr && (e.target.style.borderColor = "#4f46e5")}
                onBlur={(e) => !emailErr && (e.target.style.borderColor = "#d1d5db")}
              />
              {emailErr && <p style={{ marginTop: 4, fontSize: 11.5, color: "#ef4444" }}>{emailErr}</p>}
              {step === "password" && (
                <button type="button" onClick={() => { setStep("email"); setPwErr(""); setApiErr(""); }}
                  style={{ marginTop: 4, fontSize: 11.5, color: "#4f46e5", background: "none", border: "none", cursor: "pointer", padding: 0, fontWeight: 500 }}>
                  ← Change email
                </button>
              )}
            </div>

            {/* Password field — shown only on step 2 */}
            {step === "password" && (
              <div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                  <label style={{ fontSize: 12, fontWeight: 600, color: "#374151", letterSpacing: "0.01em" }} htmlFor="pw-input">
                    Password
                  </label>
                  <a href="#" style={{ fontSize: 11.5, color: "#4f46e5", textDecoration: "none", fontWeight: 500 }}>
                    Forgot password?
                  </a>
                </div>
                <div style={{ position: "relative" }}>
                  <input
                    id="pw-input"
                    type={showPw ? "text" : "password"}
                    autoFocus
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => { setPassword(e.target.value); setPwErr(""); }}
                    placeholder="Enter your password"
                    style={{
                      width: "100%", height: 42, padding: "0 42px 0 12px",
                      borderRadius: 7, fontSize: 13.5, color: "#111827",
                      border: pwErr ? "1.5px solid #ef4444" : "1.5px solid #d1d5db",
                      background: "#fff", outline: "none", boxSizing: "border-box",
                      transition: "border-color 0.15s",
                    }}
                    onFocus={(e) => !pwErr && (e.target.style.borderColor = "#4f46e5")}
                    onBlur={(e) => !pwErr && (e.target.style.borderColor = "#d1d5db")}
                  />
                  <button type="button" onClick={() => setShowPw((p) => !p)}
                    style={{
                      position: "absolute", right: 11, top: "50%", transform: "translateY(-50%)",
                      background: "none", border: "none", cursor: "pointer", color: "#9ca3af",
                      display: "flex", padding: 0,
                    }}>
                    {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                {pwErr && <p style={{ marginTop: 4, fontSize: 11.5, color: "#ef4444" }}>{pwErr}</p>}
              </div>
            )}

            {/* API Error */}
            {apiErr && (
              <div style={{
                padding: "10px 13px", borderRadius: 7,
                background: "#fef2f2", border: "1px solid #fecaca",
                fontSize: 12.5, color: "#dc2626", lineHeight: 1.5,
              }}>
                {apiErr}
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              id={step === "email" ? "email-next-btn" : "signin-submit-btn"}
              disabled={loading}
              style={{
                height: 42, borderRadius: 7, border: "none",
                background: loading ? "#9ca3af" : "linear-gradient(135deg, #1e3a8a 0%, #4f46e5 100%)",
                color: "white", fontSize: 13.5, fontWeight: 600,
                cursor: loading ? "not-allowed" : "pointer",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 7,
                boxShadow: loading ? "none" : "0 2px 10px rgba(79,70,229,0.3)",
                transition: "opacity 0.15s",
                marginTop: 2,
              }}
              onMouseOver={(e) => !loading && (e.currentTarget.style.opacity = "0.92")}
              onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
            >
              {loading
                ? <span style={{ width: 15, height: 15, borderRadius: "50%", border: "2px solid rgba(255,255,255,0.4)", borderTopColor: "white", animation: "spin 0.7s linear infinite", display: "inline-block" }} />
                : step === "email"
                  ? <><span>Continue</span><ArrowRight size={14} /></>
                  : <><span>Sign In</span><Lock size={13} /></>
              }
            </button>
          </form>
        </div>

        {/* Bottom: IT support + security */}
        <div>
          <div style={{
            padding: "14px 16px", borderRadius: 8,
            background: "#f8faff", border: "1px solid #e0e8ff",
            display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 16,
          }}>
            <HelpCircle size={14} color="#4f46e5" style={{ marginTop: 1, flexShrink: 0 }} />
            <div>
              <p style={{ fontSize: 12, fontWeight: 600, color: "#1e3a8a", marginBottom: 2 }}>
                Need access or having trouble signing in?
              </p>
              <p style={{ fontSize: 11.5, color: "#4b5563", lineHeight: 1.5 }}>
                Account access is managed by IT. Contact{" "}
                <a href="mailto:it-support@company.com" style={{ color: "#4f46e5", textDecoration: "none", fontWeight: 500 }}>
                  it-support@company.com
                </a>{" "}
                or raise a ticket in the IT helpdesk portal.
              </p>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 5, color: "#9ca3af", fontSize: 11 }}>
            <Shield size={11} />
            <span>Restricted to authorized personnel · SOC 2 Type II</span>
          </div>
        </div>
      </div>

      {/* ── RIGHT: Internal Platform Overview ──────────────────────────────── */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "48px 40px",
        background: "linear-gradient(150deg, #eef2ff 0%, #f0f4ff 40%, #ede9fe 100%)",
        position: "relative",
        overflow: "hidden",
      }}>
        {/* Background decoration */}
        <div style={{ position: "absolute", top: -100, right: -100, width: 450, height: 450, borderRadius: "50%", background: "radial-gradient(circle, rgba(79,70,229,0.08) 0%, transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: -60, left: -60, width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle, rgba(30,58,138,0.06) 0%, transparent 70%)", pointerEvents: "none" }} />

        <div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 520 }}>

          {/* Header */}
          <div style={{ marginBottom: 32 }}>
            <div style={{
              display: "inline-flex", alignItems: "center", gap: 6,
              padding: "4px 12px", borderRadius: 20,
              background: "rgba(79,70,229,0.08)", border: "1px solid rgba(79,70,229,0.15)",
              fontSize: 11, fontWeight: 600, color: "#4f46e5",
              letterSpacing: "0.05em", textTransform: "uppercase", marginBottom: 16,
            }}>
              <Users size={11} />
              Internal Platform · ~500 Employees
            </div>
            <h2 style={{
              fontSize: 26, fontWeight: 700, color: "#0f172a",
              letterSpacing: "-0.5px", lineHeight: 1.25, marginBottom: 10,
            }}>
              Your organization&apos;s<br />meeting intelligence hub
            </h2>
            <p style={{ fontSize: 13.5, color: "#475569", lineHeight: 1.65, maxWidth: 400 }}>
              Knowra centralizes all internal meeting knowledge — transcripts, decisions, action items — and makes it instantly searchable by authorized staff.
            </p>
          </div>

          {/* Stats row */}
          <div style={{
            display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 1,
            background: "#e5e7eb", borderRadius: 12, overflow: "hidden",
            border: "1px solid #e5e7eb", marginBottom: 28,
          }}>
            {STATS.map((s, i) => (
              <div key={i} style={{
                background: "white", padding: "16px 14px", textAlign: "center",
              }}>
                <p style={{ fontSize: 20, fontWeight: 700, color: "#1e3a8a", letterSpacing: "-0.5px", marginBottom: 3 }}>
                  {s.value}
                </p>
                <p style={{ fontSize: 10.5, color: "#6b7280", fontWeight: 500, lineHeight: 1.3 }}>
                  {s.label}
                </p>
              </div>
            ))}
          </div>

          {/* Capabilities */}
          <div style={{
            background: "white", borderRadius: 12,
            border: "1px solid #e5e7eb",
            overflow: "hidden",
            boxShadow: "0 2px 12px rgba(0,0,0,0.04)",
            marginBottom: 20,
          }}>
            <div style={{
              padding: "12px 16px", borderBottom: "1px solid #f1f5f9",
              background: "#f8faff",
            }}>
              <p style={{ fontSize: 11, fontWeight: 700, color: "#374151", letterSpacing: "0.05em", textTransform: "uppercase" }}>
                Platform Capabilities
              </p>
            </div>
            {CAPABILITIES.map((c, i) => {
              const Icon = c.icon;
              return (
                <div key={i} style={{
                  display: "flex", alignItems: "center", gap: 12,
                  padding: "12px 16px",
                  borderBottom: i < CAPABILITIES.length - 1 ? "1px solid #f1f5f9" : "none",
                }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: 7,
                    background: "#eef2ff",
                    display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                  }}>
                    <Icon size={14} color="#4f46e5" />
                  </div>
                  <p style={{ fontSize: 13, fontWeight: 500, color: "#1f2937" }}>{c.label}</p>
                  <div style={{
                    marginLeft: "auto",
                    width: 6, height: 6, borderRadius: "50%",
                    background: "#10b981",
                    boxShadow: "0 0 0 2px rgba(16,185,129,0.2)",
                  }} />
                </div>
              );
            })}
          </div>

          {/* Access note */}
          <div style={{
            display: "flex", alignItems: "center", gap: 8,
            padding: "10px 14px", borderRadius: 8,
            background: "rgba(79,70,229,0.05)", border: "1px solid rgba(79,70,229,0.12)",
          }}>
            <Lock size={12} color="#4f46e5" style={{ flexShrink: 0 }} />
            <p style={{ fontSize: 11.5, color: "#4b5563", lineHeight: 1.45 }}>
              Access is restricted to authorized employees. Role-based permissions are enforced at the data layer. All activity is logged and audited.
            </p>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
