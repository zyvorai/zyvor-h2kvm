"""Timestamp rendering in the console and JSON log formatters."""

import json
import logging

from h2kvm.core.logger import EmojiFormatter, JsonFormatter, LogStyle


def _record() -> logging.LogRecord:
    rec = logging.LogRecord("t", logging.INFO, __file__, 1, "hello", None, None)
    rec.created = 86400.123  # 1970-01-02T00:00:00.123Z
    return rec


def test_emoji_formatter_utc_millis():
    fmt = EmojiFormatter(LogStyle(utc=True, show_ms=True, color=False))
    assert fmt._now(86400.123) == "00:00:00.123"  # pylint: disable=protected-access


def test_emoji_formatter_utc_seconds():
    fmt = EmojiFormatter(LogStyle(utc=True, show_ms=False, color=False))
    assert fmt._now(86400.123) == "00:00:00"  # pylint: disable=protected-access


def test_json_formatter_iso_utc():
    out = json.loads(JsonFormatter(utc=True).format(_record()))
    assert any(str(v).startswith("1970-01-02T00:00:00.123") for v in out.values())
