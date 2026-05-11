import { useEffect, useRef } from 'react'
import type { InventoryItem } from '../types'

/* eslint-disable @typescript-eslint/no-explicit-any */
declare global {
  interface Window { ymaps: any }
}

interface Props {
  items: InventoryItem[]
  apiKey: string
}

export default function YandexMap({ items, apiKey }: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<any>(null)

  useEffect(() => {
    if (!apiKey || !containerRef.current) return

    const initMap = () => {
      window.ymaps.ready(() => {
        if (!containerRef.current) return
        mapRef.current?.destroy()

        const pinned = items.filter(i => i.pickup_point_data?.lat)
        const center: [number, number] = pinned.length
          ? [Number(pinned[0].pickup_point_data!.lat), Number(pinned[0].pickup_point_data!.lon)]
          : [55.75, 37.62]

        mapRef.current = new window.ymaps.Map(containerRef.current, {
          center,
          zoom: pinned.length ? 12 : 4,
          controls: ['zoomControl'],
        })

        pinned.forEach(item => {
          const pp = item.pickup_point_data!
          const mark = new window.ymaps.Placemark(
            [Number(pp.lat), Number(pp.lon)],
            {
              balloonContent: `<b>${item.name}</b><br/>${Number(item.price_per_day).toLocaleString('ru-RU')} ₽/день<br/>📍 ${pp.address}`,
              hintContent: item.name,
            },
            { preset: 'islands#blueCircleDotIcon' },
          )
          mapRef.current.geoObjects.add(mark)
        })
      })
    }

    const SCRIPT_ID = 'ymaps-script'
    if (!document.getElementById(SCRIPT_ID)) {
      const s = document.createElement('script')
      s.id = SCRIPT_ID
      s.src = `https://api-maps.yandex.ru/2.1/?apikey=${apiKey}&lang=ru_RU`
      s.onload = initMap
      document.head.appendChild(s)
    } else if (window.ymaps) {
      initMap()
    }

    return () => {
      mapRef.current?.destroy()
      mapRef.current = null
    }
  }, [items, apiKey])

  if (!apiKey) {
    return (
      <div className="w-full h-full bg-gray-100 rounded-xl flex flex-col items-center justify-center text-gray-400 gap-2">
        <span className="text-3xl">🗺️</span>
        <span className="text-sm">Добавьте VITE_YANDEX_MAPS_KEY для отображения карты</span>
      </div>
    )
  }

  return <div ref={containerRef} className="w-full h-full rounded-xl" />
}
