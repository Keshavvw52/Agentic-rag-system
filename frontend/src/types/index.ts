// Core API types matching backend Pydantic schemas

export type QueryType = 'FACTUAL' | 'ANALYTICAL' | 'SUMMARIZATION' | 'CONVERSATIONAL' | 'OUT_OF_SCOPE'
export type RetrievalStrategy = 'HYBRID_RERANK' | 'MULTI_QUERY' | 'SECTION_BASED' | 'CONVERSATIONAL' | 'FALLBACK'
export type ClaimVerification = 'SUPPORTED' | 'NOT_SUPPORTED' | 'CONTRADICTED'
export type AnswerSource = 'DOCUMENTS' | 'WEB_SEARCH' | 'GENERAL_KNOWLEDGE' | 'ABSTAINED'
export type ConfidenceLabel = 'HIGH' | 'MEDIUM' | 'LOW' | 'VERY_LOW'

export interface User {
  id: string
  username: string
  email: string
  full_name?: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface Document {
  id: string
  filename: string
  file_type: string
  chunk_count: number
  status: string
  created_at: string
  user_id: string
}

export interface ClaimResult {
  claim: string
  status: ClaimVerification
  supporting_chunk?: string
  confidence: number
}

export interface ConfidenceBreakdown {
  retrieval_relevance: number
  faithfulness: number
  context_coverage: number
  coherence: number
  final_score: number
  label: ConfidenceLabel
}

export interface QueryResponse {
  query_id: string
  query: string
  answer: string
  query_type: QueryType
  retrieval_strategy: RetrievalStrategy
  answer_source: AnswerSource
  confidence: ConfidenceBreakdown
  claims: ClaimResult[]
  hallucination_score: number
  fallback_used: boolean
  iterations_count: number
  total_duration_ms: number
  created_at: string
}

export interface SimpleQueryResponse {
  query_id: string
  query: string
  answer: string
  chunks_used: number
  created_at: string
}

export interface TraceStep {
  step: string
  decision: string
  reasoning: string
  data: Record<string, unknown>
  duration_ms: number
  timestamp: string
}

export interface IterationRecord {
  iteration: number
  query_used: string
  chunks_retrieved: number
  answer_preview: string
  hallucination_score: number
  confidence_score: number
  improvements: string[]
}

export interface Trace {
  query_id: string
  steps: TraceStep[]
  iterations: IterationRecord[]
  claims: ClaimResult[]
}

export interface Stats {
  total_queries: number
  total_documents: number
  avg_confidence: number
  avg_hallucination_score: number
  fallback_rate: number
  retry_rate: number
  avg_latency_ms: number
  query_type_distribution: Record<string, number>
  strategy_distribution: Record<string, number>
}

export interface QueryHistoryItem {
  id: string
  query: string
  query_type?: QueryType
  confidence_score?: number
  confidence_label?: ConfidenceLabel
  hallucination_score?: number
  fallback_used?: boolean
  created_at: string
}