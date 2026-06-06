"""Command-line interface for Telegram AI Bot.

``telegram-ai-bot demo`` feeds a scripted batch of updates from two chats to a
:class:`~telegram_ai_bot.bot.Bot` wired to the offline fake LLM and the
:class:`~telegram_ai_bot.transport.InMemoryTransport`, then prints every reply.
No API token, no network.

Part of Telegram AI Bot by Viprasol Tech Private Limited (https://viprasol.com).
"""

from __future__ import annotations

from typing import Any

import typer
from rich.console import Console

from telegram_ai_bot import __version__
from telegram_ai_bot.bot import Bot, echo_llm
from telegram_ai_bot.transport import InMemoryTransport

app = typer.Typer(add_completion=False, help="Telegram AI Bot — by Viprasol Tech.")
console = Console()


def _msg(chat_id: int, text: str) -> dict[str, Any]:
    """Build a minimal raw Telegram update for ``text`` in ``chat_id``."""
    return {"message": {"chat": {"id": chat_id}, "text": text}}


def _demo_updates() -> list[dict[str, Any]]:
    """A scripted conversation across two chats to show routing and isolation."""
    return [
        _msg(101, "/start"),
        _msg(101, "Hello there"),
        _msg(202, "different chat here"),
        _msg(101, "/help"),
        _msg(101, "what was my first message?"),
        _msg(202, "/reset"),
    ]


@app.command()
def version() -> None:
    """Print the installed version."""
    console.print(f"telegram-ai-bot [bold cyan]{__version__}[/] - by Viprasol Tech")


@app.command()
def demo() -> None:
    """Feed scripted updates to the offline bot and print every reply."""
    transport = InMemoryTransport()
    bot = Bot(transport=transport, llm=echo_llm)

    for raw in _demo_updates():
        message = raw["message"]
        sent = bot.handle_raw(raw)
        console.print(
            f"chat [bold]{message['chat']['id']}[/] "
            f"<- {message['text']!r}\n"
            f"  -> [green]{sent.text}[/]"
        )

    console.print(
        f"\nDelivered [bold]{len(transport.sent)}[/] replies offline "
        f"(chat 101 history: {bot.history(101)})."
    )


if __name__ == "__main__":
    app()
