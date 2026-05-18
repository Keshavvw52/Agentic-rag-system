import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { evaluationApi, statsApi } from '@/lib/api'
import type { Stats } from '@/types'

interface EvaluationResult {
  query_id: string
  query: string
  confidence_score: number
  hallucination_score: number
  confidence_label: string
  fallback_used: boolean
  retries?: number
  created_at: string
}

interface EvaluationResultsResponse {
  results: EvaluationResult[]
  summary: Record<string, unknown>
}

export default function EvaluationPage() {
  const [results, setResults] = useState<EvaluationResultsResponse | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      evaluationApi.results(),
      statsApi.get(),
    ]).then(([{ data: evalData }, { data: statsData }]) => {
      setResults(evalData)
      setStats(statsData)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="flex items-center justify-center h-64 text-surface-800">Loading evaluation data...</div>
  }

  const queryTypeData = stats ? Object.entries(stats.query_type_distribution).map(([k, v]) => ({
    name: k, value: v as number,
  })) : []

  const COLORS = ['#0ea5e9', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444']

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-surface-950">Evaluation Dashboard</h1>
        <p className="text-sm text-surface-800 mt-1">System performance metrics and evaluation results</p>
      </div>

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Total Queries', value: stats.total_queries, unit: '' },
            { label: 'Avg Confidence', value: Math.round(stats.avg_confidence * 100), unit: '%' },
            { label: 'Hallucination Rate', value: Math.round(stats.avg_hallucination_score * 100), unit: '%' },
            { label: 'Fallback Rate', value: Math.round(stats.fallback_rate * 100), unit: '%' },
          ].map(({ label, value, unit }) => (
            <div key={label} className="organic-card p-4">
              <p className="text-2xl font-bold font-display text-surface-950">{value}{unit}</p>
              <p className="text-xs text-surface-800 mt-1">{label}</p>
            </div>
          ))}
        </div>
      )}

      {/* Charts Row */}
      {stats && (
        <div className="grid grid-cols-2 gap-4">
          {/* Query Type Distribution */}
          <div className="organic-card p-5">
            <h3 className="text-sm font-bold text-surface-900 mb-4">Query Type Distribution</h3>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={queryTypeData} barSize={32}>
                <XAxis dataKey="name" tick={{ fill: '#71717a', fontSize: 10 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: '#71717a', fontSize: 10 }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ background: '#18181b', border: '1px solid #27272a', borderRadius: 8, fontSize: 12 }}
                  cursor={{ fill: 'rgba(255,255,255,0.03)' }}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {queryTypeData.map((_, i) => (
                    <Cell key={i} fill={COLORS[i % COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Performance Metrics */}
          <div className="organic-card p-5">
            <h3 className="text-sm font-bold text-surface-900 mb-4">Performance Metrics</h3>
            <div className="space-y-3">
              {[
                { label: 'Avg Confidence', value: stats.avg_confidence, color: 'bg-brand-500' },
                { label: 'Faithfulness (1 - hallucination)', value: 1 - stats.avg_hallucination_score, color: 'bg-emerald-500' },
                { label: 'Retry Rate', value: stats.retry_rate, color: 'bg-amber-500', invert: true },
                { label: 'Fallback Rate', value: stats.fallback_rate, color: 'bg-rose-500', invert: true },
              ].map(({ label, value, color }) => (
                <div key={label}>
                  <div className="flex justify-between mb-1">
                    <span className="text-xs text-surface-800">{label}</span>
                    <span className="text-xs text-surface-950">{Math.round(value * 100)}%</span>
                  </div>
                  <div className="h-2 bg-surface-200 rounded-full overflow-hidden">
                    <div className={`h-full ${color} rounded-full`} style={{ width: `${value * 100}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Recent Query Results */}
      {results && results.results.length > 0 && (
        <div className="organic-card overflow-hidden">
          <div className="px-5 py-3 border-b border-timber/60">
            <h3 className="text-sm font-bold text-surface-900">Recent Query Evaluations</h3>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-timber/60 text-surface-800 text-xs uppercase tracking-wider">
                  <th className="text-left px-5 py-3">Query</th>
                  <th className="px-4 py-3">Confidence</th>
                  <th className="px-4 py-3">Hallucination</th>
                  <th className="px-4 py-3">Fallback</th>
                  <th className="px-4 py-3">Retries</th>
                </tr>
              </thead>
              <tbody>
                {results.results.map((r, i) => (
                  <tr key={i} className="border-b border-timber/50 hover:bg-sand/30">
                    <td className="px-5 py-3 text-surface-900 max-w-xs truncate">{r.query}</td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs font-medium ${
                        r.confidence_score >= 0.7 ? 'text-emerald-400' :
                        r.confidence_score >= 0.5 ? 'text-amber-400' : 'text-rose-400'
                      }`}>
                        {Math.round(r.confidence_score * 100)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs ${r.hallucination_score > 0.2 ? 'text-red-700' : 'text-surface-800'}`}>
                        {Math.round(r.hallucination_score * 100)}%
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      <span className={`text-xs ${r.fallback_used ? 'text-clay-600' : 'text-surface-800'}`}>
                        {r.fallback_used ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center text-surface-800 text-xs">{r.retries ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
