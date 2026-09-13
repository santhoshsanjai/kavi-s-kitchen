import { apiSlice } from '../api/apiSlice'
import type { Enquiry, EnquiryCreateInput, Customer } from '../../types/customer'

export interface GetEnquiriesParams {
  search?: string
  status_filter?: string
  diet_type?: string
  skip?: number
  limit?: number
}

export interface EnquiriesResponse {
  items: Enquiry[]
  total: number
  skip: number
  limit: number
}

export interface ConvertEnquiryPayload {
  address_line: string
  area: string
  city?: string
  landmark?: string
  pincode?: string
  latitude?: number
  longitude?: number
}

export interface ConvertEnquiryResponse {
  enquiry: Enquiry
  customer: Customer
}

export const enquiryApiSlice = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getEnquiries: builder.query<EnquiriesResponse, GetEnquiriesParams | void>({
      query: (params) => ({
        url: '/enquiries',
        params: params || {},
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.items.map(({ id }) => ({ type: 'Enquiry' as const, id })),
              { type: 'Enquiry', id: 'LIST' },
            ]
          : [{ type: 'Enquiry', id: 'LIST' }],
    }),
    createEnquiry: builder.mutation<Enquiry, EnquiryCreateInput>({
      query: (enquiry) => ({
        url: '/enquiries',
        method: 'POST',
        body: enquiry,
      }),
      invalidatesTags: [{ type: 'Enquiry', id: 'LIST' }],
    }),
    updateEnquiry: builder.mutation<Enquiry, { id: string; data: Partial<EnquiryCreateInput> }>({
      query: ({ id, data }) => ({
        url: `/enquiries/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'Enquiry', id },
        { type: 'Enquiry', id: 'LIST' },
      ],
    }),
    convertEnquiryToCustomer: builder.mutation<
      ConvertEnquiryResponse,
      { id: string; data: ConvertEnquiryPayload }
    >({
      query: ({ id, data }) => ({
        url: `/enquiries/${id}/convert`,
        method: 'POST',
        body: data,
      }),
      invalidatesTags: [
        { type: 'Enquiry', id: 'LIST' },
        { type: 'Customer', id: 'LIST' },
      ],
    }),
    deleteEnquiry: builder.mutation<{ message: string; id: string }, string>({
      query: (id) => ({
        url: `/enquiries/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'Enquiry', id: 'LIST' }],
    }),
  }),
})

export const {
  useGetEnquiriesQuery,
  useCreateEnquiryMutation,
  useUpdateEnquiryMutation,
  useConvertEnquiryToCustomerMutation,
  useDeleteEnquiryMutation,
} = enquiryApiSlice
