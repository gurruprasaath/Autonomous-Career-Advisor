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
