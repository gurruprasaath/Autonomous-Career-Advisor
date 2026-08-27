import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RepoAnalysisPage from './RepoAnalysisPage'

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <RepoAnalysisPage />
    </QueryClientProvider>
  )
}

describe('RepoAnalysisPage', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('lists previously analyzed repos so re-analysis is not silent', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ([{ username: 'octocat', repo_name: 'Hello-World', file_count: 5, analyzed_at: '2026-08-20T10:00:00Z' }]),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument())
  })
})
