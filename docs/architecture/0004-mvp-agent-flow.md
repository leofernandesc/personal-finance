# ADR 0004 — Fluxo conversacional do MVP

## Status

Aceito.

## Contexto

O primeiro milestone conversacional precisa provar que uma mensagem em português
chega ao backend e vira uma operação financeira real, sem permitir que o modelo
acesse o PostgreSQL ou altere a identidade do usuário. O mesmo limite deve
servir tanto ao Hermes quanto ao smoke runner local.

## Fluxo de escrita

```text
WhatsApp/Baileys
  -> Hermes recebe mensagem e contexto do canal
  -> OllamaProvider retorna intenção estruturada
  -> tool create_transaction
  -> cliente HTTP com token + telefone + message ID
  -> FastAPI resolve WhatsAppIdentity
  -> service valida conta, categoria, Decimal, data e usuário
  -> PostgreSQL grava Transaction(source=whatsapp)
  -> Hermes apresenta somente a resposta do backend
```

O `message_id` é enviado como cabeçalho e também persiste em `agent_messages`.
A transação usa uma chave única por usuário, provider, remetente, mensagem e
operação. Se a mesma
mensagem for entregue novamente, o service retorna a transação existente e o
backend informa `replayed`, sem criar uma segunda operação.

Datas relativas trafegam como marcadores (`today`, `yesterday`, `tomorrow`) e
são resolvidas pelo backend a partir do timezone do usuário. O modelo não
converte “ontem” usando o relógio do host.

## Fluxo de consulta

Consultas como “quanto gastei este mês?” chamam `get_month_summary`. A soma é
executada por SQLAlchemy no backend, que devolve receitas, despesas e economia.
O LLM apenas transforma os números retornados em uma resposta em linguagem
natural; ele não calcula nem usa histórico de conversa como fonte de verdade.

## Limites de segurança

- O plugin só conhece endpoints HTTP e schemas de tools.
- Nenhuma credencial de PostgreSQL é carregada pelo pacote `agent`.
- `user_id` é derivado de sessão web ou de `WhatsAppIdentity` autenticada.
- Conta e categoria são resolvidas por nome dentro do usuário e retornam erro
  explícito se não existirem.
- O MVP não expõe exclusão em massa, reset ou alteração em massa.
- A alteração/exclusão conversacional é unitária; o prompt exige confirmação
  antes de excluir e recomenda consulta prévia para localizar um ID.

## Evolução

O protocolo `LLMProvider` permite trocar Ollama por llama.cpp, vLLM ou um
servidor OpenAI-compatible. O protocolo `WhatsAppProvider` permite trocar a
ponte Baileys por WhatsApp Cloud API. Essas mudanças não devem entrar em
`app/services/finance.py` nem nos modelos financeiros.
