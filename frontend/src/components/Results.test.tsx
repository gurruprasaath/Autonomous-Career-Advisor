import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import Results from './Results'
import type { AdvisorResult } from '../api/types'

const RESULT: AdvisorResult = {
  profile: { raw_text: 'x', skills: [], education: '', interests: [], hours_per_week: 10, target_role: 'Data Engineer' },
  demand: { target_role: 'Data Engineer', postings_analysed: 0, skills: [] },
  gap_report: { target_role: 'Data Engineer', gaps: [], strengths: [] },
  path: null,
  critique: null,
  resume_review: null,
  revisions_used: 0,
  notes: [],
}

function renderResults() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Results result={RESULT} onRestart={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

// Results renders both RecommendedJobsView and InterviewTipsView at once,
// so every test's mock must answer BOTH endpoints correctly — a single
// blanket mockResolvedValue would hand the jobs array to useInterviewTips()
// too, and InterviewTipsView would crash calling .map on the missing
// focus_topics field. Route by URL instead, with sane defaults for
// whichever endpoint a given test isn't focused on.
function mockBothEndpoints(overrides: { jobs?: Response; tips?: Response } = {}) {
  const defaultJobs = { ok: true, status: 200, json: async () => ([]) } as Response
  const defaultTips = {
    ok: true, status: 200,
    json: async () => ({ role: 'Data Engineer', focus_topics: [], common_questions: [], advice: '' }),
  } as Response
  vi.stubGlobal('fetch', vi.fn((url: string) => {
    if (url.includes('/api/jobs/recommendations')) return Promise.resolve(overrides.jobs ?? defaultJobs)
    if (url.includes('/api/interview-tips')) return Promise.resolve(overrides.tips ?? defaultTips)
    throw new Error(`unexpected fetch in test: ${url}`)
  }))
}

describe('Results', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('renders recommended jobs once the job-recommendations request resolves', async () => {
    mockBothEndpoints({
      jobs: {
        ok: true, status: 200,
        json: async () => ([
          { posting_id: 'job-a', title: 'Data Engineer', company: 'Acme', location: 'Remote',
            url: 'https://example.com/job-a', score: 0.7, matched_skills: ['Python'] },
        ]),
      } as Response,
    })

    renderResults()

    await waitFor(() => expect(screen.getByText(/Data Engineer — Acme/)).toBeInTheDocument())
    expect(screen.getByText('🔗 Apply')).toHaveAttribute('href', 'https://example.com/job-a')
  })

  it('renders interview tips once the interview-tips request resolves', async () => {
    mockBothEndpoints({
      tips: {
        ok: true, status: 200,
        json: async () => ({
          role: 'Data Engineer', focus_topics: ['ETL / Data Pipelines'],
          common_questions: ['Describe an ETL pipeline you built.'],
          advice: 'Review ETL fundamentals before your interview.',
        }),
      } as Response,
    })

    renderResults()

    await waitFor(() => expect(screen.getByText('Describe an ETL pipeline you built.')).toBeInTheDocument())
    expect(screen.getByText('Review ETL fundamentals before your interview.')).toBeInTheDocument()
  })

  it('shows a quiet note instead of an error box when jobs or tips fail to load', async () => {
    const notFound = {
      ok: false, status: 404, statusText: 'Not Found',
      json: async () => ({ detail: 'Generate a learning path first.' }),
    } as Response
    mockBothEndpoints({ jobs: notFound, tips: notFound })

    renderResults()

    await waitFor(() => expect(screen.getByText(/No job matches available/)).toBeInTheDocument())
    expect(screen.getByText(/No interview tips available/)).toBeInTheDocument()
  })
})
