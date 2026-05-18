"""Evaluation endpoints: hallucination check, batch eval, results comparison."""

from fastapi import APIRouter, Depends
from app.auth.jwt_handler import get_current_user
from app.schemas.schemas import HallucinationEvalRequest, HallucinationEvalResponse, ClaimVerification
from app.services.hallucination_detector import extract_claims, verify_claims, calculate_hallucination_score
from app.db.mongodb import get_database

router = APIRouter()


@router.post("/hallucination", response_model=HallucinationEvalResponse)
async def evaluate_hallucination(
    request: HallucinationEvalRequest,
    current_user: dict = Depends(get_current_user),
):
    """Run hallucination detection on arbitrary answer + context."""
    claims = await extract_claims(request.answer)
    claim_results = await verify_claims(claims, request.context)
    score = calculate_hallucination_score(claim_results)

    return HallucinationEvalResponse(
        claims=claim_results,
        hallucination_score=score,
        total_claims=len(claims),
        supported_claims=sum(1 for c in claim_results if c.status == ClaimVerification.SUPPORTED),
        unsupported_claims=sum(1 for c in claim_results if c.status == ClaimVerification.NOT_SUPPORTED),
        contradicted_claims=sum(1 for c in claim_results if c.status == ClaimVerification.CONTRADICTED),
    )


@router.get("/results")
async def get_eval_results(current_user: dict = Depends(get_current_user)):
    """Get evaluation comparison between agentic and simple RAG queries."""
    db = get_database()

    agentic_queries = await db.queries.find(
        {"user_id": current_user["id"], "is_simple": {"$ne": True}}
    ).sort("created_at", -1).limit(20).to_list(20)

    if not agentic_queries:
        return {"results": [], "summary": {}}

    avg_confidence = sum(q.get("confidence_score", 0) for q in agentic_queries) / len(agentic_queries)
    avg_hallucination = sum(q.get("hallucination_score", 0) for q in agentic_queries) / len(agentic_queries)
    fallback_count = sum(1 for q in agentic_queries if q.get("fallback_used"))

    return {
        "results": [
            {
                "query_id": str(q["_id"]),
                "query": q["query"][:100],
                "confidence_score": q.get("confidence_score", 0),
                "hallucination_score": q.get("hallucination_score", 0),
                "confidence_label": q.get("confidence_label", "UNKNOWN"),
                "fallback_used": q.get("fallback_used", False),
                "retries": q.get("retries", 0),
                "created_at": q["created_at"].isoformat(),
            }
            for q in agentic_queries
        ],
        "summary": {
            "total_queries": len(agentic_queries),
            "avg_confidence": round(avg_confidence, 4),
            "avg_hallucination": round(avg_hallucination, 4),
            "fallback_rate": round(fallback_count / len(agentic_queries), 4),
        },
    }