import json
import asyncio
from typing import Any, Optional
from groq import AsyncGroq
from app.config.settings import settings

_groq_client: AsyncGroq | None = None


def get_groq_client() -> AsyncGroq:
    global _groq_client
    if _groq_client is None:
        _groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)
    return _groq_client


async def call_groq(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant.",
    max_tokens: int = 1000,
    temperature: float = 0.1,
    model: Optional[str] = None,
    retries: int = 3,
) -> str:
    """Basic LLM call returning text."""
    client = get_groq_client()
    model = model or settings.GROQ_MODEL

    for attempt in range(retries):
        try:
            response = await client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if attempt == retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)
    return ""


async def call_groq_json(
    prompt: str,
    system_prompt: str = "You are a helpful AI assistant. Always respond with valid JSON.",
    max_tokens: int = 1000,
    temperature: float = 0.1,
    model: Optional[str] = None,
) -> dict[str, Any]:
    """LLM call that parses and returns JSON."""
    json_system = f"{system_prompt}\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, no code fences."
    raw = await call_groq(prompt, json_system, max_tokens, temperature, model)

    # Clean any markdown fencing
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try to extract JSON object from the response
        import re
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise ValueError(f"Could not parse JSON from LLM response: {raw[:200]}")


async def call_groq_with_context(
    query: str,
    context: str,
    system_prompt: str,
    max_tokens: int = 1500,
    temperature: float = 0.1,
) -> str:
    """Generate an answer given a query and retrieved context."""
    prompt = f"""CONTEXT:
{context}

QUESTION: {query}

Answer based on the context above."""

    return await call_groq(prompt, system_prompt, max_tokens, temperature)