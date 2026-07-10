Drop brand font `.ttf` files here, e.g.:

- `Bold.ttf`
- `Regular.ttf`

Pick fonts with full Cyrillic + Uzbek-Latin (apostrophe/o'/g') glyph coverage
if `SCRIPT=cyrillic` will ever be used — Google Fonts' "Inter" or "Manrope"
both cover this. `bot/images/card_renderer.py` looks for these two exact
filenames first, then falls back to common system fonts, then to Pillow's
built-in bitmap font so the bot still runs (with ugly text) if no font is
provided.
