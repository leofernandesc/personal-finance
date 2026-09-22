# ADR 0008 — Diagnóstico financeiro inicial

## Status

Aceito.

## Contexto

O Organiza Finanças precisa conhecer a situação atual do usuário antes de
orientar sua organização financeira. O formulário possui 13 seções e 69
perguntas, incluindo dados de renda, despesas, dívidas, patrimônio, metas,
comportamento e consentimentos.

O preenchimento pode durar de 15 a 20 minutos e as respostas são sensíveis.
Também é necessário permitir que o usuário altere o diagnóstico quando sua
situação mudar.

## Decisão

- Após o cadastro, o usuário é direcionado ao diagnóstico, mas pode continuar
  para o dashboard sem concluir.
- O formulário é dividido por etapas e salva um rascunho ao avançar ou ao
  escolher “Salvar e continuar depois”.
- Etapas já alcançadas podem ser reabertas livremente pelo progresso no desktop
  ou pelo seletor de etapas no celular; etapas ainda não visitadas continuam
  sujeitas à validação sequencial.
- A data de nascimento é digitada e exibida em `DD/MM/AAAA`; ao carregar
  respostas antigas e ao enviar/salvar, o frontend converte para ISO (`AAAA-MM-DD`),
  mantendo compatibilidade com a API e com os rascunhos já existentes.
- Cada usuário possui uma única linha em `financial_diagnostics`, com respostas
  validadas pelo Pydantic em `JSONB`, versão do formulário e status.
- Os dois consentimentos ficam em colunas próprias, com versão e data, para
  preservar uma trilha clara do aceite.
- A seção de detalhamento das dívidas só é exibida quando o usuário informa que
  possui dívidas. Ao responder “Não”, os detalhes condicionais são removidos.
- As respostas não criam contas, transações, orçamentos ou metas
  automaticamente. O diagnóstico é informativo e fica separado do domínio
  financeiro operacional.
- A edição posterior acontece pela rota **Meu diagnóstico** e pelo painel de
  **Configurações**.
- O perfil permite alterar nome e fuso horário sem reescrever diagnósticos já
  concluídos.
- Após a conclusão, `GET /diagnostic/summary` apresenta uma leitura
  determinística das respostas, com valores calculados pelo backend e sem
  recomendações de investimento.
- A seção de documentos registra apenas disponibilidade e forma preferida de
  envio. O MVP não recebe arquivos e não deve receber credenciais.

## Consequências

- O preenchimento parcial pode ser retomado sem perder as etapas já salvas.
- A estrutura JSONB permite evoluir o questionário com versões sem criar 69
  colunas rígidas ou misturar respostas com transações financeiras.
- Relatórios analíticos futuros poderão extrair campos selecionados sem
  alterar a fonte de verdade financeira.
- O backend continua responsável por autenticação, autorização, validação e
  isolamento entre usuários; o frontend apenas conduz a experiência.
