# ADR 0010 — Preparação do Ciclo 3 com Hermes e bridge Baileys

## Status

Aceito em 20/09/2026 para o ambiente local de desenvolvimento.

## Contexto

O domínio financeiro já possui uma fronteira HTTP autenticada para tools. O
Ciclo 3 precisa conectar essa fronteira ao Hermes e ao bridge Baileys sem abrir
acesso do agente ao PostgreSQL, sem permitir que o modelo escolha o usuário e
sem confundir a porta do canal com a porta do frontend.

Também foi observado que o modelo pequeno usado no Ciclo 1 pode interpretar
mensagens no runner, mas o runtime Hermes instalado exige uma janela de contexto
mínima de 64.000 tokens para tool calling confiável.

## Decisões

- O plugin em `agent/` registra somente tools HTTP e continua sem driver,
  credencial ou consulta direta ao PostgreSQL.
- O Hermes instalado é responsável pelo ciclo de conversa, pelo provider de
  modelo e pelo adapter Baileys. O adapter local `WhatsAppProvider` continua
  sendo uma fronteira de domínio para futuras implementações, não um segundo
  bridge concorrente.
- A configuração do bridge usa `127.0.0.1:3300`. A porta `3000` fica reservada
  ao frontend Next.js.
- O plugin é habilitado por allowlist (`plugins.enabled`) e o toolset
  `personal_finance` é associado explicitamente à plataforma WhatsApp.
- `qwen2.5:3b` permanece válido para o smoke runner do Ciclo 1. Neste host,
  `llama3.2:3b` é o modelo do gateway, com janela de 131.072 tokens; a checagem
  do Ciclo 3 bloqueia o aceite em máquinas cujo modelo não informe pelo menos
  64.000 tokens de contexto.
- `agent/integration_check.py` é um teste de prontidão somente leitura. Ele
  diferencia código instalado, modelo presente, sessão pareada e bridge
  conectado, sem transformar warnings em falso sucesso.

## Consequências

O web MVP continua independente do Ollama, Hermes e WhatsApp. A troca do modelo
ou do bridge não altera as regras financeiras. O milestone M–R ainda exige
pareamento manual, uma allowlist de desenvolvimento e uma execução real com
mensagens; doctor, testes e readiness não substituem essa evidência.
