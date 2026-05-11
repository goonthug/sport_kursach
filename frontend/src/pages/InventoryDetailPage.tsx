import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getInventoryItem } from '../api/inventory'
import { useAuthStore } from '../store/authStore'

const CONDITION_LABELS: Record<string, string> = {
  new: 'Новое',
  excellent: 'Отличное',
  good: 'Хорошее',
  fair: 'Удовлетворительное',
}

export default function InventoryDetailPage() {
  const { id } = useParams<{ id: string }>()
  const user = useAuthStore(s => s.user)

  const { data: item, isLoading, error } = useQuery({
    queryKey: ['inventory', id],
    queryFn: () => getInventoryItem(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto space-y-4 animate-pulse">
        <div className="h-72 bg-gray-200 rounded-xl" />
        <div className="h-8 bg-gray-200 rounded w-1/2" />
        <div className="h-4 bg-gray-200 rounded" />
        <div className="h-4 bg-gray-200 rounded w-3/4" />
      </div>
    )
  }

  if (error || !item) {
    return (
      <div className="text-center py-16">
        <p className="text-gray-400 text-lg">Инвентарь не найден</p>
        <Link to="/" className="mt-4 inline-block text-blue-600 hover:underline">← Вернуться в каталог</Link>
      </div>
    )
  }

  const mainPhoto = item.photos?.find(p => p.is_main) ?? item.photos?.[0]

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Link to="/" className="text-blue-600 hover:underline text-sm inline-flex items-center gap-1">
        ← Каталог
      </Link>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Фото */}
        <div className="aspect-video bg-gray-100 rounded-xl overflow-hidden">
          {mainPhoto ? (
            <img src={mainPhoto.photo_url} alt={item.name} className="w-full h-full object-cover" />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-6xl">🏋️</div>
          )}
        </div>

        {/* Детали */}
        <div className="space-y-4">
          <div>
            <span className="text-sm text-blue-600 font-medium bg-blue-50 px-2 py-0.5 rounded">
              {item.category_name}
            </span>
            <h1 className="text-2xl font-bold text-gray-900 mt-2">{item.name}</h1>
            {item.brand && <p className="text-gray-500">{item.brand} {item.model}</p>}
          </div>

          <div className="flex items-center gap-4">
            <span className="text-3xl font-bold text-blue-600">
              {Number(item.price_per_day).toLocaleString('ru-RU')} ₽
              <span className="text-base font-normal text-gray-500">/день</span>
            </span>
            {item.avg_rating && (
              <span className="text-lg">⭐ <span className="font-medium">{item.avg_rating}</span></span>
            )}
          </div>

          <div className="bg-gray-50 rounded-xl p-4 space-y-2 text-sm">
            <Row label="Состояние" value={CONDITION_LABELS[item.condition] ?? item.condition} />
            <Row label="Минимум дней" value={String(item.min_rental_days ?? 1)} />
            <Row label="Максимум дней" value={String(item.max_rental_days ?? 30)} />
            {Number(item.deposit_amount) > 0 && (
              <Row label="Залог" value={`${Number(item.deposit_amount).toLocaleString('ru-RU')} ₽`} />
            )}
            <Row label="Всего аренд" value={String(item.total_rentals)} />
          </div>

          {item.pickup_point_data && (
            <div className="bg-blue-50 rounded-xl p-4 text-sm">
              <p className="font-semibold text-blue-900">📍 {item.pickup_point_data.name}</p>
              <p className="text-blue-700 mt-0.5">
                {item.pickup_point_data.city_name}, {item.pickup_point_data.address}
              </p>
              {item.pickup_point_data.phone && (
                <p className="text-blue-600 mt-0.5">{item.pickup_point_data.phone}</p>
              )}
            </div>
          )}

          {user ? (
            <button className="w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 transition-colors">
              Арендовать
            </button>
          ) : (
            <Link
              to="/auth"
              className="block w-full bg-blue-600 text-white py-3 rounded-xl font-medium hover:bg-blue-700 text-center transition-colors"
            >
              Войдите, чтобы арендовать
            </Link>
          )}
        </div>
      </div>

      {item.description && (
        <div>
          <h2 className="font-semibold text-gray-900 mb-2">Описание</h2>
          <p className="text-gray-600 leading-relaxed">{item.description}</p>
        </div>
      )}

      {item.photos && item.photos.length > 1 && (
        <div>
          <h2 className="font-semibold text-gray-900 mb-3">Фотографии</h2>
          <div className="grid grid-cols-3 gap-3">
            {item.photos.map(p => (
              <img
                key={p.photo_id}
                src={p.photo_url}
                alt={item.name}
                className="aspect-video object-cover rounded-lg"
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between">
      <span className="text-gray-500">{label}</span>
      <span className="font-medium text-gray-900">{value}</span>
    </div>
  )
}
