import React, { useState } from 'react'
import {
  useGetMealPlansQuery,
  useCreateMealPlanMutation,
  useUpdateMealPlanMutation,
  useDeleteMealPlanMutation,
} from '../../features/mealPlans/mealPlanApiSlice'
import type {
  MealPlan,
  MealPlanCreateInput,
  DietType,
  MealSession,
} from '../../types/customer'
import {
  UtensilsCrossed,
  Plus,
  Calendar,
  Loader2,
  AlertCircle,
  Trash2,
  Edit2,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '../../components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../../components/ui/dialog'

export const MealPlansPage: React.FC = () => {
  const { data: plans = [], isLoading, refetch } = useGetMealPlansQuery()
  const [createPlan, { isLoading: isCreating }] = useCreateMealPlanMutation()
  const [updatePlan] = useUpdateMealPlanMutation()
  const [deletePlan] = useDeleteMealPlanMutation()

  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingPlan, setEditingPlan] = useState<MealPlan | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  const [formData, setFormData] = useState<MealPlanCreateInput>({
    name: '',
    diet_type: 'VEG',
    meal_sessions: ['LUNCH'],
    price: 2999,
    billing_cycle: 'MONTHLY',
    service_days: 26,
    delivery_eligible: true,
    is_active: true,
    description: '',
  })

  const openCreateModal = () => {
    setEditingPlan(null)
    setFormData({
      name: '',
      diet_type: 'VEG',
      meal_sessions: ['LUNCH'],
      price: 2999,
      billing_cycle: 'MONTHLY',
      service_days: 26,
      delivery_eligible: true,
      is_active: true,
      description: '',
    })
    setFormError(null)
    setIsModalOpen(true)
  }

  const openEditModal = (plan: MealPlan) => {
    setEditingPlan(plan)
    setFormData({
      name: plan.name,
      diet_type: plan.diet_type,
      meal_sessions: plan.meal_sessions,
      price: plan.price,
      billing_cycle: plan.billing_cycle,
      service_days: plan.service_days,
      delivery_eligible: plan.delivery_eligible,
      is_active: plan.is_active,
      description: plan.description || '',
    })
    setFormError(null)
    setIsModalOpen(true)
  }

  const handleSessionToggle = (session: MealSession) => {
    setFormData((prev) => {
      const exists = prev.meal_sessions.includes(session)
      const updated = exists
        ? prev.meal_sessions.filter((s) => s !== session)
        : [...prev.meal_sessions, session]
      return {
        ...prev,
        meal_sessions: updated.length > 0 ? updated : [session],
      }
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!formData.name.trim() || formData.price <= 0) {
      setFormError('Plan name and a valid price are required.')
      return
    }

    try {
      if (editingPlan) {
        await updatePlan({ id: editingPlan.id, data: formData }).unwrap()
      } else {
        await createPlan(formData).unwrap()
      }
      setIsModalOpen(false)
      refetch()
    } catch (err: any) {
      setFormError(err?.data?.detail || 'Failed to save meal plan.')
    }
  }

  const handleToggleActive = async (plan: MealPlan) => {
    try {
      await updatePlan({ id: plan.id, data: { is_active: !plan.is_active } }).unwrap()
      refetch()
    } catch (err) {
      console.error('Toggle active error', err)
    }
  }

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to remove this meal plan?')) {
      try {
        await deletePlan(id).unwrap()
        refetch()
      } catch (err) {
        console.error('Delete plan error', err)
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 font-serif">
            Configurable Meal Plans
          </h1>
          <p className="text-sm text-stone-500 mt-1">
            Configure monthly subscription tiers, meal session inclusions, and pricing.
          </p>
        </div>

        <Button
          onClick={openCreateModal}
          className="bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-2 shadow-md"
        >
          <Plus className="w-4 h-4" />
          <span>Create Meal Plan</span>
        </Button>
      </div>

      {/* Plans Grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-16 text-stone-500 gap-2">
          <Loader2 className="w-8 h-8 animate-spin text-amber-600" />
          <span className="text-xs">Loading meal plans...</span>
        </div>
      ) : plans.length === 0 ? (
        <div className="text-center py-16 text-stone-400 bg-white rounded-xl border border-dashed border-stone-300">
          <UtensilsCrossed className="w-10 h-10 mx-auto text-stone-300" />
          <h3 className="mt-2 text-sm font-semibold text-stone-700">No Meal Plans Defined</h3>
          <p className="text-xs text-stone-400 mt-1">Click "Create Meal Plan" to add your first subscription tier.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {plans.map((plan) => (
            <Card
              key={plan.id}
              className={`border transition-all flex flex-col justify-between ${
                plan.is_active
                  ? 'border-stone-200 hover:shadow-md hover:border-amber-400 bg-white'
                  : 'border-stone-200 bg-stone-50/70 opacity-75'
              }`}
            >
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span
                      className={`inline-block px-2.5 py-0.5 rounded-full text-[11px] font-bold ${
                        plan.diet_type === 'VEG'
                          ? 'bg-emerald-100 text-emerald-900'
                          : 'bg-red-100 text-red-900'
                      }`}
                    >
                      {plan.diet_type === 'VEG' ? 'Vegetarian' : 'Non-Vegetarian'}
                    </span>
                    <CardTitle className="text-lg font-bold text-stone-900 mt-2">
                      {plan.name}
                    </CardTitle>
                  </div>

                  <button
                    onClick={() => handleToggleActive(plan)}
                    className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                      plan.is_active
                        ? 'bg-emerald-50 text-emerald-700 border border-emerald-300'
                        : 'bg-stone-100 text-stone-500 border border-stone-300'
                    }`}
                  >
                    {plan.is_active ? 'Active' : 'Paused'}
                  </button>
                </div>

                <div className="flex items-baseline gap-1 mt-3">
                  <span className="text-3xl font-extrabold text-stone-900 font-sans">
                    ₹{plan.price.toLocaleString()}
                  </span>
                  <span className="text-xs text-stone-500 font-medium">/{plan.billing_cycle.toLowerCase()}</span>
                </div>
              </CardHeader>

              <CardContent className="space-y-3 text-xs flex-1">
                {plan.description && (
                  <p className="text-stone-600 leading-relaxed">{plan.description}</p>
                )}

                <div className="pt-2 border-t border-stone-100 space-y-1.5">
                  <div className="flex items-center gap-2 text-stone-600">
                    <Calendar className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>
                      <strong>{plan.service_days} service days</strong> (Mon – Sat)
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 flex-wrap pt-1">
                    <span className="text-stone-500">Includes:</span>
                    {plan.meal_sessions.map((session) => (
                      <span
                        key={session}
                        className="px-2 py-0.5 rounded bg-amber-50 text-amber-900 text-[10px] font-bold border border-amber-200"
                      >
                        {session}
                      </span>
                    ))}
                  </div>
                </div>
              </CardContent>

              <CardFooter className="pt-3 border-t border-stone-100 flex items-center justify-between">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => openEditModal(plan)}
                  className="text-xs text-stone-600 hover:text-amber-800"
                >
                  <Edit2 className="w-3.5 h-3.5 mr-1" />
                  <span>Edit Plan</span>
                </Button>

                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleDelete(plan.id)}
                  className="text-xs text-stone-400 hover:text-red-700"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </Button>
              </CardFooter>
            </Card>
          ))}
        </div>
      )}

      {/* Create / Edit Plan Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-md bg-white border-stone-200">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold font-serif text-stone-900">
              {editingPlan ? 'Edit Meal Plan' : 'Create New Meal Plan'}
            </DialogTitle>
            <DialogDescription className="text-xs text-stone-500">
              Define the name, sessions, and monthly pricing for this plan.
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="p-2.5 rounded bg-red-50 text-red-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4 my-2">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Plan Name *</Label>
              <Input
                required
                placeholder="e.g. Veg Full Day"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                className="text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Diet Type</Label>
                <select
                  value={formData.diet_type}
                  onChange={(e) => setFormData({ ...formData, diet_type: e.target.value as DietType })}
                  className="w-full text-sm rounded border border-stone-200 p-2"
                >
                  <option value="VEG">Vegetarian</option>
                  <option value="NON_VEG">Non-Vegetarian</option>
                </select>
              </div>

              <div className="space-y-1">
                <Label className="text-xs font-semibold">Price (₹) *</Label>
                <Input
                  type="number"
                  required
                  min={1}
                  value={formData.price}
                  onChange={(e) => setFormData({ ...formData, price: parseFloat(e.target.value) || 0 })}
                  className="text-sm"
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label className="text-xs font-semibold">Included Meal Sessions</Label>
              <div className="grid grid-cols-3 gap-2">
                {(['BREAKFAST', 'LUNCH', 'DINNER'] as const).map((session) => {
                  const isSelected = formData.meal_sessions.includes(session)
                  return (
                    <button
                      key={session}
                      type="button"
                      onClick={() => handleSessionToggle(session)}
                      className={`p-2 rounded text-xs font-bold border transition-all ${
                        isSelected
                          ? 'bg-amber-100 border-amber-500 text-amber-900 shadow-xs'
                          : 'bg-white border-stone-200 text-stone-500'
                      }`}
                    >
                      {session}
                    </button>
                  )
                })}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Service Days</Label>
                <Input
                  type="number"
                  value={formData.service_days}
                  onChange={(e) =>
                    setFormData({ ...formData, service_days: parseInt(e.target.value) || 26 })
                  }
                  className="text-sm"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Billing Cycle</Label>
                <select
                  value={formData.billing_cycle}
                  onChange={(e) => setFormData({ ...formData, billing_cycle: e.target.value })}
                  className="w-full text-sm rounded border border-stone-200 p-2"
                >
                  <option value="MONTHLY">Monthly</option>
                  <option value="WEEKLY">Weekly</option>
                  <option value="DAILY">Daily</option>
                </select>
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Description</Label>
              <Input
                placeholder="Brief plan summary"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="text-sm"
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isCreating}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold"
              >
                {isCreating ? 'Saving...' : editingPlan ? 'Update Plan' : 'Create Plan'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
