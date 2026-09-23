# ADR 0021 — Bind local por padrão no Docker Compose

## Status

Aceito.

## Contexto

A stack de desenvolvimento publicava PostgreSQL, API e frontend em todas as
interfaces do host. Isso tornava o banco e a aplicação acessíveis pela rede
local mesmo quando a pessoa apenas queria usar o produto no próprio computador.
Ao mesmo tempo, existe uma necessidade legítima de abrir a interface em um
celular durante testes responsivos.

## Decisão

- PostgreSQL é publicado somente em `127.0.0.1:5432`.
- API e frontend são publicados em `127.0.0.1` por padrão, configurável pelo
  `APP_BIND_HOST`.
- Para um teste temporário em outro dispositivo, `APP_BIND_HOST` pode apontar
  para o IP LAN específico do host. `ALLOWED_HOSTS`, `CORS_ORIGINS` e
  `NEXT_PUBLIC_API_URL` também precisam incluir esse IP.
- O acesso LAN usa HTTP de desenvolvimento, sem TLS, e deve ser restrito a uma
  rede confiável. Não é uma configuração de produção.
- O CI verifica o bind efetivo da configuração padrão do Compose.

## Consequências

O uso local comum não expõe portas à LAN. Testes em dispositivo físico continuam
possíveis com uma alteração explícita e temporária, sem publicar o banco. A
configuração de produção ainda requer TLS, cookies seguros, hosts e origens
explícitos, conforme o roadmap.
