import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import {
  Brain, MessageSquare, BarChart3,
  Settings, LogOut, Layers
} from 'lucide-react'
import { useAuthStore } from '@/store'
import toast from 'react-hot-toast'

const navItems = [
  { to: '/dashboard', label: 'Query', icon: MessageSquare, end: true },
  { to: '/dashboard/compare', label: 'Comparison', icon: Layers },
  { to: '/dashboard/evaluation', label: 'Evaluation', icon: BarChart3 },
  { to: '/dashboard/settings', label: 'Settings', icon: Settings },
]

export default function DashboardLayout() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    toast.success('Signed out')
    navigate('/')
  }

  return (
    <div className="organic-page flex font-sans">
      <div className="pointer-events-none absolute -left-24 top-24 h-72 w-72 organic-blob bg-brand-500/10 blur-3xl" />
      <div className="pointer-events-none absolute bottom-10 right-10 h-80 w-80 organic-blob-alt bg-clay-500/10 blur-3xl" />
      {/* Sidebar */}
      <aside className="relative z-10 m-4 mr-0 w-64 flex-shrink-0 rounded-[2rem] border border-timber/60 bg-white/60 shadow-soft backdrop-blur-md flex flex-col">
        {/* Logo */}
        <div className="p-5 border-b border-timber/60">
          <NavLink to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-full bg-brand-500 flex items-center justify-center shadow-soft">
              <Brain className="w-5 h-5 text-brand-50" />
            </div>
            <span className="font-display font-bold text-xl text-surface-950">AgenticRAG</span>
          </NavLink>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-0.5">
          {navItems.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition-all ${
                  isActive
                    ? 'bg-brand-500/15 text-brand-700 font-bold shadow-soft'
                    : 'text-surface-800 hover:text-surface-950 hover:bg-sand/40'
                }`
              }
            >
              <Icon className="w-4 h-4 flex-shrink-0" />
              {label}
            </NavLink>
          ))}
        </nav>

        {/* User */}
        <div className="p-3 border-t border-timber/60">
          <div className="flex items-center gap-3 px-3 py-2.5 mb-1">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-clay-500 to-brand-500 flex items-center justify-center text-xs font-bold text-white shadow-soft">
              {user?.username?.[0]?.toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm text-surface-950 truncate font-bold">{user?.username}</p>
              <p className="text-xs text-surface-800 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-3 px-3 py-2.5 rounded-full text-sm text-surface-800 hover:text-red-700 hover:bg-red-500/10 transition-all w-full"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="relative z-10 flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  )
}
