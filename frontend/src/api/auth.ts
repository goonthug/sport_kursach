import api from './client'
import type { User } from '../types'

export const login = (email: string, password: string) =>
  api.post<{ user: User }>('/auth/login/', { email, password }).then(r => r.data)

export const logout = () =>
  api.post('/auth/logout/').then(r => r.data)

export const getProfile = () =>
  api.get<{ user: User }>('/auth/profile/').then(r => r.data)

export interface RegisterData {
  email: string
  password: string
  role: 'client' | 'owner'
  full_name: string
  phone?: string
  passport_series?: string
  passport_number?: string
  passport_issue_date?: string
  passport_department_code?: string
  passport_nda_accepted?: boolean
  tax_number?: string
}

export const register = (data: RegisterData) =>
  api.post<{ user: User }>('/auth/register/', data).then(r => r.data)
