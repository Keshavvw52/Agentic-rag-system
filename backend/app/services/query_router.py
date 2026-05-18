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
{history_block}

Respond with JSON:
{{
  "query_type": "FACTUAL|ANALYTICAL|SUMMARIZATION|CONVERSATIONAL|OUT_OF_SCOPE",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one sentence explaining why>"
}}"""


def _looks_like_memory_query(query: str) -> bool:
    normalized = " ".join(query.lower().split())

    direct_markers = (
        "previous question",
        "previous questions",
        "previous query",
        "previous queries",
        "last query",
        "last queries",
        "earlier query",
        "earlier queries",
        "conversation history",
        "what did i ask",
        "what was my last",
        "what were my last",
        "questions i asked",
        "queries i asked",
    )
    if any(marker in normalized for marker in direct_markers):
        return True

    has_last_or_previous = any(word in normalized for word in ("last", "previous", "earlier"))
    has_question_or_query = any(word in normalized for word in ("question", "questions", "query", "queries"))
    has_first_person = any(phrase in normalized for phrase in ("i asked", "have i asked", "my"))

    return has_last_or_previous and has_question_or_query and has_first_person


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
        history_block = ""
        if conversation_history:
            recent_history = "\n".join(
                f"- {msg.get('role', 'user')}: {msg.get('content', '')}"
                for msg in conversation_history[-6:]
            )
            history_block = (
                "\nRecent conversation history is available. "
                "If the query refers to earlier questions, previous answers, "
                "or chat context, prefer CONVERSATIONAL.\n"
                f"Conversation history:\n{recent_history}\n"
            )

        result = await call_groq_json(
            CLASSIFICATION_PROMPT.format(query=query, history_block=history_block),
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

        # Lightweight override for explicit memory-style follow-ups.
        if conversation_history and _looks_like_memory_query(query):
            query_type = QueryType.CONVERSATIONAL
            confidence = max(confidence, 0.9)
            reasoning = "The query explicitly refers to earlier turns, so it should use conversational memory."

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
