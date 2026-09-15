import React, { useState, useEffect, useRef } from 'react'
import {
  Navigation,
  MapPin,
  Phone,
  CheckCircle2,
  Truck,
  AlertTriangle,
  Play,
  RotateCcw,
  Loader2,
  XCircle,
  Radio,
  Coffee,
  Check,
  Compass
} from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import {
  useGetMyTodayDeliveriesQuery,
  useUpdateMyStatusMutation,
} from '../../features/drivers/driverApiSlice'
import {
  useStartDeliveryMutation,
  useCompleteDeliveryMutation,
  useFailDeliveryMutation,
} from '../../features/orders/orderApiSlice'
import type { Order } from '../../types/order'

export const DriverTodayPage: React.FC = () => {
  const { data, isLoading, refetch } = useGetMyTodayDeliveriesQuery()
  const [updateStatus] = useUpdateMyStatusMutation()
  const [startDeliveryMutation, { isLoading: isStarting }] = useStartDeliveryMutation()
  const [completeDeliveryMutation, { isLoading: isCompleting }] = useCompleteDeliveryMutation()
  const [failDeliveryMutation, { isLoading: isFailing }] = useFailDeliveryMutation()

  // Modal dialog states
  const [completeModalOrder, setCompleteModalOrder] = useState<Order | null>(null)
  const [failModalOrder, setFailModalOrder] = useState<Order | null>(null)
  const [recipientName, setRecipientName] = useState('')
  const [deliveryNote, setDeliveryNote] = useState('')
  const [failReason, setFailReason] = useState('CUSTOMER_UNAVAILABLE')
  const [failNote, setFailNote] = useState('')
  const [gpsError, setGpsError] = useState<string | null>(null)
  const [currentCoords, setCurrentCoords] = useState<{ lat: number; lng: number; speed?: number } | null>(null)

  // WebSocket reference for live GPS streaming
  const socketRef = useRef<WebSocket | null>(null)
  const watchIdRef = useRef<number | null>(null)

  const orders = data?.orders || []
  const driverId = data?.driver_id
  const drivingStatus = data?.driving_status || 'AVAILABLE'

  // Active order currently out for delivery
  const activeOrder = orders.find((o) => o.status === 'OUT_FOR_DELIVERY')

  // Setup live GPS tracking when driver is ON_DELIVERY or has an active order
  useEffect(() => {
    if (!driverId) return

    const isTrackingActive = drivingStatus === 'ON_DELIVERY' || !!activeOrder

    if (isTrackingActive && 'geolocation' in navigator) {
      // Connect WebSocket to backend tracking endpoint
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : `${window.location.hostname}:8000`
      const wsUrl = `${wsProtocol}//${wsHost}/api/v1/tracking/ws/driver/${driverId}`

      try {
        const ws = new WebSocket(wsUrl)
        socketRef.current = ws

        ws.onopen = () => {
          console.log('[GPS WS] Connected to live tracking stream')
          setGpsError(null)
        }

        ws.onerror = (e) => {
          console.warn('[GPS WS] WebSocket error:', e)
        }

        ws.onclose = () => {
          console.log('[GPS WS] Disconnected')
        }

        // Start watchPosition
        watchIdRef.current = navigator.geolocation.watchPosition(
          (pos) => {
            const lat = pos.coords.latitude
            const lng = pos.coords.longitude
            const speed = pos.coords.speed ? Math.round(pos.coords.speed * 3.6) : 0 // km/h
            const heading = pos.coords.heading || 0

            setCurrentCoords({ lat, lng, speed })
            setGpsError(null)

            if (ws.readyState === WebSocket.OPEN) {
              ws.send(
                JSON.stringify({
                  latitude: lat,
                  longitude: lng,
                  speed,
                  heading,
                  driving_status: 'ON_DELIVERY',
                  active_order_id: activeOrder?.id,
                  customer_name: activeOrder?.customer_name,
                  destination_lat: activeOrder?.delivery_address?.latitude,
                  destination_lng: activeOrder?.delivery_address?.longitude,
                  timestamp: new Date().toISOString(),
                })
              )
            }
          },
          (err) => {
            console.warn('[GPS Geolocation Error]', err.message)
            setGpsError('Location permission required for live delivery tracking')
          },
          {
            enableHighAccuracy: true,
            maximumAge: 5000,
            timeout: 10000,
          }
        )
      } catch (err) {
        console.error('[GPS Setup Error]', err)
      }
    } else {
      // Clean up tracking when offline or idle
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current)
        watchIdRef.current = null
      }
      if (socketRef.current) {
        socketRef.current.close()
        socketRef.current = null
      }
      setCurrentCoords(null)
    }

    return () => {
      if (watchIdRef.current !== null) {
        navigator.geolocation.clearWatch(watchIdRef.current)
      }
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [driverId, drivingStatus, activeOrder])

  const handleStatusToggle = async (newStatus: string) => {
    try {
      await updateStatus({ driving_status: newStatus }).unwrap()
      refetch()
    } catch (err) {
      console.error('Failed to update status', err)
    }
  }

  const handleStartDelivery = async (orderId: string) => {
    try {
      await startDeliveryMutation(orderId).unwrap()
      refetch()
    } catch (err) {
      console.error('Failed to start delivery', err)
    }
  }

  const handleCompleteSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!completeModalOrder) return

    try {
      await completeDeliveryMutation({
        id: completeModalOrder.id,
        recipient_name: recipientName.trim() || completeModalOrder.customer_name,
        delivery_note: deliveryNote.trim() || undefined,
      }).unwrap()

      setCompleteModalOrder(null)
      setRecipientName('')
      setDeliveryNote('')
      refetch()
    } catch (err) {
      console.error('Failed to complete delivery', err)
    }
  }

  const handleFailSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!failModalOrder) return

    try {
      await failDeliveryMutation({
        id: failModalOrder.id,
        reason: failReason,
        notes: failNote.trim() || undefined,
      }).unwrap()

      setFailModalOrder(null)
      setFailReason('CUSTOMER_UNAVAILABLE')
      setFailNote('')
      refetch()
    } catch (err) {
      console.error('Failed to record delivery failure', err)
    }
  }

  const openNavigation = (order: Order) => {
    const addr = order.delivery_address
    let url = ''
    if (addr?.latitude && addr?.longitude) {
      url = `https://www.google.com/maps/dir/?api=1&destination=${addr.latitude},${addr.longitude}`
    } else {
      const fullAddress = `${addr?.address_line || ''}, ${addr?.area || ''}, ${addr?.city || 'Chennai'}`
      url = `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(fullAddress)}`
    }
    window.open(url, '_blank')
  }

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <Loader2 className="w-8 h-8 animate-spin text-[#E5A93C]" />
        <p className="text-sm font-medium text-stone-600">Loading today's route...</p>
      </div>
    )
  }

  const activeDeliveries = orders.filter(
    (o) => o.status !== 'DELIVERED' && o.status !== 'FAILED' && o.status !== 'CANCELLED'
  )
  const completedDeliveries = orders.filter((o) => o.status === 'DELIVERED')
  const failedDeliveries = orders.filter((o) => o.status === 'FAILED')

  return (
    <div className="space-y-4 max-w-lg mx-auto pb-12">
      {/* Driver Shift Banner */}
      <div className="bg-stone-900 text-white rounded-2xl p-4 shadow-lg border border-stone-800">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-1.5 text-xs font-semibold text-[#E5A93C] uppercase tracking-wider">
              <Compass className="w-3.5 h-3.5" />
              <span>{data?.date || new Date().toISOString().split('T')[0]}</span>
            </div>
            <h2 className="text-xl font-bold mt-0.5 text-stone-100">
              {data?.driver_name || 'Delivery Partner'}
            </h2>
          </div>

          {/* Quick status dropdown / toggle */}
          <div className="flex items-center gap-1.5">
            {drivingStatus === 'ON_DELIVERY' ? (
              <span className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30 animate-pulse">
                <Radio className="w-3 h-3 text-amber-400" />
                ON ROUTE
              </span>
            ) : drivingStatus === 'AVAILABLE' ? (
              <button
                onClick={() => handleStatusToggle('PAUSED')}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/30 transition-all"
              >
                <Check className="w-3 h-3 text-emerald-400" />
                ONLINE
              </button>
            ) : (
              <button
                onClick={() => handleStatusToggle('AVAILABLE')}
                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-xs font-bold bg-stone-700 text-stone-300 border border-stone-600 hover:bg-stone-600 transition-all"
              >
                <Coffee className="w-3 h-3 text-stone-300" />
                PAUSED
              </button>
            )}
          </div>
        </div>

        {/* GPS Live Tracking State */}
        {currentCoords && (
          <div className="mt-3 py-1.5 px-3 rounded-lg bg-emerald-950/40 border border-emerald-800/50 flex items-center justify-between text-xs text-emerald-300">
            <span className="flex items-center gap-1.5 font-medium">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
              Live GPS Streaming Active
            </span>
            <span className="font-mono text-[11px] text-emerald-200">
              {currentCoords.speed || 0} km/h &bull; {currentCoords.lat.toFixed(4)}, {currentCoords.lng.toFixed(4)}
            </span>
          </div>
        )}

        {gpsError && (
          <div className="mt-3 py-1.5 px-3 rounded-lg bg-amber-950/40 border border-amber-800/50 flex items-center gap-2 text-xs text-amber-300">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            <span>{gpsError}</span>
          </div>
        )}

        {/* Route Summary Stats */}
        <div className="grid grid-cols-4 gap-2 mt-4 pt-3 border-t border-stone-800 text-center">
          <div>
            <div className="text-xl font-black text-white">{data?.total_assigned || 0}</div>
            <div className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">Total</div>
          </div>
          <div>
            <div className="text-xl font-black text-[#E5A93C]">{activeDeliveries.length}</div>
            <div className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">Pending</div>
          </div>
          <div>
            <div className="text-xl font-black text-emerald-400">{completedDeliveries.length}</div>
            <div className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">Done</div>
          </div>
          <div>
            <div className="text-xl font-black text-rose-400">{failedDeliveries.length}</div>
            <div className="text-[10px] font-bold text-stone-400 uppercase tracking-wider">Failed</div>
          </div>
        </div>
      </div>

      {/* Active Orders List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h3 className="text-xs font-black text-stone-500 uppercase tracking-widest">
            Today's Sequence ({activeDeliveries.length} Remaining)
          </h3>
          <button
            onClick={() => refetch()}
            className="text-xs text-stone-500 hover:text-stone-800 flex items-center gap-1 font-semibold"
          >
            <RotateCcw className="w-3 h-3" />
            Refresh
          </button>
        </div>

        {activeDeliveries.length === 0 ? (
          <div className="text-center py-10 bg-white rounded-2xl border border-stone-200 shadow-sm p-6">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-2" />
            <h4 className="text-base font-bold text-stone-800">All deliveries finished!</h4>
            <p className="text-xs text-stone-500 mt-1">
              You have completed all assigned orders for today. Great job!
            </p>
          </div>
        ) : (
          activeDeliveries.map((order, idx) => {
            const isCurrentActive = order.status === 'OUT_FOR_DELIVERY'
            const seqDisplay = order.sequence_number || idx + 1

            return (
              <Card
                key={order.id}
                className={`border rounded-2xl overflow-hidden shadow-sm transition-all ${
                  isCurrentActive
                    ? 'border-[#E5A93C] bg-amber-50/20 ring-2 ring-[#E5A93C]/40'
                    : 'border-stone-200 bg-white'
                }`}
              >
                <CardContent className="p-4 space-y-3">
                  {/* Top Bar: Sequence + Customer Info */}
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-2.5">
                      <span
                        className={`w-9 h-9 rounded-xl flex items-center justify-center font-black text-sm shrink-0 shadow-sm ${
                          isCurrentActive
                            ? 'bg-[#E5A93C] text-stone-900 font-bold'
                            : 'bg-stone-100 text-stone-700 font-bold border border-stone-200'
                        }`}
                      >
                        #{seqDisplay < 10 ? `0${seqDisplay}` : seqDisplay}
                      </span>
                      <div>
                        <h4 className="font-bold text-stone-900 text-base leading-tight">
                          {order.customer_name}
                        </h4>
                        <div className="flex items-center gap-2 mt-1">
                          <span className="text-[11px] font-bold px-2 py-0.5 rounded bg-stone-100 text-stone-700 uppercase">
                            {order.meal_session} &bull; {order.quantity} {order.quantity === 1 ? 'Meal' : 'Meals'}
                          </span>
                          <span
                            className={`text-[10px] font-black px-1.5 py-0.5 rounded uppercase ${
                              order.diet_type === 'NON_VEG'
                                ? 'bg-rose-100 text-rose-700'
                                : 'bg-emerald-100 text-emerald-700'
                            }`}
                          >
                            {order.diet_type}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Status Badge */}
                    <div>
                      {isCurrentActive ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold px-2.5 py-1 rounded-full bg-amber-500 text-stone-900 animate-pulse">
                          <Truck className="w-3 h-3" />
                          OUT FOR DELIVERY
                        </span>
                      ) : (
                        <span className="text-[11px] font-semibold px-2 py-0.5 rounded bg-stone-100 text-stone-600">
                          {order.status}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Delivery Address & Distance */}
                  <div className="bg-stone-50 rounded-xl p-3 border border-stone-200/80 space-y-1.5 text-xs text-stone-700">
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-[#1B4D3E] shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-stone-900">
                          {order.delivery_address?.area || 'Chennai Locality'}
                        </p>
                        <p className="text-stone-600 mt-0.5 leading-snug">
                          {order.delivery_address?.address_line}
                        </p>
                        {order.delivery_address?.landmark && (
                          <p className="text-stone-500 text-[11px] italic mt-0.5">
                            Landmark: {order.delivery_address.landmark}
                          </p>
                        )}
                      </div>
                    </div>

                    {/* Special Preferences */}
                    {(order.special_notes || order.rice_preference || order.spice_level) && (
                      <div className="pt-1.5 border-t border-stone-200/60 text-[11px] text-stone-600 flex flex-wrap gap-2">
                        {order.rice_preference && <span>Rice: <strong>{order.rice_preference}</strong></span>}
                        {order.spice_level && <span>Spice: <strong>{order.spice_level}</strong></span>}
                        {order.special_notes && <span className="text-amber-700 italic">"{order.special_notes}"</span>}
                      </div>
                    )}
                  </div>

                  {/* Quick Action Buttons: Call & Navigate */}
                  <div className="grid grid-cols-2 gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      asChild
                      className="h-9 border-stone-300 text-stone-700 hover:bg-stone-100 font-bold"
                    >
                      <a href={`tel:${order.customer_phone}`}>
                        <Phone className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                        Call ({order.customer_phone})
                      </a>
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => openNavigation(order)}
                      className="h-9 border-stone-300 text-stone-700 hover:bg-stone-100 font-bold"
                    >
                      <Navigation className="w-3.5 h-3.5 mr-1.5 text-[#1B4D3E]" />
                      Navigate Map
                    </Button>
                  </div>

                  {/* Delivery Flow Action: START or COMPLETE / FAILED */}
                  <div className="pt-1 border-t border-stone-100">
                    {order.status !== 'OUT_FOR_DELIVERY' ? (
                      <Button
                        onClick={() => handleStartDelivery(order.id)}
                        disabled={isStarting}
                        className="w-full h-11 bg-[#1B4D3E] hover:bg-[#143d31] text-white font-black text-sm tracking-wide shadow-md"
                      >
                        {isStarting ? (
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        ) : (
                          <Play className="w-4 h-4 mr-2 text-[#E5A93C] fill-[#E5A93C]" />
                        )}
                        START DELIVERY
                      </Button>
                    ) : (
                      <div className="grid grid-cols-3 gap-2">
                        <Button
                          onClick={() => setCompleteModalOrder(order)}
                          className="col-span-2 h-11 bg-emerald-600 hover:bg-emerald-700 text-white font-black text-sm tracking-wide shadow-md"
                        >
                          <CheckCircle2 className="w-4 h-4 mr-1.5" />
                          COMPLETE
                        </Button>
                        <Button
                          variant="outline"
                          onClick={() => setFailModalOrder(order)}
                          className="col-span-1 h-11 border-rose-300 text-rose-700 hover:bg-rose-50 font-bold text-xs"
                        >
                          <XCircle className="w-3.5 h-3.5 mr-1 text-rose-600" />
                          FAILED
                        </Button>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })
        )}
      </div>

      {/* Completed Deliveries History Section */}
      {completedDeliveries.length > 0 && (
        <div className="mt-8 space-y-2 pt-4 border-t border-stone-200">
          <h3 className="text-xs font-black text-stone-400 uppercase tracking-wider px-1">
            Completed Today ({completedDeliveries.length})
          </h3>
          {completedDeliveries.map((order) => (
            <div
              key={order.id}
              className="bg-white rounded-xl p-3 border border-stone-200 flex items-center justify-between text-xs text-stone-600"
            >
              <div className="flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                <div>
                  <p className="font-bold text-stone-900">{order.customer_name}</p>
                  <p className="text-[11px] text-stone-500">
                    {order.delivery_address?.area} &bull; {order.quantity} {order.meal_session}
                  </p>
                </div>
              </div>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
                Delivered
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Modal: Complete Delivery */}
      {completeModalOrder && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-2xl border border-stone-200 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center gap-2.5 text-emerald-700">
              <CheckCircle2 className="w-6 h-6" />
              <h3 className="text-base font-bold text-stone-900">Confirm Delivery</h3>
            </div>

            <p className="text-xs text-stone-600 leading-relaxed">
              Completing delivery for <strong>{completeModalOrder.customer_name}</strong> at{' '}
              {completeModalOrder.delivery_address?.area}.
            </p>

            <form onSubmit={handleCompleteSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">
                  Recipient Name
                </label>
                <Input
                  placeholder={completeModalOrder.customer_name}
                  value={recipientName}
                  onChange={(e) => setRecipientName(e.target.value)}
                  className="h-10 text-sm"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">
                  Delivery Note (Optional)
                </label>
                <Input
                  placeholder="e.g. Handed to security / Left at door"
                  value={deliveryNote}
                  onChange={(e) => setDeliveryNote(e.target.value)}
                  className="h-10 text-sm"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setCompleteModalOrder(null)}
                  className="w-1/2 h-10 border-stone-300 text-stone-700 font-bold text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isCompleting}
                  className="w-1/2 h-10 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md"
                >
                  {isCompleting ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
                  Confirm Delivered
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Failed Delivery */}
      {failModalOrder && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-sm w-full p-5 space-y-4 shadow-2xl border border-stone-200 animate-in fade-in zoom-in duration-150">
            <div className="flex items-center gap-2.5 text-rose-700">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-base font-bold text-stone-900">Record Failed Delivery</h3>
            </div>

            <p className="text-xs text-stone-600 leading-relaxed">
              Order for <strong>{failModalOrder.customer_name}</strong> could not be completed.
              Please select the reason below.
            </p>

            <form onSubmit={handleFailSubmit} className="space-y-3">
              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">
                  Failure Reason
                </label>
                <select
                  value={failReason}
                  onChange={(e) => setFailReason(e.target.value)}
                  className="w-full h-10 px-3 text-sm rounded-lg border border-stone-300 bg-white font-medium focus:ring-2 focus:ring-rose-500 focus:outline-none"
                >
                  <option value="CUSTOMER_UNAVAILABLE">Customer Unavailable / Not Answering</option>
                  <option value="WRONG_ADDRESS">Wrong Address / Unable to Locate</option>
                  <option value="PHONE_UNREACHABLE">Phone Number Switched Off / Unreachable</option>
                  <option value="CUSTOMER_CANCELLED">Customer Cancelled on Arrival</option>
                  <option value="LOCATION_INACCESSIBLE">Location Inaccessible / Security Block</option>
                  <option value="OTHER">Other Reason (Explain in Note)</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-stone-700 block mb-1">
                  Additional Details
                </label>
                <Input
                  placeholder="Explain what happened..."
                  value={failNote}
                  onChange={(e) => setFailNote(e.target.value)}
                  required={failReason === 'OTHER'}
                  className="h-10 text-sm"
                />
              </div>

              <div className="flex items-center gap-2 pt-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setFailModalOrder(null)}
                  className="w-1/2 h-10 border-stone-300 text-stone-700 font-bold text-xs"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isFailing}
                  className="w-1/2 h-10 bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-md"
                >
                  {isFailing ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : null}
                  Mark Failed
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
