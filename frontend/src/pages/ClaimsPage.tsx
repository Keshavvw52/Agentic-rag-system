import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowLeft, CheckCircle, XCircle, AlertCircle } from 'lucide-react'
import { queryApi } from '@/lib/api'
import type { ClaimResult } from '@/types'

const statusConfig = {
  SUPPORTED: {
    icon: CheckCircle,
    color: 'text-emerald-400',
    bg: 'bg-emerald-500/10 border-emerald-500/20',
    label: 'Supported',
    badge: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  },
  NOT_SUPPORTED: {
    icon: AlertCircle,
    color: 'text-amber-400',
    bg: 'bg-amber-500/10 border-amber-500/20',
    label: 'Not Supported',
    badge: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  },
  CONTRADICTED: {
    icon: XCircle,
    color: 'text-rose-400',
    bg: 'bg-rose-500/10 border-rose-500/20',
    label: 'Contradicted',
    badge: 'text-rose-400 bg-rose-500/10 border-rose-500/20',
  },
}

export default function ClaimsPage() {
  const { queryId } = useParams<{ queryId: string }>()
  const navigate = useNavigate()
  const [claims, setClaims] = useState<ClaimResult[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('ALL')

  useEffect(() => {
    if (!queryId) return
    queryApi.claims(queryId).then(({ data }) => {
      setClaims(data.claims)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [queryId])

  const filtered = filter === 'ALL' ? claims : claims.filter(c => c.status === filter)

  const supported = claims.filter(c => c.status === 'SUPPORTED').length
  const unsupported = claims.filter(c => c.status === 'NOT_SUPPORTED').length
  const contradicted = claims.filter(c => c.status === 'CONTRADICTED').length

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-8">
        <button onClick={() => navigate(-1)} className="p-2 rounded-full hover:bg-sand/40 text-surface-800 hover:text-surface-950 transition-all">
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="font-display text-3xl font-bold text-surface-950">Claim Verification</h1>
          <p className="text-sm text-surface-800">Every factual claim verified against retrieved context</p>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-3 gap-3 mb-6">
        {[
          { label: 'Supported', count: supported, color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20' },
          { label: 'Not Supported', count: unsupported, color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/20' },
          { label: 'Contradicted', count: contradicted, color: 'text-rose-400', bg: 'bg-rose-500/10 border-rose-500/20' },
        ].map(({ label, count, color, bg }) => (
          <div key={label} className={`border rounded-xl p-4 text-center ${bg}`}>
            <p className={`text-2xl font-bold font-display ${color}`}>{count}</p>
            <p className="text-xs text-surface-800 mt-0.5">{label}</p>
          </div>
        ))}
      </div>

      {/* Summary bar */}
      {claims.length > 0 && (
        <div className="flex items-center gap-1 h-2 rounded-full overflow-hidden mb-6">
          <div className="bg-emerald-500 h-full" style={{ width: `${(supported / claims.length) * 100}%` }} />
          <div className="bg-amber-500 h-full" style={{ width: `${(unsupported / claims.length) * 100}%` }} />
          <div className="bg-rose-500 h-full" style={{ width: `${(contradicted / claims.length) * 100}%` }} />
        </div>
      )}

      {/* Filter tabs */}
      <div className="flex items-center gap-2 mb-4">
        {['ALL', 'SUPPORTED', 'NOT_SUPPORTED', 'CONTRADICTED'].map(f => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`text-xs px-3 py-1.5 rounded-lg border transition-all ${
              filter === f
                ? 'bg-brand-500/15 border-brand-500/25 text-brand-700'
                : 'bg-white/50 border-timber/60 text-surface-800 hover:text-surface-950'
            }`}
          >
            {f.replace('_', ' ')} {f === 'ALL' ? `(${claims.length})` : ''}
          </button>
        ))}
      </div>

      {loading && <div className="text-center py-16 text-surface-800">Loading claims...</div>}

      {!loading && claims.length === 0 && (
        <div className="text-center py-16 text-surface-800">No claims extracted for this query</div>
      )}

      {/* Claims list */}
      <div className="space-y-3">
        {filtered.map((claim, i) => {
          const cfg = statusConfig[claim.status] || statusConfig.NOT_SUPPORTED
          const Icon = cfg.icon

          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.04 }}
              className={`border rounded-xl p-4 ${cfg.bg}`}
            >
              <div className="flex items-start gap-3">
                <Icon className={`w-4 h-4 ${cfg.color} flex-shrink-0 mt-0.5`} />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1.5">
                    <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${cfg.badge}`}>
                      {cfg.label}
                    </span>
                    <span className="text-xs text-zinc-600">
                      {Math.round(claim.confidence * 100)}% confidence
                    </span>
                  </div>
                  <p className="text-sm text-surface-900 leading-relaxed">{claim.claim}</p>
                  {claim.supporting_chunk && (
                    <div className="mt-2 p-2.5 bg-white/50 rounded-2xl border border-timber/60">
                      <p className="text-xs text-surface-800 mb-1">Supporting evidence</p>
                      <p className="text-xs text-surface-800 italic">"{claim.supporting_chunk}"</p>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
