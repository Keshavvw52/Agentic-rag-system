"""
Fallback chain: when document retrieval fails, gracefully escalate through:
Level 1: Retry with alternative strategy (handled in graph)
Level 2: Web search (Tavily or DuckDuckGo)
Level 3: LLM general knowledge
Level 4: Abstain with explanation
"""

from app.schemas.schemas import AnswerSource
from app.services.groq_client import call_groq
from app.config.settings import settings

WEB_SEARCH_SYSTEM = """You are a helpful assistant. You have access to web search results.
Answer the question based on the search results provided. Clearly indicate this information
comes from web search, not from the user's documents."""

LLM_KNOWLEDGE_SYSTEM = """You are a helpful assistant answering from general knowledge.
IMPORTANT: This answer comes from your general training knowledge, NOT from the user's documents.
Clearly state this limitation. Be accurate but acknowledge uncertainty."""


async def fallback_web_search(query: str) -> tuple[str, AnswerSource, list[dict]]:
    """
    Level 2 fallback: search the web for an answer.
    Returns (answer, source, web_results)
    """
    web_results = []

    if settings.USE_TAVILY and settings.TAVILY_API_KEY:
        web_results = await _tavily_search(query)
    else:
        web_results = await _duckduckgo_search(query)

    if not web_results:
        return "", AnswerSource.WEB_SEARCH, []

    # Format results for LLM
    results_text = "\n\n".join([
        f"Source: {r.get('url', 'Web')}\n{r.get('content', r.get('snippet', ''))}"
        for r in web_results[:5]
    ])

    answer = await call_groq(
        f"Web search results for: {query}\n\n{results_text}\n\nAnswer the question based on these results.",
        system_prompt=WEB_SEARCH_SYSTEM,
        max_tokens=1000,
        temperature=0.1,
    )

    return answer, AnswerSource.WEB_SEARCH, web_results


async def fallback_llm_knowledge(query: str) -> tuple[str, AnswerSource]:
    """
    Level 3 fallback: use LLM's general knowledge.
    """
    answer = await call_groq(
        f"Question: {query}\n\nAnswer from your general knowledge. Start your response with: 'Based on general knowledge (not from your documents):'",
        system_prompt=LLM_KNOWLEDGE_SYSTEM,
        max_tokens=1000,
        temperature=0.2,
    )
    return answer, AnswerSource.GENERAL_KNOWLEDGE


def fallback_abstain(query: str, retrieval_attempts: list[str]) -> tuple[str, AnswerSource]:
    """
    Level 4 fallback: honest 'I don't know' response.
    """
    attempts_text = "\n".join(f"- {a}" for a in retrieval_attempts)
    answer = (
        f"I cannot reliably answer this question based on the available documents.\n\n"
        f"**What I searched for:**\n{attempts_text}\n\n"
        f"**Why I could not answer:** The uploaded documents do not appear to contain "
        f"sufficient information to answer: '{query}'\n\n"
        f"**Suggestions:** Try uploading documents that are more relevant to this topic, "
        f"or rephrase your question if you believe the information should be in the uploaded documents."
    )
    return answer, AnswerSource.ABSTAINED


async def _tavily_search(query: str) -> list[dict]:
    """Search using Tavily API."""
    try:
        from tavily import AsyncTavilyClient
        client = AsyncTavilyClient(api_key=settings.TAVILY_API_KEY)
        response = await client.search(query, max_results=5)
        return response.get("results", [])
    except Exception as e:
        print(f"Tavily search failed: {e}")
        return []


async def _duckduckgo_search(query: str) -> list[dict]:
    """Search using DuckDuckGo (no API key required)."""
    try:
        from duckduckgo_search import DDGS
        import asyncio

        def _search():
            with DDGS() as ddgs:
                return list(ddgs.text(query, max_results=5))

        results = await asyncio.get_event_loop().run_in_executor(None, _search)
        return [
            {"content": r.get("body", ""), "url": r.get("href", ""), "title": r.get("title", "")}
            for r in results
        ]
    except Exception as e:
        print(f"DuckDuckGo search failed: {e}")
        return []