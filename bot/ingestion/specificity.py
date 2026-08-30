"""Specificity gate — rejects items that are all headline, no data.

Distinct from bot/ingestion/relevance.py (which asks "is this on-brand for
Sahifalab's audience?"): this asks "does this actually contain a concrete
number, stat, or scenario worth building a post around?" A relevant-but-vague
item — common with thin RSS summaries or aggregator snippets — should be
rejected here rather than reaching the LLM, which will otherwise happily pad
it out with generic filler ("experts say...", "many people struggle with...").

This is a cheap regex heuristic, not an LLM call — it runs on every item
that passes relevance, so it needs to be fast and free.
"""
import re

_NUMERIC_PATTERNS = [
    re.compile(r"\d+(?:[.,]\d+)?\s?%"),                                          # percentages
    re.compile(r"\bn\s?=\s?\d+", re.IGNORECASE),                                  # sample sizes
    re.compile(
        r"\d[\d,.]*\s+(participants|people|respondents|students|adults|"
        r"odam|nafar|kishi|ishtirokchi)",
        re.IGNORECASE,
    ),
    re.compile(r"[$€£]\s?\d|\d+\s?(USD|UZS|EUR|so'?m|dollar|rubl|won)", re.IGNORECASE),
    re.compile(r"\b(19|20)\d{2}\b"),                                              # a year
    re.compile(r"\d+(?:[.,]\d+)?\s?(million|billion|ming|mln|mlrd)", re.IGNORECASE),
]

# Below this length, treat the item as headline-only regardless of matches —
# a single stray digit in a 40-character teaser isn't "data-dense".
MIN_LENGTH_FOR_TRUST = 200


def score(text: str | None) -> tuple[float, str | None]:
    """Returns (specificity_score in 0-1, reject_reason or None-if-passed)."""
    if not text or not text.strip():
        return 0.0, "no_content"

    matches = sum(1 for pattern in _NUMERIC_PATTERNS if pattern.search(text))
    specificity_score = min(1.0, matches / 3)

    if len(text.strip()) < MIN_LENGTH_FOR_TRUST and matches == 0:
        return 0.0, "headline_only_no_data"
    if matches == 0:
        return 0.1, "no_concrete_data"
    return specificity_score, None
