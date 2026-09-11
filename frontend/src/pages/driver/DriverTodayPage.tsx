import React from 'react'
import {
  Navigation,
  MapPin,
  Phone,
  CheckCircle2,
  Clock
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'

export const DriverTodayPage: React.FC = () => {
  const sampleDeliveries = [
    {
      id: 'DEL-101',
      sequence: 1,
      customerName: 'Anitha Sharma',
      phone: '+91 98401 23456',
      address: 'Flat 4B, Emerald Heights, Anna Nagar East, Chennai',
      mealType: 'Lunch (2 Meals)',
      status: 'IN_PROGRESS',
      deliveryTime: '12:30 PM - 1:00 PM',
    },
    {
      id: 'DEL-102',
      sequence: 2,
      customerName: 'Vikram Sundaram',
      phone: '+91 97910 88776',
      address: '15, 2nd Main Road, Shenoy Nagar, Chennai',
      mealType: 'Lunch (1 Meal)',
      status: 'ASSIGNED',
      deliveryTime: '1:00 PM - 1:30 PM',
    },
    {
      id: 'DEL-103',
      sequence: 3,
      customerName: 'Priya Narayanan',
      phone: '+91 98840 55432',
      address: '22/4, Gandhi Road, Kilpauk, Chennai',
      mealType: 'Lunch (1 Meal)',
      status: 'ASSIGNED',
      deliveryTime: '1:30 PM - 2:00 PM',
    },
  ]

  const openMaps = (address: string) => {
    const url = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
    window.open(url, '_blank')
  }

  return (
    <div className="space-y-4">
      {/* Shift Overview Banner */}
      <div className="bg-stone-900 text-white rounded-xl p-4 shadow-md">
        <div className="flex items-center justify-between">
          <div>
            <span className="text-xs font-semibold uppercase tracking-wider text-amber-400">
              Today's Route &bull; Lunch Shift
            </span>
            <h2 className="text-lg font-bold mt-0.5">
              3 Deliveries Assigned
            </h2>
          </div>
          <div className="text-right">
            <span className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-300 font-semibold">
              <Clock className="w-3 h-3" />
              On Schedule
            </span>
          </div>
        </div>

        {/* Quick progress indicators */}
        <div className="grid grid-cols-3 gap-2 mt-4 pt-3 border-t border-stone-800 text-center">
          <div>
            <div className="text-xl font-bold text-white">3</div>
            <div className="text-[10px] text-stone-400 uppercase">Total</div>
          </div>
          <div>
            <div className="text-xl font-bold text-amber-400">1</div>
            <div className="text-[10px] text-stone-400 uppercase">Active</div>
          </div>
          <div>
            <div className="text-xl font-bold text-emerald-400">0</div>
            <div className="text-[10px] text-stone-400 uppercase">Done</div>
          </div>
        </div>
      </div>

      {/* Delivery Task Cards */}
      <div className="space-y-3">
        <h3 className="text-xs font-bold text-stone-500 uppercase tracking-wider px-1">
          Assigned Sequence
        </h3>

        {sampleDeliveries.map((delivery) => (
          <Card
            key={delivery.id}
            className={`border transition-all shadow-sm ${
              delivery.status === 'IN_PROGRESS'
                ? 'border-amber-400 bg-amber-50/20 ring-1 ring-amber-300'
                : 'border-stone-200'
            }`}
          >
            <CardHeader className="p-3.5 pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="w-6 h-6 rounded-full bg-stone-900 text-white flex items-center justify-center text-xs font-bold">
                    {delivery.sequence}
                  </span>
                  <div>
                    <CardTitle className="text-sm font-bold text-stone-900">
                      {delivery.customerName}
                    </CardTitle>
                    <span className="text-[11px] text-stone-500 font-medium">
                      {delivery.mealType}
                    </span>
                  </div>
                </div>

                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    delivery.status === 'IN_PROGRESS'
                      ? 'bg-amber-100 text-amber-800'
                      : 'bg-stone-100 text-stone-600'
                  }`}
                >
                  {delivery.status === 'IN_PROGRESS' ? 'CURRENT' : 'QUEUED'}
                </span>
              </div>
            </CardHeader>

            <CardContent className="p-3.5 pt-0 space-y-3">
              <div className="flex items-start gap-2 text-xs text-stone-600">
                <MapPin className="w-3.5 h-3.5 text-stone-400 shrink-0 mt-0.5" />
                <span className="leading-snug">{delivery.address}</span>
              </div>

              {/* Action Buttons for Driver */}
              <div className="grid grid-cols-2 gap-2 pt-1">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => openMaps(delivery.address)}
                  className="flex items-center justify-center gap-1.5 text-xs text-blue-700 border-blue-200 hover:bg-blue-50"
                >
                  <Navigation className="w-3.5 h-3.5" />
                  <span>Navigate</span>
                </Button>

                <Button
                  variant="outline"
                  size="sm"
                  asChild
                  className="flex items-center justify-center gap-1.5 text-xs text-stone-700 hover:bg-stone-100"
                >
                  <a href={`tel:${delivery.phone}`}>
                    <Phone className="w-3.5 h-3.5" />
                    <span>Call Customer</span>
                  </a>
                </Button>
              </div>

              {delivery.status === 'IN_PROGRESS' && (
                <Button
                  size="sm"
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold flex items-center justify-center gap-1.5 shadow"
                >
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Mark as Delivered</span>
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
