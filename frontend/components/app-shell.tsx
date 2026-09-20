"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";
import {
  BarChart3,
  BookOpen,
  ChevronDown,
  CircleDollarSign,
  LayoutDashboard,
  LogOut,
  Menu,
  PiggyBank,
  ReceiptText,
  Settings,
  Target,
  Tags,
  WalletCards,
  X,
  type LucideIcon,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { Badge, Button } from "@/components/ui";
import { initials } from "@/lib/utils";

type NavItem = { href: string; label: string; icon: LucideIcon };

const primaryNav: NavItem[] = [
  { href: "/dashboard", label: "Visão geral", icon: LayoutDashboard },
  { href: "/transactions", label: "Transações", icon: ReceiptText },
  { href: "/accounts", label: "Contas", icon: WalletCards },
  { href: "/budgets", label: "Orçamentos", icon: PiggyBank },
  { href: "/goals", label: "Metas", icon: Target },
];

const secondaryNav: NavItem[] = [
  { href: "/categories", label: "Categorias", icon: Tags },
  { href: "/reports", label: "Relatórios", icon: BarChart3 },
  { href: "/integrations", label: "Integrações", icon: CircleDollarSign },
  { href: "/settings", label: "Configurações", icon: Settings },
];

function NavLink({ item, onNavigate }: { item: NavItem; onNavigate?: () => void }) {
  const pathname = usePathname();
  const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(`${item.href}/`));
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      onClick={onNavigate}
      className={`group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition ${active ? "bg-navy text-white" : "text-muted hover:bg-paper hover:text-ink"}`}
      aria-current={active ? "page" : undefined}
    >
      <Icon size={17} strokeWidth={active ? 2.2 : 1.8} />
      <span>{item.label}</span>
    </Link>
  );
}

function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const { user, signOut } = useAuth();
  const router = useRouter();
  const doSignOut = async () => {
    await signOut();
    router.replace("/login");
  };
  return (
    <aside className="flex h-full w-[248px] shrink-0 flex-col border-r border-line bg-white px-4 py-5">
      <Link href="/dashboard" className="mb-9 flex items-center gap-3 px-3" onClick={onNavigate}>
        <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-navy text-white">
          <BookOpen size={18} strokeWidth={1.8} />
        </span>
        <span>
          <span className="block font-display text-xl leading-none tracking-[-0.03em]">norte</span>
          <span className="mt-1 block text-[0.58rem] font-semibold uppercase tracking-[0.18em] text-muted">finanças pessoais</span>
        </span>
      </Link>

      <nav aria-label="Navegação principal" className="space-y-1">
        <p className="mb-3 px-3 text-[0.62rem] font-semibold uppercase tracking-[0.17em] text-muted/70">Seu dinheiro</p>
        {primaryNav.map((item) => <NavLink key={item.href} item={item} onNavigate={onNavigate} />)}
      </nav>
      <nav aria-label="Navegação secundária" className="mt-8 space-y-1">
        <p className="mb-3 px-3 text-[0.62rem] font-semibold uppercase tracking-[0.17em] text-muted/70">Organizar</p>
        {secondaryNav.map((item) => <NavLink key={item.href} item={item} onNavigate={onNavigate} />)}
      </nav>

      <div className="mt-auto border-t border-line pt-4">
        <div className="mb-2 flex items-center gap-3 rounded-xl px-3 py-2.5">
          <span className="flex h-8 w-8 items-center justify-center rounded-full bg-mint text-xs font-bold text-moss">{initials(user?.full_name || "Você")}</span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-ink">{user?.full_name || "Sua conta"}</p>
            <p className="truncate text-xs text-muted">{user?.email}</p>
          </div>
          <ChevronDown size={14} className="text-muted" />
        </div>
        <Button variant="quiet" size="small" className="w-full justify-start" onClick={doSignOut}>
          <LogOut size={15} /> Sair
        </Button>
      </div>
    </aside>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = useState(false);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-paper"><div className="h-8 w-8 animate-spin rounded-full border-2 border-navy border-t-transparent" /></div>;
  }
  if (!user) {
    if (typeof window !== "undefined") router.replace("/login");
    return null;
  }

  return (
    <div className="min-h-screen bg-paper">
      <div className="fixed inset-y-0 left-0 z-40 hidden lg:flex"><Sidebar /></div>
      {mobileOpen && <div className="fixed inset-0 z-40 bg-ink/20 backdrop-blur-[2px] lg:hidden" onClick={() => setMobileOpen(false)} aria-hidden="true" />}
      <div className={`fixed inset-y-0 left-0 z-50 flex transition-transform lg:hidden ${mobileOpen ? "translate-x-0" : "-translate-x-full"}`}>
        <Sidebar onNavigate={() => setMobileOpen(false)} />
        <button className="absolute left-[258px] top-5 rounded-full bg-white p-2 text-muted shadow" onClick={() => setMobileOpen(false)} aria-label="Fechar menu"><X size={16} /></button>
      </div>
      <main className="lg:pl-[248px]">
        <header className="sticky top-0 z-30 flex h-[70px] items-center justify-between border-b border-line/80 bg-paper/90 px-5 backdrop-blur md:px-8 lg:px-10">
          <button className="rounded-lg p-2 text-muted hover:bg-white lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Abrir menu"><Menu size={20} /></button>
          <div className="hidden text-sm text-muted lg:block">Controle claro para decisões melhores.</div>
          <div className="ml-auto flex items-center gap-3">
            <Badge tone="whatsapp" className="hidden sm:inline-flex"><span className="mr-1.5 h-1.5 w-1.5 rounded-full bg-[#2e9a61]" /> WhatsApp conectado</Badge>
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy text-xs font-bold text-white lg:hidden">{initials(user.full_name)}</span>
          </div>
        </header>
        <div className="mx-auto max-w-[1440px] px-5 py-8 md:px-8 lg:px-10 lg:py-10">{children}</div>
      </main>
    </div>
  );
}
