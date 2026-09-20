# ADR 0002 — Limites das integrações conversacionais

## Status

Aceito.

## Decisões

- O adaptador de canal converte a mensagem externa para um envelope interno com
  `provider`, `sender_id`, `external_message_id` e texto.
- O agente conversa com o FastAPI por HTTP autenticado com `X-Agent-Token` e
  cabeçalhos de identidade. Ele não recebe credenciais do PostgreSQL.
- O backend normaliza o número, consulta `whatsapp_identities` e deriva o usuário.
- Toda operação usa as mesmas regras financeiras dos endpoints web.
  `agent_messages` registra o envelope externo e `agent_tool_calls` registra
  individualmente intenção, tool, status e referências de resultado.
- Baileys fica atrás de `WhatsAppProvider`; o domínio não conhece detalhes do
  WhatsApp Web. Um provider futuro para Cloud API poderá substituir o atual.
- O provider de LLM será definido no pacote `agent` e exporá uma interface comum;
  Ollama é o primeiro adaptador local.

## Operações de risco

Exclusão em massa, reset, alterações em massa e exclusão de contas/histórico não
devem ser executados por uma única interpretação. O agente deve criar uma ação
pendente com token de confirmação e só então chamar uma tool destrutiva.
