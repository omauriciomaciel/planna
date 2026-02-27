<script setup lang="ts">
const auth = useAuth()

const navigation = [
  { label: 'Dashboard', icon: 'i-heroicons-chart-bar', to: '/' },
  { label: 'Lançamentos', icon: 'i-heroicons-banknotes', to: '/transactions' },
  { label: 'Crédito', icon: 'i-heroicons-credit-card', to: '/credit' },
  { label: 'Importar', icon: 'i-heroicons-arrow-up-tray', to: '/import' },
  { label: 'Categorias', icon: 'i-heroicons-tag', to: '/categories' },
  { label: 'Contas', icon: 'i-heroicons-building-library', to: '/accounts' },
  { label: 'Configurações', icon: 'i-heroicons-cog-6-tooth', to: '/settings' },
]
</script>

<template>
  <div class="min-h-screen bg-gray-950">
    <nav class="border-b border-gray-800 bg-gray-900">
      <div class="mx-auto max-w-7xl px-4">
        <div class="flex h-16 items-center justify-between">
          <div class="flex items-center gap-8">
            <NuxtLink to="/" class="text-xl font-bold text-white">
              Planna
            </NuxtLink>
            <div class="hidden md:flex gap-1">
              <NuxtLink
                v-for="item in navigation"
                :key="item.to"
                :to="item.to"
                class="px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800 transition-colors"
                active-class="!text-white !bg-gray-800"
              >
                {{ item.label }}
              </NuxtLink>
            </div>
          </div>
          <div class="flex items-center gap-4">
            <span class="text-sm text-gray-400">{{ auth.user.value?.name }}</span>
            <UButton
              variant="ghost"
              color="neutral"
              icon="i-heroicons-arrow-right-on-rectangle"
              @click="auth.logout()"
            />
          </div>
        </div>
      </div>
    </nav>

    <main class="mx-auto max-w-7xl px-4 py-6">
      <slot />
    </main>
  </div>
</template>
