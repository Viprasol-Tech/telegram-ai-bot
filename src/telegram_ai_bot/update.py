"""Parsing of raw Telegram update dictionaries into typed values.

A Telegram ``Update`` is a JSON object delivered by long-polling or webhook.
We only need the message text and its originating chat, so :func:`parse_update`
reduces the nested payload to a flat, typed :class:`Update` and splits any
leading ``/command`` (with optional ``@botname`` suffix) from its arguments.

Part of Telegram AI Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class Update:
    """A normalised inbound message.

    Attributes:
        chat_id: Identifier of the chat the message belongs to.
        text: Full message text (empty string when no text was present).
        command: Bare command name without the leading ``/`` and without any
            ``@botname`` suffix, lower-cased; ``None`` when the message is not
            a command.
        args: Whitespace-split arguments that followed the command. Always an
            empty list for non-command messages.
    """

    chat_id: int
    text: str
    command: str | None = None
    args: list[str] = field(default_factory=list)

    @property
    def is_command(self) -> bool:
        """Whether this update represents a ``/command`` message."""
        return self.command is not None


class UpdateError(ValueError):
    """Raised when an update dict is missing required fields or malformed."""


def _extract_message(update: dict[str, Any]) -> dict[str, Any]:
    """Return the message-like sub-dict from a raw update.

    Telegram delivers edits under ``edited_message`` and channel posts under
    ``channel_post``; we treat them uniformly. Raises :class:`UpdateError`
    when none is present.
    """
    for key in ("message", "edited_message", "channel_post", "edited_channel_post"):
        candidate = update.get(key)
        if isinstance(candidate, dict):
            return candidate
    raise UpdateError("update has no message, edited_message or channel_post")


def parse_command(text: str) -> tuple[str | None, list[str]]:
    """Split ``text`` into a command name and its arguments.

    A command is a token at the start of the text beginning with ``/``. An
    optional ``@botname`` mention is stripped from the command. Returns
    ``(None, [])`` when the text is not a command.

    >>> parse_command("/echo @MyBot hello world")
    ('echo', ['hello', 'world'])
    >>> parse_command("just chatting")
    (None, [])
    """
    stripped = text.strip()
    if not stripped.startswith("/"):
        return None, []
    parts = stripped.split()
    head = parts[0][1:]  # drop the leading '/'
    command = head.split("@", 1)[0].lower()
    if not command:
        return None, []
    return command, parts[1:]


def parse_update(update: dict[str, Any]) -> Update:
    """Normalise a raw Telegram update dict into an :class:`Update`.

    Args:
        update: The raw update object as delivered by the Telegram Bot API.

    Returns:
        A typed :class:`Update` with command/args already split out.

    Raises:
        UpdateError: If no message is present or the chat id is missing.
    """
    message = _extract_message(update)

    chat = message.get("chat")
    if not isinstance(chat, dict) or "id" not in chat:
        raise UpdateError("message is missing chat.id")
    chat_id_raw = chat["id"]
    if not isinstance(chat_id_raw, int) or isinstance(chat_id_raw, bool):
        raise UpdateError("chat.id must be an integer")

    text_raw = message.get("text", "")
    text = text_raw if isinstance(text_raw, str) else ""

    command, args = parse_command(text)
    return Update(chat_id=chat_id_raw, text=text, command=command, args=args)
