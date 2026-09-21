# Roadmap e critérios de aceite

Este documento separa funcionalidades implementadas de integrações que ainda
dependem de processos externos. “Código pronto” não significa “canal validado”.

## Revisão do MVP

| Critério | Estado | Evidência principal |
| --- | --- | --- |
| A–B. Cadastro, login e logout | Concluído | sessão local, Argon2 e testes de API |
| C–G. Contas, categorias, receitas, despesas e transferências | Concluído | API, UI e testes de saldo/duas pernas |
| H–J. Dashboard, saldo e gastos por categoria | Concluído | dashboard responsivo e cálculos no backend |
| K–L. Orçamentos e metas | Concluído | CRUD essencial, progresso e agregação de subcategorias |
| Diagnóstico inicial e edição posterior | Ciclo 2A concluído em código | 13 etapas, 69 perguntas, rascunho por etapa, consentimento, dependências condicionais, resumo determinístico e isolamento por usuário |
| M–O. Mensagem WhatsApp cria despesa e atualiza dashboard | Ciclo 1 concluído; canal pendente | Ollama + runner, tool, FastAPI, PostgreSQL e idempotência validados; falta sessão Hermes/Baileys real |
| P–Q. Consulta de transporte responde com dados reais | Ciclo 1 concluído; canal pendente | `get_category_summary` retornou `R$ 78,00` pelo backend; falta round trip no WhatsApp real |
| R. Reentrega não duplica transação | Concluído no backend | chave por usuário/mensagem e teste em PostgreSQL |

O MVP web está utilizável. O MVP conversacional só deve ser declarado aceito
depois dos dois round trips reais pelo WhatsApp descritos em
[`validation.md`](validation.md).

## Próximos passos priorizados

O Ciclo 1 foi concluído localmente em 20/09/2026. O Ollama foi executado em
container separado por falta de instalação nativa sem `sudo` interativo; o
modelo validado foi `qwen2.5:3b`, adequado aos recursos disponíveis nesta
máquina. O Ciclo 2A fortaleceu o diagnóstico e o onboarding sem alterar o
domínio financeiro. O próximo milestone de integração é o Ciclo 3, que ainda
depende do gateway Hermes e do pareamento do WhatsApp.

### Ciclo 2A — diagnóstico e onboarding

Concluído em código e coberto por testes locais:

1. validação do questionário alinhada aos campos obrigatórios e às opções;
2. limpeza de respostas que deixam de ser aplicáveis;
3. onboarding orientado sem bloquear o dashboard;
4. edição de nome e fuso horário em Configurações;
5. resumo determinístico em `GET /diagnostic/summary`;
6. card de resumo no diagnóstico e no dashboard;
7. documentação da decisão e dos limites de documentos.

Antes de declarar o ciclo aceito, conferir manualmente o fluxo em desktop e
mobile, incluindo rascunho, dívidas, edição e resumo.

### Ciclo 3 — fechar o milestone conversacional

Estado atual: preparação técnica implementada; round trip ainda pendente.

1. Manter Ollama local (host ou container separado) com um modelo adequado a
   português, tool calling e janela mínima de 64.000 tokens. O Ciclo 1 validou
   `qwen2.5:3b` no runner, mas o gateway deste host usará `llama3.2:3b`, com
   janela de 131.072 tokens.
2. Manter o plugin Hermes validado pela versão real disponível e o bridge
   configurado em `127.0.0.1:3300`, separado do frontend em `3000`.
3. Parear uma sessão de desenvolvimento WhatsApp Web/Baileys usando um número
   controlado e manter a allowlist explícita.
4. Fazer `make cycle3-ready` passar sem warnings.
5. Executar os cenários M–R de ponta a ponta e anexar evidências sanitizadas ao
   documento de validação.

### P1 — segurança operacional

1. Desafio de posse implementado: código HMAC temporário, limite de tentativas,
   expiração, bloqueio das tools financeiras enquanto pendente e revogação ao
   desvincular. Ainda falta executar esse fluxo no WhatsApp real com um número
   autorizado.
2. Retenção definida e rotina de limpeza implementada em
   `app.maintenance`; falta apenas escolher e agendar o scheduler de produção
   conforme a política de retenção do serviço.
3. Backup/restore local implementados com checksum, confirmação explícita e
   validação em banco temporário. Ainda falta definir retenção e armazenamento
   cifrado para produção.
4. Definir configuração de produção com TLS, cookies seguros, hosts e origens
   explícitos.

### P1 — qualidade do produto

1. Adicionar testes E2E de navegador para cadastro, lançamento, transferência,
   orçamento e meta em viewport desktop e mobile.
2. Fazer auditoria manual de teclado, foco, leitor de tela e contraste.
3. Adicionar paginação por cursor ao histórico antes de volumes grandes.
4. Criar fluxo explícito para editar uma transferência inteira, mantendo as
   duas pernas atômicas.

### P2 — evolução controlada

- Adapters reais adicionais para `LLMProvider` e `WhatsAppProvider` somente
  quando houver necessidade de troca.
- Métricas e tracing sem descrições, números de telefone ou payloads
  financeiros em logs.
- Imports e automações mantendo a mesma regra de proveniência aplicada a web e
  WhatsApp.

O histórico imutável de versões do diagnóstico, exportação/exclusão dos dados,
painel de consultor e recebimento seguro de documentos ficam fora do MVP atual
e só devem ser planejados depois de definir papéis, retenção e auditoria.

Open Finance, OCR, investimentos avançados, cobrança e aplicativos nativos
continuam fora do escopo deste MVP.
