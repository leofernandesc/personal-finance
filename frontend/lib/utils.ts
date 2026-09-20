import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function money(value: string | number | null | undefined, withSign = false) {
  const amount = Number(value ?? 0);
  const formatted = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  }).format(Math.abs(amount));
  if (!withSign) return amount < 0 ? `-${formatted}` : formatted;
  return `${amount < 0 ? "−" : amount > 0 ? "+" : ""}${formatted}`;
}

export function numberValue(value: string | number | null | undefined) {
  return Number(value ?? 0);
}

export function formatDate(value: string | Date, options?: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat("pt-BR", options ?? { day: "2-digit", month: "short" }).format(
    new Date(`${String(value).slice(0, 10)}T12:00:00`),
  );
}

export function formatLongDate(value: string | Date) {
  return new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" }).format(
    new Date(`${String(value).slice(0, 10)}T12:00:00`),
  );
}

export function monthLabel(value: string | Date) {
  return new Intl.DateTimeFormat("pt-BR", { month: "long", year: "numeric" }).format(
    new Date(`${String(value).slice(0, 10)}T12:00:00`),
  );
}

export function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join("");
}

export function percent(value: string | number) {
  return `${Math.min(100, Math.max(0, Number(value))).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
}

export const accountTypeLabels: Record<string, string> = {
  checking: "Conta corrente",
  savings: "Poupança",
  cash: "Dinheiro",
  investment: "Investimentos",
  other: "Outra conta",
};

export const sourceLabels: Record<string, string> = {
  web: "Web",
  whatsapp: "WhatsApp",
  import: "Importação",
  automatic: "Automático",
};
