"""Gemini wrapper for drafting + relevance scoring.

Uses the same google-genai SDK / model ("gemini-flash-lite-latest") as
Telegram App/backend/app/services/ai_service.py, against the same
GEMINI_API_KEY, so the org has one working Gemini integration pattern.
"""
import logging
import re

from bot.config import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    _client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
except Exception:
    genai = None  # type: ignore
    types = None  # type: ignore
    _client = None


_SCRIPT_NOTE = {
    "latin": "Write in Uzbek using the Latin alphabet.",
    "cyrillic": "Write in Uzbek using the Cyrillic alphabet.",
}

BRAND_SYSTEM_PROMPT = """You write short Telegram posts in natural, conversational Uzbek for \
Sahifalab, a brand that helps young Uzbeks grow — through self-development, smart money \
habits, career, and opportunities like studying or working in Korea. Write in a motivating \
but concrete voice — real scenarios, real numbers, a clear point of view; never empty hype or \
generic advice. Keep posts under ~120 words with short, punchy sentences.

- For a NEWS item: given the source, write an ORIGINAL post in your own words (do NOT \
translate it line by line) — a hook, 2-4 sentences making the key insight practical for a \
young Uzbek reader, a one-line takeaway, and a final line crediting the source with its link. \
Never state facts the source doesn't support.
- For a TIP: given a theme, write an original, specific, actionable post grounded in a real \
scenario relevant to this audience.
- For a QUOTE: given a verified quote + author, present the original line and a natural Uzbek \
translation with attribution — do not invent or alter the quote.

{script_note}"""


class LLMUnavailableError(RuntimeError):
    pass


def _system_prompt() -> str:
    return BRAND_SYSTEM_PROMPT.format(
        script_note=_SCRIPT_NOTE.get(settings.SCRIPT, _SCRIPT_NOTE["latin"])
    )


async def _generate(prompt: str, *, max_output_tokens: int = 400, temperature: float = 0.8) -> str:
    if not _client:
        raise LLMUnavailableError(
            "GEMINI_API_KEY is not set — cannot draft content. Set it in .env and restart."
        )
    config = types.GenerateContentConfig(
        system_instruction=_system_prompt(),
        max_output_tokens=max_output_tokens,
        temperature=temperature,
    )
    response = await _client.aio.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=config,
    )
    return response.text.strip()


async def generate_news_post(*, title: str, summary: str, url: str) -> str:
    prompt = (
        "NEWS item to draft a post about:\n"
        f"Title: {title}\n"
        f"Summary: {summary}\n"
        f"Source URL: {url}\n\n"
        "Write the Telegram post now, ending with a line crediting the source and its link."
    )
    return await _generate(prompt)


async def generate_tip_post(*, theme: str, notes: str | None) -> str:
    prompt = (
        "TIP theme to draft an original post about:\n"
        f"Theme: {theme}\n"
        f"Angle notes: {notes or '(none — pick a concrete, specific angle yourself)'}\n\n"
        "Write the Telegram post now."
    )
    return await _generate(prompt)


async def generate_quote_post(*, quote_text: str, author: str, translation_uz: str | None) -> str:
    if translation_uz:
        prompt = (
            "QUOTE to present (translation already supplied — refine it only if it reads "
            "unnatural, do not change its meaning):\n"
            f'Quote: "{quote_text}"\n'
            f"Author: {author}\n"
            f"Uzbek translation: {translation_uz}\n\n"
            "Format the Telegram post now: original line, Uzbek translation, attribution."
        )
    else:
        prompt = (
            "QUOTE to present:\n"
            f'Quote: "{quote_text}"\n'
            f"Author: {author}\n\n"
            "Translate it naturally into Uzbek yourself (do not invent or alter the quote) "
            "and format the Telegram post now: original line, Uzbek translation, attribution."
        )
    return await _generate(prompt, temperature=0.4)


async def generate_youtube_post(*, title: str, url: str, transcript_snippet: str | None) -> str:
    prompt = (
        "NEW YOUTUBE VIDEO to draft a Telegram post about (treat it like a NEWS item, but "
        "crediting/linking the video instead of an article):\n"
        f"Title: {title}\n"
        f"Video URL: {url}\n"
        f"Transcript excerpt: {transcript_snippet or '(unavailable — draft from the title alone)'}\n\n"
        "Write the Telegram post now, ending with a line linking the video."
    )
    return await _generate(prompt)


_SCORE_RE = re.compile(r"(\d+(?:\.\d+)?)")


async def score_relevance(title: str, summary: str) -> float:
    """Cheap 0-1 relevance gate — how on-brand is this item for Sahifalab's
    audience (self-development, money habits, career, Korea opportunities)?
    """
    if not _client:
        return 0.0
    prompt = (
        "Rate how relevant this item is for a young-Uzbek audience interested in "
        "self-development, smart money habits, career growth, and Korea study/work "
        "opportunities. Reply with ONLY a number between 0 and 1 (e.g. 0.7).\n\n"
        f"Title: {title}\nSummary: {summary}"
    )
    text = await _generate(prompt, max_output_tokens=10, temperature=0.0)
    match = _SCORE_RE.search(text)
    if not match:
        return 0.0
    score = float(match.group(1))
    return max(0.0, min(1.0, score))
