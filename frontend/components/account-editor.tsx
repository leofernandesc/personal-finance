"use client";

import { useState } from "react";
import { Check, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Account } from "@/lib/types";
import { Button, Input, Select, Spinner } from "@/components/ui";

export function AccountEditor({ account, onSaved, onCancel }: { account?: Account | null; onSaved: () => void; onCancel: () => void }) {
  const [name, setName] = useState(account?.name || "");
  const [accountType, setAccountType] = useState<string>(account?.account_type || "checking");
  const [openingBalance, setOpeningBalance] = useState(account?.opening_balance || "0,00");
  const [status, setStatus] = useState(account?.is_active === false ? "inactive" : "active");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const submit = async () => {
    setSaving(true); setError(null);
    try {
      if (!name.trim()) throw new Error("Dê um nome para esta conta.");
      if (account) await api.updateAccount(account.id, { name: name.trim(), account_type: accountType, is_active: status === "active" });
      else await api.createAccount({ name: name.trim(), account_type: accountType, opening_balance: openingBalance.replace(/\./g, "").replace(",", ".") || "0.00" });
      onSaved();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível salvar a conta."); } finally { setSaving(false); }
  };
  return <div className="rounded-card border border-navy/15 bg-[#fbfcfa] p-5 shadow-card md:p-6"><div className="mb-5 flex items-start justify-between"><div><p className="eyebrow">{account ? "Editar conta" : "Nova conta"}</p><h2 className="mt-1 font-display text-2xl tracking-[-0.03em]">{account ? "Mantenha o mapa atualizado." : "De onde o dinheiro sai?"}</h2></div><button onClick={onCancel} className="rounded-lg p-2 text-muted hover:bg-paper" aria-label="Fechar"><X size={18} /></button></div><div className="grid gap-4 md:grid-cols-3"><div><label className="label" htmlFor="account-name">Nome</label><Input id="account-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex.: Nubank" /></div><div><label className="label" htmlFor="account-type">Tipo</label><Select id="account-type" value={accountType} onChange={(event) => setAccountType(event.target.value)}><option value="checking">Conta corrente</option><option value="savings">Poupança</option><option value="cash">Dinheiro</option><option value="investment">Investimentos</option><option value="other">Outra</option></Select></div>{account ? <div><label className="label" htmlFor="account-status">Status</label><Select id="account-status" value={status} onChange={(event) => setStatus(event.target.value)}><option value="active">Ativa</option><option value="inactive">Inativa</option></Select></div> : <div><label className="label" htmlFor="opening-balance">Saldo inicial</label><div className="relative"><span className="absolute left-3 top-3 text-sm text-muted">R$</span><Input id="opening-balance" inputMode="decimal" value={openingBalance} onChange={(event) => setOpeningBalance(event.target.value)} className="pl-10" /></div></div>}</div>{error && <p role="alert" className="mt-4 rounded-xl border border-rust/20 bg-rust/5 px-3 py-2.5 text-sm text-rust">{error}</p>}<div className="mt-6 flex justify-end gap-2"><Button variant="quiet" onClick={onCancel}>Cancelar</Button><Button onClick={() => void submit()} disabled={saving}>{saving ? <Spinner /> : <Check size={16} />} {saving ? "Salvando…" : account ? "Salvar alterações" : "Criar conta"}</Button></div></div>;
}
