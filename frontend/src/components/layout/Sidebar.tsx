import React from 'react'
import { NavLink } from 'react-router-dom'
import { useSelector } from 'react-redux'
import {
  LayoutDashboard,
  Users,
  MessageSquare,
  Calendar,
  Truck,
  MapPin,
  UserCheck,
  ShieldCheck,
  BarChart3,
  Settings,
  X
} from 'lucide-react'
import type { RootState } from '../../app/store'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

interface NavItem {
  label: string
  to: string
  icon: React.ComponentType<{ className?: string }>
  superAdminOnly?: boolean
}

const navItems: NavItem[] = [
  { label: 'Dashboard', to: '/admin/dashboard', icon: LayoutDashboard },
  { label: 'Customers', to: '/admin/customers', icon: Users },
  { label: 'Enquiries', to: '/admin/enquiries', icon: MessageSquare },
  { label: 'Meal Planner', to: '/admin/meal-planner', icon: Calendar },
  { label: 'Deliveries', to: '/admin/deliveries', icon: Truck },
  { label: 'Live Tracking', to: '/admin/live-tracking', icon: MapPin },
  { label: 'Drivers', to: '/admin/drivers', icon: UserCheck },
  { label: 'Users & Roles', to: '/admin/users', icon: ShieldCheck, superAdminOnly: true },
  { label: 'Reports', to: '/admin/reports', icon: BarChart3 },
  { label: 'Settings', to: '/admin/settings', icon: Settings, superAdminOnly: true },
]

export const Sidebar: React.FC<SidebarProps> = ({ isOpen, onClose }) => {
  const { role } = useSelector((state: RootState) => state.auth)

  const filteredItems = navItems.filter(
    (item) => !item.superAdminOnly || role === 'SUPER_ADMIN'
  )

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-stone-900/50 backdrop-blur-sm lg:hidden transition-opacity"
          onClick={onClose}
        />
      )}

      {/* Sidebar Panel */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-stone-200 shadow-lg lg:shadow-none transform transition-transform duration-200 ease-in-out lg:translate-x-0 lg:static lg:inset-auto lg:h-[calc(100vh-65px)] lg:sticky lg:top-[65px] ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex flex-col h-full">
          {/* Mobile close button header */}
          <div className="flex items-center justify-between p-4 border-b border-stone-200 lg:hidden">
            <span className="font-semibold text-stone-800">Navigation</span>
            <button
              onClick={onClose}
              className="p-1.5 text-stone-500 hover:text-stone-800 hover:bg-stone-100 rounded-md"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation Links */}
          <div className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
            {filteredItems.map((item) => {
              const Icon = item.icon
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  onClick={() => onClose()}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-all ${
                      isActive
                        ? 'bg-amber-500/15 text-amber-900 font-semibold border-l-4 border-amber-600 pl-2.5'
                        : 'text-stone-600 hover:text-stone-900 hover:bg-stone-100'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              )
            })}
          </div>

          {/* Bottom Branding or Status */}
          <div className="p-4 border-t border-stone-200 bg-stone-50/50">
            <div className="text-xs text-stone-500 text-center font-medium">
              Kavi's Kitchen &bull; v1.0
            </div>
          </div>
        </div>
      </aside>
    </>
  )
}
