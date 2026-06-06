import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes with conflict resolution. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Append an alpha channel to a 6-digit hex color, e.g. alpha("#22d3ee", 0.25). */
export function alpha(hex: string, a: number): string {
  const v = Math.round(Math.max(0, Math.min(1, a)) * 255)
    .toString(16)
    .padStart(2, "0");
  return `${hex}${v}`;
}

/** Format a number with thousands separators. */
export function fmt(n: number): string {
  return new Intl.NumberFormat("en-US").format(n);
}

/** Clamp a value between min and max. */
export function clamp(v: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, v));
}
