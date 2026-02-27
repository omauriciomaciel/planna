<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const { format } = useCurrency()

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
  due_date: string | null
}

interface LookupOption {
  label: string
  value: string
}

const purchases = ref<CreditPurchase[]>([])
const loading = ref(true)

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
const formDueDate = ref('')
const formCard = ref<LookupOption | undefined>()
const formCategory = ref<LookupOption | undefined>()
const saving = ref(false)

const totalMonthly = computed(() =>
  purchases.value.reduce((sum, p) => sum + Number(p.installment_amount), 0)
)

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

async function loadPurchases() {
  loading.value = true
  try {
    purchases.value = await api.get<CreditPurchase[]>('/credit-purchases?limit=100')
  } finally {
    loading.value = false
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
  formDueDate.value = ''
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
  formDueDate.value = p.due_date ?? ''
  formCard.value = cardOptions.value.find(o => o.value === p.credit_card_id)
  formCategory.value = categoryOptions.value.find(o => o.value === p.category_id)
  showForm.value = true
}

async function savePurchase() {
  if (!formMerchant.value.trim() || !formTotalAmountRaw.value || !formDate.value) return
  saving.value = true
  try {
    const payload = {
      merchant: formMerchant.value.trim(),
      total_amount: formTotalAmountRaw.value,
      installment_amount: formInstallmentAmountRaw.value ?? formTotalAmountRaw.value,
      total_installments: formTotalInstallments.value,
      current_installment: formCurrentInstallment.value,
      purchase_date: formDate.value,
      due_date: formDueDate.value || null,
      credit_card_id: formCard.value?.value ?? null,
      category_id: formCategory.value?.value ?? null,
    }
    if (editingId.value) {
      await api.put(`/credit-purchases/${editingId.value}`, payload)
    } else {
      await api.post('/credit-purchases', payload)
    }
    cancelForm()
    await loadPurchases()
  } finally {
    saving.value = false
  }
}

async function deletePurchase(id: string) {
  await api.delete(`/credit-purchases/${id}`)
  await loadPurchases()
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

onMounted(() => {
  loadPurchases()
  loadLookups()
})
</script>

<template>
  <div>
    <!-- Header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-xl font-semibold text-white/90 tracking-tight">Crédito</h1>
        <p class="text-sm text-gray-500 mt-1">
          <template v-if="loading">Carregando...</template>
          <template v-else>
            {{ purchases.length }} compra{{ purchases.length !== 1 ? 's' : '' }}
            <template v-if="purchases.length > 0">
              · <span class="text-violet-400 tabular-nums">{{ format(totalMonthly) }}/mês</span>
            </template>
          </template>
        </p>
      </div>
      <UButton icon="i-heroicons-plus" @click="editingId ? cancelForm() : (showForm = !showForm)">
        Nova compra
      </UButton>
    </div>

    <!-- Form -->
    <div v-if="showForm" class="rounded-xl border border-white/8 bg-white/[0.03] p-5 mb-4">
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
            <span class="text-xs text-gray-600">
              Vencimento <span class="font-normal text-gray-700">(opcional)</span>
            </span>
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
    <div class="rounded-xl border border-white/8 overflow-hidden">

      <!-- Column header -->
      <div class="flex items-center gap-4 px-4 py-2 border-b border-white/5 bg-white/[0.015]">
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
          class="flex items-center gap-4 px-4 py-3.5 border-b border-white/5 last:border-0"
        >
          <div class="h-2.5 w-10 bg-white/5 rounded animate-pulse shrink-0" />
          <div class="h-3 bg-white/5 rounded animate-pulse flex-1" />
          <div class="h-2.5 w-24 bg-white/5 rounded animate-pulse shrink-0 hidden lg:block" />
          <div class="h-2.5 w-24 bg-white/5 rounded animate-pulse shrink-0 hidden lg:block" />
          <div class="h-2.5 w-24 bg-white/5 rounded animate-pulse shrink-0 hidden sm:block" />
          <div class="h-3 w-20 bg-white/5 rounded animate-pulse shrink-0" />
          <div class="w-16 shrink-0" />
        </div>
      </div>

      <!-- Empty state -->
      <template v-else-if="purchases.length === 0">
        <div class="flex flex-col items-center justify-center py-16 px-6 text-center">
          <div class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center mb-3">
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
          class="group flex items-center gap-4 px-4 py-3 border-b border-white/5 last:border-0 transition-colors"
          :class="editingId === p.id ? 'bg-white/[0.05]' : 'hover:bg-white/[0.02]'"
        >
          <!-- Date -->
          <span class="text-xs text-gray-500 tabular-nums w-14 shrink-0">
            {{ formatDate(p.purchase_date) }}
          </span>

          <!-- Merchant -->
          <span class="flex-1 text-sm text-white/80 truncate min-w-0">
            {{ p.merchant }}
          </span>

          <!-- Card -->
          <div class="w-28 shrink-0 hidden lg:block overflow-hidden">
            <span
              v-if="p.credit_card_name"
              class="text-xs text-violet-400/80 bg-violet-500/10 px-1.5 py-0.5 rounded truncate block max-w-full"
            >{{ p.credit_card_name }}</span>
          </div>

          <!-- Category -->
          <div class="w-28 shrink-0 hidden lg:block overflow-hidden">
            <span
              v-if="p.category_name"
              class="text-xs text-gray-500 bg-white/5 px-1.5 py-0.5 rounded truncate block max-w-full"
            >{{ p.category_name }}</span>
          </div>

          <!-- Installment progress -->
          <div class="w-28 shrink-0 hidden sm:flex flex-col items-center gap-1.5">
            <div class="flex items-center gap-[3px]">
              <span
                v-for="(filled, i) in installmentDots(p.current_installment, p.total_installments)"
                :key="i"
                class="w-1 h-1 rounded-full"
                :class="filled ? 'bg-violet-400' : 'bg-white/15'"
              />
            </div>
            <span class="text-xs text-gray-600 tabular-nums">
              {{ p.current_installment }}/{{ p.total_installments }}
            </span>
          </div>

          <!-- Installment amount -->
          <span class="text-sm font-medium tabular-nums text-white/80 w-24 text-right shrink-0">
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
              @click="deletePurchase(p.id)"
            />
          </div>
        </div>
      </template>

    </div>
  </div>
</template>
