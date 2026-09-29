"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface PageHeaderProps {
  title: string;
  subtitle?: string;
  badge?: React.ReactNode;
  icon?: React.ComponentType<{ size?: number; className?: string }>;
  actions?: React.ReactNode;
  statusDot?: boolean;
  className?: string;
}

export function PageHeader({
  title,
  subtitle,
  badge,
  icon: Icon,
  actions,
  statusDot = false,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1",
        className
      )}
    >
      <div className="space-y-1">
        <div className="flex items-center gap-2.5 flex-wrap">
          {Icon && (
            <div className="w-8 h-8 rounded-lg bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 shrink-0 shadow-2xs">
              <Icon size={17} />
            </div>
          )}
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            {title}
          </h1>

          {statusDot && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
            </span>
          )}

          {badge && <div className="ml-1">{badge}</div>}
        </div>

        {subtitle && (
          <p className="text-xs sm:text-sm text-slate-500 max-w-3xl leading-relaxed">
            {subtitle}
          </p>
        )}
      </div>

      {actions && (
        <div className="flex items-center gap-2 shrink-0 flex-wrap">
          {actions}
        </div>
      )}
    </div>
  );
}
