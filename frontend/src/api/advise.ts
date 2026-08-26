import { useMutation, useQuery } from '@tanstack/react-query'
import { apiRequest, apiUpload } from './client'
import type { AdvisorResult, AdviseRequest } from './types'

interface RolesResponse {
  roles: string[]
}

export function useRoles() {
  return useQuery({
    queryKey: ['roles'],
    queryFn: () => apiRequest<RolesResponse>('/api/roles'),
  })
}

export function useAdvise() {
  return useMutation({
    mutationFn: (payload: AdviseRequest) =>
      apiRequest<AdvisorResult>('/api/advise', {
        method: 'POST',
        body: JSON.stringify(payload),
      }),
  })
}

interface ExtractPdfResponse {
  text: string
}

export function useExtractPdf() {
  return useMutation({
    mutationFn: (file: File) => {
      const formData = new FormData()
      formData.append('file', file)
      return apiUpload<ExtractPdfResponse>('/api/extract_pdf', formData)
    },
  })
}
