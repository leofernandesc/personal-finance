"use client";

import Link from "next/link";
import React from "react";
import { ClipboardCheck, RotateCcw } from "lucide-react";
import { DiagnosticForm } from "@/components/diagnostic-form";
import { useAuth } from "@/components/auth-provider";
import { ErrorState, PageHeader, LoadingState } from "@/components/page";
import { Badge } from "@/components/ui";
import { api, ApiError } from "@/lib/api";
import type { Diagnostic } from "@/lib/types";

export default function DiagnosticPage() {
  const { user } = useAuth();
  const [diagnostic, setDiagnostic] = React.useState<Diagnostic | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  const load = React.useCallback(() => {
    setLoading(true);
    setError(null);
    api.diagnostic().then(setDiagnostic).catch((reason) => {
      setError(reason instanceof ApiError ? reason.message : "Não foi possível carregar o diagnóstico.");
    }).finally(() => setLoading(false));
  }, []);

  React.useEffect(() => { load(); }, [load]);

  if (!user || loading) return <LoadingState label="Abrindo seu diagnóstico" />;
  if (error || !diagnostic) return <ErrorState message={error ?? "Diagnóstico indisponível."} onRetry={load} />;

  return <>
    <PageHeader
      eyebrow="Seu espaço"
      title="Diagnóstico financeiro"
      description="Um retrato da sua situação atual para orientar a organização dos próximos passos. Você pode salvar e continuar depois."
      action={<Link href="/dashboard" className="inline-flex h-11 items-center justify-center gap-2 rounded-xl border border-line bg-white px-4 text-sm font-semibold text-ink hover:border-moss hover:bg-mint/20">Voltar ao início</Link>}
    />
    <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-brand-pink/50 bg-brand-pink-soft p-4 text-sm leading-6 text-brand-brown-dark sm:flex-row sm:items-center sm:justify-between">
      <div className="flex items-start gap-3"><ClipboardCheck size={19} className="mt-0.5 shrink-0" /><p><strong>{diagnostic.status === "completed" ? "Diagnóstico concluído." : "Leve o tempo que precisar."}</strong> Suas respostas ficam privadas e podem ser alteradas depois.</p></div>
      {diagnostic.status === "completed" && <Badge tone="positive">Atualizado</Badge>}
    </div>
    <DiagnosticForm user={user} diagnostic={diagnostic} />
    {diagnostic.status === "completed" && <div className="mt-6 flex items-center gap-2 text-xs text-muted"><RotateCcw size={14} /> Edite suas respostas quando sua situação mudar.</div>}
  </>;
}
