import { useMutation } from '@tanstack/react-query'
import { apiRequest, setToken } from './client'
import type { TokenResponse } from './types'

interface Credentials {
  email: string
  password: string
}

function loginRequest({ email, password }: Credentials): Promise<TokenResponse> {
  const params = new URLSearchParams()
  params.append('username', email)
  params.append('password', password)
  return apiRequest<TokenResponse>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: params,
  })
}

function registerRequest({ email, password }: Credentials): Promise<TokenResponse> {
  return apiRequest<TokenResponse>('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  })
}

export function useLogin() {
  return useMutation({
    mutationFn: loginRequest,
    onSuccess: (data) => setToken(data.access_token),
  })
}

export function useRegister() {
  return useMutation({
    mutationFn: registerRequest,
    onSuccess: (data) => setToken(data.access_token),
  })
}
