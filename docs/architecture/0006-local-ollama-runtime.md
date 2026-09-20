# ADR 0006 — Runtime local do Ollama no desenvolvimento

## Status

Aceito para o ambiente local atual.

## Contexto

O provider Ollama precisa permanecer substituível e não deve virar uma
dependência do domínio financeiro. Neste host, a instalação nativa exigiu
`sudo` interativo, indisponível para o processo automatizado, e os recursos
livres recomendaram um modelo menor durante a validação.

## Decisão

- O Ollama roda localmente em um container separado chamado
  `personal-finance-ollama`, publicado em `127.0.0.1:11434` e persistido no
  volume `personal-finance-ollama`.
- O backend e o runner continuam falando apenas com o endpoint configurável
  `OLLAMA_BASE_URL`; o domínio não conhece Docker nem o nome do container.
- O modelo validado neste host é `qwen2.5:3b`. `qwen2.5:7b` continua sendo uma
  opção para máquinas com mais memória, sem alteração no contrato do provider.
- O container do Ollama não foi adicionado como dependência obrigatória ao
  `docker-compose.yml` da aplicação; isso mantém o web MVP utilizável sem LLM.

## Consequências

O runtime pode ser reiniciado sem perder o modelo, e a aplicação web continua
isolada do agente. O processo Hermes e o pareamento WhatsApp permanecem fora
deste ADR e não foram iniciados no Ciclo 1.
