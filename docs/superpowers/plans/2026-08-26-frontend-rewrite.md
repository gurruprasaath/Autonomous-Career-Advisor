# Frontend Rewrite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `frontend/src`'s untyped, tab-state JSX app with a TypeScript + react-router + TanStack Query app that keeps the exact same feature set and visual style, fixes the two audit-confirmed bugs (GitHub evidence duplication, mobile layout overflow), and adds backend memory of which GitHub repos a user has already analyzed.

**Architecture:** Same Vite + React setup, incrementally converted in place. Each task replaces one coherent slice of the old app (entry point, one route, one domain's hooks) so the app stays buildable and testable after every task. Server state moves entirely into TanStack Query hooks under `src/api/`; no component keeps its own `useState` copy of server data.

**Tech Stack:** TypeScript, react-router-dom v6, @tanstack/react-query v5, Vitest + React Testing Library, FastAPI/SQLAlchemy (one new table, one new endpoint).

## Global Constraints

- Preserve `frontend/src/index.css`'s existing visual design (colors, panel/button/badge styles, typography) — this is an architecture rebuild, not a redesign. Only additive CSS for the two bug fixes below.
- No new product features beyond the existing feature set, plus the one approved addition: remembering analyzed GitHub repos.
- All new frontend source files are TypeScript (`.ts`/`.tsx`) with `strict: true`.
- All server reads/writes go through a TanStack Query hook in `src/api/` — no component-local `useState`/`useEffect`/`fetch` for server data.
- No backend changes beyond the `AnalyzedRepo` table, the `GET /api/github/repos` endpoint, the upsert in the analyze endpoint, and the GitHub-evidence dedup fix.
- Every task must leave `npm run build` (frontend) and `pytest` (backend, if touched) passing.
- Bug fixes to carry out as part of the relevant task (not deferred): GitHub evidence duplication (`map_languages_to_evidence`, Task 6) and mobile layout overflow — nav row (Task 3) and confidence-rating row + touch targets (Task 5).

---

### Task 1: TypeScript + Vitest toolchain

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Delete: `frontend/vite.config.js`
- Create: `frontend/src/test/setup.ts`
- Create: `frontend/src/test/smoke.test.ts`

**Interfaces:**
- Produces: `npm run test`, `npm run typecheck`, `npm run build` — every later task relies on these three commands existing and working.

- [ ] **Step 1: Install the new dependencies**

```bash
cd frontend
npm install react-router-dom @tanstack/react-query
npm install -D typescript vitest @testing-library/react @testing-library/jest-dom @testing-library/user-event jsdom
```

- [ ] **Step 2: Replace `vite.config.js` with `vite.config.ts`**

Delete `frontend/vite.config.js`. Create `frontend/vite.config.ts`:

```ts
/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8080'
    }
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    globals: true,
  }
})
```

- [ ] **Step 3: Add `tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "useDefineForClassFields": true,
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "types": ["vitest/globals", "@testing-library/jest-dom"]
  },
  "include": ["src"]
}
```

- [ ] **Step 4: Add the Vitest setup file**

`frontend/src/test/setup.ts`:

```ts
import '@testing-library/jest-dom/vitest'
```

- [ ] **Step 5: Add scripts to `package.json`**

Modify the `"scripts"` block:

```json
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "oxlint",
    "preview": "vite preview",
    "test": "vitest run",
    "test:watch": "vitest",
    "typecheck": "tsc --noEmit"
  },
```

- [ ] **Step 6: Write the toolchain smoke test**

`frontend/src/test/smoke.test.ts`:

```ts
import { describe, expect, it } from 'vitest'

describe('toolchain smoke test', () => {
  it('runs TypeScript tests via Vitest', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 7: Run the new commands and verify they pass**

Run: `npm run test` — Expected: 1 test file, 1 test, PASS.
Run: `npm run typecheck` — Expected: no output, exit code 0.
Run: `npm run build` — Expected: build succeeds (app still uses the old `.jsx` entry point at this point, which is fine).

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/tsconfig.json frontend/vite.config.ts frontend/src/test/setup.ts frontend/src/test/smoke.test.ts
git rm frontend/vite.config.js
git commit -m "feat(frontend): add TypeScript + Vitest toolchain"
```

---

### Task 2: API client core, shared types, auth hooks

**Files:**
- Create: `frontend/src/api/types.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/auth.ts`
- Create: `frontend/src/api/auth.test.tsx`

**Interfaces:**
- Consumes: nothing (first data-layer task).
- Produces: `apiRequest<T>(path, options)`, `apiUpload<T>(path, formData)`, `getToken()`, `setToken(token: string | null)` from `client.ts`; every type in `types.ts`; `useLogin()`, `useRegister()` from `auth.ts` (both TanStack `useMutation` results taking `{ email: string; password: string }` and resolving with a `TokenResponse`, storing the token as a side effect).

- [ ] **Step 1: Add the shared response/request types**

`frontend/src/api/types.ts`:

```ts
export type MasteryLevel = "none" | "beginner" | "intermediate" | "advanced"

export interface StudentSkill {
  skill_id: string
  name: string
  level: MasteryLevel
  depth_score: number
  evidence: string
}

export interface ResumeReviewResult {
  strengths: string[]
  weaknesses: string[]
  formatting_feedback: string
  overall_impression: string
}

export interface StudentProfile {
  raw_text: string
  skills: StudentSkill[]
  education: string
  interests: string[]
  hours_per_week: number
  target_role: string
}

export interface SkillDemand {
  skill_id: string
  name: string
  frequency: number
  share: number
  posting_ids: string[]
}

export interface MarketDemandProfile {
  target_role: string
  postings_analysed: number
  skills: SkillDemand[]
}

export interface SkillGap {
  skill_id: string
  name: string
  demand_share: number
  current_level: MasteryLevel
  required_level: MasteryLevel
  gap_size: number
  priority: number
}

export interface GapReport {
  target_role: string
  gaps: SkillGap[]
  strengths: string[]
}

export interface PathResource {
  course_id: string
  title: string
  provider: string
  url: string
  free: boolean
}

export interface PathStep {
  order: number
  skill_id: string
  skill_name: string
  objective: string
  resources: PathResource[]
  estimated_weeks: number
  milestone: string
}

export interface LearningPath {
  target_role: string
  steps: PathStep[]
  total_weeks: number
  rationale: string
}

export interface FGCRCritique {
  feasibility: number
  groundedness: number
  coverage: number
  realism: number
  passed: boolean
  issues: string[]
  revision_request: string
}

export interface AdvisorResult {
  profile: StudentProfile
  demand: MarketDemandProfile
  gap_report: GapReport
  path: LearningPath | null
  critique: FGCRCritique | null
  resume_review: ResumeReviewResult | null
  revisions_used: number
  notes: string[]
}

export interface AdviseRequest {
  resume_text: string
  target_role: string
  hours_per_week: number
  education: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export type TrackerStepStatus = "pending" | "in_progress" | "struggling" | "completed"

export interface TrackerStepGithubEvidence {
  repo_name: string
  last_pushed_at: string | null
}

export interface TrackerStep {
  id: number
  order: number
  skill_id: string
  skill_name: string
  objective: string
  milestone: string
  estimated_weeks: number
  status: TrackerStepStatus
  quiz_score: number | null
  confidence_rating: number | null
  time_spent_minutes: number
  resources: PathResource[]
  github_evidence: TrackerStepGithubEvidence[]
}

export interface Journey {
  id: number
  target_role: string
  created_at: string
  hours_per_week: number
  steps: TrackerStep[]
}

export interface CompetencyHistoryEntry {
  depth_score: number
  quiz_score: number | null
  confidence_rating: number | null
  has_github_evidence: boolean
  rationale: string
  recorded_at: string
}

export type CompetencyHistory = Record<string, CompetencyHistoryEntry[]>

export interface ProgressUpdate {
  quiz_score?: number | null
  confidence_rating?: number | null
  minutes_delta?: number
}

export interface QuizQuestion {
  question: string
  options: string[]
}

export interface AnalyzedRepo {
  username: string
  repo_name: string
  file_count: number
  analyzed_at: string
}
```

- [ ] **Step 2: Write the failing auth-hooks test**

`frontend/src/api/auth.test.tsx` (references `./client` and `./auth`, neither of which exist yet):

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { useLogin, useRegister } from './auth'
import { getToken, setToken } from './client'

function wrapper({ children }: { children: ReactNode }) {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
}

describe('useLogin', () => {
  beforeEach(() => {
    setToken(null)
    vi.unstubAllGlobals()
  })

  it('stores the returned access token on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'tok123', token_type: 'bearer' }),
    } as Response))

    const { result } = renderHook(() => useLogin(), { wrapper })
    result.current.mutate({ email: 'a@b.com', password: 'pw' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(getToken()).toBe('tok123')
  })

  it('surfaces the server error message on failure and does not store a token', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 400,
      statusText: 'Bad Request',
      json: async () => ({ detail: 'Incorrect email or password' }),
    } as Response))

    const { result } = renderHook(() => useLogin(), { wrapper })
    result.current.mutate({ email: 'a@b.com', password: 'wrong' })

    await waitFor(() => expect(result.current.isError).toBe(true))
    expect(result.current.error?.message).toBe('Incorrect email or password')
    expect(getToken()).toBeNull()
  })
})

describe('useRegister', () => {
  beforeEach(() => {
    setToken(null)
    vi.unstubAllGlobals()
  })

  it('stores the returned access token on success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ access_token: 'tok456', token_type: 'bearer' }),
    } as Response))

    const { result } = renderHook(() => useRegister(), { wrapper })
    result.current.mutate({ email: 'new@b.com', password: 'pw' })

    await waitFor(() => expect(result.current.isSuccess).toBe(true))
    expect(getToken()).toBe('tok456')
  })
})
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `npm run test -- auth.test.tsx`
Expected: FAIL — cannot resolve `./client` / `./auth`.

