<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const auth = useAuth()
const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleRegister() {
  error.value = ''
  loading.value = true
  try {
    await auth.register(email.value, name.value, password.value)
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
        Criar conta
      </h2>
      <p class="text-gray-400 dark:text-white/40 text-sm mt-1.5">
        Comece a organizar suas finanças
      </p>
    </div>

    <form class="space-y-4" @submit.prevent="handleRegister">
      <UFormField label="Nome" class="w-full">
        <UInput
          v-model="name"
          placeholder="Seu nome"
          required
          size="lg"
          class="w-full"
        />
      </UFormField>

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
          placeholder="Crie uma senha"
          required
          size="lg"
          class="w-full"
        />
      </UFormField>

      <UAlert v-if="error" color="error" :title="error" />

      <div class="pt-1">
        <UButton type="submit" block :loading="loading" size="lg">
          Criar conta
        </UButton>
      </div>
    </form>

    <p class="text-center text-sm text-gray-400 dark:text-white/30 mt-7">
      Já tem conta?
      <NuxtLink to="/login" class="text-primary-400 hover:text-primary-300 transition-colors">
        Entrar
      </NuxtLink>
    </p>
  </div>
</template>
