"""Tests for raw-update parsing and command splitting."""

from __future__ import annotations

import pytest

from telegram_ai_bot.update import UpdateError, parse_command, parse_update


def test_parse_plain_text_update() -> None:
    update = parse_update({"message": {"chat": {"id": 42}, "text": "hello world"}})
    assert update.chat_id == 42
    assert update.text == "hello world"
    assert update.command is None
    assert update.args == []
    assert update.is_command is False


def test_parse_command_with_args() -> None:
    update = parse_update({"message": {"chat": {"id": 7}, "text": "/echo one two"}})
    assert update.command == "echo"
    assert update.args == ["one", "two"]
    assert update.is_command is True


def test_parse_command_strips_botname_and_lowercases() -> None:
    assert parse_command("/Start@MyBot now") == ("start", ["now"])


def test_parse_command_non_command() -> None:
    assert parse_command("just chatting") == (None, [])


def test_parse_update_reads_edited_message() -> None:
    update = parse_update({"edited_message": {"chat": {"id": 9}, "text": "edited"}})
    assert update.chat_id == 9
    assert update.text == "edited"


def test_parse_update_missing_message_raises() -> None:
    with pytest.raises(UpdateError):
        parse_update({"update_id": 1})


def test_parse_update_missing_chat_id_raises() -> None:
    with pytest.raises(UpdateError):
        parse_update({"message": {"text": "no chat"}})


def test_parse_update_rejects_bool_chat_id() -> None:
    with pytest.raises(UpdateError):
        parse_update({"message": {"chat": {"id": True}, "text": "x"}})


def test_parse_update_handles_missing_text() -> None:
    update = parse_update({"message": {"chat": {"id": 5}}})
    assert update.text == ""
    assert update.command is None
