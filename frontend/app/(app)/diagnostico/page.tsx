"use client";

import Link from "next/link";
import React from "react";
import { ClipboardCheck, RotateCcw } from "lucide-react";
import { DiagnosticSummaryCard } from "@/components/diagnostic-summary";
import { DiagnosticForm } from "@/components/diagnostic-form";
import { useAuth } from "@/components/auth-provider";
import { ErrorState, PageHeader, LoadingState } from "@/components/page";
import { Badge } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { Diagnostic, DiagnosticSummary } from "@/lib/types";

export default function DiagnosticPage() {
  const { user } = useAuth();
  const [diagnostic, setDiagnostic] = React.useState<Diagnostic | null>(null);
  const [summary, setSummary] = React.useState<DiagnosticSummary | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback((showLoading = true) => {
    if (showLoading) {
      setLoading(true);
      setError(null);
    }
    api.diagnostic().then(async (value) => {
      setDiagnostic(value);
      if (value.status === "completed") {
        try {
          setSummary(await api.diagnosticSummary());
        } catch {
          setSummary(null);
        }
      } else {
        setSummary(null);
      }
    }).catch((reason) => {
      if (showLoading) setError(reason instanceof ApiError ? reason.message : "Não foi possível carregar o diagnóstico.");
    }).finally(() => {
      if (showLoading) setLoading(false);
    });
  }, []);

  React.useEffect(() => {
    load();
    const refreshInBackground = () => load(false);
    window.addEventListener("diagnostic-changed", refreshInBackground);
    return () => window.removeEventListener("diagnostic-changed", refreshInBackground);
  }, [load]);

  if (!user || loading) return <LoadingState label="Abrindo seu diagnóstico" />;
  if (error || !diagnostic) return <ErrorState message={error ?? "Diagnóstico indisponível."} onRetry={load} />;

  return <>
    <PageHeader
      key="diagnostic-page-header"
      eyebrow="Seu espaço"
      title="Diagnóstico financeiro"
      description="Um retrato da sua situação atual para orientar a organização dos próximos passos. Você pode salvar e continuar depois."
      action={<Link href="/dashboard" className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-line bg-white px-4 text-sm font-semibold text-ink hover:border-moss hover:bg-mint/20">Voltar ao início</Link>}
    />
    <div key="diagnostic-status-banner" className="mb-6 flex flex-col gap-3 rounded-2xl border border-brand-pink/50 bg-brand-pink-soft p-4 text-sm leading-6 text-brand-brown-dark sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3"><ClipboardCheck size={19} className="mt-0.5 shrink-0" /><p><strong>{diagnostic.status === "completed" ? "Diagnóstico concluído." : "Leve o tempo que precisar."}</strong> Suas respostas ficam privadas e podem ser alteradas depois.</p></div>
      {diagnostic.status === "completed" && <Badge tone="positive">Atualizado</Badge>}
    </div>
    {diagnostic.status === "not_started" && <div key="diagnostic-start-intro" className="mb-6 rounded-2xl border border-line bg-white p-5 md:p-6"><p className="text-sm font-semibold text-ink">Antes de começar</p><p className="mt-2 max-w-2xl text-sm leading-6 text-muted">São 13 etapas e cerca de 15 a 20 minutos. Você pode salvar seu progresso e voltar quando quiser. Não informe senhas, tokens ou códigos de acesso.</p><Link href="/dashboard" className="mt-4 inline-flex text-sm font-semibold text-brand-brown underline decoration-brand-pink underline-offset-4">Agora não, voltar ao início</Link></div>}
    <DiagnosticSummaryCard key="diagnostic-summary" summary={summary} />
    <DiagnosticForm key="diagnostic-form" user={user} diagnostic={diagnostic} />
    {diagnostic.status === "completed" && <div key="diagnostic-completion-note" className="mt-6 flex items-center gap-2 text-xs text-muted"><RotateCcw size={14} /> Edite suas respostas quando sua situação mudar.</div>}
  </>;
}
