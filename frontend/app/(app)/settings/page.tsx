"use client";

import Link from "next/link";
import React from "react";
import { ArrowRight, ClipboardCheck, Clock3, LockKeyhole, Mail, UserRound } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page";
import { Badge, Card, CardDescription, CardHeader, CardTitle } from "@/components/ui";
import { api } from "@/lib/api";
import type { Diagnostic } from "@/lib/types";

export default function SettingsPage() {
  const { user } = useAuth();
  const [diagnostic, setDiagnostic] = React.useState<Diagnostic | null>(null);
  React.useEffect(() => { api.diagnostic().then(setDiagnostic).catch(() => setDiagnostic(null)); }, []);
  const diagnosticLabel = diagnostic?.status === "completed" ? "Concluído" : diagnostic?.status === "draft" ? "Em andamento" : "Pendente";
  return <><PageHeader eyebrow="Seu espaço" title="Configurações" description="Confira os dados usados para manter sua vida financeira organizada e no seu fuso horário." /><div className="grid gap-5 lg:grid-cols-2"><Card><CardHeader><div><CardTitle>Perfil</CardTitle><CardDescription>Identidade e localização da sua conta.</CardDescription></div><UserRound size={19} className="text-muted" /></CardHeader><div className="space-y-4 px-5 pb-6 md:px-6"><InfoRow icon={<UserRound size={16} />} label="Nome" value={user?.full_name || "Não informado"} /><InfoRow icon={<Mail size={16} />} label="E-mail" value={user?.email || "—"} /><InfoRow icon={<Clock3 size={16} />} label="Fuso horário" value={user?.timezone || "—"} /></div></Card><Card><CardHeader><div><CardTitle>Meu diagnóstico</CardTitle><CardDescription>Revise ou atualize as respostas do seu diagnóstico financeiro.</CardDescription></div><ClipboardCheck size={19} className="text-brand-brown" /></CardHeader><div className="px-5 pb-6 md:px-6"><div className="flex items-center justify-between rounded-xl bg-brand-pink-soft p-4"><div><p className="text-sm font-semibold text-ink">{diagnosticLabel}</p><p className="mt-1 text-sm text-muted">{diagnostic ? `${diagnostic.completion_percent}% preenchido` : "Carregando status…"}</p></div><Badge tone={diagnostic?.status === "completed" ? "positive" : "warning"}>{diagnosticLabel}</Badge></div><Link href="/diagnostico" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-brand-brown hover:text-brand-brown-dark">{diagnostic?.status === "completed" ? "Editar diagnóstico" : "Continuar diagnóstico"}<ArrowRight size={15} /></Link></div></Card><Card><CardHeader><div><CardTitle>Segurança</CardTitle><CardDescription>Como o Organiza Finanças protege o acesso.</CardDescription></div><LockKeyhole size={19} className="text-moss" /></CardHeader><div className="space-y-4 px-5 pb-6 md:px-6"><div className="rounded-xl bg-mint/35 p-4"><p className="text-sm font-semibold text-ink">Sessão segura</p><p className="mt-1 text-sm leading-6 text-muted">Sua senha não fica armazenada em texto aberto e seu acesso é mantido de forma protegida.</p></div><div className="rounded-xl bg-paper p-4"><p className="text-sm font-semibold text-ink">Seu espaço é privado</p><p className="mt-1 text-sm leading-6 text-muted">Você vê apenas suas próprias contas, categorias, transações, metas e orçamentos.</p></div></div></Card></div></>;
}

function InfoRow({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) { return <div className="flex items-center gap-3 border-b border-line pb-3 last:border-0 last:pb-0"><span className="text-muted">{icon}</span><div><p className="text-[0.65rem] font-semibold uppercase tracking-[0.12em] text-muted">{label}</p><p className="mt-1 text-sm text-ink">{value}</p></div></div>; }
