"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { z } from "zod";
import { api } from "@/lib/api/client";
import { AUTH } from "@/lib/api/endpoints";
import { useSession } from "@/lib/auth/session";
import { SessionSchema } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/card";
import { Mail, Lock, Eye, EyeOff, Brain } from "lucide-react";

const LoginSchema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export default function LoginPage() {
  const router = useRouter();
  const { login } = useSession();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [apiError, setApiError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setApiError("");
    setErrors({});

    const validation = LoginSchema.safeParse({ email, password });
    if (!validation.success) {
      const fieldErrors: { email?: string; password?: string } = {};
      for (const issue of validation.error.issues) {
        const key = issue.path[0] as "email" | "password";
        fieldErrors[key] = issue.message;
      }
      setErrors(fieldErrors);
      return;
    }

    setIsLoading(true);
    try {
      // FastAPI OAuth2 form login
      const formData = new URLSearchParams();
      formData.set("username", email);
      formData.set("password", password);

      const rawResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}${AUTH.login()}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
          body: formData.toString(),
        }
      );

      if (!rawResponse.ok) {
        const err = await rawResponse.json().catch(() => ({}));
        throw new Error(err.detail ?? "Invalid credentials");
      }

      const raw = await rawResponse.json();
      
      // Fetch user profile
      const meResponse = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"}${AUTH.me()}`,
        { headers: { Authorization: `Bearer ${raw.access_token}` } }
      );
      const user = await meResponse.json();

      login(raw.access_token, raw.refresh_token ?? "", user);
      router.push("/");
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-dvh flex items-center justify-center bg-[var(--background)] p-4">
      {/* Background Glow */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 60% 50% at 50% 0%, rgba(79,124,255,0.08) 0%, transparent 70%)",
        }}
      />

      <div className="w-full max-w-sm relative z-10">
        {/* Logo */}
        <div className="flex flex-col items-center gap-3 mb-8">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[var(--primary)] to-[var(--secondary)] flex items-center justify-center shadow-[var(--shadow-glow)]">
            <Brain size={22} className="text-white" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold text-[var(--foreground)]">Knowra</h1>
            <p className="text-sm text-[var(--muted)] mt-1">Enterprise Meeting Intelligence</p>
          </div>
        </div>

        {/* Card */}
        <div
          className="rounded-[var(--radius-lg)] border border-[var(--border)] p-6 space-y-5"
          style={{ background: "var(--surface-1)" }}
        >
          <div>
            <h2 className="text-lg font-semibold text-[var(--foreground)]">Sign In</h2>
            <p className="text-xs text-[var(--muted)] mt-1">
              Access your organization&apos;s knowledge base
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" id="login-form">
            <Input
              id="login-email"
              label="Email"
              type="email"
              placeholder="you@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              error={errors.email}
              leftIcon={<Mail size={13} />}
              autoComplete="email"
            />

            <div>
              <Input
                id="login-password"
                label="Password"
                type={showPw ? "text" : "password"}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                error={errors.password}
                leftIcon={<Lock size={13} />}
                autoComplete="current-password"
              />
              <button
                type="button"
                onClick={() => setShowPw((p) => !p)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-[var(--muted)] hover:text-[var(--foreground)] transition-colors"
                style={{ position: "relative", float: "right", marginTop: "-28px", marginRight: "8px" }}
              >
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>

            {apiError && (
              <div className="px-3 py-2.5 rounded-[var(--radius-sm)] bg-[var(--danger-muted)] border border-[rgba(239,68,68,0.2)]">
                <p className="text-xs text-[var(--danger)]">{apiError}</p>
              </div>
            )}

            <Button
              type="submit"
              variant="primary"
              size="lg"
              isLoading={isLoading}
              className="w-full mt-2"
              id="login-submit-btn"
            >
              Sign In to Knowra
            </Button>
          </form>
        </div>

        <p className="text-center text-[10px] text-[var(--muted)] mt-6">
          Protected by enterprise SSO & RBAC
        </p>
      </div>
    </div>
  );
}
