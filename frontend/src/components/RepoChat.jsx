import { useState } from "react";
import { analyzeRepo, chatRepo } from "../api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

export default function RepoChat() {
  const [username, setUsername] = useState("");
  const [repo, setRepo] = useState("");
  const [status, setStatus] = useState("");
  const [analyzed, setAnalyzed] = useState(false);
  const [query, setQuery] = useState("");
  const [chatHistory, setChatHistory] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleAnalyze = async () => {
    if (!username || !repo) return;
    setStatus("Downloading and analyzing repository... This might take a minute depending on repo size.");
    setAnalyzed(false);
    try {
      const res = await analyzeRepo(username, repo);
      setStatus(`Success! Indexed ${res.files_processed} files.`);
      setAnalyzed(true);
      setChatHistory([]);
    } catch (e) {
      setStatus(`Error: ${e.message}`);
    }
  };

  const handleChat = async (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    
    const userMsg = query;
    setChatHistory(prev => [...prev, { role: "user", text: userMsg }]);
    setQuery("");
    setLoading(true);
    
    try {
      const res = await chatRepo(username, repo, userMsg);
      setChatHistory(prev => [...prev, { role: "assistant", text: res.answer }]);
    } catch (e) {
      setChatHistory(prev => [...prev, { role: "assistant", text: `Error: ${e.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="panel" style={{ maxWidth: "800px", margin: "0 auto" }}>
      <h2>GitHub Repository Analysis</h2>
      <p>Enter a public GitHub repository to download its source code and chat with it locally using AI RAG.</p>
      
      <div style={{ display: "flex", gap: "10px", marginBottom: "1rem" }}>
        <input className="input-field" placeholder="GitHub Username (e.g. torvalds)" value={username} onChange={e => setUsername(e.target.value)} />
        <input className="input-field" placeholder="Repository Name (e.g. linux)" value={repo} onChange={e => setRepo(e.target.value)} />
        <button className="primary-button" onClick={handleAnalyze}>Analyze</button>
      </div>
      
      {status && <div className="hint" style={{ marginBottom: "1rem" }}>{status}</div>}
      
      {analyzed && (
        <div className="chat-interface" style={{ border: "1px solid #ccc", borderRadius: "8px", padding: "1rem" }}>
          <div className="chat-history" style={{ maxHeight: "400px", overflowY: "auto", marginBottom: "1rem" }}>
            {chatHistory.length === 0 && <p className="hint">Ask a question about the code!</p>}
            {chatHistory.map((msg, i) => (
              <div key={i} style={{ marginBottom: "1rem", textAlign: msg.role === "user" ? "right" : "left" }}>
                <div style={{ 
                  display: "inline-block", 
                  padding: "0.5rem 1rem", 
                  borderRadius: "8px",
                  background: msg.role === "user" ? "#4f46e5" : "#f1f1f1",
                  color: msg.role === "user" ? "white" : "black",
                  whiteSpace: "pre-wrap",
                  textAlign: "left"
                }}>
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({node, ...props}) => <p style={{margin: "0 0 0.5rem 0"}} {...props} />,
                      ul: ({node, ...props}) => <ul style={{margin: "0 0 0.5rem 1rem", padding: 0}} {...props} />,
                      ol: ({node, ...props}) => <ol style={{margin: "0 0 0.5rem 1rem", padding: 0}} {...props} />,
                      li: ({node, ...props}) => <li style={{marginBottom: "0.25rem"}} {...props} />,
                      code: ({node, inline, ...props}) => 
                        inline 
                          ? <code style={{background: "rgba(0,0,0,0.1)", padding: "0.1rem 0.3rem", borderRadius: "3px"}} {...props} />
                          : <code style={{display: "block", background: "rgba(0,0,0,0.1)", padding: "0.5rem", borderRadius: "5px", overflowX: "auto"}} {...props} />
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            {loading && <div className="hint">Thinking...</div>}
          </div>
          <form onSubmit={handleChat} style={{ display: "flex", gap: "10px" }}>
            <input 
              className="input-field" 
              style={{ flex: 1 }} 
              value={query} 
              onChange={e => setQuery(e.target.value)} 
              placeholder="e.g. Where is the database connection setup?" 
              disabled={loading}
            />
            <button className="primary-button" type="submit" disabled={loading || !query.trim()}>Send</button>
          </form>
        </div>
      )}
    </div>
  );
}
