import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, format } from "date-fns";

/** Merge Tailwind class names safely */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

/** Format ISO timestamp as relative time ("3 hours ago") */
export function relativeTime(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

/** Format ISO timestamp as "Sep 15, 2026 4:22 PM" */
export function formatDate(iso: string): string {
  return format(new Date(iso), "MMM d, yyyy h:mm a");
}

/** Format seconds as MM:SS or HH:MM:SS */
export function formatDuration(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0)
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** Format a number as USD cost string */
export function formatCost(usd: number): string {
  if (usd < 0.001) return `$${(usd * 1000).toFixed(3)}m`;
  return `$${usd.toFixed(4)}`;
}

/** Format a percentage metric 0-1 as "XX.X%" */
export function formatMetric(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(value * 100).toFixed(1)}%`;
}

/** Get a semantic color class for a metric score (higher = better) */
export function metricColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-muted";
  if (value >= 0.85) return "text-emerald-400";
  if (value >= 0.65) return "text-amber-400";
  return "text-red-400";
}

/** Truncate a string to maxLen with ellipsis */
export function truncate(str: string, maxLen: number): string {
  if (str.length <= maxLen) return str;
  return str.slice(0, maxLen - 1) + "…";
}

/** Build color for speaker label (deterministic from label string) */
const SPEAKER_COLORS = [
  "#60a5fa", // blue-400
  "#a78bfa", // violet-400
  "#34d399", // emerald-400
  "#fb923c", // orange-400
  "#f472b6", // pink-400
  "#38bdf8", // sky-400
  "#facc15", // yellow-400
  "#4ade80", // green-400
];

export function speakerColor(label: string): string {
  let hash = 0;
  for (let i = 0; i < label.length; i++) {
    hash = label.charCodeAt(i) + ((hash << 5) - hash);
  }
  return SPEAKER_COLORS[Math.abs(hash) % SPEAKER_COLORS.length];
}
