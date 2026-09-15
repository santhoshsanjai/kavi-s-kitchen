import { apiSlice } from '../api/apiSlice'
import type { Driver, DriverTodayDeliveriesResponse, LiveDriver } from '../../types/order'

export const driverApiSlice = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getDrivers: builder.query<Driver[], void>({
      query: () => '/drivers',
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({ type: 'Driver' as const, id })),
              { type: 'Driver', id: 'LIST' },
            ]
          : [{ type: 'Driver', id: 'LIST' }],
    }),
    getMyTodayDeliveries: builder.query<DriverTodayDeliveriesResponse, void>({
      query: () => '/drivers/me/today-deliveries',
      providesTags: ['Order', 'Driver'],
    }),
    updateDriverStatus: builder.mutation<
      { message: string; driving_status: string },
      { id: string; driving_status: string }
    >({
      query: ({ id, driving_status }) => ({
        url: `/drivers/${id}/status`,
        method: 'PATCH',
        body: { driving_status },
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Driver', id },
        { type: 'Driver', id: 'LIST' },
      ],
    }),
    updateMyStatus: builder.mutation<
      { message: string; driving_status: string },
      { driving_status: string }
    >({
      query: (body) => ({
        url: '/drivers/me/status',
        method: 'PATCH',
        body,
      }),
      invalidatesTags: ['Driver', 'Order'],
    }),
    getLiveDrivers: builder.query<LiveDriver[], void>({
      query: () => '/tracking/live-drivers',
      providesTags: ['Driver', 'Order'],
    }),
  }),
})

export const {
  useGetDriversQuery,
  useGetMyTodayDeliveriesQuery,
  useUpdateDriverStatusMutation,
  useUpdateMyStatusMutation,
  useGetLiveDriversQuery,
} = driverApiSlice
