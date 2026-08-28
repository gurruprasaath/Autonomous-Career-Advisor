import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AnalysisStepPage from './AnalysisStepPage'
import { loadWizardState, saveWizardState } from './wizardStorage'
import { ADVISOR_RESULT_FIXTURE } from '../../test/fixtures'

const mutateAsync = vi.fn()
vi.mock('../../api/advise', () => ({
  useAdvise: () => ({ mutateAsync }),
}))

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/generate/analysis']}>
        <Routes>
          <Route path="/generate/profile" element={<p>Profile Step</p>} />
          <Route path="/generate/role" element={<p>Role Step</p>} />
          <Route path="/generate/analysis" element={<AnalysisStepPage />} />
          <Route path="/generate/results" element={<p>Results Step</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AnalysisStepPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    mutateAsync.mockReset()
  })

  it('redirects to the profile step when the profile or role is missing', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('runs the advisor once on mount and saves the result on success', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 }, role: 'Data Engineer' })
    mutateAsync.mockResolvedValue(ADVISOR_RESULT_FIXTURE)
    renderPage()

    await waitFor(() => expect(screen.getByText('Results Step')).toBeInTheDocument())
    expect(mutateAsync).toHaveBeenCalledTimes(1)
    expect(loadWizardState().result).toEqual(ADVISOR_RESULT_FIXTURE)
  })

  it('returns to the role step with an error message on failure', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 }, role: 'Data Engineer' })
    mutateAsync.mockRejectedValue(new Error('advisor exploded'))
    renderPage()

    await waitFor(() => expect(screen.getByText('Role Step')).toBeInTheDocument())
  })
})
