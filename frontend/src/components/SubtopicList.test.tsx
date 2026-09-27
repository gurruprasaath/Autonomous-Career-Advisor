import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import SubtopicList, { CurriculumAttribution } from './SubtopicList'
import type { Subtopic } from '../api/types'

const SUBS: Subtopic[] = [
  { id: 'python-oop', name: 'Object-oriented programming', level: 'intermediate' },
  { id: 'python-async', name: 'Async & concurrency', level: 'advanced' },
]

describe('SubtopicList', () => {
  it('renders sub-topics in order with level tags and the roadmap link', () => {
    render(<SubtopicList subtopics={SUBS} roadmapUrl="https://roadmap.sh/python" />)
    const items = screen.getAllByRole('listitem')
    expect(items.map((li) => li.textContent)).toEqual([
      'Object-oriented programming Intermediate',
      'Async & concurrency Advanced',
    ])
    expect(screen.getByText(/See on roadmap\.sh/)).toHaveAttribute('href', 'https://roadmap.sh/python')
  })

  it('omits the roadmap link when there is no URL', () => {
    render(<SubtopicList subtopics={SUBS} roadmapUrl="" />)
    expect(screen.queryByText(/See on roadmap\.sh/)).not.toBeInTheDocument()
  })

  it('renders nothing when there are no sub-topics and no link', () => {
    const { container } = render(<SubtopicList subtopics={[]} roadmapUrl="" />)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows the curriculum attribution text', () => {
    render(<CurriculumAttribution />)
    expect(screen.getByText(
      'Sub-topics drafted with LLM assistance and reviewed by the authors; some skills cross-checked against ESCO (CC BY 4.0), OSSU (MIT), Coding Interview University (CC BY-SA 4.0) and Microsoft Learn.',
    )).toBeInTheDocument()
  })
})
