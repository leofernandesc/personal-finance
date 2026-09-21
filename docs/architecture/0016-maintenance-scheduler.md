# ADR 0016 — Scheduler explícito para retenção operacional

## Contexto

A limpeza de sessões, desafios e logs técnicos já existe como comando explícito
e seguro por padrão. Sem um scheduler documentado, a operação dependeria de
comandos manuais ou de um processo externo não versionado.

## Decisão

O repositório passa a fornecer unidades opcionais `systemd --user` em
`ops/systemd/`:

- um serviço `oneshot` chama `python -m app.maintenance --apply`;
- um timer semanal agenda o serviço com `Persistent=true` e atraso aleatório;
- o serviço usa o `.env` do repositório, o virtualenv do backend e não depende
  do Hermes, Ollama ou frontend.

As unidades são somente referência versionada. Elas não são instaladas nem
ativadas pelo Docker Compose, pelo Makefile ou por scripts de inicialização.

## Consequências

- O procedimento de operação fica reproduzível e auditável.
- A ativação continua uma decisão explícita do operador, depois de backup,
  teste de restauração e revisão da política de retenção.
- Ambientes sem systemd podem continuar usando `make maintenance-check` e
  `make maintenance-cleanup` por um scheduler equivalente.
