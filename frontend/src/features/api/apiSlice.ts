import {
  createApi,
  fetchBaseQuery,
  type BaseQueryFn,
  type FetchArgs,
  type FetchBaseQueryError,
} from '@reduxjs/toolkit/query/react'
import type { RootState } from '../../app/store'
import { updateAccessToken, logOut } from '../auth/authSlice'

const baseQuery = fetchBaseQuery({
  baseUrl: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  prepareHeaders: (headers, { getState }) => {
    const state = getState() as RootState
    const token = state.auth?.token || localStorage.getItem('token')
    if (token) {
      headers.set('authorization', `Bearer ${token}`)
    }
    return headers
  },
})

const baseQueryWithReauth: BaseQueryFn<
  string | FetchArgs,
  unknown,
  FetchBaseQueryError
> = async (args, api, extraOptions) => {
  let result = await baseQuery(args, api, extraOptions)

  if (result.error && result.error.status === 401) {
    // Try to refresh token
    const state = api.getState() as RootState
    const refreshToken = state.auth?.refreshToken || localStorage.getItem('refreshToken')

    if (refreshToken) {
      const refreshResult = await baseQuery(
        {
          url: '/auth/refresh',
          method: 'POST',
          body: { refresh_token: refreshToken },
        },
        api,
        extraOptions
      )

      if (refreshResult.data) {
        const data = refreshResult.data as { access_token: string }
        api.dispatch(updateAccessToken(data.access_token))
        // Retry original query
        result = await baseQuery(args, api, extraOptions)
      } else {
        // Refresh token failed, log out user
        api.dispatch(logOut())
      }
    } else {
      api.dispatch(logOut())
    }
  }

  return result
}

export const apiSlice = createApi({
  reducerPath: 'api',
  baseQuery: baseQueryWithReauth,
  tagTypes: ['User', 'Customer', 'Order', 'MealPlan', 'Enquiry', 'Driver'],
  endpoints: () => ({}),
})
