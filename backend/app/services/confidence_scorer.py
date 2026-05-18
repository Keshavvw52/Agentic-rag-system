"""
Confidence scoring system: 4-factor weighted confidence score.
Components: retrieval_relevance, faithfulness, context_coverage, coherence
Formula: 0.3 * retrieval_relevance + 0.3 * faithfulness + 0.2 * context_coverage + 0.2 * coherence
"""

from app.schemas.schemas import ConfidenceBreakdown, ConfidenceLabel, ClaimResult, ClaimVerification
from app.services.groq_client import call_groq_json
from app.config.settings import settings

COVERAGE_PROMPT = """Does the context provide enough information to fully answer the question?

Question: {query}

Context (first 2000 chars):
{context}

Rate the coverage 0.0-1.0:
- 1.0: Context fully answers the question
- 0.5: Context partially answers the question  
- 0.0: Context does not contain information to answer

Respond with JSON: {{"coverage_score": <float 0.0-1.0>, "reasoning": "<brief>"}}"""

COHERENCE_PROMPT = """Rate the quality and coherence of this answer.

Question: {query}
Answer: {answer}

Rate 0.0-1.0:
- 1.0: Well-structured, directly addresses the question, clear and comprehensive
- 0.5: Partially addresses the question or lacks clarity
- 0.0: Incoherent, off-topic, or refuses to answer

Respond with JSON: {{"coherence_score": <float 0.0-1.0>, "reasoning": "<brief>"}}"""


async def compute_confidence(
    query: str,
    answer: str,
    chunks: list[dict],
    claim_results: list[ClaimResult],
    hallucination_score: float,
) -> ConfidenceBreakdown:
    """
    Compute the full multi-factor confidence score.
    """
    import asyncio

    context = "\n\n".join(c["text"] for c in chunks[:10])

    # 1. Retrieval Relevance: average of chunk scores
    retrieval_relevance = _compute_retrieval_relevance(chunks)

    # 2. Faithfulness: inverse of hallucination score
    faithfulness = max(0.0, 1.0 - hallucination_score)

    # 3. Context Coverage and 4. Coherence (async LLM calls)
    coverage_score, coherence_score = await asyncio.gather(
        _compute_coverage(query, context),
        _compute_coherence(query, answer),
        return_exceptions=True,
    )

    # Fallback if LLM calls fail
    if isinstance(coverage_score, Exception):
        coverage_score = 0.5
    if isinstance(coherence_score, Exception):
        coherence_score = 0.5

    # Weighted formula
    final_score = (
        0.3 * retrieval_relevance
        + 0.3 * faithfulness
        + 0.2 * float(coverage_score)
        + 0.2 * float(coherence_score)
    )
    final_score = round(min(1.0, max(0.0, final_score)), 4)

    # Determine label
    label = _get_confidence_label(final_score)

    return ConfidenceBreakdown(
        retrieval_relevance=round(retrieval_relevance, 4),
        faithfulness=round(faithfulness, 4),
        context_coverage=round(float(coverage_score), 4),
        coherence=round(float(coherence_score), 4),
        final_score=final_score,
        label=label,
    )


def _compute_retrieval_relevance(chunks: list[dict]) -> float:
    """Average relevance score of retrieved chunks."""
    if not chunks:
        return 0.0
    scores = [c.get("score", 0.5) for c in chunks]
    return sum(scores) / len(scores)


async def _compute_coverage(query: str, context: str) -> float:
    """LLM-based context coverage scoring."""
    try:
        result = await call_groq_json(
            COVERAGE_PROMPT.format(query=query, context=context[:2000]),
            system_prompt="You are a context coverage evaluator.",
            max_tokens=100,
            temperature=0.0,
        )
        return float(result.get("coverage_score", 0.5))
    except Exception:
        return 0.5


async def _compute_coherence(query: str, answer: str) -> float:
    """LLM-based answer coherence scoring."""
    try:
        result = await call_groq_json(
            COHERENCE_PROMPT.format(query=query, answer=answer[:1000]),
            system_prompt="You are an answer quality evaluator.",
            max_tokens=100,
            temperature=0.0,
        )
        return float(result.get("coherence_score", 0.5))
    except Exception:
        return 0.5


def _get_confidence_label(score: float) -> ConfidenceLabel:
    """Map confidence score to label."""
    if score >= settings.CONFIDENCE_THRESHOLD_HIGH:
        return ConfidenceLabel.HIGH
    elif score >= settings.CONFIDENCE_THRESHOLD_MEDIUM:
        return ConfidenceLabel.MEDIUM
    elif score >= settings.CONFIDENCE_THRESHOLD_LOW:
        return ConfidenceLabel.LOW
    else:
        return ConfidenceLabel.VERY_LOW