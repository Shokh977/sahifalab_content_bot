"""Message templates for admin draft previews."""
import asyncpg

PILLAR_LABELS = {
    "finance": "💰 FINANCE",
    "news": "🗞 NEWS",
    "tip": "💡 TIP",
    "quote": "❝ QUOTE",
    "youtube": "▶️ YOUTUBE",
    "poll": "📊 POLL",
}


def render_admin_preview(draft: asyncpg.Record) -> str:
    label = PILLAR_LABELS.get(draft["pillar"], draft["pillar"].upper())
    header = f"{label} · Draft #{draft['id']}"
    if draft["edit_count"]:
        header += f" · tahrirlangan ({draft['edit_count']}x)"

    if draft["pillar"] == "poll":
        options = draft["poll_options"]
        if isinstance(options, str):
            import json
            options = json.loads(options)
        body = draft["poll_question"] + "\n" + "\n".join(f"• {o}" for o in options)
    else:
        body = draft["body_text"] or "(matn yo'q)"

    return f"{header}\n\n{body}"
