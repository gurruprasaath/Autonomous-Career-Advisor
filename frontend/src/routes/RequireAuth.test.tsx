import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RequireAuth from './RequireAuth'
import { setToken } from '../api/client'

function renderAt(path: string) {
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/login" element={<p>Login Page</p>} />
        <Route path="/protected" element={<RequireAuth><p>Protected Content</p></RequireAuth>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('RequireAuth', () => {
  beforeEach(() => setToken(null))

  it('renders the wrapped children when a token is present', () => {
    setToken('tok123')
    renderAt('/protected')
    expect(screen.getByText('Protected Content')).toBeInTheDocument()
  })

  it('redirects to /login when no token is present', () => {
    setToken(null)
    renderAt('/protected')
    expect(screen.getByText('Login Page')).toBeInTheDocument()
    expect(screen.queryByText('Protected Content')).not.toBeInTheDocument()
  })
})
