"""
LangGraph Agentic RAG Pipeline.

Complete state graph with nodes for:
  classify_query → route_strategy → retrieve_documents → evaluate_retrieval
  → (retry/fallback if needed) → generate_answer → hallucination_check
  → (regenerate if needed) → confidence_scoring → finalize_response

Uses conditional edges, retry loops, and full decision tracing.
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END

from app.schemas.schemas import (
    AgentState, QueryType, RetrievalStrategy, ChunkLabel,
    ClaimResult, ConfidenceBreakdown, TraceStep, IterationRecord,
    AnswerSource, ConfidenceLabel, ClaimVerification,
)
from app.services.query_router import classify_query, get_alternative_strategy
from app.services.retrieval import retrieve
from app.services.corrective_rag import evaluate_retrieval, decide_crag_action, refine_query, filter_relevant_chunks
from app.services.hallucination_detector import extract_claims, verify_claims, calculate_hallucination_score, regenerate_answer
from app.services.confidence_scorer import compute_confidence
from app.services.fallback_chain import fallback_web_search, fallback_llm_knowledge, fallback_abstain
from app.services.groq_client import call_groq_with_context
from app.config.settings import settings

ANSWER_SYSTEM_PROMPT = """You are a helpful, accurate AI assistant.
Answer questions based on the provided context.
Be concise, accurate, and well-structured.
If the context doesn't fully answer the question, say so clearly."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _add_trace(state: AgentState, step: str, decision: str, reasoning: str, data: dict, start_time: float) -> None:
    """Helper to add a trace step."""
    duration_ms = (time.time() - start_time) * 1000
    state.decision_trace.append(TraceStep(
        step=step,
        decision=decision,
        reasoning=reasoning,
        data=data,
        duration_ms=round(duration_ms, 2),
        timestamp=_now(),
    ))


# ─── Graph Nodes ─────────────────────────────────────────────────────────────

async def node_classify_query(state: AgentState) -> AgentState:
    """Node 1: Classify query type and select retrieval strategy."""
    t = time.time()
    print(f"[Agent] Classifying query: {state.query[:80]}...")

    query_type, confidence, reasoning, strategy = await classify_query(
        query=state.query,
        conversation_history=state.conversation_history,
    )

    state.query_type = query_type
    state.query_type_confidence = confidence
    state.query_type_reasoning = reasoning
    state.retrieval_strategy = strategy
    state.routing_confidence = confidence

    _add_trace(state, "classify_query",
        f"Classified as {query_type.value} → Routing to {strategy.value}",
        reasoning,
        {"query_type": query_type.value, "confidence": confidence, "strategy": strategy.value},
        t,
    )
    return state


async def node_retrieve_documents(state: AgentState) -> AgentState:
    """Node 2: Retrieve documents using selected strategy."""
    t = time.time()
    strategy = state.retrieval_strategy or RetrievalStrategy.HYBRID_RERANK
    query = state.refined_query or state.query

    print(f"[Agent] Retrieving with {strategy.value} (attempt {state.retries + 1})")

    chunks = await retrieve(
        query=query,
        user_id=state.user_id,
        strategy=strategy,
        conversation_history=state.conversation_history,
    )

    state.retrieved_chunks = chunks
    state.retrieval_scores = [c.get("score", 0.0) for c in chunks]

    _add_trace(state, "retrieve_documents",
        f"Retrieved {len(chunks)} chunks using {strategy.value}",
        f"Query: '{query}', Strategy: {strategy.value}, Retry #{state.retries}",
        {"chunks_count": len(chunks), "strategy": strategy.value, "query_used": query},
        t,
    )
    return state


async def node_evaluate_retrieval(state: AgentState) -> AgentState:
    """Node 3: CRAG evaluation - score and label each chunk."""
    t = time.time()
    chunks = state.retrieved_chunks

    if not chunks:
        state.crag_labels = []
        _add_trace(state, "evaluate_retrieval",
            "FALLBACK - No chunks retrieved",
            "Empty retrieval result",
            {"decision": "FALLBACK", "reason": "no_chunks"},
            t,
        )
        return state

    labels, scores = await evaluate_retrieval(state.query, chunks)
    state.crag_labels = labels

    # Update chunk scores with CRAG evaluations
    for i, (chunk, score) in enumerate(zip(state.retrieved_chunks, scores)):
        chunk["crag_score"] = score
        chunk["crag_label"] = labels[i].value if i < len(labels) else "AMBIGUOUS"

    correct = labels.count(ChunkLabel.CORRECT)
    ambiguous = labels.count(ChunkLabel.AMBIGUOUS)
    incorrect = labels.count(ChunkLabel.INCORRECT)
    decision = decide_crag_action(labels)

    _add_trace(state, "evaluate_retrieval",
        f"CRAG Decision: {decision} ({correct}✓ {ambiguous}~ {incorrect}✗)",
        f"Correct: {correct}, Ambiguous: {ambiguous}, Incorrect: {incorrect}",
        {
            "decision": decision,
            "correct": correct,
            "ambiguous": ambiguous,
            "incorrect": incorrect,
            "labels": [l.value for l in labels],
        },
        t,
    )
    return state


