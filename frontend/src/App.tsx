import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useSelector } from 'react-redux'
import type { RootState } from './app/store'

import { ProtectedRoute } from './components/auth/ProtectedRoute'
import { AdminLayout } from './components/layout/AdminLayout'
import { DriverLayout } from './components/layout/DriverLayout'

import { LoginPage } from './pages/auth/LoginPage'
import { DashboardPage } from './pages/admin/DashboardPage'
import { DriverTodayPage } from './pages/driver/DriverTodayPage'
import { ModulePlaceholderPage } from './pages/admin/ModulePlaceholderPage'

export function App() {
  const { isAuthenticated, role } = useSelector((state: RootState) => state.auth)

  return (
    <BrowserRouter>
      <Routes>
        {/* Public Login Route */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate
                to={role === 'DRIVER' ? '/driver/today' : '/admin/dashboard'}
                replace
              />
            ) : (
              <LoginPage />
            )
          }
        />

        {/* Root Route Redirect */}
        <Route
          path="/"
          element={
            <Navigate
              to={
                isAuthenticated
                  ? role === 'DRIVER'
                    ? '/driver/today'
                    : '/admin/dashboard'
                  : '/login'
              }
              replace
            />
          }
        />

        {/* Admin & Super Admin Protected Routes */}
        <Route
          path="/admin"
          element={
            <ProtectedRoute allowedRoles={['SUPER_ADMIN', 'ADMIN']}>
              <AdminLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/admin/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route
            path="customers"
            element={
              <ModulePlaceholderPage
                title="Customer Master & Enquiries"
                phase="Phase 3"
                description="Manage customer profiles, dietary preferences, and Google Maps address selection."
              />
            }
          />
          <Route
            path="enquiries"
            element={
              <ModulePlaceholderPage
                title="Enquiries & Leads"
                phase="Phase 3"
                description="Track incoming enquiries and transition them directly into active meal subscribers."
              />
            }
          />
          <Route
            path="meal-planner"
            element={
              <ModulePlaceholderPage
                title="Daily Meal Planner Grid"
                phase="Phase 4"
                description="Interactive spreadsheet-like meal planning for breakfast, lunch, and dinner."
              />
            }
          />
          <Route
            path="deliveries"
            element={
              <ModulePlaceholderPage
                title="Delivery Assignment"
                phase="Phase 4"
                description="Assign delivery orders to active drivers and optimize daily route sequences."
              />
            }
          />
          <Route
            path="live-tracking"
            element={
              <ModulePlaceholderPage
                title="Live Driver Tracking Map"
                phase="Phase 5"
                description="Real-time WebSocket tracking of delivery drivers across customer destination routes."
              />
            }
          />
          <Route
            path="drivers"
            element={
              <ModulePlaceholderPage
                title="Driver Fleet"
                phase="Phase 5"
                description="View active driver availability, vehicle assignments, and shift histories."
              />
            }
          />
          <Route
            path="users"
            element={
              <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                <ModulePlaceholderPage
                  title="User & Access Management"
                  phase="Phase 2 / Super Admin"
                  description="Create, deactivate, and manage administrators and delivery staff accounts."
                />
              </ProtectedRoute>
            }
          />
          <Route
            path="reports"
            element={
              <ModulePlaceholderPage
                title="Business Analytics & Reports"
                phase="Phase 6"
                description="Monthly revenue, active subscription trends, and delivery SLA performance metrics."
              />
            }
          />
          <Route
            path="settings"
            element={
              <ProtectedRoute allowedRoles={['SUPER_ADMIN']}>
                <ModulePlaceholderPage
                  title="System & Delivery Settings"
                  phase="Phase 6"
                  description="Configure delivery radii, delivery charges, and system preferences."
                />
              </ProtectedRoute>
            }
          />
        </Route>

        {/* Driver Protected Routes */}
        <Route
          path="/driver"
          element={
            <ProtectedRoute allowedRoles={['DRIVER']}>
              <DriverLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/driver/today" replace />} />
          <Route path="today" element={<DriverTodayPage />} />
          <Route path="completed" element={<DriverTodayPage />} />
          <Route path="profile" element={<DriverTodayPage />} />
        </Route>

        {/* Fallback 404 */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
