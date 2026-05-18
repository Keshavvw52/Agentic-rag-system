import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Save, Loader2 } from 'lucide-react'
import toast from 'react-hot-toast'
import { configApi } from '@/lib/api'

const STRATEGIES = ['HYBRID_RERANK', 'MULTI_QUERY', 'SECTION_BASED', 'CONVERSATIONAL', 'FALLBACK']

function Select({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="organic-input rounded-full px-3 py-2 text-sm w-full"
    >
      {STRATEGIES.map(s => <option key={s} value={s} className="bg-zinc-900">{s.replace('_', ' ')}</option>)}
    </select>
  )
}

function SliderField({ label, value, onChange, min, max, step, format }: {
  label: string; value: number; onChange: (v: number) => void;
  min: number; max: number; step: number; format?: (v: number) => string
}) {
  return (
    <div>
      <div className="flex justify-between mb-1.5">
        <label className="text-sm text-surface-900 font-bold">{label}</label>
        <span className="text-sm text-brand-400 font-mono">{format ? format(value) : value}</span>
      </div>
      <input
        type="range"
        min={min} max={max} step={step}
        value={value}
        onChange={e => onChange(parseFloat(e.target.value))}
        className="w-full accent-brand-500"
      />
    </div>
  )
}

export default function SettingsPage() {
  const [routing, setRouting] = useState({
    factual_strategy: 'HYBRID_RERANK',
    analytical_strategy: 'MULTI_QUERY',
    summarization_strategy: 'SECTION_BASED',
    conversational_strategy: 'CONVERSATIONAL',
    routing_confidence_min: 0.70,
  })
  const [thresholds, setThresholds] = useState({
    hallucination_threshold: 0.20,
    max_retries: 3,
    max_iterations: 3,
    enable_web_search: true,
    enable_llm_knowledge: true,
  })
  const [savingRouting, setSavingRouting] = useState(false)
  const [savingThresholds, setSavingThresholds] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    configApi.getRouting().then(({ data }) => {
      if (data && Object.keys(data).length) setRouting(prev => ({ ...prev, ...data }))
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  const saveRouting = async () => {
    setSavingRouting(true)
    try {
      await configApi.updateRouting(routing)
      toast.success('Routing configuration saved')
    } finally { setSavingRouting(false) }
  }

  const saveThresholds = async () => {
    setSavingThresholds(true)
    try {
      await configApi.updateThresholds(thresholds)
      toast.success('Threshold configuration saved')
    } finally { setSavingThresholds(false) }
  }

  if (loading) return <div className="flex items-center justify-center h-64 text-surface-800">Loading settings...</div>

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="font-display text-3xl font-bold text-surface-950">Configuration</h1>
        <p className="text-sm text-surface-800 mt-1">Customize routing rules and quality thresholds</p>
      </div>

      {/* Routing Config */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} className="organic-card p-6">
        <h2 className="font-display text-xl font-bold text-surface-950 mb-5">Query to Strategy Routing</h2>
        <div className="space-y-4">
          {[
            { key: 'factual_strategy', label: 'Factual queries' },
            { key: 'analytical_strategy', label: 'Analytical queries' },
            { key: 'summarization_strategy', label: 'Summarization queries' },
            { key: 'conversational_strategy', label: 'Conversational queries' },
          ].map(({ key, label }) => (
            <div key={key} className="flex items-center gap-4">
              <label className="text-sm text-surface-800 w-40 flex-shrink-0">{label}</label>
              <Select
                value={routing[key as keyof typeof routing] as string}
                onChange={v => setRouting(r => ({ ...r, [key]: v }))}
              />
            </div>
          ))}
          <SliderField
            label="Minimum routing confidence"
            value={routing.routing_confidence_min}
            onChange={v => setRouting(r => ({ ...r, routing_confidence_min: v }))}
            min={0.3} max={1.0} step={0.05}
            format={v => `${Math.round(v * 100)}%`}
          />
        </div>
        <button
          onClick={saveRouting}
          disabled={savingRouting}
          className="organic-button mt-5 flex items-center gap-2 px-5 py-2.5 text-sm"
        >
          {savingRouting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Routing
        </button>
      </motion.div>

      {/* Threshold Config */}
      <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="organic-card p-6">
        <h2 className="font-display text-xl font-bold text-surface-950 mb-5">Quality Thresholds</h2>
        <div className="space-y-5">
          <SliderField
            label="Hallucination detection threshold"
            value={thresholds.hallucination_threshold}
            onChange={v => setThresholds(t => ({ ...t, hallucination_threshold: v }))}
            min={0.0} max={0.5} step={0.05}
            format={v => `${Math.round(v * 100)}% (re-generate if above)`}
          />
          <div className="flex items-center gap-4">
            <label className="text-sm text-surface-800 w-40">Max retries</label>
            <input
              type="number" min={1} max={5}
              value={thresholds.max_retries}
              onChange={e => setThresholds(t => ({ ...t, max_retries: parseInt(e.target.value) }))}
              className="w-24 organic-input rounded-full px-3 py-2 text-sm"
            />
          </div>
          <div className="flex items-center gap-4">
            <label className="text-sm text-surface-800 w-40">Max iterations</label>
            <input
              type="number" min={1} max={5}
              value={thresholds.max_iterations}
              onChange={e => setThresholds(t => ({ ...t, max_iterations: parseInt(e.target.value) }))}
              className="w-24 organic-input rounded-full px-3 py-2 text-sm"
            />
          </div>
          <div className="space-y-3">
            {[
              { key: 'enable_web_search', label: 'Enable web search fallback', desc: 'When document retrieval fails, search the web' },
              { key: 'enable_llm_knowledge', label: 'Enable LLM knowledge fallback', desc: 'Use general AI knowledge as last resort' },
            ].map(({ key, label, desc }) => (
              <div key={key} className="flex items-start gap-3">
                <div
                  className={`w-10 h-6 rounded-full relative cursor-pointer flex-shrink-0 transition-colors ${thresholds[key as keyof typeof thresholds] ? 'bg-brand-500' : 'bg-zinc-700'}`}
                  onClick={() => setThresholds(t => ({ ...t, [key]: !t[key as keyof typeof t] }))}
                >
                  <div className={`w-4 h-4 bg-white rounded-full absolute top-1 transition-all ${thresholds[key as keyof typeof thresholds] ? 'left-5' : 'left-1'}`} />
                </div>
                <div>
                  <p className="text-sm text-surface-900 font-bold">{label}</p>
                  <p className="text-xs text-surface-800">{desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
        <button
          onClick={saveThresholds}
          disabled={savingThresholds}
          className="organic-button mt-5 flex items-center gap-2 px-5 py-2.5 text-sm"
        >
          {savingThresholds ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
          Save Thresholds
        </button>
      </motion.div>
    </div>
  )
}
