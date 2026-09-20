"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, Edit3, PiggyBank, Plus } from "lucide-react";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/page";
import { useAuth } from "@/components/auth-provider";
import { Badge, Button, Card, Input, Progress, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type { Budget, Category } from "@/lib/types";
import { money, monthLabel, numberValue, percent, todayForTimezone } from "@/lib/utils";

export default function BudgetsPage() {
  const { user } = useAuth();
  const [budgets, setBudgets] = useState<Budget[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [categoryId, setCategoryId] = useState("");
  const [month, setMonth] = useState("");
  const [limit, setLimit] = useState("");
  const [formError, setFormError] = useState<string | null>(null);

  const load = useCallback(async () => { setLoading(true); setError(null); try { const [budgetItems, categoryItems] = await Promise.all([api.budgets(), api.categories()]); setBudgets(budgetItems); setCategories(categoryItems.filter((category) => category.kind !== "income" && category.is_active)); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar seus orçamentos."); } finally { setLoading(false); } }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { if (user?.timezone) setMonth(`${todayForTimezone(user.timezone).slice(0, 7)}-01`); }, [user?.timezone]);
  const create = async () => { setSaving(true); setFormError(null); try { if (!categoryId || !limit) throw new Error("Escolha uma categoria e informe um limite."); await api.createBudget({ category_id: categoryId, month, limit_amount: limit.replace(/\./g, "").replace(",", ".") }); setFormOpen(false); setLimit(""); await load(); } catch (reason) { setFormError(reason instanceof Error ? reason.message : "Não foi possível criar o orçamento."); } finally { setSaving(false); } };
  return <>
    <PageHeader eyebrow={monthLabel(month || todayForTimezone(user?.timezone))} title="Orçamentos" description="Dê um limite intencional para as categorias que mais importam." action={<Button onClick={() => setFormOpen((value) => !value)}><Plus size={17} /> Novo orçamento</Button>} />
    {formOpen && <Card className="mb-6 border-navy/15 bg-[#fbfcfa] p-5 md:p-6"><div className="mb-5"><p className="eyebrow">Planejar o mês</p><h2 className="mt-1 font-display text-2xl tracking-[-0.03em]">Quanto cabe aqui?</h2></div><div className="grid gap-4 md:grid-cols-3"><div><label className="label" htmlFor="budget-category">Categoria</label><Select id="budget-category" value={categoryId} onChange={(event) => setCategoryId(event.target.value)}><option value="">Selecione</option>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select></div><div><label className="label" htmlFor="budget-month">Mês</label><Input id="budget-month" type="month" value={month.slice(0, 7)} onChange={(event) => setMonth(`${event.target.value}-01`)} /></div><div><label className="label" htmlFor="budget-limit">Limite</label><div className="relative"><span className="absolute left-3 top-3 text-sm text-muted">R$</span><Input id="budget-limit" inputMode="decimal" value={limit} onChange={(event) => setLimit(event.target.value)} placeholder="800,00" className="pl-10" /></div></div></div>{formError && <p className="mt-4 text-sm text-rust">{formError}</p>}<div className="mt-5 flex justify-end gap-2"><Button variant="quiet" onClick={() => setFormOpen(false)}>Cancelar</Button><Button onClick={() => void create()} disabled={saving}>{saving ? <Spinner /> : <Check size={16} />} Criar limite</Button></div></Card>}
    {loading ? <LoadingState label="Calculando limites" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : !budgets.length ? <Card><EmptyState title="Seu mês ainda está sem limites" description="Um orçamento não é uma regra rígida: é uma intenção visível para decidir com mais calma." actionLabel="Criar primeiro orçamento" onAction={() => setFormOpen(true)} /></Card> : <div className="grid gap-4 lg:grid-cols-2">{budgets.map((budget) => <BudgetCard key={budget.id} budget={budget} onUpdated={load} />)}</div>}
  </>;
}

function BudgetCard({ budget, onUpdated }: { budget: Budget; onUpdated: () => Promise<void> }) {
  const [editing, setEditing] = useState(false);
  const [limit, setLimit] = useState(budget.limit_amount);
  const [saving, setSaving] = useState(false);
  const used = numberValue(budget.utilization_percent);
  const save = async () => { setSaving(true); try { await api.updateBudget(budget.id, { limit_amount: limit.replace(/\./g, "").replace(",", ".") }); setEditing(false); await onUpdated(); } finally { setSaving(false); } };
  return <Card className="p-5 md:p-6"><div className="flex items-start justify-between gap-4"><div className="flex items-center gap-3"><span className="flex h-10 w-10 items-center justify-center rounded-xl bg-mint/55 text-moss"><PiggyBank size={18} /></span><div><p className="font-semibold text-ink">{budget.category_name}</p><p className="mt-0.5 text-xs text-muted">{monthLabel(budget.month)}</p></div></div><button className="rounded-lg p-2 text-muted hover:bg-paper" onClick={() => setEditing((value) => !value)} aria-label="Editar orçamento"><Edit3 size={16} /></button></div><div className="mt-7 flex items-end justify-between"><div><p className="text-xs uppercase tracking-[0.12em] text-muted">Utilizado</p><p className="mt-1 font-display text-3xl tracking-[-0.035em]">{money(budget.spent_amount)}</p></div><div className="text-right"><p className={`text-sm font-semibold ${used > 100 ? "text-rust" : "text-moss"}`}>{percent(used)}</p><p className="mt-1 text-xs text-muted">de {money(budget.limit_amount)}</p></div></div><div className="mt-4"><Progress value={used} tone={used > 100 ? "rust" : "moss"} /></div><div className="mt-3 flex justify-between text-xs text-muted"><span>{numberValue(budget.remaining_amount) >= 0 ? `${money(budget.remaining_amount)} ainda disponíveis` : `${money(budget.exceeded_amount)} acima do limite`}</span><Badge tone={used > 100 ? "negative" : used > 80 ? "warning" : "positive"}>{used > 100 ? "Acima do limite" : used > 80 ? "Atenção" : "No ritmo"}</Badge></div>{editing && <div className="mt-5 flex gap-2 border-t border-line pt-4"><div className="relative flex-1"><span className="absolute left-3 top-2.5 text-xs text-muted">R$</span><Input value={limit} onChange={(event) => setLimit(event.target.value)} className="pl-9" /></div><Button size="small" onClick={() => void save()} disabled={saving}>{saving ? <Spinner /> : <Check size={14} />} Salvar</Button></div>}</Card>;
}
