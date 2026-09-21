# ADR 0014 — Paginação por cursor no histórico

## Contexto

O histórico de transações pode crescer continuamente. Um limite fixo sem um
cursor obriga o cliente a buscar sempre a mesma primeira página e aumenta o
tempo de resposta conforme o usuário acumula movimentos.

## Decisão

`GET /api/v1/transactions` mantém a lista JSON existente para compatibilidade e
aceita `limit` e `cursor`. Quando houver mais resultados, a API devolve um
cursor opaco no header `X-Next-Cursor`. O cursor carrega a ordenação e a última
chave composta da página:

- data, criação e UUID para ordenações por data;
- valor, data, criação e UUID para ordenações por valor.

O backend aplica keyset pagination depois de todos os filtros do usuário. Um
cursor inválido ou usado com outra ordenação retorna `422`; ele nunca altera a
autorização nem permite consultar dados de outro usuário. A tela de transações
usa o header para oferecer “Carregar mais”, sem substituir a resposta em lista
que as tools do agente já consomem.

## Consequências

O histórico deixa de depender de offset e permanece estável quando novas
transações são inseridas entre duas páginas. O cliente precisa reenviar os
mesmos filtros e ordenação ao usar o cursor; a API valida isso. A paginação não
altera cálculos de saldo, dashboard ou idempotência.
