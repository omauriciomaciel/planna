<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()

interface Category {
  id: string
  name: string
  emoji: string | null
  sort_order: number
  category_type: string | null
  classification: string | null
}

interface LookupOption {
  label: string
  value: string
}

const categories = ref<Category[]>([])
const loading = ref(true)
const newName = ref('')
const newEmoji = ref('')
const newCategoryType = ref<LookupOption | undefined>()
const newClassification = ref<LookupOption | undefined>()
const saving = ref(false)

const categoryTypeOptions: LookupOption[] = [
  { label: 'Entrada', value: 'income' },
  { label: 'Saída', value: 'expense' },
]

const classificationOptions: LookupOption[] = [
  { label: 'Essencial', value: 'essential' },
  { label: 'Não essencial', value: 'non_essential' },
]

function categoryTypeLabel(value: string | null) {
  if (value === 'income') return 'Entrada'
  if (value === 'expense') return 'Saída'
  return null
}

function classificationLabel(value: string | null) {
  if (value === 'essential') return 'Essencial'
  if (value === 'non_essential') return 'Não essencial'
  return null
}

async function loadCategories() {
  loading.value = true
  try {
    categories.value = await api.get<Category[]>('/categories')
  } finally {
    loading.value = false
  }
}

async function addCategory() {
  if (!newName.value.trim()) return
  saving.value = true
  try {
    await api.post('/categories', {
      name: newName.value.trim(),
      emoji: newEmoji.value.trim() || null,
      category_type: newCategoryType.value?.value ?? null,
      classification: newClassification.value?.value ?? null,
    })
    newName.value = ''
    newEmoji.value = ''
    newCategoryType.value = undefined
    newClassification.value = undefined
    await loadCategories()
  } finally {
    saving.value = false
  }
}

async function deleteCategory(id: string) {
  await api.delete(`/categories/${id}`)
  await loadCategories()
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

onMounted(loadCategories)
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-xl font-semibold text-gray-900 dark:text-white/90 tracking-tight">Categorias</h1>
      <p class="text-sm text-gray-500 mt-1">Organize suas transações por categoria</p>
    </div>

    <div class="max-w-2xl mx-auto">

      <!-- Section header -->
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-semibold text-gray-400 uppercase tracking-widest">Suas categorias</h2>
        <span class="text-xs text-gray-600 tabular-nums">
          {{ categories.length }} categoria{{ categories.length !== 1 ? 's' : '' }}
        </span>
      </div>

      <!-- Add form -->
      <div class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.03] dark:bg-white/[0.03] p-4 mb-3">
        <label class="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1.5">Nova categoria</label>
        <form class="space-y-2" @submit.prevent="addCategory">
          <div class="flex gap-2">
            <UInput
              v-model="newEmoji"
              placeholder="🏠"
              class="w-14 shrink-0"
            />
            <UInput
              v-model="newName"
              placeholder="Ex: Moradia, Alimentação..."
              class="flex-1 min-w-0"
            />
          </div>
          <div class="flex gap-2">
            <USelectMenu
              v-model="newCategoryType"
              :items="categoryTypeOptions"
              placeholder="Tipo..."
              class="flex-1"
            />
            <USelectMenu
              v-model="newClassification"
              :items="classificationOptions"
              placeholder="Classificação..."
              class="flex-1"
            />
            <UButton
              type="submit"
              icon="i-heroicons-plus"
              :loading="saving"
              :disabled="!newName.trim() || saving"
              class="shrink-0"
            />
          </div>
        </form>
      </div>

      <!-- List -->
      <div class="rounded-xl border border-black/8 dark:border-white/8 overflow-hidden">

        <!-- Loading skeleton -->
        <div v-if="loading" class="divide-y divide-black/5 dark:divide-white/5">
          <div v-for="i in 4" :key="i" class="flex items-center gap-3 px-4 py-3">
            <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 animate-pulse shrink-0" />
            <div class="h-3 w-32 bg-black/5 dark:bg-white/5 rounded animate-pulse flex-1" />
            <div class="h-4 w-14 bg-black/5 dark:bg-white/5 rounded-full animate-pulse" />
          </div>
        </div>

        <!-- Empty state -->
        <template v-else-if="categories.length === 0">
          <div class="flex flex-col items-center justify-center py-10 px-6 text-center">
            <div class="w-10 h-10 rounded-full bg-black/5 dark:bg-white/5 flex items-center justify-center mb-3">
              <UIcon name="i-heroicons-tag" class="text-gray-600 text-lg" />
            </div>
            <p class="text-sm text-gray-500">Nenhuma categoria cadastrada</p>
            <p class="text-xs text-gray-600 mt-1">Preencha o formulário acima para começar</p>
          </div>
        </template>

        <!-- Items -->
        <template v-else>
          <div
            v-for="cat in categories"
            :key="cat.id"
            class="group flex items-center gap-3 px-4 py-3 border-b border-black/5 dark:border-white/5 last:border-0 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors"
          >
            <div class="w-8 h-8 rounded-lg bg-black/5 dark:bg-white/5 flex items-center justify-center shrink-0 text-base leading-none">
              {{ cat.emoji || '🏷️' }}
            </div>
            <span class="flex-1 text-sm font-medium text-gray-700 dark:text-white/80">{{ cat.name }}</span>

            <!-- Badges -->
            <div class="flex items-center gap-1.5 shrink-0">
              <span
                v-if="categoryTypeLabel(cat.category_type)"
                class="text-xs px-1.5 py-0.5 rounded-full font-medium"
                :class="cat.category_type === 'income'
                  ? 'bg-emerald-50 dark:bg-emerald-500/10 text-emerald-600 dark:text-emerald-400'
                  : 'bg-red-50 dark:bg-red-500/10 text-red-600 dark:text-red-400'"
              >
                {{ categoryTypeLabel(cat.category_type) }}
              </span>
              <span
                v-if="classificationLabel(cat.classification)"
                class="text-xs px-1.5 py-0.5 rounded-full bg-black/5 dark:bg-white/5 text-gray-400 font-medium"
              >
                {{ classificationLabel(cat.classification) }}
              </span>
            </div>

            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              @click="requestDelete(cat.name, () => deleteCategory(cat.id))"
            />
          </div>
        </template>

      </div>
    </div>

    <UModal
      v-model:open="confirmDeleteOpen"
      title="Excluir categoria?"
      :description="`&quot;${deleteTargetLabel}&quot; será removida permanentemente.`"
    >
      <template #actions>
        <UButton variant="ghost" color="neutral" @click="confirmDeleteOpen = false">Cancelar</UButton>
        <UButton color="error" :loading="deleting" @click="confirmDelete">Excluir</UButton>
      </template>
    </UModal>
  </div>
</template>