- [ ] **Step 4: Implement the API client core**

`frontend/src/api/client.ts`:

```ts
const BASE = ""

let token: string | null = localStorage.getItem("access_token")

export function setToken(newToken: string | null) {
  token = newToken
  if (token) localStorage.setItem("access_token", token)
  else localStorage.removeItem("access_token")
}

export function getToken(): string | null {
  return token
}

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { ...headers, ...(options.headers as Record<string, string> | undefined) },
  })
  if (res.status === 401) {
    setToken(null)
    window.location.reload()
    return undefined as unknown as T // reload is already in flight; caller never sees this
  }
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return res.json()
}

export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { method: "POST", body: formData })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch { /* non-JSON error body */ }
    throw new Error(detail)
  }
  return res.json()
}
```

- [ ] **Step 5: Implement the auth hooks**

`frontend/src/api/auth.ts`:

```ts
import { useMutation } from '@tanstack/react-query'
import { apiRequest, setToken } from './client'
import type { TokenResponse } from './types'

interface Credentials {
  email: string
  password: string
}

function loginRequest({ email, password }: Credentials): Promise<TokenResponse> {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)
  return apiRequest<TokenResponse>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
  })
}

function registerRequest({ email, password }: Credentials): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function useLogin() {
  return useMutation({
    mutationFn: loginRequest,
    onSuccess: (data) => setToken(data.access_token),
  })
}

export function useRegister() {
  return useMutation({
    mutationFn: registerRequest,
    onSuccess: (data) => setToken(data.access_token),
  })
}
```

- [ ] **Step 6: Run the test to verify it passes**

Run: `npm run test -- auth.test.tsx`
Expected: 3 tests PASS.

- [ ] **Step 7: Typecheck and commit**

Run: `npm run typecheck` — Expected: no errors.

```bash
git add frontend/src/api/types.ts frontend/src/api/client.ts frontend/src/api/auth.ts frontend/src/api/auth.test.tsx
git commit -m "feat(frontend): add typed API client core and auth hooks"
```

---

### Task 3: Routing shell, route guard, LoginPage

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/AppShell.tsx`
- Create: `frontend/src/routes/RequireAuth.tsx`
- Create: `frontend/src/routes/LoginPage.tsx`
- Create: `frontend/src/routes/LoginPage.test.tsx`
- Create: `frontend/src/routes/GeneratePage.tsx` (placeholder — real content in Task 4)
- Create: `frontend/src/routes/TrackerPage.tsx` (placeholder — real content in Task 5)
- Create: `frontend/src/routes/RepoAnalysisPage.tsx` (placeholder — real content in Task 7)
- Modify: `frontend/index.html` (script src)
- Move: `frontend/src/index.css` → `frontend/src/styles/index.css`
- Delete: `frontend/src/main.jsx`
- Delete: `frontend/src/App.jsx`
- Delete: `frontend/src/components/Auth.jsx`

**Interfaces:**
- Consumes: `getToken`/`setToken` from `client.ts`, `useLogin`/`useRegister` from `auth.ts` (Task 2).
- Produces: routes `/login`, `/generate`, `/tracker`, `/repo-analysis`; `RequireAuth` guard component later tasks don't need to touch.

- [ ] **Step 1: Move the stylesheet into its final location**

```bash
git mv frontend/src/index.css frontend/src/styles/index.css
```

Add the nav-row overflow fix (this is the Task-3 half of the mobile-layout bug — the confidence-rating row is fixed in Task 5) to the end of `frontend/src/styles/index.css`:

```css

/* App nav (Generate Path / Tracker / GitHub Analysis / Logout) — must wrap
   instead of overflowing horizontally at narrow widths. */
.app-nav {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 2rem;
}
```

- [ ] **Step 2: Write the route guard**

`frontend/src/routes/RequireAuth.tsx`:

```tsx
import type { ReactNode } from 'react'
import { Navigate } from 'react-router-dom'
import { getToken } from '../api/client'

export default function RequireAuth({ children }: { children: ReactNode }) {
  if (!getToken()) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}
```

- [ ] **Step 3: Write the failing LoginPage test**

`frontend/src/routes/LoginPage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import LoginPage from './LoginPage'
import { getToken, setToken } from '../api/client'

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    setToken(null)
    vi.unstubAllGlobals()
  })

  it('logs in with email and password and stores the token', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ access_token: 'tok789', token_type: 'bearer' }),
    } as Response))

    renderPage()
    fireEvent.change(screen.getByPlaceholderText('Email'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'pw' } })
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))

    await waitFor(() => expect(getToken()).toBe('tok789'))
  })

  it('shows the server error on failed login', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false, status: 400, statusText: 'Bad Request',
      json: async () => ({ detail: 'Incorrect email or password' }),
    } as Response))

    renderPage()
    fireEvent.change(screen.getByPlaceholderText('Email'), { target: { value: 'a@b.com' } })
    fireEvent.change(screen.getByPlaceholderText('Password'), { target: { value: 'wrong' } })
    fireEvent.click(screen.getByRole('button', { name: 'Login' }))

    await waitFor(() => expect(screen.getByText('Incorrect email or password')).toBeInTheDocument())
  })

  it('toggles to the register form', () => {
    renderPage()
    fireEvent.click(screen.getByText('Register here'))
    expect(screen.getByRole('button', { name: 'Register' })).toBeInTheDocument()
  })
})
```

- [ ] **Step 4: Run the test to verify it fails**

Run: `npm run test -- LoginPage.test.tsx`
Expected: FAIL — `./LoginPage` does not exist.

- [ ] **Step 5: Implement LoginPage**

`frontend/src/routes/LoginPage.tsx`:

```tsx
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
    <div className="card" style={{ maxWidth: 400, margin: '2rem auto' }}>
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
  )
}
```

Note: the show/hide password icons are simplified to emoji here — the original inline SVGs are purely decorative and carry no behavior worth preserving pixel-for-pixel; this keeps the port focused on architecture, not icon fidelity.

- [ ] **Step 6: Run the test to verify it passes**

Run: `npm run test -- LoginPage.test.tsx`
Expected: 3 tests PASS.

- [ ] **Step 7: Write the AppShell and placeholder route pages**

`frontend/src/AppShell.tsx`:

```tsx
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
```

`frontend/src/routes/GeneratePage.tsx` (placeholder, replaced in Task 4):

```tsx
export default function GeneratePage() {
  return <div className="panel">Generate Path — coming in Task 4.</div>
}
```

`frontend/src/routes/TrackerPage.tsx` (placeholder, replaced in Task 5):

```tsx
export default function TrackerPage() {
  return <div className="panel">Learning Tracker — coming in Task 5.</div>
}
```

`frontend/src/routes/RepoAnalysisPage.tsx` (placeholder, replaced in Task 7):

```tsx
export default function RepoAnalysisPage() {
  return <div className="panel">GitHub Repository Analysis — coming in Task 7.</div>
}
```

- [ ] **Step 8: Wire up the router entry point**

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './styles/index.css'
import AppShell from './AppShell'
import RequireAuth from './routes/RequireAuth'
import LoginPage from './routes/LoginPage'
import GeneratePage from './routes/GeneratePage'
import TrackerPage from './routes/TrackerPage'
import RepoAnalysisPage from './routes/RepoAnalysisPage'

document.title = 'Autonomous Career Advisor'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth><AppShell /></RequireAuth>}>
            <Route index element={<Navigate to="/generate" replace />} />
            <Route path="generate" element={<GeneratePage />} />
            <Route path="tracker" element={<TrackerPage />} />
            <Route path="repo-analysis" element={<RepoAnalysisPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
```

Note: `<Route element={<RequireAuth><AppShell /></RequireAuth>}>` wraps `AppShell` in the guard — when unauthenticated, `RequireAuth` redirects before `AppShell`/`Outlet` ever render, and when authenticated `AppShell`'s `<Outlet />` renders whichever child route matched. This is standard react-router v6 layout-route usage.

- [ ] **Step 9: Update `index.html` and remove the old entry point**

Modify `frontend/index.html` line `<script type="module" src="/src/main.jsx"></script>` to:

```html
    <script type="module" src="/src/main.tsx"></script>
```

```bash
git rm frontend/src/main.jsx frontend/src/App.jsx frontend/src/components/Auth.jsx
```

- [ ] **Step 10: Manual verification**

