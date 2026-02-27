# Planna — Interface Design System

## Direction & Feel

**Product:** SaaS de finanças pessoais. Usuário brasileiro configurando e acompanhando sua vida financeira.

**Tom:** Caderno de registros metódico. Não é um app de banco (frio, corporativo), não é wellness (lúdico). É denso, estruturado, confiável — como uma planilha bem feita com design cuidadoso.

**Modo padrão:** Dark mode.

---

## Depth Strategy: Borders-only

Finanças é denso e técnico. Sem sombras dramáticas.

- Containers principais: `border border-white/8`
- Separadores de lista: `border-b border-white/5`
- Painéis de formulário (elevados): `border border-white/8 bg-white/[0.03]`
- Hover em itens de lista: `hover:bg-white/[0.02]`

Nunca misturar sombras com essa estratégia.

---

## Spacing

Base unit: `4` (16px). Gaps internos: `gap-2` a `gap-4`. Gaps de seção: `gap-6`.

---

## Border Radius

- Inputs e botões: padrão do Nuxt UI (`rounded`)
- Cards/containers: `rounded-xl`
- Ícone containers: `rounded-lg` (8×8, `w-8 h-8`)
- Badges inline: `rounded`

---

## Typography Scale

| Uso | Classes |
|---|---|
| Page title | `text-xl font-semibold text-white tracking-tight` |
| Page subtitle | `text-sm text-gray-500` |
| Section header | `text-xs font-semibold text-gray-400 uppercase tracking-widest` |
| Section counter | `text-xs text-gray-600 tabular-nums` |
| Form label principal | `text-xs font-medium text-gray-500 uppercase tracking-wide` |
| Form sub-label | `text-xs text-gray-600` |
| Item primary | `text-sm font-medium text-white` |
| Item secondary | `text-xs text-gray-500` |
| Dado numérico | `tabular-nums` (sempre em dados financeiros) |
| Dado monetário | `text-xs text-gray-400 tabular-nums font-medium` |

---

## Layout: Two-Column Symmetric Grid

Para páginas com duas seções paralelas (ex: accounts), usar **grid de N linhas × 2 colunas** em vez de duas colunas flex independentes. Isso garante alinhamento horizontal entre linhas correspondentes.

```html
<div class="grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-4">
  <!-- Row 1: headers -->
  <div>header esq.</div>
  <div>header dir.</div>
  <!-- Row 2: forms (mesma altura garantida pelo grid) -->
  <div>form esq.</div>
  <div>form dir.</div>
  <!-- Row 3: lists (topos sempre alinhados) -->
  <div>lista esq.</div>
  <div>lista dir.</div>
</div>
```

---

## Section Header Pattern

```html
<div class="flex items-center justify-between">
  <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-widest">
    Nome da Seção
  </h2>
  <span class="text-xs text-gray-600 tabular-nums">N itens</span>
</div>
```

---

## Form Panel Pattern

Painel destacado do fundo para agrupar campos de adição:

```html
<div class="rounded-xl border border-white/8 bg-white/[0.03] p-4 flex flex-col gap-4">
  <!-- Grupo de campos com label -->
  <div class="flex flex-col gap-1.5">
    <label class="text-xs font-medium text-gray-500 uppercase tracking-wide">
      Label Principal
      <span class="normal-case font-normal text-gray-600">(opcional)</span>
    </label>
    <!-- input aqui -->
  </div>
</div>
```

Labels sempre acima dos inputs — nunca só placeholder.

---

## List Item Pattern

Item de lista com ícone container, conteúdo em duas linhas e delete oculto no hover:

```html
<div class="group flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors">
  <!-- Ícone container -->
  <div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
    <UIcon name="i-heroicons-*" class="text-gray-400 text-sm" />
  </div>
  <!-- Conteúdo -->
  <div class="flex-1 min-w-0">
    <p class="text-sm font-medium text-white truncate">Nome primário</p>
    <p class="text-xs text-gray-500">Metadados secundários</p>
  </div>
  <!-- Delete — oculto até hover -->
  <UButton
    variant="ghost" color="error" icon="i-heroicons-trash" size="xs"
    class="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
    @click="delete(item.id)"
  />
</div>
```

---

## Empty State Pattern

```html
<div class="flex flex-col items-center justify-center py-10 px-6 text-center">
  <div class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center mb-3">
    <UIcon name="i-heroicons-*" class="text-gray-600 text-lg" />
  </div>
  <p class="text-sm text-gray-500">Mensagem principal</p>
  <p class="text-xs text-gray-600 mt-1">Instrução contextual de como adicionar</p>
</div>
```

---

## Skeleton Loading Pattern

```html
<div class="divide-y divide-white/5">
  <div v-for="i in 2" :key="i" class="flex items-center gap-3 px-4 py-3">
    <div class="w-8 h-8 rounded-lg bg-white/5 animate-pulse shrink-0" />
    <div class="flex flex-col gap-1.5 flex-1">
      <div class="h-3 w-40 bg-white/5 rounded animate-pulse" />
      <div class="h-2.5 w-16 bg-white/5 rounded animate-pulse" />
    </div>
  </div>
</div>
```

---

## Badge Inline Pattern

Para metadados associados (ex: conta vinculada a um cartão):

```html
<span class="text-xs text-gray-500 bg-white/5 px-1.5 py-0.5 rounded truncate max-w-[120px]">
  Texto do badge
</span>
```

---

## Money Mask (BRL)

Input de dinheiro com máscara de centavos (digita da direita para esquerda):

```typescript
const display = ref('')
const value = ref<number | null>(null)

function handleMoneyInput(e: Event) {
  const digits = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const cents = parseInt(digits || '0', 10)
  value.value = cents > 0 ? cents / 100 : null
  display.value = cents > 0
    ? (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : ''
}
```

```html
<UInput :value="display" type="text" placeholder="R$ 0,00" inputmode="numeric" @input="handleMoneyInput" />
```

---

## Loading / Saving States

- Dados da página: `const loading = ref(true)` — ativo antes do primeiro fetch, false após
- Submit de formulário: `const saving = ref(false)` — ativo durante a requisição
- Botão com estado: `:loading="saving" :disabled="!valid || saving"`
- Composables custosos (ex: `useCurrency`): instanciar uma vez no `setup`, nunca dentro de loops de template

---

## Iconography

Conjunto: `i-heroicons-*` exclusivamente.

| Contexto | Ícone |
|---|---|
| Conta bancária | `i-heroicons-building-library` |
| Cartão de crédito | `i-heroicons-credit-card` |
| Adicionar | `i-heroicons-plus` |
| Excluir | `i-heroicons-trash` |
