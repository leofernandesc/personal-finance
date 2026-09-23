# ADR 0023: Restringir o smoke Hermes às tools financeiras de leitura

## Status

Aceita.

## Contexto

O smoke local executa um prompt no Hermes com acesso ao plugin financeiro. A
mensagem padrão consulta o saldo, mas o comando também aceitava prompts
personalizados enquanto registrava tools que criam, editam e excluem dados.
Isso tornava a propriedade “somente leitura” dependente apenas do texto do
prompt, apesar de o smoke usar a identidade de um usuário real.

## Decisão

O script `hermes_local_smoke.sh` define `PERSONAL_FINANCE_READ_ONLY=1`. Quando
essa variável está habilitada, o plugin mantém o catálogo declarado no
manifesto, mas recusa localmente tools cujo método HTTP não seja `GET`, antes de
criar cliente HTTP ou enviar requisição. Isso mantém compatibilidade com o
Doctor do Hermes e impede escrita pelo plugin. A variável fica limitada ao
processo iniciado pelo smoke e não altera o gateway normal.

O script compara a versão instalada no perfil isolado com `agent/plugin.yaml`
e recusa executar se estiverem diferentes, imprimindo o comando para atualizar
o plugin. Mudanças de comportamento do plugin exigem bump de versão para o
smoke não usar silenciosamente uma cópia antiga.

Para manter a resposta final curta no modelo local, o smoke passa
`HERMES_MAX_TOKENS=512` por padrão. `HERMES_SMOKE_MAX_TOKENS` permite ajustar o
valor entre 1 e 2048 apenas no processo one-shot; nenhuma configuração
persistente do Hermes é alterada.

## Consequências

- Prompts personalizados no smoke podem consultar, mas não mutar dados pelo
  plugin financeiro; chamadas de escrita são recusadas antes da API.
- Testes verificam a passagem da configuração, permitem uma consulta GET e
  provam que operações de escrita não chamam o backend.
- A proteção limita-se às tools deste plugin; o smoke deve continuar usando o
  perfil Hermes isolado documentado.
- Perfis com uma versão antiga do plugin falham antes de iniciar o modelo ou
  acessar a API.
- O limite de saída reduz o risco de uma resposta extensa prender um modelo
  local lento, sem alterar o limite do gateway normal.
