import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { LeetcodeSummary } from './types'

export function useLeetcodeSummary() {
  return useQuery({
    queryKey: ['leetcode'],
    queryFn: () => apiRequest<LeetcodeSummary | null>('/api/leetcode'),
  })
}

export function useSyncLeetcode() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (username: string) =>
      apiRequest<LeetcodeSummary>('/api/leetcode/sync', {
        method: 'POST', body: JSON.stringify({ username }),
      }),
    onSuccess: (summary) => {
      queryClient.setQueryData(['leetcode'], summary)
      // Weak topics feed interview prep focus areas.
      queryClient.invalidateQueries({ queryKey: ['interview-tips'] })
    },
  })
}
