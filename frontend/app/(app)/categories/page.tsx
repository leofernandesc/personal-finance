"use client";

import { useCallback, useEffect, useState } from "react";
import { Check, ChevronDown, ChevronRight, Edit3, Plus, Tags } from "lucide-react";
import { EmptyState, ErrorState, LoadingState, PageHeader } from "@/components/page";
import { Button, Card, Input, Select, Spinner } from "@/components/ui";
import { api } from "@/lib/api";
import type { Category } from "@/lib/types";

export default function CategoriesPage() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [kind, setKind] = useState("expense");
  const [parentId, setParentId] = useState("");
  const [saving, setSaving] = useState(false);
  const load = useCallback(async () => { setLoading(true); setError(null); try { setCategories(await api.categories()); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível carregar as categorias."); } finally { setLoading(false); } }, []);
  useEffect(() => { void load(); }, [load]);
  const create = async () => { setSaving(true); setError(null); try { if (!name.trim()) throw new Error("Dê um nome para a categoria."); await api.createCategory({ name: name.trim(), kind, parent_id: parentId || null }); setName(""); setParentId(""); setFormOpen(false); await load(); } catch (reason) { setError(reason instanceof Error ? reason.message : "Não foi possível criar a categoria."); } finally { setSaving(false); } };
  const roots = categories.filter((category) => !category.parent_id);
  return <>
    <PageHeader eyebrow="Dar nome ajuda a enxergar" title="Categorias" description="Organize suas despesas e receitas do jeito que faz sentido para sua vida." action={<Button onClick={() => setFormOpen((value) => !value)}><Plus size={17} /> Nova categoria</Button>} />
    {formOpen && <Card className="mb-6 border-navy/15 bg-[#fbfcfa] p-5 md:p-6"><div className="mb-5"><p className="eyebrow">Personalizar seu mapa</p><h2 className="mt-1 font-display text-2xl tracking-[-0.03em]">Que tipo de movimento é este?</h2></div><div className="grid gap-4 md:grid-cols-3"><div><label className="label" htmlFor="category-name">Nome</label><Input id="category-name" value={name} onChange={(event) => setName(event.target.value)} placeholder="Ex.: Pets" /></div><div><label className="label" htmlFor="category-kind">Natureza</label><Select id="category-kind" value={kind} onChange={(event) => setKind(event.target.value)}><option value="expense">Despesa</option><option value="income">Receita</option><option value="both">Ambas</option></Select></div><div><label className="label" htmlFor="category-parent">Dentro de <span className="normal-case tracking-normal text-muted/70">(opcional)</span></label><Select id="category-parent" value={parentId} onChange={(event) => setParentId(event.target.value)}><option value="">Categoria principal</option>{roots.filter((category) => category.kind === kind || category.kind === "both" || kind === "both").map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</Select></div></div>{error && <p className="mt-4 text-sm text-rust">{error}</p>}<div className="mt-5 flex justify-end gap-2"><Button variant="quiet" onClick={() => setFormOpen(false)}>Cancelar</Button><Button onClick={() => void create()} disabled={saving}>{saving ? <Spinner /> : <Check size={16} />} Criar categoria</Button></div></Card>}
    {loading ? <LoadingState label="Organizando categorias" /> : error && !categories.length ? <ErrorState message={error} onRetry={() => void load()} /> : !categories.length ? <Card><EmptyState title="Seu mapa ainda está vazio" description="Crie categorias que sejam úteis para a sua realidade — elas ajudam o dashboard a contar a história certa." actionLabel="Criar categoria" onAction={() => setFormOpen(true)} /></Card> : <Card className="overflow-hidden"><div className="border-b border-line bg-paper/50 px-5 py-3 text-[0.65rem] font-semibold uppercase tracking-[0.13em] text-muted md:px-6">Categorias ativas</div><div className="divide-y divide-line">{roots.map((root) => <CategoryRow key={root.id} category={root} children={categories.filter((child) => child.parent_id === root.id)} onUpdated={load} />)}</div></Card>}
  </>;
}

function CategoryRow({ category, children, onUpdated }: { category: Category; children: Category[]; onUpdated: () => Promise<void> }) {
  const [expanded, setExpanded] = useState(true);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(category.name);
  const [saving, setSaving] = useState(false);
  const save = async () => { setSaving(true); try { await api.updateCategory(category.id, { name }); setEditing(false); await onUpdated(); } finally { setSaving(false); } };
  const deactivate = async () => { if (!window.confirm(`Desativar a categoria “${category.name}”?`)) return; await api.updateCategory(category.id, { is_active: false }); await onUpdated(); };
  return <div><div className={`flex items-center gap-3 px-5 py-4 md:px-6 ${!category.is_active ? "opacity-50" : ""}`}>{children.length ? <button onClick={() => setExpanded((value) => !value)} className="rounded-md p-1 text-muted hover:bg-paper" aria-label={expanded ? "Recolher subcategorias" : "Expandir subcategorias"}>{expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</button> : <span className="w-6" />}<span className="flex h-9 w-9 items-center justify-center rounded-xl bg-mint/45 text-moss"><Tags size={16} /></span>{editing ? <Input value={name} onChange={(event) => setName(event.target.value)} className="h-9 max-w-xs" autoFocus /> : <div className="min-w-0 flex-1"><p className="text-sm font-semibold text-ink">{category.name}</p><p className="mt-0.5 text-xs text-muted">{category.kind === "expense" ? "Despesa" : category.kind === "income" ? "Receita" : "Receita e despesa"} · {children.length} subcategoria{children.length === 1 ? "" : "s"}</p></div>}<div className="flex gap-1">{editing ? <button onClick={() => void save()} className="rounded-lg p-2 text-moss hover:bg-mint/30" aria-label="Salvar categoria">{saving ? <Spinner /> : <Check size={16} />}</button> : <button onClick={() => setEditing(true)} className="rounded-lg p-2 text-muted hover:bg-paper hover:text-navy" aria-label="Editar categoria"><Edit3 size={15} /></button>}{!editing && category.is_active && <button onClick={() => void deactivate()} className="rounded-lg px-2 text-xs font-semibold text-muted hover:bg-rust/10 hover:text-rust">Desativar</button>}</div></div>{expanded && children.length > 0 && <div className="bg-paper/35 pb-2 pl-[4.5rem] pr-5 md:pl-[6.2rem] md:pr-6">{children.map((child) => <div key={child.id} className="flex items-center gap-2 border-t border-line/70 py-3 text-sm text-muted"><span className="h-1.5 w-1.5 rounded-full bg-moss/60" />{child.name}<span className="ml-auto text-[0.65rem] uppercase tracking-[0.1em] text-muted/70">{child.kind === "expense" ? "Despesa" : "Receita"}</span></div>)}</div>}</div>;
}
