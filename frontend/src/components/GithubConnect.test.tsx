import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GithubConnect from './GithubConnect'

function renderConnect() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <GithubConnect />
    </QueryClientProvider>
  )
}

describe('GithubConnect', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('shows a match summary after a successful sync', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ matched_skills: ['python', 'html-css'], evidence_count: 3 }),
    } as Response))

    renderConnect()
    fireEvent.change(screen.getByPlaceholderText('GitHub username'), { target: { value: 'octocat' } })
    fireEvent.click(screen.getByText('Sync'))

    await waitFor(() => expect(screen.getByText(/Matched 2 skill\(s\) from 3 repo entries/)).toBeInTheDocument())
  })
})
