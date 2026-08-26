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
