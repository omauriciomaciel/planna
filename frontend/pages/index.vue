<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const auth = useAuth()
const { format } = useCurrency()

// --- Types ---
interface TopCategory {
  name: string
  amount: number
  pct: number
}

interface ClosingData {
  income: number
  expenses: number
  balance: number
  prev_income: number
  prev_expenses: number
  prev_balance: number
  commitment_rate: number
  top_categories: TopCategory[]
}

interface HistoryItem {
  month: number
  year: number
  label: string
  income: number
  expenses: number
  balance: number
}

interface SankeyData {
  income: number
  categories: Record<string, number>
}

interface Outlier {
  category: string
  expected: number
  upper_bound: number
  actual: number
}

// --- State ---
const currentDate = ref(new Date())
const year = computed(() => currentDate.value.getFullYear())
const month = computed(() => currentDate.value.getMonth() + 1)

const monthLabel = computed(() =>
  currentDate.value.toLocaleDateString('pt-BR', { month: 'long', year: 'numeric' })
)

const greeting = computed(() => {
  const h = new Date().getHours()
  return h < 12 ? 'Bom dia' : h < 18 ? 'Boa tarde' : 'Boa noite'
})

const firstName = computed(() => auth.user.value?.name?.split(' ')[0] ?? '')

// --- Data ---
const { data: closing } = useAsyncData(
  'dashboard-closing',
  () => api.get<ClosingData>(`/analytics/monthly-closing?year=${year.value}&month=${month.value}`),
  { watch: [year, month] }
)

const { data: history } = useAsyncData(
  'dashboard-history',
  () => api.get<HistoryItem[]>(`/analytics/history?year=${year.value}&month=${month.value}&n=6`),
  { watch: [year, month] }
)

const { data: sankey } = useAsyncData(
  'dashboard-sankey',
  () => api.get<SankeyData>(`/analytics/sankey?year=${year.value}&month=${month.value}`),
  { watch: [year, month] }
)

const { data: outliers } = useAsyncData(
  'dashboard-outliers',
  () => api.get<Outlier[]>(`/analytics/outliers?year=${year.value}&month=${month.value}`),
  { watch: [year, month] }
)

// --- Delta helpers ---
function pctDelta(current: number, prev: number): number | null {
  if (prev === 0) return null
  return ((current - prev) / prev) * 100
}

interface DeltaDisplay { text: string; positive: boolean }

function fmtDelta(d: number | null, goodWhenPositive = true): DeltaDisplay | null {
  if (d === null) return null
  return {
    text: `${d >= 0 ? '↑' : '↓'} ${Math.abs(d).toFixed(1)}%`,
    positive: goodWhenPositive ? d >= 0 : d <= 0,
  }
}

const incomeDelta = computed(() =>
  fmtDelta(closing.value ? pctDelta(closing.value.income, closing.value.prev_income) : null, true)
)
const expensesDelta = computed(() =>
  fmtDelta(closing.value ? pctDelta(closing.value.expenses, closing.value.prev_expenses) : null, false)
)
const balanceDelta = computed(() =>
  fmtDelta(closing.value ? pctDelta(closing.value.balance, closing.value.prev_balance) : null, true)
)

// --- Commitment ring ---
const commitmentPct = computed(() => (closing.value?.commitment_rate ?? 0) * 100)

const commitmentColor = computed(() => {
  const r = closing.value?.commitment_rate ?? 0
  return r < 0.7 ? '#34d399' : r < 0.9 ? '#fbbf24' : '#f87171'
})

const commitmentStyle = computed(() => ({
  background: `conic-gradient(from -90deg, ${commitmentColor.value} ${commitmentPct.value}%, rgba(255,255,255,0.06) ${commitmentPct.value}%)`,
}))

// --- Category bars ---
const maxCatPct = computed(() => {
  const cats = closing.value?.top_categories ?? []
  return cats.length ? Math.max(...cats.map(c => c.pct)) : 1
})

// --- Charts ---
const chartContainer = ref<HTMLElement | null>(null)
const sankeyContainer = ref<HTMLElement | null>(null)
let Plotly: any = null

