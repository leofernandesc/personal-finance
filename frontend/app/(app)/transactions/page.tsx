"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { ArrowDownLeft, ArrowLeftRight, ArrowUpRight, Edit3, Filter, Plus, Search, Trash2 } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { TransactionEditor } from "@/components/transaction-editor";
import { EmptyState, ErrorState, LoadingState, PageHeader, SearchEmpty } from "@/components/page";
import { TransactionSource } from "@/components/transaction-list";
import { Badge, Button, Card, Input, Select } from "@/components/ui";
import { api } from "@/lib/api";
import type { Account, Category, SourceType, Transaction, TransactionType } from "@/lib/types";
import { formatLongDate, money } from "@/lib/utils";

type Filters = { search: string; type: "" | TransactionType; source: "" | SourceType };

export default function TransactionsPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filters, setFilters] = useState<Filters>({ search: "", type: "", source: "" });
  const [draftFilters, setDraftFilters] = useState<Filters>(filters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(searchParams.get("new") === "1");
  const [editing, setEditing] = useState<Transaction | null>(null);

  const load = useCallback(async (currentFilters = filters) => {
    setLoading(true); setError(null);
    try {
      const [items, accountItems, categoryItems] = await Promise.all([api.transactions({ search: currentFilters.search || undefined, type: currentFilters.type || undefined, source: currentFilters.source || undefined }), api.accounts(), api.categories()]);
      setTransactions(items); setAccounts(accountItems); setCategories(categoryItems);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar as transações."); } finally { setLoading(false); }
  }, [filters]);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { if (searchParams.get("new") === "1") setEditorOpen(true); }, [searchParams]);

  const remove = async (transaction: Transaction) => {
    if (!window.confirm(`Excluir “${transaction.description}”? Essa ação pode ser desfeita apenas por restauração direta do banco.`)) return;
    try { await api.deleteTransaction(transaction.id); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível excluir."); }
  };

  const applyFilters = () => { setFilters(draftFilters); };
  const clearFilters = () => { const empty: Filters = { search: "", type: "", source: "" }; setDraftFilters(empty); setFilters(empty); };

  return <>
    <PageHeader eyebrow="Histórico completo" title="Transações" description="Tudo o que entrou e saiu, com contexto suficiente para você entender o mês." action={<Button onClick={() => { setEditing(null); setEditorOpen(true); }}><Plus size={17} /> Nova transação</Button>} />
    {editorOpen && <div className="mb-6"><TransactionEditor accounts={accounts} categories={categories} transaction={editing} onCancel={() => { setEditorOpen(false); setEditing(null); }} onSaved={() => { setEditorOpen(false); setEditing(null); void load(); }} /></div>}
    <Card className="mb-5 p-4 md:p-5"><div className="grid gap-3 md:grid-cols-[1fr_180px_180px_auto_auto] md:items-end"><div><label className="label" htmlFor="search">Pesquisar</label><div className="relative"><Search size={16} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="search" value={draftFilters.search} onChange={(event) => setDraftFilters({ ...draftFilters, search: event.target.value })} onKeyDown={(event) => { if (event.key === "Enter") applyFilters(); }} placeholder="Descrição da transação" className="pl-9" /></div></div><div><label className="label" htmlFor="type">Tipo</label><Select id="type" value={draftFilters.type} onChange={(event) => setDraftFilters({ ...draftFilters, type: event.target.value as Filters["type"] })}><option value="">Todos os tipos</option><option value="expense">Despesas</option><option value="income">Receitas</option><option value="transfer">Transferências</option></Select></div><div><label className="label" htmlFor="source">Origem</label><Select id="source" value={draftFilters.source} onChange={(event) => setDraftFilters({ ...draftFilters, source: event.target.value as Filters["source"] })}><option value="">Todas as origens</option><option value="web">Web</option><option value="whatsapp">WhatsApp</option><option value="import">Importação</option></Select></div><Button variant="secondary" onClick={applyFilters}><Filter size={15} /> Filtrar</Button><Button variant="quiet" onClick={clearFilters}>Limpar</Button></div></Card>
    {loading ? <LoadingState label="Buscando movimentos" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : !transactions.length ? <Card>{filters.search || filters.type || filters.source ? <SearchEmpty /> : <EmptyState title="Ainda não existem transações" description="Registre o primeiro movimento por aqui ou envie uma mensagem pelo WhatsApp." actionLabel="Registrar primeira" onAction={() => setEditorOpen(true)} />}</Card> : <Card className="overflow-hidden"><div className="hidden grid-cols-[minmax(240px,1fr)_160px_145px_125px_112px] gap-4 border-b border-line bg-paper/50 px-5 py-3 text-[0.65rem] font-semibold uppercase tracking-[0.13em] text-muted md:grid md:px-6"><span>Movimento</span><span>Conta</span><span>Data</span><span>Origem</span><span className="text-right">Valor</span></div><div className="divide-y divide-line">{transactions.map((transaction) => <TransactionRow key={transaction.id} transaction={transaction} onEdit={() => { setEditing(transaction); setEditorOpen(true); }} onDelete={() => void remove(transaction)} />)}</div></Card>}
    <p className="mt-4 text-xs text-muted">{user?.timezone} · {transactions.length} movimento{transactions.length === 1 ? "" : "s"} exibido{transactions.length === 1 ? "" : "s"}</p>
  </>;
}

function TransactionRow({ transaction, onEdit, onDelete }: { transaction: Transaction; onEdit: () => void; onDelete: () => void }) {
  const isIncome = transaction.type === "income";
  const isTransfer = transaction.type === "transfer";
  return <div className="group grid gap-3 px-5 py-4 md:grid-cols-[minmax(240px,1fr)_160px_145px_125px_112px] md:items-center md:gap-4 md:px-6"><div className="flex min-w-0 items-center gap-3"><span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${isIncome ? "bg-mint/60 text-moss" : isTransfer ? "bg-butter/70 text-[#796b1b]" : "bg-rust/10 text-rust"}`}>{isIncome ? <ArrowDownLeft size={16} /> : isTransfer ? <ArrowLeftRight size={16} /> : <ArrowUpRight size={16} />}</span><div className="min-w-0"><p className="truncate text-sm font-semibold text-ink">{transaction.description || "Sem descrição"}</p><p className="mt-0.5 truncate text-xs text-muted">{transaction.category_name || (isTransfer ? "Transferência" : "Sem categoria")}</p></div></div><p className="pl-12 text-xs text-muted md:pl-0">{transaction.account_name || "Conta"}</p><p className="pl-12 text-xs text-muted md:pl-0">{formatLongDate(transaction.transaction_date)}</p><div className="flex items-center justify-between pl-12 md:pl-0"><TransactionSource source={transaction.source} /><span className="text-xs text-muted md:hidden">{formatLongDate(transaction.transaction_date)}</span></div><div className="flex items-center justify-between gap-3 pl-12 md:justify-end md:pl-0"><p className={`text-sm font-semibold ${isIncome ? "text-moss" : isTransfer ? "text-muted" : "text-ink"}`}>{isIncome ? "+" : isTransfer ? "" : "−"}{money(transaction.amount)}</p><div className="flex gap-1 opacity-100 md:opacity-0 md:transition-opacity md:group-hover:opacity-100"><button onClick={onEdit} className="rounded-lg p-1.5 text-muted hover:bg-paper hover:text-navy" aria-label="Editar transação"><Edit3 size={15} /></button><button onClick={onDelete} className="rounded-lg p-1.5 text-muted hover:bg-rust/10 hover:text-rust" aria-label="Excluir transação"><Trash2 size={15} /></button></div></div></div>;
}
