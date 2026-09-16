import { Suspense } from "react";
import type { Metadata } from "next";
import { OAuthCallbackHandler } from "@/components/auth/OAuthCallbackHandler";

export const metadata: Metadata = {
  title: "Authenticating — Knowra",
  description: "Verifying single sign-on enterprise credentials.",
};

export default function OAuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center bg-[#0a0d14] text-white">
          <div className="w-8 h-8 border-2 border-slate-700 border-t-blue-500 rounded-full animate-spin" />
        </div>
      }
    >
      <OAuthCallbackHandler />
    </Suspense>
  );
}
