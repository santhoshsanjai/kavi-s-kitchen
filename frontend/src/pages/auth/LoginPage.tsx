import React, { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useDispatch } from 'react-redux'
import { useLoginMutation } from '../../features/auth/authApiSlice'
import { setCredentials } from '../../features/auth/authSlice'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Label } from '../../components/ui/label'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../../components/ui/card'
import { Eye, EyeOff, Lock, User, AlertCircle, Loader2, Sparkles } from 'lucide-react'
import logoImg from '../../assets/logo.png'

export const LoginPage: React.FC = () => {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const [login, { isLoading }] = useLoginMutation()
  const dispatch = useDispatch()
  const navigate = useNavigate()
  const location = useLocation()

  const from = (location.state as any)?.from?.pathname

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setErrorMessage(null)

    if (!identifier.trim() || !password) {
      setErrorMessage('Please enter both your identifier and password.')
      return
    }

    try {
      const response = await login({
        identifier: identifier.trim(),
        password,
      }).unwrap()

      dispatch(
        setCredentials({
          access_token: response.access_token,
          refresh_token: response.refresh_token,
          user: response.user,
          role: response.role,
          permissions: response.permissions,
        })
      )

      // Role-based routing
      if (from) {
        navigate(from, { replace: true })
      } else if (response.role === 'DRIVER') {
        navigate('/driver/today', { replace: true })
      } else {
        navigate('/admin/dashboard', { replace: true })
      }
    } catch (err: any) {
      console.error('Login error:', err)
      const detail = err?.data?.detail || 'Login failed. Please check your credentials.'
      setErrorMessage(detail)
    }
  }

  const fillCredentials = (userType: 'superadmin' | 'kitchenadmin' | 'driver') => {
    if (userType === 'superadmin') {
      setIdentifier('superadmin')
      setPassword('Admin@123')
    } else if (userType === 'kitchenadmin') {
      setIdentifier('kitchenadmin')
      setPassword('Kitchen@123')
    } else {
      setIdentifier('driver1')
      setPassword('Driver@123')
    }
    setErrorMessage(null)
  }

  return (
    <div className="min-h-screen flex flex-col justify-center items-center bg-stone-100 p-4 sm:p-6 relative overflow-hidden">
      {/* Background Decorative Circles */}
      <div className="absolute -top-32 -left-32 w-96 h-96 rounded-full bg-amber-500/10 blur-3xl pointer-events-none" />
      <div className="absolute -bottom-32 -right-32 w-96 h-96 rounded-full bg-emerald-600/10 blur-3xl pointer-events-none" />

      <div className="w-full max-w-md relative z-10">
        {/* Brand Header */}
        <div className="text-center mb-6">
          <div className="inline-block relative">
            <img
              src={logoImg}
              alt="Kavi's Kitchen"
              className="h-24 w-auto mx-auto object-contain drop-shadow-md hover:scale-105 transition-transform duration-200"
            />
          </div>
          <h1 className="mt-3 text-2xl sm:text-3xl font-bold tracking-tight text-stone-900 font-serif">
            Kavi's Kitchen
          </h1>
          <p className="text-sm text-stone-600 mt-1">
            Homestyle Meal Delivery & Kitchen Operations
          </p>
        </div>

        {/* Login Card */}
        <Card className="shadow-xl border-stone-200 bg-white/95 backdrop-blur">
          <CardHeader className="space-y-1 pb-4">
            <CardTitle className="text-xl font-bold text-stone-900">
              Sign In to Your Account
            </CardTitle>
            <CardDescription className="text-xs text-stone-500">
              Enter your username, registered email, or phone number to access your portal
            </CardDescription>
          </CardHeader>

          <CardContent>
            {errorMessage && (
              <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 flex items-start gap-2.5 text-red-800 text-xs sm:text-sm">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span>{errorMessage}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-1.5">
                <Label htmlFor="identifier" className="text-xs font-semibold text-stone-700">
                  Username, Email, or Phone
                </Label>
                <div className="relative">
                  <User className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input
                    id="identifier"
                    type="text"
                    placeholder="e.g. superadmin or 9876543210"
                    value={identifier}
                    onChange={(e) => setIdentifier(e.target.value)}
                    className="pl-9 text-sm focus-visible:ring-amber-500"
                    required
                  />
                </div>
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <Label htmlFor="password" className="text-xs font-semibold text-stone-700">
                    Password
                  </Label>
                </div>
                <div className="relative">
                  <Lock className="w-4 h-4 text-stone-400 absolute left-3 top-1/2 -translate-y-1/2" />
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="Enter your password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="pl-9 pr-10 text-sm focus-visible:ring-amber-500"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-stone-400 hover:text-stone-600 focus:outline-none"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2.5 rounded-lg shadow-md hover:shadow-lg transition-all"
              >
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Signing in...
                  </span>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>

            {/* Quick Demo Fill Buttons forpair-programming testing */}
            <div className="mt-6 pt-4 border-t border-stone-200">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-stone-600 mb-2">
                <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                <span>Quick Demo Accounts:</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                <button
                  type="button"
                  onClick={() => fillCredentials('superadmin')}
                  className="px-2 py-1.5 text-xs font-medium bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-md transition-colors text-center"
                >
                  Super Admin
                </button>
                <button
                  type="button"
                  onClick={() => fillCredentials('kitchenadmin')}
                  className="px-2 py-1.5 text-xs font-medium bg-emerald-50 hover:bg-emerald-100 text-emerald-900 border border-emerald-200 rounded-md transition-colors text-center"
                >
                  Kitchen Admin
                </button>
                <button
                  type="button"
                  onClick={() => fillCredentials('driver')}
                  className="px-2 py-1.5 text-xs font-medium bg-blue-50 hover:bg-blue-100 text-blue-900 border border-blue-200 rounded-md transition-colors text-center"
                >
                  Driver 1
                </button>
              </div>
            </div>
          </CardContent>

          <CardFooter className="pt-0 justify-center">
            <p className="text-[11px] text-stone-500 text-center">
              Protected by Kavi's Kitchen Role-Based Access Control
            </p>
          </CardFooter>
        </Card>
      </div>
    </div>
  )
}
