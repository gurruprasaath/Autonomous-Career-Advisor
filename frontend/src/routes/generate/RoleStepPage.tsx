import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useRoles } from '../../api/advise'
import RolePicker from '../../components/RolePicker'
import WizardSteps from './WizardSteps'
import { loadWizardState, saveWizardState } from './wizardStorage'

export default function RoleStepPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { profileInput } = loadWizardState()
  const [role, setRole] = useState(() => loadWizardState().role)
  const { data: rolesData, error: rolesError } = useRoles()
  const adviseError = (location.state as { error?: string } | null)?.error ?? ''

  useEffect(() => {
    if (!profileInput) navigate('/generate/profile', { replace: true })
  }, [profileInput, navigate])

  if (!profileInput) return null

  const handleSelect = (r: string) => {
    setRole(r)
    saveWizardState({ role: r })
  }

  return (
    <>
      <WizardSteps current={1} />
      {adviseError && <div className="error-box">Advisor failed: {adviseError}</div>}
      <RolePicker
        roles={rolesData?.roles ?? []}
        selected={role}
        onSelect={handleSelect}
        onBack={() => navigate('/generate/profile')}
        onAnalyse={() => navigate('/generate/analysis')}
        loadError={rolesError instanceof Error ? rolesError.message : ''}
      />
    </>
  )
}
