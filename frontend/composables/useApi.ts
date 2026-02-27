export function useApi() {
  const config = useRuntimeConfig()
  const auth = useAuth()

  async function apiFetch<T>(
    path: string,
    options: RequestInit = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string> || {}),
    }

    if (auth.token.value) {
      headers['Authorization'] = `Bearer ${auth.token.value}`
    }

    if (!(options.body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
    }

    const response = await fetch(`${config.public.apiBase}${path}`, {
      ...options,
      headers,
    })

    if (response.status === 401) {
      const refreshed = await auth.refresh()
      if (refreshed) {
        headers['Authorization'] = `Bearer ${auth.token.value}`
        const retryResponse = await fetch(`${config.public.apiBase}${path}`, {
          ...options,
          headers,
        })
        if (!retryResponse.ok) throw new Error(`API error: ${retryResponse.status}`)
        if (retryResponse.status === 204) return undefined as T
        return retryResponse.json()
      }
      auth.logout()
      navigateTo('/login')
      throw new Error('Session expired')
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({}))
      throw new Error(error.detail || `API error: ${response.status}`)
    }

    if (response.status === 204) return undefined as T
    return response.json()
  }

  return {
    get: <T>(path: string) => apiFetch<T>(path),
    post: <T>(path: string, body?: unknown) =>
      apiFetch<T>(path, {
        method: 'POST',
        body: body instanceof FormData ? body : JSON.stringify(body),
      }),
    put: <T>(path: string, body?: unknown) =>
      apiFetch<T>(path, {
        method: 'PUT',
        body: JSON.stringify(body),
      }),
    delete: <T>(path: string) =>
      apiFetch<T>(path, { method: 'DELETE' }),
    upload: <T>(path: string, formData: FormData) =>
      apiFetch<T>(path, { method: 'POST', body: formData }),
  }
}
