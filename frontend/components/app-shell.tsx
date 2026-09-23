"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import {
  BarChart3,
  ChevronDown,
  ClipboardCheck,
  CircleDollarSign,
  LayoutDashboard,
  LogOut,
  Menu,
  MessageCircle,
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
import { BrandLogo } from "@/components/brand";
import { Badge, Button } from "@/components/ui";
import { api } from "@/lib/api";
import type { Diagnostic, WhatsAppIdentity } from "@/lib/types";
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
  { href: "/diagnostico", label: "Meu diagnóstico", icon: ClipboardCheck },
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
  const { user } = useAuth();
  return (
    <aside className="flex h-full w-[248px] shrink-0 flex-col border-r border-line bg-white px-4 py-5">
      <Link href="/dashboard" className="mb-9 flex items-center px-3" onClick={onNavigate}>
        <BrandLogo size="sidebar" priority />
      </Link>

      <nav aria-label="Navegação principal" className="space-y-1">
        <p className="mb-3 px-3 text-[0.62rem] font-semibold uppercase tracking-[0.17em] text-muted">Seu dinheiro</p>
        {primaryNav.map((item) => <NavLink key={item.href} item={item} onNavigate={onNavigate} />)}
      </nav>
      <nav aria-label="Navegação secundária" className="mt-8 space-y-1">
        <p className="mb-3 px-3 text-[0.62rem] font-semibold uppercase tracking-[0.17em] text-muted">Organizar</p>
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
        <SignOutButton onNavigate={onNavigate} className="w-full justify-start" />
      </div>
    </aside>
  );
}

