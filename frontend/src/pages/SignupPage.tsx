import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Brain, Mail, Lock, User, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { authApi } from '@/lib/api'
import { useAuthStore } from '@/store'

export default function SignupPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ username: '', email: '', password: '', full_name: '' })
  const [loading, setLoading] = useState(false)

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.signup(form)
      setAuth(data.user, data.access_token)
      toast.success('Account created! Welcome aboard')
      navigate('/dashboard')
    } catch {
      // handled by interceptor
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="organic-page flex items-center justify-center px-4 py-12">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/3 left-1/2 h-[360px] w-[620px] -translate-x-1/2 organic-blob bg-clay-500/12 blur-3xl" />
        <div className="absolute bottom-12 left-10 h-56 w-56 organic-blob-alt bg-brand-500/14 blur-3xl" />
      </div>

      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 mb-6">
            <div className="w-10 h-10 rounded-full bg-brand-500 flex items-center justify-center shadow-soft">
              <Brain className="w-5 h-5 text-brand-50" />
            </div>
            <span className="font-display font-bold text-2xl text-surface-950">AgenticRAG</span>
          </Link>
          <h1 className="font-display text-4xl font-bold text-surface-950 mb-2">Create account</h1>
          <p className="text-surface-800">Start building trustworthy AI today</p>
        </div>

        <div className="organic-card p-8">
          <form onSubmit={handleSubmit} className="space-y-4">
            {[
              { key: 'full_name', label: 'Full name', placeholder: 'Jane Smith', icon: User, type: 'text', required: false },
              { key: 'username', label: 'Username', placeholder: 'jane_smith', icon: User, type: 'text', required: true },
              { key: 'email', label: 'Email', placeholder: 'jane@example.com', icon: Mail, type: 'email', required: true },
              { key: 'password', label: 'Password', placeholder: '••••••••', icon: Lock, type: 'password', required: true },
            ].map(({ key, label, placeholder, icon: Icon, type, required }) => (
              <div key={key}>
                <label className="block text-sm text-surface-900 font-bold mb-1.5">{label}{required && <span className="text-brand-700 ml-0.5">*</span>}</label>
                <div className="relative">
                  <Icon className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-brand-600" />
                  <input
                    type={type}
                    value={form[key as keyof typeof form]}
                    onChange={set(key)}
                    required={required}
                    placeholder={placeholder}
                    minLength={key === 'password' ? 6 : undefined}
                    className="w-full organic-input rounded-full pl-11 pr-4 py-3 text-sm"
                  />
                </div>
              </div>
            ))}

            <button
              type="submit"
              disabled={loading}
              className="organic-button w-full flex items-center justify-center gap-2 mt-2"
            >
              {loading && <Loader2 className="w-4 h-4 animate-spin" />}
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="text-center text-sm text-surface-800 mt-6">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-700 font-bold hover:text-brand-900">Sign in</Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
