"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Check, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Account, Category, Transaction } from "@/lib/types";
import { Button, Input, Select, Spinner } from "@/components/ui";

export function TransactionEditor({ accounts, categories, transaction, onSaved, onCancel }: { accounts: Account[]; categories: Category[]; transaction?: Transaction | null; onSaved: () => void; onCancel: () => void }) {
  const [type, setType] = useState<"expense" | "income">(transaction?.type === "income" ? "income" : "expense");
  const [accountId, setAccountId] = useState(transaction?.account_id || accounts[0]?.id || "");
  const [categoryId, setCategoryId] = useState(transaction?.category_id || "");
  const [amount, setAmount] = useState(transaction?.amount || "");
  const [description, setDescription] = useState(transaction?.description || "");
  const [transactionDate, setTransactionDate] = useState(transaction?.transaction_date || new Date().toISOString().slice(0, 10));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const availableCategories = useMemo(() => categories.filter((category) => category.is_active && (category.kind === type || category.kind === "both")), [categories, type]);

  useEffect(() => {
    if (categoryId && !availableCategories.some((category) => category.id === categoryId)) setCategoryId("");
  }, [availableCategories, categoryId, type]);

  const submit = async () => {
    setSaving(true); setError(null);
    try {
      if (!accountId || !amount || Number(amount.replace(",", ".")) <= 0) throw new Error("Informe conta e valor maior que zero.");
      const normalizedAmount = amount.replace(/\./g, "").replace(",", ".");
      const payload = { account_id: accountId, category_id: categoryId || null, type, amount: normalizedAmount, description: description || (type === "income" ? "Receita" : "Despesa"), transaction_date: transactionDate, source: transaction?.source || "web" as const };
      if (transaction) await api.updateTransaction(transaction.id, payload);
      else await api.createTransaction(payload);
      onSaved();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível salvar."); } finally { setSaving(false); }
  };

  return <div className="rounded-card border border-navy/15 bg-[#fbfcfa] p-5 shadow-card md:p-6"><div className="mb-5 flex items-start justify-between"><div><p className="eyebrow">{transaction ? "Editar movimento" : "Novo movimento"}</p><h2 className="mt-1 font-display text-2xl tracking-[-0.03em]">Registre com contexto.</h2></div><button onClick={onCancel} className="rounded-lg p-2 text-muted hover:bg-paper" aria-label="Fechar formulário"><X size={18} /></button></div><div className="mb-5 grid grid-cols-2 gap-2 rounded-xl bg-paper p-1"><button type="button" className={`flex h-10 items-center justify-center gap-2 rounded-lg text-sm font-semibold transition ${type === "expense" ? "bg-white text-rust shadow-sm" : "text-muted"}`} onClick={() => setType("expense")}><ArrowUpRight size={15} /> Despesa</button><button type="button" className={`flex h-10 items-center justify-center gap-2 rounded-lg text-sm font-semibold transition ${type === "income" ? "bg-white text-moss shadow-sm" : "text-muted"}`} onClick={() => setType("income")}><ArrowDownLeft size={15} /> Receita</button></div><div className="grid gap-4 md:grid-cols-2"><div><label className="label" htmlFor="transaction-description">Descrição</label><Input id="transaction-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder={type === "expense" ? "Ex.: almoço, gasolina…" : "Ex.: salário, cliente…"} /></div><div><label className="label" htmlFor="transaction-amount">Valor</label><div className="relative"><span className="absolute left-3 top-3 text-sm text-muted">R$</span><Input id="transaction-amount" inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="0,00" className="pl-10" /></div></div><div><label className="label" htmlFor="transaction-account">Conta</label><Select id="transaction-account" value={accountId} onChange={(event) => setAccountId(event.target.value)}><option value="">Selecione uma conta</option>{accounts.filter((account) => account.is_active).map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</Select></div><div><label className="label" htmlFor="transaction-category">Categoria <span className="normal-case tracking-normal text-muted/70">(opcional)</span></label><Select id="transaction-category" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">Outros / sem categoria</option>{availableCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select></div><div><label className="label" htmlFor="transaction-date">Data</label><Input id="transaction-date" type="date" value={transactionDate} onChange={(event) => setTransactionDate(event.target.value)} /></div></div>{error && <p role="alert" className="mt-4 rounded-xl border border-rust/20 bg-rust/5 px-3 py-2.5 text-sm text-rust">{error}</p>}<div className="mt-6 flex justify-end gap-2"><Button type="button" variant="quiet" onClick={onCancel}>Cancelar</Button><Button type="button" onClick={() => void submit()} disabled={saving}>{saving ? <Spinner /> : <Check size={16} />} {saving ? "Salvando…" : transaction ? "Salvar alterações" : "Registrar movimento"}</Button></div></div>;
}
