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

export function normalizeMoneyInput(value: string) {
  const raw = value.trim().replace(/R\$/gi, "").replace(/\s/g, "");
  if (/^-?\d+$/.test(raw)) return raw;
  if (/^-?\d{1,3}(\.\d{3})+(,\d{1,2})?$/.test(raw)) {
    return raw.replace(/\./g, "").replace(",", ".");
  }
  if (/^-?\d{1,3}(,\d{3})+(\.\d{1,2})?$/.test(raw)) {
    return raw.replace(/,/g, "");
  }
  if (/^-?\d+[,.]\d{1,2}$/.test(raw)) return raw.replace(",", ".");
  return null;
}

export function todayForTimezone(timezone = "UTC", value = new Date()) {
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: timezone,
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    }).formatToParts(value);
    const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
    return `${values.year}-${values.month}-${values.day}`;
  } catch {
    return value.toISOString().slice(0, 10);
  }
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
  return `${Math.max(0, Number(value)).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%`;
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
