# ADR 0015 — E2E web em duas viewports

## Contexto

O domínio financeiro já possui cobertura de serviço e API, mas erros de
hidratação, navegação, labels, formulários ou responsividade só aparecem quando
a aplicação é executada em um navegador. O produto também precisa validar o
fluxo de cadastro até o dashboard em telas grandes e pequenas.

## Decisão

Foi adicionado um harness Playwright em `frontend/` com dois projetos:

- Firefox desktop;
- Firefox com viewport e user agent de mobile.

O cenário usa a interface web para criar um usuário novo, abrir o diagnóstico,
salvar e retomar seu rascunho, e percorrer contas, despesa, transferência,
edição de transferência, orçamento, meta e dashboard.
Ele não acessa o PostgreSQL diretamente nem injeta dados financeiros para
validar a UI. Cada execução gera um e-mail de teste novo, e o ambiente de CI
usa uma stack Compose temporária.

O alvo `make frontend-e2e` inicia uma stack Compose temporária em um namespace
único, com credenciais de teste, portas próprias e um volume PostgreSQL isolado.
Por padrão, frontend, API e banco usam `13000`, `18000` e `15432`, publicados
somente em loopback. O frontend E2E executa um build otimizado de produção, sem
HMR ou compilação de rotas durante os cenários. O arquivo `.env` do desenvolvedor
não é carregado pelo backend E2E. A stack é removida ao terminar, inclusive
após falhas normais do teste. As portas podem ser trocadas com `E2E_WEB_PORT`,
`E2E_API_PORT` e `E2E_DB_PORT`.

## Consequências

- O fluxo essencial de web é verificado em desktop e mobile antes de uma
  alteração ser considerada pronta.
- Contas e movimentos E2E ficam apenas no volume descartável do projeto de teste;
  containers, rede, volume e imagens locais são removidos no encerramento,
  restritos ao namespace único criado pelo próprio comando.
- A execução exige Docker, dependências instaladas no frontend e o binário
  Firefox do Playwright (`cd frontend && npx playwright install firefox`).
- Firefox é baixado pelo Playwright e não faz parte da imagem de produção.
- No CI, apenas o binário do Firefox é instalado pelo Playwright; as bibliotecas
  do runner Ubuntu são reutilizadas. Isso evita que o instalador tente alterar
  o sistema operacional durante o job e falhe antes de executar os testes.
- Axe verifica violações WCAG 2 A/AA e o menu mobile tem cobertura automatizada
  de teclado para foco inicial, contenção de Tab/Shift+Tab, fechamento por
  Escape e retorno ao acionador. Isso não substitui a auditoria manual dos
  demais fluxos com teclado e leitor de tela, que continua no roadmap.
