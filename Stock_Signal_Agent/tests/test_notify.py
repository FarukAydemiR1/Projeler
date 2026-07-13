"""Bildirim katmanı testleri (ağ gerektirmez)."""

import pytest

from stock_signal_agent.notify import (
    TelegramNotifier, format_report, deliver_report, _split_chunks,
)
from stock_signal_agent.screener import Signal


def _sig(symbol="THYAO.IS", score=0.8, level="GÜÇLÜ", reasons=None, proba=0.7):
    return Signal(
        symbol=symbol, score=score, model_proba=proba, rule_score=0.75,
        reasons=reasons if reasons is not None else ["Hacim patlaması", "MACD kesişim"],
        price=344.5, currency="TRY", level=level,
    )


def test_format_report_with_signals():
    text = format_report([_sig(), _sig("AAPL", 0.5, "İZLE")], min_score=0.45)
    assert "THYAO.IS" in text
    assert "AAPL" in text
    assert "GÜÇLÜ" in text
    assert "Hacim patlaması" in text
    assert "tavsiyesi değildir" in text


def test_format_report_threshold_filters():
    text = format_report([_sig("ZAYIFHISSE", 0.2, "ZAYIF")], min_score=0.45)
    assert "geçen sinyal yok" in text
    assert "En yakın aday: ZAYIFHISSE" in text


def test_format_report_empty():
    text = format_report([], min_score=0.45)
    assert "sinyal yok" in text


def test_format_report_model_optional():
    s = _sig(proba=None)
    s.model_proba = None
    text = format_report([s], min_score=0.0)
    assert "model" not in text.lower().split("skor")[1].split("\n")[0]


def test_split_chunks_short():
    assert _split_chunks("abc", 100) == ["abc"]


def test_split_chunks_respects_limit():
    text = "\n".join(f"satır {i} " + "x" * 50 for i in range(200))
    chunks = _split_chunks(text, 500)
    assert all(len(c) <= 500 for c in chunks)
    # içerik kaybı yok
    assert "".join(c.replace("\n", "") for c in chunks) == text.replace("\n", "")


def test_split_chunks_hard_break_long_line():
    chunks = _split_chunks("y" * 1200, 500)
    assert all(len(c) <= 500 for c in chunks)
    assert sum(len(c) for c in chunks if c) >= 1200


def test_notifier_not_configured(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    n = TelegramNotifier()
    assert not n.configured
    assert n.send("test") is False


def test_deliver_report_console_fallback(monkeypatch, capsys):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    where = deliver_report("rapor içeriği")
    captured = capsys.readouterr()
    assert "rapor içeriği" in captured.out
    assert "yapılandırılmamış" in where


def test_deliver_report_telegram_success(monkeypatch):
    sent = {}

    class FakeResp:
        status_code = 200
        def json(self):
            return {"ok": True}

    def fake_post(url, json=None, timeout=None):
        sent["url"] = url
        sent["payload"] = json
        return FakeResp()

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok123")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "42")
    import stock_signal_agent.notify as notify_mod
    monkeypatch.setattr(notify_mod.requests, "post", fake_post)

    where = deliver_report("merhaba", quiet_console=True)
    assert where == "telegram"
    assert sent["payload"]["chat_id"] == "42"
    assert sent["payload"]["text"] == "merhaba"
    assert "tok123" in sent["url"]
