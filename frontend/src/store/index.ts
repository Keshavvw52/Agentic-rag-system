import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, QueryResponse, Document, Stats, Trace } from '@/types'

// ─── Auth Store ───────────────────────────────────────────────────────────────

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: User, token: string) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      setAuth: (user, token) => set({ user, token, isAuthenticated: true }),
      logout: () => set({ user: null, token: null, isAuthenticated: false }),
    }),
    { name: 'auth-storage' }
  )
)

// ─── Query Store ──────────────────────────────────────────────────────────────

interface QueryState {
  currentQuery: string
  agenticResult: QueryResponse | null
  simpleResult: { query_id: string; answer: string; chunks_used: number } | null
  currentTrace: Trace | null
  isLoading: boolean
  isLoadingSimple: boolean
  error: string | null

  setQuery: (q: string) => void
  setAgenticResult: (r: QueryResponse) => void
  setSimpleResult: (r: QueryState['simpleResult']) => void
  setTrace: (t: Trace) => void
  setLoading: (v: boolean) => void
  setLoadingSimple: (v: boolean) => void
  setError: (e: string | null) => void
  reset: () => void
}

export const useQueryStore = create<QueryState>((set) => ({
  currentQuery: '',
  agenticResult: null,
  simpleResult: null,
  currentTrace: null,
  isLoading: false,
  isLoadingSimple: false,
  error: null,

  setQuery: (q) => set({ currentQuery: q }),
  setAgenticResult: (r) => set({ agenticResult: r }),
  setSimpleResult: (r) => set({ simpleResult: r }),
  setTrace: (t) => set({ currentTrace: t }),
  setLoading: (v) => set({ isLoading: v }),
  setLoadingSimple: (v) => set({ isLoadingSimple: v }),
  setError: (e) => set({ error: e }),
  reset: () => set({
    agenticResult: null,
    simpleResult: null,
    currentTrace: null,
    error: null,
  }),
}))

// ─── Dashboard Store ──────────────────────────────────────────────────────────

interface DashboardState {
  documents: Document[]
  stats: Stats | null
  queryHistory: Array<{ id: string; query: string; confidence_score?: number; created_at: string }>
  activeTab: string

  setDocuments: (docs: Document[]) => void
  addDocument: (doc: Document) => void
  removeDocument: (id: string) => void
  setStats: (s: Stats) => void
  setHistory: (h: DashboardState['queryHistory']) => void
  setActiveTab: (t: string) => void
}

export const useDashboardStore = create<DashboardState>((set) => ({
  documents: [],
  stats: null,
  queryHistory: [],
  activeTab: 'query',

  setDocuments: (docs) => set({ documents: docs }),
  addDocument: (doc) => set((state) => ({ documents: [doc, ...state.documents] })),
  removeDocument: (id) => set((state) => ({
    documents: state.documents.filter((d) => d.id !== id),
  })),
  setStats: (s) => set({ stats: s }),
  setHistory: (h) => set({ queryHistory: h }),
  setActiveTab: (t) => set({ activeTab: t }),
}))