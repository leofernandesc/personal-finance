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
| M–O. Mensagem WhatsApp cria despesa e atualiza dashboard | Código pronto; canal pendente | tool, FastAPI, PostgreSQL e idempotência validados; falta sessão Hermes/Baileys real |
| P–Q. Consulta de transporte responde com dados reais | Código pronto; canal pendente | `get_category_summary` consulta o backend; falta round trip no WhatsApp real |
| R. Reentrega não duplica transação | Concluído no backend | chave por usuário/mensagem e teste em PostgreSQL |

O MVP web está utilizável. O MVP conversacional só deve ser declarado aceito
depois dos dois round trips reais pelo WhatsApp descritos em
[`validation.md`](validation.md).

## Próximos passos priorizados

### P0 — fechar o milestone conversacional

1. Instalar e executar Ollama no host com um modelo adequado a português e
   tool calling.
2. Instalar/configurar Hermes e validar o plugin com a versão real disponível.
3. Parear uma sessão de desenvolvimento WhatsApp Web/Baileys.
4. Executar os cenários M–R de ponta a ponta e anexar as evidências sanitizadas
   ao documento de validação.

### P1 — segurança operacional

1. Substituir o vínculo manual de telefone por um desafio de posse antes de
   preencher `verified_at`.
2. Definir expiração/retenção para sessões e logs do agente, além de rotina de
   limpeza.
3. Preparar backup/restore do PostgreSQL e validar restauração, não apenas o
   backup.
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

Open Finance, OCR, investimentos avançados, cobrança e aplicativos nativos
continuam fora do escopo deste MVP.
