# ADR 0005 — Revisão de integridade e limites do MVP

## Status

Aceito em 20/09/2026.

## Contexto

Uma revisão transversal do domínio, API, agente, frontend, migrations e operação
local encontrou uma base coerente, mas também regras importantes protegidas
somente no código, auditoria insuficiente para mensagens com várias tools e
alguns fluxos web incompletos. Em um produto financeiro, esses pontos precisam
falhar de forma segura mesmo quando há concorrência, retry ou um cliente mal
comportado.

## Decisões

### Integridade financeira no banco

- Valores de transações, transferências, orçamentos e metas possuem constraints
  de sinal no PostgreSQL.
- Tipos, origens e estados possuem domínios fechados também no banco.
- Uma transação comum e uma perna de transferência têm formatos mutuamente
  exclusivos. Transferências exigem contas distintas.
- Chaves de idempotência são únicas por usuário, não globalmente. Assim, dois
  usuários podem usar a mesma chave do cliente sem compartilhar estado.
- Exclusão de transferência marca a entidade pai e suas duas pernas no mesmo
  fluxo, preservando histórico técnico sem afetar saldos.
- Uma conta com saldo diferente de zero não pode ser desativada e desaparecer
  do saldo patrimonial; primeiro é necessário zerá-la por operações explícitas.

Pydantic continua fornecendo erros rápidos e amigáveis; as constraints são a
última linha de defesa, não uma substituição da camada de serviço.

### Proveniência e idempotência

O endpoint web força `source=web` e o endpoint interno força
`source=whatsapp`. O cliente não pode declarar uma origem privilegiada. Tools
de criação procuram primeiro uma operação com a mesma identidade externa e o
service também trata a disputa de unicidade com savepoint.

Schemas de entrada rejeitam campos desconhecidos. Em particular, enviar
`user_id` no corpo não altera nem é silenciosamente aceito; a identidade sempre
vem da sessão ou do vínculo do canal. Datas relativas são marcadores e só são
convertidas no backend, usando o timezone persistido do usuário.

A identidade idempotente do canal é formada por provider, remetente, ID da
mensagem e operação. Chaves antigas continuam reconhecidas para não duplicar
movimentos já persistidos antes desta revisão.

### Auditoria do agente

`agent_messages` representa o envelope externo, identificado por provider,
remetente e ID externo. `agent_tool_calls` registra cada tool separadamente com
usuário derivado, intenção, nome, sucesso/erro, timestamp e referências para
transação ou transferência. Texto e payload financeiro não são copiados para a
auditoria.

A mutação financeira e a linha de sucesso são commitadas juntas. Em erro, a
operação financeira sofre rollback e o erro técnico é registrado em uma nova
transação.

### Categorias, relatórios e transferências

- Orçamentos e dashboards agregam subcategorias na categoria raiz.
- Despesas sem categoria aparecem explicitamente em relatórios e não somem do
  detalhamento.
- A listagem geral mostra uma transferência uma única vez, mas o filtro por
  conta continua mostrando a perna relevante daquela conta.
- O frontend possui criação de transferência, filtros completos e relatórios de
  evolução mensal, saldo por conta e planejado versus realizado.

### Camadas de persistência

Não será mantido um pacote `repositories` vazio nem criado um repository
genérico que apenas replique métodos do SQLAlchemy. Neste estágio:

```text
route -> service de domínio -> SQLAlchemy Session -> PostgreSQL
```

Routes cuidam de transporte, autenticação, commit e serialização. Regras que
afetam integridade ou são compartilhadas entre web e agente vivem em services.
Consultas simples e específicas podem permanecer próximas da route; consultas
financeiras reutilizadas ficam no service. Um repository dedicado será criado
quando houver uma segunda fonte de dados, uma política de persistência própria
ou complexidade de consulta que justifique a abstração.

## Consequências

A migration `0002_harden_financial_integrity` é obrigatória antes de executar a
nova aplicação. A arquitetura permanece pequena para o MVP, mas agora protege
as invariantes críticas em mais de uma camada. Auditoria técnica cresce por
tool call; retenção e limpeza desses registros deverão ser definidas antes de
uma implantação de longa duração.
