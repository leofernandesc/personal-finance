"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BarChart3,
  CalendarRange,
  Download,
  Landmark,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { useAuth } from "@/components/auth-provider";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/page";
import { Badge, Button, Card, CardDescription, CardHeader, CardTitle, Input, Progress } from "@/components/ui";
import { api } from "@/lib/api";
import type { ReportData } from "@/lib/types";
import {
  accountTypeLabels,
  money,
  monthLabel,
  numberValue,
  percent,
  todayForTimezone,
} from "@/lib/utils";

const colors = ["#2f6b58", "#183a4d", "#d98d63", "#9aa85a", "#b99b3b"];

export default function ReportsPage() {
  const { user } = useAuth();
  const [data, setData] = useState<ReportData | null>(null);
  const [selectedMonth, setSelectedMonth] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (user?.timezone && !selectedMonth) {
      setSelectedMonth(todayForTimezone(user.timezone).slice(0, 7));
    }
  }, [selectedMonth, user?.timezone]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await api.report(selectedMonth ? `${selectedMonth}-01` : undefined));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível gerar o relatório.");
    } finally {
      setLoading(false);
    }
  }, [selectedMonth]);
  useEffect(() => { void load(); }, [load]);

  const categories = useMemo(
    () => data?.by_category.map((item, index) => ({
      name: item.category_name,
      value: numberValue(item.amount),
      color: colors[index % colors.length],
    })) || [],
    [data],
  );
  const evolution = useMemo(
    () => data?.monthly_evolution.map((item) => ({
      ...item,
      label: monthLabel(item.month).replace(/ de /g, " "),
      incomeValue: numberValue(item.income),
      expenseValue: numberValue(item.expense),
    })) || [],
    [data],
  );

  return (
    <>
      <PageHeader
        eyebrow="Leia o período com calma"
        title="Relatórios"
        description="Compare meses, entenda concentrações e confira o que foi planejado contra o que realmente aconteceu."
        action={(
          <div className="flex flex-wrap items-end gap-2">
            <div>
              <label className="label" htmlFor="report-month">Mês de referência</label>
              <Input id="report-month" type="month" value={selectedMonth} onChange={(event) => setSelectedMonth(event.target.value)} className="w-44 bg-white" />
            </div>
            <Button variant="secondary" onClick={() => window.print()}><Download size={16} /> Imprimir resumo</Button>
          </div>
        )}
      />

      {loading ? <LoadingState label="Montando seu panorama" /> : error ? <ErrorState message={error} onRetry={() => void load()} /> : data && (
        <div className="space-y-5">
          <div className="grid gap-4 md:grid-cols-3">
            <ReportStat icon={<TrendingUp size={17} />} label="Receitas" value={money(data.totals.income)} tone="positive" />
            <ReportStat icon={<TrendingDown size={17} />} label="Despesas" value={money(data.totals.expense)} tone="negative" />
            <ReportStat icon={<CalendarRange size={17} />} label="Resultado" value={money(data.totals.savings)} tone={numberValue(data.totals.savings) >= 0 ? "positive" : "negative"} />
          </div>

          <div className="grid gap-5 xl:grid-cols-[1.25fr_0.75fr]">
            <Card className="overflow-hidden">
              <CardHeader>
                <div><p className="eyebrow">Evolução mensal</p><CardTitle className="mt-1">Receitas x despesas</CardTitle><CardDescription>Seis meses encerrando em {monthLabel(data.period.start)}.</CardDescription></div>
                <Badge tone="neutral">6 meses</Badge>
              </CardHeader>
              {evolution.some((item) => item.incomeValue || item.expenseValue) ? (
                <div className="h-[340px] px-3 pb-6 pt-5 md:px-6" role="img" aria-label="Gráfico de receitas e despesas dos últimos seis meses">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={evolution} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
                      <CartesianGrid vertical={false} stroke="#e4e5e1" strokeDasharray="3 3" />
                      <XAxis dataKey="label" tickLine={false} axisLine={false} tick={{ fill: "#6d7782", fontSize: 10 }} minTickGap={18} />
                      <YAxis tickLine={false} axisLine={false} tick={{ fill: "#6d7782", fontSize: 10 }} tickFormatter={(value) => `R$${value}`} />
                      <Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e4e5e1", fontSize: 12 }} formatter={(value) => money(Number(value))} />
                      <Bar dataKey="incomeValue" name="Receitas" fill="#2f6b58" radius={[5, 5, 0, 0]} />
                      <Bar dataKey="expenseValue" name="Despesas" fill="#d98d63" radius={[5, 5, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : <EmptyState compact title="Ainda não há evolução" description="Registre movimentos para comparar seus meses." />}
            </Card>

            <Card className="overflow-hidden">
              <CardHeader><div><p className="eyebrow">Distribuição</p><CardTitle className="mt-1">Despesas por categoria</CardTitle><CardDescription>Onde as saídas se concentraram no mês.</CardDescription></div><BarChart3 size={19} className="text-muted" /></CardHeader>
              {categories.length ? <div className="grid grid-cols-[150px_1fr] items-center gap-2 px-5 pb-7 pt-2"><div className="h-[180px]" role="img" aria-label="Gráfico de despesas por categoria"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={categories} dataKey="value" innerRadius={50} outerRadius={72} paddingAngle={3} stroke="none">{categories.map((item) => <Cell key={item.name} fill={item.color} />)}</Pie><Tooltip formatter={(value) => money(Number(value))} /></PieChart></ResponsiveContainer></div><div className="space-y-3">{categories.slice(0, 5).map((item) => <div key={item.name} className="flex items-center justify-between gap-2"><div className="flex min-w-0 items-center gap-2"><span className="h-2 w-2 shrink-0 rounded-full" style={{ backgroundColor: item.color }} /><span className="truncate text-xs text-muted">{item.name}</span></div><span className="text-xs font-semibold text-ink">{money(item.value)}</span></div>)}</div></div> : <EmptyState compact title="Nada para classificar" description="Ainda não há despesas categorizadas neste mês." />}
            </Card>
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <Card className="overflow-hidden">
              <CardHeader><div><p className="eyebrow">Posição atual</p><CardTitle className="mt-1">Saldo por conta</CardTitle><CardDescription>O saldo vem sempre do backend financeiro.</CardDescription></div><Landmark size={19} className="text-muted" /></CardHeader>
              {data.accounts.length ? <div className="divide-y divide-line">{data.accounts.map((account) => <div key={account.id} className="flex items-center justify-between gap-4 px-5 py-4 md:px-6"><div><p className="text-sm font-semibold text-ink">{account.name}</p><p className="mt-1 text-xs text-muted">{accountTypeLabels[account.account_type] || account.account_type}</p></div><p className="text-sm font-semibold text-ink">{money(account.balance)}</p></div>)}</div> : <EmptyState compact title="Nenhuma conta ativa" description="Cadastre uma conta para acompanhar saldos." />}
            </Card>

            <Card className="overflow-hidden">
              <CardHeader><div><p className="eyebrow">Planejado x realizado</p><CardTitle className="mt-1">Orçamentos</CardTitle><CardDescription>Limite e consumo no mês de referência.</CardDescription></div></CardHeader>
              {data.budgets.length ? <div className="divide-y divide-line">{data.budgets.map((budget) => { const used = numberValue(budget.utilization_percent); return <div key={budget.id} className="px-5 py-4 md:px-6"><div className="mb-2 flex items-center justify-between"><div><p className="text-sm font-semibold text-ink">{budget.category_name}</p><p className="mt-1 text-xs text-muted">{money(budget.spent_amount)} realizado de {money(budget.limit_amount)} planejado</p></div><span className={`text-xs font-semibold ${used > 100 ? "text-rust" : "text-moss"}`}>{percent(used)}</span></div><Progress value={used} tone={used > 100 ? "rust" : "moss"} /></div>; })}</div> : <EmptyState compact title="Sem orçamento neste mês" description="Defina limites para comparar planejado e realizado." />}
            </Card>
          </div>
        </div>
      )}
    </>
  );
}

function ReportStat({ icon, label, value, tone }: { icon: React.ReactNode; label: string; value: string; tone: "positive" | "negative" | "neutral" }) {
  return <Card className="p-5"><div className="flex items-center gap-3"><span className={`flex h-9 w-9 items-center justify-center rounded-xl ${tone === "positive" ? "bg-mint/60 text-moss" : tone === "negative" ? "bg-rust/10 text-rust" : "bg-paper text-navy"}`}>{icon}</span><span className="text-xs font-semibold uppercase tracking-[0.11em] text-muted">{label}</span></div><p className="mt-5 font-display text-2xl tracking-[-0.03em]">{value}</p></Card>;
}
