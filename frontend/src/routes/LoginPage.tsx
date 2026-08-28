import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLogin, useRegister } from '../api/auth'

export default function LoginPage() {
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const navigate = useNavigate()

  const login = useLogin()
  const register = useRegister()
  const active = isLogin ? login : register

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    active.mutate({ email, password }, {
      onSuccess: () => navigate('/generate', { replace: true }),
    })
  }

  return (
    <div style={{ maxWidth: 440, margin: '3rem auto 2rem', textAlign: 'center' }}>
      <span className="kicker">Autonomous Career Advisor</span>
      <h1 style={{ fontSize: '2.2rem', marginBottom: '0.5rem' }}>
        {isLogin ? 'Welcome back.' : 'Begin your assessment.'}
      </h1>
      <p style={{ color: 'var(--text-muted)', marginBottom: '2rem' }}>
        Multi-agent skill gap analysis &amp; verified learning path generation.
      </p>

      <div className="card" style={{ textAlign: 'left' }}>
        <h2>{isLogin ? 'Login' : 'Register'}</h2>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="input-field"
          />
          <div style={{ position: 'relative' }}>
            <input
              type={showPassword ? 'text' : 'password'}
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="input-field"
              style={{ paddingRight: '40px' }}
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              title={showPassword ? 'Hide password' : 'Show password'}
              style={{
                position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem', padding: 0, boxShadow: 'none',
              }}
            >
              {showPassword ? '🙈' : '👁️'}
            </button>
          </div>
          {active.isError && <div className="error-box">{active.error.message}</div>}
          <button type="submit" className="primary-button">
            {isLogin ? 'Login' : 'Register'}
          </button>
        </form>
        <p style={{ marginTop: '1rem', textAlign: 'center' }}>
          {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
          <a href="#" onClick={(e) => { e.preventDefault(); setIsLogin(!isLogin) }}>
            {isLogin ? 'Register here' : 'Login here'}
          </a>
        </p>
      </div>
    </div>
  )
}
