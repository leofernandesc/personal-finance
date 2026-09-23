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

Na revisão de 21/09/2026, passaram 39 testes de backend, 21 testes da fronteira
do agente e 21 testes de frontend. O backend cobre criação de receita/despesa,
transferências com duas pernas, saldo, orçamento, Decimal, timezone, isolamento
de usuário, idempotência, auditoria, diagnóstico, resumo determinístico, edição
de perfil e fluxos HTTP. O plugin cobre o cliente HTTP, a recusa de contexto sem
idempotência e o conjunto esperado de 14 tools.

## Revisão das regras de cadastro — 22/09/2026

- `backend/tests/test_api_flows.py`: 13 testes passaram, incluindo rejeição de
  nome vazio e confirmação de senha divergente; o TestClient mostrou dois
  avisos de depreciação das dependências Starlette/httpx.
- TypeScript (`tsc --noEmit`), ESLint nos arquivos alterados e `git diff --check`
  passaram.
- O fluxo E2E existente foi atualizado para preencher a confirmação e exercitar
  a divergência e o controle de visibilidade da senha, mas não foi executado
  localmente para não gravar outra conta de teste no PostgreSQL compartilhado.
- Cadastro/login não oferecem recuperação ou troca de senha ainda. A decisão e
  os pré-requisitos para esses fluxos estão em
  [`docs/architecture/0020-registration-rules.md`](architecture/0020-registration-rules.md)
  e no roadmap.

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
- as páginas públicas `/login` e `/register` passaram o scan WCAG 2A/2AA do
  axe nos projetos desktop e mobile;
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

### Evidência atual — 22/09/2026

Como o host não tinha `sudo` interativo, o runtime Ollama `0.34.2` foi instalado
no diretório do usuário e iniciado com `OLLAMA_LLM_LIBRARY=cpu`. O modelo
`llama3.2:3b` foi baixado e o `/api/show` confirmou contexto de `131072` tokens.
O smoke real pela fronteira Ollama → FastAPI então produziu:

- `create_transaction`, `expense`, `25`, `Almoço`, `Alimentação`, `Nubank` e
  `relative_date=today`;
- persistência com `source=whatsapp`, valor `25.00` e data `2026-09-22`;
- repetição do mesmo `X-Agent-Message-Id` com o mesmo ID e `replayed=true`;
- `get_category_summary` retornando `127.50` para Alimentação;
- `get_month_summary` retornando `income=4500.00`, `expense=205.50` e
  `savings=4294.50`, todos calculados pelo backend.

O primeiro carregamento em CPU ultrapassou 60 segundos; por isso o runner agora
aceita `LLM_TIMEOUT_SECONDS`/`--llm-timeout` e usa 180 segundos por padrão.
Essa evidência valida o caminho local do modelo até o PostgreSQL, mas não é um
round trip WhatsApp: o bridge continua em `self-chat` e a execução estrita deve
permanecer bloqueada.

Na mesma data, o plugin foi instalado no perfil isolado
`~/.hermes/profiles/personal-finance`, o perfil foi alinhado para
`custom:ollama` com `llama3.2:3b`, e o comando `make hermes-local-smoke` foi
executado com uma consulta de leitura. O Hermes chamou `get_balance` e retornou
`R$ 6.464,50`, distribuídos em Dinheiro (`R$ 84,50`), Inter (`R$ 1.150,00`) e
Nubank (`R$ 5.230,00`). A API registrou a mesma mensagem externa com
`intent=get_balance`, `tool_name=get_balance`, `status=success` e uma única
linha em `agent_tool_calls`. Portanto, esta evidência comprova Hermes → Ollama
→ plugin → FastAPI → PostgreSQL para uma consulta, sem depender do gateway
padrão ou de uma API paga.

O preflight também confere o modo real do processo Hermes quando o bridge está
no host local. Nesta máquina, o endpoint respondeu `connected`, mas o processo
está em `--mode self-chat`; portanto, mesmo com uma allowlist hipotética, o
aceite deve continuar recusando o round trip até o gateway ser iniciado em modo
`bot`.

#### Endurecimento operacional do Ollama — 22/09/2026

- O runtime foi isolado em `docker-compose.ollama.yml`, fora da stack principal.
  A porta `11434` está publicada somente em `127.0.0.1`; o container participa
  apenas da rede dedicada `personal-finance-ollama-network` e os modelos usam o
  volume externo persistente `personal-finance-ollama`.
- O container antigo, cuja porta seria publicada em todas as interfaces, foi
  renomeado para identificá-lo como aposentado e permanece parado. Seu volume
  não foi apagado nem substituído.
- `docker compose ... config` e inspeção do container confirmaram o bind de
  loopback e a rede dedicada. O CI agora valida automaticamente esse contrato
  e a persistência do volume.
- `make cycle3-check` confirmou backend, `llama3.2:3b` (131.072 tokens) e plugin
  Hermes. `make cycle3-ready` continua falhando de forma esperada porque o
  processo efetivo do bridge permanece em `self-chat`.
- Um smoke local de interpretação chamou somente o parser Ollama e identificou
  `get_category_summary` para uma consulta sobre Transporte; não executou tool
  financeira, não gravou dados e não substitui o teste pelo WhatsApp.
- O modelo foi descarregado após o smoke para devolver RAM ao host. Em CPU, a
  inferência levou vários segundos e elevou o uso de swap; não iniciar outras
  inferências nem baixar modelos sem verificar espaço em disco e memória.
