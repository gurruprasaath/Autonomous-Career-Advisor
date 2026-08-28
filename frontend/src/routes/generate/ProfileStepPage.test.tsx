import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProfileStepPage from './ProfileStepPage'
import { loadWizardState } from './wizardStorage'

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/generate/profile']}>
        <Routes>
          <Route path="/generate/profile" element={<ProfileStepPage />} />
          <Route path="/generate/role" element={<p>Role Step</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ProfileStepPage', () => {
  beforeEach(() => sessionStorage.clear())

  it('saves the submitted profile and navigates to the role step', async () => {
    renderPage()
    fireEvent.change(screen.getByPlaceholderText(/Final year CSE student/), { target: { value: 'I know Python' } })
    fireEvent.click(screen.getByText('Continue →'))

    await waitFor(() => expect(screen.getByText('Role Step')).toBeInTheDocument())
    expect(loadWizardState().profileInput).toEqual({ resume_text: 'I know Python', education: '', hours_per_week: 10 })
  })
})
