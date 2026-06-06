"""Tests for command-vs-LLM routing, per-chat history, and the transport."""

from __future__ import annotations

from telegram_ai_bot.bot import HELP_REPLY, START_REPLY, Bot, echo_llm
from telegram_ai_bot.transport import InMemoryTransport, SentMessage, Transport
from telegram_ai_bot.update import parse_update


def _bot(llm: object = echo_llm) -> tuple[Bot, InMemoryTransport]:
    transport = InMemoryTransport()
    return Bot(transport=transport, llm=llm), transport  # type: ignore[arg-type]


def _update(chat_id: int, text: str):  # type: ignore[no-untyped-def]
    return parse_update({"message": {"chat": {"id": chat_id}, "text": text}})


def test_echo_llm_known_value() -> None:
    assert echo_llm("hello world") == 'You said: "hello world" (2 words).'
    assert echo_llm("hi") == 'You said: "hi" (1 word).'


def test_start_and_help_handled_directly() -> None:
    bot, _ = _bot()
    assert bot.reply_to(_update(1, "/start")) == START_REPLY
    assert bot.reply_to(_update(1, "/help")) == HELP_REPLY


def test_start_does_not_touch_llm() -> None:
    calls: list[str] = []

    def spy(prompt: str) -> str:
        calls.append(prompt)
        return "llm"

    bot, _ = _bot(spy)
    bot.reply_to(_update(1, "/start"))
    assert calls == []


def test_plain_text_routed_to_llm() -> None:
    bot, _ = _bot(lambda prompt: f"LLM[{prompt}]")
    assert bot.reply_to(_update(1, "ping")) == "LLM[ping]"


def test_unknown_command() -> None:
    bot, _ = _bot()
    assert bot.reply_to(_update(1, "/frobnicate")) == "Unknown command: /frobnicate. Type /help."


def test_reset_clears_history() -> None:
    bot, _ = _bot()
    bot.reply_to(_update(1, "alpha"))
    assert bot.history(1) == ["alpha"]
    assert bot.reply_to(_update(1, "/reset")) == "History cleared."
    assert bot.history(1) == []


def test_history_accumulates_and_feeds_llm() -> None:
    bot, _ = _bot(lambda prompt: prompt)
    bot.reply_to(_update(1, "first"))
    second = bot.reply_to(_update(1, "second"))
    assert second == "first\nsecond"
    assert bot.history(1) == ["first", "second"]


def test_history_is_isolated_per_chat() -> None:
    bot, _ = _bot()
    bot.reply_to(_update(1, "chat-one"))
    bot.reply_to(_update(2, "chat-two"))
    assert bot.history(1) == ["chat-one"]
    assert bot.history(2) == ["chat-two"]


def test_history_limit_evicts_oldest() -> None:
    transport = InMemoryTransport()
    bot = Bot(transport=transport, history_limit=2)
    for text in ("a", "b", "c"):
        bot.reply_to(_update(1, text))
    assert bot.history(1) == ["b", "c"]


def test_handle_records_via_transport() -> None:
    bot, transport = _bot()
    sent = bot.handle(_update(99, "/start"))
    assert sent == SentMessage(chat_id=99, text=START_REPLY)
    assert transport.sent == [sent]
    assert transport.messages_for(99) == [sent]


def test_handle_raw_parses_and_sends() -> None:
    bot, transport = _bot()
    sent = bot.handle_raw({"message": {"chat": {"id": 3}, "text": "hey"}})
    assert sent.chat_id == 3
    assert sent.text == 'You said: "hey" (1 word).'
    assert len(transport.sent) == 1


def test_in_memory_transport_records_and_clears() -> None:
    transport = InMemoryTransport()
    assert isinstance(transport, Transport)
    transport.send_message(1, "a")
    transport.send_message(2, "b")
    assert len(transport.sent) == 2
    assert transport.messages_for(2) == [SentMessage(2, "b")]
    transport.clear()
    assert transport.sent == []
