# ADR 0001 — Fundamentos do MVP

## Status

Aceito.

## Contexto

O produto precisa manter a integridade financeira mesmo quando a entrada vier de
linguagem natural. O modelo de linguagem pode interpretar uma mensagem, mas não
pode decidir autorização, acessar o banco, gerar SQL ou calcular saldos.

## Decisões

- O PostgreSQL é a fonte de verdade; o domínio financeiro fica no backend FastAPI.
- Cada entidade financeira possui `user_id` e as consultas de serviço filtram pelo
  usuário autenticado.
- Dinheiro é armazenado como `NUMERIC(14, 2)` e trafega no Python como `Decimal`.
- Transferências possuem uma entidade pai e duas transações vinculadas: uma perna
  `out` e uma perna `in`. Elas não entram nos totais de receita/despesa.
- Sessões locais usam token aleatório em cookie `HttpOnly`; somente o hash do token
  é persistido.
- Datas relativas são resolvidas com o timezone armazenado no usuário.
- Idempotência é aplicada no backend com chave única e retorno da operação já
  existente quando a mesma mensagem é reprocessada.
- O vínculo WhatsApp é resolvido por `WhatsAppIdentity` antes do agente tocar em
  qualquer tool. O LLM nunca escolhe `user_id`.

## Consequências

O MVP fica executável localmente sem SaaS pago e pode trocar o provedor de LLM ou
WhatsApp sem alterar as regras financeiras. A API precisa continuar sendo a única
porta para tools do agente, inclusive para consultas que poderiam parecer simples
de calcular no prompt.
