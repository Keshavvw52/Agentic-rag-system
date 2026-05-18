"""
Query API endpoints: agentic query, simple query, trace, claims, iterations.
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends, status

from app.schemas.schemas import (
    QueryRequest, QueryResponse, SimpleQueryResponse,
    AnswerSource, ConfidenceBreakdown, ConfidenceLabel,
)
from app.auth.jwt_handler import get_current_user
from app.db.mongodb import get_database
from app.graph.agentic_pipeline import run_agentic_pipeline
from app.services.retrieval import retrieve, RetrievalStrategy
from app.services.groq_client import call_groq_with_context

router = APIRouter()

ANSWER_SYSTEM_PROMPT = """You are a helpful AI assistant. Answer based on the provided context."""


async def _load_conversation_history(user_id: str, limit: int = 6) -> list[dict]:
    """Load recent user/assistant turns from previous queries for conversational context."""
    db = get_database()
    previous_queries = await db.queries.find(
        {"user_id": user_id},
        {"query": 1, "answer": 1, "created_at": 1},
    ).sort("created_at", -1).limit(limit).to_list(limit)

    history: list[dict] = []
    for item in reversed(previous_queries):
        query_text = (item.get("query") or "").strip()
        answer_text = (item.get("answer") or "").strip()

        if query_text:
            history.append({"role": "user", "content": query_text})
        if answer_text:
            history.append({"role": "assistant", "content": answer_text})

    return history


@router.post("", response_model=QueryResponse)
async def agentic_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Full agentic RAG query:
    classify → route → retrieve → CRAG eval → generate → hallucination check → confidence score
    """
    user_id = current_user["id"]
    query_id = str(uuid.uuid4())
    conversation_history = await _load_conversation_history(user_id)

    # Run agentic pipeline
    state = await run_agentic_pipeline(
        query=request.query,
        user_id=user_id,
        query_id=query_id,
        conversation_history=conversation_history,
    )

    # Default confidence if pipeline failed early
    if state.confidence_breakdown is None:
        state.confidence_breakdown = ConfidenceBreakdown(
            retrieval_relevance=0.0,
            faithfulness=0.0,
            context_coverage=0.0,
            coherence=0.0,
            final_score=0.0,
            label=ConfidenceLabel.VERY_LOW,
        )

    # Persist to MongoDB
    db = get_database()
    query_doc = {
        "_id": query_id,
        "user_id": user_id,
        "query": request.query,
        "answer": state.answer,
        "query_type": state.query_type.value if state.query_type else None,
        "retrieval_strategy": state.retrieval_strategy.value if state.retrieval_strategy else None,
        "answer_source": state.answer_source.value,
        "confidence_score": state.confidence_breakdown.final_score,
        "confidence_label": state.confidence_breakdown.label.value,
        "hallucination_score": state.hallucination_score,
        "fallback_used": state.fallback_used,
        "retries": state.retries,
        "iterations_count": len(state.iterations),
        "total_duration_ms": state.total_duration_ms,
        "created_at": datetime.now(timezone.utc),
    }
    await db.queries.insert_one(query_doc)

    # Persist trace
    trace_doc = {
        "query_id": query_id,
        "user_id": user_id,
        "steps": [step.model_dump(mode="json") for step in state.decision_trace],
        "iterations": [it.model_dump(mode="json") for it in state.iterations],
        "claims": [c.model_dump(mode="json") for c in state.claim_results],
        "created_at": datetime.now(timezone.utc),
    }
    await db.traces.insert_one(trace_doc)

    return QueryResponse(
        query_id=query_id,
        query=request.query,
        answer=state.answer,
        query_type=state.query_type,
        retrieval_strategy=state.retrieval_strategy,
        answer_source=state.answer_source,
        confidence=state.confidence_breakdown,
        claims=state.claim_results,
        hallucination_score=state.hallucination_score,
        fallback_used=state.fallback_used,
        iterations_count=len(state.iterations),
        total_duration_ms=state.total_duration_ms,
        created_at=query_doc["created_at"],
    )


@router.post("/simple", response_model=SimpleQueryResponse)
async def simple_query(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Simple RAG query (no agentic features) for baseline comparison.
    """
    user_id = current_user["id"]
    query_id = str(uuid.uuid4())

    chunks = await retrieve(
        query=request.query,
        user_id=user_id,
        strategy=RetrievalStrategy.HYBRID_RERANK,
    )

    context = "\n\n".join(c["text"] for c in chunks[:5])
    answer = await call_groq_with_context(
        query=request.query,
        context=context,
        system_prompt=ANSWER_SYSTEM_PROMPT,
    )

    db = get_database()
    query_doc = {
        "_id": query_id,
        "user_id": user_id,
        "query": request.query,
        "answer": answer,
        "is_simple": True,
        "chunks_used": len(chunks),
        "created_at": datetime.now(timezone.utc),
    }
    await db.queries.insert_one(query_doc)

    return SimpleQueryResponse(
        query_id=query_id,
        query=request.query,
        answer=answer,
        chunks_used=len(chunks),
        created_at=query_doc["created_at"],
    )


@router.get("/{query_id}/trace")
async def get_trace(query_id: str, current_user: dict = Depends(get_current_user)):
    """Get full agent decision trace for a query."""
    db = get_database()
    trace = await db.traces.find_one({"query_id": query_id, "user_id": current_user["id"]})
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    trace.pop("_id", None)
    return trace


@router.get("/{query_id}/claims")
async def get_claims(query_id: str, current_user: dict = Depends(get_current_user)):
    """Get claim verification results for a query."""
    db = get_database()
    trace = await db.traces.find_one({"query_id": query_id, "user_id": current_user["id"]})
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"query_id": query_id, "claims": trace.get("claims", [])}


@router.get("/{query_id}/iterations")
async def get_iterations(query_id: str, current_user: dict = Depends(get_current_user)):
    """Get refinement iteration history for a query."""
    db = get_database()
    trace = await db.traces.find_one({"query_id": query_id, "user_id": current_user["id"]})
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return {"query_id": query_id, "iterations": trace.get("iterations", [])}


@router.get("/history")
async def query_history(current_user: dict = Depends(get_current_user)):
    """Get query history for the current user."""
    db = get_database()
    cursor = db.queries.find(
        {"user_id": current_user["id"]},
        {"answer": 0}  # exclude full answer from list
    ).sort("created_at", -1).limit(50)

    queries = []
    async for q in cursor:
        q["id"] = str(q["_id"])
        queries.append(q)
    return {"queries": queries}
