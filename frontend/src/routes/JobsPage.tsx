import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useJobRecommendations } from '../api/jobs'

const PAGE_SIZE = 10

export default function JobsPage() {
  const { data: jobs, isLoading, error } = useJobRecommendations()
  const [page, setPage] = useState(0)

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

  const totalPages = Math.ceil((jobs?.length ?? 0) / PAGE_SIZE)
  const currentPage = Math.min(page, Math.max(0, totalPages - 1))
  const pageJobs = jobs?.slice(currentPage * PAGE_SIZE, currentPage * PAGE_SIZE + PAGE_SIZE) ?? []

  return (
    <div className="panel">
      <h2>Job Matches</h2>
      <p className="hint">Ranked by overlap with your current skills and what you're actively learning.</p>
      {jobs && jobs.length === 0 && <div>No matching postings found right now — try again later.</div>}
      <div className="syllabus">
        {pageJobs.map((job, i) => (
          <div className="syl-row" key={job.posting_id}>
            <div className="syl-num">{currentPage * PAGE_SIZE + i + 1}</div>
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
      {totalPages > 1 && (
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem' }}>
          <button className="ghost" onClick={() => setPage((p) => p - 1)} disabled={currentPage === 0}>
            ← Prev
          </button>
          <span className="hint" style={{ margin: 0 }}>Page {currentPage + 1} of {totalPages}</span>
          <button className="ghost" onClick={() => setPage((p) => p + 1)} disabled={currentPage >= totalPages - 1}>
            Next →
          </button>
        </div>
      )}
    </div>
  )
}
