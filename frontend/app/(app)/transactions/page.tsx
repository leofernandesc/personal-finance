"use client";

import { useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import {
  ArrowDownLeft,
  ArrowLeftRight,
  ArrowUpRight,
  Edit3,
  Filter,
  Plus,
  Search,
  Trash2,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { TransactionEditor } from "@/components/transaction-editor";
import { TransferEditor } from "@/components/transfer-editor";
import { EmptyState, ErrorState, LoadingState, PageHeader, SearchEmpty } from "@/components/page";
import { TransactionSource } from "@/components/transaction-list";
import { Button, Card, Input, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type {
  Account,
  Category,
  SourceType,
  Transaction,
  TransactionSort,
  TransactionType,
  Transfer,
} from "@/lib/types";
import { formatLongDate, money } from "@/lib/utils";

type Filters = {
  search: string;
  start: string;
  end: string;
  type: "" | TransactionType;
  account_id: string;
  category_id: string;
  source: "" | SourceType;
  sort: TransactionSort;
};

const emptyFilters: Filters = {
  search: "",
  start: "",
  end: "",
  type: "",
  account_id: "",
  category_id: "",
  source: "",
  sort: "date_desc",
};

export default function TransactionsPage() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [transfers, setTransfers] = useState<Transfer[]>([]);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [draftFilters, setDraftFilters] = useState<Filters>(emptyFilters);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadMoreError, setLoadMoreError] = useState<string | null>(null);
  const [editorMode, setEditorMode] = useState<"transaction" | "transfer" | null>(
    searchParams.get("new") === "1" ? "transaction" : null,
  );
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [editingTransfer, setEditingTransfer] = useState<Transfer | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setLoadMoreError(null);
    setNextCursor(null);
    try {
      const [transactionPage, accountItems, categoryItems, transferItems] = await Promise.all([
        api.transactions({
          search: filters.search || undefined,
          start: filters.start || undefined,
          end: filters.end || undefined,
          type: filters.type || undefined,
          account_id: filters.account_id || undefined,
          category_id: filters.category_id || undefined,
          source: filters.source || undefined,
          sort: filters.sort,
        }),
        api.accounts(),
        api.categories(),
        api.transfers(),
      ]);
      setTransactions(transactionPage.data);
      setAccounts(accountItems);
      setCategories(categoryItems);
      setTransfers(transferItems);
      setNextCursor(transactionPage.nextCursor);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível carregar as transações.");
    } finally {
      setLoading(false);
    }
  }, [filters]);

  const loadMore = async () => {
    if (!nextCursor || loadingMore) return;
    setLoadingMore(true);
    setLoadMoreError(null);
    try {
      const page = await api.transactions({
        search: filters.search || undefined,
        start: filters.start || undefined,
        end: filters.end || undefined,
        type: filters.type || undefined,
        account_id: filters.account_id || undefined,
        category_id: filters.category_id || undefined,
        source: filters.source || undefined,
        sort: filters.sort,
        cursor: nextCursor,
      });
      setTransactions((current) => [...current, ...page.data]);
      setNextCursor(page.nextCursor);
    } catch (reason) {
      setLoadMoreError(reason instanceof Error ? reason.message : "Não foi possível carregar mais movimentos.");
    } finally {
      setLoadingMore(false);
    }
  };

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    if (searchParams.get("new") === "1") setEditorMode("transaction");
  }, [searchParams]);

  const remove = async (transaction: Transaction) => {
    const label = transaction.type === "transfer"
      ? "Excluir esta transferência e suas duas movimentações?"
      : `Excluir “${transaction.description}”?`;
    if (!window.confirm(`${label} Essa ação não pode ser desfeita pela interface.`)) return;
    try {
      await api.deleteTransaction(transaction.id);
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível excluir.");
    }
  };

  const applyFilters = () => {
    if (draftFilters.start && draftFilters.end && draftFilters.start > draftFilters.end) {
      setError("A data inicial deve ser anterior à data final.");
      return;
    }
    setFilters(draftFilters);
  };

  const clearFilters = () => {
    setDraftFilters(emptyFilters);
    setFilters(emptyFilters);
  };

  const closeEditor = () => {
    setEditorMode(null);
    setEditing(null);
    setEditingTransfer(null);
  };
  const hasFilters = Object.entries(filters).some(
    ([key, value]) => key !== "sort" && Boolean(value),
  );
  const editMovement = (transaction: Transaction) => {
    if (transaction.type === "transfer") {
      const transfer = transfers.find((item) => item.id === transaction.transfer_id);
      if (!transfer) {
        setError("Não foi possível carregar os detalhes dessa transferência.");
        return;
      }
      setEditing(null);
      setEditingTransfer(transfer);
      setEditorMode("transfer");
      return;
    }
    setEditingTransfer(null);
    setEditing(transaction);
    setEditorMode("transaction");
  };

  return (
    <>
      <PageHeader
        eyebrow="Histórico completo"
        title="Transações"
        description="Tudo o que entrou, saiu ou mudou de conta, com contexto suficiente para entender o mês."
        action={(
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <Button className="w-full sm:w-auto" variant="secondary" onClick={() => { setEditing(null); setEditingTransfer(null); setEditorMode("transfer"); }}>
              <ArrowLeftRight size={16} /> Transferir
            </Button>
            <Button className="w-full sm:w-auto" onClick={() => { setEditing(null); setEditingTransfer(null); setEditorMode("transaction"); }}>
              <Plus size={17} /> Nova transação
            </Button>
          </div>
        )}
      />

      {editorMode === "transaction" && (
        <div className="mb-6">
          <TransactionEditor
            key={editing?.id ?? "new-transaction"}
            accounts={accounts}
            categories={categories}
            transaction={editing}
            timezone={user?.timezone}
            onCancel={closeEditor}
            onSaved={() => { closeEditor(); void load(); }}
          />
        </div>
      )}
      {editorMode === "transfer" && (
        <div className="mb-6">
          <TransferEditor
            key={editingTransfer?.id ?? "new-transfer"}
            accounts={accounts}
            transfer={editingTransfer}
            timezone={user?.timezone}
            onCancel={closeEditor}
            onSaved={() => { closeEditor(); void load(); }}
          />
        </div>
      )}

      <Card className="mb-5 p-4 md:p-5">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <div className="md:col-span-2">
            <label className="label" htmlFor="search">Pesquisar</label>
            <div className="relative">
              <Search size={16} className="pointer-events-none absolute left-3 top-3.5 text-muted" />
              <Input id="search" value={draftFilters.search} onChange={(event) => setDraftFilters({ ...draftFilters, search: event.target.value })} onKeyDown={(event) => { if (event.key === "Enter") applyFilters(); }} placeholder="Descrição da transação" className="pl-9" />
            </div>
          </div>
          <FilterSelect label="Tipo" id="type" value={draftFilters.type} onChange={(value) => setDraftFilters({ ...draftFilters, type: value as Filters["type"] })}>
            <option value="">Todos os tipos</option><option value="expense">Despesas</option><option value="income">Receitas</option><option value="transfer">Transferências</option>
          </FilterSelect>
          <FilterSelect label="Origem" id="source" value={draftFilters.source} onChange={(value) => setDraftFilters({ ...draftFilters, source: value as Filters["source"] })}>
            <option value="">Todas as origens</option><option value="web">Web</option><option value="whatsapp">WhatsApp</option><option value="import">Importação</option><option value="automatic">Automático</option>
          </FilterSelect>
          <FilterSelect label="Conta" id="account" value={draftFilters.account_id} onChange={(value) => setDraftFilters({ ...draftFilters, account_id: value })}>
            <option value="">Todas as contas</option>{accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
          </FilterSelect>
          <FilterSelect label="Categoria" id="category" value={draftFilters.category_id} onChange={(value) => setDraftFilters({ ...draftFilters, category_id: value })}>
            <option value="">Todas as categorias</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
          </FilterSelect>
          <div><label className="label" htmlFor="start">De</label><Input id="start" type="date" value={draftFilters.start} onChange={(event) => setDraftFilters({ ...draftFilters, start: event.target.value })} /></div>
          <div><label className="label" htmlFor="end">Até</label><Input id="end" type="date" value={draftFilters.end} onChange={(event) => setDraftFilters({ ...draftFilters, end: event.target.value })} /></div>
          <FilterSelect label="Ordenar" id="sort" value={draftFilters.sort} onChange={(value) => setDraftFilters({ ...draftFilters, sort: value as TransactionSort })}>
            <option value="date_desc">Mais recentes</option><option value="date_asc">Mais antigas</option><option value="amount_desc">Maior valor</option><option value="amount_asc">Menor valor</option>
          </FilterSelect>
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end md:col-span-2 xl:col-span-3">
            <Button className="w-full sm:w-auto" variant="secondary" onClick={applyFilters}><Filter size={15} /> Aplicar filtros</Button><Button className="w-full sm:w-auto" variant="quiet" onClick={clearFilters}>Limpar</Button>
          </div>
        </div>
      </Card>

      {loading ? <LoadingState label="Buscando movimentos" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : !transactions.length ? (
        <Card>{hasFilters ? <SearchEmpty /> : <EmptyState title="Ainda não existem transações" description="Registre o primeiro movimento por aqui ou envie uma mensagem pelo WhatsApp." actionLabel="Registrar primeira" onAction={() => setEditorMode("transaction")} />}</Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="hidden grid-cols-[minmax(240px,1fr)_190px_125px_115px_140px] gap-4 border-b border-line bg-paper/50 px-5 py-3 text-[0.65rem] font-semibold uppercase tracking-[0.13em] text-muted md:grid md:px-6"><span>Movimento</span><span>Conta</span><span>Data</span><span>Origem</span><span className="text-right">Valor</span></div>
          <div className="divide-y divide-line">{transactions.map((transaction) => <TransactionRow key={transaction.id} transaction={transaction} onEdit={() => editMovement(transaction)} onDelete={() => void remove(transaction)} />)}</div>
        </Card>
      )}
      {nextCursor && !loading && !error && (
        <div className="mt-5 flex flex-col items-center gap-2">
          {loadMoreError && <p role="alert" className="text-center text-sm text-rust">{loadMoreError}</p>}
          <Button variant="secondary" onClick={() => void loadMore()} disabled={loadingMore}>
            {loadingMore ? <Spinner /> : null}
            {loadingMore ? "Carregando…" : loadMoreError ? "Tentar carregar novamente" : "Carregar mais movimentos"}
          </Button>
        </div>
      )}
      <p className="mt-4 text-xs text-muted">{user?.timezone} · {transactions.length} movimento{transactions.length === 1 ? "" : "s"} exibido{transactions.length === 1 ? "" : "s"}</p>
    </>
  );
}

