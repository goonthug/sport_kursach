import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { aiSearch } from '../api/aiSearch'
import type { AISearchResponse } from '../types'

interface Props {
  onResults: (data: AISearchResponse) => void
  onClear: () => void
}

export default function SearchBar({ onResults, onClear }: Props) {
  const [query, setQuery] = useState('')

  const mutation = useMutation({
    mutationFn: aiSearch,
    onSuccess: onResults,
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (q) {
      mutation.mutate(q)
    } else {
      onClear()
    }
  }

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl">
      <div className="flex gap-2">
        <div className="relative flex-1">
          <input
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Беговые лыжи в Казани до 500р на завтра..."
            className="w-full px-4 py-3 pr-10 border rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 text-gray-800 bg-white"
          />
          {query && (
            <button
              type="button"
              onClick={() => { setQuery(''); onClear() }}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 text-lg leading-none"
            >
              ×
            </button>
          )}
        </div>
        <button
          type="submit"
          disabled={mutation.isPending}
          className="bg-blue-600 text-white px-6 py-3 rounded-xl hover:bg-blue-700 disabled:opacity-50 font-medium whitespace-nowrap transition-colors"
        >
          {mutation.isPending ? '...' : '🤖 AI-поиск'}
        </button>
      </div>
      {mutation.isError && (
        <p className="mt-2 text-sm text-red-500">Ошибка поиска. Попробуйте ещё раз.</p>
      )}
    </form>
  )
}
