<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const auth = useAuth()
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  loading.value = true
  try {
    await auth.login(email.value, password.value)
    navigateTo('/')
  } catch (e: any) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <div class="mb-8">
      <h2 class="text-2xl font-semibold text-gray-900 dark:text-white/90 tracking-tight">
        Bem-vindo de volta
      </h2>
      <p class="text-gray-400 dark:text-white/40 text-sm mt-1.5">
        Entre na sua conta para continuar
      </p>
    </div>

    <form class="space-y-4" @submit.prevent="handleLogin">
      <UFormField label="Email" class="w-full">
        <UInput
          v-model="email"
          type="email"
          placeholder="seu@email.com"
          required
          size="lg"
          class="w-full"
        />
      </UFormField>

      <UFormField label="Senha" class="w-full">
        <UInput
          v-model="password"
          type="password"
          placeholder="Sua senha"
          required
          size="lg"
          class="w-full"
        />
      </UFormField>

      <UAlert v-if="error" color="error" :title="error" />

      <div class="pt-1">
        <UButton type="submit" block :loading="loading" size="lg">
          Entrar
        </UButton>
      </div>
    </form>

    <p class="text-center text-sm text-gray-400 dark:text-white/30 mt-7">
      Não tem conta?
      <NuxtLink to="/register" class="text-primary-400 hover:text-primary-300 transition-colors">
        Cadastre-se
      </NuxtLink>
    </p>
  </div>
</template>
