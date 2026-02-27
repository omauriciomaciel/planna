<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()

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
  bankName: string
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
const selectedBank = ref<BankOption | undefined>(undefined)
const newCard = ref('')
const selectedCardAccount = ref<AccountOption | undefined>(undefined)
const newCardDueDay = ref<number | null>(null)
const newCardClosingDay = ref<number | null>(null)
const newCardLimit = ref<number | null>(null)
const newCardLimitDisplay = ref('')

function handleLimitInput(e: Event) {
  const digits = (e.target as HTMLInputElement).value.replace(/\D/g, '')
  const cents = parseInt(digits || '0', 10)
  newCardLimit.value = cents > 0 ? cents / 100 : null
  newCardLimitDisplay.value = cents > 0
    ? (cents / 100).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
    : ''
}

async function loadData() {
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
    bankName: b.full_name,
    bankIspb: b.ispb,
  }))
  accountOptions.value = accs.map(a => ({ label: a.name, value: a.id }))
}

async function addAccount() {
  if (!selectedBank.value) return
  await api.post('/accounts', { bank_ispb: selectedBank.value.bankIspb })
  selectedBank.value = undefined
  await loadData()
}

async function deleteAccount(id: string) {
  await api.delete(`/accounts/${id}`)
  await loadData()
}

async function addCard() {
  if (!newCard.value.trim()) return
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
}

async function deleteCard(id: string) {
  await api.delete(`/credit-cards/${id}`)
  await loadData()
}

function accountNameForCard(card: CreditCard): string | null {
  if (!card.account_id) return null
  return accounts.value.find(a => a.id === card.account_id)?.name ?? null
}

onMounted(loadData)
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-white mb-6">Contas e Cartões</h1>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- Accounts -->
      <UCard>
        <template #header>
          <h2 class="font-semibold text-white">Contas Bancárias</h2>
        </template>

        <form class="flex gap-3 mb-4" @submit.prevent="addAccount">
          <USelectMenu
            v-model="selectedBank"
            :items="bankOptions"
            placeholder="Buscar banco..."
            searchable
            search-placeholder="Nome ou código..."
            class="flex-1"
          />
          <UButton type="submit" icon="i-heroicons-plus" :disabled="!selectedBank">
            Adicionar
          </UButton>
        </form>

        <div class="divide-y divide-gray-800">
          <div
            v-for="account in accounts"
            :key="account.id"
            class="flex items-center justify-between py-3"
          >
            <div class="flex flex-col">
              <span class="text-white text-sm font-medium">{{ account.name }}</span>
              <span v-if="account.bank?.code" class="text-gray-400 text-xs">
                Código {{ account.bank.code }}
              </span>
            </div>
            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              @click="deleteAccount(account.id)"
            />
          </div>
        </div>
      </UCard>

      <!-- Credit Cards -->
      <UCard>
        <template #header>
          <h2 class="font-semibold text-white">Cartões de Crédito</h2>
        </template>

        <form class="flex flex-col gap-2 mb-4" @submit.prevent="addCard">
          <div class="flex gap-3">
            <UInput v-model="newCard" placeholder="Nome do cartão" class="flex-1" />
            <UButton type="submit" icon="i-heroicons-plus" :disabled="!newCard.trim()">
              Adicionar
            </UButton>
          </div>
          <USelectMenu
            v-model="selectedCardAccount"
            :items="accountOptions"
            placeholder="Vincular a uma conta (opcional)"
            class="w-full"
          />
          <div class="grid grid-cols-3 gap-2">
            <UInput
              v-model.number="newCardClosingDay"
              type="number"
              placeholder="Dia fechamento"
              :min="1"
              :max="31"
            />
            <UInput
              v-model.number="newCardDueDay"
              type="number"
              placeholder="Dia vencimento"
              :min="1"
              :max="31"
            />
            <UInput
              :value="newCardLimitDisplay"
              type="text"
              placeholder="Limite (R$)"
              inputmode="numeric"
              @input="handleLimitInput"
            />
          </div>
        </form>

        <div class="divide-y divide-gray-800">
          <div
            v-for="card in cards"
            :key="card.id"
            class="flex items-center justify-between py-3"
          >
            <div class="flex flex-col">
              <span class="text-white text-sm font-medium">{{ card.name }}</span>
              <span class="text-gray-400 text-xs">
                <span v-if="accountNameForCard(card)">{{ accountNameForCard(card) }}</span>
                <span v-if="accountNameForCard(card) && (card.due_day || card.limit)"> · </span>
                <span v-if="card.due_day">Venc. dia {{ card.due_day }}</span>
                <span v-if="card.due_day && card.closing_day"> · </span>
                <span v-if="card.closing_day">Fech. dia {{ card.closing_day }}</span>
                <span v-if="(card.due_day || card.closing_day) && card.limit"> · </span>
                <span v-if="card.limit">Limite {{ useCurrency().format(card.limit) }}</span>
              </span>
            </div>
            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              @click="deleteCard(card.id)"
            />
          </div>
        </div>
      </UCard>
    </div>
  </div>
</template>
