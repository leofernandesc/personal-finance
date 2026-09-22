"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Mail } from "lucide-react";
import { AuthFrame } from "@/components/auth-frame";
import { useAuth } from "@/components/auth-provider";
import { PasswordField } from "@/components/password-field";
import { Button, Input } from "@/components/ui";
import { ApiError } from "@/lib/api";

const schema = z.object({ email: z.string().trim().email("Digite um e-mail válido."), password: z.string().min(1, "Digite sua senha.").max(128, "Use até 128 caracteres.") });
type FormValues = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const { user, loading, signIn } = useAuth();
  const [error, setError] = React.useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema) });

  React.useEffect(() => { if (!loading && user) router.replace("/dashboard"); }, [loading, router, user]);

  const onSubmit = async (values: FormValues) => {
    setError(null);
    try { await signIn(values.email, values.password); router.replace("/dashboard"); }
    catch (reason) { setError(reason instanceof ApiError ? reason.message : "Não foi possível entrar agora."); }
  };

  return <AuthFrame mode="login">
    <div className="mb-8"><p className="eyebrow">Bem-vindo de volta</p><h1 className="mt-3 font-display text-4xl tracking-[-0.04em]">Entre na sua conta</h1><p className="mt-3 text-sm leading-6 text-muted">Retome o controle do seu mês com uma visão simples e honesta.</p></div>
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
      <div><label className="label" htmlFor="email">E-mail</label><div className="relative"><Mail size={17} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="email" type="email" placeholder="voce@email.com" className="pl-10" autoComplete="email" required aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "email-error" : undefined} {...register("email")} /></div>{errors.email && <p id="email-error" className="mt-1.5 text-xs text-rust">{errors.email.message}</p>}</div>
      <div><label className="label" htmlFor="password">Senha</label><PasswordField id="password" placeholder="Sua senha" autoComplete="current-password" toggleLabel="a senha" required aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "password-error" : undefined} {...register("password")} />{errors.password && <p id="password-error" className="mt-1.5 text-xs text-rust">{errors.password.message}</p>}</div>
      {error && <div role="alert" className="rounded-xl border border-rust/20 bg-rust/5 px-3 py-2.5 text-sm text-rust">{error}</div>}
      <Button type="submit" className="w-full" disabled={isSubmitting}>{isSubmitting ? "Entrando…" : <>Entrar na conta <ArrowRight size={16} /></>}</Button>
    </form>
    <p className="mt-8 text-center text-sm text-muted">Ainda não tem uma conta? <Link className="font-semibold text-navy underline decoration-mint decoration-2 underline-offset-4" href="/register">Criar agora</Link></p>
  </AuthFrame>;
}