Run: `npm run build` — Expected: succeeds.
Run: `npm run typecheck` — Expected: no errors.
Run: `npm run test` — Expected: all tests (including Task 1/2's) still PASS.

- [ ] **Step 11: Commit**

```bash
git add frontend/index.html frontend/src/main.tsx frontend/src/AppShell.tsx frontend/src/routes frontend/src/styles/index.css
git commit -m "feat(frontend): add react-router shell, route guard, and LoginPage"
```

---

### Task 4: Generate-path wizard (advise hooks + ProfileForm, RolePicker, AgentTerminal, Results, PathGraph)

**Files:**
- Create: `frontend/src/api/advise.ts`
- Create: `frontend/src/components/ProfileForm.tsx`
- Create: `frontend/src/components/ProfileForm.test.tsx`
- Create: `frontend/src/components/RolePicker.tsx`
- Create: `frontend/src/components/RolePicker.test.tsx`
- Create: `frontend/src/components/AgentTerminal.tsx`
- Create: `frontend/src/components/PathGraph.tsx`
- Create: `frontend/src/components/Results.tsx`
- Modify: `frontend/src/routes/GeneratePage.tsx` (replace placeholder)
- Delete: `frontend/src/components/ProfileForm.jsx`, `RolePicker.jsx`, `AgentTerminal.jsx`, `PathGraph.jsx`, `Results.jsx`

**Interfaces:**
- Consumes: `apiRequest`/`apiUpload` from `client.ts`, `AdvisorResult`/`AdviseRequest` types (Task 2).
- Produces: `useRoles()`, `useAdvise()`, `useExtractPdf()` from `advise.ts`; `ProfileFormValues` type from `ProfileForm.tsx`.

- [ ] **Step 1: Add the advise hooks**

`frontend/src/api/advise.ts`:

```ts
import { useMutation, useQuery } from '@tanstack/react-query'
import { apiRequest, apiUpload } from './client'
import type { AdvisorResult, AdviseRequest } from './types'

interface RolesResponse {
  roles: string[]
}

export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: () => apiRequest<RolesResponse>('/api/roles'),
  })
}

export function useAdvise() {
  return useMutation({
    mutationFn: (payload: AdviseRequest) =>
      apiRequest<AdvisorResult>('/api/advise', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  })
}

interface ExtractPdfResponse {
  text: string
}

export function useExtractPdf() {
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      return apiUpload<ExtractPdfResponse>('/api/extract_pdf', formData)
    },
  })
}
```

- [ ] **Step 2: Write the failing ProfileForm and RolePicker tests**

`frontend/src/components/ProfileForm.test.tsx`:

```tsx
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
```

`frontend/src/components/RolePicker.test.tsx`:

```tsx
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
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `npm run test -- ProfileForm.test.tsx RolePicker.test.tsx`
Expected: FAIL — `./ProfileForm` / `./RolePicker` do not exist.

- [ ] **Step 4: Implement ProfileForm and RolePicker**

`frontend/src/components/ProfileForm.tsx`:

```tsx
import { useRef, useState } from 'react'
import { useExtractPdf } from '../api/advise'

const SAMPLE = `Final year B.Tech CSE student. Comfortable with Python — built several
projects with pandas and matplotlib for data analysis coursework. Completed an
online SQL course and used PostgreSQL in a database project. Did a machine
learning course covering regression and classification with scikit-learn.
Familiar with Git and GitHub from team projects. Basic knowledge of HTML and CSS.`

export interface ProfileFormValues {
  resume_text: string
  education: string
  hours_per_week: number
}

export default function ProfileForm({ onSubmit }: { onSubmit: (values: ProfileFormValues) => void }) {
  const [text, setText] = useState('')
  const [education, setEducation] = useState('')
  const [hours, setHours] = useState(10)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const extractPdf = useExtractPdf()

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      const data = await extractPdf.mutateAsync(file)
      setText(data.text)
    } catch (err) {
      alert('Failed to extract PDF: ' + (err instanceof Error ? err.message : String(err)))
    } finally {
      e.target.value = ''
    }
  }

  return (
    <div className="panel">
      <h2>1 · Tell us about yourself</h2>
      <p className="hint">
        Paste your resume, or describe your skills, projects and coursework in your
        own words. The Profile Agent extracts and levels your skills from this text.
      </p>

      <label>Your background *</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="e.g. Final year CSE student, built projects with Python and..."
      />
      <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
        <button className="ghost" onClick={() => setText(SAMPLE)} style={{ marginTop: 0 }}>
          Use sample profile
        </button>
        <button
          className="ghost"
          onClick={() => fileInputRef.current?.click()}
          disabled={extractPdf.isPending}
          style={{ marginTop: 0, borderColor: 'var(--accent)', color: 'var(--accent)' }}
        >
          {extractPdf.isPending ? 'Extracting...' : 'Upload Resume (PDF)'}
        </button>
        <input
          type="file"
          accept="application/pdf"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={handleFileUpload}
        />
      </div>

      <div className="two-col">
        <div>
          <label>Education (optional)</label>
          <input
            type="text"
            value={education}
            onChange={(e) => setEducation(e.target.value)}
            placeholder="B.Tech Computer Science, 2026"
          />
        </div>
        <div>
          <label>Study hours available per week</label>
          <input
            type="number"
            min="1"
            max="60"
            value={hours}
            onChange={(e) => setHours(Number(e.target.value))}
          />
        </div>
      </div>

      <button
        className="primary"
        disabled={!text.trim()}
        onClick={() => onSubmit({ resume_text: text, education, hours_per_week: hours })}
      >
        Continue →
      </button>
    </div>
  )
}
```

`frontend/src/components/RolePicker.tsx`:

```tsx
export default function RolePicker({ roles, selected, onSelect, onBack, onAnalyse, loadError }: {
  roles: string[]
  selected: string
  onSelect: (role: string) => void
  onBack: () => void
  onAnalyse: () => void
  loadError: string
}) {
  return (
    <div className="panel">
      <h2>2 · Pick your target role</h2>
      <p className="hint">
        The Market Demand Agent will analyse job postings for this role and build an
        evidence-backed demand profile.
      </p>
      {loadError && <div className="error-box">Could not load roles: {loadError}</div>}
      <div className="role-grid">
        {roles.map((r) => (
          <button
            key={r}
            className={`role-card ${selected === r ? 'selected' : ''}`}
            onClick={() => onSelect(r)}
          >
            {r}
          </button>
        ))}
      </div>
      <div>
        <button className="ghost" onClick={onBack}>← Back</button>
        <button className="primary" disabled={!selected} onClick={onAnalyse}>
          Run the advisor →
        </button>
      </div>
    </div>
  )
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npm run test -- ProfileForm.test.tsx RolePicker.test.tsx`
Expected: 4 tests PASS.

- [ ] **Step 6: Port AgentTerminal, PathGraph, Results (no behavior change — direct TS port)**

`frontend/src/components/AgentTerminal.tsx`:

```tsx
import { useEffect, useState } from 'react'

const LOGS = [
  '[System] Initializing Multi-Agent System...',
  '[ProfileAgent] Parsing user background...',
  '[ProfileAgent] Extracted skills. Mapping to taxonomy...',
  '[MarketAgent] Connecting to live job board...',
  '[MarketAgent] Analyzing recent postings for target role...',
  '[MarketAgent] Extracting core competencies and demand shares...',
  '[GapAgent] Comparing user profile vs market demand...',
  '[GapAgent] Identifying critical skill gaps...',
  '[PathAgent] Generating learning path steps...',
  '[PathAgent] Searching for relevant courses...',
  '[VerifierAgent] Evaluating path feasibility (FGCR Rubric)...',
  '[VerifierAgent] Path looks good. Finalizing results...',
]

interface LogLine {
  text: string
  time: Date
}

export default function AgentTerminal({ role }: { role: string }) {
  const [lines, setLines] = useState<LogLine[]>([])

  useEffect(() => {
    let current = 0
    const interval = setInterval(() => {
      if (current < LOGS.length) {
        const text = LOGS[current].replace('target role', role || 'target role')
        setLines((prev) => [...prev, { text, time: new Date() }])
        current++
      } else {
        setLines((prev) => {
          if (!prev.some((l) => l.text === '[System] Waiting for final LLM verification...')) {
            return [...prev, { text: '[System] Waiting for final LLM verification...', time: new Date() }]
          }
          return prev
        })
        clearInterval(interval)
      }
    }, 1500)

    return () => clearInterval(interval)
  }, [role])

  return (
    <div className="panel" style={{ padding: '0', overflow: 'hidden' }}>
      <div style={{ background: '#1e1e24', padding: '8px 16px', borderBottom: '1px solid #333', display: 'flex', gap: '6px' }}>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f56' }}></div>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ffbd2e' }}></div>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#27c93f' }}></div>
        <span style={{ marginLeft: '12px', color: '#888', fontSize: '0.85rem', fontFamily: 'monospace' }}>agent-logs ~ /usr/bin/advisor</span>
      </div>
      <div style={{ padding: '20px', background: '#0d0d0d', minHeight: '250px', fontFamily: 'monospace', fontSize: '0.9rem', color: '#00ff00', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {lines.map((l, i) => (
          <div key={i} style={{ animation: 'fadeIn 0.3s ease-out' }}>
            <span style={{ color: '#888' }}>{l.time.toLocaleTimeString('en-GB')}</span> {l.text}
          </div>
        ))}
        {lines.length < LOGS.length && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', color: '#888' }}>
            <div className="spinner" style={{ width: 16, height: 16, margin: 0, borderWidth: 2 }} />
            Processing...
          </div>
        )}
      </div>
    </div>
  )
}
```

`frontend/src/components/PathGraph.tsx`:

```tsx
import { useMemo } from 'react'
import ReactFlow, { Background, Controls, MarkerType, type Edge, type Node } from 'reactflow'
import 'reactflow/dist/style.css'
import type { LearningPath } from '../api/types'

const NODE_TYPES = {}
const EDGE_TYPES = {}

export default function PathGraph({ path }: { path: LearningPath | null }) {
  const { nodes, edges } = useMemo(() => {
    if (!path || !path.steps) return { nodes: [] as Node[], edges: [] as Edge[] }

    const newNodes: Node[] = path.steps.map((step, i) => ({
      id: step.skill_id,
      position: { x: 250, y: i * 150 + 50 },
      data: {
        label: (
          <div style={{ padding: '10px', textAlign: 'center' }}>
            <strong>{step.order}. {step.skill_name}</strong>
            <div style={{ fontSize: '0.8rem', color: '#ffbd2e', marginTop: '4px' }}>
              {step.estimated_weeks} weeks
            </div>
          </div>
        ),
      },
      style: {
        background: 'rgba(24, 24, 27, 0.7)', color: '#fff', border: '1px solid #333',
        borderRadius: '8px', width: 250, backdropFilter: 'blur(12px)',
      },
    }))

    const newEdges: Edge[] = []
    for (let i = 0; i < path.steps.length - 1; i++) {
      newEdges.push({
        id: `e-${path.steps[i].skill_id}-${path.steps[i + 1].skill_id}`,
        source: path.steps[i].skill_id,
        target: path.steps[i + 1].skill_id,
        animated: true,
        style: { stroke: '#00ff00', strokeWidth: 2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: '#00ff00' },
      })
    }

    return { nodes: newNodes, edges: newEdges }
  }, [path])

  if (!path) return null

  return (
    <div className="panel" style={{ height: '600px', padding: 0 }}>
      <div style={{ padding: '20px', borderBottom: '1px solid #333', background: 'var(--panel)' }}>
        <h2 style={{ margin: 0 }}>Interactive Learning Path ({path.total_weeks} weeks)</h2>
        <p className="hint" style={{ margin: 0 }}>{path.rationale}</p>
      </div>
      <div style={{ width: '100%', height: 'calc(100% - 80px)' }}>
        <ReactFlow nodes={nodes} edges={edges} nodeTypes={NODE_TYPES} edgeTypes={EDGE_TYPES} fitView>
          <Background color="#333" gap={16} />
          <Controls style={{ background: '#111', fill: '#fff' }} />
        </ReactFlow>
      </div>
    </div>
  )
}
```

`frontend/src/components/Results.tsx`:

```tsx
import PathGraph from './PathGraph'
import type {
  AdvisorResult, FGCRCritique, GapReport, LearningPath, MarketDemandProfile,
  ResumeReviewResult, StudentProfile,
} from '../api/types'

