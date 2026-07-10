"""Optional YouTube transcript fetch, used to enrich video drafts.

Best-effort only: many videos have no transcript, or have it disabled, so
callers must tolerate a None return and fall back to title+description.
"""
import logging
import re

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger(__name__)

_VIDEO_ID_RE = re.compile(r"(?:v=|/videos/|youtu\.be/)([\w-]{11})")


def extract_video_id(url: str) -> str | None:
    match = _VIDEO_ID_RE.search(url)
    return match.group(1) if match else None


def get_transcript_text(video_url: str, *, max_chars: int = 4000) -> str | None:
    video_id = extract_video_id(video_url)
    if not video_id:
        return None
    try:
        segments = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "uz", "ru"])
    except (TranscriptsDisabled, NoTranscriptFound):
        return None
    except Exception as exc:
        logger.warning("Transcript fetch failed for %s: %s", video_id, exc)
        return None

    text = " ".join(seg["text"] for seg in segments)
    return text[:max_chars]
