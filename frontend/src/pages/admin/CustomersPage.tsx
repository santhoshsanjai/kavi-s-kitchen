import React, { useState } from 'react'
import {
  useGetCustomersQuery,
  useCreateCustomerMutation,
  useUpdateCustomerMutation,
  useToggleCustomerStatusMutation,
  useDeleteCustomerMutation,
} from '../../features/customers/customerApiSlice'
import type {
  Customer,
  CustomerCreateInput,
  CustomerType,
  MealSession,
  SpiceLevel,
} from '../../types/customer'
import {
  Users,
  Search,
  Plus,
  Edit2,
  Trash2,
  MapPin,
  Phone,
  Compass,
  CheckCircle2,
  XCircle,
  AlertCircle,
  Loader2,
  Eye,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Card, CardContent } from '../../components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../../components/ui/dialog'
import { LocationPickerModal, type SelectedLocation } from '../../components/maps/LocationPickerModal'

export const CustomersPage: React.FC = () => {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'ACTIVE' | 'INACTIVE'>('ALL')
  const [dietFilter, setDietFilter] = useState<string>('ALL')

  // API Query
  const { data, isLoading, refetch } = useGetCustomersQuery({
    search: search ? search.trim() : undefined,
    is_active: statusFilter === 'ALL' ? undefined : statusFilter === 'ACTIVE',
    diet_type: dietFilter === 'ALL' ? undefined : dietFilter,
  })

  // Mutations
  const [createCustomer, { isLoading: isCreating }] = useCreateCustomerMutation()
  const [updateCustomer, { isLoading: isUpdating }] = useUpdateCustomerMutation()
  const [toggleStatus] = useToggleCustomerStatusMutation()
  const [deleteCustomer] = useDeleteCustomerMutation()

  // Modal State
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isMapOpen, setIsMapOpen] = useState(false)
  const [editingCustomer, setEditingCustomer] = useState<Customer | null>(null)
  const [viewCustomer, setViewCustomer] = useState<Customer | null>(null)
  const [deleteCandidate, setDeleteCandidate] = useState<Customer | null>(null)
  const [formError, setFormError] = useState<string | null>(null)

  // Form State
  const [formData, setFormData] = useState<CustomerCreateInput>({
    name: '',
    phone: '',
    alternate_phone: '',
    whatsapp_number: '',
    customer_type: 'INDIVIDUAL',
    is_active: true,
    address: {
      address_line: '',
      area: 'Anna Nagar East',
      landmark: '',
      city: 'Chennai',
      pincode: '600102',
      latitude: 13.0850,
      longitude: 80.2150,
      formatted_address: 'Anna Nagar East, Chennai 600102',
    },
    meal_preference: {
      diet_type: 'VEG',
      sessions: ['LUNCH'],
      spice_level: 'NORMAL',
      rice_preference: 'Ponni Rice',
      food_exclusions: '',
      allergy_note: '',
      delivery_instructions: '',
    },
    notes: '',
  })

  const openCreateModal = () => {
    setEditingCustomer(null)
    setFormData({
      name: '',
      phone: '',
      alternate_phone: '',
      whatsapp_number: '',
      customer_type: 'INDIVIDUAL',
      is_active: true,
      address: {
        address_line: '',
        area: 'Anna Nagar East',
        landmark: '',
        city: 'Chennai',
        pincode: '600102',
        latitude: 13.0850,
        longitude: 80.2150,
        formatted_address: 'Anna Nagar East, Chennai 600102',
      },
      meal_preference: {
        diet_type: 'VEG',
        sessions: ['LUNCH'],
        spice_level: 'NORMAL',
        rice_preference: 'Ponni Rice',
        food_exclusions: '',
        allergy_note: '',
        delivery_instructions: '',
      },
      notes: '',
    })
    setFormError(null)
    setIsFormOpen(true)
  }

  const openEditModal = (customer: Customer) => {
    setEditingCustomer(customer)
    setFormData({
      name: customer.name,
      phone: customer.phone,
      alternate_phone: customer.alternate_phone || '',
      whatsapp_number: customer.whatsapp_number || '',
      customer_type: customer.customer_type,
      is_active: customer.is_active,
      address: { ...customer.address },
      meal_preference: { ...customer.meal_preference },
      notes: customer.notes || '',
    })
    setFormError(null)
    setIsFormOpen(true)
  }

  const handleLocationPicked = (loc: SelectedLocation) => {
    setFormData((prev) => ({
      ...prev,
      address: {
        ...prev.address,
        area: loc.area,
        city: loc.city,
        pincode: loc.pincode,
        latitude: loc.latitude,
        longitude: loc.longitude,
        google_place_id: loc.google_place_id,
        formatted_address: loc.formatted_address,
      },
    }))
  }

  const handleSessionToggle = (session: MealSession) => {
    setFormData((prev) => {
      const current = prev.meal_preference.sessions
      const exists = current.includes(session)
      const updated = exists ? current.filter((s) => s !== session) : [...current, session]
      return {
        ...prev,
        meal_preference: {
          ...prev.meal_preference,
          sessions: updated.length > 0 ? updated : [session],
        },
      }
    })
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!formData.name.trim() || !formData.phone.trim()) {
      setFormError('Customer name and phone number are required.')
      return
    }

    if (!formData.address.address_line.trim()) {
      setFormError('Delivery street address / door number is required.')
      return
    }

    try {
      if (editingCustomer) {
        await updateCustomer({ id: editingCustomer.id, data: formData }).unwrap()
      } else {
        await createCustomer(formData).unwrap()
      }
      setIsFormOpen(false)
      refetch()
    } catch (err: any) {
      setFormError(err?.data?.detail || 'Failed to save customer. Please check your inputs.')
    }
  }

  const handleToggleStatus = async (customer: Customer) => {
    try {
      await toggleStatus({ id: customer.id, is_active: !customer.is_active }).unwrap()
    } catch (err) {
      console.error('Status toggle failed', err)
    }
  }

  const handleDeleteConfirm = async () => {
    if (!deleteCandidate) return
    try {
      await deleteCustomer(deleteCandidate.id).unwrap()
      setDeleteCandidate(null)
      refetch()
    } catch (err) {
      console.error('Failed to delete customer', err)
    }
  }

  const customers = data?.items || []
  const totalCount = data?.total || 0
  const activeCount = customers.filter((c) => c.is_active).length
  const vegCount = customers.filter((c) => c.meal_preference.diet_type === 'VEG').length

  return (
    <div className="space-y-6">
      {/* Header & Quick Action */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 font-serif">
            Customer Master & Subscriptions
          </h1>
          <p className="text-sm text-stone-500 mt-1">
            Manage customer directories, delivery coordinates, and daily meal preferences.
          </p>
        </div>

        <Button
          onClick={openCreateModal}
          className="bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-2 shadow-md hover:shadow-lg transition-all"
        >
          <Plus className="w-4 h-4" />
          <span>Add New Customer</span>
        </Button>
      </div>

      {/* Metrics Summary Strip */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <Card className="border-stone-200">
          <CardContent className="p-4">
            <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Total Customers</div>
            <div className="text-2xl font-bold text-stone-900 mt-1">{totalCount}</div>
          </CardContent>
        </Card>
        <Card className="border-stone-200">
          <CardContent className="p-4">
            <div className="text-xs font-semibold text-emerald-600 uppercase tracking-wider">Active Deliveries</div>
            <div className="text-2xl font-bold text-emerald-700 mt-1">{activeCount}</div>
          </CardContent>
        </Card>
        <Card className="border-stone-200">
          <CardContent className="p-4">
            <div className="text-xs font-semibold text-stone-500 uppercase tracking-wider">Inactive / Paused</div>
            <div className="text-2xl font-bold text-stone-600 mt-1">{totalCount - activeCount}</div>
          </CardContent>
        </Card>
        <Card className="border-stone-200">
          <CardContent className="p-4">
            <div className="text-xs font-semibold text-amber-700 uppercase tracking-wider">Veg Preferences</div>
            <div className="text-2xl font-bold text-amber-800 mt-1">{vegCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filter and Search Bar */}
      <Card className="border-stone-200 shadow-sm">
        <CardContent className="p-4 space-y-3 sm:space-y-0 sm:flex sm:items-center sm:justify-between gap-4">
          <div className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              type="text"
              placeholder="Search by customer name, phone, area..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 text-sm"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Status Tabs */}
            <div className="inline-flex rounded-lg border border-stone-200 bg-stone-50 p-1 text-xs">
              {(['ALL', 'ACTIVE', 'INACTIVE'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`px-3 py-1 font-semibold rounded-md transition-all ${
                    statusFilter === status
                      ? 'bg-white text-stone-900 shadow-xs'
                      : 'text-stone-500 hover:text-stone-900'
                  }`}
                >
                  {status === 'ALL' ? 'All' : status === 'ACTIVE' ? 'Active' : 'Inactive'}
                </button>
              ))}
            </div>

            {/* Diet Filter */}
            <select
              value={dietFilter}
              onChange={(e) => setDietFilter(e.target.value)}
              className="text-xs rounded-lg border border-stone-200 bg-white px-3 py-1.5 text-stone-700 focus:outline-none focus:ring-1 focus:ring-amber-500 font-medium"
            >
              <option value="ALL">All Diets</option>
              <option value="VEG">Veg Only</option>
              <option value="NON_VEG">Non-Veg Only</option>
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Customer Directory Table */}
      <Card className="border-stone-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-stone-700">
            <thead className="bg-stone-50 border-b border-stone-200 text-xs font-semibold text-stone-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Delivery Address</th>
                <th className="px-4 py-3">Meal Preferences</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan={5} className="text-center py-12">
                    <div className="flex flex-col items-center justify-center gap-2 text-stone-500">
                      <Loader2 className="w-6 h-6 animate-spin text-amber-600" />
                      <span className="text-xs">Loading customer directory...</span>
                    </div>
                  </td>
                </tr>
              ) : customers.length === 0 ? (
                <tr>
                  <td colSpan={5} className="text-center py-12">
                    <div className="flex flex-col items-center justify-center gap-2 text-stone-400">
                      <Users className="w-8 h-8 stroke-1 text-stone-300" />
                      <span className="text-sm font-medium text-stone-600">No customers found</span>
                      <span className="text-xs text-stone-400">
                        Try modifying your search or click "Add New Customer" above.
                      </span>
                    </div>
                  </td>
                </tr>
              ) : (
                customers.map((cust) => (
                  <tr key={cust.id} className="hover:bg-stone-50/70 transition-colors">
                    {/* Customer Basic Info */}
                    <td className="px-4 py-3">
                      <div className="font-bold text-stone-900 text-sm">{cust.name}</div>
                      <div className="flex items-center gap-1 text-xs text-stone-500 mt-0.5">
                        <Phone className="w-3 h-3 text-stone-400" />
                        <span>{cust.phone}</span>
                      </div>
                      <span className="inline-block mt-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-stone-100 text-stone-600">
                        {cust.customer_type}
                      </span>
                    </td>

                    {/* Address & GPS */}
                    <td className="px-4 py-3 max-w-xs">
                      <div className="text-xs text-stone-800 font-medium truncate">
                        {cust.address.address_line}
                      </div>
                      <div className="flex items-center gap-1 text-xs text-stone-500 mt-0.5">
                        <MapPin className="w-3 h-3 text-amber-600 shrink-0" />
                        <span>
                          {cust.address.area}, {cust.address.pincode}
                        </span>
                      </div>
                      {cust.address.landmark && (
                        <div className="text-[11px] text-stone-400 italic">
                          Near {cust.address.landmark}
                        </div>
                      )}
                    </td>

                    {/* Meal Preferences */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        <span
                          className={`inline-block px-2 py-0.5 rounded-full text-[11px] font-bold ${
                            cust.meal_preference.diet_type === 'VEG'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {cust.meal_preference.diet_type}
                        </span>
                        <span className="text-xs text-stone-500 font-medium">
                          &bull; {cust.meal_preference.spice_level}
                        </span>
                      </div>
                      <div className="flex flex-wrap gap-1 mt-1">
                        {cust.meal_preference.sessions.map((s) => (
                          <span
                            key={s}
                            className="px-1.5 py-0.5 rounded bg-amber-50 text-amber-900 text-[10px] font-medium border border-amber-200"
                          >
                            {s}
                          </span>
                        ))}
                      </div>
                    </td>

                    {/* Active / Inactive Status Toggle */}
                    <td className="px-4 py-3">
                      <button
                        onClick={() => handleToggleStatus(cust)}
                        className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold transition-all ${
                          cust.is_active
                            ? 'bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100'
                            : 'bg-stone-100 text-stone-600 border border-stone-300 hover:bg-stone-200'
                        }`}
                      >
                        {cust.is_active ? (
                          <>
                            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                            <span>Active</span>
                          </>
                        ) : (
                          <>
                            <XCircle className="w-3.5 h-3.5 text-stone-500" />
                            <span>Paused</span>
                          </>
                        )}
                      </button>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setViewCustomer(cust)}
                          className="p-1.5 h-8 text-stone-500 hover:text-stone-900"
                          title="View Profile"
                        >
                          <Eye className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => openEditModal(cust)}
                          className="p-1.5 h-8 text-amber-700 hover:text-amber-800 hover:bg-amber-50"
                          title="Edit Customer"
                        >
                          <Edit2 className="w-4 h-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => setDeleteCandidate(cust)}
                          className="p-1.5 h-8 text-stone-400 hover:text-red-700 hover:bg-red-50"
                          title="Delete Customer"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Add / Edit Customer Modal */}
      <Dialog open={isFormOpen} onOpenChange={setIsFormOpen}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto bg-white border-stone-200">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold font-serif text-stone-900">
              {editingCustomer ? 'Edit Customer Details' : 'Register New Customer'}
            </DialogTitle>
            <DialogDescription className="text-xs text-stone-500">
              Fill in customer profile information, delivery address, and meal diet preferences.
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="p-3 rounded-lg bg-red-50 border border-red-200 flex items-center gap-2 text-red-800 text-xs">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-600" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5 my-2">
            {/* 1. Basic Information */}
            <div className="space-y-3 border-b border-stone-200 pb-4">
              <h3 className="text-xs font-bold text-stone-700 uppercase tracking-wider">
                1. Basic Information
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Full Name *</Label>
                  <Input
                    required
                    placeholder="e.g. Anitha Sharma"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Phone Number *</Label>
                  <Input
                    required
                    placeholder="e.g. 9840123456"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">WhatsApp Number</Label>
                  <Input
                    placeholder="e.g. 9840123456"
                    value={formData.whatsapp_number}
                    onChange={(e) => setFormData({ ...formData, whatsapp_number: e.target.value })}
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Customer Type</Label>
                  <select
                    value={formData.customer_type}
                    onChange={(e) =>
                      setFormData({ ...formData, customer_type: e.target.value as CustomerType })
                    }
                    className="w-full text-sm rounded-md border border-stone-200 bg-white p-2 text-stone-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
                  >
                    <option value="INDIVIDUAL">Individual</option>
                    <option value="FAMILY">Family</option>
                    <option value="OFFICE">Office / Corporate</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
              </div>
            </div>

            {/* 2. Address & Google Location */}
            <div className="space-y-3 border-b border-stone-200 pb-4">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold text-stone-700 uppercase tracking-wider">
                  2. Delivery Address & GPS Coordinates
                </h3>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsMapOpen(true)}
                  className="flex items-center gap-1.5 text-xs text-amber-800 border-amber-300 hover:bg-amber-50"
                >
                  <Compass className="w-3.5 h-3.5 text-amber-600" />
                  <span>Select on Map</span>
                </Button>
              </div>

              <div className="space-y-2">
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Door / Flat / Street Address *</Label>
                  <Input
                    required
                    placeholder="e.g. Flat 4B, Emerald Heights, 2nd Cross Street"
                    value={formData.address.address_line}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        address: { ...formData.address, address_line: e.target.value },
                      })
                    }
                    className="text-sm"
                  />
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Area / Locality *</Label>
                    <Input
                      required
                      placeholder="e.g. Anna Nagar East"
                      value={formData.address.area}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          address: { ...formData.address, area: e.target.value },
                        })
                      }
                      className="text-sm"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Landmark</Label>
                    <Input
                      placeholder="e.g. Near Metro Station"
                      value={formData.address.landmark}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          address: { ...formData.address, landmark: e.target.value },
                        })
                      }
                      className="text-sm"
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs font-semibold">Pincode</Label>
                    <Input
                      placeholder="e.g. 600102"
                      value={formData.address.pincode}
                      onChange={(e) =>
                        setFormData({
                          ...formData,
                          address: { ...formData.address, pincode: e.target.value },
                        })
                      }
                      className="text-sm"
                    />
                  </div>
                </div>

                {/* GPS Pin Badge Indicator */}
                <div className="flex items-center justify-between text-[11px] bg-stone-50 p-2.5 rounded-lg border border-stone-200">
                  <div className="flex items-center gap-1.5 text-stone-600">
                    <MapPin className="w-3.5 h-3.5 text-amber-600 shrink-0" />
                    <span>
                      Coordinates: <strong>{formData.address.latitude}</strong>,{' '}
                      <strong>{formData.address.longitude}</strong>
                    </span>
                  </div>
                  <span className="text-emerald-700 font-semibold bg-emerald-100 px-2 py-0.5 rounded-full text-[10px]">
                    GPS Pin Verified
                  </span>
                </div>
              </div>
            </div>

            {/* 3. Meal Preferences & Delivery Instructions */}
            <div className="space-y-3">
              <h3 className="text-xs font-bold text-stone-700 uppercase tracking-wider">
                3. Meal Diet & Delivery Preferences
              </h3>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Diet Category</Label>
                  <div className="grid grid-cols-2 gap-2">
                    {(['VEG', 'NON_VEG'] as const).map((diet) => (
                      <button
                        key={diet}
                        type="button"
                        onClick={() =>
                          setFormData({
                            ...formData,
                            meal_preference: { ...formData.meal_preference, diet_type: diet },
                          })
                        }
                        className={`p-2 rounded-lg text-xs font-bold border transition-all text-center ${
                          formData.meal_preference.diet_type === diet
                            ? diet === 'VEG'
                              ? 'bg-emerald-100 border-emerald-500 text-emerald-900 shadow-xs'
                              : 'bg-red-100 border-red-500 text-red-900 shadow-xs'
                            : 'bg-white border-stone-200 text-stone-600'
                        }`}
                      >
                        {diet === 'VEG' ? '🥗 Vegetarian' : '🍗 Non-Vegetarian'}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Spice Level</Label>
                  <select
                    value={formData.meal_preference.spice_level}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        meal_preference: {
                          ...formData.meal_preference,
                          spice_level: e.target.value as SpiceLevel,
                        },
                      })
                    }
                    className="w-full text-sm rounded-md border border-stone-200 bg-white p-2 text-stone-800 focus:outline-none focus:ring-1 focus:ring-amber-500"
                  >
                    <option value="MILD">Mild (Low spice)</option>
                    <option value="NORMAL">Normal (Standard South Indian)</option>
                    <option value="SPICY">Spicy (Authentic spicy)</option>
                  </select>
                </div>
              </div>

              {/* Sessions selector */}
              <div className="space-y-1.5 pt-1">
                <Label className="text-xs font-semibold">Scheduled Meal Sessions</Label>
                <div className="grid grid-cols-3 gap-2">
                  {(['BREAKFAST', 'LUNCH', 'DINNER'] as const).map((session) => {
                    const isSelected = formData.meal_preference.sessions.includes(session)
                    return (
                      <button
                        key={session}
                        type="button"
                        onClick={() => handleSessionToggle(session)}
                        className={`p-2 rounded-lg text-xs font-semibold border transition-all ${
                          isSelected
                            ? 'bg-amber-100 border-amber-500 text-amber-950 font-bold shadow-xs'
                            : 'bg-white border-stone-200 text-stone-500 hover:bg-stone-50'
                        }`}
                      >
                        {session === 'BREAKFAST'
                          ? '🌅 Breakfast'
                          : session === 'LUNCH'
                          ? '☀️ Lunch'
                          : '🌙 Dinner'}
                      </button>
                    )
                  })}
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Food Exclusions / Allergies</Label>
                  <Input
                    placeholder="e.g. No Brinjal, Nut allergy"
                    value={formData.meal_preference.food_exclusions}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        meal_preference: {
                          ...formData.meal_preference,
                          food_exclusions: e.target.value,
                        },
                      })
                    }
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Driver Delivery Instructions</Label>
                  <Input
                    placeholder="e.g. Ring bell twice, leave at reception"
                    value={formData.meal_preference.delivery_instructions}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        meal_preference: {
                          ...formData.meal_preference,
                          delivery_instructions: e.target.value,
                        },
                      })
                    }
                    className="text-sm"
                  />
                </div>
              </div>
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2 border-t border-stone-200">
              <Button type="button" variant="outline" onClick={() => setIsFormOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isCreating || isUpdating}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold"
              >
                {isCreating || isUpdating ? (
                  <span className="flex items-center gap-1.5">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Saving...
                  </span>
                ) : editingCustomer ? (
                  'Update Customer'
                ) : (
                  'Create Customer'
                )}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Location Picker Modal */}
      <LocationPickerModal
        isOpen={isMapOpen}
        onClose={() => setIsMapOpen(false)}
        onSelectLocation={handleLocationPicked}
        initialLocation={{
          latitude: formData.address.latitude,
          longitude: formData.address.longitude,
          area: formData.address.area,
        }}
      />

      {/* View Customer Details Drawer/Modal */}
      {viewCustomer && (
        <Dialog open={Boolean(viewCustomer)} onOpenChange={() => setViewCustomer(null)}>
          <DialogContent className="max-w-md bg-white border-stone-200">
            <DialogHeader>
              <DialogTitle className="text-lg font-bold font-serif text-stone-900">
                Customer Profile
              </DialogTitle>
              <DialogDescription className="text-xs text-stone-500">
                Full customer profile, dietary preferences, and delivery coordinates.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 my-2 text-sm">
              <div className="bg-stone-50 p-3.5 rounded-xl border border-stone-200 space-y-1.5">
                <div className="font-bold text-base text-stone-900">{viewCustomer.name}</div>
                <div className="text-xs text-stone-600 flex items-center gap-2">
                  <Phone className="w-3.5 h-3.5 text-stone-400" />
                  <span>{viewCustomer.phone}</span>
                </div>
                <div className="inline-block text-[10px] font-semibold px-2 py-0.5 rounded bg-amber-100 text-amber-900">
                  {viewCustomer.customer_type}
                </div>
              </div>

              <div className="space-y-1">
                <div className="text-xs font-bold text-stone-500 uppercase tracking-wider">
                  Address & Navigation
                </div>
                <p className="text-stone-800 text-xs leading-relaxed">
                  {viewCustomer.address.address_line}, {viewCustomer.address.area},{' '}
                  {viewCustomer.address.city} - {viewCustomer.address.pincode}
                </p>
                {viewCustomer.address.landmark && (
                  <p className="text-xs text-stone-500 italic">
                    Landmark: {viewCustomer.address.landmark}
                  </p>
                )}
                <div className="text-[11px] text-amber-800 font-mono mt-1">
                  GPS: {viewCustomer.address.latitude}, {viewCustomer.address.longitude}
                </div>
              </div>

              <div className="space-y-1.5 border-t border-stone-200 pt-3">
                <div className="text-xs font-bold text-stone-500 uppercase tracking-wider">
                  Meal Plan & Preferences
                </div>
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                      viewCustomer.meal_preference.diet_type === 'VEG'
                        ? 'bg-emerald-100 text-emerald-900'
                        : 'bg-red-100 text-red-900'
                    }`}
                  >
                    {viewCustomer.meal_preference.diet_type}
                  </span>
                  <span className="text-xs text-stone-600">
                    Spice: {viewCustomer.meal_preference.spice_level}
                  </span>
                </div>
                {viewCustomer.meal_preference.food_exclusions && (
                  <div className="text-xs text-stone-600">
                    <strong>Exclusions:</strong> {viewCustomer.meal_preference.food_exclusions}
                  </div>
                )}
                {viewCustomer.meal_preference.delivery_instructions && (
                  <div className="text-xs text-stone-600">
                    <strong>Instructions:</strong> {viewCustomer.meal_preference.delivery_instructions}
                  </div>
                )}
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setViewCustomer(null)} className="w-full">
                Close Profile
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}

      {/* Delete Confirmation Modal */}
      {deleteCandidate && (
        <Dialog open={Boolean(deleteCandidate)} onOpenChange={() => setDeleteCandidate(null)}>
          <DialogContent className="max-w-sm bg-white border-stone-200">
            <DialogHeader>
              <DialogTitle className="text-stone-900 font-bold">Remove Customer</DialogTitle>
              <DialogDescription className="text-xs text-stone-500">
                Are you sure you want to remove <strong>{deleteCandidate.name}</strong>? This action cannot be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter className="gap-2 sm:gap-0 mt-3">
              <Button variant="outline" onClick={() => setDeleteCandidate(null)}>
                Cancel
              </Button>
              <Button
                onClick={handleDeleteConfirm}
                className="bg-red-600 hover:bg-red-700 text-white"
              >
                Delete
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
