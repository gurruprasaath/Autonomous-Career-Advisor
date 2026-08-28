import { Navigate } from 'react-router-dom'
import { loadWizardState } from './wizardStorage'

export default function GenerateResumePage() {
  const { profileInput, result } = loadWizardState()
  if (result) return <Navigate to="/generate/results" replace />
  if (profileInput) return <Navigate to="/generate/role" replace />
  return <Navigate to="/generate/profile" replace />
}
