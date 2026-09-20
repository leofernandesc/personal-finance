import type {
  Account,
  Budget,
  Category,
  DashboardData,
  Goal,
  ReportData,
  SourceType,
  Transaction,
  TransactionSort,
  TransactionType,
  Transfer,
  User,
  WhatsAppIdentity,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    let detail: unknown;
    try {
      detail = await response.json();
    } catch {
      detail = undefined;
    }
    const detailObject = detail as { detail?: unknown } | undefined;
    const nested = detailObject?.detail;
    const message = typeof nested === "string" ? nested : "Não foi possível concluir a operação.";
    throw new ApiError(response.status, message, nested);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  me: () => request<User>("/auth/me"),
  login: (body: { email: string; password: string }) => request<{ user: User }>("/auth/login", json("POST", body)),
  register: (body: { email: string; password: string; full_name: string; timezone: string }) =>
    request<{ user: User }>("/auth/register", json("POST", body)),
  logout: () => request<{ message: string }>("/auth/logout", json("POST")),
  dashboard: (start?: string, end?: string) =>
    request<DashboardData>(`/dashboard${start || end ? `?${new URLSearchParams({ ...(start ? { start } : {}), ...(end ? { end } : {}) })}` : ""}`),
  report: (month?: string, months = 6) => {
    const search = new URLSearchParams({ months: String(months) });
    if (month) search.set("month", month);
    return request<ReportData>(`/reports/monthly?${search}`);
  },
  accounts: () => request<Account[]>("/accounts"),
  createAccount: (body: { name: string; account_type: string; opening_balance: string }) =>
    request<Account>("/accounts", json("POST", body)),
  updateAccount: (id: string, body: Partial<{ name: string; account_type: string; is_active: boolean }>) =>
    request<Account>(`/accounts/${id}`, json("PATCH", body)),
  categories: () => request<Category[]>("/categories"),
  createCategory: (body: { name: string; kind: string; parent_id?: string | null }) =>
    request<Category>("/categories", json("POST", body)),
  updateCategory: (id: string, body: Partial<{ name: string; kind: string; parent_id: string | null; is_active: boolean }>) =>
    request<Category>(`/categories/${id}`, json("PATCH", body)),
  transactions: (params: { start?: string; end?: string; type?: TransactionType; account_id?: string; category_id?: string; source?: SourceType; search?: string; sort?: TransactionSort } = {}) => {
    const search = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => value && search.set(key, value));
    return request<Transaction[]>(`/transactions${search.size ? `?${search}` : ""}`);
  },
  createTransaction: (body: {
    account_id: string;
    category_id?: string | null;
    type: "income" | "expense";
    amount: string;
    description: string;
    transaction_date?: string;
    idempotency_key?: string;
  }) => request<Transaction>("/transactions", json("POST", body)),
  updateTransaction: (id: string, body: Partial<{ account_id: string; category_id: string | null; amount: string; description: string; transaction_date: string }>) =>
    request<Transaction>(`/transactions/${id}`, json("PATCH", body)),
  deleteTransaction: (id: string) => request<{ message: string }>(`/transactions/${id}`, json("DELETE")),
  transfers: () => request<Transfer[]>("/transfers"),
  createTransfer: (body: { source_account_id: string; destination_account_id: string; amount: string; description: string; transaction_date?: string; idempotency_key?: string }) =>
    request<Transfer>("/transfers", json("POST", body)),
  budgets: (month?: string) => request<Budget[]>(`/budgets${month ? `?month=${month}` : ""}`),
  createBudget: (body: { category_id: string; month: string; limit_amount: string }) =>
    request<Budget>("/budgets", json("POST", body)),
  updateBudget: (id: string, body: { limit_amount: string }) => request<Budget>(`/budgets/${id}`, json("PATCH", body)),
  goals: () => request<Goal[]>("/goals"),
  createGoal: (body: { name: string; target_amount: string; current_amount: string; deadline?: string | null }) =>
    request<Goal>("/goals", json("POST", body)),
  updateGoal: (id: string, body: Partial<{ name: string; target_amount: string; current_amount: string; deadline: string | null; status: string }>) =>
    request<Goal>(`/goals/${id}`, json("PATCH", body)),
  archiveGoal: (id: string) => request<{ message: string }>(`/goals/${id}`, json("DELETE")),
  whatsappIdentity: () => request<WhatsAppIdentity>("/integrations/whatsapp/identity"),
  linkWhatsApp: (phone_e164: string) => request<WhatsAppIdentity>("/integrations/whatsapp/link", json("POST", { phone_e164 })),
  unlinkWhatsApp: () => request<{ linked: false }>("/integrations/whatsapp/link", json("DELETE")),
};
