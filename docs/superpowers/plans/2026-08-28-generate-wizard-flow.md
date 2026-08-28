# Generate Wizard Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Generate Path wizard real per-step URLs (`/generate/profile`, `/generate/role`, `/generate/analysis`, `/generate/results`) with `sessionStorage`-backed state so refresh/back-forward keep your place, and replace the resume-upload button+hidden-input with a drop-zone that shows a real upload confirmation and inline errors instead of `alert()`.

**Architecture:** The single `GeneratePage.tsx` with in-memory `step` state is replaced by four sibling route components under `frontend/src/routes/generate/`, plus an index-route resume component, all reading/writing one `sessionStorage` key through a small `wizardStorage.ts` helper (same `try/catch`-guarded idiom `RepoAnalysisPage.tsx` already uses for chat history, just session-scoped). `ProfileForm`, `RolePicker`, `AgentTerminal`, and `Results` keep their existing behavior and are reused unchanged except `ProfileForm` gains one optional prop. `ProfileForm`'s upload interaction is redesigned in place (drop-zone → confirmation card, inline `.error-box` on failure) using only existing CSS tokens.

**Tech Stack:** Same as the rest of the frontend — React 19, TypeScript, react-router-dom v6, TanStack Query v5, Vitest + React Testing Library. No new dependencies.

## Global Constraints

- No backend, `/api/advise`, `/api/extract_pdf`, or agent changes — this is entirely frontend routing/UX.
- `RolePicker`, `AgentTerminal`, and `Results` keep their exact current prop signatures — no changes to those three files.
- `ProfileForm`'s manual-paste textarea, education/hours inputs, sample-profile button, and Continue button keep their current behavior, placeholder text, and button labels unchanged (existing `ProfileForm.test.tsx` cases must keep passing unmodified).
- Wizard state persistence is `sessionStorage` only (cleared when the tab closes) — never `localStorage`, never a backend call.
- Every step page redirects to `/generate/profile` when its own prerequisite state is missing, per the design spec's routing table — not to the immediately-prior step.
- A failed advisor run (the `/generate/analysis` mutation) returns the user to `/generate/role` with the error message shown inline, matching today's `setStep(1)` fallback — this is separate from the missing-prerequisite redirect above.
- Every task must leave `npm run typecheck && npm run test && npm run build` passing (run from `frontend/`).

---

### Task 1: `ProfileForm` drop-zone upload redesign

**Files:**
- Modify: `frontend/src/components/ProfileForm.tsx`
- Modify: `frontend/src/styles/index.css`
- Modify: `frontend/src/components/ProfileForm.test.tsx`

**Interfaces:**
- Consumes: `useExtractPdf()` from `../api/advise` (existing, unchanged).
- Produces: `ProfileForm({ onSubmit, initialValues }: { onSubmit: (values: ProfileFormValues) => void; initialValues?: ProfileFormValues | null })` — Task 3's `ProfileStepPage` passes `initialValues` by this exact name.

- [ ] **Step 1: Write the failing upload-redesign tests**

Replace the full contents of `frontend/src/components/ProfileForm.test.tsx` with (adds three new cases, keeps the two existing ones untouched):

```tsx
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
```

- [ ] **Step 2: Run the tests to verify the new ones fail**

Run: `npm run test -- ProfileForm.test.tsx`
Expected: the two pre-existing tests PASS; the three new upload tests FAIL (no "Drop your resume PDF here" text exists yet — `alert()` is still used, no confirmation/remove UI exists).

- [ ] **Step 3: Redesign `ProfileForm.tsx`**

Replace the full contents of `frontend/src/components/ProfileForm.tsx` with:

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

