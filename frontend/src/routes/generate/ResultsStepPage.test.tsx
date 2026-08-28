import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ResultsStepPage from './ResultsStepPage'
import { loadWizardState, saveWizardState } from './wizardStorage'
import { ADVISOR_RESULT_FIXTURE } from '../../test/fixtures'

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/generate/results']}>
      <Routes>
        <Route path="/generate/profile" element={<p>Profile Step</p>} />
        <Route path="/generate/results" element={<ResultsStepPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ResultsStepPage', () => {
  beforeEach(() => sessionStorage.clear())

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
