const BASE = ""

let token: string | null = null

try {
  token = localStorage.getItem("access_token")
} catch {
  // localStorage not available in test environment
}

export function setToken(newToken: string | null) {
  token = newToken
  try {
    if (token) localStorage.setItem("access_token", token)
    else localStorage.removeItem("access_token")
  } catch {
    // localStorage not available
  }
}

export function getToken(): string | null {
  return token
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  })
  if (res.status === 401) {
    setToken(null)
    window.location.reload()
    return undefined as unknown as T // reload is already in flight; caller never sees this
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: formData })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return res.json()
}
