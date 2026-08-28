import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import GenerateResumePage from './GenerateResumePage'
import { saveWizardState } from './wizardStorage'
import { ADVISOR_RESULT_FIXTURE } from '../../test/fixtures'

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/generate']}>
      <Routes>
        <Route path="/generate" element={<GenerateResumePage />} />
        <Route path="/generate/profile" element={<p>Profile Step</p>} />
        <Route path="/generate/role" element={<p>Role Step</p>} />
        <Route path="/generate/results" element={<p>Results Step</p>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('GenerateResumePage', () => {
  beforeEach(() => sessionStorage.clear())

  it('resumes at the profile step when nothing is saved', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('resumes at the role step when a profile is saved but no result yet', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 } })
    renderPage()
    await waitFor(() => expect(screen.getByText('Role Step')).toBeInTheDocument())
  })

  it('resumes at the results step when a result is saved', async () => {
    saveWizardState({ result: ADVISOR_RESULT_FIXTURE })
    renderPage()
    await waitFor(() => expect(screen.getByText('Results Step')).toBeInTheDocument())
  })
})
