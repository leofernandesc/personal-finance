export type AccountType = "checking" | "savings" | "cash" | "investment" | "other";
export type CategoryKind = "expense" | "income" | "both";
export type TransactionType = "income" | "expense" | "transfer";
export type SourceType = "web" | "whatsapp" | "import" | "automatic";

export type User = {
  id: string;
  email: string;
  full_name: string;
  timezone: string;
};

export type Account = {
  id: string;
  name: string;
  account_type: AccountType;
  opening_balance: string;
  is_active: boolean;
  balance: string;
};

export type Category = {
  id: string;
  name: string;
  kind: CategoryKind;
  parent_id: string | null;
  is_active: boolean;
};

export type Transaction = {
  id: string;
  account_id: string;
  category_id: string | null;
  transfer_id: string | null;
  type: TransactionType;
  transfer_leg: "in" | "out" | null;
  description: string;
  amount: string;
  transaction_date: string;
  source: SourceType;
  created_at: string;
  account_name?: string | null;
  category_name?: string | null;
  account?: Account;
  category?: Category;
};

export type Budget = {
  id: string;
  category_id: string;
  category_name: string;
  month: string;
  limit_amount: string;
  spent_amount: string;
  remaining_amount: string;
  utilization_percent: string;
  exceeded_amount: string;
};

export type Goal = {
  id: string;
  name: string;
  target_amount: string;
  current_amount: string;
  deadline: string | null;
  status: "active" | "completed" | "archived";
};

export type DashboardData = {
  period: { start: string; end: string };
  totals: { income: string; expense: string; savings: string };
  total_balance: string;
  accounts: Array<Pick<Account, "id" | "name" | "account_type" | "balance">>;
  by_category: Array<{ category_id: string; category_name: string; amount: string }>;
  flow: Array<{ date: string; income: string; expense: string }>;
  budgets: Budget[];
  recent_transactions: Transaction[];
};

export type WhatsAppIdentity = {
  linked: boolean;
  phone_e164: string | null;
};

export type ApiErrorShape = {
  code?: string;
  message?: string;
  available?: string[];
};
