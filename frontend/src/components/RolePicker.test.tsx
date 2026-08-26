import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import RolePicker from './RolePicker'

describe('RolePicker', () => {
  it('lets the user pick a role and enables Analyse once one is picked', () => {
    const onSelect = vi.fn()
    const { rerender } = render(
      <RolePicker roles={['Data Analyst', 'Backend Engineer']} selected="" onSelect={onSelect}
                  onBack={vi.fn()} onAnalyse={vi.fn()} loadError="" />
    )
    expect(screen.getByText('Run the advisor →')).toBeDisabled()

    fireEvent.click(screen.getByText('Backend Engineer'))
    expect(onSelect).toHaveBeenCalledWith('Backend Engineer')

    rerender(
      <RolePicker roles={['Data Analyst', 'Backend Engineer']} selected="Backend Engineer" onSelect={onSelect}
                  onBack={vi.fn()} onAnalyse={vi.fn()} loadError="" />
    )
    expect(screen.getByText('Run the advisor →')).not.toBeDisabled()
  })

  it('shows the role-load error when present', () => {
    render(<RolePicker roles={[]} selected="" onSelect={vi.fn()} onBack={vi.fn()} onAnalyse={vi.fn()} loadError="network down" />)
    expect(screen.getByText(/Could not load roles: network down/)).toBeInTheDocument()
  })
})
