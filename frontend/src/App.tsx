import { Routes, Route } from 'react-router-dom'
import { useEffect } from 'react'
import Layout from './components/Layout'
import CatalogPage from './pages/CatalogPage'
import AuthPage from './pages/AuthPage'
import InventoryDetailPage from './pages/InventoryDetailPage'
import { useAuthStore } from './store/authStore'

export default function App() {
  const fetchProfile = useAuthStore(s => s.fetchProfile)

  useEffect(() => {
    fetchProfile()
  }, [fetchProfile])

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<CatalogPage />} />
        <Route path="/inventory/:id" element={<InventoryDetailPage />} />
      </Route>
      <Route path="/auth" element={<AuthPage />} />
    </Routes>
  )
}
