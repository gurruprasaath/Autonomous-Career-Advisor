import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAdvise } from '../../api/advise'
import AgentTerminal from '../../components/AgentTerminal'
import WizardSteps from './WizardSteps'
import { loadWizardState, saveWizardState } from './wizardStorage'

export default function AnalysisStepPage() {
  const navigate = useNavigate()
  const advise = useAdvise()
  const started = useRef(false)
  const { profileInput, role } = loadWizardState()

  useEffect(() => {
    if (!profileInput || !role) {
      navigate('/generate/profile', { replace: true })
      return
    }
    if (started.current) return // guards against StrictMode's dev-mode double-invoke
    started.current = true

    advise.mutateAsync({ ...profileInput, target_role: role })
      .then((res) => {
        saveWizardState({ result: res })
        navigate('/generate/results')
      })
      .catch((e) => {
        const message = e instanceof Error ? e.message : String(e)
        navigate('/generate/role', { state: { error: message } })
      })
    // Intentionally runs once on mount only — re-running on every render would
    // re-fire the advisor request.
  }, [])

  if (!profileInput || !role) return null

  return (
    <>
      <WizardSteps current={2} />
      <AgentTerminal role={role} />
    </>
  )
}
