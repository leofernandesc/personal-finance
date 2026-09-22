# ADR 0018 — Fallback local do Ollama em CPU

## Status

Aceito para desenvolvimento local.

## Contexto

O host de validação não possui o comando Ollama instalado e o instalador padrão
exige `sudo` interativo. A primeira inicialização também tentou descobrir GPU e
encerrou antes de disponibilizar a API. Ainda assim, o Ciclo 3 precisa de uma
forma gratuita e reproduzível de validar o provider local sem alterar o domínio
financeiro.

## Decisão

- Instalar o pacote oficial do Ollama em um diretório do usuário quando não
  houver privilégio para `/usr/local`.
- Iniciar o servidor em `127.0.0.1:11434` com `OLLAMA_LLM_LIBRARY=cpu` quando a
  descoberta de GPU não for confiável.
- Manter os modelos fora do repositório, em um diretório de dados local, e
  selecionar `llama3.2:3b` para o gateway por sua janela de contexto observada
  de 131.072 tokens.
- Permitir que o smoke runner configure o timeout do provider; o padrão de 180
  segundos atende o primeiro carregamento em CPU sem alterar a autorização,
  validação ou persistência financeira.

## Consequências

- O web MVP continua funcionando sem Ollama e o provider permanece substituível.
- A primeira inferência em CPU pode ser lenta e consumir aproximadamente 2,4 GiB
  de memória; o ambiente deve ser monitorado antes de iniciar outros modelos.
- O runtime local não prova disponibilidade do WhatsApp. O bridge, a allowlist,
  o modo `bot` e o round trip autorizado continuam sendo gates separados.
