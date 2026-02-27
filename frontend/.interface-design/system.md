# Planna — Interface Design System

## Direction & Feel

**Product:** SaaS de finanças pessoais. Usuário brasileiro configurando e acompanhando sua vida financeira.

**Tom:** Caderno de registros metódico. Não é um app de banco (frio, corporativo), não é wellness (lúdico). É denso, estruturado, confiável — como uma planilha bem feita com design cuidadoso.

**Modo padrão:** `colorMode.preference = 'system'` (toggle no nav via `useColorMode()`).

---

## Depth Strategy: Borders-only

Finanças é denso e técnico. Sem sombras dramáticas.

Estratégia dual light/dark — **sempre usar `dark:` prefix**:

| Papel | Classe |
|---|---|
| Container principal | `border border-black/8 dark:border-white/8` |
| Separador de lista | `border-b border-black/5 dark:border-white/5` |
| Painel elevado (form) | `border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03]` |
| Hover em lista | `hover:bg-black/[0.02] dark:hover:bg-white/[0.02]` |
| Ícone container | `bg-black/5 dark:bg-white/5` |
| Badge inline | `bg-black/5 dark:bg-white/5` |
| Row ativo | `bg-black/[0.05] dark:bg-white/[0.05]` |
| Cabeçalho de coluna | `bg-black/[0.015] dark:bg-white/[0.015]` |

Nunca misturar sombras com essa estratégia.

**Exceção — Dashboard (`/index`):** Os cards KPI e painéis de gráfico usam superfícies opacas `bg-white dark:bg-gray-900` com `border border-black/5 dark:border-white/5`. O dashboard é informacional e de leitura rápida — a superfície opaca dá presença visual aos cards, diferenciando-os do fundo `gray-50`/`gray-950`. Essa exceção não se aplica a nenhuma outra página.

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
| Page title | `text-xl font-semibold text-gray-900 dark:text-white/90 tracking-tight` |
| Page subtitle | `text-sm text-gray-500` |
| Section header | `text-xs font-semibold text-gray-400 uppercase tracking-widest` |
| Section counter | `text-xs text-gray-600 tabular-nums` |
| Form label principal | `text-xs font-medium text-gray-500 uppercase tracking-wide` |
| Form sub-label | `text-xs text-gray-600` |
| Item primary | `text-sm font-medium text-gray-900 dark:text-white` |
| Item secondary | `text-xs text-gray-500` |
| Item muted | `text-sm text-gray-700 dark:text-white/80` |
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
<div class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-4 flex flex-col gap-4">
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
<div class="group flex items-center gap-3 px-4 py-3 border-b border-black/5 dark:border-white/5 last:border-0 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors">
  <!-- Ícone container -->
  <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
    <UIcon name="i-heroicons-*" class="text-gray-400 text-sm" />
  </div>
  <!-- Conteúdo -->
  <div class="flex-1 min-w-0">
    <p class="text-sm font-medium text-gray-900 dark:text-white truncate">Nome primário</p>
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
  <div class="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-3">
    <UIcon name="i-heroicons-*" class="text-gray-600 text-lg" />
  </div>
  <p class="text-sm text-gray-500">Mensagem principal</p>
  <p class="text-xs text-gray-600 mt-1">Instrução contextual de como adicionar</p>
</div>
```

---

## Skeleton Loading Pattern

```html
<div class="divide-y divide-black/5 dark:divide-white/5">
  <div v-for="i in 2" :key="i" class="flex items-center gap-3 px-4 py-3">
    <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 animate-pulse shrink-0" />
    <div class="flex flex-col gap-1.5 flex-1">
      <div class="h-3 w-40 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
      <div class="h-2.5 w-16 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
    </div>
  </div>
</div>
```

---

## Badge Inline Pattern

Para metadados associados (ex: conta vinculada a um cartão):

```html
<span class="text-xs text-gray-500 bg-black/5 dark:bg-white/5 px-1.5 py-0.5 rounded truncate max-w-[120px]">
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
| Editar | `i-heroicons-pencil-square` |
| Lançamento | `i-heroicons-banknotes` |
| Categoria | `i-heroicons-tag` |

---

## Semantic Colors

| Significado | Cor |
|---|---|
| Entrada / saldo positivo | `text-emerald-600 dark:text-emerald-400` |
| Saída / saldo negativo / expense | `text-red-600 dark:text-red-400` |
| Crédito / parcelas / cartão | `text-violet-600 dark:text-violet-400`, `bg-violet-50 dark:bg-violet-500/10` |
| Badge income | `bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400` |
| Badge expense | `bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400` |
| Status pago | `UBadge color="success" variant="subtle"` |
| Status pendente | `UBadge color="warning" variant="subtle"` |

Nunca usar violet para income/expense. Nunca usar emerald/red para crédito.

---

## List Table Pattern (páginas densas)

Para listas com múltiplas colunas (lançamentos, crédito):

