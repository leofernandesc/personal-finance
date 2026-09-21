"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Clock3, LockKeyhole, Mail, UserRound } from "lucide-react";
import { AuthFrame } from "@/components/auth-frame";
import { useAuth } from "@/components/auth-provider";
import { Button, Input, Select } from "@/components/ui";
import { ApiError } from "@/lib/api";

const schema = z.object({
  full_name: z.string().max(120),
  email: z.string().email("Digite um e-mail válido."),
  password: z.string().min(8, "Use pelo menos 8 caracteres."),
  timezone: z.string().min(1),
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const { user, loading, signUp } = useAuth();
  const [error, setError] = React.useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { timezone: "America/Manaus" } });
  React.useEffect(() => { if (!loading && user) router.replace("/dashboard"); }, [loading, router, user]);
  const onSubmit = async (values: FormValues) => {
    setError(null);
    try { await signUp(values); router.replace("/diagnostico?inicio=1"); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "Não foi possível criar sua conta."); }
  };
  return <AuthFrame mode="register">
    <div className="mb-8"><p className="eyebrow">Comece leve</p><h1 className="mt-3 font-display text-4xl tracking-[-0.04em]">Crie seu espaço</h1><p className="mt-3 text-sm leading-6 text-muted">Em poucos passos, você já pode registrar o primeiro movimento.</p></div>
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div><label className="label" htmlFor="full_name">Como podemos chamar você?</label><div className="relative"><UserRound size={17} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="full_name" placeholder="Seu nome" className="pl-10" autoComplete="name" {...register("full_name")} /></div></div>
      <div><label className="label" htmlFor="email">E-mail</label><div className="relative"><Mail size={17} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="email" type="email" placeholder="voce@email.com" className="pl-10" autoComplete="email" {...register("email")} /></div>{errors.email && <p className="mt-1.5 text-xs text-rust">{errors.email.message}</p>}</div>
      <div><label className="label" htmlFor="password">Senha</label><div className="relative"><LockKeyhole size={17} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="password" type="password" placeholder="Mínimo de 8 caracteres" className="pl-10" autoComplete="new-password" {...register("password")} /></div>{errors.password && <p className="mt-1.5 text-xs text-rust">{errors.password.message}</p>}</div>
      <div><label className="label" htmlFor="timezone">Seu fuso horário</label><div className="relative"><Clock3 size={17} className="pointer-events-none absolute left-3 top-3.5 z-10 text-muted" /><Select id="timezone" className="pl-10" {...register("timezone")}><option value="America/Manaus">Manaus (GMT−04:00)</option><option value="America/Sao_Paulo">São Paulo (GMT−03:00)</option><option value="America/Belem">Belém (GMT−03:00)</option><option value="America/Rio_Branco">Rio Branco (GMT−05:00)</option><option value="UTC">UTC</option></Select></div></div>
      {error && <div role="alert" className="rounded-xl border border-rust/20 bg-rust/5 px-3 py-2.5 text-sm text-rust">{error}</div>}
      <Button type="submit" className="mt-2 w-full" disabled={isSubmitting}>{isSubmitting ? "Criando seu espaço…" : <>Criar minha conta <ArrowRight size={16} /></>}</Button>
    </form>
    <p className="mt-8 text-center text-sm text-muted">Já tem uma conta? <Link className="font-semibold text-navy underline decoration-mint decoration-2 underline-offset-4" href="/login">Entrar</Link></p>
  </AuthFrame>;
}
