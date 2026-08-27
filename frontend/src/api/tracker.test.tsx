import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useRecalculateJourney, useRecordProgress } from './tracker'

function makeWrapper() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  )
  return { queryClient, wrapper }
}

describe('useRecordProgress', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('invalidates the journeys query on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({}),
    } as Response))

    const { queryClient, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useRecordProgress(), { wrapper })
    result.current.mutate({ stepId: 1, update: { confidence_rating: 3 } })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['journeys'] })
  })
})

describe('useRecalculateJourney', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('invalidates both the journeys and competency-history queries on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({}),
    } as Response))

    const { queryClient, wrapper } = makeWrapper()
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries')

    const { result } = renderHook(() => useRecalculateJourney(), { wrapper })
    result.current.mutate(1)

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['journeys'] })
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['competency-history'] })
  })
})
