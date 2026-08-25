import { useState, useEffect, useRef } from "react";
import { getJourneys, recordProgress, getStepQuiz, syncGithub, recalculateJourney } from "../api";

function QuizModal({ step, onClose, onScored }) {
  const [questions, setQuestions] = useState(null);
  const [answers, setAnswers] = useState({});
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getStepQuiz(step.id)
      .then((d) => setQuestions(d.questions))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [step.id]);

  const submit = () => {
    const correct = questions.filter((q, i) => answers[i] === q.correct_index).length;
    const score = Math.round((correct / questions.length) * 100);
    onScored(score);
  };

  return (
    <div className="card" style={{ maxWidth: 600, margin: "2rem auto" }}>
      <h2>Quiz: {step.skill_name}</h2>
      {loading && <p>Generating questions...</p>}
      {error && <div className="error-box">{error}</div>}
      {questions && questions.map((q, i) => (
        <div key={i} style={{ marginBottom: "1rem" }}>
          <p><strong>{i + 1}. {q.question}</strong></p>
          {q.options.map((opt, oi) => (
            <label key={oi} style={{ display: "block", marginLeft: "1rem" }}>
              <input type="radio" name={`q${i}`} checked={answers[i] === oi}
                    onChange={() => setAnswers({ ...answers, [i]: oi })} /> {opt}
            </label>
          ))}
        </div>
      ))}
      {questions && (
        <button className="primary-button" onClick={submit}
               disabled={Object.keys(answers).length !== questions.length}>
          Submit
        </button>
      )}
      <button className="secondary-button" style={{ marginLeft: "0.5rem" }} onClick={onClose}>Cancel</button>
    </div>
  );
}

function StepTracker({ step, onChanged }) {
  const [running, setRunning] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [quizOpen, setQuizOpen] = useState(false);
  const intervalRef = useRef(null);

  useEffect(() => {
    if (running) {
      intervalRef.current = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    } else {
      clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [running]);

  const stopAndSave = async () => {
    setRunning(false);
    const minutes = Math.round(elapsedSec / 60);
    if (minutes > 0) {
      await recordProgress(step.id, { minutes_delta: minutes });
      onChanged();
    }
    setElapsedSec(0);
  };

  const rateConfidence = async (rating) => {
    await recordProgress(step.id, { confidence_rating: rating });
    onChanged();
  };

  const budgetMinutes = step.estimated_weeks * 10 * 60; // rough: hours_per_week baked into estimated_weeks already
  const pct = Math.min(100, Math.round(((step.time_spent_minutes || 0) / Math.max(budgetMinutes, 1)) * 100));

  return (
    <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
        {!running ? (
          <button className="secondary-button" onClick={() => setRunning(true)}>▶ Start timer</button>
        ) : (
          <button className="secondary-button" onClick={stopAndSave}>⏸ Stop ({Math.floor(elapsedSec / 60)}m{elapsedSec % 60}s)</button>
        )}
        <span className="hint">{step.time_spent_minutes || 0}m logged · {pct}% of budget</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
        <span className="hint">Confidence:</span>
        {[1, 2, 3, 4, 5].map((n) => (
          <button key={n} className={`secondary-button ${step.confidence_rating === n ? "active" : ""}`}
                 style={{ padding: "4px 10px" }} onClick={() => rateConfidence(n)}>{n}</button>
        ))}
      </div>

      <div>
        <button className="primary-button" onClick={() => setQuizOpen(true)}>Take Quiz</button>
        {step.quiz_score != null && <span className="hint" style={{ marginLeft: "0.5rem" }}>Last score: {step.quiz_score}%</span>}
      </div>

      {step.github_evidence && step.github_evidence.length > 0 && (
        <div className="hint">
          ✓ GitHub evidence: {step.github_evidence.map((e) => e.repo_name).join(", ")}
        </div>
      )}

      {quizOpen && (
        <QuizModal step={step} onClose={() => setQuizOpen(false)}
                  onScored={async (score) => {
                    await recordProgress(step.id, { quiz_score: score });
                    setQuizOpen(false);
                    onChanged();
                  }} />
      )}
    </div>
  );
}

function GithubConnect({ onSynced }) {
  const [username, setUsername] = useState("");
  const [status, setStatus] = useState("");

  const sync = async () => {
    if (!username.trim()) return;
    setStatus("Syncing...");
    try {
      const res = await syncGithub(username.trim());
      setStatus(`Matched ${res.matched_skills.length} skill(s) from ${res.evidence_count} repo entries.`);
      onSynced();
    } catch (e) {
      setStatus(e.message);
    }
  };

  return (
    <div className="panel" style={{ marginBottom: "1.5rem" }}>
      <h2>Connect GitHub</h2>
      <p className="hint">We read your public repos' languages as evidence you've practiced a skill. No login required.</p>
      <div style={{ display: "flex", gap: "0.5rem" }}>
        <input className="input-field" placeholder="GitHub username" value={username}
              onChange={(e) => setUsername(e.target.value)} style={{ maxWidth: 300 }} />
        <button className="primary-button" onClick={sync}>Sync</button>
      </div>
      {status && <p className="hint">{status}</p>}
    </div>
  );
}

export default function LearningTracker() {
  const [journeys, setJourneys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [recalculating, setRecalculating] = useState(null);

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

  useEffect(() => { fetchJourneys(); }, []);

  const recalculate = async (journeyId) => {
    setRecalculating(journeyId);
    try {
      await recalculateJourney(journeyId);
      await fetchJourneys();
    } catch (e) {
      alert("Recalculate failed: " + e.message);
    } finally {
      setRecalculating(null);
    }
  };

  if (loading) return <div>Loading journeys...</div>;
  if (error) return <div className="error-box">{error}</div>;

  return (
    <div className="tracker">
      <GithubConnect onSynced={fetchJourneys} />
      {journeys.length === 0 && <div>No learning paths generated yet. Go to Generate Path!</div>}
      {journeys.map((j) => {
        const hasStruggling = j.steps.some((s) => s.status === "struggling");
        return (
          <div key={j.id} className="panel" style={{ marginBottom: "2rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h2>Target Role: {j.target_role}</h2>
                <p className="hint">Created At: {new Date(j.created_at).toLocaleString()}</p>
              </div>
              {hasStruggling && (
                <button className="primary-button" disabled={recalculating === j.id}
                       onClick={() => recalculate(j.id)}>
                  {recalculating === j.id ? "Recalculating..." : "Recalculate Sub-Path"}
                </button>
              )}
            </div>
            <div className="timeline">
              {j.steps.map((s) => (
                <div className={`tstep ${s.status === "completed" ? "done" : s.status === "struggling" ? "warn" : ""}`} key={s.id}>
                  <h3 style={{ margin: 0 }}>
                    {s.order}. {s.skill_name} <span className="weeks">{s.estimated_weeks} wk</span>
                    <span className="hint" style={{ marginLeft: "0.5rem" }}>({s.status})</span>
                  </h3>
                  <p>{s.objective}</p>
                  <p className="milestone">🏁 {s.milestone}</p>
                  {s.resources && s.resources.length > 0 && (
                    <div style={{ marginTop: "1rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      {s.resources.map((r) => (
                        <a key={r.course_id} className="resource" href={r.url} target="_blank" rel="noreferrer">
                          📚 {r.title} — {r.provider} {r.free ? "(free)" : ""}
                        </a>
                      ))}
                    </div>
                  )}
                  <StepTracker step={s} onChanged={fetchJourneys} />
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
