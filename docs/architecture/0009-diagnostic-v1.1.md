# ADR 0009 — Diagnóstico v1.1 e resumo determinístico

## Status

Aceito.

## Contexto

O formulário de diagnóstico já possui 13 etapas, 69 perguntas, rascunho,
consentimentos e edição posterior. A revisão mostrou que perguntas dependentes
precisavam limpar respostas antigas e que o usuário precisava receber uma
leitura útil depois do envio.

As respostas incluem informações pessoais e financeiras. O resumo não pode
depender de um modelo de linguagem, somar valores no navegador ou criar
movimentações financeiras.

## Decisão

- O diagnóstico continua sendo uma linha por usuário com respostas validadas em
  `JSONB`.
- A versão do questionário passa a `2`; respostas existentes continuam
  legíveis e são normalizadas ao serem editadas.
- O backend valida as opções, os campos obrigatórios e as dependências
  condicionais. O frontend conduz a experiência, mas não substitui essa
  validação.
- O preenchimento após o cadastro é orientado, sem bloquear dashboard ou
  lançamentos. Um aviso permanece visível até o diagnóstico ser concluído.
- `GET /diagnostic/summary` calcula margem, dívidas, reserva, sinais e próximos
  passos a partir das respostas concluídas.
- O resumo é determinístico, usa `Decimal`, devolve valores como texto com duas
  casas e identifica sua base como `self_reported_diagnostic`.
- O resumo não recomenda investimentos, não cria contas, transações, metas ou
  orçamentos e não usa Ollama, Hermes ou outra IA.
- Documentos continuam sendo apenas indicados no formulário. O MVP não recebe
  arquivos nem cria links públicos.
- O perfil permite alterar nome e fuso horário em `/auth/me`. O e-mail continua
  imutável nesta etapa, e um diagnóstico concluído mantém sua própria fotografia
  das respostas.
- Não há painel de consultor, papel administrativo ou histórico imutável de
  revisões no MVP atual.

## Consequências

- O usuário recebe orientação inicial sem misturar diagnóstico com o saldo real
  das contas.
- Alterações em respostas condicionais não deixam dados inválidos escondidos no
  JSONB.
- O contrato do resumo pode evoluir sem acoplar a aplicação financeira a um
  provedor de IA.
- Histórico de versões, exportação, exclusão e fluxo de documentos ficam para
  um ciclo posterior com requisitos próprios de segurança e retenção.
