import { useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Loader2, Zap, Brain } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { queryApi } from '@/lib/api'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer } from 'recharts'
import type { QueryResponse, SimpleQueryResponse } from '@/types'
import ConfidenceBadge from '@/components/ConfidenceBadge'

export default function ComparisonPage() {
  const [query, setQuery] = useState('')
  const [agenticResult, setAgenticResult] = useState<QueryResponse | null>(null)
  const [simpleResult, setSimpleResult] = useState<SimpleQueryResponse | null>(null)
  const [loadingAgentic, setLoadingAgentic] = useState(false)
  const [loadingSimple, setLoadingSimple] = useState(false)

  const handleCompare = async () => {
    if (!query.trim()) return
    setAgenticResult(null)
    setSimpleResult(null)
    setLoadingAgentic(true)
    setLoadingSimple(true)

    // Run both in parallel
    Promise.all([
      queryApi.agentic(query).then(({ data }) => {
        setAgenticResult(data)
        setLoadingAgentic(false)
      }).catch(() => setLoadingAgentic(false)),
      queryApi.simple(query).then(({ data }) => {
        setSimpleResult(data)
        setLoadingSimple(false)
      }).catch(() => setLoadingSimple(false)),
    ])
  }

  const radarData = agenticResult ? [
    { metric: 'Retrieval\nRelevance', agentic: agenticResult.confidence.retrieval_relevance * 100, simple: 60 },
    { metric: 'Faithfulness', agentic: agenticResult.confidence.faithfulness * 100, simple: 50 },
    { metric: 'Coverage', agentic: agenticResult.confidence.context_coverage * 100, simple: 55 },
    { metric: 'Coherence', agentic: agenticResult.confidence.coherence * 100, simple: 65 },
    { metric: 'Confidence', agentic: agenticResult.confidence.final_score * 100, simple: 55 },
  ] : []

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="font-display text-3xl font-bold text-surface-950">Agentic vs Simple Comparison</h1>
        <p className="text-sm text-surface-800 mt-1">Run the same query through both pipelines and see the difference</p>
      </div>

      {/* Query Input */}
      <div className="flex gap-3 mb-8">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleCompare()}
          placeholder="Enter a query to compare both approaches…"
          className="flex-1 organic-input rounded-full px-4 py-3 text-sm"
        />
        <button
          onClick={handleCompare}
          disabled={loadingAgentic || loadingSimple || !query.trim()}
          className="organic-button flex items-center gap-2 px-6 py-3 text-sm"
        >
          {(loadingAgentic || loadingSimple) ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Send className="w-4 h-4" />
          )}
          Compare
        </button>
      </div>

      {/* Comparison grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Agentic */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-lg bg-gradient-to-br from-brand-500 to-violet-600 flex items-center justify-center">
              <Zap className="w-3 h-3 text-brand-50" />
            </div>
            <h2 className="font-bold text-surface-950">Agentic RAG</h2>
            <span className="text-xs text-surface-800 ml-auto">Self-correcting · Verified</span>
          </div>
          <div className="organic-card min-h-48 overflow-hidden">
            {loadingAgentic && (
              <div className="flex items-center justify-center h-48">
                <div className="text-center">
                  <Loader2 className="w-6 h-6 text-brand-400 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-surface-800">Running agentic pipeline...</p>
                </div>
              </div>
            )}
            {agenticResult && !loadingAgentic && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="p-4 border-b border-timber/60 flex items-center gap-2 flex-wrap">
                  <ConfidenceBadge confidence={agenticResult.confidence} />
                  <span className="text-xs text-surface-800">
                    {agenticResult.claims.length} claims · {agenticResult.iterations_count} iterations
                  </span>
                  {agenticResult.hallucination_score > 0 && (
                    <span className="text-xs text-amber-400">
                      {Math.round(agenticResult.hallucination_score * 100)}% hallucination
                    </span>
                  )}
                </div>
                <div className="p-4 prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{agenticResult.answer}</ReactMarkdown>
                </div>
              </motion.div>
            )}
            {!loadingAgentic && !agenticResult && (
              <div className="flex items-center justify-center h-48 text-surface-800 text-sm">
                Result will appear here
              </div>
            )}
          </div>
        </div>

        {/* Simple */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <div className="w-6 h-6 rounded-full bg-sand flex items-center justify-center">
              <Brain className="w-3 h-3 text-clay-600" />
            </div>
            <h2 className="font-bold text-surface-950">Simple RAG</h2>
            <span className="text-xs text-surface-800 ml-auto">Baseline · No verification</span>
          </div>
          <div className="organic-card min-h-48 overflow-hidden">
            {loadingSimple && (
              <div className="flex items-center justify-center h-48">
                <div className="text-center">
                  <Loader2 className="w-6 h-6 text-clay-600 animate-spin mx-auto mb-2" />
                  <p className="text-xs text-surface-800">Running simple pipeline...</p>
                </div>
              </div>
            )}
            {simpleResult && !loadingSimple && (
              <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                <div className="p-4 border-b border-timber/60 flex items-center gap-2">
                  <span className="text-xs px-2.5 py-1 rounded-full bg-sand/60 border border-timber text-surface-800">
                    No confidence score
                  </span>
                  <span className="text-xs text-surface-800">{simpleResult.chunks_used} chunks used</span>
                </div>
                <div className="p-4 prose prose-invert prose-sm max-w-none">
                  <ReactMarkdown>{simpleResult.answer}</ReactMarkdown>
                </div>
              </motion.div>
            )}
            {!loadingSimple && !simpleResult && (
              <div className="flex items-center justify-center h-48 text-surface-800 text-sm">
                Result will appear here
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Radar Chart Comparison */}
      {agenticResult && (
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="organic-card mt-6 p-6"
        >
          <h3 className="font-display text-xl font-bold text-surface-950 mb-4 text-center">Quality Comparison</h3>
          <div className="grid grid-cols-2 gap-8 items-center">
            <ResponsiveContainer width="100%" height={250}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#27272a" />
                <PolarAngleAxis dataKey="metric" tick={{ fill: '#71717a', fontSize: 11 }} />
                <Radar name="Agentic" dataKey="agentic" stroke="#0ea5e9" fill="#0ea5e9" fillOpacity={0.15} strokeWidth={2} />
                <Radar name="Simple" dataKey="simple" stroke="#52525b" fill="#52525b" fillOpacity={0.1} strokeWidth={1.5} strokeDasharray="4 2" />
              </RadarChart>
            </ResponsiveContainer>

            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <div className="w-3 h-0.5 bg-brand-500" />
                <span className="text-sm text-surface-900">Agentic RAG</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-0.5 bg-zinc-600 border-dashed" />
                <span className="text-sm text-surface-800">Simple RAG (estimated)</span>
              </div>
              <div className="mt-4 space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-surface-800">Hallucinations caught</span>
                  <span className="text-emerald-400 font-semibold">
                    {agenticResult.claims.filter(c => c.status !== 'SUPPORTED').length}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-surface-800">Self-corrections</span>
                  <span className="text-brand-400 font-semibold">{agenticResult.iterations_count}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-surface-800">Confidence</span>
                  <span className="text-surface-950 font-bold">{Math.round(agenticResult.confidence.final_score * 100)}%</span>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}