async def node_retry_retrieval(state: AgentState) -> AgentState:
    """Node 4: Retry with refined query and/or alternative strategy."""
    t = time.time()
    state.retries += 1

    # Refine query
    refined = await refine_query(state.query, state.retrieved_chunks)
    state.refined_query = refined

    # Switch to alternative strategy
    current_strategy = state.retrieval_strategy or RetrievalStrategy.HYBRID_RERANK
    alt_strategy = get_alternative_strategy(current_strategy)
    state.retrieval_strategy = alt_strategy

    _add_trace(state, "retry_retrieval",
        f"Retrying with {alt_strategy.value} and refined query",
        f"Original: '{state.query}' → Refined: '{refined}'",
        {
            "retry_number": state.retries,
            "original_query": state.query,
            "refined_query": refined,
            "new_strategy": alt_strategy.value,
        },
        t,
    )
    return state


async def node_fallback_handler(state: AgentState) -> AgentState:
    """Node 5: Execute fallback chain when retrieval fails."""
    t = time.time()

    # Track what was attempted
    attempts = [
        f"Vector search in your documents (strategy: {state.retrieval_strategy.value if state.retrieval_strategy else 'unknown'})",
        f"Query refinement and retry ({state.retries} attempts)",
    ]

    answer = ""
    source = AnswerSource.ABSTAINED

    # Level 2: Web search
    if settings.USE_TAVILY or True:  # Try DuckDuckGo always
        try:
            answer, source, web_results = await fallback_web_search(state.query)
            if answer:
                state.fallback_used = True
                state.fallback_level = 2
                state.retrieved_chunks = [
                    {"text": r.get("content", ""), "score": 0.5, "metadata": {"source": r.get("url", "")}}
                    for r in web_results
                ]
        except Exception as e:
            print(f"Web search fallback failed: {e}")

    # Level 3: LLM knowledge
    if not answer:
        try:
            answer, source = await fallback_llm_knowledge(state.query)
            state.fallback_used = True
            state.fallback_level = 3
        except Exception as e:
            print(f"LLM knowledge fallback failed: {e}")

    # Level 4: Abstain
    if not answer:
        answer, source = fallback_abstain(state.query, attempts)
        state.fallback_used = True
        state.fallback_level = 4

    state.answer = answer
    state.answer_source = source

    _add_trace(state, "fallback_handler",
        f"Fallback Level {state.fallback_level}: {source.value}",
        f"Document retrieval failed after {state.retries} retries. Used {source.value}",
        {"fallback_level": state.fallback_level, "source": source.value},
        t,
    )
    return state


async def node_generate_answer(state: AgentState) -> AgentState:
    """Node 6: Generate answer from retrieved context."""
    t = time.time()

    # Filter to best chunks only
    good_chunks = filter_relevant_chunks(
        state.retrieved_chunks,
        state.crag_labels,
        [c.get("crag_score", c.get("score", 0.5)) for c in state.retrieved_chunks],
    )

    if not good_chunks:
        good_chunks = state.retrieved_chunks[:5]  # fallback to top chunks

    context = "\n\n---\n\n".join([
        f"[Source: {c['metadata'].get('filename', 'document')}]\n{c['text']}"
        for c in good_chunks[:10]
    ])

    answer = await call_groq_with_context(
        query=state.query,
        context=context,
        system_prompt=ANSWER_SYSTEM_PROMPT,
        max_tokens=1500,
        temperature=0.1,
    )

    state.answer = answer
    state.answer_source = AnswerSource.DOCUMENTS

    # Track iteration
    iteration_num = len(state.iterations) + 1
    state.iterations.append(IterationRecord(
        iteration=iteration_num,
        query_used=state.refined_query or state.query,
        chunks_retrieved=len(good_chunks),
        answer_preview=answer[:200],
        hallucination_score=0.0,  # will be updated after detection
        confidence_score=0.0,  # will be updated after scoring
    ))

    _add_trace(state, "generate_answer",
        f"Generated answer from {len(good_chunks)} verified chunks",
        f"Used {len(good_chunks)} chunks, context: {len(context)} chars",
        {"chunks_used": len(good_chunks), "answer_length": len(answer)},
        t,
    )
    return state


