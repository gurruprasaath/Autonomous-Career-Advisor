import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import StepTracker from './StepTracker'
import type { TrackerStep } from '../api/types'

const STEP: TrackerStep = {
  id: 1, order: 1, skill_id: 'python', skill_name: 'Python', objective: 'Learn Python',
  milestone: 'Build a CLI tool', estimated_weeks: 2, status: 'in_progress',
  quiz_score: null, confidence_rating: null, time_spent_minutes: 30,
  resources: [], github_evidence: [],
}

function renderStep() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <StepTracker step={STEP} hoursPerWeek={10} />
    </QueryClientProvider>
  )
}

describe('StepTracker', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('renders one touch-friendly confidence button per rating 1-5', () => {
    renderStep()
    for (const n of [1, 2, 3, 4, 5]) {
      expect(screen.getByText(String(n))).toHaveClass('confidence-btn')
    }
  })

  it('posts the picked confidence rating', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ id: 1, status: 'in_progress' }),
    } as Response)
    vi.stubGlobal('fetch', fetchMock)

    renderStep()
    fireEvent.click(screen.getByText('4'))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/tracker/step/1/progress',
        expect.objectContaining({ method: 'POST', body: JSON.stringify({ confidence_rating: 4 }) })
      )
    })
  })
})
