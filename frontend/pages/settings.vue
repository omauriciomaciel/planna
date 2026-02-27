<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const toast = useToast()

interface Settings {
  auto_categorize: boolean
  notify_due_expenses: boolean
  due_days_ahead: number
  notify_abnormal_expenses: boolean
  notify_overdue_expenses: boolean
  notify_monthly_closing: boolean
  ignore_invoice_payment: boolean
}

const settings = ref<Settings | null>(null)
const saving = ref(false)

async function loadSettings() {
  settings.value = await api.get<Settings>('/settings')
}

async function saveSettings() {
  if (!settings.value) return
  saving.value = true
  try {
    settings.value = await api.put<Settings>('/settings', settings.value)
    toast.add({ title: 'Configurações salvas!', color: 'success' })
  } catch (e: any) {
    toast.add({ title: e.message, color: 'error' })
  } finally {
    saving.value = false
  }
}

onMounted(loadSettings)
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-white mb-6">Configurações</h1>

    <UCard v-if="settings">
      <form class="space-y-6" @submit.prevent="saveSettings">
        <div class="space-y-4">
          <h3 class="text-lg font-medium text-white">Categorização</h3>
          <UCheckbox v-model="settings.auto_categorize" label="Categorização automática (KMeans)" />
        </div>

        <USeparator />

        <div class="space-y-4">
          <h3 class="text-lg font-medium text-white">Notificações por Email</h3>

          <div class="flex items-center gap-4">
            <UCheckbox v-model="settings.notify_due_expenses" label="Despesas vencendo em" />
            <UInput
              v-model.number="settings.due_days_ahead"
              type="number"
              class="w-20"
              :min="1"
              :max="30"
            />
            <span class="text-gray-400">dias</span>
          </div>

          <UCheckbox v-model="settings.notify_overdue_expenses" label="Despesas vencidas" />
          <UCheckbox
            v-model="settings.notify_abnormal_expenses"
            label="Despesas acima do normal (IQR)"
          />
          <UCheckbox v-model="settings.notify_monthly_closing" label="Fechamento mensal" />
        </div>

        <USeparator />

        <div class="space-y-4">
          <h3 class="text-lg font-medium text-white">Visualização</h3>
          <UCheckbox
            v-model="settings.ignore_invoice_payment"
            label="Ignorar pagamento de fatura no Sankey"
          />
        </div>

        <UButton type="submit" :loading="saving" block>
          Salvar configurações
        </UButton>
      </form>
    </UCard>
  </div>
</template>
