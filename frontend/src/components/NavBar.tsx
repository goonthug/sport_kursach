import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function NavBar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/auth')
  }

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4 h-16 flex items-center justify-between">
        <Link to="/" className="text-xl font-bold text-blue-600">
          🏋️ СпортРент
        </Link>
        <div className="flex items-center gap-6">
          <Link to="/" className="text-sm text-gray-600 hover:text-blue-600">
            Каталог
          </Link>
          {user ? (
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-700 font-medium">{user.full_name}</span>
              <span className="text-xs text-gray-400 capitalize">{user.role}</span>
              <button
                onClick={handleLogout}
                className="text-sm text-red-500 hover:text-red-700"
              >
                Выйти
              </button>
            </div>
          ) : (
            <Link
              to="/auth"
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm hover:bg-blue-700 transition-colors"
            >
              Войти
            </Link>
          )}
        </div>
      </div>
    </nav>
  )
}
