"use client";

import React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { ArrowRight, Clock3, Mail, UserRound } from "lucide-react";
import { AuthFrame } from "@/components/auth-frame";
import { useAuth } from "@/components/auth-provider";
import { PasswordField } from "@/components/password-field";
import { Button, Input, Select } from "@/components/ui";
import { ApiError } from "@/lib/api";

const schema = z.object({
  full_name: z.string().trim().min(1, "Informe seu nome.").max(120, "Use até 120 caracteres."),
  email: z.string().trim().email("Digite um e-mail válido."),
  password: z.string().min(8, "Use pelo menos 8 caracteres.").max(128, "Use até 128 caracteres."),
  password_confirmation: z.string().min(1, "Confirme sua senha.").max(128, "Use até 128 caracteres."),
  timezone: z.string().min(1),
}).refine((values) => values.password === values.password_confirmation, {
  message: "As senhas não coincidem.",
  path: ["password_confirmation"],
});
type FormValues = z.infer<typeof schema>;

export default function RegisterPage() {
  const router = useRouter();
  const { user, loading, signUp } = useAuth();
  const [redirectingAfterRegistration, setRedirectingAfterRegistration] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormValues>({ resolver: zodResolver(schema), defaultValues: { timezone: "America/Manaus", password_confirmation: "" } });
  React.useEffect(() => {
    if (!loading && user && !redirectingAfterRegistration) router.replace("/dashboard");
  }, [loading, redirectingAfterRegistration, router, user]);
  const onSubmit = async (values: FormValues) => {
    setError(null);
    try {
      setRedirectingAfterRegistration(true);
      await signUp(values);
      router.replace("/diagnostico?inicio=1");
    }
    catch (reason) {
      setRedirectingAfterRegistration(false);
      setError(reason instanceof ApiError ? reason.message : "Não foi possível criar sua conta.");
    }
  };
  return <AuthFrame mode="register">
    <div className="mb-8"><p className="eyebrow">Comece leve</p><h1 className="mt-3 font-display text-4xl tracking-[-0.04em]">Crie seu espaço</h1><p className="mt-3 text-sm leading-6 text-muted">Em poucos passos, você já pode registrar o primeiro movimento.</p></div>
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
      <div><label className="label" htmlFor="full_name">Como podemos chamar você?</label><div className="relative"><UserRound size={17} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="full_name" placeholder="Seu nome" className="pl-10" autoComplete="name" required aria-invalid={Boolean(errors.full_name)} aria-describedby={errors.full_name ? "full-name-error" : undefined} {...register("full_name")} /></div>{errors.full_name && <p id="full-name-error" className="mt-1.5 text-xs text-rust">{errors.full_name.message}</p>}</div>
      <div><label className="label" htmlFor="email">E-mail</label><div className="relative"><Mail size={17} className="pointer-events-none absolute left-3 top-3.5 text-muted" /><Input id="email" type="email" placeholder="voce@email.com" className="pl-10" autoComplete="email" required aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? "email-error" : undefined} {...register("email")} /></div>{errors.email && <p id="email-error" className="mt-1.5 text-xs text-rust">{errors.email.message}</p>}</div>
      <div><label className="label" htmlFor="password">Senha</label><PasswordField id="password" placeholder="Mínimo de 8 caracteres" autoComplete="new-password" toggleLabel="a senha" required aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? "password-error" : undefined} {...register("password")} />{errors.password && <p id="password-error" className="mt-1.5 text-xs text-rust">{errors.password.message}</p>}</div>
      <div><label className="label" htmlFor="password_confirmation">Confirme sua senha</label><PasswordField id="password_confirmation" placeholder="Digite a mesma senha novamente" autoComplete="new-password" toggleLabel="a confirmação da senha" required aria-invalid={Boolean(errors.password_confirmation)} aria-describedby={errors.password_confirmation ? "password-confirmation-error" : undefined} {...register("password_confirmation")} />{errors.password_confirmation && <p id="password-confirmation-error" className="mt-1.5 text-xs text-rust">{errors.password_confirmation.message}</p>}</div>
      <div><label className="label" htmlFor="timezone">Seu fuso horário</label><div className="relative"><Clock3 size={17} className="pointer-events-none absolute left-3 top-3.5 z-10 text-muted" /><Select id="timezone" className="pl-10" required {...register("timezone")}><option value="America/Manaus">Manaus (GMT−04:00)</option><option value="America/Sao_Paulo">São Paulo (GMT−03:00)</option><option value="America/Belem">Belém (GMT−03:00)</option><option value="America/Rio_Branco">Rio Branco (GMT−05:00)</option><option value="UTC">UTC</option></Select></div></div>
      {error && <div role="alert" className="rounded-xl border border-rust/20 bg-rust/5 px-3 py-2.5 text-sm text-rust">{error}</div>}
      <Button type="submit" className="mt-2 w-full" disabled={isSubmitting}>{isSubmitting ? "Criando seu espaço…" : <>Criar minha conta <ArrowRight size={16} /></>}</Button>
    </form>
    <p className="mt-8 text-center text-sm text-muted">Já tem uma conta? <Link className="font-semibold text-navy underline decoration-mint decoration-2 underline-offset-4" href="/login">Entrar</Link></p>
  </AuthFrame>;
}
