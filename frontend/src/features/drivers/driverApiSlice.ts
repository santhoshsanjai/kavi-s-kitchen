import { apiSlice } from '../api/apiSlice'
import type { Driver } from '../../types/order'

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
  }),
})

export const { useGetDriversQuery, useUpdateDriverStatusMutation } = driverApiSlice
