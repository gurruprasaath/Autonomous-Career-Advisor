import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'

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
