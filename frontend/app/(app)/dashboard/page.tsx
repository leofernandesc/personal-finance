"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { ArrowDownLeft, ArrowUpRight, ChevronRight, MoreHorizontal, Plus, WalletCards } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/page";
import { TransactionLink, TransactionList } from "@/components/transaction-list";
import { Badge, Button, Card, CardDescription, CardHeader, CardTitle, Progress } from "@/components/ui";
import { api } from "@/lib/api";
import type { DashboardData, DiagnosticSummary } from "@/lib/types";
import { accountTypeLabels, formatDate, money, monthLabel, numberValue, percent, todayForTimezone } from "@/lib/utils";

const categoryColors = ["#76584e", "#e8b8b8", "#a87565", "#c99a8f", "#8e6e62", "#b9787d"];

export default function DashboardPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [data, setData] = useState<DashboardData | null>(null);
  const [diagnosticSummary, setDiagnosticSummary] = useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { setData(await api.dashboard()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar o dashboard."); } finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  useEffect(() => { api.diagnosticSummary().then(setDiagnosticSummary).catch(() => setDiagnosticSummary(null)); }, []);

  const today = todayForTimezone(user?.timezone);
  const firstName = user?.full_name?.split(" ")[0] || "por aí";
  const categoryData = useMemo(() => data?.by_category.map((item, index) => ({ ...item, amountNumber: numberValue(item.amount), color: categoryColors[index % categoryColors.length] })) ?? [], [data]);

  return <>
    <PageHeader eyebrow={monthLabel(today)} title={`Olá, ${firstName}.`} description="Aqui está a leitura do seu dinheiro neste mês." action={<Button onClick={() => router.push("/transactions?new=1")}><Plus size={17} /> Nova transação</Button>} />
    {loading ? <LoadingState label="Organizando seu mês" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : !data ? <ErrorState onRetry={() => void load()} /> : <div className="space-y-5">
      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <SummaryCard label="Saldo total" value={money(data.total_balance)} description="em todas as contas" tone="navy" icon={<WalletCards size={17} />} />
        <SummaryCard label="Entradas no mês" value={money(data.totals.income)} description="receitas confirmadas" tone="positive" icon={<ArrowDownLeft size={17} />} />
        <SummaryCard label="Saídas no mês" value={money(data.totals.expense)} description="despesas registradas" tone="negative" icon={<ArrowUpRight size={17} />} />
        <SummaryCard label="Economia do mês" value={money(data.totals.savings)} description={numberValue(data.totals.savings) >= 0 ? "você está no positivo" : "vale olhar com calma"} tone={numberValue(data.totals.savings) >= 0 ? "positive" : "negative"} icon={<span className="text-base">✦</span>} />
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.65fr_1fr]">
        <Card className="overflow-hidden">
          <CardHeader><div><p className="eyebrow">Ritmo do mês</p><CardTitle className="mt-1">Entradas e saídas</CardTitle><CardDescription>O movimento financeiro dia a dia.</CardDescription></div><Badge tone="neutral">{data.flow.length ? `${data.flow.length} dias` : "Sem movimentação"}</Badge></CardHeader>
          <div className="h-[240px] px-1 pb-4 pt-3 sm:h-[260px] md:h-[285px] md:px-4 md:pt-4"><FlowChart data={data.flow} /></div>
          {!data.flow.length && <div className="-mt-28 pb-16"><EmptyState compact title="Seu mês começa aqui" description="Registre uma entrada ou saída para acompanhar o ritmo do seu dinheiro." actionLabel="Registrar transação" onAction={() => router.push("/transactions?new=1")} /></div>}
        </Card>
        <Card className="overflow-hidden">
          <CardHeader><div><p className="eyebrow">Onde foi parar</p><CardTitle className="mt-1">Gastos por categoria</CardTitle><CardDescription>As maiores fatias das suas saídas.</CardDescription></div><Link href="/reports" className="rounded-lg p-1.5 text-muted hover:bg-paper" aria-label="Abrir relatório"><ChevronRight size={18} /></Link></CardHeader>
          {categoryData.length ? <div className="grid grid-cols-1 items-center gap-4 px-5 pb-6 pt-1 md:grid-cols-[145px_1fr] md:gap-1 md:px-6"><div className="mx-auto h-[155px] w-full max-w-[180px] md:mx-0 md:h-[170px] md:max-w-none"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={categoryData} dataKey="amountNumber" nameKey="category_name" innerRadius={49} outerRadius={70} paddingAngle={3} stroke="none">{categoryData.map((entry) => <Cell key={entry.category_id} fill={entry.color} />)}</Pie><Tooltip formatter={(value) => money(Number(value))} /></PieChart></ResponsiveContainer></div><div className="w-full space-y-3">{categoryData.slice(0, 4).map((item) => <div key={item.category_id} className="flex items-center justify-between gap-2"><div className="flex min-w-0 items-center gap-2"><span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: item.color }} /><span className="truncate text-xs text-muted">{item.category_name}</span></div><span className="text-xs font-semibold text-ink">{money(item.amount)}</span></div>)}</div></div> : <EmptyState compact title="Nada para classificar" description="Quando uma despesa entrar, você verá as categorias mais importantes aqui." />}
        </Card>
      </section>

      <section className="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
        <Card className="overflow-hidden"><CardHeader><div><p className="eyebrow">Planejamento</p><CardTitle className="mt-1">Orçamentos do mês</CardTitle><CardDescription>Quanto já foi usado em cada limite.</CardDescription></div><Link href="/budgets" className="text-xs font-semibold text-moss hover:text-navy">Gerenciar</Link></CardHeader>{data.budgets.length ? <div className="divide-y divide-line">{data.budgets.slice(0, 4).map((budget) => { const used = numberValue(budget.utilization_percent); return <div key={budget.id} className="px-5 py-4 md:px-6"><div className="mb-2 flex items-center justify-between gap-4"><div><p className="text-sm font-semibold text-ink">{budget.category_name}</p><p className="mt-0.5 text-xs text-muted">{money(budget.spent_amount)} de {money(budget.limit_amount)}</p></div><span className={`text-xs font-semibold ${used > 100 ? "text-rust" : "text-ink"}`}>{percent(used)}</span></div><Progress value={used} tone={used > 100 ? "rust" : "moss"} /><div className="mt-2 flex justify-between text-[0.68rem] text-muted"><span>{numberValue(budget.remaining_amount) >= 0 ? `${money(budget.remaining_amount)} restantes` : `${money(budget.exceeded_amount)} acima do limite`}</span><span>{monthLabel(budget.month)}</span></div></div> })}</div> : <EmptyState compact title="Orçamento à vista" description="Defina limites por categoria para dar uma intenção ao seu mês." actionLabel="Criar orçamento" onAction={() => router.push("/budgets")} />}</Card>
        <Card className="overflow-hidden"><CardHeader><div><p className="eyebrow">Últimos movimentos</p><CardTitle className="mt-1">Transações recentes</CardTitle><CardDescription>O que acabou de acontecer.</CardDescription></div><TransactionLink /></CardHeader>{data.recent_transactions.length ? <TransactionList transactions={data.recent_transactions} compact /> : <EmptyState compact title="Ainda não existem transações" description="Você também pode registrar pelo WhatsApp." actionLabel="Registrar primeira" onAction={() => router.push("/transactions?new=1")} />}</Card>
      </section>

      {diagnosticSummary?.status === "completed" && <section><Card className="overflow-hidden"><CardHeader><div><p className="eyebrow">Seu ponto de partida</p><CardTitle className="mt-1">O que merece atenção</CardTitle><CardDescription>Uma leitura das respostas do seu diagnóstico.</CardDescription></div><Link href="/diagnostico" className="text-xs font-semibold text-moss hover:text-navy">Ver diagnóstico</Link></CardHeader><div className="grid gap-3 px-5 pb-6 sm:grid-cols-3 md:px-6"><div className="rounded-xl bg-paper p-4"><p className="text-xs text-muted">Margem informada</p><p className="mt-2 font-display text-xl text-ink">{diagnosticSummary.metrics.monthly_margin ? money(diagnosticSummary.metrics.monthly_margin) : "—"}</p></div><div className="rounded-xl bg-paper p-4"><p className="text-xs text-muted">Dívidas informadas</p><p className="mt-2 font-display text-xl text-ink">{diagnosticSummary.metrics.total_debt ? money(diagnosticSummary.metrics.total_debt) : "—"}</p></div><div className="rounded-xl bg-brand-pink-soft p-4"><p className="text-xs text-brand-brown">Próximo foco</p><p className="mt-2 text-sm font-semibold text-brand-brown-dark">{diagnosticSummary.next_steps[0]?.title ?? "Continue acompanhando seu mês"}</p></div></div></Card></section>}

      <section><div className="mb-3 flex items-center justify-between"><div><p className="eyebrow">Panorama</p><h2 className="mt-1 font-display text-2xl tracking-[-0.03em]">Suas contas</h2></div><Link href="/accounts" className="text-xs font-semibold text-moss hover:text-navy">Ver contas</Link></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{data.accounts.map((account) => <Card key={account.id} className="flex items-center gap-4 p-5"><span className="flex h-11 w-11 items-center justify-center rounded-2xl bg-paper text-navy"><WalletCards size={19} /></span><div className="min-w-0 flex-1"><p className="truncate text-sm font-semibold text-ink">{account.name}</p><p className="mt-1 text-xs text-muted">{accountTypeLabels[account.account_type] || account.account_type}</p></div><p className="text-sm font-semibold text-ink">{money(account.balance)}</p><MoreHorizontal size={17} className="text-muted" /></Card>)}</div></section>
    </div>}
  </>;
}

