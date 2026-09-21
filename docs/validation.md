# Validação do repositório

Este arquivo registra os comandos usados para verificar o MVP e separa código
validado de integrações que exigem um processo externo.

## Checks automatizados

Executar na raiz, salvo indicação contrária:

```bash
make check

cd backend
.venv/bin/alembic check
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/pytest -q
.venv/bin/ruff check ../agent
.venv/bin/ruff format --check ../agent

cd ..
PYTHONPATH=. backend/.venv/bin/pytest -q agent/tests
backend/.venv/bin/python -m compileall -q backend/app agent
hermes plugins doctor ./agent --ci

cd frontend
npm test
npm run lint
npm run typecheck
npm run build
npm audit --omit=dev --audit-level=high
```

Na revisão de 20/09/2026, passaram 28 testes de backend, 3 testes da fronteira
do agente e 17 testes de frontend. O backend cobre criação de receita/despesa,
transferências com duas pernas, saldo, orçamento, Decimal, timezone, isolamento
de usuário, idempotência, auditoria e fluxos HTTP. O plugin cobre o cliente HTTP,
a recusa de contexto sem idempotência e o conjunto esperado de 13 tools.

## Execução real local — 20/09/2026

Além da suíte automatizada, o ambiente local foi exercitado com PostgreSQL 16
no Docker Compose:

- `docker compose config --quiet` passou;
- backend, frontend e PostgreSQL foram reconstruídos e ficaram ativos; banco e
  API ficaram `healthy`, e o PostgreSQL aceitou as migrations Alembic;
- Alembic confirmou `0002_harden_financial_integrity (head)`;
- as migrations `0001 -> 0002` também foram aplicadas em um banco temporário
  vazio e `alembic check` não encontrou drift entre ORM e schema;
- o seed criou o usuário demo, contas, categorias, transações, orçamentos e
  meta;
- login por cookie, `GET /api/v1/dashboard` e o relatório de seis meses
  responderam pelo container FastAPI;
- readiness respondeu `ready`, OpenAPI expôs a versão 0.2.0 e 33 paths;
- `POST /integrations/whatsapp/link` vinculou um telefone de teste;
- `create_transaction` persistiu `Gasolina` de `R$ 50,00` com
  `source=whatsapp`;
- a mesma mensagem, com o mesmo ID externo, retornou `replayed=true` e o mesmo
  ID sem duplicar a despesa;
- `create_transfer` moveu `R$ 300,00` do Nubank para o Inter, com duas pernas
  e patrimônio total inalterado pela transferência;
- `get_month_summary` e `get_category_summary` retornaram os números calculados
  no backend;
- tools de sucesso e erro foram persistidas separadamente em
  `agent_tool_calls`;
- o frontend Next.js 16 em Compose iniciou em `:3000` e respondeu `200`;
- lint, typecheck, build de produção e `npm audit` passaram, com zero
  vulnerabilidades reportadas nas dependências auditadas;
- `hermes plugins doctor ./agent --ci` confirmou import, registro de 13 tools e
  um hook.

O usuário demo usado nos testes é `demo@personal-finance.dev` / `demo1234`.
Essas credenciais são somente para desenvolvimento local.

## Milestone comprovado por código

O caminho a seguir está implementado e testado nas fronteiras do repositório:

```text
tool Hermes/smoke runner
  -> BackendFinanceClient
  -> headers X-Agent-Token + X-Agent-Sender-Id + X-Agent-Message-Id
  -> endpoint FastAPI do agente
  -> service financeiro
  -> Transaction/PostgreSQL
```

O teste de serviço comprova que `source` permanece `whatsapp` e que a mesma
mensagem é idempotente. A geração OpenAPI também inclui as rotas de agente,
webhook e CRUD financeiro.

## Ciclo 1 — smoke real com Ollama local

Em 20/09/2026, o caminho local foi exercitado sem iniciar o gateway Hermes ou
parear o WhatsApp:

- Ollama foi executado no container separado `personal-finance-ollama`, na porta
  `11434`, com o modelo `qwen2.5:3b` em volume nomeado;
- o runner estruturou “Gastei R$ 25 com almoço hoje pelo Nubank.” como
  `create_transaction`, `expense`, `25`, `Alimentação`, `Nubank` e `today`;
- a API persistiu a despesa com `source=whatsapp` e data `2026-09-20`;
- a repetição com o mesmo `X-Agent-Message-Id` retornou `replayed=true` e o
  mesmo ID, sem criar uma segunda transação;
- “Quanto gastei com alimentação este mês?” chamou `get_category_summary` e
  retornou `R$ 102,50` calculados pelo backend;
- “Quanto gastei com transporte este mês?” chamou `get_category_summary` e
  retornou `R$ 78,00` calculados pelo backend;
- uma mensagem sem conta, em um usuário com múltiplas contas, foi recusada com
  `ACCOUNT_REQUIRED` sem persistência;
- o runner foi endurecido com temperatura/seed fixos, validação semântica e
  rejeição de intenções incompletas antes do HTTP.

Esse resultado comprova o Ciclo 1, mas não comprova entrega por WhatsApp real.
O Ciclo 2 continua dependente do gateway Hermes/Baileys e do pareamento manual.

## Validações dependentes do ambiente

- Ollama precisa estar instalado e com um modelo baixado para validar a
  interpretação real em português. No Hermes, configure o endpoint local
  `http://127.0.0.1:11434/v1` e contexto mínimo de `64000`. O adaptador é local,
  mas o binário não é empacotado neste repositório.
- O pareamento e a entrega efetiva pelo WhatsApp Web precisam de uma sessão
  Hermes/Baileys ativa e de um telefone previamente vinculado.
- Docker Compose precisa de um daemon Docker acessível ao usuário para subir o
  PostgreSQL. A suíte de serviços pode continuar sendo executada com PostgreSQL
  local.

Essas condições não são tratadas como sucesso apenas porque o código foi
escrito. Depois de disponíveis, valide manualmente:

1. vincular o número pela tela Integrações;
2. enviar “Gastei 50 reais de gasolina.”;
3. conferir `source=whatsapp`, categoria e saldo no dashboard;
4. repetir a mesma mensagem/ID e confirmar que não duplica;
5. perguntar “Quanto gastei com transporte este mês?”;
6. conferir que a resposta contém os números devolvidos por
   `get_category_summary`, não um cálculo do modelo.
