import React, { useState } from 'react'
import {
  useGetEnquiriesQuery,
  useCreateEnquiryMutation,
  useUpdateEnquiryMutation,
  useConvertEnquiryToCustomerMutation,
} from '../../features/enquiries/enquiryApiSlice'
import type {
  Enquiry,
  EnquiryCreateInput,
  EnquiryStatus,
  DietType,
} from '../../types/customer'
import {
  MessageSquare,
  Plus,
  Search,
  CheckCircle2,
  Phone,
  MapPin,
  AlertCircle,
  Loader2,
  UserCheck,
  Compass
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

const STATUS_TABS: (EnquiryStatus | 'ALL')[] = [
  'ALL',
  'NEW',
  'CONTACTED',
  'QUOTED',
  'FOLLOW_UP',
  'CONFIRMED',
  'CONVERTED',
]

export const EnquiriesPage: React.FC = () => {
  const [search, setSearch] = useState('')
  const [selectedStatus, setSelectedStatus] = useState<EnquiryStatus | 'ALL'>('ALL')

  // API Query
  const { data, isLoading, refetch } = useGetEnquiriesQuery({
    search: search.trim() || undefined,
    status_filter: selectedStatus === 'ALL' ? undefined : selectedStatus,
  })

  // Mutations
  const [createEnquiry, { isLoading: isCreating }] = useCreateEnquiryMutation()
  const [updateEnquiry] = useUpdateEnquiryMutation()
  const [convertEnquiry, { isLoading: isConverting }] = useConvertEnquiryToCustomerMutation()

  // Modal State
  const [isCreateOpen, setIsCreateOpen] = useState(false)
  const [convertTarget, setConvertTarget] = useState<Enquiry | null>(null)
  const [isMapOpen, setIsMapOpen] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)

  // Create Form State
  const [formData, setFormData] = useState<EnquiryCreateInput>({
    customer_name: '',
    phone: '',
    requested_meal: 'Lunch & Dinner',
    number_of_persons: 1,
    diet_type: 'VEG',
    subscription_type: 'SUBSCRIPTION',
    delivery_location: '',
    quoted_price: 2799,
    notes: '',
    status: 'NEW',
  })

  // Convert Address Form State
  const [convertAddress, setConvertAddress] = useState({
    address_line: '',
    area: 'Anna Nagar East',
    city: 'Chennai',
    landmark: '',
    pincode: '600102',
    latitude: 13.0850,
    longitude: 80.2150,
  })

  const openCreateModal = () => {
    setFormData({
      customer_name: '',
      phone: '',
      requested_meal: 'Lunch & Dinner',
      number_of_persons: 1,
      diet_type: 'VEG',
      subscription_type: 'SUBSCRIPTION',
      delivery_location: '',
      quoted_price: 2799,
      notes: '',
      status: 'NEW',
    })
    setFormError(null)
    setIsCreateOpen(true)
  }

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError(null)

    if (!formData.customer_name.trim() || !formData.phone.trim() || !formData.delivery_location.trim()) {
      setFormError('Please fill in customer name, phone number, and delivery location.')
      return
    }

    try {
      await createEnquiry(formData).unwrap()
      setIsCreateOpen(false)
      refetch()
    } catch (err: any) {
      setFormError(err?.data?.detail || 'Failed to save enquiry.')
    }
  }

  const handleStatusChange = async (enquiry: Enquiry, newStatus: EnquiryStatus) => {
    try {
      await updateEnquiry({ id: enquiry.id, data: { status: newStatus } }).unwrap()
      refetch()
    } catch (err) {
      console.error('Status change error', err)
    }
  }

  const startConversion = (enquiry: Enquiry) => {
    setConvertTarget(enquiry)
    setConvertAddress({
      address_line: enquiry.delivery_location,
      area: enquiry.delivery_location.split(',')[0] || 'Anna Nagar East',
      city: 'Chennai',
      landmark: '',
      pincode: '600102',
      latitude: 13.0850,
      longitude: 80.2150,
    })
    setFormError(null)
  }

  const handleConvertSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!convertTarget) return
    setFormError(null)

    if (!convertAddress.address_line.trim() || !convertAddress.area.trim()) {
      setFormError('Address and locality are required to register the customer.')
      return
    }

    try {
      await convertEnquiry({ id: convertTarget.id, data: convertAddress }).unwrap()
      setConvertTarget(null)
      refetch()
    } catch (err: any) {
      setFormError(err?.data?.detail || 'Failed to convert enquiry.')
    }
  }

  const getStatusBadge = (status: EnquiryStatus) => {
    switch (status) {
      case 'NEW':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-blue-100 text-blue-800">NEW</span>
      case 'CONTACTED':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-100 text-purple-800">CONTACTED</span>
      case 'QUOTED':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-100 text-amber-800">QUOTED</span>
      case 'FOLLOW_UP':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-orange-100 text-orange-800">FOLLOW-UP</span>
      case 'CONFIRMED':
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-teal-100 text-teal-800">CONFIRMED</span>
      case 'CONVERTED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-100 text-emerald-800">
            <CheckCircle2 className="w-3 h-3" />
            CONVERTED
          </span>
        )
      default:
        return <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-stone-100 text-stone-600">{status}</span>
    }
  }

  const enquiries = data?.items || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 font-serif">
            Customer Enquiry Pipeline
          </h1>
          <p className="text-sm text-stone-500 mt-1">
            Capture prospective customer leads, schedule follow-ups, and convert confirmed requests into active subscriptions.
          </p>
        </div>

        <Button
          onClick={openCreateModal}
          className="bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center gap-2 shadow-md"
        >
          <Plus className="w-4 h-4" />
          <span>Record New Enquiry</span>
        </Button>
      </div>

      {/* Filter & Tabs */}
      <Card className="border-stone-200 shadow-sm">
        <CardContent className="p-4 space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative flex-1 max-w-md">
              <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <Input
                type="text"
                placeholder="Search by customer name, phone, or location..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 text-sm"
              />
            </div>
          </div>

          {/* Status Filter Tabs */}
          <div className="flex items-center gap-1 overflow-x-auto pb-1 text-xs">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab}
                onClick={() => setSelectedStatus(tab)}
                className={`px-3 py-1.5 rounded-lg font-semibold whitespace-nowrap transition-all ${
                  selectedStatus === tab
                    ? 'bg-amber-600 text-white shadow-xs'
                    : 'bg-stone-100 text-stone-600 hover:bg-stone-200'
                }`}
              >
                {tab === 'ALL' ? 'All Enquiries' : tab}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Enquiries Table */}
      <Card className="border-stone-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm text-stone-700">
            <thead className="bg-stone-50 border-b border-stone-200 text-xs font-semibold text-stone-500 uppercase tracking-wider">
              <tr>
                <th className="px-4 py-3">Customer</th>
                <th className="px-4 py-3">Requested Meal</th>
                <th className="px-4 py-3">Delivery Zone</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Notes</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-stone-200 bg-white">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="text-center py-12">
                    <Loader2 className="w-6 h-6 animate-spin text-amber-600 mx-auto" />
                    <span className="text-xs text-stone-500 mt-1 block">Loading enquiries...</span>
                  </td>
                </tr>
              ) : enquiries.length === 0 ? (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-stone-400">
                    <MessageSquare className="w-8 h-8 stroke-1 mx-auto text-stone-300" />
                    <span className="text-sm font-medium text-stone-600 mt-2 block">No enquiries found</span>
                    <span className="text-xs text-stone-400">Click "Record New Enquiry" to add one.</span>
                  </td>
                </tr>
              ) : (
                enquiries.map((enq) => (
                  <tr key={enq.id} className="hover:bg-stone-50/70 transition-colors">
                    {/* Customer */}
                    <td className="px-4 py-3">
                      <div className="font-bold text-stone-900">{enq.customer_name}</div>
                      <div className="flex items-center gap-1 text-xs text-stone-500 mt-0.5">
                        <Phone className="w-3 h-3 text-stone-400" />
                        <span>{enq.phone}</span>
                      </div>
                    </td>

                    {/* Meal details */}
                    <td className="px-4 py-3">
                      <div className="text-xs font-semibold text-stone-800">
                        {enq.requested_meal || 'Lunch'}
                      </div>
                      <div className="flex items-center gap-1.5 mt-0.5">
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                            enq.diet_type === 'VEG'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {enq.diet_type}
                        </span>
                        <span className="text-[11px] text-stone-500">
                          &bull; {enq.number_of_persons} person(s)
                        </span>
                      </div>
                      {enq.quoted_price && (
                        <div className="text-xs text-amber-800 font-bold mt-0.5">
                          ₹{enq.quoted_price.toLocaleString()}
                        </div>
                      )}
                    </td>

                    {/* Delivery Location */}
                    <td className="px-4 py-3 max-w-xs">
                      <div className="flex items-start gap-1 text-xs text-stone-700">
                        <MapPin className="w-3.5 h-3.5 text-stone-400 shrink-0 mt-0.5" />
                        <span className="truncate">{enq.delivery_location}</span>
                      </div>
                    </td>

                    {/* Status Dropdown */}
                    <td className="px-4 py-3">
                      <div className="space-y-1">
                        <div>{getStatusBadge(enq.status)}</div>
                        {enq.status !== 'CONVERTED' && (
                          <select
                            value={enq.status}
                            onChange={(e) => handleStatusChange(enq, e.target.value as EnquiryStatus)}
                            className="text-[11px] border border-stone-200 rounded px-1.5 py-0.5 bg-white text-stone-600 focus:outline-none"
                          >
                            <option value="NEW">New</option>
                            <option value="CONTACTED">Contacted</option>
                            <option value="QUOTED">Quoted</option>
                            <option value="FOLLOW_UP">Follow-Up</option>
                            <option value="CONFIRMED">Confirmed</option>
                            <option value="CLOSED">Closed</option>
                          </select>
                        )}
                      </div>
                    </td>

                    {/* Notes */}
                    <td className="px-4 py-3 max-w-xs">
                      <span className="text-xs text-stone-500 truncate block">
                        {enq.notes || '—'}
                      </span>
                    </td>

                    {/* Actions */}
                    <td className="px-4 py-3 text-right">
                      {enq.status !== 'CONVERTED' ? (
                        <Button
                          size="sm"
                          onClick={() => startConversion(enq)}
                          className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold gap-1 shadow-xs"
                        >
                          <UserCheck className="w-3.5 h-3.5" />
                          <span>Convert to Customer</span>
                        </Button>
                      ) : (
                        <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
                          Customer Active
                        </span>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Record New Enquiry Modal */}
      <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
        <DialogContent className="max-w-md bg-white border-stone-200">
          <DialogHeader>
            <DialogTitle className="text-xl font-bold font-serif text-stone-900">
              Record New Enquiry
            </DialogTitle>
            <DialogDescription className="text-xs text-stone-500">
              Add details from an incoming phone, WhatsApp, or in-person meal enquiry.
            </DialogDescription>
          </DialogHeader>

          {formError && (
            <div className="p-2.5 rounded bg-red-50 text-red-800 text-xs flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleCreateSubmit} className="space-y-3.5 my-2">
            <div className="space-y-1">
              <Label className="text-xs font-semibold">Prospect Name *</Label>
              <Input
                required
                placeholder="e.g. Suresh Babu"
                value={formData.customer_name}
                onChange={(e) => setFormData({ ...formData, customer_name: e.target.value })}
                className="text-sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Phone Number *</Label>
                <Input
                  required
                  placeholder="e.g. 9841122334"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  className="text-sm"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-xs font-semibold">Diet Preference</Label>
                <select
                  value={formData.diet_type}
                  onChange={(e) => setFormData({ ...formData, diet_type: e.target.value as DietType })}
                  className="w-full text-sm rounded border border-stone-200 p-2"
                >
                  <option value="VEG">Vegetarian</option>
                  <option value="NON_VEG">Non-Vegetarian</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1">
                <Label className="text-xs font-semibold">Requested Meal</Label>
                <Input
                  placeholder="e.g. Lunch & Dinner"
                  value={formData.requested_meal}
                  onChange={(e) => setFormData({ ...formData, requested_meal: e.target.value })}
                  className="text-sm"
                />
              </div>

              <div className="space-y-1">
                <Label className="text-xs font-semibold">Persons Count</Label>
                <Input
                  type="number"
                  min={1}
                  value={formData.number_of_persons}
                  onChange={(e) =>
                    setFormData({ ...formData, number_of_persons: parseInt(e.target.value) || 1 })
                  }
                  className="text-sm"
                />
              </div>
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Delivery Locality / Address *</Label>
              <Input
                required
                placeholder="e.g. Nungambakkam High Road, Chennai"
                value={formData.delivery_location}
                onChange={(e) => setFormData({ ...formData, delivery_location: e.target.value })}
                className="text-sm"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Quoted Monthly Price (₹)</Label>
              <Input
                type="number"
                placeholder="e.g. 2799"
                value={formData.quoted_price}
                onChange={(e) =>
                  setFormData({ ...formData, quoted_price: parseFloat(e.target.value) || 0 })
                }
                className="text-sm"
              />
            </div>

            <div className="space-y-1">
              <Label className="text-xs font-semibold">Enquiry Notes / Requirements</Label>
              <Input
                placeholder="e.g. Requested 3 days trial box before monthly sign-up"
                value={formData.notes}
                onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                className="text-sm"
              />
            </div>

            <DialogFooter className="gap-2 sm:gap-0 pt-2">
              <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={isCreating}
                className="bg-amber-600 hover:bg-amber-700 text-white font-semibold"
              >
                {isCreating ? 'Saving...' : 'Save Enquiry'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Convert Enquiry to Customer Modal */}
      {convertTarget && (
        <Dialog open={Boolean(convertTarget)} onOpenChange={() => setConvertTarget(null)}>
          <DialogContent className="max-w-lg bg-white border-stone-200">
            <DialogHeader>
              <DialogTitle className="text-xl font-bold font-serif text-stone-900 flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-emerald-600" />
                <span>Convert Enquiry to Customer</span>
              </DialogTitle>
              <DialogDescription className="text-xs text-stone-500">
                Confirm delivery address and GPS pin for <strong>{convertTarget.customer_name}</strong> (
                {convertTarget.phone}) to create the customer record.
              </DialogDescription>
            </DialogHeader>

            {formError && (
              <div className="p-2.5 rounded bg-red-50 text-red-800 text-xs flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleConvertSubmit} className="space-y-4 my-2">
              <div className="flex items-center justify-between">
                <Label className="text-xs font-semibold">Street / Door Address *</Label>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => setIsMapOpen(true)}
                  className="flex items-center gap-1 text-xs text-amber-800 border-amber-300"
                >
                  <Compass className="w-3.5 h-3.5 text-amber-600" />
                  <span>Pick on Map</span>
                </Button>
              </div>

              <Input
                required
                placeholder="e.g. 78 Arcot Road, 2nd Floor"
                value={convertAddress.address_line}
                onChange={(e) => setConvertAddress({ ...convertAddress, address_line: e.target.value })}
                className="text-sm"
              />

              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Area / Locality *</Label>
                  <Input
                    required
                    value={convertAddress.area}
                    onChange={(e) => setConvertAddress({ ...convertAddress, area: e.target.value })}
                    className="text-sm"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs font-semibold">Landmark</Label>
                  <Input
                    placeholder="Near Bus Stand"
                    value={convertAddress.landmark}
                    onChange={(e) => setConvertAddress({ ...convertAddress, landmark: e.target.value })}
                    className="text-sm"
                  />
                </div>
              </div>

              <div className="bg-stone-50 p-2.5 rounded border text-xs text-stone-600 flex items-center justify-between">
                <div>
                  GPS: <strong>{convertAddress.latitude}</strong>,{' '}
                  <strong>{convertAddress.longitude}</strong>
                </div>
                <span className="text-[10px] bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">
                  Ready to Convert
                </span>
              </div>

              <DialogFooter className="gap-2 sm:gap-0 pt-2">
                <Button type="button" variant="outline" onClick={() => setConvertTarget(null)}>
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isConverting}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                >
                  {isConverting ? 'Creating Customer...' : 'Confirm Conversion'}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      )}

      {/* Location Picker for Conversion */}
      <LocationPickerModal
        isOpen={isMapOpen}
        onClose={() => setIsMapOpen(false)}
        onSelectLocation={(loc: SelectedLocation) => {
          setConvertAddress((prev) => ({
            ...prev,
            area: loc.area,
            city: loc.city,
            pincode: loc.pincode || '600001',
            latitude: loc.latitude,
            longitude: loc.longitude,
          }))
        }}
        initialLocation={{
          latitude: convertAddress.latitude,
          longitude: convertAddress.longitude,
          area: convertAddress.area,
        }}
      />
    </div>
  )
}