async def node_hallucination_check(state: AgentState) -> AgentState:
    """Node 7: Extract claims, verify against context, score hallucinations."""
    t = time.time()

    if not state.answer or state.answer_source != AnswerSource.DOCUMENTS:
        # Skip for fallback answers
        _add_trace(state, "hallucination_check",
            "Skipped (non-document answer)",
            f"Answer source: {state.answer_source.value}",
            {"skipped": True},
            t,
        )
        return state

    context = "\n\n".join(c["text"] for c in state.retrieved_chunks[:10])

    # Extract claims
    claims = await extract_claims(state.answer)
    state.claims = claims

    # Verify claims
    if claims:
        claim_results = await verify_claims(claims, context)
        state.claim_results = claim_results
        state.hallucination_score = calculate_hallucination_score(claim_results)
    else:
        state.claim_results = []
        state.hallucination_score = 0.0

    # Update iteration record
    if state.iterations:
        state.iterations[-1].hallucination_score = state.hallucination_score

    supported = sum(1 for c in state.claim_results if c.status == ClaimVerification.SUPPORTED)
    unsupported = sum(1 for c in state.claim_results if c.status != ClaimVerification.SUPPORTED)

    needs_regen = state.hallucination_score > settings.HALLUCINATION_THRESHOLD

    _add_trace(state, "hallucination_check",
        f"Score: {state.hallucination_score:.1%} ({'REGENERATE' if needs_regen else 'PASS'})",
        f"{len(claims)} claims: {supported} supported, {unsupported} unsupported",
        {
            "total_claims": len(claims),
            "supported": supported,
            "unsupported": unsupported,
            "hallucination_score": state.hallucination_score,
            "threshold": settings.HALLUCINATION_THRESHOLD,
            "needs_regeneration": needs_regen,
        },
        t,
    )
    return state


async def node_regenerate_answer(state: AgentState) -> AgentState:
    """Node 8: Re-generate with stricter grounding when hallucinations detected."""
    t = time.time()

    context = "\n\n".join(c["text"] for c in state.retrieved_chunks[:10])
    new_answer = await regenerate_answer(state.query, context, state.claim_results)

    old_score = state.hallucination_score
    state.answer = new_answer

    # Re-check hallucinations
    new_claims = await extract_claims(new_answer)
    state.claims = new_claims
    if new_claims:
        new_results = await verify_claims(new_claims, context)
        state.claim_results = new_results
        state.hallucination_score = calculate_hallucination_score(new_results)

    improvement = old_score - state.hallucination_score

    # Track iteration
    iteration_num = len(state.iterations) + 1
    state.iterations.append(IterationRecord(
        iteration=iteration_num,
        query_used=state.refined_query or state.query,
        chunks_retrieved=len(state.retrieved_chunks),
        answer_preview=new_answer[:200],
        hallucination_score=state.hallucination_score,
        confidence_score=0.0,
        improvements=[f"Reduced hallucination score by {improvement:.1%}"],
    ))

    _add_trace(state, "regenerate_answer",
        f"Regenerated: hallucination {old_score:.1%} → {state.hallucination_score:.1%}",
        f"Improvement: {improvement:.1%}",
        {
            "old_hallucination_score": old_score,
            "new_hallucination_score": state.hallucination_score,
            "improvement": improvement,
        },
        t,
    )
    return state


async def node_confidence_scoring(state: AgentState) -> AgentState:
    """Node 9: Compute multi-factor confidence score."""
    t = time.time()

    confidence = await compute_confidence(
        query=state.query,
        answer=state.answer,
        chunks=state.retrieved_chunks,
        claim_results=state.claim_results,
        hallucination_score=state.hallucination_score,
    )
    state.confidence_breakdown = confidence

    # Update last iteration
    if state.iterations:
        state.iterations[-1].confidence_score = confidence.final_score

    _add_trace(state, "confidence_scoring",
        f"Confidence: {confidence.final_score:.1%} ({confidence.label.value})",
        f"R:{confidence.retrieval_relevance:.2f} F:{confidence.faithfulness:.2f} "
        f"C:{confidence.context_coverage:.2f} Co:{confidence.coherence:.2f}",
        {
            "final_score": confidence.final_score,
            "label": confidence.label.value,
            "breakdown": {
                "retrieval_relevance": confidence.retrieval_relevance,
                "faithfulness": confidence.faithfulness,
                "context_coverage": confidence.context_coverage,
                "coherence": confidence.coherence,
            },
        },
        t,
    )
    return state


