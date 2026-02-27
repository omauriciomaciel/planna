export default defineNuxtRouteMiddleware((to) => {
  const auth = useAuth()

  if (!auth.isAuthenticated.value && to.path !== '/login' && to.path !== '/register') {
    return navigateTo('/login')
  }
})
