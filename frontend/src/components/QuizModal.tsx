import { useEffect, useState } from 'react'
import { useGenerateQuiz, useSubmitQuiz } from '../api/tracker'
import type { QuizQuestion, TrackerStep } from '../api/types'

export default function QuizModal({ step, onClose, onScored }: {
  step: TrackerStep
  onClose: () => void
  onScored: (score: number) => void
}) {
  const [questions, setQuestions] = useState<QuizQuestion[] | null>(null)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [error, setError] = useState('')
  const generateQuiz = useGenerateQuiz()
  const submitQuiz = useSubmitQuiz()

  useEffect(() => {
    generateQuiz.mutate(step.id, {
      onSuccess: (d) => setQuestions(d.questions),
      onError: (e) => setError(e instanceof Error ? e.message : String(e)),
    })
    // step.id is stable for the lifetime of this modal; re-running on every
    // generateQuiz identity change would re-request a fresh quiz on rerender.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step.id])

  const submit = async () => {
    if (!questions) return
    setError('')
    try {
      const orderedAnswers = questions.map((_, i) => answers[i])
      const { score } = await submitQuiz.mutateAsync({ stepId: step.id, answers: orderedAnswers })
      onScored(score)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="card" style={{ maxWidth: 600, margin: '2rem auto' }}>
      <h2>Quiz: {step.skill_name}</h2>
      {generateQuiz.isPending && <p>Generating questions...</p>}
      {error && <div className="error-box">{error}</div>}
      {questions && questions.map((q, i) => (
        <div key={i} style={{ marginBottom: '1rem' }}>
          <p><strong>{i + 1}. {q.question}</strong></p>
          {q.options.map((opt, oi) => (
            <label key={oi} style={{ display: 'block', marginLeft: '1rem' }}>
              <input type="radio" name={`q${i}`} checked={answers[i] === oi}
                     onChange={() => setAnswers({ ...answers, [i]: oi })} /> {opt}
            </label>
          ))}
        </div>
      ))}
      {questions && (
        <button className="primary-button" onClick={submit}
                disabled={submitQuiz.isPending || Object.keys(answers).length !== questions.length}>
          {submitQuiz.isPending ? 'Submitting...' : 'Submit'}
        </button>
      )}
      <button className="secondary-button" style={{ marginLeft: '0.5rem' }} onClick={onClose}>Cancel</button>
    </div>
  )
}
