import api from './client'
import type { InventoryItem, City, PaginatedResponse } from '../types'

export interface InventoryFilters {
  search?: string
  city?: string
  category?: string
  min_price?: number
  max_price?: number
  ordering?: string
  page?: number
}

export const getInventory = (filters: InventoryFilters = {}) =>
  api.get<PaginatedResponse<InventoryItem>>('/items/', { params: filters }).then(r => r.data)

export const getInventoryItem = (id: string) =>
  api.get<InventoryItem>(`/items/${id}/`).then(r => r.data)

export const getCities = (search?: string) =>
  api.get<PaginatedResponse<City>>('/cities/', { params: search ? { search } : {} }).then(r => r.data)
