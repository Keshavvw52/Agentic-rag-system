"""
Query API endpoints: agentic query, simple query, trace, claims, iterations.
"""

import json
import time
import uuid
from datetime import datetime, timezone
from typing import AsyncIterator
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from app.schemas.schemas import (
    QueryRequest, QueryResponse, SimpleQueryResponse, AgentState,
    AnswerSource, ConfidenceBreakdown, ConfidenceLabel,
    IterationRecord,
)
from app.auth.jwt_handler import get_current_user
from app.db.mongodb import get_database
from app.graph.agentic_pipeline import (
    run_agentic_pipeline,
    node_classify_query,
    node_retrieve_documents,
    node_evaluate_retrieval,
    node_retry_retrieval,
    node_hallucination_check,
    node_regenerate_answer,
    node_confidence_scoring,
    node_finalize_response,
    should_retry_or_fallback,
    should_regenerate,
    _add_trace,
    ANSWER_SYSTEM_PROMPT,
)
from app.config.settings import settings
from app.services.retrieval import retrieve, RetrievalStrategy
from app.services.corrective_rag import filter_relevant_chunks
from app.services.fallback_chain import fallback_abstain, _duckduckgo_search, _tavily_search, WEB_SEARCH_SYSTEM, LLM_KNOWLEDGE_SYSTEM
from app.services.groq_client import call_groq_stream, call_groq_with_context, call_groq_with_context_stream

router = APIRouter()

SIMPLE_ANSWER_SYSTEM_PROMPT = """You are a helpful AI assistant. Answer based on the provided context."""


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


def _serialize_event(event: str, data: dict) -> str:
    return json.dumps({"event": event, "data": data}, default=str) + "\n"


async def _persist_query_artifacts(
    state: AgentState,
    query_id: str,
    query_text: str,
    user_id: str,
) -> tuple[dict, QueryResponse]:
    if state.confidence_breakdown is None:
        state.confidence_breakdown = ConfidenceBreakdown(
            retrieval_relevance=0.0,
            faithfulness=0.0,
            context_coverage=0.0,
            coherence=0.0,
            final_score=0.0,
            label=ConfidenceLabel.VERY_LOW,
        )

    db = get_database()
    created_at = datetime.now(timezone.utc)
    query_doc = {
        "_id": query_id,
        "user_id": user_id,
        "query": query_text,
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
        "created_at": created_at,
    }
    await db.queries.insert_one(query_doc)

    trace_doc = {
        "query_id": query_id,
        "user_id": user_id,
        "steps": [step.model_dump(mode="json") for step in state.decision_trace],
        "iterations": [it.model_dump(mode="json") for it in state.iterations],
        "claims": [c.model_dump(mode="json") for c in state.claim_results],
        "created_at": created_at,
    }
    await db.traces.insert_one(trace_doc)

    response = QueryResponse(
        query_id=query_id,
        query=query_text,
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
        created_at=created_at,
    )

    return query_doc, response


async def _stream_fallback_answer(state: AgentState) -> AsyncIterator[str]:
    t = time.time()
    attempts = [
        f"Vector search in your documents (strategy: {state.retrieval_strategy.value if state.retrieval_strategy else 'unknown'})",
        f"Query refinement and retry ({state.retries} attempts)",
    ]

    if settings.USE_TAVILY and settings.TAVILY_API_KEY:
        web_results = await _tavily_search(state.query)
    else:
        web_results = await _duckduckgo_search(state.query)

    if web_results:
        results_text = "\n\n".join([
            f"Source: {r.get('url', 'Web')}\n{r.get('content', r.get('snippet', ''))}"
            for r in web_results[:5]
        ])

        answer_parts: list[str] = []
        async for chunk in call_groq_stream(
            f"Web search results for: {state.query}\n\n{results_text}\n\nAnswer the question based on these results.",
            system_prompt=WEB_SEARCH_SYSTEM,
            max_tokens=1000,
            temperature=0.1,
        ):
            answer_parts.append(chunk)
            yield _serialize_event("answer_delta", {"text": chunk})

        state.answer = "".join(answer_parts)
        state.answer_source = AnswerSource.WEB_SEARCH
        state.fallback_used = True
        state.fallback_level = 2
        state.retrieved_chunks = [
            {"text": r.get("content", ""), "score": 0.5, "metadata": {"source": r.get("url", "")}}
            for r in web_results
        ]
    else:
        answer_parts = []
        async for chunk in call_groq_stream(
            f"Question: {state.query}\n\nAnswer from your general knowledge. Start your response with: 'Based on general knowledge (not from your documents):'",
            system_prompt=LLM_KNOWLEDGE_SYSTEM,
            max_tokens=1000,
            temperature=0.2,
        ):
            answer_parts.append(chunk)
            yield _serialize_event("answer_delta", {"text": chunk})

        if answer_parts:
            state.answer = "".join(answer_parts)
            state.answer_source = AnswerSource.GENERAL_KNOWLEDGE
            state.fallback_used = True
            state.fallback_level = 3
        else:
            answer, source = fallback_abstain(state.query, attempts)
            state.answer = answer
            state.answer_source = source
            state.fallback_used = True
            state.fallback_level = 4
            yield _serialize_event("answer_delta", {"text": answer})

    _add_trace(
        state,
        "fallback_handler",
        f"Fallback Level {state.fallback_level}: {state.answer_source.value}",
        f"Document retrieval failed after {state.retries} retries. Used {state.answer_source.value}",
        {"fallback_level": state.fallback_level, "source": state.answer_source.value},
        t,
    )


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

    _, response = await _persist_query_artifacts(state, query_id, request.query, user_id)
    return response


