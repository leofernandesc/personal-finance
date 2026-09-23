# Organiza Finanças

Aplicação local de controle de finanças pessoais com dashboard web, API
multiusuário e uma camada conversacional preparada para Hermes, Ollama e
WhatsApp Web. O objetivo do MVP é registrar e consultar a vida financeira sem
entregar a fonte de verdade a um modelo de linguagem.

## Estado atual

O MVP web está implementado: autenticação local, diagnóstico financeiro
editável, resumo determinístico do diagnóstico, edição de perfil, domínio
financeiro, transferências, dashboard responsivo, relatórios, orçamentos e
metas. O Ciclo 1 conversacional também foi validado localmente com Ollama,
runner, FastAPI e PostgreSQL, incluindo idempotência e consultas reais. O
round trip com uma sessão WhatsApp/Hermes/Baileys ainda depende de um número
controlado e não é tratado como concluído antecipadamente. O fluxo web
essencial também possui E2E automatizado em Firefox desktop e mobile.

O projeto não depende de serviços pagos. PostgreSQL, FastAPI, Next.js, Hermes e
Ollama podem rodar localmente.

## Arquitetura

```text
Frontend Next.js ───────────────┐
                                ├─> FastAPI ─> regras de negócio ─> PostgreSQL
WhatsApp Web/Baileys ─> Hermes ─┤
                         Ollama ┘
```

O agente recebe contexto do canal, interpreta português brasileiro e escolhe
uma tool. A tool faz uma chamada HTTP autenticada ao backend. O backend deriva o
usuário pelo cookie da web ou pelo número WhatsApp vinculado, valida a operação,
calcula saldos e grava no PostgreSQL. Nem Hermes nem o LLM possuem credenciais
do banco, geram SQL ou escolhem `user_id`.

Cada mensagem externa possui um envelope técnico em `agent_messages`; cada
tool executada possui uma linha em `agent_tool_calls`. A gravação financeira e
o sucesso da auditoria são atômicos, enquanto falhas sofrem rollback antes de
serem registradas sem texto ou payload sensível.

Transferências têm uma entidade própria e duas pernas de transação (`out` e
`in`), portanto não são contabilizadas como receita ou despesa. Valores usam
`NUMERIC(14,2)` no PostgreSQL e `Decimal` no Python. Datas relativas usam o
timezone do usuário.

## Stack

- Frontend: Next.js 16 App Router, React 19, TypeScript, Tailwind CSS, Recharts, React Hook
  Form e Zod.
- Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy, Alembic e psycopg.
- Banco: PostgreSQL 16.
- Agente: plugin Hermes com tools HTTP, `LLMProvider` e `OllamaProvider`.
- Canal: abstração `WhatsAppProvider`, com fronteira preparada para Baileys e
  uma futura WhatsApp Cloud API.

## Estrutura

```text
personal-finance/
├── frontend/                 # aplicação web e experiência responsiva
├── backend/                  # API, domínio, autenticação e testes
├── agent/                    # plugin Hermes, Ollama e cliente HTTP do backend
├── database/migrations/      # migrations Alembic
├── docs/architecture/        # decisões arquiteturais registradas
├── .github/workflows/ci.yml  # checks automatizados no GitHub
├── Makefile                  # atalhos de desenvolvimento e validação
├── docker-compose.yml        # PostgreSQL, backend e frontend
├── .env.example              # configuração sem secrets
└── README.md
```

## Pré-requisitos

Para o MVP web:

- Git;
- Python 3.12+;
- Node.js 22+ e npm;
- Docker Engine com Docker Compose, ou PostgreSQL 16 local.

Para o fluxo conversacional:

- Hermes instalado localmente;
- Ollama instalado localmente ou executado no container separado descrito em
  [`docs/architecture/0006-local-ollama-runtime.md`](docs/architecture/0006-local-ollama-runtime.md);
- um modelo que responda a saída estruturada, por exemplo `qwen2.5:3b` ou
  `qwen2.5:7b` em máquinas com mais memória;
- um ambiente de teste com WhatsApp Web/Baileys pareado.

## Configuração inicial

Na raiz do repositório:

```bash
cp .env.example .env
```

Altere, no mínimo, `AGENT_SHARED_SECRET` em qualquer ambiente compartilhado.
Para desenvolvimento local, os valores do exemplo são suficientes.

