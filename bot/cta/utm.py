"""UTM-tagged links for CTAs — click tracking without a dedicated shortener
service, since the bot is long-polling only and has no public HTTP endpoint.
"""
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from bot.config import settings


def build_utm_link(path: str, *, campaign: str) -> str:
    """path can be a full URL or a path relative to settings.UTM_BASE_URL."""
    base = path if path.startswith("http") else settings.UTM_BASE_URL.rstrip("/") + "/" + path.lstrip("/")
    parsed = urlparse(base)
    query = dict(parse_qsl(parsed.query))
    query.update({
        "utm_source": settings.UTM_SOURCE,
        "utm_medium": settings.UTM_MEDIUM,
        "utm_campaign": campaign,
    })
    return urlunparse(parsed._replace(query=urlencode(query)))
