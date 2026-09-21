# ADR 0007 — Identidade visual Organiza Finanças

## Status

Aceito.

## Contexto

O produto recebeu uma logo própria com lettering marrom e um detalhe circular
rosa. A interface precisava usar essa identidade sem perder a sensação de
clareza, confiança e leitura rápida esperada em um produto financeiro.

## Decisão

- O nome exibido no produto é **Organiza Finanças**.
- A logo original fica versionada em `referências visuais/` e a cópia otimizada
  para uso da aplicação fica em `frontend/public/logo-organiza-financas.png`.
- O fundo principal permanece branco (`#ffffff`), evitando que o rosa da logo
  domine áreas de leitura financeira.
- O marrom é a cor estrutural da marca: navegação, títulos, ações principais e
  elementos de gráfico.
- O rosa é usado com baixa intensidade em foco, seleção, estados ativos,
  destaques e alguns elementos de apoio.
- A paleta semântica mantém cores financeiras legíveis e não depende apenas de
  cor para comunicar receita, despesa ou estado.

## Paleta de referência

| Papel | Cor |
| --- | --- |
| Fundo | `#ffffff` |
| Marrom de marca | `#533129` |
| Marrom escuro | `#3b211c` |
| Rosa de marca | `#e8b8b8` |
| Rosa suave | `#fbf1f1` |
| Texto principal | `#34231f` |
| Borda | `#eadfdd` |

## Consequências

- A logo é um componente compartilhado entre autenticação, sidebar e cabeçalho
  mobile, preservando proporção e texto alternativo.
- Gráficos e cartões usam tokens da marca em vez de cores espalhadas pela UI.
- O ADR 0003 continua válido para hierarquia, responsividade e acessibilidade;
  esta decisão atualiza apenas a identidade cromática e o nome do produto.