function FilterSelect({ label, id, value, onChange, children }: { label: string; id: string; value: string; onChange: (value: string) => void; children: React.ReactNode }) {
  return <div><label className="label" htmlFor={id}>{label}</label><Select id={id} value={value} onChange={(event) => onChange(event.target.value)}>{children}</Select></div>;
}

function TransactionRow({ transaction, onEdit, onDelete }: { transaction: Transaction; onEdit?: () => void; onDelete: () => void }) {
  const isIncome = transaction.type === "income";
  const isTransfer = transaction.type === "transfer";
  const accountLabel = isTransfer
    ? `${transaction.transfer_source_account_name || transaction.account_name || "Origem"} → ${transaction.transfer_destination_account_name || "Destino"}`
    : transaction.account_name || "Conta";
  return <div className="group grid gap-3 px-5 py-4 md:grid-cols-[minmax(240px,1fr)_190px_125px_115px_140px] md:items-center md:gap-4 md:px-6"><div className="flex min-w-0 items-center gap-3"><span className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-xl ${isIncome ? "bg-mint/60 text-moss" : isTransfer ? "bg-butter/70 text-[#796b1b]" : "bg-rust/10 text-rust"}`}>{isIncome ? <ArrowDownLeft size={16} /> : isTransfer ? <ArrowLeftRight size={16} /> : <ArrowUpRight size={16} />}</span><div className="min-w-0"><p className="truncate text-sm font-semibold text-ink">{transaction.description || "Sem descrição"}</p><p className="mt-0.5 truncate text-xs text-muted">{transaction.category_name || (isTransfer ? "Transferência entre contas" : "Sem categoria")}</p></div></div><p className="break-words pl-12 text-xs text-muted md:pl-0"><span className="mr-1 uppercase tracking-[0.08em] text-[0.6rem] text-muted/70 md:hidden">Conta</span>{accountLabel}</p><p className="pl-12 text-xs text-muted md:pl-0"><span className="mr-1 uppercase tracking-[0.08em] text-[0.6rem] text-muted/70 md:hidden">Data</span>{formatLongDate(transaction.transaction_date)}</p><div className="pl-12 md:pl-0"><span className="mr-1 uppercase tracking-[0.08em] text-[0.6rem] text-muted/70 md:hidden">Origem</span><TransactionSource source={transaction.source} /></div><div className="flex items-center justify-between gap-3 pl-12 md:justify-end md:pl-0"><div className="text-right"><p className={`text-sm font-semibold ${isIncome ? "text-moss" : isTransfer ? "text-muted" : "text-ink"}`}>{isIncome ? "+" : isTransfer ? "" : "−"}{money(transaction.amount)}</p>{isTransfer && <p className="text-[0.65rem] text-muted">sem impacto patrimonial</p>}</div><div className="flex gap-1 opacity-100 md:opacity-0 md:transition-opacity md:group-hover:opacity-100 md:group-focus-within:opacity-100">{onEdit && <button onClick={onEdit} className="rounded-lg p-1.5 text-muted hover:bg-paper hover:text-navy" aria-label={isTransfer ? "Editar transferência" : "Editar transação"}><Edit3 size={15} /></button>}<button onClick={onDelete} className="rounded-lg p-1.5 text-muted hover:bg-rust/10 hover:text-rust" aria-label={isTransfer ? "Excluir transferência" : "Excluir transação"}><Trash2 size={15} /></button></div></div></div>;
}
