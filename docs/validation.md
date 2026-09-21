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

Na revisão de 21/09/2026, passaram 39 testes de backend, 19 testes da fronteira
do agente e 21 testes de frontend. O backend cobre criação de receita/despesa,
transferências com duas pernas, saldo, orçamento, Decimal, timezone, isolamento
de usuário, idempotência, auditoria, diagnóstico, resumo determinístico, edição
de perfil e fluxos HTTP. O plugin cobre o cliente HTTP, a recusa de contexto sem
idempotência e o conjunto esperado de 14 tools.

## Execução real local — 21/09/2026

Além da suíte automatizada, o ambiente local foi exercitado com PostgreSQL 16
no Docker Compose:

- `docker compose config --quiet` passou;
- backend, frontend e PostgreSQL foram reconstruídos e ficaram ativos; banco e
  API ficaram `healthy`, e o PostgreSQL aceitou as migrations Alembic;
- Alembic confirmou `0005_operational_cleanup_indexes (head)`;
- as migrations `0001 -> 0005` também foram aplicadas em um banco temporário
  vazio e `alembic check` não encontrou drift entre ORM e schema;
- o seed criou o usuário demo, contas, categorias, transações, orçamentos e
  meta;
- login por cookie, `GET /api/v1/dashboard` e o relatório de seis meses
  responderam pelo container FastAPI;
- readiness respondeu `ready` somente depois de confirmar conexão e as 13 tabelas
  financeiras obrigatórias, OpenAPI expôs a versão 0.2.0 e 40 paths;
- `POST /integrations/whatsapp/link` vinculou um telefone de teste;
- o acesso do agente a uma identidade não verificada retornou `403`;
- a tela/API gerou um código expirável, o endpoint do agente confirmou o código
  e o acesso financeiro passou a funcionar; desvincular e vincular novamente
  voltou a exigir verificação;
- quando executado dentro do Hermes, o cliente do agente usa o mapa LID↔telefone
  do próprio bridge antes de enviar a identidade à API; fora do Hermes, mantém
  um fallback sem dependência dessa instalação;
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
- `delete_transaction` criou uma ação pendente e só excluiu depois do token
  expirável correspondente, sem alterar a transação na primeira chamada;
- `PATCH /transfers/{id}` alterou origem, destino, valor, descrição, data e as
  duas pernas da transferência em uma única operação, preservando o cálculo de
  saldo por conta;
- o histórico respondeu páginas estáveis com `X-Next-Cursor`, sem duplicar ou
  perder movimentos entre páginas; cursor inválido retornou `422`;
- o CORS expôs `X-Next-Cursor` para a origem web, permitindo que o botão de
  continuação funcione no navegador;
- o frontend Next.js 16 em Compose iniciou em `:3000` e respondeu `200`;
- lint, typecheck, build de produção e `npm audit` passaram, com zero
  vulnerabilidades reportadas nas dependências auditadas;
- `hermes plugins doctor ./agent --ci` confirmou import, registro de 14 tools e
  um hook.

O E2E de navegador também passou localmente em 21/09/2026:

- Playwright 1.63 com Firefox 155 foi instalado no host apenas como dependência
  de desenvolvimento e navegador de teste, sem alterar o runtime financeiro;
- o cenário `frontend/e2e/core-flow.spec.ts` passou em `desktop-firefox` e
  `mobile-firefox`;
- o cenário criou um usuário novo, abriu o diagnóstico após o cadastro, salvou
  a primeira etapa e confirmou a retomada do rascunho, criou Nubank e Inter,
  registrou uma despesa, criou e editou uma transferência, criou orçamento e
  meta, e confirmou o saldo no dashboard;
- o preflight CORS para `PUT /diagnostic/draft` passou, evitando regressão no
  salvamento do diagnóstico pelo navegador;
- o workflow de CI repete o cenário em uma stack Compose temporária e remove
  seus volumes ao terminar.

Durante essa validação foi corrigida uma corrida de navegação no cadastro: o
efeito que protege a rota autenticada não pode sobrescrever o destino explícito
do diagnóstico inicial.

O fluxo operacional também foi exercitado com `make db-backup` e
`make db-backup-check`: o dump custom foi validado por checksum, restaurado em
um banco PostgreSQL temporário e consultou `users` e `alembic_version` antes de
ser removido. O banco de desenvolvimento não foi sobrescrito.

