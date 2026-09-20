import Link from "next/link";
import { ArrowUpRight, BookOpen, ShieldCheck } from "lucide-react";

export function AuthFrame({ children, mode }: { children: React.ReactNode; mode: "login" | "register" }) {
  return (
    <main className="grid min-h-screen bg-paper lg:grid-cols-[0.9fr_1.1fr]">
      <section className="relative hidden overflow-hidden bg-navy px-12 py-12 text-white lg:flex lg:flex-col">
        <div className="absolute -right-28 -top-28 h-80 w-80 rounded-full border border-white/10" />
        <div className="absolute -bottom-40 -left-24 h-96 w-96 rounded-full border border-mint/10" />
        <Link href="/" className="relative flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-mint text-navy"><BookOpen size={19} /></span>
          <span><span className="block font-display text-2xl leading-none">norte</span><span className="mt-1 block text-[0.58rem] font-semibold uppercase tracking-[0.18em] text-white/50">finanças pessoais</span></span>
        </Link>
        <div className="relative mt-auto max-w-md pb-10">
          <p className="mb-5 text-xs font-semibold uppercase tracking-[0.2em] text-mint">Menos ruído. Mais direção.</p>
          <h1 className="font-display text-5xl leading-[0.98] tracking-[-0.045em] text-white">Sua vida financeira, no seu ritmo.</h1>
          <p className="mt-6 max-w-sm text-sm leading-7 text-white/65">Um lugar calmo para entender o que entrou, o que saiu e o que você quer construir a seguir.</p>
          <div className="mt-10 flex items-center gap-2 text-xs text-white/50"><ShieldCheck size={16} className="text-mint" /> Seus dados ficam separados por usuário e protegidos.</div>
        </div>
        <div className="relative flex items-center gap-2 text-xs text-white/40">Feito para clareza <ArrowUpRight size={14} /></div>
      </section>
      <section className="flex min-h-screen items-center justify-center px-5 py-10 md:px-10">
        <div className="w-full max-w-[430px]">
          <div className="mb-8 lg:hidden"><span className="font-display text-2xl tracking-[-0.03em]">norte</span><span className="ml-2 text-[0.58rem] font-semibold uppercase tracking-[0.18em] text-muted">finanças pessoais</span></div>
          {children}
          <p className="mt-10 text-center text-xs leading-5 text-muted">Ao continuar, você concorda em usar o Norte apenas para organizar suas próprias informações financeiras.</p>
        </div>
      </section>
    </main>
  );
}
