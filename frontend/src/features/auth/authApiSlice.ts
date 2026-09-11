import { apiSlice } from '../api/apiSlice'
import type { LoginResponse, UserRole, User } from '../../types/auth'

export interface LoginRequest {
  identifier: string
  password: string
}

export interface RefreshRequest {
  refresh_token: string
}

export interface MeResponse {
  user: User
  role: UserRole
  permissions: string[]
}

export const authApiSlice = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    login: builder.mutation<LoginResponse, LoginRequest>({
      query: (credentials) => ({
        url: '/auth/login',
        method: 'POST',
        body: credentials,
      }),
      invalidatesTags: ['User'],
    }),
    refreshToken: builder.mutation<{ access_token: string; token_type: string }, RefreshRequest>({
      query: (body) => ({
        url: '/auth/refresh',
        method: 'POST',
        body,
      }),
    }),
    getMe: builder.query<MeResponse, void>({
      query: () => '/auth/me',
      providesTags: ['User'],
    }),
    logout: builder.mutation<{ message: string }, void>({
      query: () => ({
        url: '/auth/logout',
        method: 'POST',
      }),
      invalidatesTags: ['User'],
    }),
  }),
})

export const {
  useLoginMutation,
  useRefreshTokenMutation,
  useGetMeQuery,
  useLogoutMutation,
} = authApiSlice