const PLOT_CFG = { displayModeBar: false, responsive: true }

const BASE_LAYOUT = {
  paper_bgcolor: 'transparent',
  plot_bgcolor: 'transparent',
  font: { color: 'rgba(255,255,255,0.35)', family: 'inherit', size: 11 },
  hoverlabel: {
    bgcolor: '#1f2937',
    bordercolor: 'rgba(255,255,255,0.08)',
    font: { color: 'rgba(255,255,255,0.9)', size: 12 },
  },
}

function renderHistoryChart() {
  if (!Plotly || !chartContainer.value || !history.value?.length) return
  const d = history.value

  Plotly.react(chartContainer.value, [
    {
      name: 'Receitas',
      type: 'bar',
      x: d.map(m => m.label),
      y: d.map(m => m.income),
      marker: { color: 'rgba(52,211,153,0.65)' },
      hovertemplate: '<b>%{x}</b><br>Receitas: R$ %{y:,.2f}<extra></extra>',
    },
    {
      name: 'Despesas',
      type: 'bar',
      x: d.map(m => m.label),
      y: d.map(m => m.expenses),
      marker: { color: 'rgba(248,113,113,0.6)' },
      hovertemplate: '<b>%{x}</b><br>Despesas: R$ %{y:,.2f}<extra></extra>',
    },
  ], {
    ...BASE_LAYOUT,
    margin: { t: 8, r: 10, b: 36, l: 60 },
    barmode: 'group',
    bargap: 0.35,
    bargroupgap: 0.06,
    xaxis: {
      gridcolor: 'transparent',
      linecolor: 'rgba(255,255,255,0.05)',
      tickcolor: 'transparent',
    },
    yaxis: {
      gridcolor: 'rgba(255,255,255,0.04)',
      linecolor: 'transparent',
      tickcolor: 'transparent',
      tickprefix: 'R$',
      tickformat: ',.0f',
    },
    legend: {
      orientation: 'h',
      x: 0,
      y: 1.18,
      font: { color: 'rgba(255,255,255,0.45)', size: 11 },
      bgcolor: 'transparent',
    },
  }, PLOT_CFG)
}

function renderSankeyChart() {
  if (!Plotly || !sankeyContainer.value || !sankey.value) return
  const { income, categories } = sankey.value
  if (!Object.keys(categories).length) return

  const catNames = Object.keys(categories)
  const catValues = Object.values(categories)
  const balance = income - catValues.reduce((a, b) => a + b, 0)

  const nodeLabels = ['Receitas', ...catNames]
  const sources = catNames.map(() => 0)
  const targets = catNames.map((_, i) => i + 1)
  const values = [...catValues]

  const CAT_COLORS = [
    'rgba(251,113,133,0.8)', 'rgba(251,146,60,0.8)', 'rgba(251,191,36,0.8)',
    'rgba(163,230,53,0.8)', 'rgba(94,234,212,0.8)', 'rgba(147,197,253,0.8)',
    'rgba(196,181,253,0.8)', 'rgba(249,168,212,0.8)',
  ]

  if (balance > 1) {
    nodeLabels.push('Saldo')
    sources.push(0)
    targets.push(nodeLabels.length - 1)
    values.push(balance)
  }

  Plotly.react(sankeyContainer.value, [{
    type: 'sankey',
    orientation: 'h',
    node: {
      pad: 20,
      thickness: 22,
      line: { color: 'rgba(255,255,255,0.06)', width: 0.5 },
      label: nodeLabels,
      color: [
        '#34d399',
        ...catNames.map((_, i) => CAT_COLORS[i % CAT_COLORS.length]),
        ...(balance > 1 ? ['rgba(99,102,241,0.85)'] : []),
      ],
      hovertemplate: '%{label}<br>R$ %{value:,.2f}<extra></extra>',
    },
    link: {
      source: sources,
      target: targets,
      value: values,
      color: sources.map(() => 'rgba(52,211,153,0.09)'),
      hovertemplate: '%{source.label} → %{target.label}<br>R$ %{value:,.2f}<extra></extra>',
    },
  }], {
    ...BASE_LAYOUT,
    margin: { t: 16, r: 24, b: 16, l: 24 },
  }, PLOT_CFG)
}

