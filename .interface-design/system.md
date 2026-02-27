# Planna — Interface Design System

## Direction & Feel

**Product domain:** controle financeiro pessoal — fechamento mensal, fluxo de caixa, balanço, categorização
**Who:** pessoa que quer clareza sobre o próprio dinheiro; abre o app regularmente, quer objetividade
**Feel:** preciso, confiante, calmo — como um caderno financeiro bem organizado. Não frio como banco, mas pessoal e intencional.

**Signature:** grade de pontos esmeralda evocando planilha/ledger; painel lateral de marca que separa identidade do formulário

---

## Color Palette

| Token | Value | Role |
|-------|-------|------|
| Brand surface | `#0e1411` | Painel de marca (warm-dark green) |
| Base background | `bg-gray-950` | Fundo geral da app |
| Brand accent | `emerald-400` / `rgba(52,211,153,…)` | Logo, links de destaque |
| Brand mark bg | `rgba(52,211,153,0.1)` + border `rgba(52,211,153,0.2)` | Caixa do logotipo [P] |
| Dot grid | `rgba(52,211,153,0.18)` | Textura de fundo do painel |
| Text primary | `text-white/90` | Headings principais |
| Text secondary | `text-white/70` | Taglines, labels de suporte |
| Text muted | `text-white/40` | Subtítulos, metadados |
| Text ghost | `text-white/25`–`text-white/30` | Rodapé, links secundários |
| Border | `border-white/5` | Separadores de superfície |

---

## Depth Strategy

**Borders-only** — sem sombras. Separação por cor de superfície e bordas sutis.
- `border-white/5` para divisores de seção
- Elevação por mudança de `background-color`, não por shadow

---

## Spacing

Base unit: `4px` (Tailwind default). Escala usada:
- Entre campos: `space-y-4`
- Entre seções do form: `mb-8`, `mt-7`
- Padding de painel: `p-14` (desktop), `p-8` (mobile)
- Máximo de formulário: `max-w-[360px]`

---

## Typography

- Heading de tela: `text-2xl font-semibold text-white/90 tracking-tight`
- Subtítulo: `text-sm text-white/40 mt-1.5`
- Label de campo: padrão Nuxt UI (herdado do tema)
- Tagline de marca: `text-xl font-medium text-white/70 leading-snug`
- Links: `text-primary-400 hover:text-primary-300 transition-colors`

---

## Component Patterns

### Auth Layout (`layouts/auth.vue`)
- Split 2 colunas no desktop: `lg:grid lg:grid-cols-2`
- Painel esquerdo: `background-color: #0e1411` + dot grid + logo no topo + tagline no rodapé
- Painel direito: `bg-gray-950` centrado, `max-w-[360px]`
- Mobile: coluna única, logo compacto acima do formulário (`lg:hidden`)
- Borda separadora: `border-r border-white/5`

### Logo Mark
```html
<div class="w-8 h-8 rounded-lg flex items-center justify-center"
     style="background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.2)">
  <span class="text-emerald-400 font-bold text-sm leading-none">P</span>
</div>
<span class="text-white/80 font-semibold text-base tracking-tight">Planna</span>
```

### Dot Grid (ledger texture)
```html
<div class="absolute inset-0 pointer-events-none"
     style="background-image: radial-gradient(circle, rgba(52,211,153,0.18) 1px, transparent 1px);
            background-size: 28px 28px; opacity: 0.4" />
```

### Auth Form (inline, sem UCard)
- Heading + subtítulo acima do form
- `UFormField class="w-full"` + `UInput size="lg" class="w-full"` — ambos precisam de `w-full` no Nuxt UI v3, senão o input não estica para preencher o container
- `UButton block size="lg"` para submit
- Link de alternância (`/login` ↔ `/register`) no rodapé, `text-center text-sm text-white/30`

---

## Border Radius

- Logo mark: `rounded-lg`
- Inputs/buttons: padrão Nuxt UI
- Modais: padrão Nuxt UI

---

## Decisions Log

| Default rejeitado | Substituído por |
|-------------------|-----------------|
| Card centralizado em fundo liso | Split layout com painel de marca |
| `text-white` sem hierarquia | Escala `/90` `/70` `/40` `/25` |
| `hover:underline` em links | `transition-colors` com variante `hover:text-primary-300` |
| `UCard` no form de auth | Form inline com heading próprio |