Os principais comandos também estão disponíveis no Makefile:

```bash
make help
make setup
make up
make check
```

### Subir com Docker Compose

Para iniciar apenas o PostgreSQL:

```bash
docker compose up -d db
```

Para iniciar toda a aplicação:

```bash
docker compose up -d --build
```

O backend aguarda o healthcheck do banco, executa `alembic upgrade head` e fica
disponível em `http://localhost:8000`. O frontend fica em
`http://localhost:3000`. A documentação OpenAPI fica em
`http://localhost:8000/docs`.

Por padrão, as portas do PostgreSQL, da API e do frontend ficam acessíveis
somente no próprio computador (`127.0.0.1`). Para abrir a aplicação
temporariamente em um celular conectado à mesma rede Wi-Fi, use o IP local
específico do computador (exemplo `192.168.1.20`) em `.env`:

```dotenv
APP_BIND_HOST=192.168.1.20
ALLOWED_HOSTS=localhost,127.0.0.1,192.168.1.20,backend,testserver
CORS_ORIGINS=http://localhost:3000,http://192.168.1.20:3000
NEXT_PUBLIC_API_URL=http://192.168.1.20:8000/api/v1
```

Recrie API e frontend:

```bash
docker compose up -d --force-recreate backend frontend
```

Abra `http://192.168.1.20:3000` no celular. O PostgreSQL continua preso ao
loopback. Esse acesso usa HTTP sem TLS: faça isso somente em uma rede confiável,
nunca em Wi-Fi público. Depois do teste, restaure `APP_BIND_HOST=127.0.0.1`,
`NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`, `CORS_ORIGINS` e
`ALLOWED_HOSTS` para os valores locais, e recrie API e frontend novamente.

Para acompanhar ou parar os serviços:

```bash
docker compose logs -f backend
docker compose down
```

Para aplicar migrations ou carregar o usuário demo a partir do host, use:

```bash
make migrate
make seed
```

Esses alvos usam `127.0.0.1` por padrão. Se o PostgreSQL estiver em outro
endereço, sobrescreva com `make seed LOCAL_DATABASE_URL=...`; o hostname
`db` só é resolvido dentro da rede do Compose.

`docker compose down` preserva o volume nomeado; use `docker compose down -v`
somente quando quiser apagar o banco local de demonstração.

### Backup e restauração local

O PostgreSQL é a fonte de verdade financeira. Crie um dump local com checksum
SHA-256:

```bash
make db-backup
```

O arquivo fica em `backups/`, que não é versionado. Para testar a recuperação
sem alterar o banco em uso, restaure o dump em uma base temporária:

```bash
make db-backup-check BACKUP=backups/personal_finance_YYYYMMDDTHHMMSSZ.dump
```

A restauração do banco do Compose é destrutiva e exige confirmação explícita:

```bash
make db-restore BACKUP=backups/personal_finance_YYYYMMDDTHHMMSSZ.dump
make migrate
```

Os scripts não cifram o dump. Em qualquer ambiente compartilhado, armazene o
arquivo em local protegido e defina retenção antes de usá-lo como backup
operacional.

### Executar sem Docker

Com um PostgreSQL local acessível:

```bash
cd backend
python3.12 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload
```

O carregamento de configuração procura o `.env` da raiz, mesmo com o comando
executado dentro de `backend/`. Para executar o frontend em outro terminal:

```bash
cd frontend
npm install
npm run dev
```

O frontend usa `NEXT_PUBLIC_API_URL` e, por padrão, chama
`http://localhost:8000/api/v1`.

### Dados de demonstração

Depois de aplicar as migrations e garantir acesso ao banco:

```bash
cd backend
PYTHONPATH=. .venv/bin/python -m app.seed_demo
```

Credenciais do usuário demo:

```text
e-mail: demo@personal-finance.dev
senha:  demo1234
```

O seed cria Nubank, Inter, Dinheiro, categorias, transações do mês,
orçamentos e a meta de reserva de emergência. Ele é idempotente por e-mail e
não duplica o usuário demo. Como a senha é pública, o comando recusa execução
fora de `development` ou `test`; nunca disponibilize essas credenciais em uma
instalação compartilhada.

### Manutenção operacional

