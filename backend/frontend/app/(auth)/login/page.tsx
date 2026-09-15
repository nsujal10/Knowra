"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { useSession } from "@/lib/auth/session";
import { Eye, EyeOff, ArrowRight, Brain, Mic2, GitBranch, BarChart3, Shield, CheckCircle2 } from "lucide-react";

// ─── Validation ───────────────────────────────────────────────────────────────
const EmailSchema   = z.string().email("Enter a valid email address");
const PasswordSchema = z.string().min(6, "Password must be at least 6 characters");
type Step = "email" | "password";

// ─── Right-panel features ─────────────────────────────────────────────────────
const FEATURES = [
  { icon: Mic2,       color: "#4f7cff", label: "Enterprise Transcription",   desc: "Speaker-diarized, >95% accuracy" },
  { icon: Brain,      color: "#7c5cfc", label: "Permission-Aware RAG",       desc: "Cited answers from your meetings" },
  { icon: GitBranch,  color: "#10b981", label: "Knowledge Graph",            desc: "Connect people, topics & decisions" },
  { icon: BarChart3,  color: "#f59e0b", label: "AI Observability",           desc: "WER, faithfulness, cost tracking" },
];

// ─── Static chat preview data ─────────────────────────────────────────────────
const CHAT_PREVIEW = [
  { role: "user",      text: "What tasks are overdue from last week?" },
  { role: "assistant", text: "The API rate-limit fix (Dev team) is 3 days past due. The mobile onboarding flow is blocked — no design handoff received yet.", cite: "Q3 Planning · Sep 12" },
];

