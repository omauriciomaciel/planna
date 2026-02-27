export default defineNuxtRouteMiddleware((to) => {
  if (import.meta.server) return

  const auth = useAuth()

  if (!auth.isAuthenticated.value && to.path !== '/login' && to.path !== '/register') {
    return navigateTo('/login')
  }
})
