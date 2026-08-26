import { describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import ProfileForm from './ProfileForm'

function renderForm(onSubmit = vi.fn()) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <ProfileForm onSubmit={onSubmit} />
    </QueryClientProvider>
  )
  return onSubmit
}

describe('ProfileForm', () => {
  it('disables Continue until background text is entered', () => {
    renderForm()
    expect(screen.getByText('Continue →')).toBeDisabled()
  })

  it('submits the entered background, education, and hours', () => {
    const onSubmit = vi.fn()
    renderForm(onSubmit)

    fireEvent.change(screen.getByPlaceholderText(/Final year CSE student/), { target: { value: 'I know Python' } })
    fireEvent.change(screen.getByPlaceholderText(/B.Tech Computer Science/), { target: { value: 'B.Tech CSE' } })
    fireEvent.change(screen.getByDisplayValue('10'), { target: { value: '15' } })
    fireEvent.click(screen.getByText('Continue →'))

    expect(onSubmit).toHaveBeenCalledWith({ resume_text: 'I know Python', education: 'B.Tech CSE', hours_per_week: 15 })
  })
})
