import { create } from 'zustand'
import type { User } from '../types'
import { login as loginApi, logout as logoutApi, getProfile } from '../api/auth'

interface AuthState {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  fetchProfile: () => Promise<void>
}

export const useAuthStore = create<AuthState>(set => ({
  user: null,
  loading: false,

  login: async (email, password) => {
    const { user } = await loginApi(email, password)
    set({ user })
  },

  logout: async () => {
    await logoutApi()
    set({ user: null })
  },

  fetchProfile: async () => {
    try {
      set({ loading: true })
      const { user } = await getProfile()
      set({ user })
    } catch {
      set({ user: null })
    } finally {
      set({ loading: false })
    }
  },
}))
