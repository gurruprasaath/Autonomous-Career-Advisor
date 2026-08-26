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
                  <title>Depth: {d.depth_score}</title>
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
