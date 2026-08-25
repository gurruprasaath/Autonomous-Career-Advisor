import { useEffect, useState } from "react";
import { advise, getRoles, getToken } from "./api";
import ProfileForm from "./components/ProfileForm";
import RolePicker from "./components/RolePicker";
import Results from "./components/Results";
import AgentTerminal from "./components/AgentTerminal";
import Auth from "./components/Auth";
import LearningTracker from "./components/LearningTracker";

const STEPS = ["Profile", "Target role", "Analysis", "Learning path"];

export default function App() {
  const [step, setStep] = useState(0);
  const [profileInput, setProfileInput] = useState(null);
  const [roles, setRoles] = useState([]);
  const [rolesError, setRolesError] = useState("");
  const [role, setRole] = useState("");
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  
  const [isLoggedIn, setIsLoggedIn] = useState(!!getToken());
  const [currentTab, setCurrentTab] = useState("generator"); // "generator", "tracker"

  useEffect(() => {
    getRoles()
      .then((d) => { setRoles(d.roles); setRolesError(""); })
      .catch((e) => setRolesError(e.message));
  }, []);

  const runAdvisor = async () => {
    setStep(2);
    setError("");
    try {
      const res = await advise({ ...profileInput, target_role: role });
      setResult(res);
      setStep(3);
    } catch (e) {
      setError(e.message);
      setStep(1);
    }
  };

  const restart = () => {
    setStep(0);
    setProfileInput(null);
    setRole("");
    setResult(null);
    setError("");
  };

  return (
    <>
      <header className="app-header">
        <h1>Autonomous Career Advisor</h1>
        <p>Multi-agent skill gap analysis &amp; verified learning path generation</p>
      </header>

      <div className="steps">
        {STEPS.map((s, i) => (
          <span key={s}
                className={`step-chip ${i === step ? "active" : ""} ${i < step ? "done" : ""}`}>
            {i < step ? "✓ " : ""}{s}
          </span>
        ))}
      </div>

      {error && <div className="error-box">Advisor failed: {error}</div>}

      {!isLoggedIn ? (
        <Auth onLogin={() => setIsLoggedIn(true)} />
      ) : (
        <>
          <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center', marginBottom: '2rem' }}>
            <button className={`secondary-button ${currentTab === 'generator' ? 'active' : ''}`} onClick={() => setCurrentTab('generator')}>Generate Path</button>
            <button className={`secondary-button ${currentTab === 'tracker' ? 'active' : ''}`} onClick={() => setCurrentTab('tracker')}>My Learning Tracker</button>
          </div>

          {currentTab === "generator" && (
            <>
              {step === 0 && (
                <ProfileForm
                  onSubmit={(input) => { setProfileInput(input); setStep(1); }}
                />
              )}

              {step === 1 && (
                <RolePicker
                  roles={roles} selected={role} onSelect={setRole}
                  onBack={() => setStep(0)} onAnalyse={runAdvisor} loadError={rolesError}
                />
              )}

              {step === 2 && (
                <AgentTerminal role={role} />
              )}

              {step === 3 && result && <Results result={result} onRestart={restart} />}
            </>
          )}

          {currentTab === "tracker" && (
            <LearningTracker />
          )}
        </>
      )}
    </>
  );
}
