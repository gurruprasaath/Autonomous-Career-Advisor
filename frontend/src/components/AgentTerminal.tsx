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
      <div style={{ background: '#2a2116', padding: '8px 16px', borderBottom: '1px solid #3d3122', display: 'flex', gap: '6px' }}>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ff5f56' }}></div>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#ffbd2e' }}></div>
        <div style={{ width: 12, height: 12, borderRadius: '50%', background: '#27c93f' }}></div>
        <span style={{ marginLeft: '12px', color: '#8a7a5c', fontSize: '0.85rem', fontFamily: "'IBM Plex Mono', monospace" }}>typesetting ~ /usr/bin/advisor</span>
      </div>
      <div style={{ padding: '20px', background: '#1a140c', minHeight: '250px', fontFamily: "'IBM Plex Mono', monospace", fontSize: '0.9rem', color: '#e0a94a', display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {lines.map((l, i) => (
          <div key={i} style={{ animation: 'fadeIn 0.3s ease-out' }}>
            <span style={{ color: '#8a7a5c' }}>{l.time.toLocaleTimeString('en-GB')}</span> {l.text}
          </div>
        ))}
        {lines.length < LOGS.length && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '12px', color: '#8a7a5c' }}>
            <div className="spinner" style={{ width: 16, height: 16, margin: 0, borderWidth: 2 }} />
            Processing...
          </div>
        )}
      </div>
    </div>
  )
}
