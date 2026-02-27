<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const { format } = useCurrency()
const colorMode = useColorMode()
const isDark = computed(() => colorMode.value === 'dark')

// --- Types ---
interface CreditPurchase {
  id: string
  purchase_date: string
  credit_card_id: string | null
  credit_card_name: string | null
  merchant: string
  category_id: string | null
  category_name: string | null
  total_amount: number
  installment_amount: number
  current_installment: number
  total_installments: number
  due_date: string
}

interface LookupOption {
  label: string
  value: string
}

interface CreditHistoryItem {
  month: number
  year: number
  label: string
  credit_total: number
  income: number
  expenses: number
  balance: number
  commitment: number
  cards: Record<string, number>
}

interface CreditAnalytics {
  history: CreditHistoryItem[]
  cards: string[]
  current_month: CreditHistoryItem | null
}

// --- Data ---
const purchases = ref<CreditPurchase[]>([])
const loading = ref(true)
const analytics = ref<CreditAnalytics | null>(null)

const cardOptions = ref<LookupOption[]>([])
const categoryOptions = ref<LookupOption[]>([])

// Form state
const showForm = ref(false)
const editingId = ref<string | null>(null)
const formMerchant = ref('')
const formTotalAmountDisplay = ref('')
const formTotalAmountRaw = ref<number | null>(null)
const formTotalInstallments = ref(1)
const formCurrentInstallment = ref(1)
const formInstallmentAmountDisplay = ref('')
const formInstallmentAmountRaw = ref<number | null>(null)
const formDate = ref(new Date().toISOString().split('T')[0])
const formDueDate = ref(new Date().toISOString().split('T')[0])
const formCard = ref<LookupOption | undefined>()
const formCategory = ref<LookupOption | undefined>()
const saving = ref(false)

const totalMonthly = computed(() =>
  purchases.value.reduce((sum, p) => sum + Number(p.installment_amount), 0)
)

// --- Commitment ring ---
const commitmentPct = computed(() => (analytics.value?.current_month?.commitment ?? 0) * 100)

const commitmentColor = computed(() => {
  const r = analytics.value?.current_month?.commitment ?? 0
  return r < 0.7 ? '#34d399' : r < 0.9 ? '#fbbf24' : '#f87171'
})

const commitmentStyle = computed(() => ({
  background: `conic-gradient(from -90deg, ${commitmentColor.value} ${commitmentPct.value}%, ${isDark.value ? 'rgba(255,255,255,0.06)' : 'rgba(0,0,0,0.06)'} ${commitmentPct.value}%)`,
}))

// --- Credit as % of expenses ---
const creditPctOfExpenses = computed(() => {
  const cur = analytics.value?.current_month
  if (!cur) return 0
  const totalExp = cur.expenses + cur.credit_total
  if (totalExp === 0) return 0
  return (cur.credit_total / totalExp) * 100
})

// --- Charts ---
const creditChartEl = ref<HTMLElement | null>(null)
const balanceChartEl = ref<HTMLElement | null>(null)
let Plotly: any = null

const PLOT_CFG = { displayModeBar: false, responsive: true }

function getBaseLayout() {
  const dark = isDark.value
  return {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: {
      color: dark ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.45)',
      family: 'inherit',
      size: 11,
    },
    hoverlabel: {
      bgcolor: dark ? '#1f2937' : '#f9fafb',
      bordercolor: dark ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)',
      font: { color: dark ? 'rgba(255,255,255,0.9)' : '#111827', size: 12 },
    },
  }
}

// Violet palette for stacked card bars
const CARD_COLORS = [
  'rgba(139,92,246,0.7)',   // violet-500
  'rgba(167,139,250,0.6)',  // violet-400
  'rgba(196,181,253,0.5)',  // violet-300
  'rgba(109,40,217,0.6)',   // violet-700
  'rgba(221,214,254,0.45)', // violet-200
]

