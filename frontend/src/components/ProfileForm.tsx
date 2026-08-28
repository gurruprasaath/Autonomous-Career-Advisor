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
