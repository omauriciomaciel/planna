# Planna — sistema de interface

## Direção

- Sensação: calma doméstica com rigor financeiro — próxima de um caderno de contas bem cuidado, não de um terminal bancário.
- Pessoa: um casal consultando e organizando a vida financeira da casa.
- Tarefa dominante: entender a situação compartilhada e executar uma ação por vez com confiança.
- Assinatura: a transformação `Banco + nota fiscal → visão compartilhada`, usada para explicar de onde vêm os dados e no que eles se tornam.
- Evitar: azul-fintech genérico, gradientes decorativos, glassmorphism, mosaicos de KPIs coloridos e dashboards vazios usados como decoração.

## Paleta

Use somente tokens semânticos definidos em `frontend/src/app/globals.css`.

- `background` — papel quente: `oklch(0.965 0.014 85)`.
- `foreground` — tinta verde-escura: `oklch(0.24 0.025 155)`.
- `card` — folha elevada: `oklch(0.99 0.006 85)`.
- `primary` — verde-caixa: `oklch(0.34 0.07 160)`; reservado para ação principal e identidade.
- `muted` / `muted-foreground` — extrato e metadados.
- `accent` — recibo âmbar discreto; usar apenas quando houver significado.
- `destructive` — erro ou ação destrutiva, nunca decoração.

A distribuição é aproximadamente 60/30/10: papel dominante, tinta/estruturas secundárias e pouco verde de ação. O modo claro é a direção aprovada; não habilitar o modo escuro até substituir os tokens neutros provisórios por equivalentes desta mesma paleta.

## Tipografia e hierarquia

- Corpo e controles: `Avenir Next`, `Avenir`, `Segoe UI`, sans-serif.
- Títulos: `Georgia`, `Times New Roman`, serif — traz o caráter editorial/doméstico.
- Escala: razão aproximada de 1,25, partindo de 14–16 px.
- Display de entrada: 36 px no mobile e 48 px a partir de `sm`, peso 600, entrelinha 1,12 e tracking fechado.
- Título de card: 16 px, peso 500, entrelinha curta.
- Corpo: 16 px; descrições e metadados: 14 px em `muted-foreground`.
- Sobrancelha: 14 px, peso 500, caixa alta, tracking `0.08em`.
- Valores financeiros e contagens futuras devem usar números tabulares.
- Títulos usam `text-wrap: balance`; textos corridos usam `text-wrap: pretty`.

Cada tela tem um único foco. Ele vence por contraste e espaço; elementos secundários recuam por peso e cor antes de ficarem menores.

## Espaçamento e composição

- Unidade-base: 4 px. Use somente múltiplos dessa unidade.
- Densidade: confortável e contida; 8 px entre partes do mesmo campo, 16 px em cards, 20 px entre campos e 24 px entre blocos editoriais.
- Área externa: 16 px no mobile, 32 px a partir de `sm`, 48 px no eixo vertical.
- Largura máxima da entrada: 64 rem; em `lg`, texto flexível + card fixo de 26 rem, separados por 48 px.
- Controles essenciais têm pelo menos 44 px de altura.
- Em telas estreitas, o fluxo vira uma coluna naturalmente; não usar posicionamento absoluto para recompor o layout.

## Profundidade e formas

- Estratégia única: superfícies claras com anéis/bordas discretos. Sem sombras decorativas.
- Inputs são visualmente insetos: fundo transparente sobre o card e borda `input` um pouco mais escura.
- Card: `rounded-xl`, anel de 1 px com `foreground/10`, fundo `card`, espaçamento interno de 16 px.
- Inputs e botões: `rounded-lg`; o raio cresce junto com o tamanho do recipiente.
- Foco: borda `ring` + anel de 3 px a 50%; erro troca para `destructive`.

## Padrões de componentes

- Botão primário — 44 px de altura · 14 px de padding horizontal · `rounded-lg` · texto 14 px/500 · fundo `primary`. Use uma vez como ação dominante do contexto.
- Botão secundário — mesmas medidas · variante `outline` · usado para voltar, sair ou trocar uma escolha.
- Campo de texto — 44 px de altura · 14 px de padding horizontal · `rounded-lg` · label e descrição sempre visíveis quando ajudam a decisão.
- Grupo de formulário — 20 px entre campos/ação; 8 px entre label, controle e ajuda.
- Card de tarefa — composição `CardHeader` + `CardContent` + `CardFooter` quando necessário; footer recebe `muted/50` e divisor apenas quando contém ação separada.
- Estados assíncronos — manter a mesma área e hierarquia para carregando, sucesso, erro e autenticado; mensagens transitórias usam `aria-live="polite"`.

## Regras para as próximas fases

- Reutilizar os componentes de `frontend/src/components/ui` antes de criar variações locais.
- Cor comunica ação, estado ou identidade; estrutura vem de espaço, peso tipográfico e contraste tonal.
- Implementar sempre estados de carregamento, vazio, erro, hover, foco e desabilitado relevantes.
- Manter labels, HTML semântico e áreas de toque de 44 × 44 px.
- Dados reais devem substituir esqueletos e demonstrações; não inventar métricas para preencher espaço.
- Antes de adicionar um novo padrão, conferir se ele já existe aqui ou nos componentes instalados.
