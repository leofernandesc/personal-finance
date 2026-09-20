import { ArrowUpRight, Plus, RefreshCw, SearchX, WalletMinimal } from "lucide-react";
import { Button, Card, Spinner } from "@/components/ui";

export function PageHeader({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: React.ReactNode }) {
  return <div className="mb-8 flex flex-col gap-5 md:flex-row md:items-end md:justify-between"><div>{eyebrow && <p className="eyebrow">{eyebrow}</p>}<h1 className="page-title mt-2">{title}</h1>{description && <p className="mt-3 max-w-2xl text-sm leading-6 text-muted">{description}</p>}</div>{action && <div className="shrink-0">{action}</div>}</div>;
}

export function LoadingState({ label = "Carregando seus dados" }: { label?: string }) {
  return <Card className="flex min-h-52 items-center justify-center"><div className="flex items-center gap-3 text-sm text-muted"><Spinner /> {label}…</div></Card>;
}

export function ErrorState({ message = "Não conseguimos carregar isso agora.", onRetry }: { message?: string; onRetry?: () => void }) {
  return <Card className="flex min-h-52 flex-col items-center justify-center px-6 text-center"><div className="mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-rust/10 text-rust"><RefreshCw size={18} /></div><p className="text-sm font-semibold text-ink">Algo saiu do eixo.</p><p className="mt-1 max-w-xs text-sm leading-6 text-muted">{message}</p>{onRetry && <Button variant="secondary" size="small" className="mt-5" onClick={onRetry}><RefreshCw size={14} /> Tentar novamente</Button>}</Card>;
}

export function EmptyState({ title, description, actionLabel = "Registrar agora", onAction, compact = false }: { title: string; description: string; actionLabel?: string; onAction?: () => void; compact?: boolean }) {
  return <div className={`flex flex-col items-center justify-center text-center ${compact ? "min-h-40 px-4" : "min-h-64 px-6"}`}><div className="mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-mint/55 text-moss"><WalletMinimal size={21} /></div><p className="font-display text-xl tracking-[-0.02em] text-ink">{title}</p><p className="mt-2 max-w-sm text-sm leading-6 text-muted">{description}</p>{onAction && <Button size="small" className="mt-5" onClick={onAction}><Plus size={15} /> {actionLabel}</Button>}</div>;
}

export function InlineLink({ children, href }: { children: React.ReactNode; href: string }) {
  return <a href={href} className="inline-flex items-center gap-1 text-xs font-semibold text-moss hover:text-navy">{children}<ArrowUpRight size={13} /></a>;
}

export function SearchEmpty() {
  return <div className="flex min-h-40 flex-col items-center justify-center text-center text-muted"><SearchX size={20} /><p className="mt-2 text-sm">Nenhum resultado com esses filtros.</p></div>;
}
