import { apiSlice } from '../api/apiSlice'
import type { MealPlan, MealPlanCreateInput } from '../../types/customer'

export const mealPlanApiSlice = apiSlice.injectEndpoints({
  endpoints: (builder) => ({
    getMealPlans: builder.query<MealPlan[], { is_active?: boolean; diet_type?: string } | void>({
      query: (params) => ({
        url: '/meal-plans',
        params: params || {},
      }),
      providesTags: (result) =>
        result
          ? [
              ...result.map(({ id }) => ({ type: 'MealPlan' as const, id })),
              { type: 'MealPlan', id: 'LIST' },
            ]
          : [{ type: 'MealPlan', id: 'LIST' }],
    }),
    createMealPlan: builder.mutation<MealPlan, MealPlanCreateInput>({
      query: (plan) => ({
        url: '/meal-plans',
        method: 'POST',
        body: plan,
      }),
      invalidatesTags: [{ type: 'MealPlan', id: 'LIST' }],
    }),
    updateMealPlan: builder.mutation<MealPlan, { id: string; data: Partial<MealPlanCreateInput> }>({
      query: ({ id, data }) => ({
        url: `/meal-plans/${id}`,
        method: 'PUT',
        body: data,
      }),
      invalidatesTags: (_result, _error, { id }) => [
        { type: 'MealPlan', id },
        { type: 'MealPlan', id: 'LIST' },
      ],
    }),
    deleteMealPlan: builder.mutation<{ message: string; id: string }, string>({
      query: (id) => ({
        url: `/meal-plans/${id}`,
        method: 'DELETE',
      }),
      invalidatesTags: [{ type: 'MealPlan', id: 'LIST' }],
    }),
  }),
})

export const {
  useGetMealPlansQuery,
  useCreateMealPlanMutation,
  useUpdateMealPlanMutation,
  useDeleteMealPlanMutation,
} = mealPlanApiSlice
