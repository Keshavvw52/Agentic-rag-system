from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


# ─── Enums ───────────────────────────────────────────────────────────────────

class QueryType(str, Enum):
    FACTUAL = "FACTUAL"
    ANALYTICAL = "ANALYTICAL"
    SUMMARIZATION = "SUMMARIZATION"
    CONVERSATIONAL = "CONVERSATIONAL"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class RetrievalStrategy(str, Enum):
    HYBRID_RERANK = "HYBRID_RERANK"
    MULTI_QUERY = "MULTI_QUERY"
    SECTION_BASED = "SECTION_BASED"
    CONVERSATIONAL = "CONVERSATIONAL"
    FALLBACK = "FALLBACK"


class ChunkLabel(str, Enum):
    CORRECT = "CORRECT"
    AMBIGUOUS = "AMBIGUOUS"
    INCORRECT = "INCORRECT"


class ClaimVerification(str, Enum):
    SUPPORTED = "SUPPORTED"
    NOT_SUPPORTED = "NOT_SUPPORTED"
    CONTRADICTED = "CONTRADICTED"


class AnswerSource(str, Enum):
    DOCUMENTS = "DOCUMENTS"
    WEB_SEARCH = "WEB_SEARCH"
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
    ABSTAINED = "ABSTAINED"


class ConfidenceLabel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    VERY_LOW = "VERY_LOW"


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str
    password: str = Field(..., min_length=6)
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str
    full_name: Optional[str]
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# ─── Document Schemas ─────────────────────────────────────────────────────────

class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    chunk_count: int
    status: str
    created_at: datetime
    user_id: str


# ─── Agent State ──────────────────────────────────────────────────────────────

class ClaimResult(BaseModel):
    claim: str
    status: ClaimVerification
    supporting_chunk: Optional[str] = None
    confidence: float = 0.0


class ConfidenceBreakdown(BaseModel):
    retrieval_relevance: float
    faithfulness: float
    context_coverage: float
    coherence: float
    final_score: float
    label: ConfidenceLabel


class TraceStep(BaseModel):
    step: str
    decision: str
    reasoning: str
    data: dict[str, Any] = {}
    duration_ms: float
    timestamp: datetime


class IterationRecord(BaseModel):
    iteration: int
    query_used: str
    chunks_retrieved: int
    answer_preview: str
    hallucination_score: float
    confidence_score: float
    improvements: list[str] = []


class AgentState(BaseModel):
    """Complete shared state for the LangGraph agentic pipeline."""
    # Identity
    query_id: str
    user_id: str

    # Input
    query: str
    conversation_history: list[dict] = []

    # Classification
    query_type: Optional[QueryType] = None
    query_type_confidence: float = 0.0
    query_type_reasoning: str = ""

    # Routing
    retrieval_strategy: Optional[RetrievalStrategy] = None
    routing_confidence: float = 0.0

    # Retrieval
    retrieved_chunks: list[dict] = []
    retrieval_scores: list[float] = []
    crag_labels: list[ChunkLabel] = []
    refined_query: Optional[str] = None
    retries: int = 0

    # Generation
    answer: str = ""
    answer_source: AnswerSource = AnswerSource.DOCUMENTS

    # Hallucination
    claims: list[str] = []
    claim_results: list[ClaimResult] = []
    hallucination_score: float = 0.0

    # Confidence
    confidence_breakdown: Optional[ConfidenceBreakdown] = None

    # Fallback
    fallback_used: bool = False
    fallback_level: int = 0

    # Trace
    decision_trace: list[TraceStep] = []
    iterations: list[IterationRecord] = []
    total_duration_ms: float = 0.0

    # Status
    error: Optional[str] = None
    finalized: bool = False


# ─── Query Request/Response Schemas ──────────────────────────────────────────

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class QueryResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    query_type: Optional[QueryType]
    retrieval_strategy: Optional[RetrievalStrategy]
    answer_source: AnswerSource
    confidence: ConfidenceBreakdown
    claims: list[ClaimResult]
    hallucination_score: float
    fallback_used: bool
    iterations_count: int
    total_duration_ms: float
    created_at: datetime


class SimpleQueryResponse(BaseModel):
    query_id: str
    query: str
    answer: str
    chunks_used: int
    created_at: datetime


# ─── Evaluation Schemas ───────────────────────────────────────────────────────

class HallucinationEvalRequest(BaseModel):
    answer: str
    context: str


class HallucinationEvalResponse(BaseModel):
    claims: list[ClaimResult]
    hallucination_score: float
    total_claims: int
    supported_claims: int
    unsupported_claims: int
    contradicted_claims: int


class EvalResultResponse(BaseModel):
    query: str
    agentic_score: float
    simple_score: float
    agentic_hallucination: float
    simple_hallucination: float
    improvement: float


# ─── Config Schemas ───────────────────────────────────────────────────────────

class RoutingConfig(BaseModel):
    factual_strategy: RetrievalStrategy = RetrievalStrategy.HYBRID_RERANK
    analytical_strategy: RetrievalStrategy = RetrievalStrategy.MULTI_QUERY
    summarization_strategy: RetrievalStrategy = RetrievalStrategy.SECTION_BASED
    conversational_strategy: RetrievalStrategy = RetrievalStrategy.CONVERSATIONAL
    routing_confidence_min: float = 0.70


class ThresholdConfig(BaseModel):
    hallucination_threshold: float = 0.20
    max_retries: int = 3
    max_iterations: int = 3
    confidence_high: float = 0.90
    confidence_medium: float = 0.70
    confidence_low: float = 0.50
    enable_web_search: bool = True
    enable_llm_knowledge: bool = True


# ─── Stats Schema ─────────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_queries: int
    total_documents: int
    avg_confidence: float
    avg_hallucination_score: float
    fallback_rate: float
    retry_rate: float
    avg_latency_ms: float
    query_type_distribution: dict[str, int]
    strategy_distribution: dict[str, int]