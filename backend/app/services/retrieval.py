import asyncio
from typing import Optional
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder

from app.config.settings import settings
from app.db.chromadb import get_user_collection, embed_texts
from app.schemas.schemas import RetrievalStrategy

_reranker: CrossEncoder | None = None


def get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = CrossEncoder(settings.RERANKER_MODEL)
    return _reranker


async def retrieve(
    query: str,
    user_id: str,
    strategy: RetrievalStrategy,
    top_k: int = None,
    conversation_history: list[dict] = None,
) -> list[dict]:
    """Route to the appropriate retrieval strategy."""
    top_k = top_k or settings.TOP_K_RETRIEVAL

    if strategy == RetrievalStrategy.HYBRID_RERANK:
        chunks = await hybrid_search(query, user_id, top_k)
        return await rerank(query, chunks, settings.TOP_K_RERANK)

    elif strategy == RetrievalStrategy.MULTI_QUERY:
        return await multi_query_retrieval(query, user_id, top_k)

    elif strategy == RetrievalStrategy.SECTION_BASED:
        return await section_based_retrieval(query, user_id, top_k)

    elif strategy == RetrievalStrategy.CONVERSATIONAL:
        return await conversational_retrieval(query, user_id, top_k, conversation_history)

    else:  # FALLBACK — basic semantic
        return await semantic_search(query, user_id, top_k)


async def semantic_search(query: str, user_id: str, top_k: int) -> list[dict]:
    """Pure vector similarity search."""
    collection = get_user_collection(user_id)
    query_emb = embed_texts([query])[0]

    results = collection.query(
        query_embeddings=[query_emb],
        n_results=min(top_k, collection.count() or 1),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        score = 1 - distance  # cosine → similarity
        chunks.append({
            "text": doc,
            "score": round(score, 4),
            "metadata": results["metadatas"][0][i],
            "source": "semantic",
        })
    return sorted(chunks, key=lambda x: x["score"], reverse=True)


async def bm25_search(query: str, user_id: str, top_k: int) -> list[dict]:
    """BM25 keyword-based search over user's document corpus."""
    collection = get_user_collection(user_id)

    # Fetch all docs for this user
    all_docs = collection.get(include=["documents", "metadatas"])
    if not all_docs["documents"]:
        return []

    texts = all_docs["documents"]
    metadatas = all_docs["metadatas"]

    # Tokenize and build BM25 index
    tokenized = [t.lower().split() for t in texts]
    bm25 = BM25Okapi(tokenized)
    query_tokens = query.lower().split()
    scores = bm25.get_scores(query_tokens)

    # Get top_k results
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    chunks = []
    for idx in top_indices:
        if scores[idx] > 0:
            chunks.append({
                "text": texts[idx],
                "score": round(float(scores[idx]) / (max(scores) + 1e-8), 4),
                "metadata": metadatas[idx],
                "source": "bm25",
            })
    return chunks


async def hybrid_search(query: str, user_id: str, top_k: int) -> list[dict]:
    """Combine semantic and BM25 results with reciprocal rank fusion."""
    semantic_chunks, bm25_chunks = await asyncio.gather(
        semantic_search(query, user_id, top_k),
        bm25_search(query, user_id, top_k),
    )

    # Reciprocal Rank Fusion (RRF)
    scores: dict[str, float] = {}
    text_map: dict[str, dict] = {}
    k = 60  # RRF constant

    for rank, chunk in enumerate(semantic_chunks):
        key = chunk["text"][:200]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        text_map[key] = chunk

    for rank, chunk in enumerate(bm25_chunks):
        key = chunk["text"][:200]
        scores[key] = scores.get(key, 0) + 1 / (k + rank + 1)
        if key not in text_map:
            text_map[key] = chunk

    # Sort by RRF score
    sorted_keys = sorted(scores, key=scores.__getitem__, reverse=True)[:top_k]
    result = []
    for key in sorted_keys:
        chunk = text_map[key].copy()
        chunk["score"] = round(scores[key], 6)
        chunk["source"] = "hybrid"
        result.append(chunk)
    return result


async def rerank(query: str, chunks: list[dict], top_k: int) -> list[dict]:
    """Cross-encoder re-ranking for precision."""
    if not chunks:
        return []

    reranker = get_reranker()
    pairs = [(query, c["text"]) for c in chunks]
    scores = reranker.predict(pairs)

    for i, chunk in enumerate(chunks):
        chunk["rerank_score"] = float(scores[i])

    reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)[:top_k]
    # Normalize rerank scores to 0-1
    if reranked:
        max_s = max(c["rerank_score"] for c in reranked)
        min_s = min(c["rerank_score"] for c in reranked)
        rng = max_s - min_s + 1e-8
        for c in reranked:
            c["score"] = round((c["rerank_score"] - min_s) / rng, 4)
    return reranked


async def multi_query_retrieval(query: str, user_id: str, top_k: int) -> list[dict]:
    """
    Generate multiple query variations and merge results.
    Good for analytical queries needing broad coverage.
    """
    from app.services.groq_client import call_groq

    # Generate 3 query variations
    prompt = f"""Generate 3 different search queries to comprehensively answer: "{query}"
Return only the 3 queries, one per line, no numbering."""

    variations_text = await call_groq(prompt, max_tokens=200, temperature=0.3)
    variations = [q.strip() for q in variations_text.strip().split("\n") if q.strip()]
    variations = variations[:3] + [query]  # always include original

    # Retrieve for all variations concurrently
    all_results = await asyncio.gather(*[
        hybrid_search(q, user_id, top_k // 2) for q in variations
    ])

    # Merge and deduplicate by text content
    seen: set[str] = set()
    merged: list[dict] = []
    for results in all_results:
        for chunk in results:
            key = chunk["text"][:100]
            if key not in seen:
                seen.add(key)
                merged.append(chunk)

    # Re-rank merged results
    if merged:
        merged = await rerank(query, merged, top_k)
    return merged


async def section_based_retrieval(query: str, user_id: str, top_k: int) -> list[dict]:
    """
    Retrieve larger context windows for summarization queries.
    Uses larger chunk retrieval with minimal filtering.
    """
    # For summarization, we want broader coverage — get more chunks
    chunks = await semantic_search(query, user_id, top_k * 2)
    # Group by document and take top chunks per document
    by_doc: dict[str, list] = {}
    for chunk in chunks:
        doc_id = chunk["metadata"].get("document_id", "unknown")
        by_doc.setdefault(doc_id, []).append(chunk)

    # Take top chunks per document evenly
    result = []
    per_doc = max(1, top_k // max(len(by_doc), 1))
    for doc_chunks in by_doc.values():
        result.extend(doc_chunks[:per_doc])

    return result[:top_k]


async def conversational_retrieval(
    query: str, user_id: str, top_k: int, history: list[dict] | None
) -> list[dict]:
    """
    Context-aware retrieval that incorporates chat history.
    Rewrites the query to be standalone before retrieval.
    """
    if not history:
        return await hybrid_search(query, user_id, top_k)

    from app.services.groq_client import call_groq

    # Rewrite query with context
    history_text = "\n".join([
        f"{msg['role'].upper()}: {msg['content']}" for msg in history[-4:]
    ])
    prompt = f"""Given this conversation:
{history_text}

Rewrite this follow-up question as a standalone search query: "{query}"
Return only the rewritten query, nothing else."""

    standalone_query = await call_groq(prompt, max_tokens=100, temperature=0.1)
    standalone_query = standalone_query.strip()

    return await hybrid_search(standalone_query or query, user_id, top_k)