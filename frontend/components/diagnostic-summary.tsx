import { AlertCircle, CheckCircle2, CircleHelp, Flag, Target } from "lucide-react";
import { Badge, Card, CardDescription, CardHeader, CardTitle } from "@/components/ui";
import type { DiagnosticSummary } from "@/lib/types";
import { formatLongDate, money } from "@/lib/utils";

const signalTone: Record<DiagnosticSummary["signals"][number]["level"], "positive" | "negative" | "warning" | "neutral"> = {
  positive: "positive",
  attention: "warning",
  priority: "negative",
  info: "neutral",
};

function SignalIcon({ level }: { level: DiagnosticSummary["signals"][number]["level"] }) {
  if (level === "positive") return <CheckCircle2 size={17} />;
  if (level === "priority") return <Flag size={17} />;
  if (level === "attention") return <AlertCircle size={17} />;
  return <CircleHelp size={17} />;
}

function Metric({ label, value }: { label: string; value: string | null }) {
  return <div className="rounded-xl bg-paper p-4"><p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted">{label}</p><p className="mt-2 font-display text-xl tracking-[-0.02em] text-ink">{value ? money(value) : "—"}</p></div>;
}

export function DiagnosticSummaryCard({ summary }: { summary: DiagnosticSummary | null }) {
  if (!summary || summary.status !== "completed") return null;
  return <section className="mt-6 space-y-5" aria-label="Resumo do diagnóstico">
    <Card>
      <CardHeader>
        <div><CardTitle>Seu ponto de partida</CardTitle><CardDescription>Uma leitura das respostas que você informou. Ela não substitui uma análise personalizada.</CardDescription></div>
        <Badge tone="positive">Atualizado</Badge>
      </CardHeader>
      <div className="grid gap-3 px-5 pb-6 sm:grid-cols-2 lg:grid-cols-4 md:px-6">
        <Metric label="Renda mensal média" value={summary.metrics.monthly_income} />
        <Metric label="Despesas mensais" value={summary.metrics.monthly_expenses} />
        <Metric label="Margem mensal" value={summary.metrics.monthly_margin} />
        <Metric label="Dívidas informadas" value={summary.metrics.total_debt} />
      </div>
      {summary.snapshot_date && <p className="px-5 pb-5 text-xs text-muted md:px-6">Respostas enviadas em {formatLongDate(summary.snapshot_date)}.</p>}
    </Card>

    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader><div><CardTitle>Pontos de atenção</CardTitle><CardDescription>O que merece ser observado primeiro.</CardDescription></div><AlertCircle size={18} className="text-brand-brown" /></CardHeader>
        <div className="space-y-3 px-5 pb-6 md:px-6">{summary.signals.length ? summary.signals.map((signal) => <div key={`${signal.level}-${signal.title}`} className="flex items-start gap-3 rounded-xl bg-paper p-3"><span className="mt-0.5 text-brand-brown"><SignalIcon level={signal.level} /></span><div><div className="flex flex-wrap items-center gap-2"><p className="text-sm font-semibold text-ink">{signal.title}</p><Badge tone={signalTone[signal.level]}>{signal.level === "positive" ? "Ponto forte" : signal.level === "priority" ? "Prioridade" : signal.level === "attention" ? "Atenção" : "Informação"}</Badge></div><p className="mt-1 text-sm leading-6 text-muted">{signal.description}</p></div></div>) : <p className="text-sm text-muted">Ainda não há pontos de atenção calculados.</p>}</div>
      </Card>

      <Card>
        <CardHeader><div><CardTitle>Próximos passos</CardTitle><CardDescription>Pequenas ações para começar com clareza.</CardDescription></div><Target size={18} className="text-moss" /></CardHeader>
        <ol className="space-y-4 px-5 pb-6 md:px-6">{summary.next_steps.length ? summary.next_steps.map((step) => <li key={step.priority} className="flex gap-3"><span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-mint text-xs font-bold text-moss">{step.priority}</span><div><p className="text-sm font-semibold text-ink">{step.title}</p><p className="mt-1 text-sm leading-6 text-muted">{step.description}</p></div></li>) : <li className="text-sm text-muted">Nenhum próximo passo foi calculado.</li>}</ol>
      </Card>
    </div>
  </section>;
}
