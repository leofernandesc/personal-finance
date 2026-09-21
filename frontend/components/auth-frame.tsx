import Link from "next/link";
import { ArrowUpRight, ShieldCheck } from "lucide-react";
import { BrandLogo } from "@/components/brand";

export function AuthFrame({ children, mode }: { children: React.ReactNode; mode: "login" | "register" }) {
  return (
    <main className="grid min-h-screen bg-white lg:grid-cols-[0.9fr_1.1fr]">
      <section className="relative hidden overflow-hidden border-r border-line bg-white px-12 py-12 text-ink lg:flex lg:flex-col">
        <div className="absolute -right-28 -top-28 h-80 w-80 rounded-full border border-brand-pink/45" />
        <div className="absolute -bottom-40 -left-24 h-96 w-96 rounded-full border border-brand-pink/30" />
        <Link href="/" className="relative flex items-center gap-3">
          <BrandLogo size="auth" priority />
        </Link>
        <div className="relative mt-auto max-w-md pb-10">
          <p className="mb-5 text-xs font-semibold uppercase tracking-[0.2em] text-brand-brown">Menos ruído. Mais direção.</p>
          <h1 className="font-display text-5xl leading-[0.98] tracking-[-0.045em] text-brand-brown-dark">Sua vida financeira, no seu ritmo.</h1>
          <p className="mt-6 max-w-sm text-sm leading-7 text-muted">Um lugar calmo para entender o que entrou, o que saiu e o que você quer construir a seguir.</p>
          <div className="mt-10 flex items-center gap-2 text-xs text-muted"><ShieldCheck size={16} className="text-brand-brown" /> Seus dados ficam separados por usuário e protegidos.</div>
        </div>
        <div className="relative flex items-center gap-2 text-xs text-muted">Feito para clareza <ArrowUpRight size={14} /></div>
      </section>
      <section className="flex min-h-screen items-center justify-center px-5 py-10 md:px-10" aria-label={mode === "register" ? "Criar conta" : "Entrar"}>
        <div className="w-full max-w-[430px]">
          <div className="mb-8 lg:hidden"><BrandLogo size="mobile" priority /></div>
          {children}
          <p className="mt-10 text-center text-xs leading-5 text-muted">Ao continuar, você concorda em usar o Organiza Finanças apenas para organizar suas próprias informações financeiras.</p>
        </div>
      </section>
    </main>
  );
}
