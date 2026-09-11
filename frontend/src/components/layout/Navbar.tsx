import React from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { useNavigate } from 'react-router-dom'
import { LogOut, Menu, UserCheck, Shield, Utensils } from 'lucide-react'
import type { RootState } from '../../app/store'
import { logOut } from '../../features/auth/authSlice'
import { Button } from '../ui/button'
import logoImg from '../../assets/logo.png'

interface NavbarProps {
  onToggleSidebar?: () => void
}

export const Navbar: React.FC<NavbarProps> = ({ onToggleSidebar }) => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { user, role } = useSelector((state: RootState) => state.auth)

  const handleLogout = () => {
    dispatch(logOut())
    navigate('/login')
  }

  const getRoleBadge = (userRole?: string | null) => {
    switch (userRole) {
      case 'SUPER_ADMIN':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 text-amber-900 border border-amber-300">
            <Shield className="w-3 h-3 text-amber-700" />
            Super Admin
          </span>
        )
      case 'ADMIN':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-900 border border-emerald-300">
            <Utensils className="w-3 h-3 text-emerald-700" />
            Kitchen Admin
          </span>
        )
      case 'DRIVER':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-100 text-blue-900 border border-blue-300">
            <UserCheck className="w-3 h-3 text-blue-700" />
            Driver
          </span>
        )
      default:
        return null
    }
  }

  return (
    <header className="sticky top-0 z-40 bg-white/95 backdrop-blur border-b border-stone-200 shadow-sm transition-all">
      <div className="flex items-center justify-between px-4 py-2.5 sm:px-6">
        {/* Left Side: Brand Logo & Mobile Toggle */}
        <div className="flex items-center gap-3">
          {onToggleSidebar && (
            <button
              onClick={onToggleSidebar}
              className="lg:hidden p-2 text-stone-600 hover:text-stone-900 hover:bg-stone-100 rounded-md focus:outline-none focus:ring-2 focus:ring-primary"
              aria-label="Toggle Navigation"
            >
              <Menu className="w-5 h-5" />
            </button>
          )}
          <div className="flex items-center gap-2.5">
            <img
              src={logoImg}
              alt="Kavi's Kitchen Logo"
              className="h-10 w-auto object-contain drop-shadow-sm"
            />
            <div className="hidden sm:block">
              <span className="text-lg font-bold tracking-tight text-stone-900 font-serif">
                Kavi's Kitchen
              </span>
              <span className="block text-[11px] font-medium text-stone-500 uppercase tracking-wider">
                Management System
              </span>
            </div>
          </div>
        </div>

        {/* Right Side: User Profile & Logout */}
        <div className="flex items-center gap-3 sm:gap-4">
          <div className="hidden sm:flex flex-col items-end">
            <span className="text-sm font-semibold text-stone-800">
              {user?.full_name || user?.username || 'User'}
            </span>
            <div className="mt-0.5">{getRoleBadge(role)}</div>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleLogout}
            className="flex items-center gap-1.5 text-stone-700 hover:text-red-700 hover:bg-red-50 hover:border-red-200 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            <span className="hidden sm:inline">Logout</span>
          </Button>
        </div>
      </div>
    </header>
  )
}
