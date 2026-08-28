import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

  it('reuses an already-analyzed repo instead of re-downloading it', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ([{ username: 'octocat', repo_name: 'Hello-World', file_count: 5, analyzed_at: '2026-08-20T10:00:00Z' }]),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)

    renderPage()
    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument())

    fireEvent.change(screen.getByPlaceholderText('GitHub Username (e.g. torvalds)'), { target: { value: 'octocat' } })
    fireEvent.change(screen.getByPlaceholderText('Repository Name (e.g. linux)'), { target: { value: 'Hello-World' } })
    fireEvent.click(screen.getByText('Analyze'))

    // "Already analyzed" also appears as the static history-list label, so match
    // the status message's own wording (the "(" only appears there).
    await waitFor(() => expect(screen.getByText(/Already analyzed \(/)).toBeInTheDocument())

    // The only network call made is the initial GET /api/github/repos list —
    // clicking Analyze on a known repo must never hit the analyze endpoint.
    expect(fetchMock).not.toHaveBeenCalledWith(expect.stringContaining('/analyze'), expect.anything())
    expect(screen.getByText('Ask a question about the code!')).toBeInTheDocument()
  })
})
