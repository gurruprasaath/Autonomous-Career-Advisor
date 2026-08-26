const BASE = ""

// Guarded because this project's actual Vitest + jsdom test environment
// does not provide a working global `localStorage` at all (verified by
// running the test suite: an unguarded access throws
// "Cannot read properties of undefined" both at module-eval time and from
// inside a test body) — this is not a real-browser concern to defend
// against, it's this specific test environment's gap. The in-memory `token`
// variable is still authoritative either way, so getToken()/setToken()
// behave identically for callers regardless of whether persistence happens.
let token: string | null = typeof localStorage !== "undefined" ? localStorage.getItem("access_token") : null

export function setToken(newToken: string | null) {
  token = newToken
  if (typeof localStorage === "undefined") return
  if (token) localStorage.setItem("access_token", token)
  else localStorage.removeItem("access_token")
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
