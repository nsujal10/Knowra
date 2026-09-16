"use client";

import React, { useEffect, useState, useRef } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useSession } from "@/lib/auth/session";
import type { User as AuthUser } from "@/lib/types";
import { Brain, AlertCircle, ArrowRight } from "lucide-react";
import Link from "next/link";

export function OAuthCallbackHandler() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { login } = useSession();

  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [statusText, setStatusText] = useState("Exchanging security tokens…");
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;
    processedRef.current = true;

    const accessToken = searchParams.get("access_token");
    const refreshToken = searchParams.get("refresh_token");
    const rawRedirect = searchParams.get("redirect");
    const errorParam = searchParams.get("error") || searchParams.get("detail");

    const targetUrl =
      rawRedirect && rawRedirect.startsWith("/") && !rawRedirect.startsWith("//")
        ? rawRedirect
        : "/";

    if (errorParam) {
      setErrorMessage(errorParam);
      return;
    }

    if (!accessToken || !refreshToken) {
      setErrorMessage("No authorization tokens were returned by the identity provider.");
      return;
    }

    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

    async function establishSession() {
      try {
        setStatusText("Verifying enterprise identity claims…");
        const meRes = await fetch(`${apiUrl}/auth/me`, {
          headers: { Authorization: `Bearer ${accessToken}` },
        });

        const userProfile = meRes.ok ? await meRes.json() : null;

        const mappedUser: AuthUser = {
          id: String(userProfile?.user_id ?? "unknown"),
          email: userProfile?.email ?? "sso-user@enterprise.com",
          full_name: userProfile?.full_name ?? "Enterprise User",
          role_code: userProfile?.role_code ?? "ADMIN",
          tenant_id: String(userProfile?.organization_id ?? "default"),
          is_active: userProfile?.is_active ?? true,
        };

        setStatusText("Provisioning workspace context…");
        login(accessToken!, refreshToken!, mappedUser);

        // Redirect to dashboard or original target
        router.replace(targetUrl);
      } catch (err: unknown) {
        setErrorMessage(
          err instanceof Error
            ? err.message
            : "Failed to establish enterprise session from SSO tokens."
        );
      }
    }

    establishSession();
  }, [searchParams, login, router]);

  if (errorMessage) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-4 font-sans">
        <div className="w-full max-w-md bg-white rounded-xl shadow-lg border border-slate-200 p-7 text-center">
          <div className="w-12 h-12 rounded-full bg-red-50 text-red-600 flex items-center justify-center mx-auto mb-4 border border-red-200">
            <AlertCircle size={24} />
          </div>
          <h1 className="text-lg font-bold text-slate-900 mb-2">Single Sign-On Failed</h1>
          <p className="text-xs text-red-600 bg-red-50 p-3 rounded-lg border border-red-200 mb-6 leading-relaxed">
            {errorMessage}
          </p>
          <Link
            href="/login"
            className="inline-flex items-center justify-center gap-2 w-full h-10 px-4 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold transition-colors"
          >
            <span>Return to Sign In</span>
            <ArrowRight size={15} />
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0a0d14] text-white p-4 font-sans relative overflow-hidden">
      {/* Ambient background glow */}
      <div
        className="absolute w-[400px] h-[400px] rounded-full pointer-events-none"
        style={{
          background: "radial-gradient(circle, rgba(37,99,235,0.22) 0%, transparent 70%)",
          filter: "blur(60px)",
        }}
      />

      <div className="relative z-10 flex flex-col items-center max-w-sm text-center">
        <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-500/30 mb-5 animate-pulse">
          <Brain size={28} color="white" />
        </div>

        <h2 className="text-base font-semibold text-slate-100 tracking-tight mb-2">
          Authenticating Enterprise SSO
        </h2>
        <p className="text-xs text-slate-400 mb-6 flex items-center gap-2">
          <span className="w-3.5 h-3.5 border-2 border-slate-500 border-t-blue-400 rounded-full animate-spin shrink-0" />
          <span>{statusText}</span>
        </p>

        <div className="text-[11px] text-slate-500 border-t border-slate-800 pt-4 w-full">
          Connecting to Knowra Multi-Tenant Intelligence Engine
        </div>
      </div>
    </div>
  );
}
