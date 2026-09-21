export type AccountType = "checking" | "savings" | "cash" | "investment" | "other";
export type CategoryKind = "expense" | "income" | "both";
export type TransactionType = "income" | "expense" | "transfer";
export type SourceType = "web" | "whatsapp" | "import" | "automatic";
export type TransactionSort = "date_desc" | "date_asc" | "amount_desc" | "amount_asc";

export type User = {
  id: string;
  email: string;
  full_name: string;
  timezone: string;
};

export type DiagnosticStatus = "not_started" | "draft" | "completed";

export type DiagnosticAnswers = Record<string, unknown>;

export type Diagnostic = {
  status: DiagnosticStatus;
  current_section: number;
  completion_percent: number;
  version: number;
  answers: DiagnosticAnswers;
  consent_data_processing: boolean;
  consent_service_disclaimer: boolean;
  consent_version: string;
  consented_at: string | null;
  completed_at: string | null;
  updated_at: string | null;
};

export type DiagnosticSummarySignal = {
  level: "positive" | "attention" | "priority" | "info";
  title: string;
  description: string;
};

export type DiagnosticSummary = {
  status: "not_ready" | "completed";
  snapshot_date: string | null;
  metrics: {
    monthly_income: string | null;
    family_monthly_income: string | null;
    monthly_expenses: string | null;
    monthly_margin: string | null;
    total_debt: string | null;
    monthly_debt_installments: string | null;
    reserve_amount: string | null;
    financial_score: number | null;
  };
  signals: DiagnosticSummarySignal[];
  next_steps: Array<{ priority: number; title: string; description: string }>;
  basis: "self_reported_diagnostic" | "not_ready";
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
  transfer_source_account_name?: string | null;
  transfer_destination_account_name?: string | null;
  account?: Account;
  category?: Category;
};

export type Transfer = {
  id: string;
  source_account_id: string;
  destination_account_id: string;
  amount: string;
  description: string;
  transaction_date: string;
  source: SourceType;
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
  by_category: Array<{ category_id: string | null; category_name: string; amount: string }>;
  flow: Array<{ date: string; income: string; expense: string }>;
  budgets: Budget[];
  recent_transactions: Transaction[];
};

export type ReportData = DashboardData & {
  monthly_evolution: Array<{
    month: string;
    income: string;
    expense: string;
    savings: string;
  }>;
};

export type WhatsAppIdentity = {
  linked: boolean;
  phone_e164: string | null;
  verified: boolean;
};

export type ApiErrorShape = {
  code?: string;
  message?: string;
  available?: string[];
};
