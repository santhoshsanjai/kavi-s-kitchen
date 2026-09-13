export type CustomerType = 'INDIVIDUAL' | 'FAMILY' | 'OFFICE' | 'OTHER'
export type DietType = 'VEG' | 'NON_VEG' | 'EGG' | 'CUSTOM'
export type MealSession = 'BREAKFAST' | 'LUNCH' | 'DINNER'
export type SpiceLevel = 'MILD' | 'NORMAL' | 'SPICY'

export interface Address {
  address_line: string
  area: string
  landmark?: string
  city: string
  pincode?: string
  latitude?: number
  longitude?: number
  google_place_id?: string
  formatted_address?: string
}

export interface MealPreference {
  diet_type: DietType
  sessions: MealSession[]
  spice_level: SpiceLevel
  rice_preference?: string
  food_exclusions?: string
  allergy_note?: string
  delivery_instructions?: string
}

export interface Customer {
  id: string
  name: string
  phone: string
  alternate_phone?: string
  whatsapp_number?: string
  customer_type: CustomerType
  is_active: boolean
  address: Address
  meal_preference: MealPreference
  notes?: string
  created_at: string
  updated_at?: string
}

export interface CustomerCreateInput {
  name: string
  phone: string
  alternate_phone?: string
  whatsapp_number?: string
  customer_type: CustomerType
  is_active?: boolean
  address: Address
  meal_preference: MealPreference
  notes?: string
}

export type EnquiryStatus =
  | 'NEW'
  | 'CONTACTED'
  | 'QUOTED'
  | 'FOLLOW_UP'
  | 'CONFIRMED'
  | 'REJECTED'
  | 'CONVERTED'
  | 'CLOSED'

export interface Enquiry {
  id: string
  customer_name: string
  phone: string
  requested_meal?: string
  requested_date?: string
  number_of_persons: number
  diet_type: DietType
  subscription_type: string
  delivery_location: string
  quoted_price?: number
  notes?: string
  follow_up_date?: string
  assigned_admin?: string
  status: EnquiryStatus
  customer_id?: string
  enquiry_date: string
  created_at: string
}

export interface EnquiryCreateInput {
  customer_name: string
  phone: string
  requested_meal?: string
  requested_date?: string
  number_of_persons: number
  diet_type: DietType
  subscription_type?: string
  delivery_location: string
  quoted_price?: number
  notes?: string
  follow_up_date?: string
  assigned_admin?: string
  status?: EnquiryStatus
}

export interface MealPlan {
  id: string
  name: string
  diet_type: DietType
  meal_sessions: MealSession[]
  price: number
  billing_cycle: string
  service_days: number
  delivery_eligible: boolean
  is_active: boolean
  description?: string
  created_at: string
}

export interface MealPlanCreateInput {
  name: string
  diet_type: DietType
  meal_sessions: MealSession[]
  price: number
  billing_cycle?: string
  service_days?: number
  delivery_eligible?: boolean
  is_active?: boolean
  description?: string
}