onMounted(async () => {
  Plotly = (await import('plotly.js-dist-min')).default
  renderHistoryChart()
  renderSankeyChart()
})

onUnmounted(() => {
  if (Plotly) {
    if (chartContainer.value) Plotly.purge(chartContainer.value)
    if (sankeyContainer.value) Plotly.purge(sankeyContainer.value)
  }
})

watch(history, renderHistoryChart)
watch(sankey, renderSankeyChart)

function changeMonth(delta: number) {
  const d = new Date(currentDate.value)
  d.setMonth(d.getMonth() + delta)
  currentDate.value = d
}
</script>

<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold text-white/90 tracking-tight">
          {{ greeting }}<span v-if="firstName">, {{ firstName }}</span>
        </h1>
        <p class="text-sm text-white/35 mt-0.5 capitalize">{{ monthLabel }}</p>
      </div>
      <div class="flex items-center gap-0.5">
        <button
          class="p-2 rounded-lg text-white/35 hover:text-white/70 hover:bg-white/5 transition-colors"
          @click="changeMonth(-1)"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
        </button>
        <button
          class="p-2 rounded-lg text-white/35 hover:text-white/70 hover:bg-white/5 transition-colors"
          @click="changeMonth(1)"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      </div>
    </div>

    <!-- KPI row -->
    <div v-if="closing" class="grid grid-cols-2 lg:grid-cols-4 gap-3">
      <!-- Receitas -->
      <div class="rounded-xl border border-white/5 bg-gray-900 p-4 lg:p-5">
        <p class="text-[10px] font-semibold uppercase tracking-widest text-white/30 mb-3">Receitas</p>
        <p class="text-2xl font-semibold text-white/90 tabular-nums leading-none">{{ format(closing.income) }}</p>
        <div v-if="incomeDelta" class="flex items-center gap-1.5 mt-2.5">
          <span class="text-xs font-medium" :class="incomeDelta.positive ? 'text-emerald-400' : 'text-rose-400'">
            {{ incomeDelta.text }}
          </span>
          <span class="text-[11px] text-white/20">vs anterior</span>
        </div>
      </div>

      <!-- Despesas -->
      <div class="rounded-xl border border-white/5 bg-gray-900 p-4 lg:p-5">
        <p class="text-[10px] font-semibold uppercase tracking-widest text-white/30 mb-3">Despesas</p>
        <p class="text-2xl font-semibold text-white/90 tabular-nums leading-none">{{ format(closing.expenses) }}</p>
        <div v-if="expensesDelta" class="flex items-center gap-1.5 mt-2.5">
          <span class="text-xs font-medium" :class="expensesDelta.positive ? 'text-emerald-400' : 'text-rose-400'">
            {{ expensesDelta.text }}
          </span>
          <span class="text-[11px] text-white/20">vs anterior</span>
        </div>
      </div>

      <!-- Saldo -->
      <div class="rounded-xl border border-white/5 bg-gray-900 p-4 lg:p-5">
        <p class="text-[10px] font-semibold uppercase tracking-widest text-white/30 mb-3">Saldo</p>
        <p
          class="text-2xl font-semibold tabular-nums leading-none"
          :class="closing.balance >= 0 ? 'text-emerald-400' : 'text-rose-400'"
        >
          {{ format(closing.balance) }}
        </p>
        <div v-if="balanceDelta" class="flex items-center gap-1.5 mt-2.5">
          <span class="text-xs font-medium" :class="balanceDelta.positive ? 'text-emerald-400' : 'text-rose-400'">
            {{ balanceDelta.text }}
          </span>
          <span class="text-[11px] text-white/20">vs anterior</span>
        </div>
      </div>

      <!-- Taxa comprometida -->
      <div class="rounded-xl border border-white/5 bg-gray-900 p-4 lg:p-5 flex items-center gap-4">
        <div class="relative shrink-0 w-[52px] h-[52px]">
          <div class="w-[52px] h-[52px] rounded-full" :style="commitmentStyle">
            <div class="absolute inset-[6px] rounded-full bg-gray-900 flex items-center justify-center">
              <span class="text-[11px] font-semibold text-white/90 tabular-nums">{{ commitmentPct.toFixed(0) }}%</span>
            </div>
          </div>
        </div>
        <div class="min-w-0">
          <p class="text-[10px] font-semibold uppercase tracking-widest text-white/30 mb-1">Comprometida</p>
          <p class="text-sm text-white/55 leading-snug">
            {{ commitmentPct.toFixed(1) }}% da receita
          </p>
          <p class="text-[11px] text-white/25">em despesas</p>
        </div>
      </div>
    </div>

    <!-- Categories + History -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <!-- Top Categories -->
      <div class="rounded-xl border border-white/5 bg-gray-900 p-5">
        <h2 class="text-[10px] font-semibold uppercase tracking-widest text-white/30 mb-5">Top categorias</h2>
        <div v-if="closing?.top_categories?.length" class="space-y-[18px]">
          <div v-for="cat in closing.top_categories" :key="cat.name">
            <div class="flex items-baseline justify-between mb-[7px]">
              <div class="flex items-baseline gap-2 min-w-0 mr-3">
                <span class="text-sm text-white/65 truncate">{{ cat.name }}</span>
                <span class="text-[11px] text-white/25 shrink-0">{{ (cat.pct * 100).toFixed(0) }}%</span>
              </div>
              <span class="text-sm font-medium text-white/85 tabular-nums shrink-0">{{ format(cat.amount) }}</span>
            </div>
            <div class="h-[3px] rounded-full bg-white/5 overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-700"
                :style="{ width: `${(cat.pct / maxCatPct) * 100}%`, background: 'rgba(52,211,153,0.5)' }"
              />
            </div>
          </div>
        </div>
        <p v-else class="text-sm text-white/20 text-center py-10">Sem categorias neste mês</p>
      </div>

      <!-- History chart -->
      <div class="rounded-xl border border-white/5 bg-gray-900 p-5">
        <h2 class="text-[10px] font-semibold uppercase tracking-widest text-white/30 mb-4">Últimos 6 meses</h2>
        <div ref="chartContainer" class="h-[226px]">
          <div v-if="!history" class="h-full flex items-center justify-center text-sm text-white/20">
            Carregando...
          </div>
        </div>
      </div>
    </div>

    <!-- Sankey -->
    <div class="rounded-xl border border-white/5 bg-gray-900 p-5">
      <h2 class="text-[10px] font-semibold uppercase tracking-widest text-white/30 mb-2">Fluxo de caixa</h2>
      <div ref="sankeyContainer" class="h-[370px]">
        <div v-if="!sankey" class="h-full flex items-center justify-center text-sm text-white/20">
          Carregando...
        </div>
        <div
          v-else-if="sankey && !Object.keys(sankey.categories).length"
          class="h-full flex items-center justify-center text-sm text-white/20"
        >
          Sem movimentações neste mês
        </div>
      </div>
    </div>

    <!-- Outliers -->
    <div
      v-if="outliers?.length"
      class="rounded-xl border bg-amber-500/[0.03] p-5"
      style="border-color: rgba(245,158,11,0.12)"
    >
      <div class="flex items-center gap-2 mb-4">
        <svg
          class="w-3.5 h-3.5 text-amber-400 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <h2 class="text-[10px] font-semibold uppercase tracking-widest text-amber-400/70">
          Gastos fora do padrão
        </h2>
      </div>
      <div class="space-y-3">
        <div v-for="o in outliers" :key="o.category" class="flex items-center justify-between">
          <span class="text-sm text-white/65">{{ o.category }}</span>
          <div class="flex items-center gap-3">
            <span class="text-xs text-white/25">esperado ~{{ format(o.expected) }}</span>
            <span class="text-sm font-medium text-amber-400">{{ format(o.actual) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
