import { useState } from 'react'
import { useLeetcodeSummary, useSyncLeetcode } from '../api/leetcode'

export default function LeetcodeConnect() {
  const [username, setUsername] = useState('')
  const { data: summary } = useLeetcodeSummary()
  const syncLeetcode = useSyncLeetcode()

  const sync = () => {
    if (!username.trim()) return
    syncLeetcode.mutate(username.trim())
  }

  return (
    <div className="panel" style={{ marginBottom: '1.5rem' }}>
      <h2>Connect LeetCode</h2>
      <p className="hint">We read your public LeetCode stats as evidence of problem-solving skill. No login required.</p>
      <div style={{ display: 'flex', gap: '0.5rem' }}>
        <input className="input-field" placeholder="LeetCode username" value={username}
               onChange={(e) => setUsername(e.target.value)} style={{ maxWidth: 300 }} />
        <button className="primary-button" onClick={sync} disabled={syncLeetcode.isPending}>
          {syncLeetcode.isPending ? 'Syncing...' : 'Sync'}
        </button>
      </div>
      {syncLeetcode.error && <p className="hint">{syncLeetcode.error.message}</p>}
      {summary && (
        <div style={{ marginTop: '1rem' }}>
          <p style={{ margin: '0 0 0.3rem' }}><strong>{summary.username}</strong></p>
          <p style={{ margin: '0 0 0.3rem' }}>{`Easy ${summary.easy} · Medium ${summary.medium} · Hard ${summary.hard}`}</p>
          <p style={{ margin: '0 0 0.5rem', fontWeight: 600 }}>
            {summary.dsa_depth !== null ? `DSA depth ${summary.dsa_depth}/10` : 'No solved problems yet'}
          </p>
          {summary.weak_topics.length > 0 && (
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', alignItems: 'center' }}>
              <span className="hint" style={{ margin: 0 }}>Practice next:</span>
              {summary.weak_topics.map((t) => <span key={t} className="tag">{t}</span>)}
            </div>
          )}
          {summary.synced_at && (
            <p className="hint">Last synced {new Date(summary.synced_at).toLocaleString()}</p>
          )}
        </div>
      )}
    </div>
  )
}
