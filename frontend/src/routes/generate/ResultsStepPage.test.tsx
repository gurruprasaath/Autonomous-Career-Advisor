import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ResultsStepPage from './ResultsStepPage'
import { loadWizardState, saveWizardState } from './wizardStorage'
import { ADVISOR_RESULT_FIXTURE } from '../../test/fixtures'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/generate/results']}>
        <Routes>
          <Route path="/generate/profile" element={<p>Profile Step</p>} />
          <Route path="/generate/results" element={<ResultsStepPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ResultsStepPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
    // Results now also renders RecommendedJobsView/InterviewTipsView, each
    // firing its own request — stub both endpoints so this page-navigation
    // test isn't tripped up by unrelated network calls.
    vi.stubGlobal('fetch', vi.fn((url: string) => {
      if (url.includes('/api/jobs/recommendations')) {
        return Promise.resolve({ ok: true, status: 200, json: async () => ([]) } as Response)
      }
      if (url.includes('/api/interview-tips')) {
        return Promise.resolve({
          ok: true, status: 200,
          json: async () => ({ role: 'Data Engineer', focus_topics: [], common_questions: [], advice: '' }),
        } as Response)
      }
      throw new Error(`unexpected fetch in test: ${url}`)
    }))
  })

  it('redirects to the profile step when there is no result saved', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('renders the results and clears state on restart', async () => {
    saveWizardState({ result: ADVISOR_RESULT_FIXTURE })
    renderPage()

    fireEvent.click(await screen.findByText('↺ Start over'))

    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
    expect(loadWizardState().result).toBeNull()
  })
})
