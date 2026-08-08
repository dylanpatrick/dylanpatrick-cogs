"""Dependency-free helpers for the AskChatGPT cog."""

from __future__ import annotations

import hashlib
import hmac
import re
import unicodedata


def strip_bot_mentions(content: str, bot_id: int) -> str:
    """Remove only exact mentions of the bot from a Discord message."""

    pattern = re.compile(rf"<@!?{re.escape(str(bot_id))}>")
    return pattern.sub("", content).strip()


def normalize_profile(text: str) -> str:
    """Normalize a self-written profile without applying a length policy."""

    cleaned = []
    for character in text:
        if character.isspace() or unicodedata.category(character).startswith("C"):
            cleaned.append(" ")
        else:
            cleaned.append(character)
    return " ".join("".join(cleaned).split())


def truncate_text(text: str, limit: int) -> str:
    """Return text no longer than limit, adding an ASCII ellipsis when possible."""

    if limit <= 0:
        return ""
    if len(text) <= limit:
        return text
    if limit <= 3:
        return text[:limit]
    return f"{text[: limit - 3]}..."


def safety_identifier(user_id: int, salt: str) -> str:
    """Create a stable, pseudonymous OpenAI safety identifier."""

    return hmac.new(
        salt.encode("utf-8"),
        str(user_id).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
