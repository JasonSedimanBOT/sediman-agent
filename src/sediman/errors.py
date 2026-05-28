from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ErrorInfo:
    code: str
    message: str
    suggestion: str | None = None


_ERROR_PATTERNS = re.compile(
    r"(?:error|failed|timeout|not found|exception|unreachable|refused|denied)",
    re.IGNORECASE,
)


def classify_error(exc: Exception) -> ErrorInfo:
    msg = str(exc)
    exc_type = type(exc).__name__

    if "AuthenticationError" in exc_type or "auth" in msg.lower() or "api_key" in msg.lower() or "invalid api key" in msg.lower() or "incorrect api key" in msg.lower():
        return ErrorInfo("AUTH_ERROR", "Invalid or missing API key.", "Set your API key: export OPENAI_API_KEY=sk-...")

    if "ConnectionError" in exc_type or "ConnectionRefused" in msg or "connect" in msg.lower():
        return ErrorInfo("CONNECTION_ERROR", "Cannot connect to the LLM provider.", "Check your network connection and API base URL.")

    if "timeout" in msg.lower() or "TimeoutError" in exc_type:
        return ErrorInfo("TIMEOUT", "The request timed out.", "Try again, or use a simpler task.")

    if "RateLimitError" in exc_type or "rate" in msg.lower():
        return ErrorInfo("RATE_LIMIT", "Rate limit exceeded.", "Wait a moment and try again.")

    if "not found" in msg.lower() and "browser" in msg.lower():
        return ErrorInfo("BROWSER_NOT_FOUND", "Browser not found.", "Install Chromium or run with a different browser.")

    if "ModuleNotFoundError" in exc_type:
        return ErrorInfo("MISSING_DEP", f"Missing dependency: {msg}", "Run: pip install sediman-browse")

    return ErrorInfo("INTERNAL_ERROR", msg[:300] if msg else exc_type, None)


def looks_like_error(text: str) -> bool:
    if not text:
        return True
    matches = _ERROR_PATTERNS.findall(text)
    if len(matches) >= 2:
        return True
    first_line = text.split("\n")[0].lower()
    return bool(re.match(r"^(error|failed|exception|traceback)", first_line))
