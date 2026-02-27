<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()

interface NamedItem {
  id: string
  name: string
}

const accounts = ref<NamedItem[]>([])
const cards = ref<NamedItem[]>([])
const newAccount = ref('')
const newCard = ref('')

async function loadData() {
  const [accs, cds] = await Promise.all([
    api.get<NamedItem[]>('/accounts'),
    api.get<NamedItem[]>('/credit-cards'),
  ])
  accounts.value = accs
  cards.value = cds
}

async function addAccount() {
  if (!newAccount.value.trim()) return
  await api.post('/accounts', { name: newAccount.value.trim() })
  newAccount.value = ''
  await loadData()
}

async function deleteAccount(id: string) {
  await api.delete(`/accounts/${id}`)
  await loadData()
}

async function addCard() {
  if (!newCard.value.trim()) return
  await api.post('/credit-cards', { name: newCard.value.trim() })
  newCard.value = ''
  await loadData()
}

async function deleteCard(id: string) {
  await api.delete(`/credit-cards/${id}`)
  await loadData()
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
          <UInput v-model="newAccount" placeholder="Nome da conta" class="flex-1" />
          <UButton type="submit" icon="i-heroicons-plus">Adicionar</UButton>
        </form>

        <div class="divide-y divide-gray-800">
          <div
            v-for="account in accounts"
            :key="account.id"
            class="flex items-center justify-between py-3"
          >
            <span class="text-white">{{ account.name }}</span>
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

        <form class="flex gap-3 mb-4" @submit.prevent="addCard">
          <UInput v-model="newCard" placeholder="Nome do cartão" class="flex-1" />
          <UButton type="submit" icon="i-heroicons-plus">Adicionar</UButton>
        </form>

        <div class="divide-y divide-gray-800">
          <div
            v-for="card in cards"
            :key="card.id"
            class="flex items-center justify-between py-3"
          >
            <span class="text-white">{{ card.name }}</span>
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
