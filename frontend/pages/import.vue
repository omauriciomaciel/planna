<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()
const toast = useToast()

interface NamedItem {
  id: string
  name: string
}

interface LookupOption {
  label: string
  value: string
}

interface PdfPurchase {
  purchase_date: string
  due_date: string
  merchant: string
  installment_amount: number
  total_amount: number
  current_installment: number
  total_installments: number
}

const importType = ref<'ofx' | 'csv' | 'pdf'>('ofx')
const file = ref<File | null>(null)
const isDragging = ref(false)
const loading = ref(false)

const selectedAccount = ref<LookupOption | undefined>()
const selectedCard = ref<LookupOption | undefined>()
const selectedPdfCard = ref<LookupOption | undefined>()
const fileType = ref<LookupOption>({ label: 'CSV (Nubank)', value: 'csv' })

const accountOptions = ref<LookupOption[]>([])
const cardOptions = ref<LookupOption[]>([])

const fileTypeOptions: LookupOption[] = [
  { label: 'CSV (Nubank)', value: 'csv' },
  { label: 'OFX (Nubank)', value: 'ofx' },
]

const fileInputRef = ref<HTMLInputElement>()

// PDF preview state
const pdfPreview = ref<PdfPurchase[]>([])
const pdfSource = ref<'text' | 'ocr' | ''>('')
const pdfStep = ref<'upload' | 'preview'>('upload')

async function loadLookups() {
  const [accsResult, cardsResult] = await Promise.allSettled([
    api.get<NamedItem[]>('/accounts'),
    api.get<NamedItem[]>('/credit-cards'),
  ])
  if (accsResult.status === 'fulfilled') {
    accountOptions.value = accsResult.value.map(a => ({ label: a.name, value: String(a.id) }))
  }
  if (cardsResult.status === 'fulfilled') {
    cardOptions.value = cardsResult.value.map(c => ({ label: c.name, value: String(c.id) }))
  }
}

function triggerFileInput() {
  fileInputRef.value?.click()
}

function onFileChange(event: Event) {
  const target = event.target as HTMLInputElement
  file.value = target.files?.[0] || null
}

function onDrop(event: DragEvent) {
  isDragging.value = false
  const dropped = event.dataTransfer?.files?.[0]
  if (dropped) file.value = dropped
}

function resetPdfState() {
  pdfPreview.value = []
  pdfSource.value = ''
  pdfStep.value = 'upload'
}

function switchType(type: 'ofx' | 'csv' | 'pdf') {
  importType.value = type
  file.value = null
  resetPdfState()
}

async function handleImport() {
  if (!file.value) return
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)

    let result: { imported: number }

    if (importType.value === 'ofx') {
      if (selectedAccount.value) {
        formData.append('account_id', selectedAccount.value.value)
      }
      result = await api.upload('/import/ofx/confirm', formData)
    } else {
      if (selectedCard.value) {
        formData.append('credit_card_id', selectedCard.value.value)
      }
      formData.append('file_type', fileType.value.value)
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

async function handlePdfPreview() {
  if (!file.value) return
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)

    const result = await api.upload<{ purchases: PdfPurchase[]; count: number; source: 'text' | 'ocr' }>(
      '/import/pdf',
      formData,
    )

    pdfPreview.value = result.purchases
    pdfSource.value = result.source
    pdfStep.value = 'preview'
  } catch (e: any) {
    toast.add({ title: e.message, color: 'error' })
  } finally {
    loading.value = false
  }
}

async function handlePdfConfirm() {
  if (!file.value) return
  loading.value = true
  try {
    const formData = new FormData()
    formData.append('file', file.value)
    if (selectedPdfCard.value) {
      formData.append('credit_card_id', selectedPdfCard.value.value)
    }

    const result = await api.upload<{ imported: number }>('/import/pdf/confirm', formData)

    toast.add({
      title: `${result.imported} compras importadas com sucesso!`,
      color: 'success',
    })
    file.value = null
    resetPdfState()
  } catch (e: any) {
    toast.add({ title: e.message, color: 'error' })
  } finally {
    loading.value = false
  }
}

const { format: formatCurrency } = useCurrency()

