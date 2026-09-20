# ADR 0003 — Direção visual do produto

## Status

Aceito.

## Direção

O frontend usa uma linguagem editorial e calma: fundo marfim, superfícies claras,
tipografia de alto contraste, azul petróleo como ação primária e verde/terracota
apenas para estados financeiros. A hierarquia prioriza saldo, fluxo do mês e
próximas decisões — não uma parede de gráficos.

- Desktop: navegação lateral compacta e conteúdo em duas colunas.
- Mobile: cabeçalho com menu e cards empilhados; tabelas viram listas roláveis.
- Valores sempre exibem sinal ou rótulo textual, além de cor.
- Gráficos têm resumo textual, tooltips acessíveis e estado vazio explicativo.
- Loading usa skeletons discretos; erros oferecem ação de tentar novamente.
- A tela inicial explica como registrar pelo WhatsApp quando ainda não há dados.
