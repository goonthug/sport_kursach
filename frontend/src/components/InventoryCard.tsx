import { Link } from 'react-router-dom'
import type { InventoryItem } from '../types'

const CONDITION_LABELS: Record<string, string> = {
  new: 'Новое',
  excellent: 'Отличное',
  good: 'Хорошее',
  fair: 'Удовлетворительное',
}

export default function InventoryCard({ item }: { item: InventoryItem }) {
  return (
    <Link
      to={`/inventory/${item.inventory_id}`}
      className="bg-white rounded-xl shadow-sm border hover:shadow-md transition-shadow overflow-hidden block"
    >
      <div className="aspect-video bg-gray-100 relative">
        {item.main_photo ? (
          <img src={item.main_photo} alt={item.name} className="w-full h-full object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl">🏋️</div>
        )}
        <span className="absolute top-2 left-2 bg-blue-600 text-white text-xs px-2 py-1 rounded-full">
          {item.category_name}
        </span>
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-gray-900 truncate">{item.name}</h3>
        {item.brand && <p className="text-sm text-gray-500">{item.brand}</p>}
        <div className="mt-2 flex items-center justify-between">
          <span className="text-lg font-bold text-blue-600">
            {Number(item.price_per_day).toLocaleString('ru-RU')} ₽<span className="text-sm font-normal text-gray-500">/день</span>
          </span>
          {item.avg_rating && (
            <span className="text-sm text-yellow-500">⭐ {item.avg_rating}</span>
          )}
        </div>
        {item.pickup_point_data && (
          <p className="mt-1 text-xs text-gray-400 truncate">
            📍 {item.pickup_point_data.city_name}, {item.pickup_point_data.address}
          </p>
        )}
        <p className="mt-1 text-xs text-gray-400">
          {CONDITION_LABELS[item.condition] ?? item.condition}
        </p>
      </div>
    </Link>
  )
}
