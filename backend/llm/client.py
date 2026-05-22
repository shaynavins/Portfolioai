import json
import os

from api.config import settings
from langchain_google_genai import ChatGoogleGenerativeAI

try:
    from langchain_anthropic import ChatAnthropic
    CLAUDE_AVAILABLE = True
except ImportError:
    CLAUDE_AVAILABLE = False


def create_gemini_llm(*, model: str | None = None, max_tokens: int | None = None):
    return ChatGoogleGenerativeAI(
        model=model or settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=0,
        max_tokens=max_tokens,
    )


def create_claude_llm(*, model: str = "claude-3-5-sonnet-20241022", max_tokens: int | None = None):
    """Create Claude LLM. Requires ANTHROPIC_API_KEY in environment."""
    if not CLAUDE_AVAILABLE:
        raise ImportError("langchain-anthropic is not installed")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    return ChatAnthropic(
        model=model,
        api_key=api_key,
        temperature=0,
        max_tokens=max_tokens or 4096,
    )


def parse_json_response(response) -> dict:
    text = _extract_text(response.content).strip()

    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start_positions = [pos for pos in (text.find("{"), text.find("[")) if pos != -1]
        end_positions = [pos for pos in (text.rfind("}"), text.rfind("]")) if pos != -1]
        if start_positions and end_positions:
            candidate = text[min(start_positions): max(end_positions) + 1]
            return json.loads(candidate)
        raise


def _extract_text(content) -> str:
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("text"):
                parts.append(item["text"])
        return "\n".join(parts)

    return str(content)
