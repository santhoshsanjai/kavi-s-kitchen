import React, { useState, useEffect, useRef } from 'react'
import {
  MapPin,
  Phone,
  Truck,
  RotateCcw,
  Loader2,
  Radio,
  Compass,
  ExternalLink,
  ShieldCheck,
} from 'lucide-react'
import { Card, CardContent } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { useGetLiveDriversQuery } from '../../features/drivers/driverApiSlice'
import type { LiveDriver } from '../../types/order'

export const LiveTrackingPage: React.FC = () => {
  const { data: initialDrivers = [], isLoading, refetch } = useGetLiveDriversQuery(undefined, {
    pollingInterval: 15000, // Background poll every 15s as fallback to WebSocket
  })

  const [drivers, setDrivers] = useState<LiveDriver[]>([])
  const [selectedDriver, setSelectedDriver] = useState<LiveDriver | null>(null)
  const [wsConnected, setWsConnected] = useState(false)
  const socketRef = useRef<WebSocket | null>(null)

  // Sync initial query data into local state
  useEffect(() => {
    if (initialDrivers.length > 0) {
      setDrivers(initialDrivers)
      if (!selectedDriver) {
        setSelectedDriver(initialDrivers[0])
      }
    }
  }, [initialDrivers])

  // Establish Admin live stream WebSocket
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsHost = window.location.hostname === 'localhost' ? 'localhost:8000' : `${window.location.hostname}:8000`
    const wsUrl = `${wsProtocol}//${wsHost}/api/v1/tracking/ws/admin`

    try {
      const ws = new WebSocket(wsUrl)
      socketRef.current = ws

      ws.onopen = () => {
        console.log('[Admin WS] Live Fleet Stream Connected')
        setWsConnected(true)
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.event === 'INITIAL_FLEET_STATE' && Array.isArray(msg.drivers)) {
            // merge
            refetch()
          } else if (msg.event === 'DRIVER_LOCATION_UPDATE' && msg.data) {
            const update = msg.data
            setDrivers((prev) => {
              const existingIdx = prev.findIndex((d) => d.driver_id === update.driver_id)
              if (existingIdx >= 0) {
                const updatedList = [...prev]
                updatedList[existingIdx] = {
                  ...updatedList[existingIdx],
                  latitude: update.latitude,
                  longitude: update.longitude,
                  speed: update.speed,
                  heading: update.heading,
                  driving_status: update.driving_status || updatedList[existingIdx].driving_status,
                  last_updated: update.timestamp || new Date().toISOString(),
                }
                return updatedList
              }
              return prev
            })

            // Update selected driver if matching
            setSelectedDriver((prev) => {
              if (prev && prev.driver_id === update.driver_id) {
                return {
                  ...prev,
                  latitude: update.latitude,
                  longitude: update.longitude,
                  speed: update.speed,
                  heading: update.heading,
                  driving_status: update.driving_status || prev.driving_status,
                  last_updated: update.timestamp || new Date().toISOString(),
                }
              }
              return prev
            })
          } else if (
            msg.event === 'ORDER_OUT_FOR_DELIVERY' ||
            msg.event === 'ORDER_DELIVERED' ||
            msg.event === 'ORDER_FAILED' ||
            msg.event === 'DRIVER_STATUS_CHANGE'
          ) {
            // Refresh driver list on lifecycle events
            refetch()
          }
        } catch (e) {
          console.warn('[Admin WS] Error parsing message', e)
        }
      }

      ws.onclose = () => {
        setWsConnected(false)
      }

      ws.onerror = () => {
        setWsConnected(false)
      }
    } catch (e) {
      console.warn('[Admin WS] Connection error', e)
    }

    return () => {
      if (socketRef.current) {
        socketRef.current.close()
      }
    }
  }, [refetch])

  const onDeliveryCount = drivers.filter((d) => d.driving_status === 'ON_DELIVERY').length
  const availableCount = drivers.filter((d) => d.driving_status === 'AVAILABLE').length

  const openGoogleMapsLive = (driver: LiveDriver) => {
    let url = `https://www.google.com/maps/search/?api=1&query=${driver.latitude},${driver.longitude}`
    if (driver.active_order?.latitude && driver.active_order?.longitude) {
      url = `https://www.google.com/maps/dir/?api=1&origin=${driver.latitude},${driver.longitude}&destination=${driver.active_order.latitude},${driver.active_order.longitude}`
    }
    window.open(url, '_blank')
  }

  return (
    <div className="space-y-5">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-black text-stone-900 tracking-tight">
              Live Fleet Tracking
            </h1>
            <span
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-bold ${
                wsConnected
                  ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                  : 'bg-amber-100 text-amber-800 border border-amber-300'
              }`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  wsConnected ? 'bg-emerald-500 animate-ping' : 'bg-amber-500'
                }`}
              />
              {wsConnected ? 'Real-time WebSocket Live' : 'Polling Sync (15s)'}
            </span>
          </div>
          <p className="text-sm text-stone-600 mt-0.5">
            Monitor active delivery partners, live GPS paths, and real-time order drop-offs.
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
            Refresh Fleet
          </Button>
        </div>
      </div>

      {/* Fleet KPI Quick Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-stone-500 uppercase">Active Fleet</p>
            <p className="text-2xl font-black text-stone-900 mt-1">{drivers.length}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center text-stone-600">
            <Truck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-amber-600 uppercase">On Route</p>
            <p className="text-2xl font-black text-amber-600 mt-1">{onDeliveryCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600">
            <Radio className="w-5 h-5 animate-pulse" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-emerald-600 uppercase">Available / Idle</p>
            <p className="text-2xl font-black text-emerald-600 mt-1">{availableCount}</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
            <ShieldCheck className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white p-4 rounded-xl border border-stone-200 shadow-sm flex items-center justify-between">
          <div>
            <p className="text-xs font-bold text-stone-500 uppercase">Hub Location</p>
            <p className="text-base font-bold text-stone-800 mt-1 truncate">Anna Nagar, Chennai</p>
          </div>
          <div className="w-10 h-10 rounded-xl bg-stone-100 flex items-center justify-center text-[#1B4D3E]">
            <MapPin className="w-5 h-5" />
          </div>
        </div>
      </div>

      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20 bg-white rounded-2xl border border-stone-200 shadow-sm">
          <Loader2 className="w-8 h-8 animate-spin text-[#E5A93C] mb-2" />
          <p className="text-sm font-medium text-stone-600">Connecting to live fleet stream...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Driver List Column */}
          <div className="lg:col-span-4 space-y-3">
            <h3 className="text-xs font-black text-stone-500 uppercase tracking-wider px-1">
              Active Drivers ({drivers.length})
            </h3>

            {drivers.length === 0 ? (
              <div className="bg-white p-6 rounded-xl border border-stone-200 text-center text-stone-500 text-xs">
                No active drivers online right now.
              </div>
            ) : (
              <div className="space-y-2 max-h-[620px] overflow-y-auto pr-1">
                {drivers.map((driver) => {
                  const isSelected = selectedDriver?.driver_id === driver.driver_id
                  const isOnRoute = driver.driving_status === 'ON_DELIVERY'

                  return (
                    <Card
                      key={driver.driver_id}
                      onClick={() => setSelectedDriver(driver)}
                      className={`cursor-pointer transition-all border rounded-xl overflow-hidden shadow-sm hover:border-[#E5A93C] ${
                        isSelected
                          ? 'border-[#E5A93C] bg-amber-50/20 ring-2 ring-[#E5A93C]/40'
                          : 'border-stone-200 bg-white'
                      }`}
                    >
                      <CardContent className="p-3.5 space-y-2">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <div
                              className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-black ${
                                isOnRoute
                                  ? 'bg-[#E5A93C] text-stone-900'
                                  : 'bg-stone-100 text-stone-700'
                              }`}
                            >
                              <Truck className="w-4 h-4" />
                            </div>
                            <div>
                              <h4 className="font-bold text-stone-900 text-sm">
                                {driver.driver_name}
                              </h4>
                              <p className="text-[11px] text-stone-500">
                                {driver.vehicle_type} &bull; {driver.vehicle_number}
                              </p>
                            </div>
                          </div>

                          <span
                            className={`text-[10px] font-black px-2 py-0.5 rounded-full uppercase ${
                              isOnRoute
                                ? 'bg-amber-100 text-amber-800 border border-amber-300 animate-pulse'
                                : 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            }`}
                          >
                            {driver.driving_status}
                          </span>
                        </div>

                        {/* Current delivery assignment if any */}
                        {driver.active_order ? (
                          <div className="bg-stone-50 rounded-lg p-2 text-xs border border-stone-200 text-stone-700 flex items-start gap-2">
                            <MapPin className="w-3.5 h-3.5 text-[#1B4D3E] shrink-0 mt-0.5" />
                            <div className="truncate">
                              <p className="font-semibold text-stone-900 truncate">
                                Delivering to: {driver.active_order.customer_name}
                              </p>
                              <p className="text-[11px] text-stone-500 truncate">
                                {driver.active_order.area} &bull; {driver.active_order.meal_session}
                              </p>
                            </div>
                          </div>
                        ) : (
                          <p className="text-[11px] text-stone-400 italic">No active order in transit</p>
                        )}
                      </CardContent>
                    </Card>
                  )
                })}
              </div>
            )}
          </div>

          {/* Interactive Map Visualizer & Live Telemetry Details */}
          <div className="lg:col-span-8 space-y-4">
            {selectedDriver ? (
              <div className="bg-white rounded-2xl border border-stone-200 shadow-sm overflow-hidden">
                {/* Simulated High-Res Map Viewport */}
                <div className="relative w-full h-80 bg-stone-900 overflow-hidden flex items-center justify-center text-white">
                  {/* Street grid background pattern */}
                  <div className="absolute inset-0 opacity-20 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px]" />
                  
                  {/* Chennai Locality Indicators */}
                  <div className="absolute top-4 left-4 z-10 bg-stone-900/80 backdrop-blur-md px-3 py-1.5 rounded-lg border border-stone-700 text-xs flex items-center gap-2">
                    <Compass className="w-3.5 h-3.5 text-[#E5A93C]" />
                    <span className="font-bold">Chennai Metropolitan Fleet Map</span>
                  </div>

                  <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
                    <Button
                      size="sm"
                      onClick={() => openGoogleMapsLive(selectedDriver)}
                      className="bg-[#1B4D3E] hover:bg-[#143d31] text-white font-bold text-xs h-8 shadow-md"
                    >
                      <ExternalLink className="w-3.5 h-3.5 mr-1 text-[#E5A93C]" />
                      Open Full Google Maps
                    </Button>
                  </div>

                  {/* Visual Driver Node */}
                  <div className="relative z-10 flex flex-col items-center animate-bounce">
                    <div className="w-12 h-12 rounded-full bg-[#E5A93C] text-stone-900 flex items-center justify-center shadow-2xl border-4 border-white font-black text-base">
                      <Truck className="w-6 h-6" />
                    </div>
                    <div className="bg-stone-900/90 text-white text-[11px] font-bold px-2.5 py-1 rounded-md mt-1 border border-stone-700 shadow-lg whitespace-nowrap">
                      {selectedDriver.driver_name} &bull; {selectedDriver.speed || 0} km/h
                    </div>
                  </div>

                  {/* Route Destination Pin if active order */}
                  {selectedDriver.active_order && (
                    <div className="absolute bottom-6 right-16 z-10 flex flex-col items-center">
                      <div className="w-8 h-8 rounded-full bg-rose-600 text-white flex items-center justify-center shadow-lg border-2 border-white">
                        <MapPin className="w-4 h-4" />
                      </div>
                      <span className="text-[10px] font-bold bg-stone-900/90 text-stone-200 px-2 py-0.5 rounded mt-1 border border-stone-700">
                        {selectedDriver.active_order.customer_name}
                      </span>
                    </div>
                  )}

                  {/* GPS Coordinates readout */}
                  <div className="absolute bottom-3 left-4 text-[10px] font-mono text-stone-400 bg-stone-950/70 px-2 py-1 rounded">
                    Lat: {selectedDriver.latitude.toFixed(6)} | Lng: {selectedDriver.longitude.toFixed(6)}
                  </div>
                </div>

                {/* Driver Telemetry Information */}
                <div className="p-5 space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-stone-100 pb-3">
                    <div>
                      <h3 className="text-lg font-black text-stone-900">
                        {selectedDriver.driver_name}
                      </h3>
                      <p className="text-xs text-stone-500">
                        Vehicle: {selectedDriver.vehicle_type} ({selectedDriver.vehicle_number})
                      </p>
                    </div>

                    <div className="flex items-center gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        asChild
                        className="h-9 border-stone-300 text-stone-700 hover:bg-stone-100 text-xs font-bold"
                      >
                        <a href={`tel:${selectedDriver.phone || '9876543210'}`}>
                          <Phone className="w-3.5 h-3.5 mr-1 text-emerald-600" />
                          Call Driver
                        </a>
                      </Button>
                    </div>
                  </div>

                  {/* Active Order Card */}
                  {selectedDriver.active_order ? (
                    <div className="bg-amber-50/40 rounded-xl p-4 border border-amber-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-amber-800 uppercase tracking-wider">
                          Active In-Transit Order
                        </span>
                        <span className="text-xs font-bold text-stone-700">
                          {selectedDriver.active_order.quantity} x {selectedDriver.active_order.meal_session}
                        </span>
                      </div>

                      <div>
                        <h4 className="font-bold text-stone-900 text-sm">
                          {selectedDriver.active_order.customer_name}
                        </h4>
                        <p className="text-xs text-stone-600 mt-0.5">
                          {selectedDriver.active_order.address_line}, {selectedDriver.active_order.area}
                        </p>
                      </div>

                      <div className="pt-2 flex items-center justify-between text-xs">
                        <a
                          href={`tel:${selectedDriver.active_order.customer_phone}`}
                          className="font-bold text-emerald-700 hover:underline flex items-center gap-1"
                        >
                          <Phone className="w-3 h-3" />
                          {selectedDriver.active_order.customer_phone}
                        </a>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-stone-50 rounded-xl p-4 border border-stone-200 text-center text-xs text-stone-500">
                      Driver currently has no order out for delivery. Ready for assignment.
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-2xl border border-stone-200 shadow-sm p-12 text-center text-stone-500">
                <Truck className="w-12 h-12 mx-auto text-stone-300 mb-2" />
                <h4 className="font-bold text-stone-700">Select a Driver</h4>
                <p className="text-xs text-stone-400 mt-1">
                  Choose a driver from the left roster to view live coordinates and delivery progress.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
