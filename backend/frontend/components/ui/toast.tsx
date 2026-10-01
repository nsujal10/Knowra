"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastType = "success" | "error" | "info";

interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastContextValue {
  show: (message: string, type?: ToastType) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

let externalToast: ToastContextValue | null = null;

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const show = useCallback((message: string, type: ToastType = "info") => {
    const id = Math.random().toString(36).substring(2, 9);
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      dismiss(id);
    }, 4000);
  }, [dismiss]);

  const value: ToastContextValue = {
    show,
    success: (msg: string) => show(msg, "success"),
    error: (msg: string) => show(msg, "error"),
    info: (msg: string) => show(msg, "info"),
  };

  externalToast = value;

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Toast container */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm pointer-events-none">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={cn(
              "pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl border shadow-lg text-xs font-medium animate-in slide-in-from-bottom-3 fade-in duration-200 backdrop-blur-md",
              t.type === "success" && "bg-white/95 border-emerald-200 text-slate-800 shadow-emerald-500/5",
              t.type === "error" && "bg-white/95 border-rose-200 text-slate-800 shadow-rose-500/5",
              t.type === "info" && "bg-white/95 border-slate-200 text-slate-800 shadow-slate-500/5"
            )}
          >
            {t.type === "success" && (
              <div className="w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center shrink-0">
                <CheckCircle2 size={13} className="stroke-[2.5]" />
              </div>
            )}
            {t.type === "error" && (
              <div className="w-5 h-5 rounded-full bg-rose-100 text-rose-600 flex items-center justify-center shrink-0">
                <AlertCircle size={13} className="stroke-[2.5]" />
              </div>
            )}
            {t.type === "info" && (
              <div className="w-5 h-5 rounded-full bg-indigo-100 text-indigo-600 flex items-center justify-center shrink-0">
                <Info size={13} className="stroke-[2.5]" />
              </div>
            )}
            <span className="flex-1 text-slate-700 leading-snug">{t.message}</span>
            <button
              onClick={() => dismiss(t.id)}
              className="text-slate-400 hover:text-slate-600 p-0.5 rounded-md hover:bg-slate-100 transition-colors shrink-0 cursor-pointer"
            >
              <X size={13} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    return {
      show: (msg: string) => externalToast?.show(msg),
      success: (msg: string) => externalToast?.success(msg),
      error: (msg: string) => externalToast?.error(msg),
      info: (msg: string) => externalToast?.info(msg),
    };
  }
  return ctx;
}

export const toast = {
  show: (msg: string, type?: ToastType) => externalToast?.show(msg, type),
  success: (msg: string) => externalToast?.success(msg),
  error: (msg: string) => externalToast?.error(msg),
  info: (msg: string) => externalToast?.info(msg),
};
