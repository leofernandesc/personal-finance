import type { ButtonHTMLAttributes, HTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

export function Button({ className, variant = "primary", size = "default", ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "quiet" | "danger"; size?: "default" | "small" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-navy px-4 text-white shadow-sm hover:bg-navy/90",
        variant === "secondary" && "border border-line bg-white px-4 text-ink hover:border-moss hover:bg-mint/20",
        variant === "quiet" && "px-3 text-muted hover:bg-paper hover:text-ink",
        variant === "danger" && "border border-rust/20 bg-rust/5 px-4 text-rust hover:bg-rust/10",
        size === "default" ? "h-11 text-sm" : "h-9 px-3 text-xs",
        className,
      )}
      {...props}
    />
  );
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("surface", className)} {...props} />;
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-start justify-between gap-4 px-5 pb-3 pt-5 md:px-6 md:pt-6", className)} {...props} />;
}

export function CardTitle({ className, children }: { className?: string; children: ReactNode }) {
  return <h2 className={cn("font-display text-xl tracking-[-0.025em] text-ink", className)}>{children}</h2>;
}

export function CardDescription({ className, children }: { className?: string; children: ReactNode }) {
  return <p className={cn("mt-1 text-sm leading-6 text-muted", className)}>{children}</p>;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn("field", className)} {...props} />;
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn("field", className)} {...props} />;
}

export function Badge({ className, tone = "neutral", children }: { className?: string; tone?: "neutral" | "positive" | "negative" | "whatsapp" | "warning"; children: ReactNode }) {
  return (
    <span className={cn(
      "inline-flex items-center rounded-full px-2.5 py-1 text-[0.68rem] font-semibold tracking-wide",
      tone === "neutral" && "bg-paper text-muted",
      tone === "positive" && "bg-mint/60 text-moss",
      tone === "negative" && "bg-rust/10 text-rust",
      tone === "whatsapp" && "bg-[#dcf8e8] text-[#287853]",
      tone === "warning" && "bg-butter/70 text-[#796b1b]",
      className,
    )}>{children}</span>
  );
}

export function Progress({ value, tone = "moss" }: { value: number; tone?: "moss" | "rust" | "navy" }) {
  return (
    <div className="h-2 overflow-hidden rounded-full bg-paper" aria-label={`${Math.round(value)}% utilizado`} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100}>
      <div className={cn("h-full rounded-full transition-all", tone === "moss" && "bg-moss", tone === "rust" && "bg-rust", tone === "navy" && "bg-navy")} style={{ width: `${Math.min(Math.max(value, 0), 100)}%` }} />
    </div>
  );
}

export function Divider({ className }: { className?: string }) {
  return <div className={cn("border-t border-line", className)} />;
}

export function Spinner({ className }: { className?: string }) {
  return <span className={cn("inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent", className)} aria-label="Carregando" />;
}