function renderCreditChart() {
  if (!Plotly || !creditChartEl.value || !analytics.value) return
  const { history, cards } = analytics.value
  if (!history.length) return

  const dark = isDark.value
  const traces = cards.map((cardName, i) => ({
    name: cardName,
    type: 'bar' as const,
    x: history.map(h => h.label),
    y: history.map(h => h.cards[cardName] ?? 0),
    marker: { color: CARD_COLORS[i % CARD_COLORS.length] },
    hovertemplate: `<b>${cardName}</b><br>%{x}: R$ %{y:,.2f}<extra></extra>`,
  }))

  // If no cards breakdown, show total as single bar
  if (!cards.length) {
    traces.push({
      name: 'Crédito',
      type: 'bar',
      x: history.map(h => h.label),
      y: history.map(h => h.credit_total),
      marker: { color: CARD_COLORS[0] },
      hovertemplate: '<b>%{x}</b><br>Crédito: R$ %{y:,.2f}<extra></extra>',
    })
  }

  Plotly.react(creditChartEl.value, traces, {
    ...getBaseLayout(),
    margin: { t: 8, r: 10, b: 36, l: 60 },
    barmode: 'stack',
    bargap: 0.35,
    xaxis: {
      gridcolor: 'transparent',
      linecolor: dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)',
      tickcolor: 'transparent',
    },
    yaxis: {
      gridcolor: dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.05)',
      linecolor: 'transparent',
      tickcolor: 'transparent',
      tickprefix: 'R$',
      tickformat: ',.0f',
    },
    legend: {
      orientation: 'h' as const,
      x: 0,
      y: 1.18,
      font: { color: dark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.5)', size: 11 },
      bgcolor: 'transparent',
    },
    showlegend: cards.length > 1,
  }, PLOT_CFG)
}

function renderBalanceChart() {
  if (!Plotly || !balanceChartEl.value || !analytics.value) return
  const { history } = analytics.value
  if (!history.length) return

  const dark = isDark.value
  Plotly.react(balanceChartEl.value, [
    {
      name: 'Receita',
      type: 'scatter',
      mode: 'lines+markers',
      x: history.map(h => h.label),
      y: history.map(h => h.income),
      line: { color: 'rgba(52,211,153,0.7)', width: 2 },
      marker: { size: 5, color: 'rgba(52,211,153,0.9)' },
      hovertemplate: '<b>%{x}</b><br>Receita: R$ %{y:,.2f}<extra></extra>',
    },
    {
      name: 'Despesas + Crédito',
      type: 'scatter',
      mode: 'lines+markers',
      x: history.map(h => h.label),
      y: history.map(h => h.expenses + h.credit_total),
      line: { color: 'rgba(248,113,113,0.7)', width: 2 },
      marker: { size: 5, color: 'rgba(248,113,113,0.9)' },
      hovertemplate: '<b>%{x}</b><br>Despesas: R$ %{y:,.2f}<extra></extra>',
    },
    {
      name: 'Saldo',
      type: 'bar',
      x: history.map(h => h.label),
      y: history.map(h => h.balance),
      marker: {
        color: history.map(h =>
          h.balance >= 0 ? 'rgba(52,211,153,0.25)' : 'rgba(248,113,113,0.25)'
        ),
      },
      hovertemplate: '<b>%{x}</b><br>Saldo: R$ %{y:,.2f}<extra></extra>',
    },
  ], {
    ...getBaseLayout(),
    margin: { t: 8, r: 10, b: 36, l: 60 },
    barmode: 'overlay',
    bargap: 0.4,
    xaxis: {
      gridcolor: 'transparent',
      linecolor: dark ? 'rgba(255,255,255,0.05)' : 'rgba(0,0,0,0.06)',
      tickcolor: 'transparent',
    },
    yaxis: {
      gridcolor: dark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.05)',
      linecolor: 'transparent',
      tickcolor: 'transparent',
      tickprefix: 'R$',
      tickformat: ',.0f',
    },
    legend: {
      orientation: 'h' as const,
      x: 0,
      y: 1.18,
      font: { color: dark ? 'rgba(255,255,255,0.45)' : 'rgba(0,0,0,0.5)', size: 11 },
      bgcolor: 'transparent',
    },
  }, PLOT_CFG)
}

function renderCharts() {
  renderCreditChart()
  renderBalanceChart()
}

// --- Form helpers ---
function recomputeInstallmentAmount() {
  if (formTotalAmountRaw.value && formTotalInstallments.value > 0) {
    const installment = Math.round((formTotalAmountRaw.value / formTotalInstallments.value) * 100) / 100
    formInstallmentAmountRaw.value = installment
    formInstallmentAmountDisplay.value = installment.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  }
}

