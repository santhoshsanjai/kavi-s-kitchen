import type { Address, DietType, MealSession, SpiceLevel } from './customer'
export type { Address, DietType, MealSession, SpiceLevel }

export type OrderStatus =
  | 'PLANNED'
  | 'CONFIRMED'
  | 'PREPARING'
  | 'READY'
  | 'ASSIGNED'
  | 'OUT_FOR_DELIVERY'
  | 'DELIVERED'
  | 'FAILED'
  | 'CANCELLED'
  | 'SKIPPED'

export type OrderType = 'SUBSCRIPTION' | 'AD_HOC' | 'BULK'

export interface Order {
  id: string
  order_date: string
  customer_id: string
  customer_name: string
  customer_phone: string
  delivery_address: Address
  meal_session: MealSession
  diet_type: DietType
  quantity: number
  order_type: OrderType
  spice_level: SpiceLevel
  rice_preference?: string
  special_notes?: string
  status: OrderStatus
  assigned_driver_id?: string
  assigned_driver_name?: string
  sequence_number?: number
  delivery_notes?: string
  delivery_charge: number
  total_price: number
  created_at: string
  updated_at?: string
}

export interface SessionStats {
  total: number
  veg: number
  non_veg: number
  ready: number
  delivered: number
}

export interface DailySummary {
  date: string
  total_orders: number
  breakfast: SessionStats
  lunch: SessionStats
  dinner: SessionStats
}

export interface OrdersListResponse {
  items: Order[]
  total: number
  summary: DailySummary
}

export interface Driver {
  id: string
  username: string
  full_name: string
  phone?: string
  email?: string
  role: string
  is_active: boolean
  driving_status: string
  vehicle_type?: string
  vehicle_number?: string
  assigned_deliveries_count: number
  completed_today_count: number
  last_latitude?: number
  last_longitude?: number
  last_location_time?: string
}

export interface OrderCreateInput {
  order_date: string
  customer_id: string
  customer_name: string
  customer_phone: string
  delivery_address: Address
  meal_session: MealSession
  diet_type: DietType
  quantity: number
  order_type?: OrderType
  spice_level?: SpiceLevel
  rice_preference?: string
  special_notes?: string
  delivery_notes?: string
  delivery_charge?: number
  total_price?: number
}
