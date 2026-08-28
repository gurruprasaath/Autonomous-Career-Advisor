import { useEffect, useState, type FormEvent } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useAnalyzedRepos, useAnalyzeRepo, useChatRepo } from '../api/github'

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
}

function chatStorageKey(username: string, repo: string) {
  return `repo-chat:${username}/${repo}`
}

function loadChatHistory(username: string, repo: string): ChatMessage[] {
  try {
    const raw = localStorage.getItem(chatStorageKey(username, repo))
    return raw ? (JSON.parse(raw) as ChatMessage[]) : []
  } catch {
    return []
  }
}

function saveChatHistory(username: string, repo: string, history: ChatMessage[]) {
  try {
    localStorage.setItem(chatStorageKey(username, repo), JSON.stringify(history))
  } catch {
    // localStorage unavailable (private mode, quota) — chat still works for this session, just won't persist
  }
}

export default function RepoAnalysisPage() {
  const [username, setUsername] = useState('')
  const [repo, setRepo] = useState('')
  const [status, setStatus] = useState('')
  const [analyzed, setAnalyzed] = useState(false)
  const [query, setQuery] = useState('')
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([])

  const { data: analyzedRepos } = useAnalyzedRepos()
  const analyzeRepo = useAnalyzeRepo()
  const chatRepo = useChatRepo()

  // Persist this repo's conversation as it grows, so reopening it later restores it.
  useEffect(() => {
    if (analyzed && username && repo) {
      saveChatHistory(username, repo, chatHistory)
    }
  }, [chatHistory, analyzed, username, repo])

  const handleAnalyze = () => {
    if (!username || !repo) return

    const existing = analyzedRepos?.find((r) => r.username === username && r.repo_name === repo)
    if (existing) {
      // Already analyzed — reuse it instead of re-downloading, and restore the saved chat.
      setAnalyzed(true)
      setChatHistory(loadChatHistory(username, repo))
      setStatus(`Already analyzed (${existing.file_count} files, ${new Date(existing.analyzed_at).toLocaleString()}) — resuming your saved chat.`)
      return
    }

    setStatus('Downloading and analyzing repository... This might take a minute depending on repo size.')
    setAnalyzed(false)
    analyzeRepo.mutate({ username, repoName: repo }, {
      onSuccess: (res) => {
        setStatus(`Success! Indexed ${res.files_processed} files.`)
        setAnalyzed(true)
        setChatHistory(loadChatHistory(username, repo))
      },
      onError: (e) => setStatus(`Error: ${e instanceof Error ? e.message : String(e)}`),
    })
  }

  const openFromHistory = (u: string, r: string) => {
    setUsername(u)
    setRepo(r)
    setAnalyzed(true)
    setChatHistory(loadChatHistory(u, r))
    setStatus(`Reusing previous analysis of ${u}/${r} — resuming your saved chat.`)
  }

  const handleChat = (e: FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    const userMsg = query
    setChatHistory((prev) => [...prev, { role: 'user', text: userMsg }])
    setQuery('')

    chatRepo.mutate({ username, repoName: repo, query: userMsg }, {
      onSuccess: (res) => setChatHistory((prev) => [...prev, { role: 'assistant', text: res.answer }]),
      onError: (e) => setChatHistory((prev) => [...prev, { role: 'assistant', text: `Error: ${e instanceof Error ? e.message : String(e)}` }]),
    })
  }

  return (
    <div className="panel" style={{ maxWidth: '800px', margin: '0 auto' }}>
      <h2>GitHub Repository Analysis</h2>
      <p className="hint">Enter a public GitHub repository to download its source code and chat with it locally using AI RAG.</p>

      {analyzedRepos && analyzedRepos.length > 0 && (
        <div className="repo-history">
          <strong>Already analyzed</strong>
          <ul>
            {analyzedRepos.map((r) => (
              <li key={`${r.username}/${r.repo_name}`}>
                <a href="#" onClick={(e) => { e.preventDefault(); openFromHistory(r.username, r.repo_name) }}>
                  {r.username}/{r.repo_name}
                </a>{' '}
                — {r.file_count} files, analyzed {new Date(r.analyzed_at).toLocaleString()}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ display: 'flex', gap: '10px', marginBottom: '1rem' }}>
        <input className="input-field" placeholder="GitHub Username (e.g. torvalds)" value={username} onChange={(e) => setUsername(e.target.value)} />
        <input className="input-field" placeholder="Repository Name (e.g. linux)" value={repo} onChange={(e) => setRepo(e.target.value)} />
        <button className="primary-button" onClick={handleAnalyze}>Analyze</button>
      </div>

      {status && <div className="hint" style={{ marginBottom: '1rem' }}>{status}</div>}

      {analyzed && (
        <div style={{ border: '1px solid var(--panel-border)', borderRadius: '12px', padding: '1rem' }}>
          <div style={{ maxHeight: '400px', overflowY: 'auto', marginBottom: '1rem' }}>
            {chatHistory.length === 0 && <p className="hint">Ask a question about the code!</p>}
            {chatHistory.map((msg, i) => (
              <div key={i} style={{ marginBottom: '1rem', textAlign: msg.role === 'user' ? 'right' : 'left' }}>
                <div style={{
                  display: 'inline-block', padding: '0.5rem 1rem', borderRadius: '10px',
                  background: msg.role === 'user' ? 'var(--primary)' : 'var(--bg-main)',
                  color: msg.role === 'user' ? 'white' : 'var(--text-main)',
                  border: msg.role === 'user' ? 'none' : '1px solid var(--panel-border)',
                  whiteSpace: 'pre-wrap', textAlign: 'left',
                }}>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      p: ({ ...props }) => <p style={{ margin: '0 0 0.5rem 0' }} {...props} />,
                      ul: ({ ...props }) => <ul style={{ margin: '0 0 0.5rem 1rem', padding: 0 }} {...props} />,
                      ol: ({ ...props }) => <ol style={{ margin: '0 0 0.5rem 1rem', padding: 0 }} {...props} />,
                      li: ({ ...props }) => <li style={{ marginBottom: '0.25rem' }} {...props} />,
                      code: ({ className, ...props }) =>
                        className?.includes('language-')
                          ? <code style={{ display: 'block', fontFamily: "'IBM Plex Mono', monospace", background: 'rgba(36,29,18,0.08)', padding: '0.5rem', borderRadius: '6px', overflowX: 'auto' }} className={className} {...props} />
                          : <code style={{ fontFamily: "'IBM Plex Mono', monospace", background: 'rgba(36,29,18,0.08)', padding: '0.1rem 0.3rem', borderRadius: '4px' }} {...props} />,
                    }}
                  >
                    {msg.text}
                  </ReactMarkdown>
                </div>
              </div>
            ))}
            {chatRepo.isPending && <div className="hint">Thinking...</div>}
          </div>
          <form onSubmit={handleChat} style={{ display: 'flex', gap: '10px' }}>
            <input
              className="input-field" style={{ flex: 1 }} value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="e.g. Where is the database connection setup?"
              disabled={chatRepo.isPending}
            />
            <button className="primary-button" type="submit" disabled={chatRepo.isPending || !query.trim()}>Send</button>
          </form>
        </div>
      )}
    </div>
  )
}
