import axios from 'axios'
import toast from 'react-hot-toast'
import type {
  ClaimResult,
  Document,
  QueryResponse,
  SimpleQueryResponse,
  Stats,
  TokenResponse,
  Trace,
  User,
} from '@/types'

interface LoginPayload {
  email: string
  password: string
}

interface SignupPayload extends LoginPayload {
  username: string
  full_name?: string
}

interface DocumentsResponse {
  documents: Document[]
}

interface ClaimsResponse {
  query_id: string
  claims: ClaimResult[]
}

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

interface RoutingConfig {
  factual_strategy: string
  analytical_strategy: string
  summarization_strategy: string
  conversational_strategy: string
  routing_confidence_min: number
}

interface ThresholdConfig {
  hallucination_threshold: number
  max_retries: number
  max_iterations: number
  enable_web_search: boolean
  enable_llm_knowledge: boolean
}

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
})

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

api.interceptors.request.use((config) => {
  const raw = localStorage.getItem('auth-storage')
  const token = raw ? JSON.parse(raw)?.state?.token : null

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }

  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    const detail = error.response?.data?.detail
    toast.error(typeof detail === 'string' ? detail : 'Request failed')
    return Promise.reject(error)
  }
)

export const authApi = {
  signup: (payload: SignupPayload) => api.post<TokenResponse>('/auth/signup', payload),
  login: (payload: LoginPayload) => api.post<TokenResponse>('/auth/login', payload),
  me: () => api.get<User>('/auth/me'),
}

export const documentsApi = {
  list: () => api.get<DocumentsResponse>('/documents'),
  upload: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post<Document>('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  delete: (id: string) => api.delete<{ message: string }>(`/documents/${id}`),
}

export const queryApi = {
  agentic: (query: string) => api.post<QueryResponse>('/query', { query }),
  agenticStream: async (
    query: string,
    handlers: {
      onStatus?: (message: string) => void
      onAnswerDelta?: (text: string) => void
      onAnswerReplace?: (text: string) => void
      onComplete: (result: QueryResponse) => void
    }
  ) => {
    const raw = localStorage.getItem('auth-storage')
    const token = raw ? JSON.parse(raw)?.state?.token : null

    const response = await fetch(`${API_BASE_URL}/query/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ query }),
    })

    if (!response.ok) {
      let detail = 'Query failed'
      try {
        const payload = await response.json()
        if (typeof payload?.detail === 'string') detail = payload.detail
      } catch {
        // ignore invalid JSON errors
      }
      toast.error(detail)
      throw new Error(detail)
    }

    if (!response.body) {
      throw new Error('Streaming is not available in this browser')
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done })

      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        const trimmed = line.trim()
        if (!trimmed) continue

        const payload = JSON.parse(trimmed) as {
          event: 'status' | 'answer_delta' | 'answer_replace' | 'complete' | 'error'
          data: unknown
        }

        if (payload.event === 'status') {
          handlers.onStatus?.((payload.data as { message?: string }).message || '')
        } else if (payload.event === 'answer_delta') {
          handlers.onAnswerDelta?.((payload.data as { text?: string }).text || '')
        } else if (payload.event === 'answer_replace') {
          handlers.onAnswerReplace?.((payload.data as { text?: string }).text || '')
        } else if (payload.event === 'complete') {
          handlers.onComplete(payload.data as QueryResponse)
        } else if (payload.event === 'error') {
          const detail = (payload.data as { detail?: string }).detail || 'Query failed'
          toast.error(detail)
          throw new Error(detail)
        }
      }

      if (done) break
    }
  },
  simple: (query: string) => api.post<SimpleQueryResponse>('/query/simple', { query }),
  trace: (queryId: string) => api.get<Trace>(`/query/${queryId}/trace`),
  claims: (queryId: string) => api.get<ClaimsResponse>(`/query/${queryId}/claims`),
}

export const evaluationApi = {
  results: () => api.get<EvaluationResultsResponse>('/evaluate/results'),
}

export const statsApi = {
  get: () => api.get<Stats>('/stats'),
}

export const configApi = {
  getRouting: () => api.get<Partial<RoutingConfig>>('/config/routing'),
  updateRouting: (payload: RoutingConfig) => api.put('/config/routing', payload),
  updateThresholds: (payload: ThresholdConfig) => api.put('/config/thresholds', payload),
}

export default api
