import React from 'react'
import { useSelector } from 'react-redux'
import type { RootState } from '../../app/store'
import {
  Users,
  UtensilsCrossed,
  Truck,
  MessageSquare,
  Calendar,
  MapPin,
  TrendingUp,
  ArrowRight
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Link } from 'react-router-dom'

export const DashboardPage: React.FC = () => {
  const { user } = useSelector((state: RootState) => state.auth)

  const quickStats = [
    {
      title: 'Active Customers',
      value: '48',
      change: '+12% this month',
      icon: Users,
      color: 'text-amber-700 bg-amber-100',
    },
    {
      title: "Today's Meals",
      value: '134',
      change: 'Breakfast: 42 • Lunch: 56 • Dinner: 36',
      icon: UtensilsCrossed,
      color: 'text-emerald-700 bg-emerald-100',
    },
    {
      title: 'Active Deliveries',
      value: '18',
      change: '3 Drivers on route',
      icon: Truck,
      color: 'text-blue-700 bg-blue-100',
    },
    {
      title: 'New Enquiries',
      value: '6',
      change: '2 pending follow-up',
      icon: MessageSquare,
      color: 'text-purple-700 bg-purple-100',
    },
  ]

  return (
    <div className="space-y-6">
      {/* Welcome Banner */}
      <div className="bg-gradient-to-r from-amber-600 to-amber-700 text-white rounded-2xl p-6 sm:p-8 shadow-md relative overflow-hidden">
        <div className="relative z-10 max-w-2xl">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/20 text-xs font-semibold backdrop-blur mb-3">
            <TrendingUp className="w-3.5 h-3.5" />
            <span>Kitchen Operations Active</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight font-serif">
            Welcome back, {user?.full_name || 'Chef'}!
          </h1>
          <p className="mt-2 text-amber-100 text-sm sm:text-base leading-relaxed">
            Here is your daily kitchen overview. Track active meal subscriptions, coordinate driver delivery routes, and manage customer preferences in real time.
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button
              asChild
              className="bg-white text-stone-900 hover:bg-stone-100 font-semibold shadow"
            >
              <Link to="/admin/meal-planner" className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-amber-700" />
                <span>Open Meal Planner</span>
              </Link>
            </Button>
            <Button
              asChild
              variant="outline"
              className="bg-transparent text-white border-white/40 hover:bg-white/10 hover:text-white"
            >
              <Link to="/admin/live-tracking" className="flex items-center gap-2">
                <MapPin className="w-4 h-4 text-amber-300" />
                <span>Live Driver Map</span>
              </Link>
            </Button>
          </div>
        </div>

        {/* Decorative background element */}
        <div className="absolute right-0 bottom-0 opacity-10 translate-x-8 translate-y-8 pointer-events-none hidden md:block">
          <UtensilsCrossed className="w-64 h-64 text-white" />
        </div>
      </div>

      {/* Quick Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
        {quickStats.map((stat) => {
          const Icon = stat.icon
          return (
            <Card key={stat.title} className="shadow-sm hover:shadow-md transition-shadow border-stone-200">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-xs font-semibold text-stone-500 uppercase tracking-wider">
                  {stat.title}
                </CardTitle>
                <div className={`p-2 rounded-lg ${stat.color}`}>
                  <Icon className="w-4 h-4" />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-stone-900">{stat.value}</div>
                <p className="text-xs text-stone-500 mt-1">{stat.change}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Quick Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6">
        <Card className="border-stone-200 hover:border-amber-400 transition-colors">
          <CardHeader>
            <CardTitle className="text-base font-bold text-stone-900 flex items-center justify-between">
              <span>Customer Management</span>
              <Users className="w-4 h-4 text-amber-600" />
            </CardTitle>
            <CardDescription className="text-xs text-stone-500">
              Create, edit, and organize customer profiles, addresses, and diet preferences.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="ghost" size="sm" className="w-full justify-between text-amber-700 hover:text-amber-800 hover:bg-amber-50">
              <Link to="/admin/customers">
                <span>View All Customers</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="border-stone-200 hover:border-emerald-400 transition-colors">
          <CardHeader>
            <CardTitle className="text-base font-bold text-stone-900 flex items-center justify-between">
              <span>Meal Planning Grid</span>
              <Calendar className="w-4 h-4 text-emerald-600" />
            </CardTitle>
            <CardDescription className="text-xs text-stone-500">
              Schedule breakfast, lunch, and dinner deliveries across active subscriptions.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="ghost" size="sm" className="w-full justify-between text-emerald-700 hover:text-emerald-800 hover:bg-emerald-50">
              <Link to="/admin/meal-planner">
                <span>Launch Grid Planner</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>

        <Card className="border-stone-200 hover:border-blue-400 transition-colors">
          <CardHeader>
            <CardTitle className="text-base font-bold text-stone-900 flex items-center justify-between">
              <span>Delivery Assignment</span>
              <Truck className="w-4 h-4 text-blue-600" />
            </CardTitle>
            <CardDescription className="text-xs text-stone-500">
              Assign routes to drivers and monitor live progress and completed drops.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="ghost" size="sm" className="w-full justify-between text-blue-700 hover:text-blue-800 hover:bg-blue-50">
              <Link to="/admin/deliveries">
                <span>Manage Deliveries</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
