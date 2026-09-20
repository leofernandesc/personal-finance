import Link from "next/link";
import { ArrowDownLeft, ArrowLeftRight, ArrowUpRight } from "lucide-react";
import { Badge } from "@/components/ui";
import type { Transaction } from "@/lib/types";
import { formatDate, money, sourceLabels } from "@/lib/utils";

function TransactionMark({ type }: { type: Transaction["type"] }) {
  if (type === "income") return <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-mint/60 text-moss"><ArrowDownLeft size={17} /></span>;
  if (type === "transfer") return <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-butter/70 text-[#796b1b]"><ArrowLeftRight size={17} /></span>;
  return <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-rust/10 text-rust"><ArrowUpRight size={17} /></span>;
}

export function TransactionList({ transactions, compact = false }: { transactions: Transaction[]; compact?: boolean }) {
  if (!transactions.length) return null;
  return <div className="divide-y divide-line">{transactions.map((transaction) => <div key={transaction.id} className="flex items-center gap-3 px-5 py-3.5 md:px-6"><TransactionMark type={transaction.type} /><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink">{transaction.description || (transaction.type === "income" ? "Receita" : "Despesa")}</p><p className="mt-0.5 truncate text-xs text-muted">{transaction.category_name || transaction.category?.name || (transaction.type === "transfer" ? "Transferência" : "Sem categoria")} <span className="px-1 text-line">·</span> {transaction.account_name || transaction.account?.name || "Conta"}</p></div><div className="hidden text-right sm:block"><p className={`text-sm font-semibold ${transaction.type === "income" ? "text-moss" : transaction.type === "expense" ? "text-ink" : "text-muted"}`}>{transaction.type === "income" ? "+" : transaction.type === "expense" ? "−" : ""}{money(transaction.amount)}</p><p className="mt-0.5 text-[0.68rem] text-muted">{formatDate(transaction.transaction_date)} {compact ? "" : `· ${sourceLabels[transaction.source] || transaction.source}`}</p></div><div className="text-right sm:hidden"><p className={`text-sm font-semibold ${transaction.type === "income" ? "text-moss" : "text-ink"}`}>{transaction.type === "income" ? "+" : transaction.type === "expense" ? "−" : ""}{money(transaction.amount)}</p><p className="mt-0.5 text-[0.68rem] text-muted">{formatDate(transaction.transaction_date)}</p></div></div>)}</div>;
}

export function TransactionSource({ source }: { source: Transaction["source"] }) {
  return <Badge tone={source === "whatsapp" ? "whatsapp" : "neutral"}>{sourceLabels[source] || source}</Badge>;
}

export function TransactionLink() {
  return <Link href="/transactions" className="text-xs font-semibold text-moss hover:text-navy">Ver todas</Link>;
}
