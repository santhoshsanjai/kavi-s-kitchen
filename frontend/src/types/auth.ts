export type UserRole = 'SUPER_ADMIN' | 'ADMIN' | 'DRIVER'

export interface User {
  id: string
  username: string
  email?: string
  phone?: string
  full_name: string
  role: UserRole
  is_active: boolean
  created_at: string
}

export interface AuthState {
  user: User | null
  token: string | null
  refreshToken: string | null
  role: UserRole | null
  permissions: string[]
  isAuthenticated: boolean
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
  role: UserRole
  permissions: string[]
}

export interface RefreshResponse {
  access_token: string
  token_type: string
}
