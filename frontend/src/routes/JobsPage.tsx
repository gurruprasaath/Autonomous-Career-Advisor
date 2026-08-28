import { Link } from 'react-router-dom'
import { useJobRecommendations } from '../api/jobs'

export default function JobsPage() {
  const { data: jobs, isLoading, error } = useJobRecommendations()

  if (isLoading) return <div>Finding job matches...</div>

  if (error) {
    return (
      <div className="panel">
        <h2>Job Matches</h2>
        <p className="hint">{error instanceof Error ? error.message : String(error)}</p>
        <Link to="/generate" className="primary-button" style={{ textDecoration: 'none' }}>Generate Path →</Link>
      </div>
    )
  }

  return (
    <div className="panel">
      <h2>Job Matches</h2>
      <p className="hint">Ranked by overlap with your current skills and what you're actively learning.</p>
      {jobs && jobs.length === 0 && <div>No matching postings found right now — try again later.</div>}
      <div className="syllabus">
        {jobs?.map((job, i) => (
          <div className="syl-row" key={job.posting_id}>
            <div className="syl-num">{i + 1}</div>
            <div>
              <div className="syl-name">{job.title} — {job.company}</div>
              <p className="syl-obj">{job.location}</p>
              {job.matched_skills.length > 0 && (
                <div className="skill-list" style={{ marginTop: '0.5rem' }}>
                  {job.matched_skills.map((s) => <span key={s} className="tag good">{s}</span>)}
                </div>
              )}
              {job.url && (
                <a className="resource" href={job.url} target="_blank" rel="noreferrer" style={{ marginTop: '0.6rem', display: 'inline-flex' }}>
                  🔗 Apply
                </a>
              )}
            </div>
            <div className="weeks">{Math.round(job.score * 100)}% match</div>
          </div>
        ))}
      </div>
    </div>
  )
}
