from app.schemas.schemas import QueryType, RetrievalStrategy
from app.services.groq_client import call_groq_json
from app.config.settings import settings


ROUTING_TABLE: dict[QueryType, RetrievalStrategy] = {
    QueryType.FACTUAL: RetrievalStrategy.HYBRID_RERANK,
    QueryType.ANALYTICAL: RetrievalStrategy.MULTI_QUERY,
    QueryType.SUMMARIZATION: RetrievalStrategy.SECTION_BASED,
    QueryType.CONVERSATIONAL: RetrievalStrategy.CONVERSATIONAL,
    QueryType.OUT_OF_SCOPE: RetrievalStrategy.FALLBACK,
}

CLASSIFICATION_SYSTEM_PROMPT = """You are a query classification expert for a RAG system.
Classify the query into exactly one of these types:
- FACTUAL: Looking for a specific fact, number, date, or data point
- ANALYTICAL: Requires reasoning, comparison, or analysis across multiple pieces of information
- SUMMARIZATION: Wants a broad summary or overview of content
- CONVERSATIONAL: Follow-up question referencing previous conversation
- OUT_OF_SCOPE: Cannot be answered from documents (weather, current events, personal info, etc.)

Respond only with valid JSON."""

CLASSIFICATION_PROMPT = """Classify this query: "{query}"

Respond with JSON:
{{
  "query_type": "FACTUAL|ANALYTICAL|SUMMARIZATION|CONVERSATIONAL|OUT_OF_SCOPE",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one sentence explaining why>"
}}"""


async def classify_query(
    query: str,
    conversation_history: list[dict] | None = None,
    user_routing_config: dict | None = None,
) -> tuple[QueryType, float, str, RetrievalStrategy]:
    """
    Classify the query and select the optimal retrieval strategy.

    Returns:
        (query_type, confidence, reasoning, retrieval_strategy)
    """
    try:
        result = await call_groq_json(
            CLASSIFICATION_PROMPT.format(query=query),
            system_prompt=CLASSIFICATION_SYSTEM_PROMPT,
            max_tokens=200,
            temperature=0.0,
        )

        query_type_str = result.get("query_type", "FACTUAL").upper()
        confidence = float(result.get("confidence", 0.5))
        reasoning = result.get("reasoning", "")

        # Validate enum
        try:
            query_type = QueryType(query_type_str)
        except ValueError:
            query_type = QueryType.FACTUAL
            confidence = 0.5

        # If classification is uncertain, use safe default
        if confidence < settings.ROUTING_CONFIDENCE_MIN:
            query_type = QueryType.FACTUAL
            reasoning = f"Low confidence ({confidence:.0%}); defaulting to FACTUAL for safe routing. " + reasoning

        # Apply user's custom routing config if available
        strategy = _select_strategy(query_type, user_routing_config)

        return query_type, confidence, reasoning, strategy

    except Exception as e:
        # Safe fallback
        return (
            QueryType.FACTUAL,
            0.5,
            f"Classification failed, defaulted to FACTUAL: {str(e)}",
            RetrievalStrategy.HYBRID_RERANK,
        )


def _select_strategy(
    query_type: QueryType,
    user_config: dict | None,
) -> RetrievalStrategy:
    """Apply user's custom routing config or default routing table."""
    if user_config:
        config_map = {
            QueryType.FACTUAL: user_config.get("factual_strategy"),
            QueryType.ANALYTICAL: user_config.get("analytical_strategy"),
            QueryType.SUMMARIZATION: user_config.get("summarization_strategy"),
            QueryType.CONVERSATIONAL: user_config.get("conversational_strategy"),
        }
        strategy_str = config_map.get(query_type)
        if strategy_str:
            try:
                return RetrievalStrategy(strategy_str)
            except ValueError:
                pass

    return ROUTING_TABLE.get(query_type, RetrievalStrategy.HYBRID_RERANK)


def get_alternative_strategy(current: RetrievalStrategy) -> RetrievalStrategy:
    """Return an alternative strategy for retry."""
    alternatives = {
        RetrievalStrategy.HYBRID_RERANK: RetrievalStrategy.MULTI_QUERY,
        RetrievalStrategy.MULTI_QUERY: RetrievalStrategy.HYBRID_RERANK,
        RetrievalStrategy.SECTION_BASED: RetrievalStrategy.HYBRID_RERANK,
        RetrievalStrategy.CONVERSATIONAL: RetrievalStrategy.HYBRID_RERANK,
        RetrievalStrategy.FALLBACK: RetrievalStrategy.HYBRID_RERANK,
    }
    return alternatives.get(current, RetrievalStrategy.HYBRID_RERANK)