function Bar({ label, value, max = 1, gap = false, right }: {
  label: string; value: number; max?: number; gap?: boolean; right?: string
}) {
  const pct = Math.min(100, Math.round((value / max) * 100))
  return (
    <div className="bar-row">
      <span className="bar-label" title={label}>{label}</span>
      <div className="bar-track">
        <div className={`bar-fill ${gap ? 'gap' : ''}`} style={{ width: `${pct}%` }} />
      </div>
      <span className="bar-value">{right ?? `${pct}%`}</span>
    </div>
  )
}

function DemandChart({ demand }: { demand: MarketDemandProfile }) {
  const top = demand.skills.slice(0, 12)
  return (
    <div className="panel">
      <h2>Market demand — {demand.target_role}</h2>
      <p className="hint">
        From {demand.postings_analysed} job postings. Every bar is backed by real
        posting IDs (hover a skill to see them) — nothing here is model guesswork.
      </p>
      {top.map((s) => (
        <div key={s.skill_id} title={`Evidence: ${s.posting_ids.join(', ')}`}>
          <Bar label={s.name} value={s.share} right={`${Math.round(s.share * 100)}%`} />
        </div>
      ))}
    </div>
  )
}

function ProfileView({ profile }: { profile: StudentProfile }) {
  return (
    <div className="panel">
      <h2>Your extracted profile</h2>
      <p className="hint">{profile.skills.length} skills mapped onto the taxonomy.</p>
      <div className="skill-list">
        {profile.skills.map((s) => (
          <span key={s.skill_id} className="tag" title={s.evidence}>
            {s.name} <span className="tag level">{s.level} (Depth: {s.depth_score}/10)</span>
          </span>
        ))}
      </div>
    </div>
  )
}

