import React, { useState } from 'react'
import {
  useGetOrdersQuery,
  useGenerateDailyOrdersMutation,
  useUpdateOrderStatusMutation,
  useBulkUpdateStatusMutation,
} from '../../features/orders/orderApiSlice'
import type {
  Order,
  OrderStatus,
  MealSession,
} from '../../types/order'
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  CheckCircle2,
  Clock,
  Truck,
  XCircle,
  Loader2,
  Search,
  CheckCheck,
  Flame,
  UserCheck
} from 'lucide-react'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Card, CardContent } from '../../components/ui/card'

const formatDateForInput = (d: Date) => {
  return d.toISOString().split('T')[0]
}

const formatDisplayDate = (dateStr: string) => {
  const [y, m, d] = dateStr.split('-').map(Number)
  const dateObj = new Date(y, m - 1, d)
  return dateObj.toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  })
}

export const MealPlannerPage: React.FC = () => {
  const [selectedDate, setSelectedDate] = useState<string>(
    formatDateForInput(new Date())
  )
  const [activeSessionTab, setActiveSessionTab] = useState<'ALL' | MealSession>('ALL')
  const [search, setSearch] = useState('')
  const [mode, setMode] = useState<'GRID' | 'CARDS'>('GRID')
  const [notification, setNotification] = useState<string | null>(null)

  // API Query
  const { data, isLoading, refetch } = useGetOrdersQuery({
    date: selectedDate,
    meal_session: activeSessionTab === 'ALL' ? undefined : activeSessionTab,
    search: search.trim() || undefined,
  })

  // Mutations
  const [generateOrders, { isLoading: isGenerating }] = useGenerateDailyOrdersMutation()
  const [updateStatus] = useUpdateOrderStatusMutation()
  const [bulkUpdateStatus] = useBulkUpdateStatusMutation()

  const handlePrevDay = () => {
    const d = new Date(selectedDate)
    d.setDate(d.getDate() - 1)
    setSelectedDate(formatDateForInput(d))
  }

  const handleNextDay = () => {
    const d = new Date(selectedDate)
    d.setDate(d.getDate() + 1)
    setSelectedDate(formatDateForInput(d))
  }

  const handleToday = () => {
    setSelectedDate(formatDateForInput(new Date()))
  }

  const handleGenerate = async () => {
    try {
      const res = await generateOrders({ date: selectedDate }).unwrap()
      setNotification(res.message)
      refetch()
      setTimeout(() => setNotification(null), 4000)
    } catch (err: any) {
      alert(err?.data?.detail || 'Failed to generate orders.')
    }
  }

  const handleCycleStatus = async (order: Order) => {
    const cycleMap: Record<OrderStatus, OrderStatus> = {
      PLANNED: 'PREPARING',
      PREPARING: 'READY',
      READY: 'PLANNED',
      CONFIRMED: 'PREPARING',
      ASSIGNED: 'READY',
      OUT_FOR_DELIVERY: 'DELIVERED',
      DELIVERED: 'PLANNED',
      FAILED: 'PLANNED',
      CANCELLED: 'PLANNED',
      SKIPPED: 'PLANNED',
    }
    const nextStatus = cycleMap[order.status] || 'PLANNED'
    try {
      await updateStatus({ id: order.id, status: nextStatus }).unwrap()
      refetch()
    } catch (err) {
      console.error('Failed to cycle status', err)
    }
  }

  const handleDirectStatusChange = async (orderId: string, newStatus: OrderStatus) => {
    try {
      await updateStatus({ id: orderId, status: newStatus }).unwrap()
      refetch()
    } catch (err) {
      console.error('Failed to update status', err)
    }
  }

  const handleMarkAllReady = async (session: MealSession) => {
    const targetOrders = (data?.items || []).filter(
      (o) => o.meal_session === session && ['PLANNED', 'PREPARING', 'CONFIRMED'].includes(o.status)
    )
    if (targetOrders.length === 0) {
      alert(`No pending orders to mark as ready for ${session}.`)
      return
    }

    try {
      await bulkUpdateStatus({
        order_ids: targetOrders.map((o) => o.id),
        status: 'READY',
      }).unwrap()
      refetch()
    } catch (err) {
      console.error('Bulk update error', err)
    }
  }

  const getStatusBadge = (status: OrderStatus) => {
    switch (status) {
      case 'PLANNED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-700 border border-stone-200">
            <Clock className="w-3 h-3 text-stone-500" />
            PLANNED
          </span>
        )
      case 'PREPARING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-900 border border-amber-300 animate-pulse">
            <Flame className="w-3 h-3 text-amber-600" />
            PREPARING
          </span>
        )
      case 'READY':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-900 border border-emerald-300">
            <CheckCheck className="w-3 h-3 text-emerald-600" />
            READY
          </span>
        )
      case 'ASSIGNED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-blue-100 text-blue-900 border border-blue-300">
            <UserCheck className="w-3 h-3 text-blue-600" />
            ASSIGNED
          </span>
        )
      case 'OUT_FOR_DELIVERY':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-100 text-purple-900 border border-purple-300">
            <Truck className="w-3 h-3 text-purple-600" />
            ON ROUTE
          </span>
        )
      case 'DELIVERED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-green-100 text-green-900 border border-green-300">
            <CheckCircle2 className="w-3 h-3 text-green-700" />
            DELIVERED
          </span>
        )
      case 'SKIPPED':
      case 'CANCELLED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-red-800 border border-red-200">
            <XCircle className="w-3 h-3 text-red-600" />
            {status}
          </span>
        )
      default:
        return (
          <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-stone-100 text-stone-700">
            {status}
          </span>
        )
    }
  }

  const orders = data?.items || []
  const summary = data?.summary

  // Group orders by customer for the spreadsheet grid mode
  const customerMap = new Map<string, { customerName: string; phone: string; address: string; area: string; diet: string; sessions: Record<string, Order> }>()

  orders.forEach((o) => {
    if (!customerMap.has(o.customer_id)) {
      customerMap.set(o.customer_id, {
        customerName: o.customer_name,
        phone: o.customer_phone,
        address: o.delivery_address.address_line,
        area: o.delivery_address.area,
        diet: o.diet_type,
        sessions: {},
      })
    }
    const record = customerMap.get(o.customer_id)!
    record.sessions[o.meal_session] = o
  })

  const gridRows = Array.from(customerMap.entries())

  return (
    <div className="space-y-6">
      {/* Date Header and Quick Action */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 font-serif">
              Daily Meal Planner Grid
            </h1>
            <span className="bg-amber-100 text-amber-900 text-xs px-2.5 py-0.5 rounded-full font-bold border border-amber-300">
              Kitchen Operations
            </span>
          </div>
          <p className="text-sm text-stone-500 mt-1">
            {formatDisplayDate(selectedDate)}
          </p>
        </div>

        {/* Date Controls & Generator */}
        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex items-center rounded-lg border border-stone-200 bg-white shadow-xs p-1">
            <button
              onClick={handlePrevDay}
              className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-100 rounded"
              title="Previous Day"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={handleToday}
              className="px-2.5 py-1 text-xs font-semibold text-stone-700 hover:bg-stone-100 rounded"
            >
              Today
            </button>
            <button
              onClick={handleNextDay}
              className="p-1.5 text-stone-500 hover:text-stone-900 hover:bg-stone-100 rounded"
              title="Next Day"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>

          <div className="relative">
            <Input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-40 text-xs font-semibold"
            />
          </div>

          <Button
            onClick={handleGenerate}
            disabled={isGenerating}
            className="bg-amber-600 hover:bg-amber-700 text-white font-semibold text-xs flex items-center gap-1.5 shadow-md"
          >
            {isGenerating ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Sparkles className="w-3.5 h-3.5" />
            )}
            <span>Generate Daily Orders</span>
          </Button>
        </div>
      </div>

      {notification && (
        <div className="p-3 bg-emerald-50 border border-emerald-300 text-emerald-800 rounded-lg text-xs font-medium flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span>{notification}</span>
        </div>
      )}

      {/* Kitchen Prep & Box Count Bar */}
      {summary && (
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 sm:gap-4">
          <Card className="border-stone-200 bg-stone-900 text-white shadow-sm">
            <CardContent className="p-4">
              <div className="text-[11px] font-bold text-stone-400 uppercase tracking-wider">
                Total Day Schedule
              </div>
              <div className="text-2xl font-extrabold mt-1">{summary.total_orders} Meals</div>
              <div className="text-[11px] text-stone-400 mt-1">Across all sessions</div>
            </CardContent>
          </Card>

          <Card className="border-stone-200 shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-700 uppercase tracking-wider">
                  🌅 Breakfast
                </span>
                <span className="text-xs font-bold text-stone-900">{summary.breakfast.total}</span>
              </div>
              <div className="text-xs text-stone-600 mt-2 space-y-0.5">
                <div>Veg: <strong>{summary.breakfast.veg}</strong> &bull; Non-Veg: <strong>{summary.breakfast.non_veg}</strong></div>
                <div className="text-emerald-700">Ready: <strong>{summary.breakfast.ready}</strong></div>
              </div>
              <button
                onClick={() => handleMarkAllReady('BREAKFAST')}
                className="text-[11px] text-amber-800 hover:text-amber-900 font-semibold mt-2 underline"
              >
                Mark All Breakfast Ready &rarr;
              </button>
            </CardContent>
          </Card>

          <Card className="border-stone-200 shadow-sm bg-amber-50/30 border-amber-300/50">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-amber-900 uppercase tracking-wider">
                  ☀️ Lunch Box
                </span>
                <span className="text-xs font-bold text-stone-900">{summary.lunch.total}</span>
              </div>
              <div className="text-xs text-stone-600 mt-2 space-y-0.5">
                <div>Veg: <strong>{summary.lunch.veg}</strong> &bull; Non-Veg: <strong>{summary.lunch.non_veg}</strong></div>
                <div className="text-emerald-700">Ready: <strong>{summary.lunch.ready}</strong></div>
              </div>
              <button
                onClick={() => handleMarkAllReady('LUNCH')}
                className="text-[11px] text-amber-800 hover:text-amber-900 font-semibold mt-2 underline"
              >
                Mark All Lunch Ready &rarr;
              </button>
            </CardContent>
          </Card>

          <Card className="border-stone-200 shadow-sm">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-purple-700 uppercase tracking-wider">
                  🌙 Dinner
                </span>
                <span className="text-xs font-bold text-stone-900">{summary.dinner.total}</span>
              </div>
              <div className="text-xs text-stone-600 mt-2 space-y-0.5">
                <div>Veg: <strong>{summary.dinner.veg}</strong> &bull; Non-Veg: <strong>{summary.dinner.non_veg}</strong></div>
                <div className="text-emerald-700">Ready: <strong>{summary.dinner.ready}</strong></div>
              </div>
              <button
                onClick={() => handleMarkAllReady('DINNER')}
                className="text-[11px] text-amber-800 hover:text-amber-900 font-semibold mt-2 underline"
              >
                Mark All Dinner Ready &rarr;
              </button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Control Filter Toolbar */}
      <Card className="border-stone-200 shadow-sm">
        <CardContent className="p-3.5 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="relative flex-1 max-w-sm">
            <Search className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <Input
              type="text"
              placeholder="Filter by customer name, phone, area..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9 text-xs"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {/* Session Tabs */}
            <div className="inline-flex rounded-lg border border-stone-200 bg-stone-50 p-1 text-xs">
              {(['ALL', 'BREAKFAST', 'LUNCH', 'DINNER'] as const).map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveSessionTab(tab)}
                  className={`px-3 py-1 font-semibold rounded-md transition-all ${
                    activeSessionTab === tab
                      ? 'bg-white text-stone-900 shadow-xs'
                      : 'text-stone-500 hover:text-stone-900'
                  }`}
                >
                  {tab === 'ALL'
                    ? 'All Sessions'
                    : tab === 'BREAKFAST'
                    ? '🌅 Breakfast'
                    : tab === 'LUNCH'
                    ? '☀️ Lunch'
                    : '🌙 Dinner'}
                </button>
              ))}
            </div>

            {/* View Mode */}
            <div className="inline-flex rounded-lg border border-stone-200 bg-stone-50 p-1 text-xs">
              <button
                onClick={() => setMode('GRID')}
                className={`px-3 py-1 font-semibold rounded-md transition-all ${
                  mode === 'GRID' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500'
                }`}
              >
                Grid Mode
              </button>
              <button
                onClick={() => setMode('CARDS')}
                className={`px-3 py-1 font-semibold rounded-md transition-all ${
                  mode === 'CARDS' ? 'bg-white text-stone-900 shadow-xs' : 'text-stone-500'
                }`}
              >
                Cards View
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Grid Mode: The Core Interactive Spreadsheet View */}
      {mode === 'GRID' ? (
        <Card className="border-stone-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-stone-700">
              <thead className="bg-stone-50 border-b border-stone-200 text-xs font-semibold text-stone-500 uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3 min-w-[220px]">Customer & Location</th>
                  <th className="px-4 py-3 min-w-[170px]">🌅 Breakfast Session</th>
                  <th className="px-4 py-3 min-w-[170px]">☀️ Lunch Session</th>
                  <th className="px-4 py-3 min-w-[170px]">🌙 Dinner Session</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200 bg-white">
                {isLoading ? (
                  <tr>
                    <td colSpan={4} className="text-center py-16">
                      <Loader2 className="w-6 h-6 animate-spin text-amber-600 mx-auto" />
                      <span className="text-xs text-stone-500 mt-2 block">Loading daily planner...</span>
                    </td>
                  </tr>
                ) : gridRows.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="text-center py-16 text-stone-400">
                      <Calendar className="w-8 h-8 stroke-1 mx-auto text-stone-300" />
                      <span className="text-sm font-semibold text-stone-700 mt-2 block">
                        No Meal Occurrences for {formatDisplayDate(selectedDate)}
                      </span>
                      <p className="text-xs text-stone-400 max-w-sm mx-auto mt-1">
                        Click <strong>"Generate Daily Orders"</strong> above to auto-create occurrences from active customer subscriptions.
                      </p>
                    </td>
                  </tr>
                ) : (
                  gridRows.map(([customerId, cust]) => (
                    <tr key={customerId} className="hover:bg-stone-50/70 transition-colors">
                      {/* Customer Info */}
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2">
                          <span
                            className={`w-2 h-2 rounded-full ${
                              cust.diet === 'VEG' ? 'bg-emerald-500' : 'bg-red-500'
                            }`}
                            title={cust.diet}
                          />
                          <span className="font-bold text-stone-900 text-sm">{cust.customerName}</span>
                        </div>
                        <div className="text-xs text-stone-500 mt-0.5">{cust.phone}</div>
                        <div className="text-[11px] text-stone-400 truncate max-w-[200px] mt-0.5">
                          {cust.address}, {cust.area}
                        </div>
                      </td>

                      {/* Breakfast Cell */}
                      <td className="px-4 py-3.5">
                        {cust.sessions['BREAKFAST'] ? (
                          <div className="space-y-1">
                            <button
                              onClick={() => handleCycleStatus(cust.sessions['BREAKFAST'])}
                              title="Click to advance status"
                              className="cursor-pointer hover:opacity-80 transition-opacity block"
                            >
                              {getStatusBadge(cust.sessions['BREAKFAST'].status)}
                            </button>
                            <div className="flex items-center justify-between text-[11px] text-stone-500">
                              <span>Qty: {cust.sessions['BREAKFAST'].quantity}</span>
                              <select
                                value={cust.sessions['BREAKFAST'].status}
                                onChange={(e) =>
                                  handleDirectStatusChange(
                                    cust.sessions['BREAKFAST'].id,
                                    e.target.value as OrderStatus
                                  )
                                }
                                className="text-[10px] border border-stone-200 rounded px-1 py-0.5 bg-white text-stone-600"
                              >
                                <option value="PLANNED">Planned</option>
                                <option value="PREPARING">Preparing</option>
                                <option value="READY">Ready</option>
                                <option value="DELIVERED">Delivered</option>
                                <option value="SKIPPED">Skip</option>
                                <option value="CANCELLED">Cancel</option>
                              </select>
                            </div>
                          </div>
                        ) : (
                          <span className="text-stone-300 font-mono text-center block text-sm">—</span>
                        )}
                      </td>

                      {/* Lunch Cell */}
                      <td className="px-4 py-3.5 bg-amber-50/20">
                        {cust.sessions['LUNCH'] ? (
                          <div className="space-y-1">
                            <button
                              onClick={() => handleCycleStatus(cust.sessions['LUNCH'])}
                              title="Click to advance status"
                              className="cursor-pointer hover:opacity-80 transition-opacity block"
                            >
                              {getStatusBadge(cust.sessions['LUNCH'].status)}
                            </button>
                            <div className="flex items-center justify-between text-[11px] text-stone-500">
                              <span>Qty: {cust.sessions['LUNCH'].quantity}</span>
                              <select
                                value={cust.sessions['LUNCH'].status}
                                onChange={(e) =>
                                  handleDirectStatusChange(
                                    cust.sessions['LUNCH'].id,
                                    e.target.value as OrderStatus
                                  )
                                }
                                className="text-[10px] border border-stone-200 rounded px-1 py-0.5 bg-white text-stone-600"
                              >
                                <option value="PLANNED">Planned</option>
                                <option value="PREPARING">Preparing</option>
                                <option value="READY">Ready</option>
                                <option value="DELIVERED">Delivered</option>
                                <option value="SKIPPED">Skip</option>
                                <option value="CANCELLED">Cancel</option>
                              </select>
                            </div>
                          </div>
                        ) : (
                          <span className="text-stone-300 font-mono text-center block text-sm">—</span>
                        )}
                      </td>

                      {/* Dinner Cell */}
                      <td className="px-4 py-3.5">
                        {cust.sessions['DINNER'] ? (
                          <div className="space-y-1">
                            <button
                              onClick={() => handleCycleStatus(cust.sessions['DINNER'])}
                              title="Click to advance status"
                              className="cursor-pointer hover:opacity-80 transition-opacity block"
                            >
                              {getStatusBadge(cust.sessions['DINNER'].status)}
                            </button>
                            <div className="flex items-center justify-between text-[11px] text-stone-500">
                              <span>Qty: {cust.sessions['DINNER'].quantity}</span>
                              <select
                                value={cust.sessions['DINNER'].status}
                                onChange={(e) =>
                                  handleDirectStatusChange(
                                    cust.sessions['DINNER'].id,
                                    e.target.value as OrderStatus
                                  )
                                }
                                className="text-[10px] border border-stone-200 rounded px-1 py-0.5 bg-white text-stone-600"
                              >
                                <option value="PLANNED">Planned</option>
                                <option value="PREPARING">Preparing</option>
                                <option value="READY">Ready</option>
                                <option value="DELIVERED">Delivered</option>
                                <option value="SKIPPED">Skip</option>
                                <option value="CANCELLED">Cancel</option>
                              </select>
                            </div>
                          </div>
                        ) : (
                          <span className="text-stone-300 font-mono text-center block text-sm">—</span>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </Card>
      ) : (
        /* Cards Mode: Focused preparation cards */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {orders.map((order) => (
            <Card key={order.id} className="border-stone-200 shadow-sm hover:shadow transition-all">
              <CardContent className="p-4 space-y-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <div className="font-bold text-stone-900 text-sm">{order.customer_name}</div>
                    <div className="text-xs text-stone-500">{order.customer_phone}</div>
                  </div>
                  {getStatusBadge(order.status)}
                </div>

                <div className="flex items-center gap-2 text-xs">
                  <span
                    className={`font-bold px-2 py-0.5 rounded text-[10px] ${
                      order.diet_type === 'VEG'
                        ? 'bg-emerald-100 text-emerald-900'
                        : 'bg-red-100 text-red-900'
                    }`}
                  >
                    {order.diet_type}
                  </span>
                  <span className="text-stone-600 font-semibold">{order.meal_session}</span>
                  <span className="text-stone-400">&bull; Qty: {order.quantity}</span>
                </div>

                <div className="text-xs text-stone-600 bg-stone-50 p-2 rounded">
                  <div className="truncate font-medium">{order.delivery_address.address_line}</div>
                  <div className="text-[11px] text-stone-400">{order.delivery_address.area}</div>
                </div>

                {order.special_notes && (
                  <div className="text-xs text-amber-800 bg-amber-50 p-1.5 rounded">
                    <strong>Note:</strong> {order.special_notes}
                  </div>
                )}

                <div className="flex items-center justify-between pt-2 border-t border-stone-100">
                  <span className="text-[11px] text-stone-400">
                    {order.assigned_driver_name ? (
                      <span className="text-blue-700 font-semibold">
                        Driver: {order.assigned_driver_name} (#{order.sequence_number})
                      </span>
                    ) : (
                      'Unassigned'
                    )}
                  </span>

                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleCycleStatus(order)}
                    className="text-xs h-7"
                  >
                    Advance Status
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
