import { beforeEach, describe, expect, it } from 'vitest'
import { clearWizardState, loadWizardState, saveWizardState } from './wizardStorage'

describe('wizardStorage', () => {
  beforeEach(() => sessionStorage.clear())

  it('returns empty state when nothing is saved', () => {
    expect(loadWizardState()).toEqual({ profileInput: null, role: '', result: null })
  })

  it('persists a partial save and merges it with prior state', () => {
    saveWizardState({ role: 'Data Engineer' })
    saveWizardState({ profileInput: { resume_text: 'I know Python', education: '', hours_per_week: 10 } })

    expect(loadWizardState()).toEqual({
      profileInput: { resume_text: 'I know Python', education: '', hours_per_week: 10 },
      role: 'Data Engineer',
      result: null,
    })
  })

  it('clearWizardState removes everything', () => {
    saveWizardState({ role: 'Data Engineer' })
    clearWizardState()

    expect(loadWizardState()).toEqual({ profileInput: null, role: '', result: null })
  })

  it('falls back to empty state on corrupted JSON', () => {
    sessionStorage.setItem('generate-wizard-state', '{not json')
    expect(loadWizardState()).toEqual({ profileInput: null, role: '', result: null })
  })
})
