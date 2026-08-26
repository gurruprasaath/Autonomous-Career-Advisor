import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useLogin, useRegister } from './auth'
import { getToken, setToken } from './client'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useLogin', () => {
  beforeEach(() => {
    setToken(null)
    vi.unstubAllGlobals()
  })

  it('stores the returned access token on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'tok123', token_type: 'bearer' }),
    } as Response))

    const { result } = renderHook(() => useLogin(), { wrapper })
    result.current.mutate({ email: 'a@b.com', password: 'pw' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(getToken()).toBe('tok123')
  })

  it('surfaces the server error message on failure and does not store a token', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Incorrect email or password' }),
    } as Response))

    const { result } = renderHook(() => useLogin(), { wrapper })
    result.current.mutate({ email: 'a@b.com', password: 'wrong' })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toBe('Incorrect email or password')
    expect(getToken()).toBeNull()
  })
})

describe('useRegister', () => {
  beforeEach(() => {
    setToken(null)
    vi.unstubAllGlobals()
  })

  it('stores the returned access token on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'tok456', token_type: 'bearer' }),
    } as Response))

    const { result } = renderHook(() => useRegister(), { wrapper })
    result.current.mutate({ email: 'new@b.com', password: 'pw' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(getToken()).toBe('tok456')
  })
})