@router.post("/stream")
async def agentic_query_stream(
    request: QueryRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    query_id = str(uuid.uuid4())

    async def event_generator():
        start = time.time()
        conversation_history = await _load_conversation_history(user_id)
        state = AgentState(
            query_id=query_id,
            user_id=user_id,
            query=request.query,
            conversation_history=conversation_history,
        )

        try:
            yield _serialize_event("status", {"message": "Classifying query..."})
            state = await node_classify_query(state)

            while True:
                yield _serialize_event("status", {"message": f"Retrieving documents via {state.retrieval_strategy.value if state.retrieval_strategy else RetrievalStrategy.HYBRID_RERANK.value}..."})
                state = await node_retrieve_documents(state)

                yield _serialize_event("status", {"message": "Evaluating retrieval quality..."})
                state = await node_evaluate_retrieval(state)

                next_step = should_retry_or_fallback(state)
                if next_step == "retry_retrieval":
                    yield _serialize_event("status", {"message": "Refining search and trying again..."})
                    state = await node_retry_retrieval(state)
                    continue
                if next_step == "fallback_handler":
                    yield _serialize_event("status", {"message": "Document support is weak, switching to fallback answer generation..."})
                    async for event in _stream_fallback_answer(state):
                        yield event
                    break

                good_chunks = filter_relevant_chunks(
                    state.retrieved_chunks,
                    state.crag_labels,
                    [c.get("crag_score", c.get("score", 0.5)) for c in state.retrieved_chunks],
                )
                if not good_chunks:
                    good_chunks = state.retrieved_chunks[:5]

                context = "\n\n---\n\n".join([
                    f"[Source: {c['metadata'].get('filename', 'document')}]\n{c['text']}"
                    for c in good_chunks[:10]
                ])

                yield _serialize_event("status", {"message": "Generating answer..."})
                answer_started_at = time.time()
                answer_parts: list[str] = []
                async for chunk in call_groq_with_context_stream(
                    query=state.query,
                    context=context,
                    system_prompt=ANSWER_SYSTEM_PROMPT,
                    max_tokens=1500,
                    temperature=0.1,
                ):
                    answer_parts.append(chunk)
                    yield _serialize_event("answer_delta", {"text": chunk})

                state.answer = "".join(answer_parts)
                state.answer_source = AnswerSource.DOCUMENTS
                state.iterations.append(IterationRecord(
                    iteration=len(state.iterations) + 1,
                    query_used=state.refined_query or state.query,
                    chunks_retrieved=len(good_chunks),
                    answer_preview=state.answer[:200],
                    hallucination_score=0.0,
                    confidence_score=0.0,
                ))
                _add_trace(
                    state,
                    "generate_answer",
                    f"Generated answer from {len(good_chunks)} verified chunks",
                    f"Used {len(good_chunks)} chunks, context: {len(context)} chars",
                    {"chunks_used": len(good_chunks), "answer_length": len(state.answer)},
                    answer_started_at,
                )
                break

            if state.answer_source == AnswerSource.DOCUMENTS:
                yield _serialize_event("status", {"message": "Checking answer grounding..."})
                state = await node_hallucination_check(state)

                while should_regenerate(state) == "regenerate_answer":
                    yield _serialize_event("status", {"message": "Tightening the answer to remove unsupported claims..."})
                    state = await node_regenerate_answer(state)
                    yield _serialize_event("answer_replace", {"text": state.answer})

            yield _serialize_event("status", {"message": "Scoring confidence..."})
            state = await node_confidence_scoring(state)
            state = await node_finalize_response(state)
            state.total_duration_ms = round((time.time() - start) * 1000, 2)

            _, response = await _persist_query_artifacts(state, query_id, request.query, user_id)
            yield _serialize_event("complete", response.model_dump(mode="json"))
        except Exception as exc:
            yield _serialize_event("error", {"detail": str(exc)})

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")


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
        system_prompt=SIMPLE_ANSWER_SYSTEM_PROMPT,
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
