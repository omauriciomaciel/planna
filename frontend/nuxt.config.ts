export default defineNuxtConfig({
  modules: ['@nuxt/ui', '@pinia/nuxt'],

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: 'http://localhost:8000/api',
    },
  },

  colorMode: {
    preference: 'dark',
  },

  compatibilityDate: '2025-01-01',
})