export default function LoginPage() {
  const router      = useRouter();
  const { login }   = useSession();

  const [tab, setTab]           = useState<"signin" | "signup">("signin");
  const [step, setStep]         = useState<Step>("email");
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw]     = useState(false);
  const [emailErr, setEmailErr] = useState("");
  const [pwErr, setPwErr]       = useState("");
  const [apiErr, setApiErr]     = useState("");
  const [loading, setLoading]   = useState(false);

  const switchTab = (t: "signin" | "signup") => {
    setTab(t);
    setStep("email");
    setEmail("");
    setPassword("");
    setEmailErr("");
    setPwErr("");
    setApiErr("");
  };

  const handleEmailContinue = () => {
    const r = EmailSchema.safeParse(email);
    if (!r.success) { setEmailErr(r.error.issues[0].message); return; }
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
      if (!res.ok) { const e = await res.json().catch(() => ({})); throw new Error(e.detail ?? "Invalid credentials"); }
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
    <div style={{ display: "flex", minHeight: "100dvh", fontFamily: "Inter, system-ui, sans-serif" }}>

      {/* ── LEFT PANEL ──────────────────────────────────────────────────────── */}
      <div style={{
        width: "480px",
        minWidth: "480px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        padding: "48px 56px",
        background: "#ffffff",
        borderRight: "1px solid #f0f0f0",
        position: "relative",
        zIndex: 1,
      }}>

        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "40px" }}>
          <div style={{
            width: 36, height: 36, borderRadius: 10,
            background: "linear-gradient(135deg, #4f7cff 0%, #7c5cfc 100%)",
            display: "flex", alignItems: "center", justifyContent: "center",
            boxShadow: "0 4px 12px rgba(79,124,255,0.3)",
          }}>
            <Brain size={18} color="white" />
          </div>
          <span style={{ fontSize: 18, fontWeight: 700, color: "#0f1117", letterSpacing: "-0.3px" }}>
            Knowra
          </span>
        </div>

        {/* Tab switcher */}
        <div style={{ display: "flex", borderBottom: "1px solid #e5e7eb", marginBottom: "32px" }}>
          {(["signin", "signup"] as const).map((t) => (
            <button
              key={t}
              onClick={() => switchTab(t)}
              style={{
                paddingBottom: 12,
                paddingRight: 20,
                fontSize: 14,
                fontWeight: 500,
                border: "none",
                background: "transparent",
                cursor: "pointer",
                color: tab === t ? "#4f7cff" : "#6b7280",
                borderBottom: tab === t ? "2px solid #4f7cff" : "2px solid transparent",
                marginBottom: -1,
                transition: "all 0.15s",
              }}
            >
              {t === "signin" ? "Sign in" : "Create account"}
            </button>
          ))}
        </div>

        {/* ─── SIGN IN FLOW ──────────────────────────────────────────────── */}
        {tab === "signin" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

            {step === "email" ? (
              <>
                {/* Email field */}
                <div>
                  <label style={{ display: "block", fontSize: 13, fontWeight: 500, color: "#374151", marginBottom: 6 }}
                    htmlFor="email-input">
                    Email address
                  </label>
                  <input
                    id="email-input"
                    type="email"
                    autoFocus
                    autoComplete="email"
                    value={email}
                    onChange={(e) => { setEmail(e.target.value); setEmailErr(""); }}
                    onKeyDown={(e) => e.key === "Enter" && handleEmailContinue()}
                    placeholder="you@company.com"
                    style={{
                      width: "100%", height: 44, padding: "0 14px",
                      borderRadius: 8, border: emailErr ? "1.5px solid #ef4444" : "1.5px solid #d1d5db",
                      fontSize: 14, color: "#111827", background: "#fff",
                      outline: "none", boxSizing: "border-box",
                      transition: "border-color 0.15s",
                    }}
                    onFocus={(e) => !emailErr && (e.target.style.borderColor = "#4f7cff")}
                    onBlur={(e) => !emailErr && (e.target.style.borderColor = "#d1d5db")}
                  />
                  {emailErr && <p style={{ marginTop: 4, fontSize: 12, color: "#ef4444" }}>{emailErr}</p>}
                </div>

                <button
                  onClick={handleEmailContinue}
                  id="email-continue-btn"
                  style={{
                    height: 44, borderRadius: 8, border: "none",
                    background: "linear-gradient(135deg, #4f7cff 0%, #7c5cfc 100%)",
                    color: "white", fontSize: 14, fontWeight: 600,
                    cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                    boxShadow: "0 2px 12px rgba(79,124,255,0.35)",
                    transition: "opacity 0.15s, transform 0.1s",
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.opacity = "0.9")}
                  onMouseOut={(e) => (e.currentTarget.style.opacity = "1")}
                >
                  Continue <ArrowRight size={15} />
                </button>

                {/* Divider */}
                <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "4px 0" }}>
                  <div style={{ flex: 1, height: 1, background: "#e5e7eb" }} />
                  <span style={{ fontSize: 12, color: "#9ca3af" }}>or</span>
                  <div style={{ flex: 1, height: 1, background: "#e5e7eb" }} />
                </div>

                {/* SSO Buttons */}
                {[
                  { emoji: "🔷", label: "Continue with Microsoft" },
                  { emoji: "💬", label: "Continue with Slack" },
                  { emoji: "🏢", label: "Continue with your organization" },
                ].map((opt) => (
                  <button key={opt.label}
                    style={{
                      height: 44, borderRadius: 8, border: "1.5px solid #e5e7eb",
                      background: "#fff", color: "#374151", fontSize: 14, fontWeight: 500,
                      cursor: "pointer", display: "flex", alignItems: "center", gap: 10, padding: "0 14px",
                      transition: "border-color 0.15s, background 0.15s",
                    }}
                    onMouseOver={(e) => { e.currentTarget.style.borderColor = "#d1d5db"; e.currentTarget.style.background = "#f9fafb"; }}
                    onMouseOut={(e) => { e.currentTarget.style.borderColor = "#e5e7eb"; e.currentTarget.style.background = "#fff"; }}
                  >
                    <span style={{ fontSize: 18 }}>{opt.emoji}</span>
                    {opt.label}
                  </button>
                ))}
              </>
            ) : (
              /* Password step */
              <form onSubmit={handleSignIn} style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {/* Email pill */}
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "8px 12px", background: "#f9fafb", borderRadius: 8, border: "1px solid #e5e7eb",
                }}>
                  <span style={{ fontSize: 13, color: "#374151", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {email}
                  </span>
                  <button type="button" onClick={() => setStep("email")}
                    style={{ fontSize: 12, color: "#4f7cff", background: "none", border: "none", cursor: "pointer", fontWeight: 500, whiteSpace: "nowrap" }}>
                    Change
                  </button>
                </div>

                {/* Password field */}
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <label style={{ fontSize: 13, fontWeight: 500, color: "#374151" }} htmlFor="pw-input">
                      Password
                    </label>
                    <a href="#" style={{ fontSize: 12, color: "#4f7cff", textDecoration: "none" }}>Forgot password?</a>
                  </div>
                  <div style={{ position: "relative" }}>
                    <input
                      id="pw-input"
                      type={showPw ? "text" : "password"}
                      autoFocus
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => { setPassword(e.target.value); setPwErr(""); }}
                      placeholder="••••••••"
                      style={{
                        width: "100%", height: 44, padding: "0 44px 0 14px",
                        borderRadius: 8, border: pwErr ? "1.5px solid #ef4444" : "1.5px solid #d1d5db",
                        fontSize: 14, color: "#111827", background: "#fff",
                        outline: "none", boxSizing: "border-box",
                      }}
                      onFocus={(e) => !pwErr && (e.target.style.borderColor = "#4f7cff")}
                      onBlur={(e) => !pwErr && (e.target.style.borderColor = "#d1d5db")}
                    />
                    <button type="button" onClick={() => setShowPw((p) => !p)}
                      style={{
                        position: "absolute", right: 12, top: "50%", transform: "translateY(-50%)",
                        background: "none", border: "none", cursor: "pointer", color: "#9ca3af", display: "flex",
                      }}>
                      {showPw ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                  {pwErr && <p style={{ marginTop: 4, fontSize: 12, color: "#ef4444" }}>{pwErr}</p>}
                </div>

                {apiErr && (
                  <div style={{
                    padding: "10px 14px", borderRadius: 8, background: "#fef2f2",
                    border: "1px solid #fecaca", fontSize: 13, color: "#dc2626",
                  }}>
                    {apiErr}
                  </div>
                )}

                <button type="submit" id="signin-submit-btn" disabled={loading}
                  style={{
                    height: 44, borderRadius: 8, border: "none",
                    background: loading ? "#9ca3af" : "linear-gradient(135deg, #4f7cff 0%, #7c5cfc 100%)",
                    color: "white", fontSize: 14, fontWeight: 600,
                    cursor: loading ? "not-allowed" : "pointer",
                    display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                    boxShadow: loading ? "none" : "0 2px 12px rgba(79,124,255,0.35)",
                  }}>
                  {loading
                    ? <span style={{ width: 16, height: 16, borderRadius: "50%", border: "2px solid white", borderTopColor: "transparent", animation: "spin 0.7s linear infinite", display: "inline-block" }} />
                    : <><span>Sign in to Knowra</span><ArrowRight size={15} /></>
                  }
                </button>
              </form>
            )}
          </div>
        )}

        {/* ─── SIGN UP FLOW ──────────────────────────────────────────────── */}
        {tab === "signup" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              { emoji: "🔵", label: "Continue with Google" },
              { emoji: "🔷", label: "Continue with Microsoft" },
              { emoji: "💬", label: "Continue with Slack" },
              { emoji: "🍎", label: "Continue with Apple" },
            ].map((opt) => (
              <button key={opt.label}
                style={{
                  height: 44, borderRadius: 8, border: "1.5px solid #e5e7eb",
                  background: "#fff", color: "#374151", fontSize: 14, fontWeight: 500,
                  cursor: "pointer", display: "flex", alignItems: "center", gap: 10, padding: "0 14px",
                  transition: "border-color 0.15s, background 0.15s",
                }}
                onMouseOver={(e) => { e.currentTarget.style.background = "#f9fafb"; e.currentTarget.style.borderColor = "#d1d5db"; }}
                onMouseOut={(e) => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.borderColor = "#e5e7eb"; }}
              >
                <span style={{ fontSize: 18 }}>{opt.emoji}</span>
                {opt.label}
              </button>
            ))}

            <div style={{ display: "flex", alignItems: "center", gap: 12, margin: "4px 0" }}>
              <div style={{ flex: 1, height: 1, background: "#e5e7eb" }} />
              <span style={{ fontSize: 12, color: "#9ca3af" }}>or</span>
              <div style={{ flex: 1, height: 1, background: "#e5e7eb" }} />
            </div>

            <button onClick={() => switchTab("signin")}
              style={{
                background: "none", border: "none", cursor: "pointer",
                fontSize: 14, fontWeight: 500, color: "#4f7cff",
                textAlign: "center", textDecoration: "underline",
              }}>
              Continue with email and password
            </button>
          </div>
        )}

        {/* Legal */}
        <p style={{
          marginTop: 32, fontSize: 11.5, color: "#9ca3af",
          textAlign: "center", lineHeight: 1.6,
        }}>
          By {tab === "signin" ? "signing in" : "creating an account"}, I agree to Knowra&apos;s{" "}
          <a href="#" style={{ color: "#4f7cff", textDecoration: "none" }}>Terms of Service</a>{" "}
          and acknowledge I have read the{" "}
          <a href="#" style={{ color: "#4f7cff", textDecoration: "none" }}>Privacy Policy</a>.
        </p>

        {/* Security badge */}
        <div style={{
          marginTop: 20, display: "flex", alignItems: "center", justifyContent: "center",
          gap: 5, color: "#9ca3af", fontSize: 11,
        }}>
          <Shield size={12} />
          <span>SOC 2 compliant · End-to-end encrypted</span>
        </div>
      </div>

      {/* ── RIGHT PANEL ─────────────────────────────────────────────────────── */}
      <div style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "48px 40px",
        background: "linear-gradient(145deg, #f0f4ff 0%, #f4f0ff 50%, #edf6ff 100%)",
        position: "relative",
        overflow: "hidden",
      }}>

        {/* Decorative blobs */}
        <div style={{ position: "absolute", top: -120, right: -120, width: 400, height: 400, borderRadius: "50%", background: "radial-gradient(circle, rgba(79,124,255,0.12) 0%, transparent 70%)", pointerEvents: "none" }} />
        <div style={{ position: "absolute", bottom: -80, left: -80, width: 300, height: 300, borderRadius: "50%", background: "radial-gradient(circle, rgba(124,92,252,0.1) 0%, transparent 70%)", pointerEvents: "none" }} />

        <div style={{ position: "relative", zIndex: 1, width: "100%", maxWidth: 500 }}>

          {/* ── Chat Preview Card ── */}
          <div style={{
            background: "white",
            borderRadius: 16,
            overflow: "hidden",
            boxShadow: "0 8px 40px rgba(79,124,255,0.12), 0 2px 8px rgba(0,0,0,0.06)",
            marginBottom: 36,
          }}>
            {/* Titlebar */}
            <div style={{
              background: "linear-gradient(135deg, #1a1f35 0%, #2a1b5e 100%)",
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              gap: 12,
            }}>
              <div style={{ display: "flex", gap: 5 }}>
                {["#ff5f57","#febc2e","#28c840"].map((c) => (
                  <div key={c} style={{ width: 10, height: 10, borderRadius: "50%", background: c, opacity: 0.9 }} />
                ))}
              </div>
              <div style={{ display: "flex", gap: 6, marginLeft: 4 }}>
                {["🎙️","💬","📅","📋","🔗"].map((i) => (
                  <div key={i} style={{
                    width: 26, height: 26, borderRadius: 7,
                    background: "rgba(255,255,255,0.1)",
                    display: "flex", alignItems: "center", justifyContent: "center", fontSize: 13,
                  }}>{i}</div>
                ))}
              </div>
            </div>

            {/* Chat body */}
            <div style={{ padding: "16px", background: "#f8f9fb" }}>
              {/* Search bar */}
              <div style={{
                display: "flex", alignItems: "center", gap: 8,
                background: "white", borderRadius: 10, border: "1.5px solid #e5e7eb",
                padding: "8px 12px", marginBottom: 14,
                boxShadow: "0 1px 4px rgba(0,0,0,0.04)",
              }}>
                <span style={{
                  fontSize: 9, fontWeight: 700, background: "linear-gradient(135deg, #4f7cff, #7c5cfc)",
                  color: "white", padding: "2px 6px", borderRadius: 5, letterSpacing: "0.02em",
                }}>AI</span>
                <span style={{ fontSize: 12, color: "#9ca3af", flex: 1 }}>Ask anything about your meetings…</span>
                <div style={{
                  width: 24, height: 24, borderRadius: "50%",
                  background: "linear-gradient(135deg, #4f7cff, #7c5cfc)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                }}>
                  <ArrowRight size={12} color="white" />
                </div>
              </div>

              {/* Messages */}
              {CHAT_PREVIEW.map((msg, i) => (
                <div key={i} style={{ marginBottom: 10 }}>
                  <div style={{
                    display: "flex",
                    justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                  }}>
                    <div style={{
                      maxWidth: "85%",
                      padding: "9px 13px",
                      borderRadius: msg.role === "user" ? "14px 14px 4px 14px" : "14px 14px 14px 4px",
                      background: msg.role === "user"
                        ? "linear-gradient(135deg, #4f7cff, #7c5cfc)"
                        : "white",
                      color: msg.role === "user" ? "white" : "#374151",
                      fontSize: 12,
                      lineHeight: 1.55,
                      boxShadow: msg.role === "assistant" ? "0 1px 6px rgba(0,0,0,0.07)" : "none",
                      border: msg.role === "assistant" ? "1px solid #f0f0f0" : "none",
                    }}>
                      {msg.text}
                    </div>
                  </div>
                  {msg.role === "assistant" && msg.cite && (
                    <div style={{
                      marginTop: 6, marginLeft: 2,
                      display: "inline-flex", alignItems: "center", gap: 5,
                      background: "white", border: "1px solid #e0e8ff",
                      borderRadius: 20, padding: "3px 10px",
                      fontSize: 10.5, color: "#6b7280",
                      boxShadow: "0 1px 3px rgba(0,0,0,0.04)",
                    }}>
                      <CheckCircle2 size={10} color="#4f7cff" />
                      <span>Cited from <strong style={{ color: "#4f7cff", fontWeight: 600 }}>{msg.cite}</strong></span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* ── Headline ── */}
          <div style={{ textAlign: "center", marginBottom: 28 }}>
            <h2 style={{
              fontSize: 24, fontWeight: 700, color: "#0f1117",
              letterSpacing: "-0.4px", marginBottom: 8,
            }}>
              Meetings + Ask Knowra
            </h2>
            <p style={{
              fontSize: 14, color: "#6b7280", lineHeight: 1.65,
              maxWidth: 380, margin: "0 auto",
            }}>
              AI-powered meeting intelligence with verifiable citations.
              Connect your calendar, get instant answers from every conversation.
            </p>
          </div>

          {/* ── Feature Grid ── */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
            {FEATURES.map((f, i) => {
              const Icon = f.icon;
              return (
                <div key={i} style={{
                  background: "rgba(255,255,255,0.8)",
                  border: "1px solid rgba(255,255,255,0.9)",
                  borderRadius: 12,
                  padding: "12px 14px",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 10,
                  backdropFilter: "blur(8px)",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.04)",
                }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 8, flexShrink: 0,
                    background: `${f.color}15`,
                    display: "flex", alignItems: "center", justifyContent: "center",
                  }}>
                    <Icon size={15} color={f.color} />
                  </div>
                  <div>
                    <p style={{ fontSize: 12, fontWeight: 600, color: "#1f2937", marginBottom: 2 }}>{f.label}</p>
                    <p style={{ fontSize: 11, color: "#9ca3af", lineHeight: 1.4 }}>{f.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Spinner keyframe */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