function handleTotalAmountInput(e: Event) {
  const digits = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const cents = parseInt(digits || '0', 10)
  formTotalAmountRaw.value = cents > 0 ? cents / 100 : null
  formTotalAmountDisplay.value = cents > 0
    ? (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : ''
  recomputeInstallmentAmount()
}

function handleInstallmentAmountInput(e: Event) {
  const digits = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const cents = parseInt(digits || '0', 10)
  formInstallmentAmountRaw.value = cents > 0 ? cents / 100 : null
  formInstallmentAmountDisplay.value = cents > 0
    ? (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : ''
}

// --- Data loading ---
async function loadPurchases() {
  loading.value = true
  try {
    purchases.value = await api.get<CreditPurchase[]>('/credit-purchases?limit=100')
  } finally {
    loading.value = false
  }
}

async function loadAnalytics() {
  try {
    const now = new Date()
    analytics.value = await api.get<CreditAnalytics>(
      `/analytics/credit?year=${now.getFullYear()}&month=${now.getMonth() + 1}&n=6`
    )
    await nextTick()
    renderCharts()
  } catch {
    // analytics is optional — don't block the page
  }
}

async function loadLookups() {
  const [cardsResult, categoriesResult] = await Promise.allSettled([
    api.get<{ id: string; name: string }[]>('/credit-cards'),
    api.get<{ id: string; name: string; emoji: string | null }[]>('/categories'),
  ])
  if (cardsResult.status === 'fulfilled') {
    cardOptions.value = cardsResult.value.map(c => ({ label: c.name, value: c.id }))
  }
  if (categoriesResult.status === 'fulfilled') {
    categoryOptions.value = categoriesResult.value.map(c => ({
      label: c.emoji ? `${c.emoji} ${c.name}` : c.name,
      value: c.id,
    }))
  }
}

function cancelForm() {
  showForm.value = false
  editingId.value = null
  formMerchant.value = ''
  formTotalAmountDisplay.value = ''
  formTotalAmountRaw.value = null
  formTotalInstallments.value = 1
  formCurrentInstallment.value = 1
  formInstallmentAmountDisplay.value = ''
  formInstallmentAmountRaw.value = null
  formDate.value = new Date().toISOString().split('T')[0]
  formDueDate.value = new Date().toISOString().split('T')[0]
  formCard.value = undefined
  formCategory.value = undefined
}

function startEdit(p: CreditPurchase) {
  editingId.value = p.id
  formMerchant.value = p.merchant
  formTotalAmountRaw.value = Number(p.total_amount)
  formTotalAmountDisplay.value = Number(p.total_amount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  formTotalInstallments.value = p.total_installments
  formCurrentInstallment.value = p.current_installment
  formInstallmentAmountRaw.value = Number(p.installment_amount)
  formInstallmentAmountDisplay.value = Number(p.installment_amount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  formDate.value = p.purchase_date
  formDueDate.value = p.due_date
  formCard.value = cardOptions.value.find(o => o.value === p.credit_card_id)
  formCategory.value = categoryOptions.value.find(o => o.value === p.category_id)
  showForm.value = true
}

async function savePurchase() {
  if (!formMerchant.value.trim() || !formTotalAmountRaw.value || !formDate.value || !formDueDate.value) return
  saving.value = true
  try {
    const payload = {
      merchant: formMerchant.value.trim(),
      total_amount: formTotalAmountRaw.value,
      installment_amount: formInstallmentAmountRaw.value ?? formTotalAmountRaw.value,
      total_installments: formTotalInstallments.value,
      current_installment: formCurrentInstallment.value,
      purchase_date: formDate.value,
      due_date: formDueDate.value,
      credit_card_id: formCard.value?.value ?? null,
      category_id: formCategory.value?.value ?? null,
    }
    if (editingId.value) {
      await api.put(`/credit-purchases/${editingId.value}`, payload)
    } else {
      await api.post('/credit-purchases', payload)
    }
    cancelForm()
    await Promise.all([loadPurchases(), loadAnalytics()])
  } finally {
    saving.value = false
  }
}

async function deletePurchase(id: string) {
  await api.delete(`/credit-purchases/${id}`)
  await Promise.all([loadPurchases(), loadAnalytics()])
}

// Delete confirmation
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

function formatDate(dateStr: string) {
  const [, month, day] = dateStr.split('-')
  return `${day}/${month}`
}

// Installment dots: proportional track, max 12 dots
function installmentDots(current: number, total: number): boolean[] {
  const size = Math.min(total, 12)
  const filled = Math.round((current / total) * size)
  return Array.from({ length: size }, (_, i) => i < filled)
}

onMounted(async () => {
  loadPurchases()
  loadLookups()
  Plotly = (await import('plotly.js-dist-min')).default
  loadAnalytics()
})

onUnmounted(() => {
  if (Plotly) {
    if (creditChartEl.value) Plotly.purge(creditChartEl.value)
    if (balanceChartEl.value) Plotly.purge(balanceChartEl.value)
  }
})

watch(isDark, renderCharts)
watch(analytics, () => nextTick(renderCharts))
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-gray-900 dark:text-white/90 tracking-tight">Crédito</h1>
        <p class="text-sm text-gray-500 mt-1">
          <template v-if="loading">Carregando...</template>
          <template v-else>
            {{ purchases.length }} compra{{ purchases.length !== 1 ? 's' : '' }}
            <template v-if="purchases.length > 0">
              · <span class="text-violet-600 dark:text-violet-400 tabular-nums">{{ format(totalMonthly) }}/mês</span>
            </template>
          </template>
        </p>
      </div>
      <UButton icon="i-heroicons-plus" @click="editingId ? cancelForm() : (showForm = !showForm)">
        Nova compra
      </UButton>
    </div>

    <!-- Analytics cards -->
    <div v-if="analytics?.current_month" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <!-- Crédito este mês -->
      <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-gray-900 p-4 lg:p-5">
        <p class="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-white/30 mb-3">Crédito no mês</p>
        <p class="text-2xl font-semibold text-violet-600 dark:text-violet-400 tabular-nums leading-none">
          {{ format(analytics.current_month.credit_total) }}
        </p>
        <p class="text-[11px] text-gray-400 dark:text-white/20 mt-2.5 tabular-nums">
          {{ creditPctOfExpenses.toFixed(0) }}% das despesas totais
        </p>
      </div>

      <!-- Saldo -->
      <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-gray-900 p-4 lg:p-5">
        <p class="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-white/30 mb-3">Saldo</p>
        <p
          class="text-2xl font-semibold tabular-nums leading-none"
          :class="analytics.current_month.balance >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
        >
          {{ format(analytics.current_month.balance) }}
        </p>
        <p class="text-[11px] text-gray-400 dark:text-white/20 mt-2.5 tabular-nums">
          receita − despesas − crédito
        </p>
      </div>

      <!-- Receita -->
      <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-gray-900 p-4 lg:p-5">
        <p class="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-white/30 mb-3">Receita</p>
        <p class="text-2xl font-semibold text-gray-900 dark:text-white/90 tabular-nums leading-none">
          {{ format(analytics.current_month.income) }}
        </p>
        <p class="text-[11px] text-gray-400 dark:text-white/20 mt-2.5">
          este mês
        </p>
      </div>

      <!-- Comprometimento -->
      <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-gray-900 p-4 lg:p-5 flex items-center gap-4">
        <div class="relative shrink-0 w-[52px] h-[52px]">
          <div class="w-[52px] h-[52px] rounded-full" :style="commitmentStyle">
            <div class="absolute inset-[6px] rounded-full bg-white dark:bg-gray-900 flex items-center justify-center">
              <span class="text-[11px] font-semibold text-gray-900 dark:text-white/90 tabular-nums">{{ commitmentPct.toFixed(0) }}%</span>
            </div>
          </div>
        </div>
        <div class="min-w-0">
          <p class="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-white/30 mb-1">Comprometida</p>
          <p class="text-sm text-gray-500 dark:text-white/55 leading-snug tabular-nums">
            {{ commitmentPct.toFixed(1) }}% da receita
          </p>
          <p class="text-[11px] text-gray-400 dark:text-white/25">despesas + crédito</p>
        </div>
      </div>
    </div>

    <!-- Charts row -->
    <div v-if="analytics" class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Credit spending by card -->
      <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-gray-900 p-5">
        <h2 class="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-white/30 mb-4">Gastos no crédito</h2>
        <div ref="creditChartEl" class="h-[226px]">
          <div v-if="!analytics.history.length" class="h-full flex items-center justify-center text-sm text-gray-400 dark:text-white/20">
            Sem dados
          </div>
        </div>
      </div>

      <!-- Balance history -->
      <div class="rounded-xl border border-black/5 dark:border-white/5 bg-white dark:bg-gray-900 p-5">
        <h2 class="text-[10px] font-semibold uppercase tracking-widest text-gray-400 dark:text-white/30 mb-4">Saldo mensal</h2>
        <div ref="balanceChartEl" class="h-[226px]">
          <div v-if="!analytics.history.length" class="h-full flex items-center justify-center text-sm text-gray-400 dark:text-white/20">
            Sem dados
          </div>
        </div>
      </div>
    </div>

    <!-- Form -->
    <div v-if="showForm" class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-5">
      <label class="text-xs font-medium text-gray-500 uppercase tracking-wide mb-4 block">
        {{ editingId ? 'Editar compra' : 'Nova compra no crédito' }}
      </label>
      <form class="space-y-3" @submit.prevent="savePurchase">

        <!-- Merchant -->
        <UInput v-model="formMerchant" placeholder="Estabelecimento..." class="w-full" />

        <!-- Total + Installments -->
        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1.5">
            <span class="text-xs text-gray-600">Valor total</span>
            <UInput
              :value="formTotalAmountDisplay"
              placeholder="R$ 0,00"
              inputmode="numeric"
              @input="handleTotalAmountInput"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <span class="text-xs text-gray-600">Parcelas</span>
            <UInput
              v-model.number="formTotalInstallments"
              type="number"
              placeholder="1"
              :min="1"
              :max="72"
              @change="recomputeInstallmentAmount"
            />
          </div>
        </div>

        <!-- Installment amount + Current installment -->
        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1.5">
            <span class="text-xs text-gray-600">Valor da parcela</span>
            <UInput
              :value="formInstallmentAmountDisplay"
              placeholder="R$ 0,00"
              inputmode="numeric"
              @input="handleInstallmentAmountInput"
            />
          </div>
          <div class="flex flex-col gap-1.5">
            <span class="text-xs text-gray-600">Parcela atual</span>
            <UInput
              v-model.number="formCurrentInstallment"
              type="number"
              placeholder="1"
              :min="1"
              :max="formTotalInstallments"
            />
          </div>
        </div>

        <!-- Dates -->
        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1.5">
            <span class="text-xs text-gray-600">Data da compra</span>
            <UInput v-model="formDate" type="date" />
          </div>
          <div class="flex flex-col gap-1.5">
            <span class="text-xs text-gray-600">Vencimento</span>
            <UInput v-model="formDueDate" type="date" />
          </div>
        </div>

        <!-- Card + Category -->
        <div class="grid grid-cols-2 gap-3">
          <USelectMenu v-model="formCard" :items="cardOptions" placeholder="Cartão..." />
          <USelectMenu v-model="formCategory" :items="categoryOptions" placeholder="Categoria..." />
        </div>

        <!-- Actions -->
        <div class="flex items-center justify-end gap-2 pt-1">
          <UButton variant="ghost" color="neutral" @click="cancelForm">Cancelar</UButton>
          <UButton
            type="submit"
            :loading="saving"
            :disabled="!formMerchant.trim() || !formTotalAmountRaw || saving"
            :icon="editingId ? 'i-heroicons-check' : 'i-heroicons-plus'"
          >
            {{ editingId ? 'Salvar' : 'Adicionar' }}
          </UButton>
        </div>
      </form>
    </div>

    <!-- List -->
    <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">

      <!-- Column header -->
      <div class="flex items-center gap-4 px-4 py-2 border-b border-black/5 dark:border-white/5 bg-black/[0.015] dark:bg-white/[0.015]">
        <span class="text-xs font-medium text-gray-600 w-14 shrink-0">Data</span>
        <span class="text-xs font-medium text-gray-600 flex-1">Estabelecimento</span>
        <span class="text-xs font-medium text-gray-600 w-28 shrink-0 hidden lg:block">Cartão</span>
        <span class="text-xs font-medium text-gray-600 w-28 shrink-0 hidden lg:block">Categoria</span>
        <span class="text-xs font-medium text-gray-600 w-28 shrink-0 text-center hidden sm:block">Parcelas</span>
        <span class="text-xs font-medium text-gray-600 w-24 text-right shrink-0">Parcela</span>
        <span class="w-16 shrink-0" />
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading">
        <div
          v-for="i in 6"
          :key="i"
          class="flex items-center gap-4 px-4 py-3.5 border-b border-black/5 dark:border-white/5 last:border-0"
        >
          <div class="h-2.5 w-10 bg-black/5 dark:bg-white/5 rounded animate-pulse shrink-0" />
          <div class="h-3 bg-black/5 dark:bg-white/5 rounded animate-pulse flex-1" />
          <div class="h-2.5 w-24 bg-black/5 dark:bg-white/5 rounded animate-pulse shrink-0 hidden lg:block" />
          <div class="h-2.5 w-24 bg-black/5 dark:bg-white/5 rounded animate-pulse shrink-0 hidden lg:block" />
          <div class="h-2.5 w-24 bg-black/5 dark:bg-white/5 rounded animate-pulse shrink-0 hidden sm:block" />
          <div class="h-3 w-20 bg-black/5 dark:bg-white/5 rounded animate-pulse shrink-0" />
          <div class="w-16 shrink-0" />
        </div>
      </div>

      <!-- Empty state -->
      <template v-else-if="purchases.length === 0">
        <div class="flex flex-col items-center justify-center py-16 px-6 text-center">
          <div class="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-3">
            <UIcon name="i-heroicons-credit-card" class="text-gray-600 text-lg" />
          </div>
          <p class="text-sm text-gray-500">Nenhuma compra no crédito</p>
          <p class="text-xs text-gray-600 mt-1">Adicione uma compra parcelada para acompanhar</p>
          <UButton variant="soft" class="mt-4" icon="i-heroicons-plus" @click="showForm = true">
            Adicionar compra
          </UButton>
        </div>
      </template>

      <!-- Rows -->
      <template v-else>
        <div
          v-for="p in purchases"
          :key="p.id"
          class="group flex items-center gap-4 px-4 py-3 border-b border-black/5 dark:border-white/5 last:border-0 transition-colors"
          :class="editingId === p.id ? 'bg-black/[0.05] dark:bg-white/[0.05]' : 'hover:bg-black/[0.02] dark:hover:bg-white/[0.02]'"
        >
          <!-- Date -->
          <span class="text-xs text-gray-500 tabular-nums w-14 shrink-0">
            {{ formatDate(p.purchase_date) }}
          </span>

          <!-- Merchant -->
          <span class="flex-1 text-sm text-gray-700 dark:text-white/80 truncate min-w-0">
            {{ p.merchant }}
          </span>

          <!-- Card -->
          <div class="w-28 shrink-0 hidden lg:block overflow-hidden">
            <span
              v-if="p.credit_card_name"
              class="text-xs text-violet-600 dark:text-violet-400/80 bg-violet-50 dark:bg-violet-500/10 px-1.5 py-0.5 rounded truncate block max-w-full"
            >{{ p.credit_card_name }}</span>
          </div>

          <!-- Category -->
          <div class="w-28 shrink-0 hidden lg:block overflow-hidden">
            <span
              v-if="p.category_name"
              class="text-xs text-gray-500 bg-black/5 dark:bg-white/5 px-1.5 py-0.5 rounded truncate block max-w-full"
            >{{ p.category_name }}</span>
          </div>

          <!-- Installment progress -->
          <div class="w-28 shrink-0 hidden sm:flex flex-col items-center gap-1.5">
            <div class="flex items-center gap-[3px]">
              <span
                v-for="(filled, i) in installmentDots(p.current_installment, p.total_installments)"
                :key="i"
                class="w-1 h-1 rounded-full"
                :class="filled ? 'bg-violet-500 dark:bg-violet-400' : 'bg-black/15 dark:bg-white/15'"
              />
            </div>
            <span class="text-xs text-gray-600 tabular-nums">
              {{ p.current_installment }}/{{ p.total_installments }}
            </span>
          </div>

          <!-- Installment amount -->
          <span class="text-sm font-medium tabular-nums text-gray-700 dark:text-white/80 w-24 text-right shrink-0">
            {{ format(p.installment_amount) }}
          </span>

          <!-- Actions -->
          <div class="w-16 shrink-0 flex items-center justify-end gap-1">
            <UButton
              variant="ghost"
              color="neutral"
              icon="i-heroicons-pencil-square"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity"
              @click="startEdit(p)"
            />
            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity"
              @click="requestDelete(p.merchant, () => deletePurchase(p.id))"
            />
          </div>
        </div>
      </template>

    </div>

    <UModal
      v-model:open="confirmDeleteOpen"
      title="Excluir compra?"
      :description="`&quot;${deleteTargetLabel}&quot; será removido permanentemente.`"
    >
      <template #actions>
        <UButton variant="ghost" color="neutral" @click="confirmDeleteOpen = false">Cancelar</UButton>
        <UButton color="error" :loading="deleting" @click="confirmDelete">Excluir</UButton>
      </template>
    </UModal>
  </div>
</template>