export default function ProfileForm({ onSubmit, initialValues }: {
  onSubmit: (values: ProfileFormValues) => void
  initialValues?: ProfileFormValues | null
}) {
  const [text, setText] = useState(initialValues?.resume_text ?? '')
  const [education, setEducation] = useState(initialValues?.education ?? '')
  const [hours, setHours] = useState(initialValues?.hours_per_week ?? 10)
  const [uploadedFileName, setUploadedFileName] = useState('')
  const [uploadedChars, setUploadedChars] = useState(0)
  const [uploadError, setUploadError] = useState('')
  const [dragging, setDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const extractPdf = useExtractPdf()

  const uploadFile = async (file: File) => {
    setUploadError('')
    if (file.type !== 'application/pdf') {
      setUploadError('Please upload a PDF file.')
      return
    }
    try {
      const data = await extractPdf.mutateAsync(file)
      setText(data.text)
      setUploadedFileName(file.name)
      setUploadedChars(data.text.length)
    } catch (err) {
      setUploadError('Failed to extract PDF: ' + (err instanceof Error ? err.message : String(err)))
    }
  }

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (file) uploadFile(file)
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files?.[0]
    if (file) uploadFile(file)
  }

  const removeUpload = () => {
    setUploadedFileName('')
    setUploadedChars(0)
    setUploadError('')
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
      </div>

      {uploadError && <div className="error-box">{uploadError}</div>}

      {uploadedFileName ? (
        <div className="upload-confirm">
          <span>✓ Extracted {uploadedChars.toLocaleString()} characters from {uploadedFileName}.</span>
          <button className="ghost" onClick={removeUpload} style={{ marginTop: 0 }}>Remove</button>
        </div>
      ) : (
        <div
          className={`dropzone ${dragging ? 'dragging' : ''}`}
          onClick={() => fileInputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
        >
          {extractPdf.isPending
            ? 'Extracting text from your resume...'
            : '📄 Drop your resume PDF here, or click to browse'}
        </div>
      )}
      <input
        type="file"
        accept="application/pdf"
        ref={fileInputRef}
        style={{ display: 'none' }}
        onChange={handleFileInput}
      />

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

- [ ] **Step 4: Add the drop-zone/upload-confirmation CSS**

In `frontend/src/styles/index.css`, immediately after the existing `.note { ... }` block (the one right after `.error-box`), add:

```css
/* Resume upload */
.dropzone {
  margin-top: 16px;
  padding: 24px;
  border: 2px dashed var(--panel-border);
  border-radius: 14px;
  background: var(--bg-main);
  color: var(--text-muted);
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s, color 0.15s;
}

.dropzone:hover,
.dropzone.dragging {
  border-color: var(--primary);
  background: var(--primary-light);
  color: var(--primary-hover);
}

.upload-confirm {
  margin-top: 16px;
  padding: 14px 20px;
  border: 1px solid rgba(58, 138, 92, 0.25);
  border-radius: 14px;
  background: var(--success-light);
  color: #1f5c3a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 500;
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npm run test -- ProfileForm.test.tsx`
Expected: all 5 tests PASS.

- [ ] **Step 6: Typecheck and build**

Run: `npm run typecheck && npm run build`
Expected: both succeed with no errors.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ProfileForm.tsx frontend/src/components/ProfileForm.test.tsx frontend/src/styles/index.css
git commit -m "feat(frontend): redesign resume upload as a drop-zone with inline confirmation/errors"
```

---

### Task 2: `wizardStorage` sessionStorage helper

**Files:**
- Create: `frontend/src/routes/generate/wizardStorage.ts`
- Test: `frontend/src/routes/generate/wizardStorage.test.ts`

**Interfaces:**
- Consumes: `ProfileFormValues` from `../../components/ProfileForm` (existing), `AdvisorResult` from `../../api/types` (existing).
- Produces: `WizardState = { profileInput: ProfileFormValues | null, role: string, result: AdvisorResult | null }`, `loadWizardState(): WizardState`, `saveWizardState(partial: Partial<WizardState>): void`, `clearWizardState(): void` — Task 3's four step pages and `GenerateResumePage` call these three functions by these exact names.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/routes/generate/wizardStorage.test.ts`:

```ts
import { beforeEach, describe, expect, it } from 'vitest'
import { clearWizardState, loadWizardState, saveWizardState } from './wizardStorage'

describe('wizardStorage', () => {
  beforeEach(() => sessionStorage.clear())

  it('returns empty state when nothing is saved', () => {
    expect(loadWizardState()).toEqual({ profileInput: null, role: '', result: null })
  })

  it('persists a partial save and merges it with prior state', () => {
    saveWizardState({ role: 'Data Engineer' })
    saveWizardState({ profileInput: { resume_text: 'I know Python', education: '', hours_per_week: 10 } })

    expect(loadWizardState()).toEqual({
      profileInput: { resume_text: 'I know Python', education: '', hours_per_week: 10 },
      role: 'Data Engineer',
      result: null,
    })
  })

  it('clearWizardState removes everything', () => {
    saveWizardState({ role: 'Data Engineer' })
    clearWizardState()

    expect(loadWizardState()).toEqual({ profileInput: null, role: '', result: null })
  })

  it('falls back to empty state on corrupted JSON', () => {
    sessionStorage.setItem('generate-wizard-state', '{not json')
    expect(loadWizardState()).toEqual({ profileInput: null, role: '', result: null })
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm run test -- wizardStorage.test.ts`
Expected: FAIL — `wizardStorage.ts` does not exist yet.

- [ ] **Step 3: Implement `wizardStorage.ts`**

Create `frontend/src/routes/generate/wizardStorage.ts`:

```ts
import type { AdvisorResult } from '../../api/types'
import type { ProfileFormValues } from '../../components/ProfileForm'

const KEY = 'generate-wizard-state'

export interface WizardState {
  profileInput: ProfileFormValues | null
  role: string
  result: AdvisorResult | null
}

const EMPTY_STATE: WizardState = { profileInput: null, role: '', result: null }

export function loadWizardState(): WizardState {
  try {
    const raw = sessionStorage.getItem(KEY)
    return raw ? { ...EMPTY_STATE, ...JSON.parse(raw) } : EMPTY_STATE
  } catch {
    return EMPTY_STATE // sessionStorage unavailable or corrupted — start fresh
  }
}

export function saveWizardState(partial: Partial<WizardState>): void {
  try {
    sessionStorage.setItem(KEY, JSON.stringify({ ...loadWizardState(), ...partial }))
  } catch {
    // sessionStorage unavailable — the wizard still works for this page load
  }
}

export function clearWizardState(): void {
  try {
    sessionStorage.removeItem(KEY)
  } catch {
    // ignore
  }
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `npm run test -- wizardStorage.test.ts`
Expected: all 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/routes/generate/wizardStorage.ts frontend/src/routes/generate/wizardStorage.test.ts
git commit -m "feat(frontend): add sessionStorage-backed wizard state helper"
```

---

### Task 3: Real per-step routes for the Generate wizard

**Files:**
- Create: `frontend/src/routes/generate/WizardSteps.tsx`
- Create: `frontend/src/routes/generate/GenerateResumePage.tsx`
- Create: `frontend/src/routes/generate/ProfileStepPage.tsx`
- Create: `frontend/src/routes/generate/RoleStepPage.tsx`
- Create: `frontend/src/routes/generate/AnalysisStepPage.tsx`
- Create: `frontend/src/routes/generate/ResultsStepPage.tsx`
- Create: `frontend/src/test/fixtures.ts`
- Test: `frontend/src/routes/generate/GenerateResumePage.test.tsx`
- Test: `frontend/src/routes/generate/ProfileStepPage.test.tsx`
- Test: `frontend/src/routes/generate/RoleStepPage.test.tsx`
- Test: `frontend/src/routes/generate/AnalysisStepPage.test.tsx`
- Test: `frontend/src/routes/generate/ResultsStepPage.test.tsx`
- Modify: `frontend/src/main.tsx`
- Delete: `frontend/src/routes/GeneratePage.tsx`

**Interfaces:**
- Consumes: `loadWizardState`/`saveWizardState`/`clearWizardState` from `./wizardStorage` (Task 2); `ProfileForm`'s `initialValues` prop (Task 1); `useRoles`/`useAdvise` from `../../api/advise` (existing); `RolePicker`, `AgentTerminal`, `Results` (existing, unchanged).
- Produces: five default-exported route components (`GenerateResumePage`, `ProfileStepPage`, `RoleStepPage`, `AnalysisStepPage`, `ResultsStepPage`) wired into `main.tsx` under `/generate`, `/generate/profile`, `/generate/role`, `/generate/analysis`, `/generate/results`.

- [ ] **Step 1: Add the shared advisor-result test fixture**

Create `frontend/src/test/fixtures.ts`:

```ts
import type { AdvisorResult } from '../api/types'

export const ADVISOR_RESULT_FIXTURE: AdvisorResult = {
  profile: { raw_text: 'x', skills: [], education: '', interests: [], hours_per_week: 10, target_role: 'Data Engineer' },
  demand: { target_role: 'Data Engineer', postings_analysed: 0, skills: [] },
  gap_report: { target_role: 'Data Engineer', gaps: [], strengths: [] },
  path: null,
  critique: null,
  resume_review: null,
  revisions_used: 0,
  notes: [],
}
```

- [ ] **Step 2: Write the failing `GenerateResumePage` test**

Create `frontend/src/routes/generate/GenerateResumePage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import GenerateResumePage from './GenerateResumePage'
import { saveWizardState } from './wizardStorage'
import { ADVISOR_RESULT_FIXTURE } from '../../test/fixtures'

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/generate']}>
      <Routes>
        <Route path="/generate" element={<GenerateResumePage />} />
        <Route path="/generate/profile" element={<p>Profile Step</p>} />
        <Route path="/generate/role" element={<p>Role Step</p>} />
        <Route path="/generate/results" element={<p>Results Step</p>} />
      </Routes>
    </MemoryRouter>
  )
}

describe('GenerateResumePage', () => {
  beforeEach(() => sessionStorage.clear())

  it('resumes at the profile step when nothing is saved', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('resumes at the role step when a profile is saved but no result yet', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 } })
    renderPage()
    await waitFor(() => expect(screen.getByText('Role Step')).toBeInTheDocument())
  })

  it('resumes at the results step when a result is saved', async () => {
    saveWizardState({ result: ADVISOR_RESULT_FIXTURE })
    renderPage()
    await waitFor(() => expect(screen.getByText('Results Step')).toBeInTheDocument())
  })
})
```

Run: `npm run test -- GenerateResumePage.test.tsx`
Expected: FAIL — `GenerateResumePage.tsx` does not exist yet.

- [ ] **Step 3: Implement `GenerateResumePage` and the shared `WizardSteps` strip**

Create `frontend/src/routes/generate/WizardSteps.tsx` (extracted unchanged from the old `GeneratePage.tsx` step strip, reused by all four step pages below):

```tsx
const STEPS = ['Profile', 'Target role', 'Analysis', 'Learning path']

export default function WizardSteps({ current }: { current: number }) {
  return (
    <div className="steps">
      {STEPS.map((s, i) => (
        <span key={s} className={`step-chip ${i === current ? 'active' : ''} ${i < current ? 'done' : ''}`}>
          {String(i + 1).padStart(2, '0')} {i < current ? '✓ ' : ''}{s}
        </span>
      ))}
    </div>
  )
}
```

Create `frontend/src/routes/generate/GenerateResumePage.tsx`:

```tsx
import { Navigate } from 'react-router-dom'
import { loadWizardState } from './wizardStorage'

export default function GenerateResumePage() {
  const { profileInput, result } = loadWizardState()
  if (result) return <Navigate to="/generate/results" replace />
  if (profileInput) return <Navigate to="/generate/role" replace />
  return <Navigate to="/generate/profile" replace />
}
```

Run: `npm run test -- GenerateResumePage.test.tsx`
Expected: all 3 tests PASS.

- [ ] **Step 4: Write the failing `ProfileStepPage` test**

Create `frontend/src/routes/generate/ProfileStepPage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ProfileStepPage from './ProfileStepPage'
import { loadWizardState } from './wizardStorage'

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/generate/profile']}>
        <Routes>
          <Route path="/generate/profile" element={<ProfileStepPage />} />
          <Route path="/generate/role" element={<p>Role Step</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ProfileStepPage', () => {
  beforeEach(() => sessionStorage.clear())

  it('saves the submitted profile and navigates to the role step', async () => {
    renderPage()
    fireEvent.change(screen.getByPlaceholderText(/Final year CSE student/), { target: { value: 'I know Python' } })
    fireEvent.click(screen.getByText('Continue →'))

    await waitFor(() => expect(screen.getByText('Role Step')).toBeInTheDocument())
    expect(loadWizardState().profileInput).toEqual({ resume_text: 'I know Python', education: '', hours_per_week: 10 })
  })
})
```

Run: `npm run test -- ProfileStepPage.test.tsx`
Expected: FAIL — `ProfileStepPage.tsx` does not exist yet.

- [ ] **Step 5: Implement `ProfileStepPage`**

Create `frontend/src/routes/generate/ProfileStepPage.tsx`:

```tsx
import { useNavigate } from 'react-router-dom'
import ProfileForm, { type ProfileFormValues } from '../../components/ProfileForm'
import WizardSteps from './WizardSteps'
import { loadWizardState, saveWizardState } from './wizardStorage'

export default function ProfileStepPage() {
  const navigate = useNavigate()
  const { profileInput } = loadWizardState()

  const handleSubmit = (values: ProfileFormValues) => {
    saveWizardState({ profileInput: values })
    navigate('/generate/role')
  }

  return (
    <>
      <WizardSteps current={0} />
      <ProfileForm initialValues={profileInput} onSubmit={handleSubmit} />
    </>
  )
}
```

Run: `npm run test -- ProfileStepPage.test.tsx`
Expected: PASS.

- [ ] **Step 6: Write the failing `RoleStepPage` tests**

Create `frontend/src/routes/generate/RoleStepPage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import RoleStepPage from './RoleStepPage'
import { loadWizardState, saveWizardState } from './wizardStorage'

function renderPage(initialEntries: (string | { pathname: string; state?: unknown })[] = ['/generate/role']) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={initialEntries}>
        <Routes>
          <Route path="/generate/profile" element={<p>Profile Step</p>} />
          <Route path="/generate/role" element={<RoleStepPage />} />
          <Route path="/generate/analysis" element={<p>Analysis Step</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('RoleStepPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.unstubAllGlobals()
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true, status: 200, json: async () => ({ roles: ['Data Engineer'] }),
    } as Response))
  })

  it('redirects to the profile step when no profile is saved yet', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('lets you pick a role, persists it, and moves on to analysis', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 } })
    renderPage()

    await waitFor(() => expect(screen.getByText('Data Engineer')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Data Engineer'))
    fireEvent.click(screen.getByText('Run the advisor →'))

    await waitFor(() => expect(screen.getByText('Analysis Step')).toBeInTheDocument())
    expect(loadWizardState().role).toBe('Data Engineer')
  })

  it('shows an inline error passed back from a failed analysis', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 } })
    renderPage([{ pathname: '/generate/role', state: { error: 'boom' } }])

    await waitFor(() => expect(screen.getByText('Advisor failed: boom')).toBeInTheDocument())
  })
})
```

Run: `npm run test -- RoleStepPage.test.tsx`
Expected: FAIL — `RoleStepPage.tsx` does not exist yet.

- [ ] **Step 7: Implement `RoleStepPage`**

Create `frontend/src/routes/generate/RoleStepPage.tsx`:

```tsx
import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useRoles } from '../../api/advise'
import RolePicker from '../../components/RolePicker'
import WizardSteps from './WizardSteps'
import { loadWizardState, saveWizardState } from './wizardStorage'

export default function RoleStepPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { profileInput } = loadWizardState()
  const [role, setRole] = useState(() => loadWizardState().role)
  const { data: rolesData, error: rolesError } = useRoles()
  const adviseError = (location.state as { error?: string } | null)?.error ?? ''

  useEffect(() => {
    if (!profileInput) navigate('/generate/profile', { replace: true })
  }, [profileInput, navigate])

  if (!profileInput) return null

  const handleSelect = (r: string) => {
    setRole(r)
    saveWizardState({ role: r })
  }

  return (
    <>
      <WizardSteps current={1} />
      {adviseError && <div className="error-box">Advisor failed: {adviseError}</div>}
      <RolePicker
        roles={rolesData?.roles ?? []}
        selected={role}
        onSelect={handleSelect}
        onBack={() => navigate('/generate/profile')}
        onAnalyse={() => navigate('/generate/analysis')}
        loadError={rolesError instanceof Error ? rolesError.message : ''}
      />
    </>
  )
}
```

Run: `npm run test -- RoleStepPage.test.tsx`
Expected: all 3 tests PASS.

- [ ] **Step 8: Write the failing `AnalysisStepPage` tests**

Create `frontend/src/routes/generate/AnalysisStepPage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import AnalysisStepPage from './AnalysisStepPage'
import { loadWizardState, saveWizardState } from './wizardStorage'
import { ADVISOR_RESULT_FIXTURE } from '../../test/fixtures'

const mutateAsync = vi.fn()
vi.mock('../../api/advise', () => ({
  useAdvise: () => ({ mutateAsync }),
}))

function renderPage() {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/generate/analysis']}>
        <Routes>
          <Route path="/generate/profile" element={<p>Profile Step</p>} />
          <Route path="/generate/role" element={<p>Role Step</p>} />
          <Route path="/generate/analysis" element={<AnalysisStepPage />} />
          <Route path="/generate/results" element={<p>Results Step</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('AnalysisStepPage', () => {
  beforeEach(() => {
    sessionStorage.clear()
    mutateAsync.mockReset()
  })

  it('redirects to the profile step when the profile or role is missing', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('runs the advisor once on mount and saves the result on success', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 }, role: 'Data Engineer' })
    mutateAsync.mockResolvedValue(ADVISOR_RESULT_FIXTURE)
    renderPage()

    await waitFor(() => expect(screen.getByText('Results Step')).toBeInTheDocument())
    expect(mutateAsync).toHaveBeenCalledTimes(1)
    expect(loadWizardState().result).toEqual(ADVISOR_RESULT_FIXTURE)
  })

  it('returns to the role step with an error message on failure', async () => {
    saveWizardState({ profileInput: { resume_text: 'x', education: '', hours_per_week: 10 }, role: 'Data Engineer' })
    mutateAsync.mockRejectedValue(new Error('advisor exploded'))
    renderPage()

    await waitFor(() => expect(screen.getByText('Role Step')).toBeInTheDocument())
  })
})
```

Run: `npm run test -- AnalysisStepPage.test.tsx`
Expected: FAIL — `AnalysisStepPage.tsx` does not exist yet.

- [ ] **Step 9: Implement `AnalysisStepPage`**

Create `frontend/src/routes/generate/AnalysisStepPage.tsx`:

```tsx
import { useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAdvise } from '../../api/advise'
import AgentTerminal from '../../components/AgentTerminal'
import WizardSteps from './WizardSteps'
import { loadWizardState, saveWizardState } from './wizardStorage'

export default function AnalysisStepPage() {
  const navigate = useNavigate()
  const advise = useAdvise()
  const started = useRef(false)
  const { profileInput, role } = loadWizardState()

  useEffect(() => {
    if (!profileInput || !role) {
      navigate('/generate/profile', { replace: true })
      return
    }
    if (started.current) return // guards against StrictMode's dev-mode double-invoke
    started.current = true

    advise.mutateAsync({ ...profileInput, target_role: role })
      .then((res) => {
        saveWizardState({ result: res })
        navigate('/generate/results')
      })
      .catch((e) => {
        const message = e instanceof Error ? e.message : String(e)
        navigate('/generate/role', { state: { error: message } })
      })
    // Intentionally runs once on mount only — re-running on every render would
    // re-fire the advisor request.
  }, [])

  if (!profileInput || !role) return null

  return (
    <>
      <WizardSteps current={2} />
      <AgentTerminal role={role} />
    </>
  )
}
```

Run: `npm run test -- AnalysisStepPage.test.tsx`
Expected: all 3 tests PASS.

- [ ] **Step 10: Write the failing `ResultsStepPage` tests**

Create `frontend/src/routes/generate/ResultsStepPage.test.tsx`:

```tsx
import { beforeEach, describe, expect, it } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import ResultsStepPage from './ResultsStepPage'
import { loadWizardState, saveWizardState } from './wizardStorage'
import { ADVISOR_RESULT_FIXTURE } from '../../test/fixtures'

function renderPage() {
  render(
    <MemoryRouter initialEntries={['/generate/results']}>
      <Routes>
        <Route path="/generate/profile" element={<p>Profile Step</p>} />
        <Route path="/generate/results" element={<ResultsStepPage />} />
      </Routes>
    </MemoryRouter>
  )
}

describe('ResultsStepPage', () => {
  beforeEach(() => sessionStorage.clear())

  it('redirects to the profile step when there is no result saved', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
  })

  it('renders the results and clears state on restart', async () => {
    saveWizardState({ result: ADVISOR_RESULT_FIXTURE })
    renderPage()

    fireEvent.click(await screen.findByText('↺ Start over'))

    await waitFor(() => expect(screen.getByText('Profile Step')).toBeInTheDocument())
    expect(loadWizardState().result).toBeNull()
  })
})
```

Run: `npm run test -- ResultsStepPage.test.tsx`
Expected: FAIL — `ResultsStepPage.tsx` does not exist yet.

- [ ] **Step 11: Implement `ResultsStepPage`**

Create `frontend/src/routes/generate/ResultsStepPage.tsx`:

```tsx
import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Results from '../../components/Results'
import WizardSteps from './WizardSteps'
import { clearWizardState, loadWizardState } from './wizardStorage'

export default function ResultsStepPage() {
  const navigate = useNavigate()
  const { result } = loadWizardState()

  useEffect(() => {
    if (!result) navigate('/generate/profile', { replace: true })
  }, [result, navigate])

  if (!result) return null

  const restart = () => {
    clearWizardState()
    navigate('/generate/profile')
  }

  return (
    <>
      <WizardSteps current={3} />
      <Results result={result} onRestart={restart} />
    </>
  )
}
```

Run: `npm run test -- ResultsStepPage.test.tsx`
Expected: both tests PASS.

- [ ] **Step 12: Wire the new routes into `main.tsx` and delete the old `GeneratePage`**

Replace the full contents of `frontend/src/main.tsx` with:

```tsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './styles/index.css'
import AppShell from './AppShell'
import RequireAuth from './routes/RequireAuth'
import LoginPage from './routes/LoginPage'
import GenerateResumePage from './routes/generate/GenerateResumePage'
import ProfileStepPage from './routes/generate/ProfileStepPage'
import RoleStepPage from './routes/generate/RoleStepPage'
import AnalysisStepPage from './routes/generate/AnalysisStepPage'
import ResultsStepPage from './routes/generate/ResultsStepPage'
import TrackerPage from './routes/TrackerPage'
import RepoAnalysisPage from './routes/RepoAnalysisPage'
import JobsPage from './routes/JobsPage'

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
            <Route path="generate">
              <Route index element={<GenerateResumePage />} />
              <Route path="profile" element={<ProfileStepPage />} />
              <Route path="role" element={<RoleStepPage />} />
              <Route path="analysis" element={<AnalysisStepPage />} />
              <Route path="results" element={<ResultsStepPage />} />
            </Route>
            <Route path="tracker" element={<TrackerPage />} />
            <Route path="repo-analysis" element={<RepoAnalysisPage />} />
            <Route path="jobs" element={<JobsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
```

Delete `frontend/src/routes/GeneratePage.tsx` (there is no `GeneratePage.test.tsx` to delete alongside it — it was never created).

- [ ] **Step 13: Run the full frontend suite, typecheck, and build**

Run: `npm run typecheck && npm run test && npm run build`
Expected: all pass, including every pre-existing test file (nothing outside `frontend/src/routes/generate/` and `ProfileForm.*` was touched).

- [ ] **Step 14: Commit**

```bash
git add frontend/src/routes/generate frontend/src/test/fixtures.ts frontend/src/main.tsx
git rm frontend/src/routes/GeneratePage.tsx
git commit -m "feat(frontend): split Generate wizard into real per-step routes with sessionStorage resume"
```
