const STEPS = ['Profile', 'Target role', 'Analysis', 'Learning path']

export default function WizardSteps({ current }: { current: number }) {
  return (
    <div className="steps">
      {STEPS.map((s, i) => (
        <span key={s} className={`step-chip ${i === current ? 'active' : ''} ${i < current ? 'done' : ''}`}>
          {String(i + 1).padStart(2, '0')} {i < current ? '✓ ' : ''}{s}
        </span>
      ))}
    </div>
  )
}
