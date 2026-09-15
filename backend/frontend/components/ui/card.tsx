"use client";

import React from "react";
import { cn } from "@/lib/utils";

// ─── Card ─────────────────────────────────────────────────────────────────────
interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hoverable?: boolean;
}

export const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ className, hoverable, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "bg-[var(--surface-1)] border border-[var(--border)] rounded-[var(--radius-md)] p-5",
        hoverable &&
          "transition-all duration-200 hover:border-[var(--border-strong)] hover:bg-[var(--surface-2)] cursor-pointer",
        className
      )}
      {...props}
    />
  )
);
Card.displayName = "Card";

export const CardHeader = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div
    className={cn("flex items-start justify-between gap-3 mb-4", className)}
    {...props}
  />
);

export const CardTitle = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) => (
  <h3
    className={cn("font-semibold text-[var(--foreground)] leading-tight", className)}
    {...props}
  />
);

export const CardContent = ({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) => (
  <div className={cn("", className)} {...props} />
);

// ─── Badge ────────────────────────────────────────────────────────────────────
type BadgeVariant =
  | "default"
  | "primary"
  | "success"
  | "warning"
  | "danger"
  | "secondary";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const BADGE_STYLES: Record<BadgeVariant, string> = {
  default:
    "bg-[var(--surface-3)] text-[var(--muted-strong)] border border-[var(--border)]",
  primary:
    "bg-[var(--primary-muted)] text-[var(--primary)] border border-[rgba(79,124,255,0.2)]",
  success:
    "bg-[var(--success-muted)] text-[var(--success)] border border-[rgba(16,185,129,0.2)]",
  warning:
    "bg-[var(--warning-muted)] text-[var(--warning)] border border-[rgba(245,158,11,0.2)]",
  danger:
    "bg-[var(--danger-muted)] text-[var(--danger)] border border-[rgba(239,68,68,0.2)]",
  secondary:
    "bg-[var(--secondary-muted)] text-[var(--secondary)] border border-[rgba(124,92,252,0.2)]",
};

export const Badge = ({
  variant = "default",
  className,
  ...props
}: BadgeProps) => (
  <span
    className={cn(
      "inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider",
      "px-2 py-0.5 rounded-full",
      BADGE_STYLES[variant],
      className
    )}
    {...props}
  />
);

// ─── Input ────────────────────────────────────────────────────────────────────
interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  leftIcon?: React.ReactNode;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, leftIcon, id, ...props }, ref) => {
    const inputId = id ?? label?.toLowerCase().replace(/\s+/g, "-");
    return (
      <div className="flex flex-col gap-1.5 w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="text-xs font-medium text-[var(--muted-strong)] uppercase tracking-wider"
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--muted)]">
              {leftIcon}
            </span>
          )}
          <input
            ref={ref}
            id={inputId}
            className={cn(
              "w-full h-9 bg-[var(--surface-2)] border border-[var(--border)] rounded-[var(--radius-sm)]",
              "text-sm text-[var(--foreground)] placeholder:text-[var(--muted)]",
              "px-3 transition-all duration-200",
              "focus:outline-none focus:border-[var(--primary)] focus:bg-[var(--surface-3)]",
              "focus:ring-1 focus:ring-[var(--primary)] focus:ring-opacity-40",
              leftIcon && "pl-9",
              error && "border-[var(--danger)] focus:border-[var(--danger)]",
              className
            )}
            {...props}
          />
        </div>
        {error && (
          <p className="text-xs text-[var(--danger)]">{error}</p>
        )}
      </div>
    );
  }
);
Input.displayName = "Input";

// ─── Spinner ──────────────────────────────────────────────────────────────────
export const Spinner = ({
  size = 16,
  className,
}: {
  size?: number;
  className?: string;
}) => (
  <span
    className={cn("inline-block rounded-full border-2 border-[var(--border)] border-t-[var(--primary)] animate-spinner", className)}
    style={{ width: size, height: size }}
    aria-label="Loading"
  />
);

// ─── Empty State ──────────────────────────────────────────────────────────────
export const EmptyState = ({
  icon,
  title,
  description,
  action,
}: {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) => (
  <div className="flex flex-col items-center justify-center py-16 gap-4 text-center">
    {icon && (
      <div className="text-[var(--muted)] text-4xl">{icon}</div>
    )}
    <div>
      <p className="text-sm font-medium text-[var(--muted-strong)]">{title}</p>
      {description && (
        <p className="text-xs text-[var(--muted)] mt-1">{description}</p>
      )}
    </div>
    {action}
  </div>
);
