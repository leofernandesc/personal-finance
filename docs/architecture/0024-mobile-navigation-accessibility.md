# ADR 0024: Acessibilidade do menu de navegação mobile

## Estado

Aceito.

## Contexto

O menu mobile existente era apenas deslocado para fora da tela. Seus links
permaneciam no fluxo de foco e o usuário de teclado não tinha Escape, contenção
do foco nem retorno ao botão de abertura. Isso fazia o menu se comportar de
forma diferente para navegação visual, teclado e tecnologia assistiva.

## Decisão

Manter a implementação leve existente e dar semântica de diálogo modal ao menu:

- o acionador anuncia `aria-expanded` e referencia o diálogo com `aria-controls`;
- ao abrir, o conteúdo principal fica inerte e o foco vai ao primeiro controle;
- Tab e Shift+Tab mantêm o foco dentro do diálogo;
- Escape e o botão de fechar encerram o menu e devolvem foco ao acionador;
- fechado, o painel usa `display: none`, removendo seus controles da navegação.

Os fluxos são cobertos em Playwright no Firefox mobile e o axe continua
verificando WCAG 2 A/AA. Não é adicionada biblioteca de diálogo para esse único
componente.

## Consequências

- Teclado e leitor de tela recebem um limite modal compreensível e testável.
- A implementação customizada de foco precisa permanecer coberta por testes ao
  mudar navegação, controles ou breakpoints.
- Essa cobertura automatizada não substitui teste manual com leitor de tela nem
  revisão de teclado nas demais páginas.
