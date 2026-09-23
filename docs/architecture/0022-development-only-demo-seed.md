# ADR 0022: Restringir o seed de demonstração a ambientes locais

## Status

Aceita.

## Contexto

O seed cria a conta `demo@personal-finance.dev` com a senha pública `demo1234`.
É útil para desenvolvimento e testes visuais, mas uma execução acidental em um
ambiente compartilhado exporia uma conta financeira previsível.

## Decisão

`app.seed_demo` só pode executar quando `ENVIRONMENT` for `development` ou
`test`. O ambiente é verificado antes de abrir uma sessão ou consultar o banco.
O comando falha de forma explícita em `staging` e `production`; usuários demo
preexistentes não são apagados automaticamente.

## Consequências

- O seed continua simples e idempotente para desenvolvimento local.
- A CI consegue exercitar o bloqueio sem conectar a nenhum banco.
- Antes de promover uma instalação existente a ambiente compartilhado, o
  operador ainda deve verificar manualmente se uma conta demo já foi criada.
- A conta demo e sua senha nunca devem ser habilitadas em uma instalação
  compartilhada.
