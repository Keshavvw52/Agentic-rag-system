"""Stats and health endpoints."""

from fastapi import APIRouter, Depends
from app.auth.jwt_handler import get_current_user
from app.db.mongodb import get_database

router = APIRouter()


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_user)):
    db = get_database()
    user_id = current_user["id"]

    queries = await db.queries.find(
        {"user_id": user_id, "is_simple": {"$ne": True}}
    ).to_list(None)

    docs = await db.documents.count_documents({"user_id": user_id})

    if not queries:
        return {
            "total_queries": 0,
            "total_documents": docs,
            "avg_confidence": 0,
            "avg_hallucination_score": 0,
            "fallback_rate": 0,
            "retry_rate": 0,
            "avg_latency_ms": 0,
            "query_type_distribution": {},
            "strategy_distribution": {},
        }

    total = len(queries)
    avg_conf = sum(q.get("confidence_score", 0) for q in queries) / total
    avg_hall = sum(q.get("hallucination_score", 0) for q in queries) / total
    fallbacks = sum(1 for q in queries if q.get("fallback_used"))
    retries = sum(1 for q in queries if q.get("retries", 0) > 0)
    avg_lat = sum(q.get("total_duration_ms", 0) for q in queries) / total

    type_dist: dict[str, int] = {}
    strat_dist: dict[str, int] = {}
    for q in queries:
        qt = q.get("query_type", "UNKNOWN")
        type_dist[qt] = type_dist.get(qt, 0) + 1
        rs = q.get("retrieval_strategy", "UNKNOWN")
        strat_dist[rs] = strat_dist.get(rs, 0) + 1

    return {
        "total_queries": total,
        "total_documents": docs,
        "avg_confidence": round(avg_conf, 4),
        "avg_hallucination_score": round(avg_hall, 4),
        "fallback_rate": round(fallbacks / total, 4),
        "retry_rate": round(retries / total, 4),
        "avg_latency_ms": round(avg_lat, 2),
        "query_type_distribution": type_dist,
        "strategy_distribution": strat_dist,
    }