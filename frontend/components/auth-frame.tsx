import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { BrandLogo } from "@/components/brand";

export function AuthFrame({ children, mode }: { children: React.ReactNode; mode: "login" | "register" }) {
  return (
    <main className="relative flex min-h-screen flex-col overflow-hidden bg-[#fffafa] px-4 py-6 sm:px-6 md:py-8">
      <div className="pointer-events-none absolute -right-40 -top-40 h-[30rem] w-[30rem] rounded-full border border-brand-pink/35" aria-hidden="true" />
      <div className="pointer-events-none absolute -bottom-56 -left-40 h-[30rem] w-[30rem] rounded-full border border-brand-pink/25" aria-hidden="true" />

      <header className="relative z-10 mx-auto flex w-full max-w-6xl items-center justify-between">
        <Link href="/" className="rounded-lg focus-visible:outline-none" aria-label="Ir para a página inicial">
          <BrandLogo size="auth" className="w-[178px] sm:w-[205px]" priority />
        </Link>
        <p className="hidden text-sm text-muted sm:block">Clareza para cada decisão.</p>
      </header>

      <section className="relative z-10 flex flex-1 items-center justify-center py-12 sm:py-16" aria-label={mode === "register" ? "Criar conta" : "Entrar"}>
        <div className="w-full max-w-[458px]">
          <div className="rounded-[1.6rem] border border-line bg-white px-6 py-7 shadow-card sm:px-10 sm:py-9">
            {children}
            <p className="mt-9 text-center text-xs leading-5 text-muted">Ao continuar, você concorda em usar o Organiza Finanças apenas para organizar suas próprias informações financeiras.</p>
          </div>
          <div className="mx-auto mt-5 flex max-w-[360px] items-start justify-center gap-2 text-center text-xs leading-5 text-muted">
            <ShieldCheck size={15} className="mt-0.5 shrink-0 text-brand-brown" aria-hidden="true" />
            <span>Seus dados ficam separados por usuário e protegidos.</span>
          </div>
        </div>
      </section>

      <footer className="relative z-10 mx-auto w-full max-w-6xl text-center text-[0.68rem] text-muted">
        Organiza Finanças · Feito para organizar com calma
      </footer>
    </main>
  );
}
