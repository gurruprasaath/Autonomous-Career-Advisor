import PathGraph from './PathGraph'
import type {
  AdvisorResult, FGCRCritique, GapReport, LearningPath, MarketDemandProfile,
  ResumeReviewResult, StudentProfile,
} from '../api/types'

function Bar({ label, value, max = 1, gap = false, right, rank }: {
  label: string; value: number; max?: number; gap?: boolean; right?: string; rank?: number
}) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  return (
    <div className="bar-row">
      {rank != null && <span className="bar-num">{rank}</span>}
      <span className="bar-label" title={label}>{label}</span>
      <div className="bar-track">
        <div className={`bar-fill ${gap ? 'gap' : ''}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="bar-value">{right ?? `${pct}%`}</span>
    </div>
  )
}

function DemandChart({ demand }: { demand: MarketDemandProfile }) {
  const top = demand.skills.slice(0, 12)
  return (
    <div className="panel">
      <h2>Market demand — {demand.target_role}</h2>
      <p className="hint">
        From {demand.postings_analysed} job postings. Every bar is backed by real
        posting IDs (hover a skill to see them) — nothing here is model guesswork.
      </p>
      {top.map((s, i) => (
        <div key={s.skill_id} title={`Evidence: ${s.posting_ids.join(', ')}`}>
          <Bar rank={i + 1} label={s.name} value={s.share} right={`${Math.round(s.share * 100)}%`} />
        </div>
      ))}
    </div>
  )
}

function ProfileView({ profile }: { profile: StudentProfile }) {
  return (
    <div className="panel">
      <h2>Your extracted profile</h2>
      <p className="hint">{profile.skills.length} skills mapped onto the taxonomy.</p>
      <div className="skill-list">
        {profile.skills.map((s) => (
          <span key={s.skill_id} className="tag" title={s.evidence}>
            {s.name} <span className="tag level">{s.level} (Depth: {s.depth_score}/10)</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function ResumeReviewView({ review }: { review: ResumeReviewResult | null }) {
  if (!review) return null
  return (
    <div className="panel">
      <h2>Resume Feedback (AI Agent)</h2>
      <div className="pullquote">
        <p>{review.overall_impression}</p>
        <cite>Resume Review Agent</cite>
      </div>
      <div className="two-col">
        <div>
          <h3 style={{ color: 'var(--success)', marginTop: 0 }}>Strengths</h3>
          <ul>{review.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div>
          <h3 style={{ color: 'var(--warning)', marginTop: 0 }}>Areas to Improve</h3>
          <ul>{review.weaknesses.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      <div style={{ marginTop: '1rem', fontStyle: 'italic', fontSize: '0.9rem' }}>
        <strong>Formatting Feedback:</strong> {review.formatting_feedback}
      </div>
    </div>
  )
}

function GapView({ report }: { report: GapReport }) {
  const maxP = Math.max(...report.gaps.map((g) => g.priority), 0.001)
  return (
    <div className="panel">
      <h2>Skill gaps (priority = demand × gap)</h2>
      <p className="hint">Computed deterministically over the taxonomy — auditable, not LLM-guessed.</p>
      {report.gaps.slice(0, 10).map((g, i) => (
        <div key={g.skill_id} title={`${g.current_level} → ${g.required_level}`}>
          <Bar rank={i + 1} label={g.name} value={g.priority} max={maxP} gap right={g.priority.toFixed(2)} />
        </div>
      ))}
      {report.strengths.length > 0 && (
        <>
          <label>Already at market level:</label>
          <div className="skill-list">
            {report.strengths.map((s) => <span key={s} className="tag good">✓ {s}</span>)}
          </div>
        </>
      )}
    </div>
  )
}

function VerifierBadge({ critique, revisions }: { critique: FGCRCritique | null; revisions: number }) {
  if (!critique) return null
  const cls = (v: number) => (v >= 4 ? 'good' : v >= 3 ? 'warn' : 'bad')
  const dims: [string, number][] = [
    ['Feasibility', critique.feasibility], ['Groundedness', critique.groundedness],
    ['Coverage', critique.coverage], ['Realism', critique.realism],
  ]
  return (
    <div className="panel">
      <h2>
        Verifier (FGCR rubric){' '}
        <span className={`badge ${critique.passed ? 'pass' : 'fail'}`}>
          {critique.passed ? '✓ verified' : '✗ issues remain'}
        </span>
      </h2>
      <p className="hint">
        An adversarial critic agent scored this path; hard rule-checks cap the LLM's
        scores. Revision loops used: {revisions}.
      </p>
      <div className="fgcr">
        {dims.map(([dim, v]) => (
          <div className="fgcr-card" key={dim}>
            <div className={`score ${cls(v)}`}>{v.toFixed(1)}</div>
            <div className="dim">{dim} / 5</div>
          </div>
        ))}
      </div>
      {critique.issues.length > 0 && (
        <ul className="hint">{critique.issues.map((i, k) => <li key={k}>{i}</li>)}</ul>
      )}
    </div>
  )
}

function PathTimeline({ path }: { path: LearningPath | null }) {
  if (!path) return null
  return (
    <div className="panel">
      <h2>Your learning path — {path.total_weeks} weeks total</h2>
      <p className="hint">{path.rationale}</p>
      <div className="syllabus">
        {path.steps.map((s) => (
          <div className="syl-row" key={s.skill_id}>
            <div className="syl-num">{s.order}</div>
            <div>
              <div className="syl-name">{s.skill_name}</div>
              <p className="syl-obj">{s.objective}</p>
              <p className="milestone">🏁 {s.milestone}</p>
              {s.resources.length > 0 && (
                <div style={{ marginTop: '0.6rem', display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
                  {s.resources.map((r) => (
                    <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                      📚 {r.title} — {r.provider}{r.free ? ' (free)' : ''}
                    </a>
                  ))}
                </div>
              )}
            </div>
            <div className="weeks">{s.estimated_weeks} wk</div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Results({ result, onRestart }: { result: AdvisorResult; onRestart: () => void }) {
  return (
    <>
      {result.notes.length > 0 && result.notes.map((n, i) => <div className="note" key={i}>⚠ {n}</div>)}
      <div className="two-col">
        <ProfileView profile={result.profile} />
        <GapView report={result.gap_report} />
      </div>
      <ResumeReviewView review={result.resume_review} />
      <DemandChart demand={result.demand} />
      <VerifierBadge critique={result.critique} revisions={result.revisions_used} />
      <PathGraph path={result.path} />
      <PathTimeline path={result.path} />
      <button className="ghost" onClick={onRestart}>↺ Start over</button>
    </>
  )
}