Sessões expiradas, desafios de confirmação vencidos e logs técnicos antigos
podem ser limpos por uma rotina explícita. A simulação não altera o banco:

```bash
make maintenance-check
```

Para aplicar a limpeza, use o comando que exige `--apply` internamente:

```bash
make maintenance-cleanup
```

Por padrão, logs técnicos sem vínculo financeiro são retidos por 180 dias.
Registros ligados a transações ou transferências permanecem para manter a
idempotência de mensagens e a auditoria. A rotina nunca remove dados
financeiros; antes de definir um agendamento compartilhado, configure backup e
retenção conforme a política de privacidade do serviço.

Para um host Linux com `systemd --user`, há um timer semanal versionado em
`ops/systemd/`. Ele não é ativado automaticamente; siga o runbook em
[`docs/operations.md`](docs/operations.md) somente depois de validar backup,
restauração e retenção.

## Fluxos principais

### Web

1. Crie uma conta em `/register` ou use o usuário demo.
2. Faça login em `/login`.
3. Preencha o diagnóstico inicial ou salve para continuar depois; ele não
   bloqueia o restante da aplicação.
4. Cadastre contas e, se necessário, ajuste categorias.
5. Registre receitas, despesas e transferências em **Transações**.
6. Edite uma transferência pelo histórico; a aplicação atualiza suas duas
   movimentações de forma conjunta.
7. Consulte saldo, fluxo, categorias, orçamentos e metas no dashboard.

### Diagnóstico financeiro

O diagnóstico fica disponível em **Meu diagnóstico** e em **Configurações**.
Ele é dividido em etapas, salva rascunhos por seção e pode ser editado depois
do envio. As respostas incluem consentimento, identificação, renda, despesas,
cartões, dívidas, patrimônio, metas, comportamento e disponibilidade.

O formulário não recebe documentos nem credenciais. A seção de documentos
apenas registra o que poderá ser disponibilizado futuramente por um canal
seguro. O diagnóstico é informativo e não cria transações, contas ou metas
automaticamente. Depois do envio, a aplicação apresenta um resumo calculado
pelas respostas informadas. Ele não representa o saldo atual das contas e não
é uma recomendação de investimento.

O perfil permite alterar nome e fuso horário em **Configurações**. O e-mail de
acesso permanece bloqueado nesta versão.

### Hermes + Ollama + WhatsApp

O plugin vive em `agent/`. Ele registra 14 tools no toolset
`personal_finance`. Todas chamam endpoints `/api/v1/integrations/agent/*` com:

- `X-Agent-Token` para autenticação entre processos;
- `X-Agent-Provider` para identificar o canal;
- `X-Agent-Sender-Id` para resolver o telefone;
- `X-Agent-Message-Id` para idempotência.

Ollama fica opcional e isolado do Compose principal. Inicie o serviço local
com a porta disponível somente em `127.0.0.1` e mantenha os modelos no volume
persistente:

```bash
make ollama-up
make ollama-model
```

`make ollama-model` baixa `llama3.2:3b` para o Hermes e pode ocupar alguns GB em
disco; a inferência também usa memória RAM. Não é necessário se o modelo já
estiver no volume. Para encerrar o servidor sem remover os modelos:

```bash
make ollama-down
```

Para o smoke runner do Ciclo 1, o `qwen2.5:3b` pode ser baixado separadamente:

```bash
docker compose -p personal-finance-ollama -f docker-compose.ollama.yml exec ollama ollama pull qwen2.5:3b
export OLLAMA_BASE_URL=http://127.0.0.1:11434
export OLLAMA_MODEL=qwen2.5:3b
```

O smoke runner exige identidade e ID externo explícitos:

```bash
export PERSONAL_FINANCE_API_URL=http://127.0.0.1:8000/api/v1/integrations/agent
export AGENT_SHARED_SECRET='o-mesmo-valor-do-.env'
PYTHONPATH=. backend/.venv/bin/python -m agent.runner \
  --sender +5592999999999 \
  --message-id smoke-001 \
  'Gastei R$ 25 com almoço hoje pelo Nubank.'
```

O mesmo `--message-id` deve retornar `replayed=true` em uma repetição. Esse
runner valida o Ciclo 1, mas não substitui o gateway nem inicia o pareamento do
WhatsApp do Ciclo 3.

