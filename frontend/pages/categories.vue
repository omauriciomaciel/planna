<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const api = useApi()

interface Category {
  id: string
  name: string
  emoji: string | null
  sort_order: number
}

const categories = ref<Category[]>([])
const loading = ref(true)
const newName = ref('')
const newEmoji = ref('')
const saving = ref(false)

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
    })
    newName.value = ''
    newEmoji.value = ''
    await loadCategories()
  } finally {
    saving.value = false
  }
}

async function deleteCategory(id: string) {
  await api.delete(`/categories/${id}`)
  await loadCategories()
}

onMounted(loadCategories)
</script>

<template>
  <div>
    <div class="mb-8">
      <h1 class="text-xl font-semibold text-white/90 tracking-tight">Categorias</h1>
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
      <div class="rounded-xl border border-white/8 bg-white/[0.03] p-4 mb-3">
        <label class="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-1.5">Nova categoria</label>
        <form class="flex gap-2" @submit.prevent="addCategory">
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
          <UButton
            type="submit"
            icon="i-heroicons-plus"
            :loading="saving"
            :disabled="!newName.trim() || saving"
            class="shrink-0"
          />
        </form>
      </div>

      <!-- List -->
      <div class="rounded-xl border border-white/8 overflow-hidden">

        <!-- Loading skeleton -->
        <div v-if="loading" class="divide-y divide-white/5">
          <div v-for="i in 4" :key="i" class="flex items-center gap-3 px-4 py-3">
            <div class="w-8 h-8 rounded-lg bg-white/5 animate-pulse shrink-0" />
            <div class="h-3 w-32 bg-white/5 rounded animate-pulse flex-1" />
          </div>
        </div>

        <!-- Empty state -->
        <template v-else-if="categories.length === 0">
          <div class="flex flex-col items-center justify-center py-10 px-6 text-center">
            <div class="w-10 h-10 rounded-full bg-white/5 flex items-center justify-center mb-3">
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
            class="group flex items-center gap-3 px-4 py-3 border-b border-white/5 last:border-0 hover:bg-white/[0.02] transition-colors"
          >
            <div class="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center shrink-0 text-base leading-none">
              {{ cat.emoji || '🏷️' }}
            </div>
            <span class="flex-1 text-sm font-medium text-white/80">{{ cat.name }}</span>
            <UButton
              variant="ghost"
              color="error"
              icon="i-heroicons-trash"
              size="xs"
              class="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
              @click="deleteCategory(cat.id)"
            />
          </div>
        </template>

      </div>
    </div>
  </div>
</template>