function ResumeReviewView({ review }: { review: ResumeReviewResult | null }) {
  if (!review) return null
  return (
    <div className="panel">
      <h2>Resume Feedback (AI Agent)</h2>
      <p className="hint">{review.overall_impression}</p>
      <div className="two-col" style={{ marginTop: '1rem' }}>
        <div>
          <h3 style={{ color: 'var(--success)', marginTop: 0 }}>Strengths</h3>
          <ul>{review.strengths.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
        <div>
          <h3 style={{ color: 'var(--warning)', marginTop: 0 }}>Areas to Improve</h3>
          <ul>{review.weaknesses.map((s, i) => <li key={i}>{s}</li>)}</ul>
        </div>
      </div>
      <div style={{ marginTop: '1rem', fontStyle: 'italic', fontSize: '0.9rem' }}>
        <strong>Formatting Feedback:</strong> {review.formatting_feedback}
      </div>
    </div>
  )
}

function GapView({ report }: { report: GapReport }) {
  const maxP = Math.max(...report.gaps.map((g) => g.priority), 0.001)
  return (
    <div className="panel">
      <h2>Skill gaps (priority = demand × gap)</h2>
      <p className="hint">Computed deterministically over the taxonomy — auditable, not LLM-guessed.</p>
      {report.gaps.slice(0, 10).map((g) => (
        <div key={g.skill_id} title={`${g.current_level} → ${g.required_level}`}>
          <Bar label={g.name} value={g.priority} max={maxP} gap right={g.priority.toFixed(2)} />
        </div>
      ))}
      {report.strengths.length > 0 && (
        <>
          <label>Already at market level:</label>
          <div className="skill-list">
            {report.strengths.map((s) => <span key={s} className="tag good">✓ {s}</span>)}
          </div>
        </>
      )}
    </div>
  )
}

function VerifierBadge({ critique, revisions }: { critique: FGCRCritique | null; revisions: number }) {
  if (!critique) return null
  const cls = (v: number) => (v >= 4 ? 'good' : v >= 3 ? 'warn' : 'bad')
  const dims: [string, number][] = [
    ['Feasibility', critique.feasibility], ['Groundedness', critique.groundedness],
    ['Coverage', critique.coverage], ['Realism', critique.realism],
  ]
  return (
    <div className="panel">
      <h2>
        Verifier (FGCR rubric){' '}
        <span className={`badge ${critique.passed ? 'pass' : 'fail'}`}>
          {critique.passed ? '✓ verified' : '✗ issues remain'}
        </span>
      </h2>
      <p className="hint">
        An adversarial critic agent scored this path; hard rule-checks cap the LLM's
        scores. Revision loops used: {revisions}.
      </p>
      <div className="fgcr">
        {dims.map(([dim, v]) => (
          <div className="fgcr-card" key={dim}>
            <div className={`score ${cls(v)}`}>{v.toFixed(1)}</div>
            <div className="dim">{dim} / 5</div>
          </div>
        ))}
      </div>
      {critique.issues.length > 0 && (
        <ul className="hint">{critique.issues.map((i, k) => <li key={k}>{i}</li>)}</ul>
      )}
    </div>
  )
}

function PathTimeline({ path }: { path: LearningPath | null }) {
  if (!path) return null
  return (
    <div className="panel">
      <h2>Your learning path — {path.total_weeks} weeks total</h2>
      <p className="hint">{path.rationale}</p>
      <div className="timeline">
        {path.steps.map((s) => (
          <div className="tstep" key={s.skill_id}>
            <h3>{s.order}. {s.skill_name} <span className="weeks">{s.estimated_weeks} wk</span></h3>
            <p>{s.objective}</p>
            <p className="milestone">🏁 {s.milestone}</p>
            {s.resources.map((r) => (
              <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                📚 {r.title} — {r.provider}{r.free ? ' (free)' : ''}
              </a>
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Results({ result, onRestart }: { result: AdvisorResult; onRestart: () => void }) {
  return (
    <>
      {result.notes.length > 0 && result.notes.map((n, i) => <div className="note" key={i}>⚠ {n}</div>)}
      <div className="two-col">
        <ProfileView profile={result.profile} />
        <GapView report={result.gap_report} />
      </div>
      <ResumeReviewView review={result.resume_review} />
      <DemandChart demand={result.demand} />
      <VerifierBadge critique={result.critique} revisions={result.revisions_used} />
      <PathGraph path={result.path} />
      <PathTimeline path={result.path} />
      <button className="ghost" onClick={onRestart}>↺ Start over</button>
    </>
  )
}
```

- [ ] **Step 7: Replace the GeneratePage placeholder with the real wizard**

`frontend/src/routes/GeneratePage.tsx`:

```tsx
import { useState } from 'react'
import { useAdvise, useRoles } from '../api/advise'
import type { AdvisorResult } from '../api/types'
import ProfileForm, { type ProfileFormValues } from '../components/ProfileForm'
import RolePicker from '../components/RolePicker'
import AgentTerminal from '../components/AgentTerminal'
import Results from '../components/Results'

const STEPS = ['Profile', 'Target role', 'Analysis', 'Learning path']

export default function GeneratePage() {
  const [step, setStep] = useState(0)
  const [profileInput, setProfileInput] = useState<ProfileFormValues | null>(null)
  const [role, setRole] = useState('')
  const [result, setResult] = useState<AdvisorResult | null>(null)
  const [error, setError] = useState('')

  const { data: rolesData, error: rolesError } = useRoles()
  const advise = useAdvise()

  const runAdvisor = async () => {
    if (!profileInput) return
    setStep(2)
    setError('')
    try {
      const res = await advise.mutateAsync({ ...profileInput, target_role: role })
      setResult(res)
      setStep(3)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
      setStep(1)
    }
  }

  const restart = () => {
    setStep(0)
    setProfileInput(null)
    setRole('')
    setResult(null)
    setError('')
  }

  return (
    <>
      <div className="steps">
        {STEPS.map((s, i) => (
          <span key={s} className={`step-chip ${i === step ? 'active' : ''} ${i < step ? 'done' : ''}`}>
            {i < step ? '✓ ' : ''}{s}
          </span>
        ))}
      </div>

      {error && <div className="error-box">Advisor failed: {error}</div>}

      {step === 0 && (
        <ProfileForm onSubmit={(input) => { setProfileInput(input); setStep(1) }} />
      )}

      {step === 1 && (
        <RolePicker
          roles={rolesData?.roles ?? []}
          selected={role}
          onSelect={setRole}
          onBack={() => setStep(0)}
          onAnalyse={runAdvisor}
          loadError={rolesError instanceof Error ? rolesError.message : ''}
        />
      )}

      {step === 2 && <AgentTerminal role={role} />}

      {step === 3 && result && <Results result={result} onRestart={restart} />}
    </>
  )
}
```

- [ ] **Step 8: Remove the old components and verify**

```bash
git rm frontend/src/components/ProfileForm.jsx frontend/src/components/RolePicker.jsx frontend/src/components/AgentTerminal.jsx frontend/src/components/PathGraph.jsx frontend/src/components/Results.jsx
```

Run: `npm run typecheck && npm run test && npm run build`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/api/advise.ts frontend/src/components frontend/src/routes/GeneratePage.tsx
git commit -m "feat(frontend): port the Generate Path wizard to TypeScript"
```

---

### Task 5: Learning Tracker (tracker + github-sync hooks, split components, mobile-overflow + touch-target fix)

**Files:**
- Create: `frontend/src/api/tracker.ts`
- Create: `frontend/src/api/github.ts` (starts with `useSyncGithub` only — extended in Task 7)
- Create: `frontend/src/components/CompetencyChart.tsx`
- Create: `frontend/src/components/CompetencyChart.test.tsx`
- Create: `frontend/src/components/QuizModal.tsx`
- Create: `frontend/src/components/StepTracker.tsx`
- Create: `frontend/src/components/StepTracker.test.tsx`
- Create: `frontend/src/components/GithubConnect.tsx`
- Create: `frontend/src/components/GithubConnect.test.tsx`
- Modify: `frontend/src/routes/TrackerPage.tsx` (replace placeholder)
- Modify: `frontend/src/styles/index.css` (confidence-row wrap + touch-target fix)
- Delete: `frontend/src/components/LearningTracker.jsx`

**Interfaces:**
- Consumes: `apiRequest` (Task 2); `TrackerStep`, `Journey`, `CompetencyHistory`, `ProgressUpdate`, `QuizQuestion` types (Task 2).
- Produces: `useJourneys()`, `useCompetencyHistory()`, `useRecordProgress()`, `useGenerateQuiz()`, `useSubmitQuiz()`, `useRecalculateJourney()` from `tracker.ts`; `useSyncGithub()` from `github.ts` (Task 7 adds more hooks to this same file).

- [ ] **Step 1: Add the tracker hooks**

`frontend/src/api/tracker.ts`:

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { CompetencyHistory, Journey, ProgressUpdate, QuizQuestion } from './types'

export function useJourneys() {
  return useQuery({
    queryKey: ['journeys'],
    queryFn: () => apiRequest<Journey[]>('/api/tracker/journeys'),
  })
}

export function useCompetencyHistory() {
  return useQuery({
    queryKey: ['competency-history'],
    queryFn: () => apiRequest<CompetencyHistory>('/api/tracker/competency-history'),
  })
}

export function useRecordProgress() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ stepId, update }: { stepId: number; update: ProgressUpdate }) =>
      apiRequest(`/api/tracker/step/${stepId}/progress`, {
        method: 'POST', body: JSON.stringify(update),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journeys'] }),
  })
}

export function useGenerateQuiz() {
  return useMutation({
    mutationFn: (stepId: number) =>
      apiRequest<{ questions: QuizQuestion[] }>(`/api/tracker/step/${stepId}/quiz`, { method: 'POST' }),
  })
}

export function useSubmitQuiz() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ stepId, answers }: { stepId: number; answers: (number | undefined)[] }) =>
      apiRequest<{ score: number }>(`/api/tracker/step/${stepId}/quiz/submit`, {
        method: 'POST', body: JSON.stringify({ answers }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journeys'] }),
  })
}

export function useRecalculateJourney() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (journeyId: number) =>
      apiRequest(`/api/tracker/journey/${journeyId}/recalculate`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journeys'] })
      queryClient.invalidateQueries({ queryKey: ['competency-history'] })
    },
  })
}
```

`frontend/src/api/github.ts` (extended in Task 7 — do not remove existing exports there):

```ts
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'

interface SyncGithubResponse {
  matched_skills: string[]
  evidence_count: number
}

export function useSyncGithub() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (username: string) =>
      apiRequest<SyncGithubResponse>('/api/github/sync', {
        method: 'POST', body: JSON.stringify({ username }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journeys'] }),
  })
}
```

- [ ] **Step 2: Write the failing CompetencyChart test**

`frontend/src/components/CompetencyChart.test.tsx`:

```tsx
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
    expect(screen.getByText(/Initial resume estimate/)).toBeInTheDocument()
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
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `npm run test -- CompetencyChart.test.tsx`
Expected: FAIL — `./CompetencyChart` does not exist.

- [ ] **Step 4: Implement CompetencyChart**

`frontend/src/components/CompetencyChart.tsx`:

```tsx
import { useState } from 'react'
import type { CompetencyHistory } from '../api/types'

export default function CompetencyChart({ historyData, skillNames }: {
  historyData: CompetencyHistory
  skillNames: Record<string, string>
}) {
  const [selectedSkill, setSelectedSkill] = useState('')

  const skillIds = Object.keys(historyData || {})
  if (skillIds.length === 0) return null

  const activeSkill = selectedSkill || skillIds[0]
  const data = historyData[activeSkill] || []

  const width = 500
  const height = 200
  const pad = 30

  const mapY = (val: number) => height - pad - ((val - 1) / 9) * (height - 2 * pad)
  const minTime = data.length > 0 ? new Date(data[0].recorded_at).getTime() : 0
  const maxTime = data.length > 0 ? new Date(data[data.length - 1].recorded_at).getTime() : 0
  const timeRange = maxTime - minTime || 1
  const mapX = (time: number) => pad + ((time - minTime) / timeRange) * (width - 2 * pad)

  const points = data.map((d) => `${mapX(new Date(d.recorded_at).getTime())},${mapY(d.depth_score)}`).join(' ')

  return (
    <div className="panel" style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Competency Growth</h2>
        <select value={activeSkill} onChange={(e) => setSelectedSkill(e.target.value)} className="input-field">
          {skillIds.map((id) => <option key={id} value={id}>{skillNames[id] || id}</option>)}
        </select>
      </div>
      {data.length > 0 && (
        <>
          <svg width="100%" viewBox={`0 0 ${width} ${height}`} style={{ background: '#f8f9fa', borderRadius: '8px', marginTop: '1rem' }}>
            {[1, 5, 10].map((val) => (
              <g key={val}>
                <line x1={pad} y1={mapY(val)} x2={width - pad} y2={mapY(val)} stroke="#ddd" strokeDasharray="4 4" />
                <text x={pad - 5} y={mapY(val) + 4} fontSize="10" textAnchor="end" fill="#666">{val}</text>
              </g>
            ))}
            <polyline points={points} fill="none" stroke="#007bff" strokeWidth="2" />
            {data.map((d, i) => {
              const cx = mapX(new Date(d.recorded_at).getTime())
              const cy = mapY(d.depth_score)
              return (
                <g key={i}>
                  <circle cx={cx} cy={cy} r="4" fill="#007bff" />
                  <title>Depth: {d.depth_score}&#10;{d.rationale}</title>
                </g>
              )
            })}
          </svg>
          <div style={{ marginTop: '0.5rem' }} className="hint">
            Latest assessment: {data[data.length - 1].rationale}
          </div>
        </>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `npm run test -- CompetencyChart.test.tsx`
Expected: 3 tests PASS.

- [ ] **Step 6: Implement QuizModal**

`frontend/src/components/QuizModal.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { useGenerateQuiz, useSubmitQuiz } from '../api/tracker'
import type { QuizQuestion, TrackerStep } from '../api/types'

export default function QuizModal({ step, onClose, onScored }: {
  step: TrackerStep
  onClose: () => void
  onScored: (score: number) => void
}) {
  const [questions, setQuestions] = useState<QuizQuestion[] | null>(null)
  const [answers, setAnswers] = useState<Record<number, number>>({})
  const [error, setError] = useState('')
  const generateQuiz = useGenerateQuiz()
  const submitQuiz = useSubmitQuiz()

  useEffect(() => {
    generateQuiz.mutate(step.id, {
      onSuccess: (d) => setQuestions(d.questions),
      onError: (e) => setError(e instanceof Error ? e.message : String(e)),
    })
    // step.id is stable for the lifetime of this modal; re-running on every
    // generateQuiz identity change would re-request a fresh quiz on rerender.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step.id])

  const submit = async () => {
    if (!questions) return
    setError('')
    try {
      const orderedAnswers = questions.map((_, i) => answers[i])
      const { score } = await submitQuiz.mutateAsync({ stepId: step.id, answers: orderedAnswers })
      onScored(score)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  return (
    <div className="card" style={{ maxWidth: 600, margin: '2rem auto' }}>
      <h2>Quiz: {step.skill_name}</h2>
      {generateQuiz.isPending && <p>Generating questions...</p>}
      {error && <div className="error-box">{error}</div>}
      {questions && questions.map((q, i) => (
        <div key={i} style={{ marginBottom: '1rem' }}>
          <p><strong>{i + 1}. {q.question}</strong></p>
          {q.options.map((opt, oi) => (
            <label key={oi} style={{ display: 'block', marginLeft: '1rem' }}>
              <input type="radio" name={`q${i}`} checked={answers[i] === oi}
                     onChange={() => setAnswers({ ...answers, [i]: oi })} /> {opt}
            </label>
          ))}
        </div>
      ))}
      {questions && (
        <button className="primary-button" onClick={submit}
                disabled={submitQuiz.isPending || Object.keys(answers).length !== questions.length}>
          {submitQuiz.isPending ? 'Submitting...' : 'Submit'}
        </button>
      )}
      <button className="secondary-button" style={{ marginLeft: '0.5rem' }} onClick={onClose}>Cancel</button>
    </div>
  )
}
```

- [ ] **Step 7: Write the failing StepTracker test**

`frontend/src/components/StepTracker.test.tsx`:

```tsx
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
```

- [ ] **Step 8: Run the test to verify it fails**

Run: `npm run test -- StepTracker.test.tsx`
Expected: FAIL — `./StepTracker` does not exist.

- [ ] **Step 9: Implement StepTracker with the mobile-overflow and touch-target fixes**

`frontend/src/components/StepTracker.tsx`:

```tsx
import { useEffect, useRef, useState } from 'react'
import { useRecordProgress } from '../api/tracker'
import type { TrackerStep } from '../api/types'
import QuizModal from './QuizModal'

export default function StepTracker({ step, hoursPerWeek }: {
  step: TrackerStep
  hoursPerWeek: number
}) {
  const [running, setRunning] = useState(false)
  const [elapsedSec, setElapsedSec] = useState(0)
  const [quizOpen, setQuizOpen] = useState(false)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const recordProgress = useRecordProgress()

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000)
    } else if (intervalRef.current) {
      clearInterval(intervalRef.current)
    }
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [running])

  const stopAndSave = async () => {
    setRunning(false)
    if (elapsedSec > 0) {
      const minutes = Math.max(1, Math.round(elapsedSec / 60))
      await recordProgress.mutateAsync({ stepId: step.id, update: { minutes_delta: minutes } })
    }
    setElapsedSec(0)
  }

  const rateConfidence = (rating: number) => {
    recordProgress.mutate({ stepId: step.id, update: { confidence_rating: rating } })
  }

  const budgetMinutes = step.estimated_weeks * (hoursPerWeek || 10) * 60
  const pct = Math.min(100, Math.round(((step.time_spent_minutes || 0) / Math.max(budgetMinutes, 1)) * 100))

  return (
    <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
        {!running ? (
          <button className="secondary-button" onClick={() => setRunning(true)}>▶ Start timer</button>
        ) : (
          <button className="secondary-button" onClick={stopAndSave}>⏸ Stop ({Math.floor(elapsedSec / 60)}m{elapsedSec % 60}s)</button>
        )}
        <span className="hint">{step.time_spent_minutes || 0}m logged · {pct}% of budget</span>
      </div>

      <div className="confidence-row">
        <span className="hint">Confidence:</span>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} className={`secondary-button confidence-btn ${step.confidence_rating === n ? 'active' : ''}`}
                  onClick={() => rateConfidence(n)}>{n}</button>
        ))}
      </div>

      <div>
        <button className="primary-button" onClick={() => setQuizOpen(true)}>Take Quiz</button>
        {step.quiz_score != null && <span className="hint" style={{ marginLeft: '0.5rem' }}>Last score: {step.quiz_score}%</span>}
      </div>

      {step.github_evidence.length > 0 && (
        <div className="hint">
          ✓ GitHub evidence: {step.github_evidence.map((e) => e.repo_name).join(', ')}
        </div>
      )}

      {quizOpen && (
        <QuizModal step={step} onClose={() => setQuizOpen(false)}
                   onScored={(score) => {
                     recordProgress.mutate({ stepId: step.id, update: { quiz_score: score } })
                     setQuizOpen(false)
                   }} />
      )}
    </div>
  )
}
```

Add the mobile-overflow + touch-target fix to `frontend/src/styles/index.css`:

```css

