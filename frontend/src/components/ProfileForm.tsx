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
