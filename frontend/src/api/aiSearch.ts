import api from './client'
import type { AISearchResponse } from '../types'

export const aiSearch = (query: string) =>
  api.post<AISearchResponse>('/ai-search/', { query }).then(r => r.data)