/* Confidence-rating row (StepTracker) — must wrap at narrow widths instead
   of overflowing horizontally, and each button needs a touch-friendly
   (~44px) target instead of the old 4px/10px padding. */
.confidence-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}

.confidence-btn {
  padding: 10px 16px;
  min-width: 44px;
  min-height: 44px;
}
```

- [ ] **Step 10: Run the test to verify it passes**

Run: `npm run test -- StepTracker.test.tsx`
Expected: 2 tests PASS.

- [ ] **Step 11: Write the failing GithubConnect test**

`frontend/src/components/GithubConnect.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import GithubConnect from './GithubConnect'

function renderConnect() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <GithubConnect />
    </QueryClientProvider>
  )
}

describe('GithubConnect', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('shows a match summary after a successful sync', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ({ matched_skills: ['python', 'html-css'], evidence_count: 3 }),
    } as Response))

    renderConnect()
    fireEvent.change(screen.getByPlaceholderText('GitHub username'), { target: { value: 'octocat' } })
    fireEvent.click(screen.getByText('Sync'))

    await waitFor(() => expect(screen.getByText(/Matched 2 skill\(s\) from 3 repo entries/)).toBeInTheDocument())
  })
})
```

- [ ] **Step 12: Run the test to verify it fails, then implement GithubConnect**

Run: `npm run test -- GithubConnect.test.tsx` — Expected: FAIL.

`frontend/src/components/GithubConnect.tsx`:

```tsx
import { useState } from 'react'
import { useSyncGithub } from '../api/github'

export default function GithubConnect() {
  const [username, setUsername] = useState('')
  const [status, setStatus] = useState('')
  const syncGithub = useSyncGithub()

  const sync = () => {
    if (!username.trim()) return
    setStatus('Syncing...')
    syncGithub.mutate(username.trim(), {
      onSuccess: (res) => setStatus(`Matched ${res.matched_skills.length} skill(s) from ${res.evidence_count} repo entries.`),
      onError: (e) => setStatus(e instanceof Error ? e.message : String(e)),
    })
  }

  return (
    <div className="panel" style={{ marginBottom: '1.5rem' }}>
      <h2>Connect GitHub</h2>
      <p className="hint">We read your public repos' languages as evidence you've practiced a skill. No login required.</p>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input className="input-field" placeholder="GitHub username" value={username}
               onChange={(e) => setUsername(e.target.value)} style={{ maxWidth: 300 }} />
        <button className="primary-button" onClick={sync}>Sync</button>
      </div>
      {status && <p className="hint">{status}</p>}
    </div>
  )
}
```

Run: `npm run test -- GithubConnect.test.tsx` — Expected: PASS.

- [ ] **Step 13: Replace the TrackerPage placeholder**

`frontend/src/routes/TrackerPage.tsx`:

```tsx
import { useState } from 'react'
import { useCompetencyHistory, useJourneys, useRecalculateJourney } from '../api/tracker'
import GithubConnect from '../components/GithubConnect'
import CompetencyChart from '../components/CompetencyChart'
import StepTracker from '../components/StepTracker'

