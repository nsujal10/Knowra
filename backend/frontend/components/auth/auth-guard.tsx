"use client";

import React, { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useSession } from "@/lib/auth/session";
import { Brain, ShieldCheck } from "lucide-react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useSession();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const redirectQuery =
        pathname && pathname !== "/" ? `?redirect=${encodeURIComponent(pathname)}` : "";
      router.replace(`/login${redirectQuery}`);
    }
  }, [isLoading, isAuthenticated, router, pathname]);

  if (isLoading) {
    return (
      <div
        className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0a0d14] text-white"
        style={{
          fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif",
        }}
      >
        {/* Glow ambient background */}
        <div
          style={{
            position: "absolute",
            width: 340,
            height: 340,
            borderRadius: "50%",
            background: "radial-gradient(circle, rgba(37,99,235,0.2) 0%, transparent 70%)",
            filter: "blur(40px)",
            pointerEvents: "none",
          }}
        />

        {/* Animated Brand Card */}
        <div className="relative z-10 flex flex-col items-center">
          <div
            style={{
              width: 56,
              height: 56,
              borderRadius: 14,
              background: "linear-gradient(135deg, #2563eb 0%, #4f46e5 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 8px 32px rgba(37,99,235,0.35)",
              animation: "pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite",
            }}
          >
            <Brain size={28} color="white" />
          </div>

          <h2 className="mt-5 text-base font-semibold text-slate-100 tracking-tight">
            Knowra Workspace
          </h2>
          <p className="mt-1.5 text-xs text-slate-400 flex items-center gap-2 font-normal">
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "#3b82f6",
                display: "inline-block",
                animation: "ping 1.4s cubic-bezier(0, 0, 0.2, 1) infinite",
              }}
            />
            Verifying enterprise session & permissions…
          </p>

          <div className="mt-6 flex items-center gap-1.5 text-[11px] text-slate-500 font-medium">
            <ShieldCheck size={14} className="text-emerald-500" />
            <span>End-to-end encrypted · RBAC enforced</span>
          </div>
        </div>

        <style>{`
          @keyframes pulse {
            0%, 100% { transform: scale(1); opacity: 1; }
            50% { transform: scale(1.05); opacity: 0.9; }
          }
        `}</style>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
