# Operação do agente local

Este documento descreve a fronteira entre o processo Hermes, o modelo local e a
API financeira. O pacote `agent/` é um adaptador de integração, não uma segunda
implementação das regras financeiras.

## Componentes

| Componente | Responsabilidade | Não pode fazer |
| --- | --- | --- |
| `WhatsAppProvider` | transportar mensagem, telefone e ID externo | escolher usuário financeiro |
| Hermes | memória conversacional, roteamento e execução de tools | acessar PostgreSQL ou gerar SQL |
| `OllamaProvider` | extrair intenção e parâmetros estruturados | calcular saldo ou persistir dados |
| `BackendFinanceClient` | chamar a API com headers de identidade | contornar autenticação |
| FastAPI | autorizar, validar, calcular e persistir | confiar em `user_id` do modelo |

## Contexto de identidade

O cliente HTTP lê o contexto da sessão Hermes, quando disponível:

- `HERMES_SESSION_PLATFORM`;
- `HERMES_SESSION_USER_ID` ou `HERMES_SESSION_CHAT_ID`;
- `HERMES_SESSION_MESSAGE_ID`.

Para o WhatsApp, o valor vira `X-Agent-Sender-Id`. O backend normaliza o número,
procura uma linha ativa em `whatsapp_identities` e deriva o `User`. Um número
sem vínculo recebe erro e não pode registrar operações.

O `X-Agent-Message-Id` é a fronteira de idempotência. Nunca reutilize um ID para
representar duas mensagens distintas. O cliente recusa chamadas sem remetente
ou ID externo para não abrir um caminho sem proteção contra reentrega.

O vínculo feito pela interface web é intencionalmente manual no MVP local e não
preenche `verified_at`. Antes de qualquer uso fora de desenvolvimento, adicione
um desafio de posse do número no provider do canal.

## Tools disponíveis

O plugin registra as seguintes tools no toolset `personal_finance`:

```text
create_transaction       update_transaction       delete_transaction
create_transfer           get_accounts             get_categories
get_transactions          get_balance              get_month_summary
get_category_summary      get_budget_status        create_budget
create_goal
```

As tools de leitura devolvem dados calculados pela API. As tools de mutação não
aceitam SQL, `user_id` ou IDs de conta/categoria inventados pelo prompt. Para
operações por nome, o backend resolve a entidade do próprio usuário e retorna
as opções existentes em caso de ambiguidade.

Para “hoje”, “ontem” e “amanhã”, a tool envia `relative_date`. A API converte o
marcador com o timezone do usuário; o modelo não deve produzir uma data absoluta
usando o relógio do processo Hermes.

Cada execução cria uma linha em `agent_tool_calls`, inclusive consultas e
falhas. A auditoria contém metadados técnicos e referências, não o texto da
mensagem nem o payload financeiro.

## Configuração

No shell do processo Hermes:

```bash
export PERSONAL_FINANCE_API_URL=http://127.0.0.1:8000/api/v1/integrations/agent
export AGENT_SHARED_SECRET='o-mesmo-valor-do-.env'
```

Verifique o plugin antes de habilitá-lo:

```bash
hermes plugins doctor ./agent --ci
mkdir -p .hermes/plugins
ln -sfn "$(pwd)/agent" .hermes/plugins/personal-finance
export HERMES_ENABLE_PROJECT_PLUGINS=1
```

Execute o Hermes a partir da raiz do monorepo para que o plugin local seja
descoberto. Para uma instalação permanente, copie o diretório `agent/` para
`~/.hermes/plugins/personal-finance/` e habilite-o com o CLI. O plugin pode ser
validado sem uma conta WhatsApp real pelo doctor e pelos testes unitários. Para
o canal, pareie o WhatsApp Web no fluxo de gateway do Hermes, habilite o toolset
`personal_finance` para essa plataforma e mantenha o backend acessível no
endereço configurado.

## Ollama

```bash
ollama serve
ollama pull qwen2.5:7b
```

O adaptador chama `POST /api/chat` e solicita JSON conforme schema. A escolha do
modelo é configuração (`OLLAMA_MODEL`), não regra financeira. O prompt em
`agent/prompts/system.md` instrui o modelo a consultar tools e nunca inventar
contas, categorias, usuários ou cálculos.

Para o Hermes gateway, configure o provider local pelo wizard:

```bash
hermes model
```

Selecione **Custom endpoint**, com `http://127.0.0.1:11434/v1`, uma chave
placeholder como `none`, o nome do modelo baixado e contexto `64000`. O Hermes
faz as chamadas OpenAI-compatible para Ollama e usa as tools registradas pelo
plugin; o adapter nativo em `agent/llm/ollama.py` é usado pelo runner isolado e
permite trocar o provider sem contaminar o domínio.

## Smoke runner

O runner é útil para isolar o caminho Ollama → FastAPI antes de parear o canal:

```bash
PYTHONPATH=. backend/.venv/bin/python -m agent.runner \
  --sender +5592999999999 \
  --message-id smoke-001 \
  'Gastei R$ 25 com almoço.'
```

O telefone precisa estar vinculado ao usuário demo ou a um usuário autenticado.
Para testar idempotência, repita o mesmo `--message-id` e confirme que o
backend retorna `replayed: true` e mantém uma única transação.

## Escritas destrutivas

O plugin não registra ferramentas de exclusão em massa, reset, exclusão de
contas ou alteração em massa. `delete_transaction` é unitária e o prompt exige
confirmação explícita. Caso a UX conversacional cresça para ações amplas, a
implementação deve usar `PendingAgentAction` com expiração e token de
confirmação antes de executar a mutação.