Antes de mandar mensagens, vincule o telefone autenticado ao usuário pela tela
**Integrações**, ou pela API autenticada:

```bash
curl -X POST http://localhost:8000/api/v1/integrations/whatsapp/link \
  -H 'Content-Type: application/json' \
  -H 'Cookie: pf_session=<sessao-da-web>' \
  -d '{"phone_e164":"+5592999999999"}'
```

Esse vínculo manual existe somente para desenvolvimento e começa com
`verified=false`. Na tela de Integrações, gere o código temporário e envie-o
pelo próprio WhatsApp; somente depois o backend libera as tools financeiras.
Uma implantação fora do ambiente local deve manter esse desafio e adicionar
políticas de retenção/monitoramento do canal.

Verifique o plugin e habilite a descoberta local do monorepo:

```bash
hermes plugins doctor ./agent --ci
mkdir -p .hermes/plugins
ln -sfn "$(pwd)/agent" .hermes/plugins/personal-finance
export HERMES_ENABLE_PROJECT_PLUGINS=1
```

O doctor deve confirmar o manifesto, o import e as 14 tools. Execute o Hermes a
partir da raiz do repositório para que o plugin local seja descoberto. Para uma
instalação permanente fora do monorepo, copie `agent/` para
`~/.hermes/plugins/personal-finance/` e habilite `personal-finance` com o CLI.

Para validar o perfil financeiro sem tocar no gateway padrão, instale o plugin
no perfil isolado e execute uma consulta somente de leitura:

```bash
HERMES_HOME="$HOME/.hermes/profiles/personal-finance" \
  hermes plugins install "file:///caminho/para/personal-finance#agent" --enable
HERMES_SMOKE_SENDER=+5592999999999 make hermes-local-smoke
```

O script usa `llama3.2:3b`, injeta somente o contexto técnico necessário para a
sessão e tem como mensagem padrão “Quanto dinheiro tenho atualmente?”. Para
testar outra mensagem, defina `HERMES_SMOKE_TEXT`; mensagens de mutação alteram
os dados reais do usuário informado. O script não inicia o gateway nem o
WhatsApp e não substitui o round trip do canal.
No Hermes, habilite o toolset `personal_finance` para a plataforma WhatsApp e
configure a porta do bridge fora da porta do frontend:

```yaml
plugins:
  enabled:
    - personal-finance
platform_toolsets:
  whatsapp:
    - personal_finance
platforms:
  whatsapp:
    enabled: false
    extra:
      bridge_port: 3300
```

O bridge usa `127.0.0.1:3300`; o frontend continua em `3000`. Mantenha o
WhatsApp desativado até concluir o pareamento e conferir a allowlist.
A ponte WhatsApp/Web é responsabilidade do Hermes/Baileys; o domínio
financeiro não conhece Baileys.

Antes de ativar o gateway, defina uma allowlist explícita para o número de
desenvolvimento:

```bash
export WHATSAPP_ALLOWED_USERS=+5592XXXXXXXXX
```

Para Ollama:

```bash
ollama serve
ollama pull llama3.2:3b
hermes model
```

No wizard `hermes model`, selecione **Custom endpoint** e configure:

```text
Base URL:      http://127.0.0.1:11434/v1
API key:       none
Model:         llama3.2:3b
Contexto:      64000 ou maior
```

O endpoint customizado é o caminho usado pelo Hermes para chamadas OpenAI-
compatible. O `agent/llm/ollama.py` usa a API nativa `/api/chat` no smoke runner
e mantém a mesma fronteira `LLMProvider`. Para máquinas sem muita memória, um
modelo menor pode ser usado no smoke runner alterando `OLLAMA_MODEL`; para o
gateway, o modelo precisa suportar tool-calling e uma janela mínima de 64.000.
Neste host, `llama3.2:3b` foi baixado e informa 131.072 tokens; o
`qwen2.5:3b` validado no Ciclo 1 tem janela de 32.768 e permanece restrito ao
runner.

Antes de iniciar o gateway, execute as verificações somente leitura:

```bash
make cycle3-check
make cycle3-ready
```

`cycle3-ready` só passa quando backend, modelo, plugin, sessão, bridge e
allowlist estão prontos. O pareamento real exige QR code e deve ser feito com um número de
desenvolvimento:

