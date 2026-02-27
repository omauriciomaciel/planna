<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const { format: formatCurrency } = useCurrency()

interface Bank {
  ispb: string
  code: number | null
  name: string
  full_name: string
}

interface Account {
  id: string
  name: string
  bank_ispb: string | null
  bank: Bank | null
  initial_balance: number
  current_balance: number
}

interface CreditCard {
  id: string
  name: string
  account_id: string | null
  due_day: number | null
  closing_day: number | null
  limit: number | null
}

interface BankOption {
  label: string
  value: string
  bankIspb: string
}

interface AccountOption {
  label: string
  value: string
}

const accounts = ref<Account[]>([])
const cards = ref<CreditCard[]>([])
const bankOptions = ref<BankOption[]>([])
const accountOptions = ref<AccountOption[]>([])
const loading = ref(true)

// Account form
const selectedBank = ref<BankOption | undefined>(undefined)
const newAccountInitialBalance = ref(0)
const newAccountInitialBalanceDisplay = ref('')
const savingAccount = ref(false)

function handleInitialBalanceInput(e: Event) {
  const digits = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const cents = parseInt(digits || '0', 10)
  newAccountInitialBalance.value = cents / 100
  newAccountInitialBalanceDisplay.value = cents > 0
    ? (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : ''
}

// Card form
const newCard = ref('')
const selectedCardAccount = ref<AccountOption | undefined>(undefined)
const newCardDueDay = ref<number | null>(null)
const newCardClosingDay = ref<number | null>(null)
const newCardLimit = ref<number | null>(null)
const newCardLimitDisplay = ref('')
const savingCard = ref(false)

function handleLimitInput(e: Event) {
  const digits = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const cents = parseInt(digits || '0', 10)
  newCardLimit.value = cents > 0 ? cents / 100 : null
  newCardLimitDisplay.value = cents > 0
    ? (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : ''
}

async function loadData() {
  loading.value = true
  const [accs, cds, banks] = await Promise.all([
    api.get<Account[]>('/accounts'),
    api.get<CreditCard[]>('/credit-cards'),
    api.get<Bank[]>('/banks'),
  ])
  accounts.value = accs
  cards.value = cds
  bankOptions.value = banks.map(b => ({
    label: b.code ? `${b.code} – ${b.full_name}` : b.full_name,
    value: b.ispb,
    bankIspb: b.ispb,
  }))
  accountOptions.value = accs.map(a => ({ label: a.name, value: a.id }))
  loading.value = false
}

async function addAccount() {
  if (!selectedBank.value) return
  savingAccount.value = true
  await api.post('/accounts', {
    bank_ispb: selectedBank.value.bankIspb,
    initial_balance: newAccountInitialBalance.value,
  })
  selectedBank.value = undefined
  newAccountInitialBalance.value = 0
  newAccountInitialBalanceDisplay.value = ''
  await loadData()
  savingAccount.value = false
}

async function deleteAccount(id: string) {
  await api.delete(`/accounts/${id}`)
  await loadData()
}

async function addCard() {
  if (!newCard.value.trim()) return
  savingCard.value = true
  await api.post('/credit-cards', {
    name: newCard.value.trim(),
    account_id: selectedCardAccount.value?.value ?? null,
    due_day: newCardDueDay.value,
    closing_day: newCardClosingDay.value,
    limit: newCardLimit.value,
  })
  newCard.value = ''
  selectedCardAccount.value = undefined
  newCardDueDay.value = null
  newCardClosingDay.value = null
  newCardLimit.value = null
  newCardLimitDisplay.value = ''
  await loadData()
  savingCard.value = false
}

async function deleteCard(id: string) {
  await api.delete(`/credit-cards/${id}`)
  await loadData()
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

function accountNameForCard(card: CreditCard): string | null {
  if (!card.account_id) return null
  return accounts.value.find(a => a.id === card.account_id)?.name ?? null
}

onMounted(loadData)
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-white tracking-tight">Contas e Cartões</h1>
      <p class="text-sm text-gray-500 mt-1">Gerencie suas contas bancárias e cartões de crédito</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-x-6 gap-y-4">

      <!-- ── Row 1: Headers ── -->
      <div class="flex items-center justify-between">
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Contas Bancárias</h2>
        <span class="text-xs text-gray-600 tabular-nums">{{ accounts.length }} conta{{ accounts.length !== 1 ? 's' : '' }}</span>
      </div>
      <div class="flex items-center justify-between">
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Cartões de Crédito</h2>
        <span class="text-xs text-gray-600 tabular-nums">{{ cards.length }} cartão{{ cards.length !== 1 ? 'ões' : '' }}</span>
      </div>

      <!-- ── Row 2: Forms (mesmo grid row = mesma altura) ── -->

      <!-- Add account form -->
      <form class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-4 flex flex-col gap-4" @submit.prevent="addAccount">
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 uppercase tracking-wide">Banco</label>
          <div class="flex gap-2">
            <USelectMenu
              v-model="selectedBank"
              :items="bankOptions"
              placeholder="Buscar banco pelo nome ou código..."
              searchable
              search-placeholder="Ex: Bradesco, 237..."
              class="flex-1 min-w-0"
            />
            <UButton
              type="submit"
              icon="i-heroicons-plus"
              :loading="savingAccount"
              :disabled="!selectedBank || savingAccount"
              class="shrink-0"
            />
          </div>
        </div>
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Saldo inicial
          </label>
          <UInput
            :value="newAccountInitialBalanceDisplay"
            type="text"
            placeholder="R$ 0,00"
            inputmode="numeric"
            @input="handleInitialBalanceInput"
          />
        </div>
      </form>

      <!-- Add card form -->
      <div class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-4 flex flex-col gap-4">
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 uppercase tracking-wide">Nome do cartão</label>
          <div class="flex gap-2">
            <UInput v-model="newCard" placeholder="Ex: Nubank, Itaú Gold..." class="flex-1 min-w-0" />
            <UButton
              type="button"
              icon="i-heroicons-plus"
              :loading="savingCard"
              :disabled="!newCard.trim() || savingCard"
              class="shrink-0"
              @click="addCard"
            />
          </div>
        </div>
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 uppercase tracking-wide">
            Conta vinculada <span class="normal-case font-normal text-gray-600">(opcional)</span>
          </label>
          <USelectMenu
            v-model="selectedCardAccount"
            :items="accountOptions"
            placeholder="Selecionar conta..."
            class="w-full"
          />
        </div>
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 uppercase tracking-wide">Ciclo de cobrança</label>
          <div class="grid grid-cols-3 gap-2">
            <div class="flex flex-col gap-1">
              <span class="text-xs text-gray-600">Fechamento</span>
              <UInput v-model.number="newCardClosingDay" type="number" placeholder="Dia" :min="1" :max="31" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-gray-600">Vencimento</span>
              <UInput v-model.number="newCardDueDay" type="number" placeholder="Dia" :min="1" :max="31" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-xs text-gray-600">Limite</span>
              <UInput :value="newCardLimitDisplay" type="text" placeholder="R$ 0,00" inputmode="numeric" @input="handleLimitInput" />
            </div>
          </div>
        </div>
      </div>

      <!-- ── Row 3: Lists (mesmo grid row = topo alinhado) ── -->

      <!-- Accounts list -->
      <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">
        <div v-if="loading" class="divide-y divide-black/5 dark:divide-white/5">
          <div v-for="i in 2" :key="i" class="flex items-center gap-3 px-4 py-3">
            <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 animate-pulse shrink-0" />
            <div class="flex flex-col gap-1.5 flex-1">
              <div class="h-3 w-40 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
              <div class="h-2.5 w-16 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
            </div>
          </div>
        </div>
        <template v-else-if="accounts.length === 0">
          <div class="flex flex-col items-center justify-center py-10 px-6 text-center">
            <div class="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-3">
              <UIcon name="i-heroicons-building-library" class="text-gray-600 text-lg" />
            </div>
            <p class="text-sm text-gray-500">Nenhuma conta cadastrada</p>
            <p class="text-xs text-gray-600 mt-1">Selecione um banco acima para começar</p>
          </div>
        </template>
        <template v-else>
          <div
            v-for="account in accounts"
            :key="account.id"
            class="group flex items-center gap-3 px-4 py-3 border-b border-black/5 dark:border-white/5 last:border-0 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
          >
            <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
              <UIcon name="i-heroicons-building-library" class="text-gray-400 text-sm" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-900 dark:text-white truncate">{{ account.name }}</p>
              <p v-if="account.bank?.code" class="text-xs text-gray-500">
                Código {{ account.bank.code }} · ISPB {{ account.bank_ispb }}
              </p>
            </div>
            <div class="text-right shrink-0 mr-1">
              <p
                class="text-sm font-medium tabular-nums"
                :class="account.current_balance >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'"
              >
                {{ formatCurrency(account.current_balance) }}
              </p>
              <p class="text-xs text-gray-600 tabular-nums">
                inicial {{ formatCurrency(account.initial_balance) }}
              </p>
            </div>
            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              @click="requestDelete(account.name, () => deleteAccount(account.id))"
            />
          </div>
        </template>
      </div>

      <!-- Cards list -->
      <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">
        <div v-if="loading" class="divide-y divide-black/5 dark:divide-white/5">
          <div v-for="i in 2" :key="i" class="flex items-center gap-3 px-4 py-3">
            <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 animate-pulse shrink-0" />
            <div class="flex flex-col gap-1.5 flex-1">
              <div class="h-3 w-32 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
              <div class="h-2.5 w-48 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
            </div>
          </div>
        </div>
        <template v-else-if="cards.length === 0">
          <div class="flex flex-col items-center justify-center py-10 px-6 text-center">
            <div class="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-3">
              <UIcon name="i-heroicons-credit-card" class="text-gray-600 text-lg" />
            </div>
            <p class="text-sm text-gray-500">Nenhum cartão cadastrado</p>
            <p class="text-xs text-gray-600 mt-1">Preencha o formulário acima para adicionar</p>
          </div>
        </template>
        <template v-else>
          <div
            v-for="card in cards"
            :key="card.id"
            class="group flex items-center gap-3 px-4 py-3 border-b border-black/5 dark:border-white/5 last:border-0 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
          >
            <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
              <UIcon name="i-heroicons-credit-card" class="text-gray-400 text-sm" />
            </div>
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2">
                <p class="text-sm font-medium text-gray-900 dark:text-white">{{ card.name }}</p>
                <span
                  v-if="accountNameForCard(card)"
                  class="text-xs text-gray-500 bg-black/5 dark:bg-white/5 px-1.5 py-0.5 rounded truncate max-w-[120px]"
                >{{ accountNameForCard(card) }}</span>
              </div>
              <div class="flex items-center gap-3 mt-0.5">
                <span v-if="card.closing_day" class="text-xs text-gray-500">
                  Fech. <span class="text-gray-400 tabular-nums">{{ card.closing_day }}</span>
                </span>
                <span v-if="card.due_day" class="text-xs text-gray-500">
                  Venc. <span class="text-gray-400 tabular-nums">{{ card.due_day }}</span>
                </span>
                <span v-if="card.limit" class="text-xs text-gray-400 tabular-nums font-medium">
                  {{ formatCurrency(card.limit) }}
                </span>
              </div>
            </div>
            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              @click="requestDelete(card.name, () => deleteCard(card.id))"
            />
          </div>
        </template>
      </div>

    </div>

    <UModal
      v-model:open="confirmDeleteOpen"
      title="Confirmar exclusão"
      :description="`&quot;${deleteTargetLabel}&quot; será removido permanentemente.`"
    >
      <template #actions>
        <UButton variant="ghost" color="neutral" @click="confirmDeleteOpen = false">Cancelar</UButton>
        <UButton color="error" :loading="deleting" @click="confirmDelete">Excluir</UButton>
      </template>
    </UModal>
  </div>
</template>
