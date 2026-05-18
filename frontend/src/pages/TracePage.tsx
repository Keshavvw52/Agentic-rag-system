import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Clock, CheckCircle, AlertCircle, RefreshCw,
  GitBranch, Shield, BarChart3, Zap, ChevronDown, ChevronRight
} from 'lucide-react'
import { queryApi } from '@/lib/api'
import type { Trace, TraceStep } from '@/types'

const stepConfig: Record<string, { icon: typeof Zap; color: string; bg: string }> = {
  classify_query:    { icon: GitBranch, color: 'text-violet-400', bg: 'bg-violet-500/15 border-violet-500/30' },
  retrieve_documents:{ icon: Zap,       color: 'text-brand-400',  bg: 'bg-brand-500/15 border-brand-500/30'  },
  evaluate_retrieval:{ icon: CheckCircle,color:'text-blue-400',   bg: 'bg-blue-500/15 border-blue-500/30'    },
  retry_retrieval:   { icon: RefreshCw,  color: 'text-amber-400', bg: 'bg-amber-500/15 border-amber-500/30'  },
  fallback_handler:  { icon: AlertCircle,color:'text-orange-400', bg: 'bg-orange-500/15 border-orange-500/30'},
  generate_answer:   { icon: Zap,        color: 'text-emerald-400',bg:'bg-emerald-500/15 border-emerald-500/30'},
  hallucination_check:{icon: Shield,     color: 'text-rose-400',  bg: 'bg-rose-500/15 border-rose-500/30'    },
  regenerate_answer: { icon: RefreshCw,  color: 'text-amber-400', bg: 'bg-amber-500/15 border-amber-500/30'  },
  confidence_scoring:{ icon: BarChart3,  color: 'text-purple-400',bg: 'bg-purple-500/15 border-purple-500/30'},
  finalize_response: { icon: CheckCircle,color: 'text-emerald-400',bg:'bg-emerald-500/15 border-emerald-500/30'},
}

function TraceCard({ step, index }: { step: TraceStep; index: number }) {
  const [expanded, setExpanded] = useState(false)
  const cfg = stepConfig[step.step] || { icon: Zap, color: 'text-surface-800', bg: 'bg-sand/40 border-timber/60' }
  const Icon = cfg.icon

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay: index * 0.06 }}
      className="relative flex gap-4"
    >
      {/* Timeline connector */}
      <div className="flex flex-col items-center">
        <div className={`w-9 h-9 rounded-xl border flex items-center justify-center flex-shrink-0 ${cfg.bg}`}>
          <Icon className={`w-4 h-4 ${cfg.color}`} />
        </div>
        <div className="w-px flex-1 bg-timber/70 my-1" />
      </div>

      {/* Card */}
      <div className="flex-1 pb-4">
        <div
          className="organic-panel overflow-hidden cursor-pointer transition-all hover:-translate-y-0.5"
          onClick={() => setExpanded(!expanded)}
        >
          <div className="flex items-center justify-between px-4 py-3">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-mono text-surface-800">{String(index + 1).padStart(2, '0')}</span>
                <span className="text-sm font-bold text-surface-950 capitalize">
                  {step.step.replace(/_/g, ' ')}
                </span>
              </div>
              <p className="text-xs text-surface-800 mt-0.5">{step.decision}</p>
            </div>
            <div className="flex items-center gap-3 ml-4 flex-shrink-0">
              <div className="flex items-center gap-1 text-xs text-surface-800">
                <Clock className="w-3 h-3" />
                {step.duration_ms.toFixed(0)}ms
              </div>
              {expanded ? (
                <ChevronDown className="w-4 h-4 text-surface-800" />
              ) : (
                <ChevronRight className="w-4 h-4 text-surface-800" />
              )}
            </div>
          </div>

          {expanded && (
            <div className="border-t border-timber/60 px-4 py-3 space-y-3">
              <div>
                <p className="text-xs text-surface-800 mb-1">Reasoning</p>
                <p className="text-sm text-surface-900 leading-relaxed">{step.reasoning}</p>
              </div>

              {Object.keys(step.data).length > 0 && (
                <div>
                  <p className="text-xs text-surface-800 mb-2">Data</p>
                  <div className="bg-surface-200/70 rounded-2xl p-3 font-mono text-xs text-surface-900 overflow-auto max-h-48">
                    {JSON.stringify(step.data, null, 2)}
                  </div>
                </div>
              )}

              <div className="flex items-center gap-2 text-xs text-surface-800">
                <Clock className="w-3 h-3" />
                {new Date(step.timestamp).toLocaleTimeString()}
              </div>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

export default function TracePage() {
  const { queryId } = useParams<{ queryId: string }>()
  const navigate = useNavigate()
  const [trace, setTrace] = useState<Trace | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!queryId) return
    queryApi.trace(queryId).then(({ data }) => {
      setTrace(data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [queryId])

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center gap-3 mb-8">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-full hover:bg-sand/40 text-surface-800 hover:text-surface-950 transition-all"
        >
          <ArrowLeft className="w-4 h-4" />
        </button>
        <div>
          <h1 className="font-display text-3xl font-bold text-surface-950">Decision Trace</h1>
          <p className="text-sm text-surface-800">Full agent reasoning log</p>
        </div>
      </div>

      {loading && (
        <div className="text-center py-16 text-surface-800">Loading trace...</div>
      )}

      {!loading && !trace && (
        <div className="text-center py-16 text-surface-800">Trace not found</div>
      )}

      {trace && (
        <div>
          {/* Summary */}
          <div className="grid grid-cols-3 gap-3 mb-8">
            <div className="organic-card p-4 text-center">
              <p className="text-2xl font-bold font-display text-surface-950">{trace.steps.length}</p>
              <p className="text-xs text-surface-800 mt-0.5">Agent steps</p>
            </div>
            <div className="organic-card p-4 text-center">
              <p className="text-2xl font-bold font-display text-surface-950">{trace.iterations.length}</p>
              <p className="text-xs text-surface-800 mt-0.5">Iterations</p>
            </div>
            <div className="organic-card p-4 text-center">
              <p className="text-2xl font-bold font-display text-surface-950">{trace.claims.length}</p>
              <p className="text-xs text-surface-800 mt-0.5">Claims verified</p>
            </div>
          </div>

          {/* Timeline */}
          <div>
            {trace.steps.map((step, i) => (
              <TraceCard key={i} step={step} index={i} />
            ))}
          </div>

          {/* Iteration History */}
          {trace.iterations.length > 1 && (
            <div className="mt-8">
              <h2 className="font-display text-xl font-bold text-surface-950 mb-4">Refinement Iterations</h2>
              <div className="space-y-3">
                {trace.iterations.map((iter) => (
                  <div key={iter.iteration} className="organic-panel p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-bold text-surface-950">Iteration {iter.iteration}</span>
                      <div className="flex items-center gap-3 text-xs">
                        <span className="text-surface-800">
                          Hallucination: {Math.round(iter.hallucination_score * 100)}%
                        </span>
                        <span className="text-surface-800">
                          Confidence: {Math.round(iter.confidence_score * 100)}%
                        </span>
                      </div>
                    </div>
                    <p className="text-xs text-surface-800 italic">Query: {iter.query_used}</p>
                    <p className="text-xs text-surface-800 mt-1">{iter.answer_preview}...</p>
                    {iter.improvements.length > 0 && (
                      <div className="mt-2 flex flex-wrap gap-1">
                        {iter.improvements.map((imp, j) => (
                          <span key={j} className="text-xs px-2 py-0.5 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-full">
                            {imp}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
