import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Brain, Mail, Lock, Eye, EyeOff, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/store'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.login({ email, password })
      setAuth(data.user, data.access_token)
      toast.success(`Welcome back, ${data.user.username}!`)
      navigate('/dashboard')
    } catch {
      // error handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="organic-page flex items-center justify-center px-4 py-12">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 h-[360px] w-[620px] -translate-x-1/2 organic-blob bg-brand-500/12 blur-3xl" />
        <div className="absolute bottom-12 right-10 h-56 w-56 organic-blob-alt bg-clay-500/14 blur-3xl" />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md"
      >
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-full bg-brand-500 flex items-center justify-center shadow-soft">
              <Brain className="w-5 h-5 text-brand-50" />
            </div>
            <span className="font-display font-bold text-2xl text-surface-950">AgenticRAG</span>
          </Link>
          <h1 className="font-display text-4xl font-bold text-surface-950 mb-2">Welcome back</h1>
          <p className="text-surface-800">Sign in to your account</p>
        </div>

        <div className="organic-card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-sm text-surface-900 font-bold mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-600" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  placeholder="you@example.com"
                  className="w-full organic-input rounded-full pl-11 pr-4 py-3 text-sm"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm text-surface-900 font-bold mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-600" />
                <input
                  type={showPass ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  required
                  placeholder="••••••••"
                  className="w-full organic-input rounded-full pl-11 pr-11 py-3 text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-surface-800 hover:text-surface-950"
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="organic-button w-full flex items-center justify-center gap-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="text-center text-sm text-surface-800 mt-6">
            Don't have an account?{' '}
            <Link to="/signup" className="text-brand-700 font-bold hover:text-brand-900">Create one</Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
