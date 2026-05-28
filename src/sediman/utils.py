from __future__ import annotations

import datetime


def format_conversation_context(
    messages: list[dict[str, str]],
    limit: int = 10,
    max_chars: int = 200,
) -> str:
    lines = []
    for msg in messages[-limit:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content'][:max_chars]}")
    return "\n".join(lines)


def relative_time(timestamp: str, now: datetime.datetime | None = None) -> str:
    if now is None:
        now = datetime.datetime.now(datetime.timezone.utc)
    try:
        if "T" in timestamp:
            ts = datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        else:
            ts = datetime.datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        delta = now - ts
        seconds = int(delta.total_seconds())
        if seconds < 60:
            return "just now"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 30:
            return f"{days}d ago"
        return timestamp[:10]
    except Exception:
        return timestamp
