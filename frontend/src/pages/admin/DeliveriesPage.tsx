import React, { useState } from 'react'
import {
  useGetOrdersQuery,
  useBulkAssignDriverMutation,
  useUpdateOrderStatusMutation,
} from '../../features/orders/orderApiSlice'
import { useGetDriversQuery } from '../../features/drivers/driverApiSlice'
import type { Order, MealSession } from '../../types/order'
import {
  Truck,
  CheckCircle2,
  MapPin,
  Phone,
  Navigation,
  Loader2,
  Sparkles,
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'

const formatDateForInput = (d: Date) => {
  return d.toISOString().split('T')[0]
}

export const DeliveriesPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(
    formatDateForInput(new Date())
  )
  const [selectedSession, setSelectedSession] = useState<MealSession>('LUNCH')
  const [selectedOrderIds, setSelectedOrderIds] = useState<string[]>([])
  const [selectedDriverId, setSelectedDriverId] = useState<string>('')
  const [notification, setNotification] = useState<string | null>(null)

  // API Queries
  const { data: ordersData, isLoading: isOrdersLoading, refetch } = useGetOrdersQuery({
    date: selectedDate,
    meal_session: selectedSession,
  })

  const { data: drivers = [] } = useGetDriversQuery()

  // Mutations
  const [bulkAssign, { isLoading: isAssigning }] = useBulkAssignDriverMutation()
  const [updateStatus] = useUpdateOrderStatusMutation()

  const orders = ordersData?.items || []
  const unassignedOrders = orders.filter((o) => !o.assigned_driver_id && o.status !== 'CANCELLED')
  const assignedOrders = orders.filter((o) => o.assigned_driver_id)

  const handleSelectAllUnassigned = () => {
    if (selectedOrderIds.length === unassignedOrders.length) {
      setSelectedOrderIds([])
    } else {
      setSelectedOrderIds(unassignedOrders.map((o) => o.id))
    }
  }

  const handleToggleSelectOrder = (id: string) => {
    setSelectedOrderIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    )
  }

  const handleAssignOrders = async () => {
    if (!selectedDriverId) {
      alert('Please select an active driver from the fleet first.')
      return
    }
    if (selectedOrderIds.length === 0) {
      alert('Please check one or more unassigned orders to assign.')
      return
    }

    const driver = drivers.find((d) => d.id === selectedDriverId)
    if (!driver) return

    // Find current max sequence number for this driver today
    const driverCurrentOrders = assignedOrders.filter(
      (o) => o.assigned_driver_id === selectedDriverId
    )
    let startSeq = driverCurrentOrders.length + 1

    const assignments = selectedOrderIds.map((orderId, idx) => ({
      order_id: orderId,
      sequence_number: startSeq + idx,
    }))

    try {
      const res = await bulkAssign({
        driver_id: driver.id,
        driver_name: driver.full_name,
        assignments,
      }).unwrap()

      setNotification(res.message)
      setSelectedOrderIds([])
      refetch()
      setTimeout(() => setNotification(null), 4000)
    } catch (err: any) {
      alert(err?.data?.detail || 'Assignment failed.')
    }
  }

  const handleMarkDelivered = async (orderId: string) => {
    try {
      await updateStatus({ id: orderId, status: 'DELIVERED' }).unwrap()
      refetch()
    } catch (err) {
      console.error(err)
    }
  }

  const openDriverRouteInMaps = (driverOrders: Order[]) => {
    if (driverOrders.length === 0) return
    const destination = driverOrders[driverOrders.length - 1].delivery_address.area + ', Chennai'
    const waypoints = driverOrders
      .slice(0, -1)
      .map((o) => encodeURIComponent(o.delivery_address.area + ', Chennai'))
      .join('|')
    const url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(
      destination
    )}&waypoints=${waypoints}`
    window.open(url, '_blank')
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 font-serif">
            Delivery Assignment & Dispatch
          </h1>
          <p className="text-sm text-stone-500 mt-1">
            Coordinate driver delivery batches, route sequence stops, and track delivery execution.
          </p>
        </div>

        {/* Date & Session Selectors */}
        <div className="flex flex-wrap items-center gap-2">
          <Input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="w-36 text-xs font-semibold"
          />

          <div className="inline-flex rounded-lg border border-stone-200 bg-stone-50 p-1 text-xs font-semibold">
            {(['BREAKFAST', 'LUNCH', 'DINNER'] as const).map((session) => (
              <button
                key={session}
                onClick={() => setSelectedSession(session)}
                className={`px-3 py-1 rounded transition-all ${
                  selectedSession === session
                    ? 'bg-amber-600 text-white shadow-xs'
                    : 'text-stone-600 hover:text-stone-900'
                }`}
              >
                {session === 'BREAKFAST'
                  ? '🌅 Breakfast'
                  : session === 'LUNCH'
                  ? '☀️ Lunch'
                  : '🌙 Dinner'}
              </button>
            ))}
          </div>
        </div>
      </div>

      {notification && (
        <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-lg text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
        <Card className="border-stone-200">
          <CardContent className="p-4">
            <div className="text-xs font-bold text-stone-500 uppercase tracking-wider">Total Deliveries</div>
            <div className="text-2xl font-bold text-stone-900 mt-1">{orders.length}</div>
          </CardContent>
        </Card>
        <Card className="border-stone-200 bg-amber-50/50 border-amber-300/60">
          <CardContent className="p-4">
            <div className="text-xs font-bold text-amber-800 uppercase tracking-wider">Unassigned Drops</div>
            <div className="text-2xl font-bold text-amber-900 mt-1">{unassignedOrders.length}</div>
          </CardContent>
        </Card>
        <Card className="border-stone-200">
          <CardContent className="p-4">
            <div className="text-xs font-bold text-blue-700 uppercase tracking-wider">Assigned to Fleet</div>
            <div className="text-2xl font-bold text-blue-800 mt-1">{assignedOrders.length}</div>
          </CardContent>
        </Card>
        <Card className="border-stone-200">
          <CardContent className="p-4">
            <div className="text-xs font-bold text-emerald-700 uppercase tracking-wider">Completed Drops</div>
            <div className="text-2xl font-bold text-emerald-800 mt-1">
              {orders.filter((o) => o.status === 'DELIVERED').length}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Main Two-Column Dispatch Control */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Unassigned Orders Bucket (7 Cols) */}
        <div className="lg:col-span-7 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-stone-900">
                Unassigned Deliveries ({unassignedOrders.length})
              </h2>
              {unassignedOrders.length > 0 && (
                <button
                  onClick={handleSelectAllUnassigned}
                  className="text-xs text-amber-700 hover:text-amber-800 font-semibold underline"
                >
                  {selectedOrderIds.length === unassignedOrders.length
                    ? 'Deselect All'
                    : 'Select All'}
                </button>
              )}
            </div>

            {selectedOrderIds.length > 0 && (
              <span className="text-xs font-bold text-amber-900 bg-amber-100 px-2.5 py-0.5 rounded-full">
                {selectedOrderIds.length} Selected
              </span>
            )}
          </div>

          {isOrdersLoading ? (
            <div className="text-center py-12 bg-white rounded-xl border">
              <Loader2 className="w-6 h-6 animate-spin text-amber-600 mx-auto" />
            </div>
          ) : unassignedOrders.length === 0 ? (
            <Card className="border-stone-200 bg-stone-50/50 p-8 text-center">
              <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
              <h3 className="mt-2 text-sm font-bold text-stone-800">All Deliveries Assigned</h3>
              <p className="text-xs text-stone-500 mt-1">
                There are no pending unassigned drops for {selectedSession} shift.
              </p>
            </Card>
          ) : (
            <div className="space-y-2.5 max-h-[600px] overflow-y-auto pr-1">
              {unassignedOrders.map((order) => {
                const isSelected = selectedOrderIds.includes(order.id)
                return (
                  <div
                    key={order.id}
                    onClick={() => handleToggleSelectOrder(order.id)}
                    className={`p-3.5 rounded-xl border transition-all cursor-pointer flex items-start gap-3 ${
                      isSelected
                        ? 'border-amber-500 bg-amber-50/30 ring-1 ring-amber-400'
                        : 'border-stone-200 bg-white hover:border-stone-300'
                    }`}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      className="mt-1 w-4 h-4 text-amber-600 rounded border-stone-300 focus:ring-amber-500 cursor-pointer"
                    />

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-bold text-stone-900 text-sm">{order.customer_name}</span>
                        <span
                          className={`text-[10px] font-bold px-1.5 py-0.2 rounded ${
                            order.diet_type === 'VEG'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-red-100 text-red-800'
                          }`}
                        >
                          {order.diet_type}
                        </span>
                      </div>

                      <div className="flex items-start gap-1 text-xs text-stone-600 mt-1">
                        <MapPin className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
                        <span className="truncate">
                          {order.delivery_address.address_line}, {order.delivery_address.area}
                        </span>
                      </div>

                      <div className="flex items-center gap-3 text-xs text-stone-500 mt-1">
                        <span className="flex items-center gap-1">
                          <Phone className="w-3 h-3" />
                          <span>{order.customer_phone}</span>
                        </span>
                        {order.special_notes && (
                          <span className="text-amber-800 italic truncate max-w-[180px]">
                            {order.special_notes}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {/* Right Column: Fleet Selection & Assigned Route Sequences (5 Cols) */}
        <div className="lg:col-span-5 space-y-4">
          {/* Driver Fleet Selector & Action */}
          <Card className="border-stone-200 shadow-sm bg-white">
            <CardHeader className="pb-3">
              <CardTitle className="text-base font-bold text-stone-900 flex items-center justify-between">
                <span>Select Driver to Assign</span>
                <Truck className="w-4 h-4 text-amber-600" />
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-1">
                <label className="text-xs font-semibold text-stone-600">Active Delivery Staff</label>
                <div className="space-y-2">
                  {drivers.map((driver) => (
                    <div
                      key={driver.id}
                      onClick={() => setSelectedDriverId(driver.id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                        selectedDriverId === driver.id
                          ? 'border-amber-500 bg-amber-50 text-amber-950 font-semibold ring-1 ring-amber-400'
                          : 'border-stone-200 hover:bg-stone-50'
                      }`}
                    >
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-full bg-stone-900 text-white flex items-center justify-center text-xs font-bold">
                          {driver.full_name[0]}
                        </div>
                        <div>
                          <div className="text-sm font-bold">{driver.full_name}</div>
                          <div className="text-[11px] text-stone-500">
                            {driver.vehicle_number} &bull; {driver.driving_status}
                          </div>
                        </div>
                      </div>

                      <div className="text-right">
                        <span className="text-xs font-bold bg-white px-2 py-0.5 rounded border border-stone-200">
                          {assignedOrders.filter((o) => o.assigned_driver_id === driver.id).length} drops
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <Button
                onClick={handleAssignOrders}
                disabled={isAssigning || selectedOrderIds.length === 0 || !selectedDriverId}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold flex items-center justify-center gap-2 shadow-md mt-2"
              >
                {isAssigning ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                <span>
                  Assign {selectedOrderIds.length > 0 ? `(${selectedOrderIds.length})` : ''} to Selected Driver
                </span>
              </Button>
            </CardContent>
          </Card>

          {/* Assigned Driver Route Sequence View */}
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-stone-800 flex items-center justify-between">
              <span>Today's Dispatched Routes</span>
            </h3>

            {drivers.map((driver) => {
              const driverOrders = assignedOrders
                .filter((o) => o.assigned_driver_id === driver.id)
                .sort((a, b) => (a.sequence_number || 0) - (b.sequence_number || 0))

              if (driverOrders.length === 0) return null

              return (
                <Card key={driver.id} className="border-stone-200 bg-white shadow-xs">
                  <CardContent className="p-3.5 space-y-3">
                    <div className="flex items-center justify-between border-b border-stone-100 pb-2">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        <span className="font-bold text-sm text-stone-900">{driver.full_name}</span>
                        <span className="text-xs text-stone-500">({driverOrders.length} stops)</span>
                      </div>

                      <button
                        onClick={() => openDriverRouteInMaps(driverOrders)}
                        className="flex items-center gap-1 text-xs text-blue-700 font-semibold hover:underline"
                        title="Open Route in Google Maps"
                      >
                        <Navigation className="w-3.5 h-3.5" />
                        <span>Maps Route</span>
                      </button>
                    </div>

                    <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                      {driverOrders.map((order, index) => (
                        <div
                          key={order.id}
                          className="flex items-center justify-between p-2 rounded bg-stone-50 text-xs"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="w-5 h-5 rounded-full bg-stone-900 text-white flex items-center justify-center font-bold text-[10px] shrink-0">
                              #{order.sequence_number || index + 1}
                            </span>
                            <div className="truncate">
                              <span className="font-bold text-stone-900">{order.customer_name}</span>
                              <span className="text-stone-500 block text-[11px] truncate">
                                {order.delivery_address.area}
                              </span>
                            </div>
                          </div>

                          <div className="flex items-center gap-1.5 shrink-0">
                            {order.status === 'DELIVERED' ? (
                              <span className="text-emerald-700 font-bold text-[10px] bg-emerald-100 px-1.5 py-0.5 rounded">
                                DELIVERED
                              </span>
                            ) : (
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleMarkDelivered(order.id)}
                                className="h-6 text-[10px] px-1.5 text-emerald-800 border-emerald-300 hover:bg-emerald-50"
                              >
                                Mark Done
                              </Button>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}
