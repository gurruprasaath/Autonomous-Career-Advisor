import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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

function pdfFile(name = 'resume.pdf') {
  return new File(['%PDF-1.4 fake resume bytes'], name, { type: 'application/pdf' })
}

describe('ProfileForm', () => {
  beforeEach(() => vi.unstubAllGlobals())

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

  it('shows an upload confirmation with filename and character count on a successful drop', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ text: 'Extracted resume text' }),
    } as Response))
    renderForm()

    fireEvent.drop(screen.getByText(/Drop your resume PDF here/), { dataTransfer: { files: [pdfFile()] } })

    await waitFor(() => expect(screen.getByText('✓ Extracted 21 characters from resume.pdf.')).toBeInTheDocument())
    expect(screen.getByDisplayValue('Extracted resume text')).toBeInTheDocument()
    expect(screen.queryByText(/Drop your resume PDF here/)).not.toBeInTheDocument()
  })

  it('shows an inline error instead of alert() when extraction fails', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 500, statusText: 'Server Error', json: async () => ({ detail: 'could not read PDF' }),
    } as Response))
    renderForm()

    fireEvent.drop(screen.getByText(/Drop your resume PDF here/), { dataTransfer: { files: [pdfFile()] } })

    await waitFor(() => expect(screen.getByText('Failed to extract PDF: could not read PDF')).toBeInTheDocument())
    expect(screen.queryByText(/✓ Extracted/)).not.toBeInTheDocument()
  })

  it('Remove clears the confirmation back to the drop-zone', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ text: 'Extracted resume text' }),
    } as Response))
    renderForm()

    fireEvent.drop(screen.getByText(/Drop your resume PDF here/), { dataTransfer: { files: [pdfFile()] } })
    await waitFor(() => expect(screen.getByText('Remove')).toBeInTheDocument())

    fireEvent.click(screen.getByText('Remove'))

    expect(screen.getByText(/Drop your resume PDF here/)).toBeInTheDocument()
    expect(screen.queryByText('Remove')).not.toBeInTheDocument()
  })
})
