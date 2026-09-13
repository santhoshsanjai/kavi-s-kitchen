import { apiSlice } from '../api/apiSlice'
import type {
  Order,
  OrdersListResponse,
  OrderCreateInput,
  OrderStatus,
  MealSession,
} from '../../types/order'

export interface GetOrdersParams {
  date?: string
  meal_session?: MealSession
  status_filter?: OrderStatus
  driver_id?: string
  search?: string
}

export interface BulkAssignPayload {
  driver_id: string
  driver_name: string
  assignments: { order_id: string; sequence_number: number }[]
}

export const orderApiSlice = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getOrders: builder.query<OrdersListResponse, GetOrdersParams | void>({
      query: (params) => ({
        url: '/orders',
        params: params || {},
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Order' as const, id })),
              { type: 'Order', id: 'LIST' },
            ]
          : [{ type: 'Order', id: 'LIST' }],
    }),
    generateDailyOrders: builder.mutation<
      { message: string; date: string; generated_count: number; existing_count: number },
      { date: string }
    >({
      query: (body) => ({
        url: '/orders/generate-daily',
        method: 'POST',
        body,
      }),
      invalidatesTags: [{ type: 'Order', id: 'LIST' }],
    }),
    createOrder: builder.mutation<Order, OrderCreateInput>({
      query: (order) => ({
        url: '/orders',
        method: 'POST',
        body: order,
      }),
      invalidatesTags: [{ type: 'Order', id: 'LIST' }],
    }),
    updateOrder: builder.mutation<Order, { id: string; data: Partial<OrderCreateInput> }>({
      query: ({ id, data }) => ({
        url: `/orders/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Order', id },
        { type: 'Order', id: 'LIST' },
      ],
    }),
    updateOrderStatus: builder.mutation<Order, { id: string; status: OrderStatus; reason?: string }>({
      query: ({ id, status, reason }) => ({
        url: `/orders/${id}/status`,
        method: 'PATCH',
        body: { status, reason },
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Order', id },
        { type: 'Order', id: 'LIST' },
      ],
    }),
    bulkUpdateStatus: builder.mutation<{ message: string; modified_count: number }, { order_ids: string[]; status: OrderStatus }>({
      query: (body) => ({
        url: '/orders/bulk-status',
        method: 'PATCH',
        body,
      }),
      invalidatesTags: [{ type: 'Order', id: 'LIST' }],
    }),
    bulkAssignDriver: builder.mutation<{ message: string; assigned_count: number }, BulkAssignPayload>({
      query: (body) => ({
        url: '/orders/bulk-assign',
        method: 'POST',
        body,
      }),
      invalidatesTags: [
        { type: 'Order', id: 'LIST' },
        { type: 'Driver', id: 'LIST' },
      ],
    }),
    deleteOrder: builder.mutation<{ message: string; id: string }, string>({
      query: (id) => ({
        url: `/orders/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Order', id: 'LIST' }],
    }),
  }),
})

export const {
  useGetOrdersQuery,
  useGenerateDailyOrdersMutation,
  useCreateOrderMutation,
  useUpdateOrderMutation,
  useUpdateOrderStatusMutation,
  useBulkUpdateStatusMutation,
  useBulkAssignDriverMutation,
  useDeleteOrderMutation,
} = orderApiSlice
