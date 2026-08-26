import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { setToken } from './api/client'

export default function AppShell() {
  const navigate = useNavigate()

  const logout = () => {
    setToken(null)
    navigate('/login', { replace: true })
  }

  return (
    <>
      <header className="app-header">
        <h1>Autonomous Career Advisor</h1>
        <p>Multi-agent skill gap analysis &amp; verified learning path generation</p>
      </header>

      <nav className="app-nav">
        <NavLink to="/generate" className={({ isActive }) => `secondary-button ${isActive ? 'active' : ''}`}>
          Generate Path
        </NavLink>
        <NavLink to="/tracker" className={({ isActive }) => `secondary-button ${isActive ? 'active' : ''}`}>
          My Learning Tracker
        </NavLink>
        <NavLink to="/repo-analysis" className={({ isActive }) => `secondary-button ${isActive ? 'active' : ''}`}>
          GitHub Analysis
        </NavLink>
        <button className="secondary-button" onClick={logout}>Logout</button>
      </nav>

      <Outlet />
    </>
  )
}
