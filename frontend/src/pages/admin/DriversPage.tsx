import React, { useState } from 'react'
import {
  Truck,
  Phone,
  RotateCcw,
  Loader2,
  ShieldCheck,
  Search,
  Edit2,
  Radio,
  Coffee,
  X
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { useGetDriversQuery, useUpdateDriverStatusMutation } from '../../features/drivers/driverApiSlice'
import type { Driver } from '../../types/order'

export const DriversPage: React.FC = () => {
  const { data: drivers = [], isLoading, refetch } = useGetDriversQuery()
  const [updateStatus, { isLoading: isUpdating }] = useUpdateDriverStatusMutation()

  const [search, setSearch] = useState('')
  const [editingDriver, setEditingDriver] = useState<Driver | null>(null)
  const [newVehicleType, setNewVehicleType] = useState('')
  const [newVehicleNumber, setNewVehicleNumber] = useState('')

  const filteredDrivers = drivers.filter(
    (d) =>
      d.full_name.toLowerCase().includes(search.toLowerCase()) ||
      d.username.toLowerCase().includes(search.toLowerCase()) ||
      (d.phone && d.phone.includes(search)) ||
      (d.vehicle_number && d.vehicle_number.toLowerCase().includes(search.toLowerCase()))
  )

  const handleStatusChange = async (driverId: string, status: string) => {
    try {
      await updateStatus({ id: driverId, driving_status: status }).unwrap()
      refetch()
    } catch (e) {
      console.error('Failed to update driver status', e)
    }
  }

  const openEditModal = (driver: Driver) => {
    setEditingDriver(driver)
    setNewVehicleType(driver.vehicle_type || 'Motorcycle')
    setNewVehicleNumber(driver.vehicle_number || 'TN-01-AB-1234')
  }

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-black text-stone-900 tracking-tight">
            Delivery Driver Fleet
          </h1>
          <p className="text-sm text-stone-600 mt-0.5">
            Manage delivery personnel, vehicles, shift status, and daily order assignments.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => refetch()}
            className="border-stone-300 hover:bg-stone-100 text-stone-700 font-semibold"
          >
            <RotateCcw className="w-3.5 h-3.5 mr-1.5" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-stone-500 uppercase">Total Drivers</p>
            <p className="text-2xl font-black text-stone-900 mt-1">{drivers.length}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center text-stone-700">
            <Truck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-emerald-600 uppercase">Available</p>
            <p className="text-2xl font-black text-emerald-600 mt-1">
              {drivers.filter((d) => d.driving_status === 'AVAILABLE').length}
            </p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-amber-600 uppercase">On Delivery</p>
            <p className="text-2xl font-black text-amber-600 mt-1">
              {drivers.filter((d) => d.driving_status === 'ON_DELIVERY').length}
            </p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-stone-500 uppercase">On Break</p>
            <p className="text-2xl font-black text-stone-700 mt-1">
              {drivers.filter((d) => d.driving_status === 'PAUSED').length}
            </p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center text-stone-500">
            <Coffee className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-stone-400" />
          <Input
            placeholder="Search driver name, phone, vehicle..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-10 bg-white border-stone-300"
          />
        </div>
      </div>

      {/* Driver Roster Table */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 bg-white rounded-2xl border border-stone-200 shadow-sm">
          <Loader2 className="w-8 h-8 animate-spin text-[#E5A93C] mb-2" />
          <p className="text-sm font-medium text-stone-600">Loading driver fleet...</p>
        </div>
      ) : (
        <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-stone-600">
              <thead className="bg-stone-50 text-xs font-black text-stone-500 uppercase tracking-wider border-b border-stone-200">
                <tr>
                  <th className="px-5 py-3.5">Driver Info</th>
                  <th className="px-4 py-3.5">Vehicle</th>
                  <th className="px-4 py-3.5">Driving Status</th>
                  <th className="px-4 py-3.5 text-center">Active Deliveries</th>
                  <th className="px-4 py-3.5 text-center">Completed Today</th>
                  <th className="px-5 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200">
                {filteredDrivers.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-5 py-8 text-center text-stone-400 text-xs">
                      No drivers found matching your search.
                    </td>
                  </tr>
                ) : (
                  filteredDrivers.map((driver) => {
                    const isOnDelivery = driver.driving_status === 'ON_DELIVERY'
                    const isAvailable = driver.driving_status === 'AVAILABLE'

                    return (
                      <tr key={driver.id} className="hover:bg-stone-50/80 transition-colors">
                        <td className="px-5 py-4">
                          <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-[#1B4D3E]/10 text-[#1B4D3E] font-black text-sm flex items-center justify-center shrink-0">
                              {driver.full_name ? driver.full_name[0] : 'D'}
                            </div>
                            <div>
                              <p className="font-bold text-stone-900">{driver.full_name}</p>
                              <div className="flex items-center gap-2 text-xs text-stone-500">
                                <span>@{driver.username}</span>
                                {driver.phone && (
                                  <>
                                    <span>&bull;</span>
                                    <a
                                      href={`tel:${driver.phone}`}
                                      className="text-emerald-700 hover:underline flex items-center gap-1 font-semibold"
                                    >
                                      <Phone className="w-3 h-3" />
                                      {driver.phone}
                                    </a>
                                  </>
                                )}
                              </div>
                            </div>
                          </div>
                        </td>

                        <td className="px-4 py-4">
                          <p className="font-semibold text-stone-800 text-xs">
                            {driver.vehicle_type || 'Motorcycle'}
                          </p>
                          <p className="text-[11px] font-mono text-stone-500">
                            {driver.vehicle_number || 'TN-01-AB-1234'}
                          </p>
                        </td>

                        <td className="px-4 py-4">
                          <select
                            value={driver.driving_status}
                            onChange={(e) => handleStatusChange(driver.id, e.target.value)}
                            disabled={isUpdating}
                            className={`text-xs font-bold px-2.5 py-1 rounded-full border focus:outline-none cursor-pointer ${
                              isOnDelivery
                                ? 'bg-amber-100 text-amber-900 border-amber-300'
                                : isAvailable
                                ? 'bg-emerald-100 text-emerald-900 border-emerald-300'
                                : 'bg-stone-100 text-stone-700 border-stone-300'
                            }`}
                          >
                            <option value="AVAILABLE">AVAILABLE (Online)</option>
                            <option value="ON_DELIVERY">ON_DELIVERY (Route)</option>
                            <option value="PAUSED">PAUSED (Break)</option>
                            <option value="OFFLINE">OFFLINE</option>
                          </select>
                        </td>

                        <td className="px-4 py-4 text-center">
                          <span
                            className={`inline-flex items-center justify-center font-bold px-2.5 py-0.5 rounded-full text-xs ${
                              driver.assigned_deliveries_count > 0
                                ? 'bg-[#E5A93C]/20 text-stone-900 font-black'
                                : 'text-stone-400'
                            }`}
                          >
                            {driver.assigned_deliveries_count}
                          </span>
                        </td>

                        <td className="px-4 py-4 text-center">
                          <span className="font-black text-emerald-600 text-xs">
                            {driver.completed_today_count}
                          </span>
                        </td>

                        <td className="px-5 py-4 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => openEditModal(driver)}
                            className="h-8 border-stone-300 text-stone-700 hover:bg-stone-100 text-xs font-semibold"
                          >
                            <Edit2 className="w-3 h-3 mr-1 text-[#E5A93C]" />
                            Edit
                          </Button>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit Driver Modal */}
      {editingDriver && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-2xl border border-stone-200">
            <div className="flex items-center justify-between">
              <h3 className="font-bold text-base text-stone-900">
                Edit Driver: {editingDriver.full_name}
              </h3>
              <button
                onClick={() => setEditingDriver(null)}
                className="text-stone-400 hover:text-stone-700"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">
                  Vehicle Type
                </label>
                <select
                  value={newVehicleType}
                  onChange={(e) => setNewVehicleType(e.target.value)}
                  className="w-full h-10 px-3 text-sm rounded-lg border border-stone-300 bg-white"
                >
                  <option value="Motorcycle">Motorcycle / Bike</option>
                  <option value="Scooter">Scooter</option>
                  <option value="Electric Scooter">Electric Scooter (EV)</option>
                  <option value="Car">Car</option>
                  <option value="Van">Van / Delivery Auto</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">
                  Vehicle Plate Number
                </label>
                <Input
                  value={newVehicleNumber}
                  onChange={(e) => setNewVehicleNumber(e.target.value)}
                  placeholder="e.g. TN-01-AB-1234"
                  className="h-10 text-sm font-mono uppercase"
                />
              </div>

              <div className="flex items-center gap-2 pt-3">
                <Button
                  variant="outline"
                  onClick={() => setEditingDriver(null)}
                  className="w-1/2 h-10 border-stone-300 text-stone-700 font-bold text-xs"
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => {
                    setEditingDriver(null)
                    refetch()
                  }}
                  className="w-1/2 h-10 bg-[#1B4D3E] hover:bg-[#143d31] text-white font-bold text-xs shadow-md"
                >
                  Save Changes
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
