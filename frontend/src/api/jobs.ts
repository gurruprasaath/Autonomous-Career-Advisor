import { useQuery } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { JobRecommendation } from './types'

export function useJobRecommendations() {
  return useQuery({
    queryKey: ['job-recommendations'],
    queryFn: () => apiRequest<JobRecommendation[]>('/api/jobs/recommendations'),
    retry: false,
  })
}
