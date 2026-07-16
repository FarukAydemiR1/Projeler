"""config.load_dotenv testleri (gizli bilgi yüklemesi, ağ gerektirmez)."""

import os

from stock_signal_agent.config import load_dotenv, load_config


def test_dotenv_loads_values(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    env = tmp_path / ".env"
    env.write_text(
        'TELEGRAM_BOT_TOKEN="123:ABC"\n'
        "TELEGRAM_CHAT_ID=42\n"
        "# yorum satırı\n"
        "export FOO=bar\n",
        encoding="utf-8",
    )
    loaded = load_dotenv(env)
    assert loaded == str(env)
    assert os.environ["TELEGRAM_BOT_TOKEN"] == "123:ABC"
    assert os.environ["TELEGRAM_CHAT_ID"] == "42"
    assert os.environ["FOO"] == "bar"  # `export ` ön eki de desteklenir


def test_dotenv_does_not_override_existing(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "gercek-ortam-degeri")
    env = tmp_path / ".env"
    env.write_text("TELEGRAM_BOT_TOKEN=dosya-degeri\n", encoding="utf-8")
    load_dotenv(env)
    # Var olan ortam değişkeni korunur (dosya üzerine yazmaz)
    assert os.environ["TELEGRAM_BOT_TOKEN"] == "gercek-ortam-degeri"


def test_dotenv_missing_file_returns_none(tmp_path):
    assert load_dotenv(tmp_path / "yok.env") is None


def test_load_config_still_works(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # kök .env/config.yaml'dan izole et
    cfg = load_config()
    assert "bist" in cfg and "us" in cfg
    assert cfg["horizon"] > 0
