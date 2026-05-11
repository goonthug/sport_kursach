import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import SearchBar from '../components/SearchBar'
import InventoryCard from '../components/InventoryCard'
import YandexMap from '../components/YandexMap'
import { getInventory } from '../api/inventory'
import type { InventoryItem, AISearchResponse } from '../types'

const MAPS_KEY = import.meta.env.VITE_YANDEX_MAPS_KEY ?? ''

export default function CatalogPage() {
  const [aiResults, setAiResults] = useState<InventoryItem[] | null>(null)
  const [parsed, setParsed] = useState<AISearchResponse['parsed'] | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['inventory'],
    queryFn: () => getInventory({ ordering: '-avg_rating' }),
  })

  const items = aiResults ?? data?.results ?? []

  const handleResults = (res: AISearchResponse) => {
    setAiResults(res.results)
    setParsed(res.parsed)
  }

  const handleClear = () => {
    setAiResults(null)
    setParsed(null)
  }

  return (
    <div className="space-y-6">
      {/* Hero с AI-поиском */}
      <div className="flex flex-col items-center gap-3 py-8 bg-gradient-to-br from-blue-50 to-white rounded-2xl">
        <h1 className="text-3xl font-bold text-gray-900">Найдите инвентарь</h1>
        <p className="text-gray-500 text-sm">Опишите запрос — AI понимает русский язык</p>
        <SearchBar onResults={handleResults} onClear={handleClear} />

        {/* Теги разобранного запроса */}
        {parsed && (
          <div className="flex flex-wrap justify-center gap-2 text-sm mt-1">
            {parsed.city_name && (
              <span className="bg-blue-100 text-blue-700 px-3 py-1 rounded-full">📍 {parsed.city_name}</span>
            )}
            {parsed.category_query && (
              <span className="bg-green-100 text-green-700 px-3 py-1 rounded-full">🏋️ {parsed.category_query}</span>
            )}
            {parsed.max_price && (
              <span className="bg-yellow-100 text-yellow-700 px-3 py-1 rounded-full">
                💰 до {parsed.max_price.toLocaleString('ru-RU')} ₽/день
              </span>
            )}
            {parsed.start_date && (
              <span className="bg-purple-100 text-purple-700 px-3 py-1 rounded-full">📅 {parsed.start_date}</span>
            )}
          </div>
        )}
      </div>

      {/* Карта + карточки */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Yandex Maps */}
        <div className="lg:w-1/2 h-80 lg:h-[580px] lg:sticky lg:top-4">
          <YandexMap items={items} apiKey={MAPS_KEY} />
        </div>

        {/* Список */}
        <div className="lg:w-1/2">
          {aiResults !== null && (
            <p className="text-sm text-gray-500 mb-3">
              Найдено по запросу: <span className="font-medium">{aiResults.length}</span> результатов
            </p>
          )}

          {isLoading && !aiResults ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="bg-white rounded-xl h-56 animate-pulse border" />
              ))}
            </div>
          ) : items.length === 0 ? (
            <div className="flex flex-col items-center py-16 text-gray-400 gap-3">
              <span className="text-5xl">🔍</span>
              <p>По вашему запросу ничего не найдено</p>
              {aiResults !== null && (
                <button onClick={handleClear} className="text-blue-500 hover:underline text-sm">
                  Показать весь каталог
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {items.map(item => (
                <InventoryCard key={item.inventory_id} item={item} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
