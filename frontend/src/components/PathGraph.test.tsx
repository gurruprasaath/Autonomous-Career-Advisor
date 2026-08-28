import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import PathGraph from './PathGraph'
import type { LearningPath } from '../api/types'

function makePath(stepCount: number): LearningPath {
  return {
    target_role: 'Cybersecurity Analyst',
    total_weeks: stepCount * 2,
    rationale: 'test path',
    steps: Array.from({ length: stepCount }, (_, i) => ({
      order: i + 1, skill_id: `skill-${i}`, skill_name: `Skill ${i + 1}`,
      objective: 'obj', resources: [], estimated_weeks: 2, milestone: 'ms',
    })),
  }
}

describe('PathGraph', () => {
  it('renders nothing when there is no path', () => {
    const { container } = render(<PathGraph path={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders one node per step with its order and weeks', () => {
    render(<PathGraph path={makePath(3)} />)
    expect(screen.getByText(/1\. Skill 1/)).toBeInTheDocument()
    expect(screen.getByText(/3\. Skill 3/)).toBeInTheDocument()
    expect(screen.getAllByText('2 weeks')).toHaveLength(3)
  })

  it('sizes the canvas to the step count instead of a fixed height', () => {
    const { container: three } = render(<PathGraph path={makePath(3)} />)
    const { container: nine } = render(<PathGraph path={makePath(9)} />)
    const threeHeight = (three.querySelector('.rf-canvas') as HTMLElement).style.height
    const nineHeight = (nine.querySelector('.rf-canvas') as HTMLElement).style.height
    expect(parseInt(nineHeight)).toBeGreaterThan(parseInt(threeHeight))
  })
})
