import { useState } from 'react'
import { ChevronDown, ChevronUp } from 'lucide-react'
import type { ConfidenceBreakdown } from '@/types'

interface Props { breakdown: ConfidenceBreakdown }

const factors = [
  { key: 'retrieval_relevance', label: 'Retrieval Relevance', weight: '30%', desc: 'How relevant the retrieved chunks are' },
  { key: 'faithfulness', label: 'Faithfulness', weight: '30%', desc: 'Inverse of hallucination score' },
  { key: 'context_coverage', label: 'Context Coverage', weight: '20%', desc: 'How fully the context answers the query' },
  { key: 'coherence', label: 'Answer Coherence', weight: '20%', desc: 'How well-structured and direct the answer is' },
] as const

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100)
  const color = pct >= 80 ? 'bg-brand-500' : pct >= 60 ? 'bg-clay-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500'
  return (
    <div className="flex items-center gap-2 flex-1">
      <div className="flex-1 h-2 bg-surface-200 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-surface-800 w-8 text-right">{pct}%</span>
    </div>
  )
}

export default function ConfidenceBreakdownPanel({ breakdown }: Props) {
  const [open, setOpen] = useState(false)

  return (
    <div className="organic-panel overflow-hidden">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center justify-between px-4 py-3 hover:bg-sand/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-surface-900 uppercase tracking-wider">Confidence Breakdown</span>
          <span className="text-xs text-surface-800">(4-factor weighted score)</span>
        </div>
        {open ? <ChevronUp className="w-4 h-4 text-surface-800" /> : <ChevronDown className="w-4 h-4 text-surface-800" />}
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-timber/60 pt-3">
          {factors.map(({ key, label, weight, desc }) => (
            <div key={key}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-surface-950 font-medium">{label}</span>
                  <span className="text-xs text-surface-800">({weight})</span>
                </div>
              </div>
              <ScoreBar score={breakdown[key]} />
              <p className="text-xs text-surface-800 mt-0.5">{desc}</p>
            </div>
          ))}

          <div className="pt-2 border-t border-timber/60 flex items-center justify-between">
            <span className="text-xs font-semibold text-surface-900">Final Score</span>
            <span className="text-sm font-bold text-surface-950">
              {Math.round(breakdown.final_score * 100)}%
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