function SummaryCard({ label, value, description, tone, icon }: { label: string; value: string; description: string; tone: "navy" | "positive" | "negative"; icon: React.ReactNode }) {
  return <Card className="p-5"><div className="flex items-start justify-between"><div><p className="text-xs font-semibold uppercase tracking-[0.11em] text-muted">{label}</p><p className="mt-4 font-display text-[1.75rem] tracking-[-0.035em] text-ink">{value}</p></div><span className={`flex h-9 w-9 items-center justify-center rounded-xl ${tone === "navy" ? "bg-navy text-white" : tone === "positive" ? "bg-mint/65 text-moss" : "bg-rust/10 text-rust"}`}>{icon}</span></div><p className="mt-3 text-xs text-muted">{description}</p></Card>;
}

function FlowChart({ data }: { data: DashboardData["flow"] }) {
  const chartData = data.map((item) => ({ ...item, label: formatDate(item.date, { day: "2-digit", month: "short" }) }));
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={chartData} margin={{ top: 10, right: 8, left: -22, bottom: 0 }}><defs><linearGradient id="incomeFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#76584e" stopOpacity={0.2} /><stop offset="95%" stopColor="#76584e" stopOpacity={0} /></linearGradient><linearGradient id="expenseFill" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#b56d70" stopOpacity={0.16} /><stop offset="95%" stopColor="#b56d70" stopOpacity={0} /></linearGradient></defs><CartesianGrid vertical={false} stroke="#eadfdd" strokeDasharray="3 3" /><XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#7b6c68", fontSize: 10 }} minTickGap={24} /><YAxis tickLine={false} axisLine={false} tick={{ fill: "#7b6c68", fontSize: 10 }} tickFormatter={(value) => `R$${value}`} /><Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #eadfdd", boxShadow: "0 10px 30px rgba(83,49,41,.09)", fontSize: 12 }} formatter={(value) => money(Number(value))} /><Area type="monotone" dataKey="income" name="Entradas" stroke="#76584e" strokeWidth={2.2} fill="url(#incomeFill)" /><Area type="monotone" dataKey="expense" name="Saídas" stroke="#b56d70" strokeWidth={2.2} fill="url(#expenseFill)" /></AreaChart></ResponsiveContainer>;
}
