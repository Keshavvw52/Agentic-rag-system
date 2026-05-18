import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from '@/store'
import HomePage from '@/pages/HomePage'
import LoginPage from '@/pages/LoginPage'
import SignupPage from '@/pages/SignupPage'
import DashboardLayout from '@/pages/DashboardLayout'
import QueryPage from '@/pages/QueryPage'
import TracePage from '@/pages/TracePage'
import ClaimsPage from '@/pages/ClaimsPage'
import ComparisonPage from '@/pages/ComparisonPage'
import EvaluationPage from '@/pages/EvaluationPage'
import SettingsPage from '@/pages/SettingsPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

function PublicRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <Navigate to="/dashboard" replace /> : <>{children}</>
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#FEFEFA',
            color: '#2C2C24',
            border: '1px solid rgba(222,216,207,0.8)',
            borderRadius: '24px',
            boxShadow: '0 10px 40px -10px rgba(193, 140, 93, 0.2)',
            fontFamily: 'Nunito, sans-serif',
          },
        }}
      />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/signup" element={<PublicRoute><SignupPage /></PublicRoute>} />
        <Route
          path="/dashboard"
          element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}
        >
          <Route index element={<QueryPage />} />
          <Route path="query/:queryId/trace" element={<TracePage />} />
          <Route path="query/:queryId/claims" element={<ClaimsPage />} />
          <Route path="compare" element={<ComparisonPage />} />
          <Route path="evaluation" element={<EvaluationPage />} />
          <Route path="settings" element={<SettingsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
