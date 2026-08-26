import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from './client'
import type { CompetencyHistory, Journey, ProgressUpdate, QuizQuestion } from './types'

export function useJourneys() {
  return useQuery({
    queryKey: ['journeys'],
    queryFn: () => apiRequest<Journey[]>('/api/tracker/journeys'),
  })
}

export function useCompetencyHistory() {
  return useQuery({
    queryKey: ['competency-history'],
    queryFn: () => apiRequest<CompetencyHistory>('/api/tracker/competency-history'),
  })
}

export function useRecordProgress() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ stepId, update }: { stepId: number; update: ProgressUpdate }) =>
      apiRequest(`/api/tracker/step/${stepId}/progress`, {
        method: 'POST', body: JSON.stringify(update),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journeys'] }),
  })
}

export function useGenerateQuiz() {
  return useMutation({
    mutationFn: (stepId: number) =>
      apiRequest<{ questions: QuizQuestion[] }>(`/api/tracker/step/${stepId}/quiz`, { method: 'POST' }),
  })
}

export function useSubmitQuiz() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({ stepId, answers }: { stepId: number; answers: (number | undefined)[] }) =>
      apiRequest<{ score: number }>(`/api/tracker/step/${stepId}/quiz/submit`, {
        method: 'POST', body: JSON.stringify({ answers }),
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['journeys'] }),
  })
}

export function useRecalculateJourney() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (journeyId: number) =>
      apiRequest(`/api/tracker/journey/${journeyId}/recalculate`, { method: 'POST' }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['journeys'] })
      queryClient.invalidateQueries({ queryKey: ['competency-history'] })
    },
  })
}
