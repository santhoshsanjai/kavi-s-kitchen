import { createSlice, type PayloadAction } from '@reduxjs/toolkit'
import type { AuthState, User, UserRole } from '../../types/auth'

const loadInitialState = (): AuthState => {
  try {
    const token = localStorage.getItem('token')
    const refreshToken = localStorage.getItem('refreshToken')
    const userStr = localStorage.getItem('user')
    const role = localStorage.getItem('role') as UserRole | null
    const permissionsStr = localStorage.getItem('permissions')

    const user: User | null = userStr ? JSON.parse(userStr) : null
    const permissions: string[] = permissionsStr ? JSON.parse(permissionsStr) : []

    return {
      user,
      token,
      refreshToken,
      role,
      permissions,
      isAuthenticated: Boolean(token && user),
    }
  } catch (e) {
    console.error('Failed to load auth from localStorage', e)
    return {
      user: null,
      token: null,
      refreshToken: null,
      role: null,
      permissions: [],
      isAuthenticated: false,
    }
  }
}

const initialState: AuthState = loadInitialState()

export const authSlice = createSlice({
  name: 'auth',
  initialState,
  reducers: {
    setCredentials: (
      state,
      action: PayloadAction<{
        access_token: string
        refresh_token?: string
        user: User
        role: UserRole
        permissions?: string[]
      }>
    ) => {
      const { access_token, refresh_token, user, role, permissions = [] } = action.payload

      state.token = access_token
      if (refresh_token) {
        state.refreshToken = refresh_token
      }
      state.user = user
      state.role = role
      state.permissions = permissions
      state.isAuthenticated = true

      localStorage.setItem('token', access_token)
      if (refresh_token) {
        localStorage.setItem('refreshToken', refresh_token)
      }
      localStorage.setItem('user', JSON.stringify(user))
      localStorage.setItem('role', role)
      localStorage.setItem('permissions', JSON.stringify(permissions))
    },
    updateAccessToken: (state, action: PayloadAction<string>) => {
      state.token = action.payload
      localStorage.setItem('token', action.payload)
    },
    logOut: (state) => {
      state.user = null
      state.token = null
      state.refreshToken = null
      state.role = null
      state.permissions = []
      state.isAuthenticated = false

      localStorage.removeItem('token')
      localStorage.removeItem('refreshToken')
      localStorage.removeItem('user')
      localStorage.removeItem('role')
      localStorage.removeItem('permissions')
    },
  },
})

export const { setCredentials, updateAccessToken, logOut } = authSlice.actions

export default authSlice.reducer
