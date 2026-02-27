<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const { format } = useCurrency()

interface Transaction {
  id: string
  date: string
  due_date: string | null
  description: string
  account_id: string | null
  category_id: string | null
  account_name: string | null
  category_name: string | null
  type: string
  amount: number
  status: string
}

interface LookupOption {
  label: string
  value: string
}

const transactions = ref<Transaction[]>([])
const loading = ref(true)

// Lookups for form selects
const accountOptions = ref<LookupOption[]>([])
const categoryOptions = ref<LookupOption[]>([])

// Form state
const showForm = ref(false)
const editingId = ref<string | null>(null)
const formType = ref<'income' | 'expense'>('expense')
const formDescription = ref('')
const formAmountDisplay = ref('')
const formAmountRaw = ref<number | null>(null)
const formDate = ref(new Date().toISOString().split('T')[0])
const formAccount = ref<LookupOption | undefined>()
const formCategory = ref<LookupOption | undefined>()
const formPaid = ref(false)
const saving = ref(false)

function handleAmountInput(e: Event) {
  const digits = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const cents = parseInt(digits || '0', 10)
  formAmountRaw.value = cents > 0 ? cents / 100 : null
  formAmountDisplay.value = cents > 0
    ? (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : ''
}

async function loadTransactions() {
  loading.value = true
  try {
    transactions.value = await api.get<Transaction[]>('/transactions?limit=100')
  } finally {
    loading.value = false
  }
}

async function loadLookups() {
  const [accountsResult, categoriesResult] = await Promise.allSettled([
    api.get<{ id: string; name: string }[]>('/accounts'),
    api.get<{ id: string; name: string; emoji: string | null }[]>('/categories'),
  ])
  if (accountsResult.status === 'fulfilled') {
    accountOptions.value = accountsResult.value.map(a => ({ label: a.name, value: String(a.id) }))
  }
  if (categoriesResult.status === 'fulfilled') {
    categoryOptions.value = categoriesResult.value.map(c => ({
      label: c.emoji ? `${c.emoji} ${c.name}` : c.name,
      value: String(c.id),
    }))
  }
}

async function loadData() {
  await loadTransactions()
}

function cancelForm() {
  showForm.value = false
  editingId.value = null
  formType.value = 'expense'
  formDescription.value = ''
  formAmountDisplay.value = ''
  formAmountRaw.value = null
  formDate.value = new Date().toISOString().split('T')[0]
  formAccount.value = undefined
  formCategory.value = undefined
  formPaid.value = false
}

function startEdit(tx: Transaction) {
  editingId.value = tx.id
  formType.value = tx.type as 'income' | 'expense'
  formDescription.value = tx.description
  formAmountRaw.value = Number(tx.amount)
  formAmountDisplay.value = Number(tx.amount).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
  formDate.value = tx.date
  formAccount.value = accountOptions.value.find(o => o.value === tx.account_id)
  formCategory.value = categoryOptions.value.find(o => o.value === tx.category_id)
  formPaid.value = tx.status === 'paid'
  showForm.value = true
}

async function saveTransaction() {
  if (!formDescription.value.trim() || !formAmountRaw.value || !formDate.value) return
  saving.value = true
  try {
    const payload = {
      date: formDate.value,
      description: formDescription.value.trim(),
      account_id: formAccount.value?.value ?? null,
      category_id: formCategory.value?.value ?? null,
      type: formType.value,
      amount: formAmountRaw.value,
      status: formPaid.value ? 'paid' : 'unpaid',
    }
    if (editingId.value) {
      await api.put(`/transactions/${editingId.value}`, payload)
    } else {
      await api.post('/transactions', payload)
    }
    cancelForm()
    await loadData()
  } finally {
    saving.value = false
  }
}

async function deleteTransaction(id: string) {
  await api.delete(`/transactions/${id}`)
  await loadData()
}

function formatDate(dateStr: string) {
  const [, month, day] = dateStr.split('-')
  return `${day}/${month}`
}

onMounted(() => {
  loadTransactions()
  loadLookups()
})
</script>

<template>
  <div>
    <!-- Page header -->
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-xl font-semibold text-white/90 tracking-tight">Lançamentos</h1>
        <p class="text-sm text-gray-500 mt-1">
          {{ loading ? 'Carregando...' : `${transactions.length} lançamentos` }}
        </p>
      </div>
      <UButton icon="i-heroicons-plus" @click="editingId ? cancelForm() : (showForm = !showForm)">
        Novo lançamento
      </UButton>
    </div>

    <!-- Add form -->
    <div v-if="showForm" class="rounded-xl border border-white/8 bg-white/[0.03] p-5 mb-4">
      <div class="flex items-center justify-between mb-4">
        <label class="text-xs font-medium text-gray-500 uppercase tracking-wide">
          {{ editingId ? 'Editar lançamento' : 'Novo lançamento' }}
        </label>
        <!-- Type toggle -->
        <div class="flex rounded-lg overflow-hidden border border-white/8 text-sm">
          <button
            type="button"
            :class="formType === 'expense'
              ? 'bg-red-500/15 text-red-400'
              : 'text-gray-500 hover:text-gray-300'"
            class="px-4 py-1.5 font-medium transition-colors border-r border-white/8"
            @click="formType = 'expense'"
          >
            Saída
          </button>
          <button
            type="button"
            :class="formType === 'income'
              ? 'bg-emerald-500/15 text-emerald-400'
              : 'text-gray-500 hover:text-gray-300'"
            class="px-4 py-1.5 font-medium transition-colors"
            @click="formType = 'income'"
          >
            Entrada
          </button>
        </div>
      </div>

      <form class="space-y-3" @submit.prevent="saveTransaction">
        <!-- Description -->
        <UInput
          v-model="formDescription"
          placeholder="Descrição do lançamento..."
          class="w-full"
        />

        <!-- Amount + Date -->
        <div class="grid grid-cols-2 gap-3">
          <UInput
            :value="formAmountDisplay"
            placeholder="R$ 0,00"
            inputmode="numeric"
            @input="handleAmountInput"
          />
          <UInput v-model="formDate" type="date" />
        </div>

        <!-- Account + Category -->
        <div class="grid grid-cols-2 gap-3">
          <USelectMenu
            v-model="formAccount"
            :items="accountOptions"
            placeholder="Conta..."
          />
          <USelectMenu
            v-model="formCategory"
            :items="categoryOptions"
            placeholder="Categoria..."
          />
        </div>

        <!-- Status + Actions -->
        <div class="flex items-center justify-between pt-1">
          <UCheckbox v-model="formPaid" label="Marcar como pago" />
          <div class="flex gap-2">
            <UButton variant="ghost" color="neutral" @click="cancelForm">Cancelar</UButton>
            <UButton
              type="submit"
              :loading="saving"
              :disabled="!formDescription.trim() || !formAmountRaw || saving"
              :icon="editingId ? 'i-heroicons-check' : 'i-heroicons-plus'"
            >
              {{ editingId ? 'Salvar' : 'Adicionar' }}
            </UButton>
          </div>
        </div>
      </form>
    </div>

    <!-- Transaction list -->
    <div class="rounded-xl border border-white/8 overflow-hidden">

      <!-- Column header -->
      <div class="flex items-center gap-4 px-4 py-2 border-b border-white/5 bg-white/[0.015]">
        <span class="text-xs font-medium text-gray-600 w-14 shrink-0">Data</span>
        <span class="text-xs font-medium text-gray-600 flex-1">Descrição</span>
        <span class="text-xs font-medium text-gray-600 w-24 shrink-0 hidden md:block">Conta</span>
        <span class="text-xs font-medium text-gray-600 w-28 shrink-0 hidden md:block">Categoria</span>
        <span class="text-xs font-medium text-gray-600 w-24 text-right shrink-0">Valor</span>
        <span class="text-xs font-medium text-gray-600 w-16 shrink-0 hidden sm:block">Status</span>
        <span class="w-16 shrink-0" />
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading">
        <div
          v-for="i in 8"
          :key="i"
          class="flex items-center gap-4 px-4 py-3 border-b border-white/5 last:border-0"
        >
          <div class="h-2.5 w-10 bg-white/5 rounded animate-pulse shrink-0" />
          <div class="h-3 bg-white/5 rounded animate-pulse flex-1" />
          <div class="h-2.5 w-20 bg-white/5 rounded animate-pulse shrink-0 hidden md:block" />
          <div class="h-2.5 w-20 bg-white/5 rounded animate-pulse shrink-0 hidden md:block" />
          <div class="h-3 w-20 bg-white/5 rounded animate-pulse shrink-0" />
          <div class="h-5 w-14 bg-white/5 rounded-full animate-pulse shrink-0 hidden sm:block" />
          <div class="w-16 shrink-0" />
        </div>
      </div>

      <!-- Empty state -->
      <template v-else-if="transactions.length === 0">
        <div class="flex flex-col items-center justify-center py-16 px-6 text-center">
          <div class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center mb-3">
            <UIcon name="i-heroicons-banknotes" class="text-gray-600 text-lg" />
          </div>
          <p class="text-sm text-gray-500">Nenhum lançamento encontrado</p>
          <p class="text-xs text-gray-600 mt-1">Adicione um lançamento ou importe um arquivo OFX/CSV</p>
          <UButton variant="soft" class="mt-4" icon="i-heroicons-plus" @click="showForm = true">
            Adicionar lançamento
          </UButton>
        </div>
      </template>

      <!-- Rows -->
      <template v-else>
        <div
          v-for="tx in transactions"
          :key="tx.id"
          class="group flex items-center gap-4 px-4 py-3 border-b border-white/5 last:border-0 transition-colors"
          :class="editingId === tx.id ? 'bg-white/[0.05]' : 'hover:bg-white/[0.02]'"
        >
          <!-- Date -->
          <span class="text-xs text-gray-500 tabular-nums w-14 shrink-0">
            {{ formatDate(tx.date) }}
          </span>

          <!-- Description -->
          <span class="flex-1 text-sm text-white/80 truncate min-w-0">
            {{ tx.description }}
          </span>

          <!-- Account -->
          <span
            v-if="tx.account_name"
            class="text-xs text-gray-500 bg-white/5 px-1.5 py-0.5 rounded truncate max-w-[96px] shrink-0 hidden md:block"
          >{{ tx.account_name }}</span>
          <span v-else class="w-24 shrink-0 hidden md:block" />

          <!-- Category -->
          <span
            v-if="tx.category_name"
            class="text-xs text-gray-500 bg-white/5 px-1.5 py-0.5 rounded truncate max-w-[112px] shrink-0 hidden md:block"
          >{{ tx.category_name }}</span>
          <span v-else class="w-28 shrink-0 hidden md:block" />

          <!-- Amount -->
          <span
            :class="tx.type === 'income' ? 'text-emerald-400' : 'text-red-400'"
            class="text-sm font-medium tabular-nums w-24 text-right shrink-0"
          >
            {{ tx.type === 'expense' ? '−' : '+' }}{{ format(tx.amount) }}
          </span>

          <!-- Status -->
          <div class="w-16 shrink-0 hidden sm:flex justify-start">
            <UBadge
              :color="tx.status === 'paid' ? 'success' : 'warning'"
              variant="subtle"
              size="sm"
            >
              {{ tx.status === 'paid' ? 'Pago' : 'Pendente' }}
            </UBadge>
          </div>

          <!-- Actions -->
          <div class="w-16 shrink-0 flex items-center justify-end gap-1">
            <UButton
              variant="ghost"
              color="neutral"
              icon="i-heroicons-pencil-square"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity"
              @click="startEdit(tx)"
            />
            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity"
              @click="deleteTransaction(tx.id)"
            />
          </div>
        </div>
      </template>

    </div>
  </div>
</template>
