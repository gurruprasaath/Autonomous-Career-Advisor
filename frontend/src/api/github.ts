import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { AnalyzedRepo } from './types'

interface SyncGithubResponse {
  matched_skills: string[]
  evidence_count: number
}

export function useSyncGithub() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (username: string) =>
      apiRequest<SyncGithubResponse>('/api/github/sync', {
        method: 'POST', body: JSON.stringify({ username }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journeys'] }),
  })
}

export function useAnalyzedRepos() {
  return useQuery({
    queryKey: ['analyzed-repos'],
    queryFn: () => apiRequest<AnalyzedRepo[]>('/api/github/repos'),
  })
}

interface AnalyzeRepoResponse {
  message: string
  files_processed: number
}

export function useAnalyzeRepo() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ username, repoName }: { username: string; repoName: string }) =>
      apiRequest<AnalyzeRepoResponse>(
        `/api/github/repo/${encodeURIComponent(username)}/${encodeURIComponent(repoName)}/analyze`,
        { method: 'POST' }
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['analyzed-repos'] }),
  })
}

interface ChatRepoResponse {
  answer: string
}

export function useChatRepo() {
  return useMutation({
    mutationFn: ({ username, repoName, query }: { username: string; repoName: string; query: string }) =>
      apiRequest<ChatRepoResponse>(
        `/api/github/repo/${encodeURIComponent(username)}/${encodeURIComponent(repoName)}/chat`,
        { method: 'POST', body: JSON.stringify({ query }) }
      ),
  })
}
