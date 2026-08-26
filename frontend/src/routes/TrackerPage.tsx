import { useState } from 'react'
import { useCompetencyHistory, useJourneys, useRecalculateJourney } from '../api/tracker'
import GithubConnect from '../components/GithubConnect'
import CompetencyChart from '../components/CompetencyChart'
import StepTracker from '../components/StepTracker'

export default function TrackerPage() {
  const { data: journeys, isLoading, error } = useJourneys()
  const { data: historyData } = useCompetencyHistory()
  const recalculate = useRecalculateJourney()
  const [recalculatingId, setRecalculatingId] = useState<number | null>(null)

  if (isLoading) return <div>Loading journeys...</div>
  if (error) return <div className="error-box">{error instanceof Error ? error.message : String(error)}</div>

  const skillNames: Record<string, string> = {}
  journeys?.forEach((j) => j.steps.forEach((s) => { skillNames[s.skill_id] = s.skill_name }))

  const runRecalculate = async (journeyId: number) => {
    setRecalculatingId(journeyId)
    try {
      await recalculate.mutateAsync(journeyId)
    } catch (e) {
      alert('Recalculate failed: ' + (e instanceof Error ? e.message : String(e)))
    } finally {
      setRecalculatingId(null)
    }
  }

  return (
    <div className="tracker">
      <GithubConnect />
      <CompetencyChart historyData={historyData ?? {}} skillNames={skillNames} />
      {journeys?.length === 0 && <div>No learning paths generated yet. Go to Generate Path!</div>}
      {journeys?.map((j) => {
        const hasStruggling = j.steps.some((s) => s.status === 'struggling')
        return (
          <div key={j.id} className="panel" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2>Target Role: {j.target_role}</h2>
                <p className="hint">Created At: {new Date(j.created_at).toLocaleString()}</p>
              </div>
              {hasStruggling && (
                <button className="primary-button" disabled={recalculatingId === j.id}
                        onClick={() => runRecalculate(j.id)}>
                  {recalculatingId === j.id ? 'Recalculating...' : 'Recalculate Sub-Path'}
                </button>
              )}
            </div>
            <div className="timeline">
              {j.steps.map((s) => (
                <div className={`tstep ${s.status === 'completed' ? 'done' : s.status === 'struggling' ? 'warn' : ''}`} key={s.id}>
                  <h3 style={{ margin: 0 }}>
                    {s.order}. {s.skill_name} <span className="weeks">{s.estimated_weeks} wk</span>
                    <span className="hint" style={{ marginLeft: '0.5rem' }}>({s.status})</span>
                  </h3>
                  <p>{s.objective}</p>
                  <p className="milestone">🏁 {s.milestone}</p>
                  {s.resources.length > 0 && (
                    <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {s.resources.map((r) => (
                        <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                          📚 {r.title} — {r.provider} {r.free ? '(free)' : ''}
                        </a>
                      ))}
                    </div>
                  )}
                  <StepTracker step={s} hoursPerWeek={j.hours_per_week} />
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
