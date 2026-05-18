import { FileText, Globe, Brain, AlertTriangle } from 'lucide-react'
import type { AnswerSource } from '@/types'

interface Props { source: AnswerSource }

const config = {
  DOCUMENTS: { icon: FileText, label: 'From Your Documents', color: 'text-brand-700 bg-brand-500/10 border-brand-500/20' },
  WEB_SEARCH: { icon: Globe, label: 'From Web Search', color: 'text-clay-600 bg-clay-500/10 border-clay-500/20' },
  GENERAL_KNOWLEDGE: { icon: Brain, label: 'From General Knowledge', color: 'text-amber-700 bg-amber-500/10 border-amber-500/20' },
  ABSTAINED: { icon: AlertTriangle, label: 'Could Not Answer', color: 'text-red-700 bg-red-500/10 border-red-500/20' },
}

export default function SourceBadge({ source }: Props) {
  const { icon: Icon, label, color } = config[source] || config.DOCUMENTS
  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${color}`}>
      <Icon className="w-3 h-3" />
      {label}
    </div>
  )
}
