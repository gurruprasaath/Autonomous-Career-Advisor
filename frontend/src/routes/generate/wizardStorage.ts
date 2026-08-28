import type { AdvisorResult } from '../../api/types'
import type { ProfileFormValues } from '../../components/ProfileForm'

const KEY = 'generate-wizard-state'

export interface WizardState {
  profileInput: ProfileFormValues | null
  role: string
  result: AdvisorResult | null
}

const EMPTY_STATE: WizardState = { profileInput: null, role: '', result: null }

export function loadWizardState(): WizardState {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? { ...EMPTY_STATE, ...JSON.parse(raw) } : EMPTY_STATE
  } catch {
    return EMPTY_STATE // sessionStorage unavailable or corrupted — start fresh
  }
}

export function saveWizardState(partial: Partial<WizardState>): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ ...loadWizardState(), ...partial }))
  } catch {
    // sessionStorage unavailable — the wizard still works for this page load
  }
}

export function clearWizardState(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // ignore
  }
}
