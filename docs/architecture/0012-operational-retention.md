# ADR 0012 — Retenção operacional sem comprometer idempotência

## Contexto

O sistema cria sessões web, desafios temporários de posse do WhatsApp e ações
pendentes de confirmação. Também registra mensagens e chamadas técnicas do
agente. Esses dados não devem crescer sem controle, mas o registro da mensagem
que já criou uma transação ou transferência é necessário para impedir que uma
reentrega antiga gere um lançamento duplicado.

## Decisão

Foi criada uma rotina explícita em `app.maintenance`:

- sessões expiradas ou revogadas são removidas;
- `PendingAgentAction` é removido quando o prazo do token termina;
- logs do agente em estado concluído, sem vínculo com transação ou
  transferência, são removidos após `AGENT_LOG_RETENTION_DAYS` (180 dias por
  padrão);
- `AgentMessage` e `AgentToolCall` vinculados a uma transação ou transferência
  permanecem como ledger técnico de idempotência e auditoria;
- transações, transferências, saldos, contas e demais dados financeiros nunca
  são alvo da rotina.

A execução sem `--apply` é apenas simulação e imprime contagens. A remoção
exige uma chamada explícita com `--apply`, para evitar que um agendamento
acidental apague registros.

## Operação local

```bash
make maintenance-check
make maintenance-cleanup
```

O primeiro comando faz dry-run. O segundo aplica a remoção. Em produção, o
comando deve ser agendado por um scheduler controlado e com backup operacional
antes de definir a retenção definitiva.

## Consequências

O banco mantém permanentemente apenas os metadados técnicos necessários para
reconhecer reentregas que já produziram efeito financeiro. Consultas, falhas e
verificações antigas deixam de ocupar espaço depois do prazo definido. A
limpeza não depende do Hermes, Ollama ou WhatsApp e pode ser executada mesmo
quando esses processos estão desligados.
