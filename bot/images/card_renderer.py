"""Renders branded PNG cards with Pillow — no scraped source images, ever.

Cards are re-rendered on demand from a draft's card_spec (see
bot/db/repo/drafts.py) rather than stored, so a scheduled draft always picks
up the current brand template.
"""
import io
import logging
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from bot.images import templates as tpl

logger = logging.getLogger(__name__)

_FONTS_DIR = Path(__file__).parent / "fonts"
_FALLBACK_SYSTEM_FONTS = ["arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"]


@lru_cache(maxsize=8)
def _load_font(weight: str, size: int) -> ImageFont.FreeTypeFont:
    filename = "Bold.ttf" if weight == "bold" else "Regular.ttf"
    candidates = [_FONTS_DIR / filename, *_FALLBACK_SYSTEM_FONTS]
    for candidate in candidates:
        try:
            return ImageFont.truetype(str(candidate), size)
        except OSError:
            continue
    logger.warning("No usable .ttf font found (brand font missing from bot/images/fonts/); "
                    "falling back to Pillow's built-in bitmap font — add real fonts before launch.")
    return ImageFont.load_default(size=size)


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    font: ImageFont.FreeTypeFont,
    fill: str,
    x: int,
    y: int,
    max_width: int,
    line_spacing: int,
) -> int:
    """Draws wrapped text, returns the y position after the last line."""
    for line in _wrap_text(draw, text, font, max_width):
        draw.text((x, y), line, font=font, fill=fill)
        y += line_spacing
    return y


def render_quote_card(*, quote_text: str, author: str, translation_uz: str | None) -> bytes:
    style = tpl.PILLAR_STYLE["quote"]
    img = Image.new("RGB", (tpl.CARD_WIDTH, tpl.CARD_HEIGHT), style["background"])
    draw = ImageDraw.Draw(img)
    max_width = tpl.CARD_WIDTH - 2 * tpl.MARGIN

    mark_font = _load_font("bold", 34)
    quote_font = _load_font("bold", 52)
    translation_font = _load_font("regular", 38)
    author_font = _load_font("regular", 32)

    y = tpl.MARGIN
    draw.text((tpl.MARGIN, y), tpl.BRAND_WORDMARK, font=mark_font, fill=style["accent"])
    y += 90

    draw.line([(tpl.MARGIN, y), (tpl.MARGIN + 100, y)], fill=style["accent"], width=6)
    y += 50

    y = _draw_wrapped(
        draw, f'"{quote_text}"', font=quote_font, fill=style["text"],
        x=tpl.MARGIN, y=y, max_width=max_width, line_spacing=64,
    )

    if translation_uz:
        y += 30
        y = _draw_wrapped(
            draw, translation_uz, font=translation_font, fill=style["muted"],
            x=tpl.MARGIN, y=y, max_width=max_width, line_spacing=48,
        )

    author_y = tpl.CARD_HEIGHT - tpl.MARGIN - 40
    draw.text((tpl.MARGIN, author_y), f"— {author}", font=author_font, fill=style["accent"])

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_tip_card(*, body_text: str) -> bytes:
    style = tpl.PILLAR_STYLE["tip"]
    img = Image.new("RGB", (tpl.CARD_WIDTH, tpl.CARD_HEIGHT), style["background"])
    draw = ImageDraw.Draw(img)
    max_width = tpl.CARD_WIDTH - 2 * tpl.MARGIN

    mark_font = _load_font("bold", 34)
    body_font = _load_font("bold", 46)

    y = tpl.MARGIN
    draw.text((tpl.MARGIN, y), tpl.BRAND_WORDMARK, font=mark_font, fill=style["accent"])
    y += 110

    _draw_wrapped(
        draw, body_text, font=body_font, fill=style["text"],
        x=tpl.MARGIN, y=y, max_width=max_width, line_spacing=58,
    )

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def render_card(card_spec: dict) -> bytes:
    kind = card_spec.get("kind")
    if kind == "quote":
        return render_quote_card(
            quote_text=card_spec["quote_text"],
            author=card_spec["author"],
            translation_uz=card_spec.get("translation_uz"),
        )
    if kind == "tip":
        return render_tip_card(body_text=card_spec["body_text"])
    raise ValueError(f"Unknown card_spec kind: {kind!r}")
