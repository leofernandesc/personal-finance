"use client";

import Link from "next/link";
import React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Check, ClipboardCheck, Clock3, LockKeyhole, Mail, UserRound } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { useAuth } from "@/components/auth-provider";
import { PageHeader } from "@/components/page";
import { ApiError, api } from "@/lib/api";
import type { Diagnostic } from "@/lib/types";
import { Badge, Button, Card, CardDescription, CardHeader, CardTitle, Input, Select } from "@/components/ui";

const profileSchema = z.object({
  full_name: z.string().trim().min(1, "Informe seu nome.").max(120),
  timezone: z.string().min(1, "Escolha seu fuso horário."),
});

type ProfileValues = z.infer<typeof profileSchema>;

export default function SettingsPage() {
  const { user, updateProfile } = useAuth();
  const [diagnostic, setDiagnostic] = React.useState<Diagnostic | null>(null);
  const [profileNotice, setProfileNotice] = React.useState<string | null>(null);
  const [profileError, setProfileError] = React.useState<string | null>(null);
  const { register, handleSubmit, reset, formState: { errors, isSubmitting } } = useForm<ProfileValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { full_name: user?.full_name ?? "", timezone: user?.timezone ?? "America/Manaus" },
  });

  React.useEffect(() => {
    reset({ full_name: user?.full_name ?? "", timezone: user?.timezone ?? "America/Manaus" });
  }, [reset, user?.full_name, user?.timezone]);

  React.useEffect(() => {
    api.diagnostic().then(setDiagnostic).catch(() => setDiagnostic(null));
  }, []);

  const saveProfile = async (values: ProfileValues) => {
    setProfileError(null);
    setProfileNotice(null);
    try {
      await updateProfile(values);
      setProfileNotice("Perfil atualizado.");
    } catch (reason) {
      setProfileError(reason instanceof ApiError ? reason.message : "Não foi possível atualizar seu perfil.");
    }
  };

  const diagnosticLabel = diagnostic?.status === "completed" ? "Concluído" : diagnostic?.status === "draft" ? "Em andamento" : "Pendente";

  return <>
    <PageHeader eyebrow="Seu espaço" title="Configurações" description="Atualize seus dados e acompanhe o diagnóstico da sua situação financeira." />
    <div className="grid gap-5 lg:grid-cols-2">
      <Card>
        <CardHeader>
          <div><CardTitle>Perfil</CardTitle><CardDescription>Nome e fuso horário usados no seu espaço.</CardDescription></div>
          <UserRound size={19} className="text-muted" />
        </CardHeader>
        <form onSubmit={handleSubmit(saveProfile)} className="space-y-5 px-5 pb-6 md:px-6" noValidate>
          <div><label className="label" htmlFor="full_name">Nome</label><Input id="full_name" autoComplete="name" {...register("full_name")} aria-invalid={Boolean(errors.full_name)} />{errors.full_name && <p className="mt-1.5 text-xs text-rust">{errors.full_name.message}</p>}</div>
          <div><label className="label" htmlFor="profile_email">E-mail</label><div className="relative"><Mail size={16} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="profile_email" value={user?.email ?? ""} className="pl-9" readOnly /></div><p className="mt-1.5 text-xs leading-5 text-muted">O e-mail de acesso não pode ser alterado nesta versão.</p></div>
          <div><label className="label" htmlFor="timezone">Fuso horário</label><div className="relative"><Clock3 size={16} className="pointer-events-none absolute left-3 top-3.5 z-10 text-muted" /><Select id="timezone" className="pl-9" {...register("timezone")}><option value="America/Manaus">Manaus (GMT−04:00)</option><option value="America/Sao_Paulo">São Paulo (GMT−03:00)</option><option value="America/Belem">Belém (GMT−03:00)</option><option value="America/Rio_Branco">Rio Branco (GMT−05:00)</option><option value="UTC">UTC</option></Select></div>{errors.timezone && <p className="mt-1.5 text-xs text-rust">{errors.timezone.message}</p>}</div>
          {profileError && <div role="alert" className="rounded-xl border border-rust/20 bg-rust/5 px-3 py-2.5 text-sm text-rust">{profileError}</div>}
          {profileNotice && <div role="status" className="flex items-center gap-2 rounded-xl border border-moss/20 bg-mint/35 px-3 py-2.5 text-sm text-moss"><Check size={15} /> {profileNotice}</div>}
          <Button type="submit" disabled={isSubmitting}>{isSubmitting ? "Salvando…" : <>Salvar alterações <ArrowRight size={15} /></>}</Button>
        </form>
      </Card>

      <Card>
        <CardHeader>
          <div><CardTitle>Meu diagnóstico</CardTitle><CardDescription>Revise ou atualize as respostas do seu diagnóstico financeiro.</CardDescription></div>
          <ClipboardCheck size={19} className="text-brand-brown" />
        </CardHeader>
        <div className="px-5 pb-6 md:px-6"><div className="flex items-center justify-between rounded-xl bg-brand-pink-soft p-4"><div><p className="text-sm font-semibold text-ink">{diagnosticLabel}</p><p className="mt-1 text-sm text-muted">{diagnostic ? `${diagnostic.completion_percent}% preenchido` : "Carregando status…"}</p></div><Badge tone={diagnostic?.status === "completed" ? "positive" : "warning"}>{diagnosticLabel}</Badge></div><Link href="/diagnostico" className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-brand-brown hover:text-brand-brown-dark">{diagnostic?.status === "completed" ? "Editar diagnóstico" : "Continuar diagnóstico"}<ArrowRight size={15} /></Link></div>
      </Card>

      <Card>
        <CardHeader><div><CardTitle>Segurança</CardTitle><CardDescription>Como o Organiza Finanças protege o acesso.</CardDescription></div><LockKeyhole size={19} className="text-moss" /></CardHeader>
        <div className="space-y-4 px-5 pb-6 md:px-6"><div className="rounded-xl bg-mint/35 p-4"><p className="text-sm font-semibold text-ink">Sessão segura</p><p className="mt-1 text-sm leading-6 text-muted">Sua senha não fica armazenada em texto aberto e seu acesso é mantido de forma protegida.</p></div><div className="rounded-xl bg-paper p-4"><p className="text-sm font-semibold text-ink">Seu espaço é privado</p><p className="mt-1 text-sm leading-6 text-muted">Você vê apenas suas próprias contas, categorias, transações, metas e orçamentos.</p></div></div>
      </Card>
    </div>
  </>;
}
