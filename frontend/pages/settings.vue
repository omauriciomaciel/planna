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
    <div class="mb-8">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-white/90 tracking-tight">Configurações</h1>
      <p class="text-sm text-gray-500 mt-1">Preferências de comportamento e notificações</p>
    </div>

    <!-- Loading skeleton -->
    <div v-if="!settings" class="max-w-2xl mx-auto space-y-6">
      <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">
        <div v-for="i in 3" :key="i" class="flex items-center justify-between px-4 py-4 border-b border-black/5 dark:border-white/5 last:border-0">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 animate-pulse shrink-0" />
            <div class="space-y-1.5">
              <div class="h-3 w-40 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
              <div class="h-2.5 w-56 bg-black/5 dark:bg-white/5 rounded animate-pulse" />
            </div>
          </div>
          <div class="w-10 h-5 bg-black/5 dark:bg-white/5 rounded-full animate-pulse shrink-0" />
        </div>
      </div>
    </div>

    <form v-else class="max-w-2xl mx-auto space-y-6" @submit.prevent="saveSettings">

      <!-- Categorização -->
      <div>
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Categorização</h2>
        <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">
          <div class="flex items-center justify-between px-4 py-4">
            <div class="flex items-center gap-3">
              <div
                class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style="background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.15)"
              >
                <UIcon name="i-heroicons-sparkles" class="text-emerald-600 dark:text-emerald-400 text-sm" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-700 dark:text-white/80">Categorização automática</p>
                <p class="text-xs text-gray-500 mt-0.5">Sugere categorias via KMeans baseado no seu histórico de gastos</p>
              </div>
            </div>
            <USwitch v-model="settings.auto_categorize" />
          </div>
        </div>
      </div>

      <!-- Notificações por Email -->
      <div>
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Notificações por Email</h2>
        <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">

          <!-- Despesas a vencer -->
          <div class="flex items-center justify-between px-4 py-4 border-b border-black/5 dark:border-white/5">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
                <UIcon name="i-heroicons-clock" class="text-gray-400 text-sm" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-700 dark:text-white/80">Despesas a vencer</p>
                <p class="text-xs text-gray-500 mt-0.5">Avisa com antecedência antes do vencimento</p>
              </div>
            </div>
            <div class="flex items-center gap-3 shrink-0">
              <div class="flex items-center gap-1.5">
                <UInput
                  v-model.number="settings.due_days_ahead"
                  type="number"
                  :min="1"
                  :max="30"
                  class="w-14"
                />
                <span class="text-xs text-gray-600">dias</span>
              </div>
              <USwitch v-model="settings.notify_due_expenses" />
            </div>
          </div>

          <!-- Despesas vencidas -->
          <div class="flex items-center justify-between px-4 py-4 border-b border-black/5 dark:border-white/5">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
                <UIcon name="i-heroicons-exclamation-circle" class="text-gray-400 text-sm" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-700 dark:text-white/80">Despesas vencidas</p>
                <p class="text-xs text-gray-500 mt-0.5">Lembrete de lançamentos que passaram da data de vencimento</p>
              </div>
            </div>
            <USwitch v-model="settings.notify_overdue_expenses" />
          </div>

          <!-- Despesas acima do normal -->
          <div class="flex items-center justify-between px-4 py-4 border-b border-black/5 dark:border-white/5">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
                <UIcon name="i-heroicons-arrow-trending-up" class="text-gray-400 text-sm" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-700 dark:text-white/80">Despesas acima do normal</p>
                <p class="text-xs text-gray-500 mt-0.5">Detecta gastos fora do padrão pelo método IQR</p>
              </div>
            </div>
            <USwitch v-model="settings.notify_abnormal_expenses" />
          </div>

          <!-- Fechamento mensal -->
          <div class="flex items-center justify-between px-4 py-4">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
                <UIcon name="i-heroicons-calendar-days" class="text-gray-400 text-sm" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-700 dark:text-white/80">Fechamento mensal</p>
                <p class="text-xs text-gray-500 mt-0.5">Resumo automático de receitas e despesas ao fim de cada mês</p>
              </div>
            </div>
            <USwitch v-model="settings.notify_monthly_closing" />
          </div>

        </div>
      </div>

      <!-- Visualização -->
      <div>
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">Visualização</h2>
        <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">
          <div class="flex items-center justify-between px-4 py-4">
            <div class="flex items-center gap-3">
              <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0">
                <UIcon name="i-heroicons-eye-slash" class="text-gray-400 text-sm" />
              </div>
              <div>
                <p class="text-sm font-medium text-gray-700 dark:text-white/80">Ignorar pagamento de fatura</p>
                <p class="text-xs text-gray-500 mt-0.5">Oculta transferências de fatura no gráfico Sankey</p>
              </div>
            </div>
            <USwitch v-model="settings.ignore_invoice_payment" />
          </div>
        </div>
      </div>

      <!-- Save -->
      <UButton type="submit" :loading="saving" block>
        Salvar configurações
      </UButton>

    </form>
  </div>
</template>