```bash
hermes whatsapp
```

Não comite `creds.json`, QR codes, tokens ou números reais. O código do projeto
não inicia o gateway automaticamente e não considera o doctor ou o smoke runner
como prova de entrega por WhatsApp.
Trocar Ollama por outro servidor exige apenas implementar o protocolo
`LLMProvider`; as tools e o backend não mudam.

Existe também um smoke runner sem WhatsApp, útil para inspecionar a fronteira
Ollama → FastAPI:

```bash
cd /home/leofernandesc/personal-finance
PYTHONPATH=. backend/.venv/bin/python -m agent.runner \
  --sender +5592999999999 \
  --message-id local-001 \
  'Gastei R$ 25 com almoço.'
```

O runner não contorna o backend: ele envia a intenção estruturada para a mesma
API autenticada usada pelas tools do Hermes.

## API e segurança

Todas as rotas de domínio estão sob `/api/v1`. As rotas web usam sessão local
em cookie `HttpOnly`; a senha é armazenada com Argon2. As rotas do agente usam o
segredo compartilhado e o telefone vinculado a um usuário.

O diagnóstico usa `GET /diagnostic`, `PUT /diagnostic/draft`,
`POST /diagnostic/submit` e `GET /diagnostic/summary`. Consentimentos são
armazenados com versão e data, e as respostas ficam vinculadas ao usuário
autenticado. O perfil usa `PATCH /auth/me` para nome e fuso horário.

O backend sempre aplica `user_id` derivado da autenticação. IDs enviados pelo
frontend são usados somente como referências de recursos já autorizados. Toda
consulta financeira filtra por usuário, e transações repetidas de WhatsApp usam
uma chave única de idempotência baseada no provider e no message ID.

Exclusão em massa, reset financeiro e alteração em massa não são tools do MVP.
A exclusão conversacional existente é unitária e deve ser confirmada pelo
agente antes da chamada. O backend nunca aceita SQL ou instruções de banco
vindas do LLM.

## Testes e qualidade

Backend:

```bash
cd backend
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/pytest -q
```

Agente:

```bash
cd /home/leofernandesc/personal-finance
PYTHONPATH=. backend/.venv/bin/pytest -q agent/tests
hermes plugins doctor ./agent --ci
```

Frontend:

```bash
cd frontend
npm test
npm run lint
npm run typecheck
npm run build
npm audit --omit=dev --audit-level=high
```

Teste de navegador, com o backend e o PostgreSQL disponíveis (o frontend é
iniciado automaticamente se ainda não estiver rodando):

```bash
cd frontend
npx playwright install firefox
npm run test:e2e
```

O fluxo cria um usuário isolado por execução e percorre cadastro, duas contas,
despesa, transferência, edição atômica da transferência, orçamento, meta e
dashboard em duas viewports. Os dados de teste ficam no banco local; use um
banco de desenvolvimento separado quando a execução não for descartável. O
workflow do GitHub sobe uma stack temporária e instala o Firefox antes de
executar o mesmo comando. O mesmo conjunto também verifica automaticamente
login e cadastro com axe; isso não substitui a auditoria manual de teclado,
foco e leitor de tela.

Na raiz, `make check` reúne os checks do backend, agente e frontend. O workflow
de CI repete essas verificações, aplica migrations em PostgreSQL 16 e usa
`npm ci` para instalações reproduzíveis. O build valida as rotas App Router e o
typecheck valida os contratos TypeScript. A revisão visual adicional deve ser
feita no navegador em desktop e mobile, conferindo teclado, foco, estados
vazios, loading, erro e feedback de salvamento.

O workflow cancela uma execução anterior da mesma branch quando um novo push
chega antes dela terminar. Isso evita filas e alertas duplicados durante uma
sequência de correções, sem esconder falhas: a execução mais recente continua
precisando passar por todos os checks.

## Decisões e documentação

- [`docs/architecture/0001-foundation.md`](docs/architecture/0001-foundation.md):
  fonte de verdade, dinheiro, transferências, sessão e timezone.
- [`docs/architecture/0002-integration-boundaries.md`](docs/architecture/0002-integration-boundaries.md):
  limites entre canal, agente, LLM e backend.
