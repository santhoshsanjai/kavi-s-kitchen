import React from 'react'
import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useDispatch, useSelector } from 'react-redux'
import type { RootState } from '../../app/store'
import { logOut } from '../../features/auth/authSlice'
import { LogOut, Navigation, CheckCircle2, User } from 'lucide-react'
import { Button } from '../ui/button'
import logoImg from '../../assets/logo.png'

export const DriverLayout: React.FC = () => {
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const { user } = useSelector((state: RootState) => state.auth)

  const handleLogout = () => {
    dispatch(logOut())
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-stone-100 flex flex-col pb-20 sm:pb-0">
      {/* Mobile-first Header */}
      <header className="sticky top-0 z-30 bg-white border-b border-stone-200 px-4 py-3 shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src={logoImg} alt="Logo" className="h-9 w-auto object-contain" />
          <div>
            <div className="font-bold text-stone-900 text-sm leading-tight">
              {user?.full_name || 'Driver Portal'}
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-[11px] font-medium text-emerald-700">Online &bull; On Duty</span>
            </div>
          </div>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={handleLogout}
          className="text-stone-500 hover:text-red-600 hover:bg-red-50 p-2"
          title="Logout"
        >
          <LogOut className="w-4 h-4" />
        </Button>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-3 sm:p-6 max-w-lg mx-auto w-full">
        <Outlet />
      </main>

      {/* Driver Bottom Navigation Bar (Mobile-friendly thumb access) */}
      <nav className="fixed bottom-0 inset-x-0 bg-white border-t border-stone-200 z-30 sm:hidden">
        <div className="grid grid-cols-3 h-16">
          <NavLink
            to="/driver/today"
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-1 text-xs font-medium transition-colors ${
                isActive ? 'text-amber-700 font-semibold' : 'text-stone-500'
              }`
            }
          >
            <Navigation className="w-5 h-5" />
            <span>Deliveries</span>
          </NavLink>

          <NavLink
            to="/driver/completed"
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-1 text-xs font-medium transition-colors ${
                isActive ? 'text-amber-700 font-semibold' : 'text-stone-500'
              }`
            }
          >
            <CheckCircle2 className="w-5 h-5" />
            <span>Completed</span>
          </NavLink>

          <NavLink
            to="/driver/profile"
            className={({ isActive }) =>
              `flex flex-col items-center justify-center gap-1 text-xs font-medium transition-colors ${
                isActive ? 'text-amber-700 font-semibold' : 'text-stone-500'
              }`
            }
          >
            <User className="w-5 h-5" />
            <span>Profile</span>
          </NavLink>
        </div>
      </nav>
    </div>
  )
}
