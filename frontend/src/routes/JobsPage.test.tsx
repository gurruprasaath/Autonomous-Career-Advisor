import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import JobsPage from './JobsPage'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <JobsPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('JobsPage', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('shows an empty state pointing to Generate Path when no journey exists yet', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 404, statusText: 'Not Found',
      json: async () => ({ detail: 'Generate a learning path first to get job recommendations.' }),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText('Generate a learning path first to get job recommendations.')).toBeInTheDocument())
    expect(screen.getByText('Generate Path →')).toBeInTheDocument()
  })

  it('renders ranked job matches with matched skills and an apply link', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ([
        { posting_id: 'job-a', title: 'Backend Engineer', company: 'Acme', location: 'Remote',
          url: 'https://example.com/job-a', score: 0.82, matched_skills: ['Python', 'Docker'] },
      ]),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText(/Backend Engineer — Acme/)).toBeInTheDocument())
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Docker')).toBeInTheDocument()
    expect(screen.getByText('🔗 Apply')).toHaveAttribute('href', 'https://example.com/job-a')
  })
})