- [`docs/architecture/0003-frontend-direction.md`](docs/architecture/0003-frontend-direction.md):
  direção visual, responsividade e acessibilidade.
- [`docs/architecture/0004-mvp-agent-flow.md`](docs/architecture/0004-mvp-agent-flow.md):
  fluxo comprovável de tool call, idempotência e operação local.
- [`docs/architecture/0005-integrity-and-architecture-review.md`](docs/architecture/0005-integrity-and-architecture-review.md):
  constraints, auditoria por tool, proveniência e decisão sobre camadas.
- [`docs/architecture/0008-financial-diagnostic.md`](docs/architecture/0008-financial-diagnostic.md):
  diagnóstico inicial, rascunho, consentimentos e edição posterior.
- [`docs/architecture/0009-diagnostic-v1.1.md`](docs/architecture/0009-diagnostic-v1.1.md):
  validação condicional, resumo determinístico, perfil e limites do MVP.
- [`docs/architecture/0013-atomic-transfer-edits.md`](docs/architecture/0013-atomic-transfer-edits.md):
  edição atômica das duas pernas de uma transferência.
- [`docs/architecture/0014-cursor-pagination.md`](docs/architecture/0014-cursor-pagination.md):
  paginação estável do histórico sem offset.
- [`docs/architecture/0015-browser-e2e.md`](docs/architecture/0015-browser-e2e.md):
  estratégia de E2E web, isolamento e cobertura responsiva.
- [`docs/architecture/0016-maintenance-scheduler.md`](docs/architecture/0016-maintenance-scheduler.md):
  scheduler opcional e explícito para retenção operacional.
- [`docs/architecture/0017-cycle3-readiness.md`](docs/architecture/0017-cycle3-readiness.md):
  verificação do modo efetivo do bridge antes do aceite do WhatsApp.
- [`docs/architecture/0018-local-ollama-cpu.md`](docs/architecture/0018-local-ollama-cpu.md):
  fallback sem `sudo` e validação local do Ollama em CPU.
- [`docs/architecture/0019-hermes-profile-isolation.md`](docs/architecture/0019-hermes-profile-isolation.md):
  isolamento do perfil financeiro no Hermes e validação do provider local.
- [`docs/architecture/0020-registration-rules.md`](docs/architecture/0020-registration-rules.md):
  validação do nome, confirmação e visibilidade de senha no cadastro e login.
- [`docs/agent.md`](docs/agent.md): configuração operacional do Hermes, Ollama e
  adapters de WhatsApp.
- [`docs/roadmap.md`](docs/roadmap.md): aceite atual e próximos passos
  priorizados.
- [`docs/validation.md`](docs/validation.md): comandos de validação e evidências
  do que foi ou não executado neste ambiente.

## Troubleshooting

**`env file .../.env not found`** — copie `.env.example` para `.env` na raiz.
O arquivo é ignorado pelo Git e nunca deve receber commit.

**Backend não conecta no banco** — confirme `docker compose ps`, o healthcheck do
PostgreSQL e `DATABASE_URL`. Fora do Compose, use `localhost` em vez de `db`.

**Porta 5432, 8000 ou 3000 ocupada** — altere o lado esquerdo do mapeamento no
Compose ou encerre o processo local conflitante.

**Número WhatsApp não vinculado** — faça login na web e vincule o telefone na
página Integrações. O modelo não pode criar nem escolher a identidade.

**Conta/categoria não encontrada** — cadastre a entidade na web; o agente não
inventa entidades e deve devolver as opções retornadas pelo backend.

**Ollama indisponível** — verifique `ollama serve`, `OLLAMA_BASE_URL`, o nome do
modelo e se `ollama pull` terminou. O dashboard e a API web não dependem do
Ollama.

**Docker sem permissão no socket** — o usuário precisa ter acesso ao daemon
Docker ou executar o serviço com uma instalação local autorizada. Isso é uma
limitação do host, não uma dependência do domínio financeiro.

## Custo e escopo

O MVP foi desenhado para custo operacional zero: software open-source, banco e
modelo local. Não há OpenAI API, APIs comerciais de LLM, SaaS de autenticação,
WhatsApp Business Cloud obrigatório, Open Finance ou integrações bancárias. A
interface de providers deixa essas substituições para uma fase futura sem
acoplar o domínio financeiro a elas.
