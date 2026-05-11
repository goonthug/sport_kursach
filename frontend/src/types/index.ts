export interface City {
  city_id: string;
  name: string;
  region: string;
  lat: number | null;
  lon: number | null;
}

export interface PickupPoint {
  point_id: string;
  name: string;
  address: string;
  lat: number;
  lon: number;
  city: string;
  city_name: string;
  phone: string;
  is_active: boolean;
}

export interface InventoryPhoto {
  photo_id: string;
  photo_url: string;
  is_main: boolean;
  description: string;
}

export interface InventoryItem {
  inventory_id: string;
  name: string;
  brand: string;
  model: string;
  price_per_day: string;
  condition: string;
  status: string;
  avg_rating: string | null;
  reviews_count: number;
  total_rentals: number;
  category_name: string;
  owner_name: string;
  pickup_point_data: PickupPoint | null;
  main_photo: string | null;
  // detail only
  description?: string;
  min_rental_days?: number;
  max_rental_days?: number;
  deposit_amount?: string;
  added_date?: string;
  photos?: InventoryPhoto[];
}

export interface User {
  user_id: string;
  email: string;
  phone: string | null;
  role: 'client' | 'owner' | 'manager' | 'administrator';
  status: string;
  avg_rating: string | null;
  loyalty_points: number;
  full_name: string;
  avatar_url: string | null;
  registration_date: string;
}

export interface AISearchResponse {
  query: string;
  parsed: {
    category_query: string | null;
    city_name: string | null;
    start_date: string | null;
    end_date: string | null;
    max_price: number | null;
    keywords: string | null;
  };
  results: InventoryItem[];
  count: number;
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
