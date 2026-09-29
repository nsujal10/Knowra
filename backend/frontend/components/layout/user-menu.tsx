"use client";

import React, { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { useSession } from "@/lib/auth/session";
import {
  User,
  Shield,
  Settings,
  LogOut,
  ChevronDown,
  Layers,
  Sparkles,
  Command,
} from "lucide-react";

interface UserMenuProps {
  onOpenCommandPalette?: () => void;
}

export function UserMenu({ onOpenCommandPalette }: UserMenuProps) {
  const [isOpen, setIsOpen] = useState(false);
  const { session, logout } = useSession();
  const menuRef = useRef<HTMLDivElement>(null);

  const fullName = session?.user?.full_name || "Sujal Nage";
  const email = session?.user?.email || "sujal.nage@softude.com";
  const role = session?.user?.role_code || "ADMIN";

  // Initials
  const initials = fullName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) || "SN";

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen]);

  return (
    <div className="relative" ref={menuRef}>
      {/* Trigger Pill */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={`flex items-center gap-2 p-1 pl-1.5 pr-2.5 rounded-full border transition-all cursor-pointer ${
          isOpen
            ? "border-indigo-300 bg-indigo-50/50 shadow-xs"
            : "border-slate-200/80 bg-white hover:border-slate-300 hover:bg-slate-50"
        }`}
        aria-label="User profile menu"
      >
        <div className="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-600 via-indigo-700 to-purple-600 flex items-center justify-center text-white text-[11px] font-bold shadow-xs">
          {initials}
        </div>
        <div className="hidden md:flex flex-col text-left">
          <span className="text-xs font-semibold text-slate-800 leading-tight">
            {fullName.split(" ")[0]}
          </span>
        </div>
        <ChevronDown size={12} className="text-slate-400" />
      </button>

      {/* Dropdown Popover */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-64 bg-white rounded-2xl shadow-xl border border-slate-200/90 overflow-hidden z-50 animate-in fade-in zoom-in-95 duration-100">
          {/* Header with User Info */}
          <div className="p-3.5 border-b border-slate-100 bg-slate-50/70">
            <div className="flex items-center gap-2.5">
              <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-600 via-indigo-700 to-purple-600 flex items-center justify-center text-white text-xs font-bold shadow-xs">
                {initials}
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-bold text-slate-900 truncate">
                  {fullName}
                </p>
                <p className="text-[11px] text-slate-400 truncate">
                  {email}
                </p>
              </div>
            </div>
            <div className="mt-2.5 flex items-center justify-between">
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                {role}
              </span>
              <span className="text-[10px] text-slate-400 font-mono">
                {session?.tenantId ? `Tenant #${session.tenantId.slice(0, 6)}` : "Knowra Prod"}
              </span>
            </div>
          </div>

          {/* Quick Links */}
          <div className="p-1.5 divide-y divide-slate-50 text-xs">
            <div className="py-1">
              {onOpenCommandPalette && (
                <button
                  onClick={() => {
                    setIsOpen(false);
                    onOpenCommandPalette();
                  }}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors text-left cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <Command size={14} className="text-slate-400" />
                    <span>Command Palette</span>
                  </div>
                  <kbd className="px-1.5 py-0.5 text-[9px] font-mono bg-slate-100 border border-slate-200 rounded text-slate-500">
                    ⌘K
                  </kbd>
                </button>
              )}
              <Link
                href="/settings"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
              >
                <Settings size={14} className="text-slate-400" />
                <span>Workspace Settings</span>
              </Link>
              <Link
                href="/integrations"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
              >
                <Layers size={14} className="text-slate-400" />
                <span>Integrations & Webhooks</span>
              </Link>
            </div>

            <div className="py-1">
              <Link
                href="/evaluation"
                onClick={() => setIsOpen(false)}
                className="flex items-center gap-2 px-3 py-2 rounded-lg text-slate-700 hover:bg-slate-50 hover:text-slate-900 transition-colors"
              >
                <Shield size={14} className="text-slate-400" />
                <span>Governance & RBAC</span>
              </Link>
            </div>

            <div className="pt-1">
              <button
                onClick={() => {
                  setIsOpen(false);
                  logout();
                }}
                className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-rose-600 hover:bg-rose-50 transition-colors text-left cursor-pointer font-medium"
              >
                <LogOut size={14} />
                <span>Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
