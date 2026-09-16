"use client";

import React, { useState } from "react";

interface SSOButtonsProps {
  redirectTarget?: string;
}

export function SSOButtons({ redirectTarget = "/" }: SSOButtonsProps) {
  const [initiating, setInitiating] = useState<string | null>(null);

  const handleSSO = (provider: "google" | "microsoft") => {
    setInitiating(provider);
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";
    const target = redirectTarget && redirectTarget.startsWith("/") ? redirectTarget : "/";
    window.location.href = `${apiUrl}/auth/${provider}/login?redirect=${encodeURIComponent(target)}`;
  };

  return (
    <div className="grid grid-cols-2 gap-2.5 mb-4">
      {/* Sign in with Google */}
      <button
        type="button"
        id="sso-btn-google"
        onClick={() => handleSSO("google")}
        disabled={initiating !== null}
        className="h-[38px] rounded-[7px] border border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300 active:bg-slate-100 text-slate-800 text-[13px] font-medium transition-all duration-150 flex items-center justify-center gap-2 shadow-xs disabled:opacity-60 cursor-pointer"
      >
        {initiating === "google" ? (
          <span className="inline-block w-4 h-4 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin" />
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" className="shrink-0">
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
        )}
        <span>Google</span>
      </button>

      {/* Sign in with Microsoft */}
      <button
        type="button"
        id="sso-btn-microsoft"
        onClick={() => handleSSO("microsoft")}
        disabled={initiating !== null}
        className="h-[38px] rounded-[7px] border border-slate-200 bg-white hover:bg-slate-50 hover:border-slate-300 active:bg-slate-100 text-slate-800 text-[13px] font-medium transition-all duration-150 flex items-center justify-center gap-2 shadow-xs disabled:opacity-60 cursor-pointer"
      >
        {initiating === "microsoft" ? (
          <span className="inline-block w-4 h-4 border-2 border-slate-300 border-t-blue-600 rounded-full animate-spin" />
        ) : (
          <svg width="15" height="15" viewBox="0 0 23 23" className="shrink-0">
            <rect width="10" height="10" fill="#f25022" />
            <rect x="12" width="10" height="10" fill="#7fba00" />
            <rect y="12" width="10" height="10" fill="#00a4ef" />
            <rect x="12" y="12" width="10" height="10" fill="#ffb900" />
          </svg>
        )}
        <span>Microsoft</span>
      </button>
    </div>
  );
}