function formatDate(iso: string) {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

function formatInstallments(current: number, total: number) {
  if (total <= 1) return 'À vista'
  return `${current}/${total}`
}

onMounted(loadLookups)
</script>

<template>
  <div>
    <!-- Page header -->
    <div class="mb-8">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-white/90 tracking-tight">Importar</h1>
      <p class="text-sm text-gray-500 mt-1">Importe extratos bancários ou faturas de cartão</p>
    </div>

    <div class="max-w-2xl mx-auto">

      <!-- Import type toggle -->
      <div class="flex rounded-xl overflow-hidden border border-black/8 dark:border-white/8 mb-4 text-sm">
        <button
          type="button"
          :class="importType === 'ofx'
            ? 'bg-black/[0.06] dark:bg-white/[0.06] text-gray-900 dark:text-white/90'
            : 'text-gray-500 hover:text-gray-300'"
          class="flex-1 flex items-center justify-center gap-2 py-3 font-medium transition-colors border-r border-black/8 dark:border-white/8"
          @click="switchType('ofx')"
        >
          <UIcon name="i-heroicons-building-library" class="text-base" />
          Extrato (OFX)
        </button>
        <button
          type="button"
          :class="importType === 'csv'
            ? 'bg-black/[0.06] dark:bg-white/[0.06] text-gray-900 dark:text-white/90'
            : 'text-gray-500 hover:text-gray-300'"
          class="flex-1 flex items-center justify-center gap-2 py-3 font-medium transition-colors border-r border-black/8 dark:border-white/8"
          @click="switchType('csv')"
        >
          <UIcon name="i-heroicons-credit-card" class="text-base" />
          Fatura (CSV/OFX)
        </button>
        <button
          type="button"
          :class="importType === 'pdf'
            ? 'bg-black/[0.06] dark:bg-white/[0.06] text-gray-900 dark:text-white/90'
            : 'text-gray-500 hover:text-gray-300'"
          class="flex-1 flex items-center justify-center gap-2 py-3 font-medium transition-colors"
          @click="switchType('pdf')"
        >
          <UIcon name="i-heroicons-document-text" class="text-base" />
          Fatura (PDF)
        </button>
      </div>

      <!-- OFX / CSV forms (existing) -->
      <form v-if="importType !== 'pdf'" class="space-y-3" @submit.prevent="handleImport">

        <!-- OFX: account select -->
        <div v-if="importType === 'ofx'" class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-4">
          <label class="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1.5">
            Conta bancária <span class="normal-case font-normal text-gray-600">(opcional)</span>
          </label>
          <USelectMenu
            v-model="selectedAccount"
            :items="accountOptions"
            placeholder="Selecionar conta..."
            class="w-full"
          />
        </div>

        <!-- CSV: card + file type -->
        <div v-else class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-4 space-y-3">
          <div>
            <label class="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1.5">
              Cartão de crédito <span class="normal-case font-normal text-gray-600">(opcional)</span>
            </label>
            <USelectMenu
              v-model="selectedCard"
              :items="cardOptions"
              placeholder="Selecionar cartão..."
              class="w-full"
            />
          </div>
          <div>
            <label class="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1.5">Formato do arquivo</label>
            <USelectMenu
              v-model="fileType"
              :items="fileTypeOptions"
              class="w-full"
            />
          </div>
        </div>

        <!-- Drop zone -->
        <div
          class="rounded-xl border-2 border-dashed transition-colors cursor-pointer"
          :class="isDragging
            ? 'border-emerald-500/40 bg-emerald-500/[0.04]'
            : file
              ? 'border-black/10 dark:border-white/10 bg-black/[0.03] dark:bg-white/[0.03]'
              : 'border-black/10 dark:border-white/10 bg-black/[0.015] dark:bg-white/[0.015] hover:border-black/20 dark:hover:border-white/20 hover:bg-black/[0.03] dark:hover:bg-white/[0.03]'"
          @click="triggerFileInput"
          @dragover.prevent="isDragging = true"
          @dragleave="isDragging = false"
          @drop.prevent="onDrop"
        >
          <div v-if="file" class="flex items-center gap-3 px-4 py-4">
            <div
              class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
              style="background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.15)"
            >
              <UIcon name="i-heroicons-document-check" class="text-emerald-600 dark:text-emerald-400 text-sm" />
            </div>
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-gray-700 dark:text-white/80 truncate">{{ file.name }}</p>
              <p class="text-xs text-gray-500 mt-0.5">{{ (file.size / 1024).toFixed(1) }} KB</p>
            </div>
            <UButton
              type="button"
              variant="ghost"
              color="neutral"
              icon="i-heroicons-x-mark"
              size="xs"
              @click.stop="file = null"
            />
          </div>
          <div v-else class="flex flex-col items-center justify-center py-10 px-6 text-center">
            <div class="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-3">
              <UIcon name="i-heroicons-arrow-up-tray" class="text-gray-500 text-lg" />
            </div>
            <p class="text-sm text-gray-500 dark:text-white/60">
              Arraste o arquivo ou <span class="text-gray-700 dark:text-white/80 font-medium">clique para selecionar</span>
            </p>
            <p class="text-xs text-gray-600 mt-1">
              {{ importType === 'ofx' ? '.OFX' : fileType.value === 'csv' ? '.CSV' : '.OFX' }}
            </p>
          </div>
        </div>

        <input
          ref="fileInputRef"
          type="file"
          :accept="importType === 'ofx' ? '.ofx' : fileType.value === 'csv' ? '.csv' : '.ofx'"
          class="hidden"
          @change="onFileChange"
        />

        <UButton
          type="submit"
          :loading="loading"
          :disabled="!file || loading"
          icon="i-heroicons-arrow-up-tray"
          block
        >
          {{ importType === 'ofx' ? 'Importar Extrato' : 'Importar Fatura' }}
        </UButton>

      </form>

      <!-- PDF import flow -->
      <div v-else class="space-y-3">

        <!-- Card select -->
        <div class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-4">
          <label class="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1.5">
            Cartão de crédito <span class="normal-case font-normal text-gray-600">(opcional)</span>
          </label>
          <USelectMenu
            v-model="selectedPdfCard"
            :items="cardOptions"
            placeholder="Selecionar cartão..."
            class="w-full"
          />
        </div>

        <!-- Step 1: Upload -->
        <template v-if="pdfStep === 'upload'">
          <!-- Drop zone -->
          <div
            class="rounded-xl border-2 border-dashed transition-colors cursor-pointer"
            :class="isDragging
              ? 'border-emerald-500/40 bg-emerald-500/[0.04]'
              : file
                ? 'border-black/10 dark:border-white/10 bg-black/[0.03] dark:bg-white/[0.03]'
                : 'border-black/10 dark:border-white/10 bg-black/[0.015] dark:bg-white/[0.015] hover:border-black/20 dark:hover:border-white/20 hover:bg-black/[0.03] dark:hover:bg-white/[0.03]'"
            @click="triggerFileInput"
            @dragover.prevent="isDragging = true"
            @dragleave="isDragging = false"
            @drop.prevent="onDrop"
          >
            <div v-if="file" class="flex items-center gap-3 px-4 py-4">
              <div
                class="w-8 h-8 rounded-lg flex items-center justify-center shrink-0"
                style="background: rgba(52,211,153,0.1); border: 1px solid rgba(52,211,153,0.15)"
              >
                <UIcon name="i-heroicons-document-check" class="text-emerald-600 dark:text-emerald-400 text-sm" />
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-medium text-gray-700 dark:text-white/80 truncate">{{ file.name }}</p>
                <p class="text-xs text-gray-500 mt-0.5">{{ (file.size / 1024).toFixed(1) }} KB</p>
              </div>
              <UButton
                type="button"
                variant="ghost"
                color="neutral"
                icon="i-heroicons-x-mark"
                size="xs"
                @click.stop="file = null"
              />
            </div>
            <div v-else class="flex flex-col items-center justify-center py-10 px-6 text-center">
              <div class="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-3">
                <UIcon name="i-heroicons-arrow-up-tray" class="text-gray-500 text-lg" />
              </div>
              <p class="text-sm text-gray-500 dark:text-white/60">
                Arraste o arquivo ou <span class="text-gray-700 dark:text-white/80 font-medium">clique para selecionar</span>
              </p>
              <p class="text-xs text-gray-600 mt-1">.PDF</p>
            </div>
          </div>

          <input
            ref="fileInputRef"
            type="file"
            accept=".pdf"
            class="hidden"
            @change="onFileChange"
          />

          <UButton
            :loading="loading"
            :disabled="!file || loading"
            icon="i-heroicons-magnifying-glass"
            block
            @click="handlePdfPreview"
          >
            {{ loading ? 'Processando PDF...' : 'Analisar PDF' }}
          </UButton>
        </template>

        <!-- Step 2: Preview & Confirm -->
        <template v-if="pdfStep === 'preview'">
          <!-- Source badge -->
          <div class="flex items-center gap-2 text-xs text-gray-500">
            <UBadge :color="pdfSource === 'ocr' ? 'warning' : 'success'" variant="subtle" size="xs">
              {{ pdfSource === 'ocr' ? 'OCR (GPT-4o)' : 'Texto extraído' }}
            </UBadge>
            <span>{{ pdfPreview.length }} compras encontradas</span>
          </div>

          <!-- Preview table -->
          <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">
            <div class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-black/8 dark:border-white/8 bg-black/[0.02] dark:bg-white/[0.02]">
                    <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Data</th>
                    <th class="text-left px-3 py-2 text-xs font-medium text-gray-500 uppercase">Estabelecimento</th>
                    <th class="text-center px-3 py-2 text-xs font-medium text-gray-500 uppercase">Parcelas</th>
                    <th class="text-right px-3 py-2 text-xs font-medium text-gray-500 uppercase">Valor</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="(item, idx) in pdfPreview"
                    :key="idx"
                    class="border-b border-black/5 dark:border-white/5 last:border-0"
                  >
                    <td class="px-3 py-2 text-gray-600 dark:text-white/70 whitespace-nowrap">{{ formatDate(item.purchase_date) }}</td>
                    <td class="px-3 py-2 text-gray-800 dark:text-white/90">{{ item.merchant }}</td>
                    <td class="px-3 py-2 text-center text-gray-600 dark:text-white/70">{{ formatInstallments(item.current_installment, item.total_installments) }}</td>
                    <td class="px-3 py-2 text-right font-medium text-gray-800 dark:text-white/90 whitespace-nowrap">{{ formatCurrency(item.installment_amount) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <!-- Action buttons -->
          <div class="flex gap-2">
            <UButton
              variant="outline"
              color="neutral"
              class="flex-1"
              @click="() => { pdfStep = 'upload'; }"
            >
              Voltar
            </UButton>
            <UButton
              :loading="loading"
              :disabled="loading"
              icon="i-heroicons-check"
              class="flex-1"
              @click="handlePdfConfirm"
            >
              Confirmar Importação
            </UButton>
          </div>
        </template>
      </div>

    </div>
  </div>
</template>