export default function TrackerPage() {
  const { data: journeys, isLoading, error } = useJourneys()
  const { data: historyData } = useCompetencyHistory()
  const recalculate = useRecalculateJourney()
  const [recalculatingId, setRecalculatingId] = useState<number | null>(null)

  if (isLoading) return <div>Loading journeys...</div>
  if (error) return <div className="error-box">{error instanceof Error ? error.message : String(error)}</div>

  const skillNames: Record<string, string> = {}
  journeys?.forEach((j) => j.steps.forEach((s) => { skillNames[s.skill_id] = s.skill_name }))

  const runRecalculate = async (journeyId: number) => {
    setRecalculatingId(journeyId)
    try {
      await recalculate.mutateAsync(journeyId)
    } catch (e) {
      alert('Recalculate failed: ' + (e instanceof Error ? e.message : String(e)))
    } finally {
      setRecalculatingId(null)
    }
  }

  return (
    <div className="tracker">
      <GithubConnect />
      <CompetencyChart historyData={historyData ?? {}} skillNames={skillNames} />
      {journeys?.length === 0 && <div>No learning paths generated yet. Go to Generate Path!</div>}
      {journeys?.map((j) => {
        const hasStruggling = j.steps.some((s) => s.status === 'struggling')
        return (
          <div key={j.id} className="panel" style={{ marginBottom: '2rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h2>Target Role: {j.target_role}</h2>
                <p className="hint">Created At: {new Date(j.created_at).toLocaleString()}</p>
              </div>
              {hasStruggling && (
                <button className="primary-button" disabled={recalculatingId === j.id}
                        onClick={() => runRecalculate(j.id)}>
                  {recalculatingId === j.id ? 'Recalculating...' : 'Recalculate Sub-Path'}
                </button>
              )}
            </div>
            <div className="timeline">
              {j.steps.map((s) => (
                <div className={`tstep ${s.status === 'completed' ? 'done' : s.status === 'struggling' ? 'warn' : ''}`} key={s.id}>
                  <h3 style={{ margin: 0 }}>
                    {s.order}. {s.skill_name} <span className="weeks">{s.estimated_weeks} wk</span>
                    <span className="hint" style={{ marginLeft: '0.5rem' }}>({s.status})</span>
                  </h3>
                  <p>{s.objective}</p>
                  <p className="milestone">🏁 {s.milestone}</p>
                  {s.resources.length > 0 && (
                    <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                      {s.resources.map((r) => (
                        <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                          📚 {r.title} — {r.provider} {r.free ? '(free)' : ''}
                        </a>
                      ))}
                    </div>
                  )}
                  <StepTracker step={s} hoursPerWeek={j.hours_per_week} />
                </div>
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 14: Remove the old component and verify**

```bash
git rm frontend/src/components/LearningTracker.jsx
```

Run: `npm run typecheck && npm run test && npm run build`
Expected: all pass.

- [ ] **Step 15: Commit**

```bash
git add frontend/src/api/tracker.ts frontend/src/api/github.ts frontend/src/components/CompetencyChart.tsx frontend/src/components/CompetencyChart.test.tsx frontend/src/components/QuizModal.tsx frontend/src/components/StepTracker.tsx frontend/src/components/StepTracker.test.tsx frontend/src/components/GithubConnect.tsx frontend/src/components/GithubConnect.test.tsx frontend/src/routes/TrackerPage.tsx frontend/src/styles/index.css
git commit -m "feat(frontend): port Learning Tracker, fix mobile overflow and confidence-button touch targets"
```

---

### Task 6: Backend — remember analyzed repos, fix GitHub-evidence duplication

**Files:**
- Modify: `backend/app/db/models.py` (add `AnalyzedRepo`)
- Modify: `backend/app/db/crud.py` (add `upsert_analyzed_repo`, `get_analyzed_repos`)
- Modify: `backend/app/providers/github.py` (dedup fix in `map_languages_to_evidence`)
- Modify: `backend/app/main.py` (upsert on analyze; add `GET /api/github/repos`)
- Test: `backend/tests/test_analyzed_repos.py` (new)
- Modify: `backend/tests/test_github_provider.py` (add dedup test)

**Interfaces:**
- Produces: `models.AnalyzedRepo` (columns: `id, user_id, username, repo_name, file_count, analyzed_at`), `crud.upsert_analyzed_repo(db, user_id, username, repo_name, file_count)`, `crud.get_analyzed_repos(db, user_id) -> list[AnalyzedRepo]`, `GET /api/github/repos` returning `[{username, repo_name, file_count, analyzed_at}]` ordered most-recent-first — this is what Task 7's `useAnalyzedRepos()` hook consumes.
- No migration statement needed: `AnalyzedRepo` is a brand-new table, and `models.Base.metadata.create_all()` (already called in `main.py`'s lifespan) creates it automatically.

- [ ] **Step 1: Write the failing tests**

`backend/tests/test_analyzed_repos.py`:

```python
"""Analyzed-repo memory: upsert on re-analyze, not duplicate rows."""
from app.db import crud, database, models


def _db():
    engine = database.create_engine("sqlite:///:memory:")
    models.Base.metadata.create_all(bind=engine)
    Session = database.sessionmaker(bind=engine)
    return Session()


def _make_user(db, email="t@example.com"):
    user = models.User(email=email, hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_upsert_inserts_new_repo():
    db = _db()
    user = _make_user(db)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "Hello-World", file_count=12)

    repos = crud.get_analyzed_repos(db, user.id)
    assert len(repos) == 1
    assert repos[0].username == "octocat"
    assert repos[0].repo_name == "Hello-World"
    assert repos[0].file_count == 12


def test_upsert_updates_existing_repo_instead_of_duplicating():
    db = _db()
    user = _make_user(db)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "Hello-World", file_count=12)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "Hello-World", file_count=20)

    repos = crud.get_analyzed_repos(db, user.id)
    assert len(repos) == 1
    assert repos[0].file_count == 20


def test_get_analyzed_repos_scoped_to_user():
    db = _db()
    user_a = _make_user(db, "a@example.com")
    user_b = _make_user(db, "b@example.com")

    crud.upsert_analyzed_repo(db, user_a.id, "octocat", "Hello-World", file_count=1)
    crud.upsert_analyzed_repo(db, user_b.id, "torvalds", "linux", file_count=1)

    assert [r.repo_name for r in crud.get_analyzed_repos(db, user_a.id)] == ["Hello-World"]
    assert [r.repo_name for r in crud.get_analyzed_repos(db, user_b.id)] == ["linux"]


def test_get_analyzed_repos_orders_most_recent_first():
    db = _db()
    user = _make_user(db)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "first-repo", file_count=1)
    crud.upsert_analyzed_repo(db, user.id, "octocat", "second-repo", file_count=1)

    repos = crud.get_analyzed_repos(db, user.id)
    assert [r.repo_name for r in repos] == ["second-repo", "first-repo"]
```

Add to `backend/tests/test_github_provider.py` (append, keeping existing imports):

```python
def test_map_languages_dedupes_same_skill_from_multiple_languages_in_one_repo():
    # GitHub reports HTML and CSS as separate languages that both map to the
    # taxonomy's single "html-css" skill — a repo with both must contribute
    # only one evidence row for that skill, not two.
    languages = {
        "HTML": [{"repo_name": "portfolio-site", "last_pushed_at": "2026-07-01T00:00:00Z"}],
        "CSS": [{"repo_name": "portfolio-site", "last_pushed_at": "2026-07-01T00:00:00Z"}],
    }
    rows = map_languages_to_evidence(languages)
    matching = [r for r in rows if r["repo_name"] == "portfolio-site"]
    assert len(matching) == 1
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_analyzed_repos.py tests/test_github_provider.py -v`
Expected: `test_analyzed_repos.py` fails with `AttributeError: module 'app.db.crud' has no attribute 'upsert_analyzed_repo'`; the new dedup test in `test_github_provider.py` fails with two rows returned instead of one.

- [ ] **Step 3: Add the `AnalyzedRepo` model**

Add to `backend/app/db/models.py` (after `CompetencyHistory`):

```python
class AnalyzedRepo(Base):
    __tablename__ = "analyzed_repos"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    username = Column(String)
    repo_name = Column(String)
    file_count = Column(Integer, default=0)
    analyzed_at = Column(DateTime, default=datetime.datetime.utcnow)
```

- [ ] **Step 4: Add the crud functions**

Add `import datetime` to the top of `backend/app/db/crud.py`, then append:

```python
def upsert_analyzed_repo(db: Session, user_id: int, username: str, repo_name: str,
                         file_count: int) -> models.AnalyzedRepo:
    """Record that this user has analyzed this repo — update the existing row
    if they've analyzed it before, insert otherwise, so re-submitting the same
    repo is recognized instead of silently re-downloading with no memory of
    the prior run."""
    existing = (db.query(models.AnalyzedRepo)
                .filter(models.AnalyzedRepo.user_id == user_id,
                        models.AnalyzedRepo.username == username,
                        models.AnalyzedRepo.repo_name == repo_name).first())
    if existing:
        existing.file_count = file_count
        existing.analyzed_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(existing)
        return existing
    db_repo = models.AnalyzedRepo(user_id=user_id, username=username,
                                  repo_name=repo_name, file_count=file_count)
    db.add(db_repo)
    db.commit()
    db.refresh(db_repo)
    return db_repo


def get_analyzed_repos(db: Session, user_id: int) -> list[models.AnalyzedRepo]:
    return (db.query(models.AnalyzedRepo)
            .filter(models.AnalyzedRepo.user_id == user_id)
            .order_by(models.AnalyzedRepo.analyzed_at.desc()).all())
```

- [ ] **Step 5: Fix the GitHub-evidence duplication in `map_languages_to_evidence`**

In `backend/app/providers/github.py`, replace the function body:

```python
def map_languages_to_evidence(languages: dict[str, list[dict]],
                              confidence_floor: float = EVIDENCE_CONFIDENCE_FLOOR) -> list[dict]:
    """GitHub language name -> taxonomy skill via match_mention, dropping
    matches below confidence_floor. Returns evidence rows with
    last_pushed_at still as the raw ISO string from GitHub (caller converts
    to a datetime for storage).

    A repo can report multiple languages that map to the same taxonomy skill
    (GitHub lists "HTML" and "CSS" separately, both -> html-css) — dedup by
    (skill_id, repo_name) so one repo contributes at most one evidence row
    per skill instead of one per matching language.
    """
    evidence_rows = []
    seen: set[tuple[str, str]] = set()
    for language, repos in languages.items():
        hit = match_mention(language)
        if not hit or hit[1] < confidence_floor:
            continue
        skill_id = hit[0]
        for repo in repos:
            key = (skill_id, repo["repo_name"])
            if key in seen:
                continue
            seen.add(key)
            evidence_rows.append({
                "skill_id": skill_id, "repo_name": repo["repo_name"],
                "repo_language": language, "last_pushed_at": repo["last_pushed_at"],
            })
    return evidence_rows
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_analyzed_repos.py tests/test_github_provider.py -v`
Expected: all PASS.

- [ ] **Step 7: Wire the endpoint changes into `main.py`**

In the `analyze_repo` function (`backend/app/main.py`), replace the final two lines:

```python
    return {"message": "Analyzed successfully", "files_processed": len(files)}
```

with:

```python
    crud.upsert_analyzed_repo(db, current_user.id, username, repo_name, len(files))
    return {"message": "Analyzed successfully", "files_processed": len(files)}
```

Add a new endpoint directly after `chat_repo`:

```python
@app.get("/api/github/repos")
def list_analyzed_repos(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    current_user = get_current_user(token, db)
    repos = crud.get_analyzed_repos(db, current_user.id)
    return [
        {
            "username": r.username,
            "repo_name": r.repo_name,
            "file_count": r.file_count,
            "analyzed_at": r.analyzed_at.isoformat(),
        }
        for r in repos
    ]
```

- [ ] **Step 8: Run the full backend test suite**

Run: `cd backend && python -m pytest -v`
Expected: all tests PASS (no regressions in the existing 38+).

- [ ] **Step 9: Commit**

```bash
git add backend/app/db/models.py backend/app/db/crud.py backend/app/providers/github.py backend/app/main.py backend/tests/test_analyzed_repos.py backend/tests/test_github_provider.py
git commit -m "fix(backend): remember analyzed GitHub repos, dedup evidence rows per repo"
```

---

### Task 7: RepoAnalysisPage (github hooks completed, analyzed-repos memory in the UI)

**Files:**
- Modify: `frontend/src/api/github.ts` (add `useAnalyzedRepos`, `useAnalyzeRepo`, `useChatRepo`)
- Create: `frontend/src/routes/RepoAnalysisPage.tsx` (replace placeholder)
- Create: `frontend/src/routes/RepoAnalysisPage.test.tsx`
- Delete: `frontend/src/components/RepoChat.jsx`
- Delete: `frontend/src/api.js`

**Interfaces:**
- Consumes: `AnalyzedRepo` type (Task 2), `GET /api/github/repos` (Task 6).
- Produces: nothing further downstream — this is the last data-layer task.

- [ ] **Step 1: Extend `github.ts`**

Modify `frontend/src/api/github.ts` to the full file (adds three hooks, keeps `useSyncGithub` from Task 5):

```ts
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { AnalyzedRepo } from './types'

interface SyncGithubResponse {
  matched_skills: string[]
  evidence_count: number
}

export function useSyncGithub() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (username: string) =>
      apiRequest<SyncGithubResponse>('/api/github/sync', {
        method: 'POST', body: JSON.stringify({ username }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journeys'] }),
  })
}

export function useAnalyzedRepos() {
  return useQuery({
    queryKey: ['analyzed-repos'],
    queryFn: () => apiRequest<AnalyzedRepo[]>('/api/github/repos'),
  })
}

interface AnalyzeRepoResponse {
  message: string
  files_processed: number
}

export function useAnalyzeRepo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ username, repoName }: { username: string; repoName: string }) =>
      apiRequest<AnalyzeRepoResponse>(
        `/api/github/repo/${encodeURIComponent(username)}/${encodeURIComponent(repoName)}/analyze`,
        { method: 'POST' }
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['analyzed-repos'] }),
  })
}

interface ChatRepoResponse {
  answer: string
}

export function useChatRepo() {
  return useMutation({
    mutationFn: ({ username, repoName, query }: { username: string; repoName: string; query: string }) =>
      apiRequest<ChatRepoResponse>(
        `/api/github/repo/${encodeURIComponent(username)}/${encodeURIComponent(repoName)}/chat`,
        { method: 'POST', body: JSON.stringify({ query }) }
      ),
  })
}
```

- [ ] **Step 2: Write the failing RepoAnalysisPage test**

`frontend/src/routes/RepoAnalysisPage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import RepoAnalysisPage from './RepoAnalysisPage'

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <RepoAnalysisPage />
    </QueryClientProvider>
  )
}

describe('RepoAnalysisPage', () => {
  beforeEach(() => vi.unstubAllGlobals())

  it('lists previously analyzed repos so re-analysis is not silent', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: async () => ([{ username: 'octocat', repo_name: 'Hello-World', file_count: 5, analyzed_at: '2026-08-20T10:00:00Z' }]),
    } as Response))

    renderPage()

    await waitFor(() => expect(screen.getByText('octocat/Hello-World')).toBeInTheDocument())
  })
})
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `npm run test -- RepoAnalysisPage.test.tsx`
Expected: FAIL — the placeholder page has no analyzed-repos list.

- [ ] **Step 4: Implement RepoAnalysisPage**

`frontend/src/routes/RepoAnalysisPage.tsx`:

```tsx
import { useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAnalyzedRepos, useAnalyzeRepo, useChatRepo } from '../api/github'

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

export default function RepoAnalysisPage() {
  const [username, setUsername] = useState('')
  const [repo, setRepo] = useState('')
  const [status, setStatus] = useState('')
  const [analyzed, setAnalyzed] = useState(false)
  const [query, setQuery] = useState('')
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])

  const { data: analyzedRepos } = useAnalyzedRepos()
  const analyzeRepo = useAnalyzeRepo()
  const chatRepo = useChatRepo()

  const handleAnalyze = () => {
    if (!username || !repo) return
    setStatus('Downloading and analyzing repository... This might take a minute depending on repo size.')
    setAnalyzed(false)
    analyzeRepo.mutate({ username, repoName: repo }, {
      onSuccess: (res) => {
        setStatus(`Success! Indexed ${res.files_processed} files.`)
        setAnalyzed(true)
        setChatHistory([])
      },
      onError: (e) => setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`),
    })
  }

  const openFromHistory = (u: string, r: string) => {
    setUsername(u)
    setRepo(r)
    setAnalyzed(true)
    setChatHistory([])
    setStatus(`Reusing previous analysis of ${u}/${r} — ask a question below, or hit Analyze to re-sync.`)
  }

  const handleChat = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    const userMsg = query
    setChatHistory((prev) => [...prev, { role: 'user', text: userMsg }])
    setQuery('')

    chatRepo.mutate({ username, repoName: repo, query: userMsg }, {
      onSuccess: (res) => setChatHistory((prev) => [...prev, { role: 'assistant', text: res.answer }]),
      onError: (e) => setChatHistory((prev) => [...prev, { role: 'assistant', text: `Error: ${e instanceof Error ? e.message : String(e)}` }]),
    })
  }

  return (
    <div className="panel" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2>GitHub Repository Analysis</h2>
      <p>Enter a public GitHub repository to download its source code and chat with it locally using AI RAG.</p>

      {analyzedRepos && analyzedRepos.length > 0 && (
        <div className="hint" style={{ marginBottom: '1rem' }}>
          <strong>Already analyzed:</strong>
          <ul>
            {analyzedRepos.map((r) => (
              <li key={`${r.username}/${r.repo_name}`}>
                <a href="#" onClick={(e) => { e.preventDefault(); openFromHistory(r.username, r.repo_name) }}>
                  {r.username}/{r.repo_name}
                </a>{' '}
                — {r.file_count} files, analyzed {new Date(r.analyzed_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '1rem' }}>
        <input className="input-field" placeholder="GitHub Username (e.g. torvalds)" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input className="input-field" placeholder="Repository Name (e.g. linux)" value={repo} onChange={(e) => setRepo(e.target.value)} />
        <button className="primary-button" onClick={handleAnalyze}>Analyze</button>
      </div>

      {status && <div className="hint" style={{ marginBottom: '1rem' }}>{status}</div>}

      {analyzed && (
        <div className="chat-interface" style={{ border: '1px solid #ccc', borderRadius: '8px', padding: '1rem' }}>
          <div className="chat-history" style={{ maxHeight: '400px', overflowY: 'auto', marginBottom: '1rem' }}>
            {chatHistory.length === 0 && <p className="hint">Ask a question about the code!</p>}
            {chatHistory.map((msg, i) => (
              <div key={i} style={{ marginBottom: '1rem', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                <div style={{
                  display: 'inline-block', padding: '0.5rem 1rem', borderRadius: '8px',
                  background: msg.role === 'user' ? '#4f46e5' : '#f1f1f1',
                  color: msg.role === 'user' ? 'white' : 'black',
                  whiteSpace: 'pre-wrap', textAlign: 'left',
                }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ ...props }) => <p style={{ margin: '0 0 0.5rem 0' }} {...props} />,
                      ul: ({ ...props }) => <ul style={{ margin: '0 0 0.5rem 1rem', padding: 0 }} {...props} />,
                      ol: ({ ...props }) => <ol style={{ margin: '0 0 0.5rem 1rem', padding: 0 }} {...props} />,
                      li: ({ ...props }) => <li style={{ marginBottom: '0.25rem' }} {...props} />,
                      code: ({ className, ...props }) =>
                        className?.includes('language-')
                          ? <code style={{ display: 'block', background: 'rgba(0,0,0,0.1)', padding: '0.5rem', borderRadius: '5px', overflowX: 'auto' }} className={className} {...props} />
                          : <code style={{ background: 'rgba(0,0,0,0.1)', padding: '0.1rem 0.3rem', borderRadius: '3px' }} {...props} />,
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            {chatRepo.isPending && <div className="hint">Thinking...</div>}
          </div>
          <form onSubmit={handleChat} style={{ display: 'flex', gap: '10px' }}>
            <input
              className="input-field" style={{ flex: 1 }} value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Where is the database connection setup?"
              disabled={chatRepo.isPending}
            />
            <button className="primary-button" type="submit" disabled={chatRepo.isPending || !query.trim()}>Send</button>
          </form>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `npm run test -- RepoAnalysisPage.test.tsx`
Expected: PASS.

- [ ] **Step 6: Remove the last old files**

```bash
git rm frontend/src/components/RepoChat.jsx frontend/src/api.js
```

- [ ] **Step 7: Full verification**

Run: `npm run typecheck && npm run test && npm run build`
Expected: all pass. Confirm no `.jsx` files remain: `ls frontend/src/**/*.jsx` (or Windows equivalent) should list nothing.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/api/github.ts frontend/src/routes/RepoAnalysisPage.tsx frontend/src/routes/RepoAnalysisPage.test.tsx
git commit -m "feat(frontend): port GitHub repo chat, show already-analyzed repos"
```

---

### Task 8: Final verification and cleanup sweep

**Files:** none expected — this task only verifies and, if the sweep finds anything, removes stragglers.

**Interfaces:** none (terminal task).

- [ ] **Step 1: Confirm no legacy files remain**

Run: `find frontend/src -name "*.jsx"` (or `Get-ChildItem -Recurse -Filter *.jsx frontend/src` in PowerShell)
Expected: no output. If any file appears, delete it and its now-orphaned imports (there should be none left, since every `.jsx` consumer was ported in Tasks 3-7).

- [ ] **Step 2: Full frontend verification**

Run: `cd frontend && npm run typecheck` — Expected: no errors.
Run: `npm run test` — Expected: every test from Tasks 1-7 PASSes.
Run: `npm run build` — Expected: succeeds, no warnings about unresolved imports.

- [ ] **Step 3: Full backend verification**

Run: `cd backend && python -m pytest -v`
Expected: all tests PASS, including the two new ones from Task 6.

- [ ] **Step 4: Manual smoke test in the browser**

Start the backend (`uvicorn app.main:app --port 8080`, no `--reload`) and the frontend (`npm run dev`), then in the Browser pane:
1. Register/login → confirm redirect to `/generate`.
2. Refresh the page on `/tracker` → confirm it stays on `/tracker` (not bounced to step 0 of a wizard) — this is the "remembers navigation" fix.
3. Run the Generate Path wizard once with the sample profile.
4. On `/repo-analysis`, analyze `octocat/Hello-World`, then reload the page → confirm "Already analyzed" now lists it (the "remembers analyzed repos" fix). Analyze it again → confirm it upserts (still one entry, updated timestamp) rather than erroring or duplicating.
5. Resize to a 375px-wide viewport on `/tracker` and `/generate` → confirm the nav row and any confidence-rating row wrap instead of causing horizontal scroll.
6. Sync a GitHub account that has both HTML and CSS in one repo (or inspect a returned `matched_skills`/evidence list) → confirm only one evidence entry per skill per repo.

- [ ] **Step 5: Commit if the sweep found anything to remove; otherwise no commit is needed**

If Step 1 found stragglers:

```bash
git add -A
git commit -m "chore(frontend): remove remaining legacy JSX files"
```