A rotina de manutenção operacional também foi adicionada com dry-run por
padrão. Ela remove somente sessões expiradas, desafios vencidos e logs técnicos
sem vínculo financeiro além da retenção configurada; mensagens e chamadas
ligadas a transações ou transferências ficam preservadas para idempotência. A
execução aplicada exige `--apply` e deve ser agendada somente depois de definir
retenção e backup do ambiente compartilhado. `make maintenance-check` foi
executado contra o backend do Compose e encontrou 3 sessões expiradas, sem
ações pendentes ou logs elegíveis; como era dry-run, nenhum registro foi
removido.

## Ciclo 3 — prontidão da integração local

O verificador `make cycle3-check` foi adicionado para separar pré-requisitos
locais de código já validado. Ele consulta somente endpoints de saúde, não lê o
conteúdo das credenciais e não altera o banco.

Para o aceite estrito, a checagem exige que o ambiente declare
`WHATSAPP_MODE=bot` e uma allowlist específica em `WHATSAPP_ALLOWED_USERS`; as
entradas precisam estar em E.164. Uma sessão conectada em `self-chat`, uma
allowlist vazia, um wildcard ou um número malformado continuam como warning.

Na primeira execução deste ciclo, antes de subir o bridge:

- backend e `hermes plugins doctor` passaram;
- o endpoint OpenAI-compatible do Ollama foi encapsulado no provider
  substituível do runner;
- a API nativa do Ollama foi corrigida para consultar `/api/show` com `POST`;
- o smoke runner continua usando `qwen2.5:3b`, cuja janela de 32.768 tokens fica
  abaixo do mínimo de 64.000 exigido pelo Hermes atual; para o gateway, o host
  agora possui `llama3.2:3b` com janela de 131.072 tokens e suporte a tool
  calling;
- uma sessão antiga de WhatsApp existe no host, porém o bridge ainda não está
  rodando;
- a porta do bridge foi fixada em `3300`, evitando o conflito observado com o
  frontend em `3000`.

Depois, o modelo `llama3.2:3b` foi baixado, a sessão Baileys subiu em `3300` e
`make cycle3-check` confirmou backend, Ollama, plugin e bridge. A interpretação
estruturada de “Gastei R$ 25 com almoço hoje.” também retornou a tool e os
parâmetros esperados sem tocar no banco. O strict check continua exigindo uma
allowlist explícita; a sessão local usada na validação ainda não foi autorizada
para receber mensagens.

Portanto, o Ciclo 3 ainda não é aceito como round trip. O aceite depende da
allowlist, da inicialização do gateway Hermes e da execução dos cenários M–R
com evidência sanitizada. `make cycle3-ready` deve passar somente depois desses
pré-requisitos.

O usuário demo usado nos testes é `demo@personal-finance.dev` / `demo1234`.
Essas credenciais são somente para desenvolvimento local.

## Ciclo 2A — diagnóstico e onboarding

Em 20/09/2026, a implementação local do Ciclo 2A foi validada com os checks de
código e testes automatizados:

- validação do questionário alinhada aos campos obrigatórios do formulário;
- respostas condicionais são removidas quando deixam de ser aplicáveis;
- opções exclusivas são rejeitadas pelo backend e respeitadas pelo frontend;
- usuários podem salvar, retomar e editar o diagnóstico sem bloquear o
  dashboard;
- `GET /api/v1/diagnostic/summary` calcula margem mensal e próximos passos com
  `Decimal`, sem usar modelo de linguagem;
- `PATCH /api/v1/auth/me` atualiza nome e fuso horário com isolamento por sessão;
- o resumo aparece no diagnóstico concluído e em um card do dashboard;
- não existe upload de documentos e nenhuma resposta cria transação, conta,
  orçamento ou meta automaticamente;
- `make check` passou: 39 testes de backend, 19 do agente, 21 do frontend e
  build de produção do Next.js.

A revisão visual manual em desktop e mobile continua sendo uma etapa de aceite
antes de considerar o ciclo concluído para uso com clientes.

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
O Ciclo 3 continua dependente do gateway Hermes/Baileys e do pareamento manual.

## Validações dependentes do ambiente

- Ollama precisa estar instalado e com um modelo baixado para validar a
  interpretação real em português. No Hermes, configure o endpoint local
  `http://127.0.0.1:11434/v1` e contexto mínimo de `64000`. O adaptador é local,
  mas o binário não é empacotado neste repositório. O `qwen2.5:3b` validado no
  runner não deve ser usado como modelo final do gateway porque sua janela é
  menor.
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
