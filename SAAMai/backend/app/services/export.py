"""
export.py
=========
Turns a stored chat into a downloadable file. Markdown, plain text and
JSON are supported out of the box (no extra dependencies); JSON is the
most complete (round-trippable) format, Markdown/TXT are meant for
reading or sharing.
"""

import json

from ..models import Chat


def export_chat(chat: Chat, fmt: str) -> tuple[str, str, str]:
    """Returns (filename, mime_type, content)."""
    fmt = fmt.lower()
    safe_title = "".join(c if c.isalnum() or c in " -_" else "_" for c in chat.title).strip() or "chat"

    if fmt == "json":
        payload = {
            "title": chat.title,
            "model": chat.model,
            "created_at": chat.created_at.isoformat(),
            "messages": [
                {"role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
                for m in chat.messages
            ],
        }
        return f"{safe_title}.json", "application/json", json.dumps(payload, ensure_ascii=False, indent=2)

    if fmt == "txt":
        lines = [f"{m.role.upper()}: {m.content}" for m in chat.messages]
        return f"{safe_title}.txt", "text/plain", "\n\n".join(lines)

    # default: markdown
    lines = [f"# {chat.title}", ""]
    for m in chat.messages:
        speaker = "**Du**" if m.role == "user" else "**SAAMai**"
        lines.append(f"{speaker} ({m.created_at.strftime('%Y-%m-%d %H:%M')}):")
        lines.append(m.content)
        lines.append("")
    return f"{safe_title}.md", "text/markdown", "\n".join(lines)
