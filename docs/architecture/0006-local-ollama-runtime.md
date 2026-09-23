# ADR 0006 — Runtime local do Ollama no desenvolvimento

## Status

Aceito para o ambiente local atual.

## Contexto

O provider Ollama precisa permanecer substituível e não deve virar uma
dependência do domínio financeiro. Neste host, a instalação nativa exigiu
`sudo` interativo, indisponível para o processo automatizado, e os recursos
livres recomendaram um modelo menor durante a validação.

## Decisão

- O Ollama roda localmente no Compose opcional
  `docker-compose.ollama.yml`; a porta publicada no host é explicitamente
  `127.0.0.1:11434`, e os modelos ficam no volume nomeado
  `personal-finance-ollama`.
- Dentro do container, `OLLAMA_HOST=0.0.0.0:11434` permite o tráfego da rede
  isolada `personal-finance-ollama-network`; ela não é compartilhada com o
  PostgreSQL/backend. Não publique a porta sem especificar o IP do host, pois
  isso pode expor a API a outras máquinas da rede.
- `make ollama-up` inicia o serviço sem torná-lo dependência da aplicação web;
  `make ollama-down` para o container e preserva o volume.
- O backend e o runner continuam falando apenas com o endpoint configurável
  `OLLAMA_BASE_URL`; o domínio não conhece Docker nem o nome do container.
- O modelo validado para o gateway neste host é `llama3.2:3b`, com janela de
  contexto observada de 131.072 tokens. `qwen2.5:3b` continua útil no smoke
  runner isolado, mas sua janela de 32.768 tokens não atende ao requisito atual
  de contexto do Hermes.
- O container do Ollama não foi adicionado como dependência obrigatória ao
  `docker-compose.yml` da aplicação; isso mantém o web MVP utilizável sem LLM.

## Consequências

O runtime pode ser reiniciado sem perder o modelo, e a aplicação web continua
isolada do agente. Um container anterior com publicação em todas as interfaces
foi renomeado e mantido parado; o Compose novo aplica a restrição de loopback e
o CI protege esse contrato. O processo Hermes e o pareamento WhatsApp permanecem
fora deste ADR.
