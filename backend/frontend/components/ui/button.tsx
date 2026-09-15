"use client";

import { cn } from "@/lib/utils";
import { type VariantProps, cva } from "class-variance-authority";
import React from "react";

const buttonVariants = cva(
  [
    "inline-flex items-center justify-center gap-2 font-medium",
    "rounded-[var(--radius-sm)] border transition-all duration-200",
    "cursor-pointer select-none whitespace-nowrap",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--primary)]",
    "disabled:opacity-40 disabled:pointer-events-none",
  ].join(" "),
  {
    variants: {
      variant: {
        primary: [
          "bg-[var(--primary)] border-transparent text-white",
          "hover:bg-[var(--primary-hover)] active:scale-[0.98]",
          "shadow-[0_0_16px_rgba(79,124,255,0.25)]",
        ].join(" "),
        secondary: [
          "bg-[var(--surface-2)] border-[var(--border)] text-[var(--foreground)]",
          "hover:bg-[var(--surface-3)] hover:border-[var(--border-strong)]",
        ].join(" "),
        ghost: [
          "bg-transparent border-transparent text-[var(--muted-strong)]",
          "hover:bg-[var(--surface-2)] hover:text-[var(--foreground)]",
        ].join(" "),
        danger: [
          "bg-[var(--danger-muted)] border-[var(--danger)] text-[var(--danger)]",
          "hover:bg-[var(--danger)] hover:text-white",
        ].join(" "),
        outline: [
          "bg-transparent border-[var(--border-strong)] text-[var(--foreground)]",
          "hover:bg-[var(--surface-2)]",
        ].join(" "),
      },
      size: {
        sm: "h-7 px-3 text-xs",
        md: "h-9 px-4 text-sm",
        lg: "h-11 px-6 text-base",
        icon: "h-8 w-8 p-0",
      },
    },
    defaultVariants: {
      variant: "primary",
      size: "md",
    },
  }
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  isLoading?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, isLoading, children, ...props }, ref) => (
    <button
      ref={ref}
      className={cn(buttonVariants({ variant, size }), className)}
      disabled={props.disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <span
          className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent animate-spinner"
          aria-hidden
        />
      )}
      {children}
    </button>
  )
);
Button.displayName = "Button";
