import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RoleStepPage from './RoleStepPage'
import { loadWizardState, saveWizardState } from './wizardStorage'

function renderPage(initialEntries: (string | { pathname: string; state?: unknown })[] = ['/generate/role']) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/generate/profile" element={<p>Profile Step</p>} />
          <Route path="/generate/role" element={<RoleStepPage />} />
          <Route path="/generate/analysis" element={<p>Analysis Step</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('RoleStepPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ roles: ['Data Engineer'] }),
    } as Response))
  })

  it('redirects to the profile step when no profile is saved yet', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('lets you pick a role, persists it, and moves on to analysis', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 } })
    renderPage()

    await waitFor(() => expect(screen.getByText('Data Engineer')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Data Engineer'))
    fireEvent.click(screen.getByText('Run the advisor →'))

    await waitFor(() => expect(screen.getByText('Analysis Step')).toBeInTheDocument())
    expect(loadWizardState().role).toBe('Data Engineer')
  })

  it('shows an inline error passed back from a failed analysis', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 } })
    renderPage([{ pathname: '/generate/role', state: { error: 'boom' } }])

    await waitFor(() => expect(screen.getByText('Advisor failed: boom')).toBeInTheDocument())
  })
})
