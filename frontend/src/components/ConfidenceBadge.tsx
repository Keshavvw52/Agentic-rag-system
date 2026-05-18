// ConfidenceBadge.tsx
import type { ConfidenceBreakdown } from '@/types'

interface Props {
  confidence: ConfidenceBreakdown
  size?: 'sm' | 'md' | 'lg'
}

const labelConfig = {
  HIGH: { color: 'text-brand-700 bg-brand-500/15 border-brand-500/30', dot: 'bg-brand-500' },
  MEDIUM: { color: 'text-clay-600 bg-clay-500/15 border-clay-500/30', dot: 'bg-clay-500' },
  LOW: { color: 'text-amber-700 bg-amber-500/15 border-amber-500/30', dot: 'bg-amber-500' },
  VERY_LOW: { color: 'text-red-700 bg-red-500/10 border-red-500/20', dot: 'bg-red-500' },
}

export default function ConfidenceBadge({ confidence, size = 'sm' }: Props) {
  const cfg = labelConfig[confidence.label] || labelConfig.VERY_LOW
  const pct = Math.round(confidence.final_score * 100)
  const sizeClass = size === 'lg' ? 'px-3 py-1.5 text-sm' : size === 'md' ? 'px-2.5 py-1 text-xs' : 'px-2 py-0.5 text-xs'

  return (
    <div className={`inline-flex items-center gap-1.5 rounded-full border font-semibold ${sizeClass} ${cfg.color}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${cfg.dot}`} />
      {pct}% {confidence.label.replace('_', ' ')} Confidence
    </div>
  )
}
