"""Outbound message transport.

The bot logic never talks to the network directly; it sends replies through a
:class:`Transport`. A real implementation would POST to the Telegram Bot API's
``sendMessage`` endpoint, but the bundled :class:`InMemoryTransport` simply
records every reply so the demo and the test-suite run fully offline with no
API token.

Part of Telegram AI Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(slots=True, frozen=True)
class SentMessage:
    """A single outbound reply recorded by a transport."""

    chat_id: int
    text: str


@runtime_checkable
class Transport(Protocol):
    """Protocol for delivering a reply to a chat.

    Any object exposing a compatible ``send_message`` method satisfies this
    protocol; the bot depends only on this surface, never on a concrete client.
    """

    def send_message(self, chat_id: int, text: str) -> SentMessage:
        """Deliver ``text`` to ``chat_id`` and return the sent message."""
        ...


@dataclass(slots=True)
class InMemoryTransport:
    """A :class:`Transport` that records messages instead of sending them.

    Useful for tests and the offline demo. Every call to :meth:`send_message`
    appends to :attr:`sent` and returns the recorded :class:`SentMessage`.
    """

    sent: list[SentMessage] = field(default_factory=list)

    def send_message(self, chat_id: int, text: str) -> SentMessage:
        """Record a reply and return it."""
        message = SentMessage(chat_id=chat_id, text=text)
        self.sent.append(message)
        return message

    def messages_for(self, chat_id: int) -> list[SentMessage]:
        """Return all recorded messages addressed to ``chat_id``."""
        return [m for m in self.sent if m.chat_id == chat_id]

    def clear(self) -> None:
        """Forget all recorded messages."""
        self.sent.clear()
