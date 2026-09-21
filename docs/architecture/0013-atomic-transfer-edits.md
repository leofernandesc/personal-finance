# ADR 0013 — Edição atômica de transferências

## Contexto

Uma transferência é uma entidade patrimonial com duas transações vinculadas:
uma perna de saída e uma perna de entrada. Permitir editar somente uma dessas
linhas poderia alterar saldos de forma incorreta ou transformar o movimento em
uma receita/despesa.

## Decisão

O recurso `PATCH /api/v1/transfers/{id}` recebe a alteração da transferência e
o serviço `update_transfer` aplica, na mesma sessão e commit:

- origem e destino autorizados do próprio usuário;
- valor positivo em `Decimal`;
- descrição e data;
- conta, valor, descrição e data nas duas pernas vinculadas.

O serviço valida que a transferência está ativa, possui exatamente as pernas
`out` e `in` e não permite origem igual ao destino. A API não expõe edição de
uma perna isolada. O formulário web usa o mesmo fluxo e continua exibindo a
transferência como neutra para o patrimônio.

## Consequências

Alterações de transferências preservam a integridade do saldo por conta e a
distinção entre movimentação patrimonial e receita/despesa. O histórico mantém
uma única linha representativa, enquanto o banco conserva as duas pernas para
cálculo. A edição conversacional continua fora deste incremento até existir
uma confirmação de intenção específica para transferências.
