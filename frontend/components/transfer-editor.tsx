"use client";

import { useEffect, useMemo, useState } from "react";
import { ArrowLeftRight, Check, X } from "lucide-react";
import { api } from "@/lib/api";
import type { Account, Transfer } from "@/lib/types";
import { normalizeMoneyInput, todayForTimezone } from "@/lib/utils";
import { Button, Input, Select, Spinner } from "@/components/ui";

export function TransferEditor({
  accounts,
  transfer,
  timezone,
  onSaved,
  onCancel,
}: {
  accounts: Account[];
  transfer?: Transfer | null;
  timezone?: string;
  onSaved: () => void;
  onCancel: () => void;
}) {
  const activeAccounts = useMemo(
    () => accounts.filter((account) => account.is_active),
    [accounts],
  );
  const [sourceAccountId, setSourceAccountId] = useState(transfer?.source_account_id || activeAccounts[0]?.id || "");
  const [destinationAccountId, setDestinationAccountId] = useState(transfer?.destination_account_id || activeAccounts[1]?.id || "");
  const [amount, setAmount] = useState(transfer?.amount || "");
  const [description, setDescription] = useState(transfer?.description || "Transferência");
  const [transactionDate, setTransactionDate] = useState(transfer?.transaction_date || todayForTimezone(timezone));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!sourceAccountId && activeAccounts[0]) setSourceAccountId(activeAccounts[0].id);
    if (
      !destinationAccountId
      || destinationAccountId === sourceAccountId
      || !activeAccounts.some((account) => account.id === destinationAccountId)
    ) {
      const destination = activeAccounts.find((account) => account.id !== sourceAccountId);
      if (destination) setDestinationAccountId(destination.id);
    }
  }, [activeAccounts, destinationAccountId, sourceAccountId]);

  const submit = async () => {
    setSaving(true);
    setError(null);
    try {
      const normalizedAmount = normalizeMoneyInput(amount);
      if (activeAccounts.length < 2) throw new Error("Cadastre pelo menos duas contas ativas para transferir.");
      if (!sourceAccountId || !destinationAccountId) throw new Error("Escolha as contas de origem e destino.");
      if (sourceAccountId === destinationAccountId) throw new Error("Origem e destino devem ser diferentes.");
      if (!normalizedAmount || Number(normalizedAmount) <= 0) throw new Error("Informe um valor monetário válido maior que zero.");
      const payload = {
        source_account_id: sourceAccountId,
        destination_account_id: destinationAccountId,
        amount: normalizedAmount,
        description: description.trim() || "Transferência",
        transaction_date: transactionDate,
      };
      if (transfer) await api.updateTransfer(transfer.id, payload);
      else await api.createTransfer(payload);
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível realizar a transferência.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="rounded-card border border-navy/15 bg-[#fbfcfa] p-5 shadow-card md:p-6">
      <div className="mb-5 flex items-start justify-between">
        <div>
          <p className="eyebrow">{transfer ? "Editar transferência" : "Entre suas contas"}</p>
          <h2 className="mt-1 font-display text-2xl tracking-[-0.03em]">Mover sem alterar seu patrimônio.</h2>
        </div>
        <button onClick={onCancel} className="rounded-lg p-2 text-muted hover:bg-paper" aria-label="Fechar formulário de transferência">
          <X size={18} />
        </button>
      </div>

      <div className="mb-5 flex items-center gap-3 rounded-xl bg-butter/35 px-4 py-3 text-sm text-[#62591d]">
        <ArrowLeftRight size={17} />
        Transferências não entram como receita nem como despesa.
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label className="label" htmlFor="transfer-source">Sai de</label>
          <Select id="transfer-source" value={sourceAccountId} onChange={(event) => setSourceAccountId(event.target.value)}>
            <option value="">Selecione a origem</option>
            {activeAccounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
          </Select>
        </div>
        <div>
          <label className="label" htmlFor="transfer-destination">Entra em</label>
          <Select id="transfer-destination" value={destinationAccountId} onChange={(event) => setDestinationAccountId(event.target.value)}>
            <option value="">Selecione o destino</option>
            {activeAccounts.filter((account) => account.id !== sourceAccountId).map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}
          </Select>
        </div>
        <div>
          <label className="label" htmlFor="transfer-description">Descrição</label>
          <Input id="transfer-description" value={description} onChange={(event) => setDescription(event.target.value)} maxLength={255} />
        </div>
        <div>
          <label className="label" htmlFor="transfer-amount">Valor</label>
          <div className="relative">
            <span className="absolute left-3 top-3 text-sm text-muted">R$</span>
            <Input id="transfer-amount" inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="0,00" className="pl-10" />
          </div>
        </div>
        <div>
          <label className="label" htmlFor="transfer-date">Data</label>
          <Input id="transfer-date" type="date" value={transactionDate} onChange={(event) => setTransactionDate(event.target.value)} />
        </div>
      </div>

      {error && <p role="alert" className="mt-4 rounded-xl border border-rust/20 bg-rust/5 px-3 py-2.5 text-sm text-rust">{error}</p>}
      <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <Button type="button" variant="quiet" className="w-full sm:w-auto" onClick={onCancel}>Cancelar</Button>
        <Button type="button" className="w-full sm:w-auto" onClick={() => void submit()} disabled={saving || activeAccounts.length < 2}>
          {saving ? <Spinner /> : <Check size={16} />} {saving ? "Salvando…" : transfer ? "Salvar alterações" : "Realizar transferência"}
        </Button>
      </div>
    </div>
  );
}