async def node_finalize_response(state: AgentState) -> AgentState:
    """Node 10: Finalize and mark the response as complete."""
    state.finalized = True
    return state


# ─── Conditional Edge Functions ───────────────────────────────────────────────

def should_retry_or_fallback(state: AgentState) -> str:
    """After CRAG evaluation: proceed, retry, or fallback."""
    from app.services.corrective_rag import decide_crag_action
    decision = decide_crag_action(state.crag_labels)

    if decision == "PROCEED":
        return "generate_answer"
    elif decision == "RETRY" and state.retries < settings.MAX_RETRIES:
        return "retry_retrieval"
    else:
        # Too many retries or must fallback
        return "fallback_handler"


def should_regenerate(state: AgentState) -> str:
    """After hallucination check: regenerate or score confidence."""
    if state.hallucination_score > settings.HALLUCINATION_THRESHOLD:
        # Only regenerate up to MAX_ITERATIONS times
        regen_count = sum(1 for step in state.decision_trace if step.step == "regenerate_answer")
        if regen_count < settings.MAX_ITERATIONS - 1:
            return "regenerate_answer"
    return "confidence_scoring"


def after_fallback(state: AgentState) -> str:
    """After fallback: go straight to confidence scoring."""
    return "confidence_scoring"


# ─── Build the Graph ─────────────────────────────────────────────────────────

def build_agentic_graph():
    """Construct and compile the LangGraph state graph."""
    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("classify_query", node_classify_query)
    graph.add_node("retrieve_documents", node_retrieve_documents)
    graph.add_node("evaluate_retrieval", node_evaluate_retrieval)
    graph.add_node("retry_retrieval", node_retry_retrieval)
    graph.add_node("fallback_handler", node_fallback_handler)
    graph.add_node("generate_answer", node_generate_answer)
    graph.add_node("hallucination_check", node_hallucination_check)
    graph.add_node("regenerate_answer", node_regenerate_answer)
    graph.add_node("confidence_scoring", node_confidence_scoring)
    graph.add_node("finalize_response", node_finalize_response)

    # Entry point
    graph.set_entry_point("classify_query")

    # Linear edges
    graph.add_edge("classify_query", "retrieve_documents")
    graph.add_edge("retrieve_documents", "evaluate_retrieval")
    graph.add_edge("retry_retrieval", "retrieve_documents")  # loop back
    graph.add_edge("generate_answer", "hallucination_check")
    graph.add_edge("confidence_scoring", "finalize_response")
    graph.add_edge("finalize_response", END)

    # Conditional edges
    graph.add_conditional_edges(
        "evaluate_retrieval",
        should_retry_or_fallback,
        {
            "generate_answer": "generate_answer",
            "retry_retrieval": "retry_retrieval",
            "fallback_handler": "fallback_handler",
        },
    )
    graph.add_conditional_edges(
        "hallucination_check",
        should_regenerate,
        {
            "regenerate_answer": "regenerate_answer",
            "confidence_scoring": "confidence_scoring",
        },
    )
    graph.add_conditional_edges(
        "regenerate_answer",
        should_regenerate,
        {
            "regenerate_answer": "regenerate_answer",
            "confidence_scoring": "confidence_scoring",
        },
    )
    graph.add_conditional_edges(
        "fallback_handler",
        after_fallback,
        {"confidence_scoring": "confidence_scoring"},
    )

    return graph.compile()


# Singleton compiled graph
_compiled_graph = None


def get_agentic_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_agentic_graph()
    return _compiled_graph


async def run_agentic_pipeline(
    query: str,
    user_id: str,
    query_id: str,
    conversation_history: list[dict] | None = None,
) -> AgentState:
    """
    Execute the full agentic RAG pipeline.
    Returns the final AgentState with all results and decision trace.
    """
    graph = get_agentic_graph()

    initial_state = AgentState(
        query_id=query_id,
        user_id=user_id,
        query=query,
        conversation_history=conversation_history or [],
    )

    start = time.time()
    result = await graph.ainvoke(initial_state)
    final_state = result if isinstance(result, AgentState) else AgentState.model_validate(result)
    final_state.total_duration_ms = round((time.time() - start) * 1000, 2)

    return final_state
