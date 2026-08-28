import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import './styles/index.css'
import AppShell from './AppShell'
import RequireAuth from './routes/RequireAuth'
import LoginPage from './routes/LoginPage'
import GeneratePage from './routes/GeneratePage'
import TrackerPage from './routes/TrackerPage'
import RepoAnalysisPage from './routes/RepoAnalysisPage'
import JobsPage from './routes/JobsPage'

document.title = 'Autonomous Career Advisor'

const queryClient = new QueryClient()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireAuth><AppShell /></RequireAuth>}>
            <Route index element={<Navigate to="/generate" replace />} />
            <Route path="generate" element={<GeneratePage />} />
            <Route path="tracker" element={<TrackerPage />} />
            <Route path="repo-analysis" element={<RepoAnalysisPage />} />
            <Route path="jobs" element={<JobsPage />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
