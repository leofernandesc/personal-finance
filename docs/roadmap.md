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

### Regras de acesso revisadas

O cadastro agora exige nome válido, senha de 8 a 128 caracteres e confirmação
idêntica validada no navegador e na API. Login e cadastro permitem revelar ou
ocultar a senha. A senha segue armazenada somente como hash Argon2.

Antes de disponibilizar o cadastro fora do ambiente local, planejar a troca de
senha autenticada, recuperação com token temporário de uso único, verificação
de e-mail quando ela for usada para recuperar acesso e limitação de tentativas
de login/cadastro. Não exibir um link de recuperação até existir um canal de
entrega configurado e validado, mantendo o custo operacional do projeto em
R$ 0.

## Próximos passos priorizados

O Ciclo 1 e o Ciclo 2A estão concluídos no código. Em 22/09/2026, o runtime
opcional do Ollama foi endurecido para bind exclusivo em `127.0.0.1`, com rede
Docker isolada e volume persistente; o modelo `llama3.2:3b` e o plugin Hermes
passam no preflight local. O Ciclo 3 permanece aberto: por escolha confirmada
do usuário, o bridge deve continuar em `self-chat`, sem número na allowlist e
sem round trip real pelo WhatsApp nesta etapa.

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

Estado atual (22/09/2026): API, modelo local, plugin e tool calls já foram
exercitados em fluxos locais; runtime Ollama está limitado ao loopback. O
preflight estrito falha corretamente porque o bridge efetivo ainda está em
`self-chat`. O usuário optou por manter esse modo; nenhuma mensagem real do
WhatsApp foi processada nem será processada pela sessão bot nesta etapa.

1. Manter Ollama local pelo Compose opcional com porta publicada somente em
   `127.0.0.1:11434`; a verificação correspondente agora roda no CI. O gateway
   usa `llama3.2:3b`, com janela observada de 131.072 tokens.
2. Manter o plugin Hermes validado pela versão real disponível e o bridge
   configurado em `127.0.0.1:3300`, separado do frontend em `3000`.
3. Com autorização explícita, permitir um número de teste controlado na
   allowlist e iniciar o bridge em `bot`; sem isso, mantê-lo em `self-chat`.
4. Fazer `make cycle3-ready` passar sem warnings e executar os cenários M–R de
   ponta a ponta, anexando evidências sanitizadas ao documento de validação.

### P1 — segurança operacional

1. Desafio de posse implementado: código HMAC temporário, limite de tentativas,
   expiração, bloqueio das tools financeiras enquanto pendente e revogação ao
   desvincular. Ainda falta executar esse fluxo no WhatsApp real com um número
   autorizado.
2. Retenção definida e rotina de limpeza implementada em `app.maintenance`.
   Unidades opcionais `systemd --user` e o runbook foram adicionados; a
   ativação continua manual e depende da política de retenção, backup e
   restauração do ambiente compartilhado.
3. Backup/restore local implementados com checksum, confirmação explícita e
   validação em banco temporário. Ainda falta definir retenção e armazenamento
   cifrado para produção.
4. Definir configuração de produção com TLS, cookies seguros, hosts e origens
   explícitos.
5. A stack local agora publica PostgreSQL, API e frontend em loopback por
   padrão; testes temporários em celular usam somente o IP LAN específico da
   aplicação e mantêm o banco inacessível pela rede
   ([ADR 0021](architecture/0021-compose-loopback-bindings.md)).

### P1 — qualidade do produto

1. Testes E2E de navegador para cadastro, lançamento, transferência, edição de
   transferência, orçamento, meta e dashboard foram adicionados e passaram em
   Firefox desktop e mobile; o workflow de CI também os executa em uma stack
   temporária.
2. Scan automatizado WCAG 2 A/AA com axe cobre login, cadastro, dashboard e
   transações em desktop e mobile; o teste mobile abre a navegação lateral.
   Ainda falta a auditoria manual de teclado, foco e leitor de tela.
3. Paginação por cursor implementada no histórico da API e no botão “Carregar
   mais” do frontend. O E2E dedicado agora cobre duas páginas, falha transitória,
   retry, preservação da primeira página e ausência de duplicatas em Firefox
   desktop e mobile.
4. Fluxo explícito para editar uma transferência inteira implementado na API,
   no formulário web e coberto pelo E2E, mantendo as duas pernas atômicas.

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
