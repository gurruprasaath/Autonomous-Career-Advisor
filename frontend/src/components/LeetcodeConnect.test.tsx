import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import LeetcodeConnect from './LeetcodeConnect'
import type { LeetcodeSummary } from '../api/types'

const SUMMARY: LeetcodeSummary = {
  username: 'alice', easy: 50, medium: 30, hard: 0, total: 80,
  dsa_depth: 6, weak_topics: ['Dynamic Programming', 'Greedy'],
  last_accepted_at: '2026-09-01T00:00:00+00:00', synced_at: '2026-09-27T10:00:00+00:00',
}

function ok(body: unknown) {
  return { ok: true, status: 200, json: async () => body } as Response
}

function fail(status: number, detail: string) {
  return { ok: false, status, statusText: 'Error', json: async () => ({ detail }) } as Response
}

function mockApi({ current, sync }: { current: LeetcodeSummary | null; sync?: Response }) {
  vi.stubGlobal('fetch', vi.fn(async (url: string) => {
    if (url === '/api/leetcode/sync') return sync ?? ok(SUMMARY)
    return ok(current)
  }))
}

function renderConnect() {
  render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <LeetcodeConnect />
    </QueryClientProvider>
  )
}

describe('LeetcodeConnect', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('shows only the connect form when never synced', async () => {
    mockApi({ current: null })
    renderConnect()
    expect(await screen.findByPlaceholderText('LeetCode username')).toBeInTheDocument()
    expect(screen.queryByText(/DSA depth/)).not.toBeInTheDocument()
  })

  it('shows counts, depth and weak topics after a successful sync', async () => {
    mockApi({ current: null })
    renderConnect()
    fireEvent.change(screen.getByPlaceholderText('LeetCode username'), { target: { value: 'alice' } })
    fireEvent.click(screen.getByText('Sync'))

    await waitFor(() => expect(screen.getByText('DSA depth 6/10')).toBeInTheDocument())
    expect(screen.getByText('Easy 50 · Medium 30 · Hard 0')).toBeInTheDocument()
    expect(screen.getByText('Dynamic Programming')).toBeInTheDocument()
    expect(screen.getByText('Greedy')).toBeInTheDocument()
  })

  it('shows an existing synced profile on load', async () => {
    mockApi({ current: { ...SUMMARY, dsa_depth: null, weak_topics: [] } })
    renderConnect()
    expect(await screen.findByText('No solved problems yet')).toBeInTheDocument()
  })

  it('shows the API error message when sync fails', async () => {
    mockApi({ current: null, sync: fail(404, "LeetCode user 'ghost' not found") })
    renderConnect()
    fireEvent.change(screen.getByPlaceholderText('LeetCode username'), { target: { value: 'ghost' } })
    fireEvent.click(screen.getByText('Sync'))

    expect(await screen.findByText("LeetCode user 'ghost' not found")).toBeInTheDocument()
  })
})
