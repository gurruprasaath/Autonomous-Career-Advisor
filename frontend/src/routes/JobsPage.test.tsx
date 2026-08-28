import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import JobsPage from './JobsPage'
import type { JobRecommendation } from '../api/types'

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

function makeJobs(count: number): JobRecommendation[] {
  return Array.from({ length: count }, (_, i) => ({
    posting_id: `job-${i}`, title: `Role ${i}`, company: 'Acme', location: 'Remote',
    url: `https://example.com/job-${i}`, score: 1 - i * 0.01, matched_skills: [],
  }))
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

  it('does not show pagination controls when everything fits on one page', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => (makeJobs(10)),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText(/Role 0 — Acme/)).toBeInTheDocument())
    expect(screen.queryByText('Next →')).not.toBeInTheDocument()
  })

  it('paginates 10 per page and Next/Prev move between pages', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => (makeJobs(25)),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText(/Role 0 — Acme/)).toBeInTheDocument())
    expect(screen.getByText('Page 1 of 3')).toBeInTheDocument()
    expect(screen.queryByText(/Role 10 — Acme/)).not.toBeInTheDocument()
    expect(screen.getByText('← Prev')).toBeDisabled()

    fireEvent.click(screen.getByText('Next →'))
    await waitFor(() => expect(screen.getByText(/Role 10 — Acme/)).toBeInTheDocument())
    expect(screen.getByText('Page 2 of 3')).toBeInTheDocument()
    expect(screen.queryByText(/Role 0 — Acme/)).not.toBeInTheDocument()

    fireEvent.click(screen.getByText('Next →'))
    await waitFor(() => expect(screen.getByText(/Role 20 — Acme/)).toBeInTheDocument())
    expect(screen.getByText('Page 3 of 3')).toBeInTheDocument()
    expect(screen.getByText('Next →')).toBeDisabled()

    fireEvent.click(screen.getByText('← Prev'))
    await waitFor(() => expect(screen.getByText(/Role 10 — Acme/)).toBeInTheDocument())
  })
})
