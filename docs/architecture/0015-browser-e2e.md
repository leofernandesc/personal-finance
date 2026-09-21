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

O cenário usa a interface web para criar um usuário novo e percorrer contas,
despesa, transferência, edição de transferência, orçamento, meta e dashboard.
Ele não acessa o PostgreSQL diretamente nem injeta dados financeiros para
validar a UI. Cada execução gera um e-mail de teste novo, e o ambiente de CI
usa uma stack Compose temporária.

O `webServer` reaproveita o frontend local quando ele já está em execução e o
inicia quando necessário. O backend e o PostgreSQL continuam sendo pré-requisitos
locais; no CI são iniciados antes do Playwright.

## Consequências

- O fluxo essencial de web é verificado em desktop e mobile antes de uma
  alteração ser considerada pronta.
- O teste local deixa registros de uma conta E2E no banco de desenvolvimento;
  por isso, um banco descartável é recomendado para execução repetida.
- Firefox é baixado pelo Playwright e não faz parte da imagem de produção.
- A cobertura não substitui a auditoria manual de teclado, leitor de tela,
  contraste e comportamento de erros; essa etapa continua no roadmap.
