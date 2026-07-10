"""Relevance scoring for ingested items (0-1) — a cheap gate before we spend
an LLM call drafting a full post. Uses the same Gemini client as drafting,
but with a tiny prompt and no image/card generation.
"""
import logging

from bot.drafting.llm_client import score_relevance as _llm_score_relevance

logger = logging.getLogger(__name__)


async def score_item(title: str, summary: str | None) -> float:
    try:
        return await _llm_score_relevance(title, summary or "")
    except Exception as exc:
        logger.warning("Relevance scoring failed (%s) — defaulting to 0.0", exc)
        return 0.0