- Nenhum round trip pelo WhatsApp foi realizado nesta etapa. A sessão continua
em `self-chat`; ativá-la em `bot` exige número de teste em E.164 na allowlist
e autorização explícita, pois mensagens recebidas podem acionar tools.
O usuário confirmou que prefere manter `self-chat`; a validação real pelo canal
fica deliberadamente suspensa, sem alterar a sessão nem a allowlist.

#### Bind seguro da stack local — 22/09/2026

Uma inspeção da stack ativa encontrou PostgreSQL, API e frontend publicados em
`0.0.0.0`. O Compose agora mantém as três portas em `127.0.0.1` por padrão; a
API e o frontend aceitam um IP LAN específico via `APP_BIND_HOST` para testes
temporários em dispositivo físico, enquanto o PostgreSQL permanece loopback.
O CI valida os binds efetivos do Compose com `.env.example`. Após a recriação
dos serviços, `docker compose ps` confirmou os três binds locais, `/ready` da
API e a página de cadastro responderam com sucesso. Os passos para teste móvel
em rede confiável e retorno à configuração local estão no README e no ADR 0021.

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
- `make check` passou: 39 testes de backend, 21 do agente, 21 do frontend e
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

## Paginação do histórico — 22/09/2026

- `make frontend-check` passou com 25 testes Vitest, ESLint, TypeScript e build
  de produção.
- O novo E2E de paginação simula uma primeira página com cursor, uma falha 503
  transitória e o retry bem-sucedido. Ele confere que os movimentos da primeira
  página permanecem visíveis durante o erro, que a nova página é anexada uma
  única vez e que o botão desaparece no fim.
- O cenário passou em Firefox desktop e mobile contra uma stack Compose e um
  volume PostgreSQL descartáveis, em portas diferentes da aplicação local. A
  stack temporária foi removida após validar seus nomes; a aplicação principal
  permaneceu saudável e seu banco compartilhado não foi usado pelo E2E.
- A reprodução encontrou que o seletor amplo `getByRole("alert")` também
  selecionava o anunciador vazio de navegação do Next.js. O teste foi
  restringido ao texto exato do alerta e repetido com sucesso nos dois projetos.

## Acessibilidade de telas autenticadas — 22/09/2026

- O axe agora examina dashboard e histórico depois de criar uma sessão E2E,
  além das páginas públicas de login e cadastro. O cenário roda no desktop e
  no mobile; neste último, abre o menu lateral antes do scan.
- A primeira execução encontrou contraste insuficiente (2,8:1) nos rótulos
  “Seu dinheiro” e “Organizar”, causados por `text-muted/70` sobre branco. Os
  rótulos agora usam a cor opaca `text-muted`; o axe passou nas duas rotas e
  nos dois projetos de navegador.
- `make frontend-check` também passou: 25 testes Vitest, lint, typecheck e build.
  Os dados E2E ficaram numa stack e volume PostgreSQL temporários, removidos ao
  final; a API principal continuou saudável.
- Isso não substitui a revisão manual de navegação por teclado, leitor de tela
  e ordem de foco, que continua pendente.

## Proteção do seed de demonstração — 22/09/2026

- `app.seed_demo` agora permite execução somente em `development` e `test`;
  em `staging` e `production`, falha antes de abrir uma sessão de banco.
- Quatro testes dedicados cobrem os dois ambientes compartilhados, os ambientes
  locais e a idempotência do seed. O fluxo permitido foi exercitado em SQLite
  em memória; nenhuma conta foi criada no PostgreSQL da aplicação.
- `make check` passou: 44 testes backend, 27 testes do agente, 25 testes
  frontend, lint, formatação, typecheck e build de produção. Permanecem dois
  avisos de depreciação vindos da combinação Starlette/httpx da suíte de testes.

## Smoke Hermes somente leitura — 23/09/2026

- O runner local agora ativa `PERSONAL_FINANCE_READ_ONLY=1`. O plugin mantém as
  14 ferramentas do manifesto, mas recusa tools `POST`, `PATCH` e `DELETE`
  antes de criar um cliente ou chamar a API; consultas `GET` continuam
  disponíveis. O gateway normal não recebe essa variável.
- `make agent-check` passou com 30 testes, lint, formatação e compilação; o
  Hermes Plugin Doctor passou sem avisos e confirmou 14 tools e 2 hooks. A
  sintaxe do script shell também foi validada.
- `make backend-check` passou com 46 testes. Os testes executam o script contra
  um perfil fictício desatualizado e confirmam que o executável Hermes falso
  não é iniciado; também cobrem o limite padrão de tokens, override e valores
  inválidos sem lançar o Hermes real.
- O perfil Hermes isolado foi atualizado para `0.2.1` e passou no Plugin Doctor
  com 14 tools e 2 hooks. O processo gateway usa `HERMES_HOME=~/.hermes`, não o
  diretório isolado; não foi reiniciado e permaneceu em `self-chat`.
- No smoke `codex-readonly-smoke-20260923-001`, o PostgreSQL registrou a
  mensagem e `get_balance` como `success`; porém o CLI não produziu a resposta
  final antes do timeout de 240 s. Nenhuma tool de escrita estava habilitada.
- No smoke `codex-readonly-smoke-20260923-002`, com limite de 128 tokens, não
  houve chamada auditada nem marcador da resposta esperada, então a execução não
  conta como round trip aprovado. O limite padrão agora é 512 tokens; ainda
  falta validá-lo com uma resposta completa.
- Nas duas tentativas, o processo `llama-server` continuou consumindo cerca de
  265% de CPU sem conexões abertas após o cliente encerrar. O modelo foi
  descarregado pelo comando `ollama stop`; o serviço Ollama permaneceu ativo,
  a API continuou pronta e a memória disponível voltou a 3,4 GiB. O modelo está
  descarregado no momento desta validação.

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
