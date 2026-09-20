"use client";

import { useCallback, useEffect, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, Edit3, Landmark, Plus, WalletCards } from "lucide-react";
import { AccountEditor } from "@/components/account-editor";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/page";
import { Badge, Button, Card } from "@/components/ui";
import { api } from "@/lib/api";
import type { Account } from "@/lib/types";
import { accountTypeLabels, money, numberValue } from "@/lib/utils";

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editorOpen, setEditorOpen] = useState(false);
  const [editing, setEditing] = useState<Account | null>(null);
  const load = useCallback(async () => { setLoading(true); setError(null); try { setAccounts(await api.accounts()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar as contas."); } finally { setLoading(false); } }, []);
  useEffect(() => { void load(); }, [load]);
  const total = accounts.filter((account) => account.is_active).reduce((sum, account) => sum + numberValue(account.balance), 0);
  return <>
    <PageHeader eyebrow="Onde você guarda" title="Contas" description="Uma leitura rápida de cada lugar onde seu dinheiro vive." action={<Button onClick={() => { setEditing(null); setEditorOpen(true); }}><Plus size={17} /> Nova conta</Button>} />
    {editorOpen && <div className="mb-6"><AccountEditor key={editing?.id ?? "new"} account={editing} onCancel={() => { setEditorOpen(false); setEditing(null); }} onSaved={() => { setEditorOpen(false); setEditing(null); void load(); }} /></div>}
    {loading ? <LoadingState label="Buscando contas" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : !accounts.length ? <Card><EmptyState title="Nenhuma conta ainda" description="Comece pela conta que você mais usa. O saldo inicial cria a primeira fotografia." actionLabel="Criar primeira conta" onAction={() => setEditorOpen(true)} /></Card> : <div className="space-y-5"><Card className="overflow-hidden bg-navy text-white"><div className="flex flex-col gap-5 p-6 md:flex-row md:items-end md:justify-between md:p-8"><div><p className="text-xs font-semibold uppercase tracking-[0.15em] text-white/55">Patrimônio acompanhado</p><p className="mt-3 font-display text-4xl tracking-[-0.04em]">{money(total)}</p><p className="mt-2 text-sm text-white/60">somando {accounts.filter((account) => account.is_active).length} contas ativas</p></div><div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10"><Landmark size={25} className="text-mint" /></div></div></Card><div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{accounts.map((account) => <AccountCard key={account.id} account={account} onEdit={() => { setEditing(account); setEditorOpen(true); }} />)}</div></div>}
  </>;
}

function AccountCard({ account, onEdit }: { account: Account; onEdit: () => void }) {
  return <Card className={`p-5 ${!account.is_active ? "opacity-60" : ""}`}><div className="flex items-start justify-between"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-paper text-navy"><WalletCards size={20} /></span><div className="flex items-center gap-2"><Badge tone={account.is_active ? "positive" : "neutral"}>{account.is_active ? "Ativa" : "Inativa"}</Badge><button className="rounded-lg p-1.5 text-muted hover:bg-paper" aria-label={`Editar ${account.name}`} onClick={onEdit}><Edit3 size={16} /></button></div></div><p className="mt-7 text-sm font-semibold text-ink">{account.name}</p><p className="mt-1 text-xs text-muted">{accountTypeLabels[account.account_type] || account.account_type}</p><p className="mt-5 font-display text-2xl tracking-[-0.03em] text-ink">{money(account.balance)}</p><div className="mt-5 flex items-center gap-4 border-t border-line pt-4 text-[0.68rem] text-muted"><span className="inline-flex items-center gap-1"><ArrowDownLeft size={13} className="text-moss" /> entradas somam</span><span className="inline-flex items-center gap-1"><ArrowUpRight size={13} className="text-rust" /> saídas subtraem</span></div></Card>;
}
