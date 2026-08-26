import { useEffect, useRef, useState } from 'react'
import { useRecordProgress } from '../api/tracker'
import type { TrackerStep } from '../api/types'
import QuizModal from './QuizModal'

export default function StepTracker({ step, hoursPerWeek }: {
  step: TrackerStep
  hoursPerWeek: number
}) {
  const [running, setRunning] = useState(false)
  const [elapsedSec, setElapsedSec] = useState(0)
  const [quizOpen, setQuizOpen] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const recordProgress = useRecordProgress()

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [running])

  const stopAndSave = async () => {
    setRunning(false)
    if (elapsedSec > 0) {
      const minutes = Math.max(1, Math.round(elapsedSec / 60))
      await recordProgress.mutateAsync({ stepId: step.id, update: { minutes_delta: minutes } })
    }
    setElapsedSec(0)
  }

  const rateConfidence = (rating: number) => {
    recordProgress.mutate({ stepId: step.id, update: { confidence_rating: rating } })
  }

  const budgetMinutes = step.estimated_weeks * (hoursPerWeek || 10) * 60
  const pct = Math.min(100, Math.round(((step.time_spent_minutes || 0) / Math.max(budgetMinutes, 1)) * 100))

  return (
    <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
        {!running ? (
          <button className="secondary-button" onClick={() => setRunning(true)}>▶ Start timer</button>
        ) : (
          <button className="secondary-button" onClick={stopAndSave}>⏸ Stop ({Math.floor(elapsedSec / 60)}m{elapsedSec % 60}s)</button>
        )}
        <span className="hint">{step.time_spent_minutes || 0}m logged · {pct}% of budget</span>
      </div>

      <div className="confidence-row">
        <span className="hint">Confidence:</span>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} className={`secondary-button confidence-btn ${step.confidence_rating === n ? 'active' : ''}`}
                  onClick={() => rateConfidence(n)}>{n}</button>
        ))}
      </div>

      <div>
        <button className="primary-button" onClick={() => setQuizOpen(true)}>Take Quiz</button>
        {step.quiz_score != null && <span className="hint" style={{ marginLeft: '0.5rem' }}>Last score: {step.quiz_score}%</span>}
      </div>

      {step.github_evidence.length > 0 && (
        <div className="hint">
          ✓ GitHub evidence: {step.github_evidence.map((e) => e.repo_name).join(', ')}
        </div>
      )}

      {quizOpen && (
        <QuizModal step={step} onClose={() => setQuizOpen(false)}
                   onScored={(score) => {
                     recordProgress.mutate({ stepId: step.id, update: { quiz_score: score } })
                     setQuizOpen(false)
                   }} />
      )}
    </div>
  )
}
