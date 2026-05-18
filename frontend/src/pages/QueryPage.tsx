import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Send, Upload, Loader2, FileText, Trash2,
  Zap, ChevronRight, AlertCircle, CheckCircle2
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import toast from 'react-hot-toast'
import { AxiosError } from 'axios'
import { queryApi, documentsApi } from '@/lib/api'
import { useQueryStore, useDashboardStore } from '@/store'
import ConfidenceBadge from '@/components/ConfidenceBadge'
import ConfidenceBreakdownPanel from '@/components/ConfidenceBreakdownPanel'
import SourceBadge from '@/components/SourceBadge'

export default function QueryPage() {
  const navigate = useNavigate()
  const {
    currentQuery, agenticResult, isLoading, error,
    setQuery, setAgenticResult, setLoading, setError, reset
  } = useQueryStore()
  const { documents, setDocuments, addDocument, removeDocument } = useDashboardStore()

  const [inputValue, setInputValue] = useState(currentQuery)
  const [isDragging, setIsDragging] = useState(false)
  const [uploadingFile, setUploadingFile] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Load documents on mount
  useEffect(() => {
    documentsApi.list().then(({ data }) => setDocuments(data.documents))
  }, [setDocuments])

  const handleQuery = async () => {
    const q = inputValue.trim()
    if (!q) return
    if (documents.length === 0) {
      toast.error('Please upload at least one document first')
      return
    }

    reset()
    setQuery(q)
    setInputValue('')
    setLoading(true)
    setError(null)

    try {
      const { data } = await queryApi.agentic(q)
      setAgenticResult(data)
    } catch (e) {
      const detail = e instanceof AxiosError ? e.response?.data?.detail : undefined
      setError(typeof detail === 'string' ? detail : 'Query failed')
    } finally {
      setLoading(false)
    }
  }

  const handleFileUpload = async (file: File) => {
    setUploadingFile(file.name)
    try {
      const { data } = await documentsApi.upload(file)
      addDocument(data)
      toast.success(`"${file.name}" uploaded and indexed!`)
    } catch {
      // handled by interceptor
    } finally {
      setUploadingFile(null)
    }
  }

  const handleDeleteDoc = async (id: string, name: string) => {
    try {
      await documentsApi.delete(id)
      removeDocument(id)
      toast.success(`"${name}" deleted`)
    } catch {
      toast.error(`Failed to delete "${name}"`)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFileUpload(file)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleQuery()
    }
  }

  return (
    <div className="flex h-screen overflow-hidden p-4 gap-4">
      {/* Left Panel: Documents */}
      <div className="w-72 flex-shrink-0 organic-card flex flex-col overflow-hidden">
        <div className="p-5 border-b border-timber/60">
          <h2 className="text-sm font-bold text-surface-950">Documents</h2>
          <p className="text-xs text-surface-800 mt-0.5">Your knowledge base</p>
        </div>

        {/* Upload Area */}
        <div className="p-3">
          <div
            onDragOver={e => { e.preventDefault(); setIsDragging(true) }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-[1.75rem] p-4 text-center cursor-pointer transition-all duration-300 ${
              isDragging
                ? 'border-brand-500 bg-brand-500/10 scale-[1.02]'
                : 'border-timber hover:border-clay-500/70 hover:bg-sand/30'
            }`}
          >
            <Upload className="w-5 h-5 text-brand-600 mx-auto mb-2" />
            <p className="text-xs text-surface-900 font-semibold">Drop PDF, TXT, DOCX</p>
            <p className="text-xs text-surface-800 mt-0.5">or click to browse</p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.txt,.docx,.doc,.md"
            className="hidden"
            onChange={e => e.target.files?.[0] && handleFileUpload(e.target.files[0])}
          />
        </div>

        {/* Upload progress */}
        {uploadingFile && (
          <div className="mx-3 mb-2 px-3 py-2 bg-brand-500/10 border border-brand-500/20 rounded-full flex items-center gap-2">
            <Loader2 className="w-3 h-3 text-brand-400 animate-spin flex-shrink-0" />
            <span className="text-xs text-brand-700 truncate">Indexing {uploadingFile}...</span>
          </div>
        )}

        {/* Document list */}
        <div className="flex-1 overflow-y-auto p-3 space-y-1.5">
          {documents.length === 0 ? (
            <p className="text-xs text-surface-800 text-center py-8">No documents yet</p>
          ) : (
            documents.map(doc => (
              <div
                key={doc.id}
                className="group flex items-start gap-2 p-2.5 rounded-2xl hover:bg-sand/40 transition-all"
              >
                <FileText className="w-4 h-4 text-brand-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-surface-950 truncate font-bold">{doc.filename}</p>
                  <p className="text-xs text-surface-800">{doc.chunk_count} chunks</p>
                </div>
                <button
                  onClick={() => handleDeleteDoc(doc.id, doc.filename)}
                  className="opacity-0 group-hover:opacity-100 text-surface-800 hover:text-red-700 transition-all flex-shrink-0"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Main Query Area */}
      <div className="flex-1 flex flex-col overflow-hidden organic-panel">
        {/* Header */}
        <div className="p-6 border-b border-timber/60 flex items-center justify-between">
          <div>
            <h1 className="font-display text-2xl font-bold text-surface-950">Agentic Query</h1>
            <p className="text-xs text-surface-800">Auto-routing · CRAG · Hallucination detection · Confidence scoring</p>
          </div>
          {agenticResult && (
            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate(`/dashboard/query/${agenticResult.query_id}/trace`)}
                className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-brand-500/10 hover:bg-brand-500/15 border border-brand-500/20 rounded-full text-brand-700 transition-all"
              >
                <Zap className="w-3 h-3" /> Decision Trace
              </button>
              <button
                onClick={() => navigate(`/dashboard/query/${agenticResult.query_id}/claims`)}
                className="text-xs flex items-center gap-1.5 px-3 py-1.5 bg-clay-500/10 hover:bg-clay-500/15 border border-clay-500/20 rounded-full text-clay-600 transition-all"
              >
                <CheckCircle2 className="w-3 h-3" /> Claims
              </button>
            </div>
          )}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-5 space-y-5">
          {/* Empty state */}
          {!agenticResult && !isLoading && !error && (
            <div className="h-full flex items-center justify-center">
              <div className="text-center max-w-md">
                <div className="w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/20 flex items-center justify-center mx-auto mb-4">
                  <Zap className="w-8 h-8 text-brand-600" />
                </div>
                <h3 className="font-display text-2xl font-bold text-surface-950 mb-2">Ask anything</h3>
                <p className="text-surface-800 text-sm">
                  Upload documents above, then ask a question. The agent will classify your query,
                  route it optimally, verify the answer, and score its confidence.
                </p>
                <div className="mt-6 flex flex-wrap gap-2 justify-center">
                  {['Summarize the key findings', 'What are the revenue numbers?', 'Compare Q1 vs Q2 growth'].map(q => (
                    <button
                      key={q}
                      onClick={() => setInputValue(q)}
                      className="text-xs px-3 py-1.5 bg-sand/40 hover:bg-sand border border-timber/60 rounded-full text-surface-900 transition-all"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Loading state */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center py-16"
            >
              <div className="relative w-16 h-16 mb-4">
                <div className="absolute inset-0 rounded-full border-2 border-brand-500/20" />
                <div className="absolute inset-0 rounded-full border-t-2 border-brand-500 animate-spin" />
                <Zap className="absolute inset-0 m-auto w-6 h-6 text-brand-400" />
              </div>
              <p className="text-surface-900 text-sm font-bold">Agent is reasoning...</p>
              <div className="mt-3 space-y-1.5">
                {['Classifying query…', 'Retrieving documents…', 'Evaluating quality…', 'Checking for hallucinations…'].map((msg, i) => (
                  <motion.p
                    key={msg}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.8 }}
                    className="text-xs text-surface-800 text-center"
                  >
                    {msg}
                  </motion.p>
                ))}
              </div>
            </motion.div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-[1.5rem]">
              <AlertCircle className="w-4 h-4 text-red-700 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-bold text-red-800">Query failed</p>
                <p className="text-xs text-red-700/80 mt-0.5">{error}</p>
              </div>
            </div>
          )}

          {/* Result */}
          {agenticResult && !isLoading && (
            <AnimatePresence>
              <motion.div
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                className="space-y-4"
              >
                {/* Query badge */}
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs px-2.5 py-1 bg-violet-500/15 border border-violet-500/20 text-violet-300 rounded-full">
                    {agenticResult.query_type}
                  </span>
                  <span className="text-xs px-2.5 py-1 bg-sand/60 border border-timber/60 text-surface-900 rounded-full">
                    {agenticResult.retrieval_strategy?.replace('_', ' ')}
                  </span>
                  {agenticResult.fallback_used && (
                    <span className="text-xs px-2.5 py-1 bg-amber-500/15 border border-amber-500/20 text-amber-300 rounded-full">
                      Fallback used
                    </span>
                  )}
                  <span className="text-xs text-surface-800 ml-auto">
                    {Math.round(agenticResult.total_duration_ms)}ms
                  </span>
                </div>

                {/* Answer card */}
                <div className="organic-card overflow-hidden">
                  <div className="flex items-center justify-between px-5 py-3 border-b border-timber/60">
                    <div className="flex items-center gap-3">
                      <ConfidenceBadge confidence={agenticResult.confidence} />
                      <SourceBadge source={agenticResult.answer_source} />
                    </div>
                    <span className="text-xs text-surface-800">
                      {agenticResult.claims.length} claims verified
                      {agenticResult.hallucination_score > 0 && (
                        <span className="text-amber-400 ml-2">
                          · {Math.round(agenticResult.hallucination_score * 100)}% hallucination
                        </span>
                      )}
                    </span>
                  </div>

                  <div className="p-5 prose prose-invert prose-sm max-w-none">
                    <ReactMarkdown>{agenticResult.answer}</ReactMarkdown>
                  </div>
                </div>

                {/* Confidence Breakdown */}
                <ConfidenceBreakdownPanel breakdown={agenticResult.confidence} />

                {/* Claims preview */}
                {agenticResult.claims.length > 0 && (
                  <div className="organic-panel p-4">
                    <div className="flex items-center justify-between mb-3">
                        <h3 className="text-xs font-semibold text-surface-900 uppercase tracking-wider">
                        Claim Verification ({agenticResult.claims.length})
                      </h3>
                      <button
                        onClick={() => navigate(`/dashboard/query/${agenticResult.query_id}/claims`)}
                        className="text-xs text-brand-700 hover:text-brand-900 flex items-center gap-1"
                      >
                        View all <ChevronRight className="w-3 h-3" />
                      </button>
                    </div>
                    <div className="space-y-2">
                      {agenticResult.claims.slice(0, 3).map((claim, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <span className={`flex-shrink-0 w-4 h-4 rounded-full flex items-center justify-center mt-0.5 text-[10px] font-bold ${
                            claim.status === 'SUPPORTED' ? 'bg-emerald-500/20 text-emerald-400' :
                            claim.status === 'CONTRADICTED' ? 'bg-rose-500/20 text-rose-400' :
                            'bg-amber-500/20 text-amber-400'
                          }`}>
                            {claim.status === 'SUPPORTED' ? '✓' : claim.status === 'CONTRADICTED' ? '✗' : '?'}
                          </span>
                          <p className="text-xs text-surface-900 leading-relaxed">{claim.claim}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            </AnimatePresence>
          )}
        </div>

        {/* Input */}
        <div className="p-4 border-t border-timber/60">
          <div className="flex items-end gap-3">
            <div className="flex-1 relative">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={e => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask a question about your documents… (Enter to send)"
                rows={2}
                className="w-full organic-input rounded-[1.5rem] px-4 py-3 text-sm resize-none"
              />
            </div>
            <button
              onClick={handleQuery}
              disabled={isLoading || !inputValue.trim()}
              className="flex-shrink-0 w-12 h-12 rounded-full bg-brand-500 hover:bg-brand-600 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-all hover:scale-105 active:scale-95 shadow-soft"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 text-white animate-spin" />
              ) : (
                <Send className="w-4 h-4 text-white" />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
