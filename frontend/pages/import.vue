<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const toast = useToast()

const importType = ref<'ofx' | 'csv'>('ofx')
const file = ref<File | null>(null)
const accountId = ref('')
const cardId = ref('')
const fileType = ref<'csv' | 'ofx'>('csv')
const loading = ref(false)

interface NamedItem {
  id: string
  name: string
}

const accounts = ref<NamedItem[]>([])
const cards = ref<NamedItem[]>([])

async function loadLookups() {
  const [accs, cds] = await Promise.all([
    api.get<NamedItem[]>('/accounts'),
    api.get<NamedItem[]>('/credit-cards'),
  ])
  accounts.value = accs
  cards.value = cds
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  file.value = target.files?.[0] || null
}

async function handleImport() {
  if (!file.value) return

  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)

    let result: { imported: number }

    if (importType.value === 'ofx') {
      if (accountId.value) {
        formData.append('account_id', accountId.value)
      }
      result = await api.upload('/import/ofx/confirm', formData)
    } else {
      if (cardId.value) {
        formData.append('credit_card_id', cardId.value)
      }
      formData.append('file_type', fileType.value)
      result = await api.upload('/import/csv/confirm', formData)
    }

    toast.add({
      title: `${result.imported} registros importados com sucesso!`,
      color: 'success',
    })
    file.value = null
  } catch (e: any) {
    toast.add({ title: e.message, color: 'error' })
  } finally {
    loading.value = false
  }
}

onMounted(loadLookups)
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-white mb-6">Importar</h1>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <!-- OFX Import -->
      <UCard>
        <template #header>
          <h2 class="font-semibold text-white">Extrato Bancário (OFX)</h2>
        </template>

        <form class="space-y-4" @submit.prevent="importType = 'ofx'; handleImport()">
          <UFormField label="Conta">
            <USelect
              v-model="accountId"
              :items="accounts.map(a => ({ label: a.name, value: a.id }))"
              placeholder="Selecione a conta"
            />
          </UFormField>

          <UFormField label="Arquivo OFX">
            <input
              type="file"
              accept=".ofx"
              class="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-gray-700 file:text-white file:cursor-pointer"
              @change="onFileChange"
            />
          </UFormField>

          <UButton type="submit" :loading="loading" :disabled="!file" block>
            Importar OFX
          </UButton>
        </form>
      </UCard>

      <!-- CSV/OFX Credit Import -->
      <UCard>
        <template #header>
          <h2 class="font-semibold text-white">Fatura de Cartão (CSV/OFX)</h2>
        </template>

        <form class="space-y-4" @submit.prevent="importType = 'csv'; handleImport()">
          <UFormField label="Cartão">
            <USelect
              v-model="cardId"
              :items="cards.map(c => ({ label: c.name, value: c.id }))"
              placeholder="Selecione o cartão"
            />
          </UFormField>

          <UFormField label="Tipo de arquivo">
            <USelect
              v-model="fileType"
              :items="[
                { label: 'CSV', value: 'csv' },
                { label: 'OFX', value: 'ofx' },
              ]"
            />
          </UFormField>

          <UFormField label="Arquivo">
            <input
              type="file"
              :accept="fileType === 'csv' ? '.csv' : '.ofx'"
              class="w-full text-sm text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:bg-gray-700 file:text-white file:cursor-pointer"
              @change="onFileChange"
            />
          </UFormField>

          <UButton type="submit" :loading="loading" :disabled="!file" block>
            Importar Fatura
          </UButton>
        </form>
      </UCard>
    </div>
  </div>
</template>
