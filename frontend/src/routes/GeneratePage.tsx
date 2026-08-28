import { useState } from 'react'
import { useAdvise, useRoles } from '../api/advise'
import type { AdvisorResult } from '../api/types'
import ProfileForm, { type ProfileFormValues } from '../components/ProfileForm'
import RolePicker from '../components/RolePicker'
import AgentTerminal from '../components/AgentTerminal'
import Results from '../components/Results'

const STEPS = ['Profile', 'Target role', 'Analysis', 'Learning path']

export default function GeneratePage() {
  const [step, setStep] = useState(0)
  const [profileInput, setProfileInput] = useState<ProfileFormValues | null>(null)
  const [role, setRole] = useState('')
  const [result, setResult] = useState<AdvisorResult | null>(null)
  const [error, setError] = useState('')

  const { data: rolesData, error: rolesError } = useRoles()
  const advise = useAdvise()

  const runAdvisor = async () => {
    if (!profileInput) return
    setStep(2)
    setError('')
    try {
      const res = await advise.mutateAsync({ ...profileInput, target_role: role })
      setResult(res)
      setStep(3)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStep(1)
    }
  }

  const restart = () => {
    setStep(0)
    setProfileInput(null)
    setRole('')
    setResult(null)
    setError('')
  }

  return (
    <>
      <div className="steps">
        {STEPS.map((s, i) => (
          <span key={s} className={`step-chip ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
            {String(i + 1).padStart(2, '0')} {i < step ? '✓ ' : ''}{s}
          </span>
        ))}
      </div>

      {error && <div className="error-box">Advisor failed: {error}</div>}

      {step === 0 && (
        <ProfileForm onSubmit={(input) => { setProfileInput(input); setStep(1) }} />
      )}

      {step === 1 && (
        <RolePicker
          roles={rolesData?.roles ?? []}
          selected={role}
          onSelect={setRole}
          onBack={() => setStep(0)}
          onAnalyse={runAdvisor}
          loadError={rolesError instanceof Error ? rolesError.message : ''}
        />
      )}

      {step === 2 && <AgentTerminal role={role} />}

      {step === 3 && result && <Results result={result} onRestart={restart} />}
    </>
  )
}
