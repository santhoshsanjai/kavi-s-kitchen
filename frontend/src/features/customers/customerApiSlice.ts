import { apiSlice } from '../api/apiSlice'
import type { Customer, CustomerCreateInput } from '../../types/customer'

export interface GetCustomersParams {
  search?: string
  is_active?: boolean
  customer_type?: string
  diet_type?: string
  skip?: number
  limit?: number
}

export interface CustomersResponse {
  items: Customer[]
  total: number
  skip: number
  limit: number
}

export const customerApiSlice = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getCustomers: builder.query<CustomersResponse, GetCustomersParams | void>({
      query: (params) => ({
        url: '/customers',
        params: params || {},
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Customer' as const, id })),
              { type: 'Customer', id: 'LIST' },
            ]
          : [{ type: 'Customer', id: 'LIST' }],
    }),
    getCustomerById: builder.query<Customer, string>({
      query: (id) => `/customers/${id}`,
      providesTags: (_result, _error, id) => [{ type: 'Customer', id }],
    }),
    createCustomer: builder.mutation<Customer, CustomerCreateInput>({
      query: (customer) => ({
        url: '/customers',
        method: 'POST',
        body: customer,
      }),
      invalidatesTags: [{ type: 'Customer', id: 'LIST' }],
    }),
    updateCustomer: builder.mutation<Customer, { id: string; data: Partial<CustomerCreateInput> }>({
      query: ({ id, data }) => ({
        url: `/customers/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Customer', id },
        { type: 'Customer', id: 'LIST' },
      ],
    }),
    toggleCustomerStatus: builder.mutation<Customer, { id: string; is_active: boolean }>({
      query: ({ id, is_active }) => ({
        url: `/customers/${id}/status`,
        method: 'PATCH',
        body: { is_active },
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Customer', id },
        { type: 'Customer', id: 'LIST' },
      ],
    }),
    deleteCustomer: builder.mutation<{ message: string; id: string }, string>({
      query: (id) => ({
        url: `/customers/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Customer', id: 'LIST' }],
    }),
  }),
})

export const {
  useGetCustomersQuery,
  useGetCustomerByIdQuery,
  useCreateCustomerMutation,
  useUpdateCustomerMutation,
  useToggleCustomerStatusMutation,
  useDeleteCustomerMutation,
} = customerApiSlice
