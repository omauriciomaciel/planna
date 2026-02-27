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
  await api.post('/categories', {
    name: newName.value.trim(),
    emoji: newEmoji.value.trim() || null,
  })
  newName.value = ''
  newEmoji.value = ''
  await loadCategories()
}

async function deleteCategory(id: string) {
  await api.delete(`/categories/${id}`)
  await loadCategories()
}

onMounted(loadCategories)
</script>

<template>
  <div>
    <h1 class="text-2xl font-bold text-white mb-6">Categorias</h1>

    <UCard class="mb-6">
      <form class="flex gap-3" @submit.prevent="addCategory">
        <UInput v-model="newEmoji" placeholder="Emoji" class="w-20" />
        <UInput v-model="newName" placeholder="Nome da categoria" class="flex-1" />
        <UButton type="submit" icon="i-heroicons-plus">Adicionar</UButton>
      </form>
    </UCard>

    <UCard>
      <div class="divide-y divide-gray-800">
        <div
          v-for="cat in categories"
          :key="cat.id"
          class="flex items-center justify-between py-3"
        >
          <span class="text-white">
            <span v-if="cat.emoji" class="mr-2">{{ cat.emoji }}</span>
            {{ cat.name }}
          </span>
          <UButton
            variant="ghost"
            color="error"
            icon="i-heroicons-trash"
            size="xs"
            @click="deleteCategory(cat.id)"
          />
        </div>
        <div v-if="!categories.length && !loading" class="py-6 text-center text-gray-500">
          Nenhuma categoria cadastrada
        </div>
      </div>
    </UCard>
  </div>
</template>
