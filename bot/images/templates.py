"""Brand colors / layout constants for card rendering.

Placeholder brand colors — swap BRAND_PRIMARY/BRAND_SECONDARY/BRAND_ACCENT for
Sahifalab's real hex values, and drop real font files into bot/images/fonts/
(see that folder's README) once available. Everything here is deliberately
easy to restyle without touching card_renderer.py's layout logic.
"""

CARD_WIDTH = 1080
CARD_HEIGHT = 1080

BRAND_PRIMARY = "#101820"     # background
BRAND_SECONDARY = "#F2A900"   # accent (quote marks, rule line)
BRAND_TEXT = "#FFFFFF"
BRAND_MUTED = "#9AA5B1"

MARGIN = 90

PILLAR_STYLE = {
    "quote": {
        "background": BRAND_PRIMARY,
        "accent": BRAND_SECONDARY,
        "text": BRAND_TEXT,
        "muted": BRAND_MUTED,
    },
    "tip": {
        "background": BRAND_SECONDARY,
        "accent": BRAND_PRIMARY,
        "text": BRAND_PRIMARY,
        "muted": "#4A4A4A",
    },
}

BRAND_WORDMARK = "SAHIFALAB"
