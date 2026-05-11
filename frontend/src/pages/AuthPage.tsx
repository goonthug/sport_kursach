import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { register } from '../api/auth'

export default function AuthPage() {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [role, setRole] = useState<'client' | 'owner'>('client')
  const [ndaAccepted, setNdaAccepted] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const { login, fetchProfile } = useAuthStore()
  const navigate = useNavigate()

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      navigate('/')
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { error?: string } } })?.response?.data?.error
      setError(msg ?? 'Ошибка входа. Проверьте email и пароль.')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (role === 'client' && !ndaAccepted) {
      setError('Необходимо принять соглашение на обработку паспортных данных (152-ФЗ)')
      return
    }
    setLoading(true)
    try {
      await register({ email, password, role, full_name: fullName, passport_nda_accepted: ndaAccepted })
      await fetchProfile()
      navigate('/')
    } catch (err: unknown) {
      const data = (err as { response?: { data?: Record<string, unknown> } })?.response?.data
      if (data && typeof data === 'object') {
        setError(Object.values(data).flat().join(' '))
      } else {
        setError('Ошибка регистрации')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="bg-white rounded-2xl shadow-sm border p-8 w-full max-w-md">
        <div className="text-center mb-6">
          <span className="text-3xl">🏋️</span>
          <h2 className="text-xl font-bold text-gray-900 mt-1">СпортРент</h2>
        </div>

        <div className="flex gap-2 mb-6 bg-gray-100 rounded-xl p-1">
          {(['login', 'register'] as const).map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setError('') }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                mode === m ? 'bg-white shadow-sm text-gray-900' : 'text-gray-500'
              }`}
            >
              {m === 'login' ? 'Войти' : 'Регистрация'}
            </button>
          ))}
        </div>

        {mode === 'login' ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <Field label="Email">
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className={inputCls} />
            </Field>
            <Field label="Пароль">
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required className={inputCls} />
            </Field>
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button type="submit" disabled={loading} className={btnCls}>
              {loading ? 'Загрузка...' : 'Войти'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} className="space-y-4">
            <Field label="Роль">
              <select value={role} onChange={e => setRole(e.target.value as 'client' | 'owner')} className={inputCls}>
                <option value="client">Арендатор (клиент)</option>
                <option value="owner">Владелец инвентаря</option>
              </select>
            </Field>
            <Field label="Полное имя">
              <input type="text" value={fullName} onChange={e => setFullName(e.target.value)} required className={inputCls} />
            </Field>
            <Field label="Email">
              <input type="email" value={email} onChange={e => setEmail(e.target.value)} required className={inputCls} />
            </Field>
            <Field label="Пароль (минимум 8 символов)">
              <input type="password" value={password} onChange={e => setPassword(e.target.value)} required minLength={8} className={inputCls} />
            </Field>
            {role === 'client' && (
              <label className="flex items-start gap-2 text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={ndaAccepted}
                  onChange={e => setNdaAccepted(e.target.checked)}
                  className="mt-0.5 accent-blue-600"
                />
                <span className="text-gray-600">
                  Согласен на обработку паспортных данных в соответствии с <span className="font-semibold">152-ФЗ</span>
                </span>
              </label>
            )}
            {error && <p className="text-red-500 text-sm">{error}</p>}
            <button type="submit" disabled={loading} className={btnCls}>
              {loading ? 'Загрузка...' : 'Зарегистрироваться'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
      {children}
    </div>
  )
}

const inputCls = 'w-full border rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-900'
const btnCls = 'w-full bg-blue-600 text-white py-2.5 rounded-xl font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors'