```html
<!-- Cabeçalho de colunas -->
<div class="flex items-center gap-4 px-4 py-2 border-b border-black/5 dark:border-white/5 bg-black/[0.015] dark:bg-white/[0.015]">
  <span class="text-xs font-medium text-gray-600 w-14 shrink-0">Data</span>
  <span class="text-xs font-medium text-gray-600 flex-1">Descrição</span>
  <span class="text-xs font-medium text-gray-600 w-24 text-right shrink-0">Valor</span>
  <span class="w-16 shrink-0" /> <!-- espaço para ações -->
</div>

<!-- Linha -->
<div class="group flex items-center gap-4 px-4 py-3
            border-b border-black/5 dark:border-white/5 last:border-0 transition-colors
            hover:bg-black/[0.02] dark:hover:bg-white/[0.02]">
  <span class="text-xs text-gray-500 tabular-nums w-14 shrink-0">01/03</span>
  <span class="flex-1 text-sm text-gray-700 dark:text-white/80 truncate min-w-0">Descrição</span>
  <span class="text-sm font-medium tabular-nums text-red-600 dark:text-red-400 w-24 text-right shrink-0">
    −R$ 150,00
  </span>
  <div class="w-16 shrink-0 flex items-center justify-end gap-1">
    <UButton ... class="opacity-0 group-hover:opacity-100 transition-opacity" />
    <UButton ... class="opacity-0 group-hover:opacity-100 transition-opacity" />
  </div>
</div>
```

**Colunas responsivas:** colunas secundárias usam `hidden md:block` ou `hidden sm:block`.
**Ações:** sempre `opacity-0 group-hover:opacity-100`. Edit antes de Delete.

---

## Inline Form Pattern (add/edit na mesma página)

```html
<div v-if="showForm" class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-5 mb-4">
  <label class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-4 block">
    Título do formulário
  </label>
  <form class="space-y-3" @submit.prevent="save">
    <!-- campo full-width -->
    <UInput v-model="name" placeholder="..." class="w-full" />
    <!-- grid 2 colunas -->
    <div class="grid grid-cols-2 gap-3">
      <div class="flex flex-col gap-1.5">
        <span class="text-xs text-gray-600">Sub-label</span>
        <UInput ... />
      </div>
      <div class="flex flex-col gap-1.5">
        <span class="text-xs text-gray-600">Sub-label</span>
        <UInput ... />
      </div>
    </div>
    <!-- ações -->
    <div class="flex items-center justify-end gap-2 pt-1">
      <UButton variant="ghost" color="neutral" @click="cancel">Cancelar</UButton>
      <UButton type="submit" :loading="saving" :disabled="!valid || saving">
        Salvar
      </UButton>
    </div>
  </form>
</div>
```

---

## Page Header Pattern

```html
<div class="flex items-center justify-between mb-8">
  <div>
    <h1 class="text-xl font-semibold text-gray-900 dark:text-white/90 tracking-tight">Título</h1>
    <p class="text-sm text-gray-500 mt-1">N itens · dado contextual</p>
  </div>
  <UButton icon="i-heroicons-plus">Ação principal</UButton>
</div>
```

---

## Delete Confirmation Modal Pattern

Um único estado de confirmação por página. O modal recebe o nome do item e um callback — não sabe o que está deletando.

```ts
const confirmDeleteOpen = ref(false)
const deleteTargetLabel = ref('')
const deleteTargetFn = ref<(() => Promise<void>) | null>(null)
const deleting = ref(false)

function requestDelete(label: string, fn: () => Promise<void>) {
  deleteTargetLabel.value = label
  deleteTargetFn.value = fn
  confirmDeleteOpen.value = true
}

async function confirmDelete() {
  if (!deleteTargetFn.value) return
  deleting.value = true
  try {
    await deleteTargetFn.value()
  } finally {
    deleting.value = false
    confirmDeleteOpen.value = false
  }
}
```

```html
<!-- No botão de exclusão -->
@click="requestDelete(item.name, () => deleteItem(item.id))"

<!-- Modal (no final do template) -->
<UModal
  v-model:open="confirmDeleteOpen"
  title="Excluir [recurso]?"
  :description="`&quot;${deleteTargetLabel}&quot; será removido permanentemente.`"
>
  <template #actions>
    <UButton variant="ghost" color="neutral" @click="confirmDeleteOpen = false">Cancelar</UButton>
    <UButton color="error" :loading="deleting" @click="confirmDelete">Excluir</UButton>
  </template>
</UModal>
```

**Páginas que usam:** transactions, credit, accounts (conta e cartão), categories.

---

## Signature Elements por Domínio

### Crédito (`/credit`)
**Trilha de parcelas** — pontos proporcionais + `X/Y`:

```ts
function installmentDots(current: number, total: number): boolean[] {
  const size = Math.min(total, 12)
  const filled = Math.round((current / total) * size)
  return Array.from({ length: size }, (_, i) => i < filled)
}
```

```html
<div class="flex flex-col items-center gap-1.5">
  <div class="flex items-center gap-[3px]">
    <span v-for="(filled, i) in installmentDots(p.current_installment, p.total_installments)"
          :key="i" class="w-1 h-1 rounded-full"
          :class="filled ? 'bg-violet-500 dark:bg-violet-400' : 'bg-black/15 dark:bg-white/15'" />
  </div>
  <span class="text-xs text-gray-600 tabular-nums">{{ current }}/{{ total }}</span>
</div>
```

### Contas (`/accounts`)
**Saldo atual** colorido por sinal + saldo inicial muted abaixo:

```html
<div class="text-right shrink-0 mr-1">
  <p class="text-sm font-medium tabular-nums"
     :class="account.current_balance >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">
    {{ formatCurrency(account.current_balance) }}
  </p>
  <p class="text-xs text-gray-600 tabular-nums">
    inicial {{ formatCurrency(account.initial_balance) }}
  </p>
</div>
```
