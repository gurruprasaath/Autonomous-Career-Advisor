import { useQuery } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { InterviewTips } from './types'

export function useInterviewTips() {
  return useQuery({
    queryKey: ['interview-tips'],
    queryFn: () => apiRequest<InterviewTips>('/api/interview-tips'),
    retry: false,
  })
}
