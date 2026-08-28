import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Results from '../../components/Results'
import WizardSteps from './WizardSteps'
import { clearWizardState, loadWizardState } from './wizardStorage'

export default function ResultsStepPage() {
  const navigate = useNavigate()
  const { result } = loadWizardState()

  useEffect(() => {
    if (!result) navigate('/generate/profile', { replace: true })
  }, [result, navigate])

  if (!result) return null

  const restart = () => {
    clearWizardState()
    navigate('/generate/profile')
  }

  return (
    <>
      <WizardSteps current={3} />
      <Results result={result} onRestart={restart} />
    </>
  )
}
