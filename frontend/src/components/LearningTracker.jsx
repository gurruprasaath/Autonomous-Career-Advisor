import { useState, useEffect } from "react";
import { getJourneys, updateStepStatus } from "../api";

export default function LearningTracker() {
  const [journeys, setJourneys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchJourneys = async () => {
    try {
      setLoading(true);
      const data = await getJourneys();
      setJourneys(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJourneys();
  }, []);

  const handleStatusChange = async (stepId, status) => {
    try {
      await updateStepStatus(stepId, status);
      await fetchJourneys();
    } catch (e) {
      alert("Failed to update status: " + e.message);
    }
  };

  if (loading) return <div>Loading journeys...</div>;
  if (error) return <div className="error-box">{error}</div>;
  if (journeys.length === 0) return <div>No learning paths generated yet. Go to Generate Path!</div>;

  return (
    <div className="tracker">
      {journeys.map((j) => (
        <div key={j.id} className="panel" style={{ marginBottom: "2rem" }}>
          <h2>Target Role: {j.target_role}</h2>
          <p className="hint">Created At: {new Date(j.created_at).toLocaleString()}</p>
          <div className="timeline">
            {j.steps.map((s) => (
              <div className={`tstep ${s.status === "completed" ? "done" : s.status === "struggling" ? "warn" : ""}`} key={s.id}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h3 style={{ margin: 0 }}>
                    {s.order}. {s.skill_name} <span className="weeks">{s.estimated_weeks} wk</span>
                  </h3>
                  <select 
                    value={s.status} 
                    onChange={(e) => handleStatusChange(s.id, e.target.value)}
                  >
                    <option value="pending">Pending</option>
                    <option value="in_progress">In Progress</option>
                    <option value="completed">Completed</option>
                    <option value="struggling">Struggling</option>
                  </select>
                </div>
                <p>{s.objective}</p>
                <p className="milestone">🏁 {s.milestone}</p>
                {s.status === "struggling" && (
                  <div className="error-box" style={{ marginTop: "0.5rem" }}>
                    <p style={{ margin: 0 }}>You've marked that you're struggling with this module.</p>
                    <button className="primary-button" style={{ marginTop: "0.5rem", padding: "0.5rem 1rem" }} onClick={() => alert("Re-planning logic triggered! (Mock)")}>
                      Recalculate Sub-Path
                    </button>
                  </div>
                )}
                {s.resources && s.resources.length > 0 && (
                  <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                    {s.resources.map((r) => (
                      <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                        📚 {r.title} — {r.provider} {r.free ? "(free)" : ""}
                      </a>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
