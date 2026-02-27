<script setup lang="ts">
definePageMeta({ layout: 'auth' })

const auth = useAuth()
const name = ref('')
const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)

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
    <!-- Header -->
    <div class="mb-8">
      <h2 class="text-2xl font-semibold text-gray-900 dark:text-white/90 tracking-tight">
        Criar conta
      </h2>
      <p class="text-sm text-gray-500 dark:text-white/40 mt-1.5">
        Comece a organizar suas finanças
      </p>
    </div>

    <!-- Form panel -->
    <div class="rounded-xl border border-black/8 dark:border-white/8 bg-black/[0.02] dark:bg-white/[0.02] p-5">
      <form class="flex flex-col gap-4" @submit.prevent="handleRegister">
        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Nome
          </label>
          <UInput
            v-model="name"
            placeholder="Seu nome"
            required
            size="lg"
            icon="i-heroicons-user"
            class="w-full"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Email
          </label>
          <UInput
            v-model="email"
            type="email"
            placeholder="seu@email.com"
            required
            size="lg"
            icon="i-heroicons-envelope"
            class="w-full"
          />
        </div>

        <div class="flex flex-col gap-1.5">
          <label class="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
            Senha
          </label>
          <UInput
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            placeholder="Crie uma senha"
            required
            size="lg"
            icon="i-heroicons-lock-closed"
            class="w-full"
            :ui="{ trailing: 'pr-10' }"
          >
            <template #trailing>
              <button
                type="button"
                class="text-gray-400 hover:text-gray-600 dark:hover:text-white/60 transition-colors"
                tabindex="-1"
                @click="showPassword = !showPassword"
              >
                <UIcon
                  :name="showPassword ? 'i-heroicons-eye-slash' : 'i-heroicons-eye'"
                  class="text-base"
                />
              </button>
            </template>
          </UInput>
        </div>

        <UAlert v-if="error" color="error" :title="error" class="mt-1" />

        <div class="pt-1">
          <UButton
            type="submit"
            block
            :loading="loading"
            size="lg"
          >
            Criar conta
          </UButton>
        </div>
      </form>
    </div>

    <!-- Login link -->
    <p class="text-center text-sm text-gray-500 dark:text-white/30 mt-7">
      Já tem conta?
      <NuxtLink
        to="/login"
        class="text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 font-medium transition-colors"
      >
        Entrar
      </NuxtLink>
    </p>
  </div>
</template>
