interface User {
  id: string
  email: string
  name: string
}

interface TokenResponse {
  access_token: string
  refresh_token: string
}

export function useAuth() {
  const token = useState<string | null>('auth_token', () => null)
  const refreshToken = useState<string | null>('auth_refresh', () => null)
  const user = useState<User | null>('auth_user', () => null)

  if (import.meta.client) {
    token.value = token.value || localStorage.getItem('token')
    refreshToken.value = refreshToken.value || localStorage.getItem('refresh_token')
  }

  const config = useRuntimeConfig()

  const isAuthenticated = computed(() => !!token.value)

  async function login(email: string, password: string) {
    const response = await fetch(`${config.public.apiBase}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Login failed')
    }

    const data: TokenResponse = await response.json()
    setTokens(data)
    await fetchUser()
  }

  async function register(email: string, name: string, password: string) {
    const response = await fetch(`${config.public.apiBase}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, name, password }),
    })

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || 'Registration failed')
    }

    await login(email, password)
  }

  async function refresh(): Promise<boolean> {
    if (!refreshToken.value) return false

    try {
      const response = await fetch(`${config.public.apiBase}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken.value }),
      })

      if (!response.ok) return false

      const data: TokenResponse = await response.json()
      setTokens(data)
      return true
    } catch {
      return false
    }
  }

  async function fetchUser() {
    if (!token.value) return

    const response = await fetch(`${config.public.apiBase}/auth/me`, {
      headers: { Authorization: `Bearer ${token.value}` },
    })

    if (response.ok) {
      user.value = await response.json()
    }
  }

  function setTokens(data: TokenResponse) {
    token.value = data.access_token
    refreshToken.value = data.refresh_token
    if (import.meta.client) {
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('refresh_token', data.refresh_token)
    }
  }

  function logout() {
    token.value = null
    refreshToken.value = null
    user.value = null
    if (import.meta.client) {
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
    }
    navigateTo('/login')
  }

  return { token, refreshToken, user, isAuthenticated, login, register, refresh, fetchUser, logout }
}
