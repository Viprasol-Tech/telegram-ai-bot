"""The Telegram AI bot core: command handling and pluggable-LLM routing.

:class:`Bot` parses each inbound update, handles ``/start`` and ``/help``
directly, and answers any other text by calling a pluggable ``LLM`` callable
``(prompt) -> reply``. A short per-chat history is maintained so the LLM (real
or fake) can be given recent context, and history is isolated per chat.

The default :func:`echo_llm` is a deterministic fake so everything runs offline
with no API keys. Swap in a real model by passing any ``Callable[[str], str]``.

Part of Telegram AI Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass, field

from telegram_ai_bot.transport import SentMessage, Transport
from telegram_ai_bot.update import Update, parse_update

LLM = Callable[[str], str]
"""A pluggable language model: maps a prompt string to a reply string."""

START_REPLY = (
    "Hello! I am the Telegram AI Bot by Viprasol Tech. "
    "Send me a message and I'll reply. Type /help for commands."
)

HELP_REPLY = (
    "Commands:\n"
    "/start - greet and introduce the bot\n"
    "/help - show this message\n"
    "/reset - clear our conversation history\n"
    "Any other text is answered by the language model."
)


def echo_llm(prompt: str) -> str:
    """A deterministic, offline fake LLM.

    It produces a stable, content-derived reply so demos and tests need no
    network or API key. The reply echoes the user's last line and reports the
    word count, which is enough to prove routing and context-passing work.
    """
    last_line = prompt.strip().splitlines()[-1] if prompt.strip() else ""
    words = len(last_line.split())
    return f'You said: "{last_line}" ({words} word{"" if words == 1 else "s"}).'


@dataclass(slots=True)
class Bot:
    """A minimal, offline-friendly Telegram AI bot.

    Args:
        transport: Where replies are delivered (defaults supplied by caller).
        llm: The pluggable model used for non-command text. Defaults to the
            deterministic :func:`echo_llm` fake.
        history_limit: Maximum number of past user turns kept per chat and fed
            to the LLM as context.
    """

    transport: Transport
    llm: LLM = echo_llm
    history_limit: int = 8
    _history: dict[int, deque[str]] = field(
        default_factory=lambda: defaultdict(deque), init=False, repr=False
    )

    def history(self, chat_id: int) -> list[str]:
        """Return a copy of the recorded user turns for ``chat_id``."""
        return list(self._history[chat_id])

    def reset(self, chat_id: int) -> None:
        """Clear the conversation history for a single chat."""
        self._history[chat_id].clear()

    def _remember(self, chat_id: int, text: str) -> None:
        """Append a user turn, evicting the oldest beyond ``history_limit``."""
        turns = self._history[chat_id]
        turns.append(text)
        while len(turns) > self.history_limit:
            turns.popleft()

    def _build_prompt(self, chat_id: int) -> str:
        """Join the remembered turns for a chat into a single prompt string."""
        return "\n".join(self._history[chat_id])

    def reply_to(self, update: Update) -> str:
        """Compute the reply text for an update without sending it.

        ``/start`` and ``/help`` are handled directly; ``/reset`` clears
        history; any other command is reported as unknown; plain text is
        recorded to history and routed to the LLM with that history as context.
        """
        if update.command is not None:
            if update.command == "start":
                return START_REPLY
            if update.command == "help":
                return HELP_REPLY
            if update.command == "reset":
                self.reset(update.chat_id)
                return "History cleared."
            return f"Unknown command: /{update.command}. Type /help."

        self._remember(update.chat_id, update.text)
        return self.llm(self._build_prompt(update.chat_id))

    def handle(self, update: Update) -> SentMessage:
        """Route a parsed update and deliver the reply via the transport."""
        text = self.reply_to(update)
        return self.transport.send_message(update.chat_id, text)

    def handle_raw(self, raw_update: dict[str, object]) -> SentMessage:
        """Parse a raw Telegram update dict, then :meth:`handle` it."""
        return self.handle(parse_update(raw_update))
