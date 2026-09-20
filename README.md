# Personal Finance

Aplicação local de controle de finanças pessoais com dashboard web, API
multiusuário e uma camada conversacional preparada para Hermes, Ollama e
WhatsApp Web. O objetivo do MVP é registrar e consultar a vida financeira sem
entregar a fonte de verdade a um modelo de linguagem.

## Estado atual

O domínio financeiro, a API, a autenticação local, o dashboard responsivo,
orçamentos, metas e o plugin do Hermes já estão implementados. As validações
automatizadas passam no repositório. O fluxo conversacional possui um adaptador
Ollama e tools HTTP reais para o FastAPI; o pareamento do WhatsApp e a execução
do modelo dependem da instalação local do Hermes/Ollama e, por isso, devem ser
validados no ambiente que tiver esses processos disponíveis.

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

Transferências têm uma entidade própria e duas pernas de transação (`out` e
`in`), portanto não são contabilizadas como receita ou despesa. Valores usam
`NUMERIC(14,2)` no PostgreSQL e `Decimal` no Python. Datas relativas usam o
timezone do usuário.

## Stack

- Frontend: Next.js App Router, TypeScript, Tailwind CSS, Recharts, React Hook
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
- Ollama instalado localmente;
- um modelo que responda a saída estruturada, por exemplo `qwen2.5:7b`;
- um ambiente de teste com WhatsApp Web/Baileys pareado.

## Configuração inicial

Na raiz do repositório:

```bash
cp .env.example .env
```

Altere, no mínimo, `AGENT_SHARED_SECRET` em qualquer ambiente compartilhado.
Para desenvolvimento local, os valores do exemplo são suficientes.

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

Para acompanhar ou parar os serviços:

```bash
docker compose logs -f backend
docker compose down
```

`docker compose down` preserva o volume nomeado; use `docker compose down -v`
somente quando quiser apagar o banco local de demonstração.

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
não duplica o usuário demo.

## Fluxos principais

### Web

1. Crie uma conta em `/register` ou use o usuário demo.
2. Faça login em `/login`.
3. Cadastre contas e, se necessário, ajuste categorias.
4. Registre receitas, despesas e transferências em **Transações**.
5. Consulte saldo, fluxo, categorias, orçamentos e metas no dashboard.

### Hermes + Ollama + WhatsApp

O plugin vive em `agent/`. Ele registra 13 tools no toolset
`personal_finance`. Todas chamam endpoints `/api/v1/integrations/agent/*` com:

- `X-Agent-Token` para autenticação entre processos;
- `X-Agent-Provider` para identificar o canal;
- `X-Agent-Sender-Id` para resolver o telefone;
- `X-Agent-Message-Id` para idempotência.

Antes de mandar mensagens, vincule o telefone autenticado ao usuário pela tela
**Integrações**, ou pela API autenticada:

```bash
curl -X POST http://localhost:8000/api/v1/integrations/whatsapp/link \
  -H 'Content-Type: application/json' \
  -H 'Cookie: pf_session=<sessao-da-web>' \
  -d '{"phone_e164":"+5592999999999"}'
```

Verifique o plugin e habilite a descoberta local do monorepo:

```bash
hermes plugins doctor ./agent --ci
mkdir -p .hermes/plugins
ln -sfn "$(pwd)/agent" .hermes/plugins/personal-finance
export HERMES_ENABLE_PROJECT_PLUGINS=1
```

O doctor deve confirmar o manifesto, o import e as 13 tools. Execute o Hermes a
partir da raiz do repositório para que o plugin local seja descoberto. Para uma
instalação permanente fora do monorepo, copie `agent/` para
`~/.hermes/plugins/personal-finance/` e habilite `personal-finance` com o CLI.
No Hermes, habilite o toolset `personal_finance` para a plataforma WhatsApp
conforme a configuração da sua instalação e inicie o gateway. A ponte
WhatsApp/Web é responsabilidade do provider do canal; o domínio financeiro não
conhece Baileys.

Para Ollama:

```bash
ollama serve
ollama pull qwen2.5:7b
hermes model
```

No wizard `hermes model`, selecione **Custom endpoint** e configure:

```text
Base URL:      http://127.0.0.1:11434/v1
API key:       none
Model:         qwen2.5:7b (ou o modelo baixado)
Contexto:      64000
```

O endpoint customizado é o caminho usado pelo Hermes para chamadas OpenAI-
compatible. O `agent/llm/ollama.py` usa a API nativa `/api/chat` no smoke runner
e mantém a mesma fronteira `LLMProvider`. Para máquinas sem muita memória, um
modelo menor pode ser usado alterando `OLLAMA_MODEL`, desde que ele suporte
tool-calling e o contexto configurado.
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
npm run typecheck
npm run build
```

O build do frontend valida as rotas App Router e o typecheck valida os contratos
TypeScript. O lint visual adicional deve ser feito no navegador em desktop e
mobile, conferindo teclado, foco, estados vazios, loading, erro e feedback de
salvamento.

## Decisões e documentação

- [`docs/architecture/0001-foundation.md`](docs/architecture/0001-foundation.md):
  fonte de verdade, dinheiro, transferências, sessão e timezone.
- [`docs/architecture/0002-integration-boundaries.md`](docs/architecture/0002-integration-boundaries.md):
  limites entre canal, agente, LLM e backend.
- [`docs/architecture/0003-frontend-direction.md`](docs/architecture/0003-frontend-direction.md):
  direção visual, responsividade e acessibilidade.
- [`docs/architecture/0004-mvp-agent-flow.md`](docs/architecture/0004-mvp-agent-flow.md):
  fluxo comprovável de tool call, idempotência e operação local.
- [`docs/agent.md`](docs/agent.md): configuração operacional do Hermes, Ollama e
  adapters de WhatsApp.
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
