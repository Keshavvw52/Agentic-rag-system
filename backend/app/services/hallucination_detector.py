"""
Hallucination detection system:
1. Extract factual claims from generated answer
2. Verify each claim against retrieved context
3. Calculate hallucination score
4. Trigger re-generation if score exceeds threshold
"""

import asyncio
from app.schemas.schemas import ClaimResult, ClaimVerification
from app.services.groq_client import call_groq_json, call_groq_with_context, call_groq
from app.config.settings import settings

CLAIM_EXTRACTION_PROMPT = """Extract ALL factual claims from this answer as a JSON list.

Answer:
{answer}

A factual claim is any specific assertion of fact (numbers, names, dates, percentages, statements of fact).
Break compound claims into individual atomic claims.

Respond with JSON:
{{
  "claims": ["claim 1", "claim 2", "claim 3"]
}}

If there are no factual claims, return: {{"claims": []}}"""

CLAIM_VERIFICATION_PROMPT = """Verify if this claim is supported by the context.

Claim: "{claim}"

Context:
---
{context}
---

Respond with JSON:
{{
  "status": "SUPPORTED|NOT_SUPPORTED|CONTRADICTED",
  "confidence": <float 0.0-1.0>,
  "supporting_text": "<relevant quote from context, or null if not found>"
}}

Labels:
- SUPPORTED: Claim is directly supported by the context
- NOT_SUPPORTED: Claim is not mentioned or verifiable from context (potential hallucination)
- CONTRADICTED: Context explicitly contradicts the claim"""

REGENERATION_SYSTEM_PROMPT = """You are a precise, factual AI assistant.
CRITICAL INSTRUCTIONS:
1. Answer ONLY based on the provided context
2. Do NOT add any information not explicitly stated in the context
3. If information is not in the context, say "The provided documents do not contain information about this"
4. Do not speculate, infer, or assume
5. Be direct and accurate"""

REGENERATION_PROMPT = """Answer this question based STRICTLY on the context provided.

Context:
{context}

Question: {query}

Previous answer had these hallucinated/unsupported claims - DO NOT include them:
{hallucinated_claims}

Answer only what is explicitly supported by the context above:"""


async def extract_claims(answer: str) -> list[str]:
    """Extract all factual claims from the generated answer."""
    if not answer or len(answer.strip()) < 20:
        return []

    try:
        result = await call_groq_json(
            CLAIM_EXTRACTION_PROMPT.format(answer=answer),
            system_prompt="You are a fact extraction expert. Extract atomic factual claims from text.",
            max_tokens=500,
            temperature=0.0,
        )
        claims = result.get("claims", [])
        return [c.strip() for c in claims if c.strip()]
    except Exception:
        return []


async def verify_claims(
    claims: list[str],
    context: str,
) -> list[ClaimResult]:
    """Verify each claim against the retrieved context."""
    if not claims:
        return []

    # Verify claims concurrently
    tasks = [_verify_single_claim(claim, context) for claim in claims]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    claim_results = []
    for claim, result in zip(claims, results):
        if isinstance(result, Exception):
            claim_results.append(ClaimResult(
                claim=claim,
                status=ClaimVerification.NOT_SUPPORTED,
                confidence=0.0,
            ))
        else:
            claim_results.append(result)

    return claim_results


async def _verify_single_claim(claim: str, context: str) -> ClaimResult:
    """Verify a single claim against context."""
    # Truncate context for verification
    context_truncated = context[:3000] if len(context) > 3000 else context

    try:
        result = await call_groq_json(
            CLAIM_VERIFICATION_PROMPT.format(
                claim=claim,
                context=context_truncated,
            ),
            system_prompt="You are a fact verification expert. Check if claims are supported by context.",
            max_tokens=200,
            temperature=0.0,
        )

        status_str = result.get("status", "NOT_SUPPORTED").upper()
        try:
            status = ClaimVerification(status_str)
        except ValueError:
            status = ClaimVerification.NOT_SUPPORTED

        return ClaimResult(
            claim=claim,
            status=status,
            supporting_chunk=result.get("supporting_text"),
            confidence=float(result.get("confidence", 0.5)),
        )
    except Exception:
        return ClaimResult(
            claim=claim,
            status=ClaimVerification.NOT_SUPPORTED,
            confidence=0.0,
        )


def calculate_hallucination_score(claim_results: list[ClaimResult]) -> float:
    """
    hallucination_score = (unsupported + contradicted) / total_claims
    Score 0 = no hallucinations, 1 = fully hallucinated.
    """
    if not claim_results:
        return 0.0

    unsupported = sum(
        1 for c in claim_results
        if c.status in (ClaimVerification.NOT_SUPPORTED, ClaimVerification.CONTRADICTED)
    )
    return round(unsupported / len(claim_results), 4)


async def regenerate_answer(
    query: str,
    context: str,
    claim_results: list[ClaimResult],
) -> str:
    """
    Re-generate the answer with stricter grounding instructions,
    explicitly avoiding previously hallucinated claims.
    """
    hallucinated = [
        c.claim for c in claim_results
        if c.status in (ClaimVerification.NOT_SUPPORTED, ClaimVerification.CONTRADICTED)
    ]

    hallucinated_list = "\n".join(f"- {c}" for c in hallucinated) if hallucinated else "None identified"

    new_answer = await call_groq(
        REGENERATION_PROMPT.format(
            context=context,
            query=query,
            hallucinated_claims=hallucinated_list,
        ),
        system_prompt=REGENERATION_SYSTEM_PROMPT,
        max_tokens=1500,
        temperature=0.0,
    )
    return new_answer.strip()