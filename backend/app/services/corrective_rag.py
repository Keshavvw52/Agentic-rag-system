"""
Corrective RAG (CRAG) implementation:
Evaluates each retrieved chunk, classifies quality, and decides whether to
proceed, refine & retry, or trigger fallback.
"""

from app.schemas.schemas import ChunkLabel
from app.services.groq_client import call_groq_json, call_groq

EVAL_SYSTEM = """You are a retrieval quality evaluator.
For each text chunk, determine if it is relevant to answering the query.
Respond with valid JSON only."""

EVAL_PROMPT = """Query: "{query}"

Text chunk:
---
{chunk}
---

Evaluate relevance. Respond with JSON:
{{
  "label": "CORRECT|AMBIGUOUS|INCORRECT",
  "relevance_score": <float 0.0-1.0>,
  "reasoning": "<brief reason>"
}}

Labels:
- CORRECT: Chunk is directly relevant and useful for answering the query
- AMBIGUOUS: Chunk is partially relevant or tangentially related
- INCORRECT: Chunk is not relevant to the query"""

QUERY_REFINEMENT_PROMPT = """Original query: "{query}"

These are the search results so far (partially relevant):
{chunks_preview}

Refine the query to be more specific and targeted to find better information.
Return only the refined query text, nothing else."""


async def evaluate_retrieval(
    query: str,
    chunks: list[dict],
) -> tuple[list[ChunkLabel], list[float]]:
    """
    Evaluate each chunk's relevance using LLM-as-judge.
    Returns (labels, scores) for each chunk.
    """
    if not chunks:
        return [], []

    labels = []
    scores = []

    # Evaluate each chunk (batch for efficiency, but one at a time for accuracy)
    import asyncio
    tasks = [_evaluate_chunk(query, chunk["text"]) for chunk in chunks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            labels.append(ChunkLabel.AMBIGUOUS)
            scores.append(0.5)
        else:
            label, score = result
            labels.append(label)
            scores.append(score)

    return labels, scores


async def _evaluate_chunk(query: str, chunk_text: str) -> tuple[ChunkLabel, float]:
    """Evaluate a single chunk."""
    try:
        # Truncate very long chunks for evaluation
        truncated = chunk_text[:500] if len(chunk_text) > 500 else chunk_text

        result = await call_groq_json(
            EVAL_PROMPT.format(query=query, chunk=truncated),
            system_prompt=EVAL_SYSTEM,
            max_tokens=150,
            temperature=0.0,
        )

        label_str = result.get("label", "AMBIGUOUS").upper()
        try:
            label = ChunkLabel(label_str)
        except ValueError:
            label = ChunkLabel.AMBIGUOUS

        score = float(result.get("relevance_score", 0.5))
        return label, score

    except Exception:
        return ChunkLabel.AMBIGUOUS, 0.5


def decide_crag_action(labels: list[ChunkLabel]) -> str:
    """
    Determine action based on chunk label distribution.
    Returns: 'PROCEED', 'RETRY', or 'FALLBACK'
    """
    if not labels:
        return "FALLBACK"

    correct = labels.count(ChunkLabel.CORRECT)
    ambiguous = labels.count(ChunkLabel.AMBIGUOUS)
    incorrect = labels.count(ChunkLabel.INCORRECT)
    total = len(labels)

    correct_ratio = correct / total
    incorrect_ratio = incorrect / total

    if correct_ratio >= 0.5:
        return "PROCEED"
    elif incorrect_ratio >= 0.6:
        return "FALLBACK"
    else:
        return "RETRY"


async def refine_query(query: str, chunks: list[dict]) -> str:
    """Use LLM to generate a more targeted query based on retrieved chunks."""
    chunks_preview = "\n".join([f"- {c['text'][:150]}..." for c in chunks[:3]])

    refined = await call_groq(
        QUERY_REFINEMENT_PROMPT.format(query=query, chunks_preview=chunks_preview),
        system_prompt="You are a search query optimization expert.",
        max_tokens=100,
        temperature=0.2,
    )
    return refined.strip() or query


def filter_relevant_chunks(
    chunks: list[dict],
    labels: list[ChunkLabel],
    scores: list[float],
) -> list[dict]:
    """
    Keep only CORRECT and high-scoring AMBIGUOUS chunks.
    Extract relevant sentences from AMBIGUOUS chunks.
    """
    filtered = []
    for chunk, label, score in zip(chunks, labels, scores):
        if label == ChunkLabel.CORRECT:
            filtered.append({**chunk, "crag_label": label.value, "crag_score": score})
        elif label == ChunkLabel.AMBIGUOUS and score >= 0.4:
            # Keep but mark as ambiguous
            filtered.append({**chunk, "crag_label": label.value, "crag_score": score})
        # INCORRECT chunks are discarded

    return filtered