function SignOutButton({ onNavigate, className = "" }: { onNavigate?: () => void; className?: string }) {
  const { signOut } = useAuth();
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);

  const doSignOut = async () => {
    setSigningOut(true);
    try {
      await signOut();
      onNavigate?.();
      router.replace("/login");
    } finally {
      setSigningOut(false);
    }
  };

  return <Button variant="secondary" size="small" className={className} onClick={doSignOut} disabled={signingOut} aria-label="Sair da conta">
    <LogOut size={15} /> <span>{signingOut ? "Saindo…" : "Sair"}</span>
  </Button>;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const mobileMenuRef = useRef<HTMLDivElement>(null);
  const mobileMenuTriggerRef = useRef<HTMLButtonElement>(null);
  const [whatsappIdentity, setWhatsAppIdentity] = useState<WhatsAppIdentity | null>(null);
  const [diagnostic, setDiagnostic] = useState<Diagnostic | null>(null);

  useEffect(() => {
    if (!user) {
      setWhatsAppIdentity(null);
      return;
    }
    const loadIdentity = () => {
      api.whatsappIdentity().then(setWhatsAppIdentity).catch(() => setWhatsAppIdentity(null));
    };
    loadIdentity();
    window.addEventListener("whatsapp-identity-changed", loadIdentity);
    return () => window.removeEventListener("whatsapp-identity-changed", loadIdentity);
  }, [user]);

  useEffect(() => {
    if (!user) {
      setDiagnostic(null);
      return;
    }
    const loadDiagnostic = () => {
      api.diagnostic().then(setDiagnostic).catch(() => setDiagnostic(null));
    };
    loadDiagnostic();
    window.addEventListener("diagnostic-changed", loadDiagnostic);
    return () => window.removeEventListener("diagnostic-changed", loadDiagnostic);
  }, [user]);

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, router, user]);

  useEffect(() => {
    if (!mobileOpen) return;

    const menu = mobileMenuRef.current;
    const menuTrigger = mobileMenuTriggerRef.current;
    if (!menu) return;

    const getFocusableElements = () => Array.from(
      menu.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      ),
    ).filter((element) => element.getClientRects().length > 0);

    getFocusableElements()[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        setMobileOpen(false);
        return;
      }
      if (event.key !== "Tab") return;

      const focusableElements = getFocusableElements();
      const first = focusableElements[0];
      const last = focusableElements.at(-1);
      if (!first || !last) {
        event.preventDefault();
        menu.focus();
        return;
      }

      if (event.shiftKey && (document.activeElement === first || !menu.contains(document.activeElement))) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !menu.contains(document.activeElement))) {
        event.preventDefault();
        first.focus();
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      menuTrigger?.focus();
    };
  }, [mobileOpen]);

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-paper"><div className="h-8 w-8 animate-spin rounded-full border-2 border-navy border-t-transparent" /></div>;
  }
  if (!user) {
    return null;
  }

  return (
    <div className="min-h-screen bg-paper">
      <div className="fixed inset-y-0 left-0 z-40 hidden lg:flex"><Sidebar /></div>
      {mobileOpen && <div className="fixed inset-0 z-40 bg-ink/20 backdrop-blur-[2px] lg:hidden" onClick={() => setMobileOpen(false)} aria-hidden="true" />}
      <div
        ref={mobileMenuRef}
        id="mobile-navigation-dialog"
        role="dialog"
        aria-label="Menu de navegação"
        aria-modal={mobileOpen}
        tabIndex={-1}
        className={`fixed inset-y-0 left-0 z-50 lg:hidden ${mobileOpen ? "flex" : "hidden"}`}
      >
        <Sidebar onNavigate={() => setMobileOpen(false)} />
        <button className="absolute left-[258px] top-5 rounded-full bg-white p-2 text-muted shadow" onClick={() => setMobileOpen(false)} aria-label="Fechar menu"><X size={16} /></button>
      </div>
      <main inert={mobileOpen} className="min-w-0 overflow-x-hidden lg:pl-[248px]">
        <header className="sticky top-0 z-30 flex h-[70px] items-center justify-between border-b border-line/80 bg-paper/90 px-5 backdrop-blur md:px-8 lg:px-10">
          <div className="flex items-center gap-3">
            <button ref={mobileMenuTriggerRef} className="rounded-lg p-2 text-muted hover:bg-brand-pink-soft lg:hidden" onClick={() => setMobileOpen(true)} aria-label="Abrir menu" aria-expanded={mobileOpen} aria-controls="mobile-navigation-dialog"><Menu size={20} /></button>
            <Link href="/dashboard" className="lg:hidden" aria-label="Ir para o dashboard"><BrandLogo size="mobile" priority /></Link>
          </div>
          <div className="hidden text-sm text-muted lg:block">Organize com clareza. Decida com calma.</div>
          <div className="ml-auto flex items-center gap-3">
            <Link href="/integrations" className="hidden sm:block" aria-label="Abrir integração do WhatsApp">
              <Badge tone={whatsappIdentity?.linked ? "whatsapp" : "neutral"}>
                <MessageCircle size={12} className="mr-1.5" />
                {whatsappIdentity?.linked ? "Número vinculado" : "Vincular WhatsApp"}
              </Badge>
            </Link>
            <SignOutButton className="inline-flex px-2 sm:px-3" />
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-navy text-xs font-bold text-white lg:hidden">{initials(user.full_name)}</span>
          </div>
        </header>
        <div className="mx-auto max-w-[1440px] px-4 py-6 sm:px-5 md:px-8 md:py-8 lg:px-10 lg:py-10">
          {diagnostic && diagnostic.status !== "completed" && pathname !== "/diagnostico" && <div className="mb-6 flex flex-col gap-3 rounded-2xl border border-brand-pink/50 bg-brand-pink-soft px-4 py-3 text-sm text-brand-brown-dark sm:flex-row sm:items-center sm:justify-between"><div><strong>Seu diagnóstico está {diagnostic.status === "draft" ? "em andamento" : "pendente"}.</strong><span className="ml-1 text-brand-brown/80">Você pode continuar quando quiser.</span></div><Link href="/diagnostico" className="font-semibold underline underline-offset-4">Continuar diagnóstico</Link></div>}
          {children}
        </div>
      </main>
    </div>
  );
}
