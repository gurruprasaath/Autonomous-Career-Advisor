import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import CompetencyChart from './CompetencyChart'

describe('CompetencyChart', () => {
  it('renders nothing when there is no history yet', () => {
    const { container } = render(<CompetencyChart historyData={{}} skillNames={{}} />)
    expect(container.firstChild).toBeNull()
  })

  it('renders a single data point without a divide-by-zero on the time axis', () => {
    render(
      <CompetencyChart
        historyData={{ python: [{ depth_score: 4, quiz_score: null, confidence_rating: null, has_github_evidence: false, rationale: 'Initial resume estimate', recorded_at: '2026-08-01T00:00:00Z' }] }}
        skillNames={{ python: 'Python' }}
      />
    )
    expect(screen.getByText(/Latest assessment: Initial resume estimate/)).toBeInTheDocument()
  })

  it('renders a multi-point trajectory and shows the latest rationale', () => {
    render(
      <CompetencyChart
        historyData={{
          python: [
            { depth_score: 3, quiz_score: null, confidence_rating: null, has_github_evidence: false, rationale: 'a', recorded_at: '2026-08-01T00:00:00Z' },
            { depth_score: 6, quiz_score: 80, confidence_rating: 4, has_github_evidence: true, rationale: 'b', recorded_at: '2026-08-10T00:00:00Z' },
          ],
        }}
        skillNames={{ python: 'Python' }}
      />
    )
    expect(screen.getByText(/Latest assessment: b/)).toBeInTheDocument()
  })
})
