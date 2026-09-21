from pathlib import Path

from agent.integration_check import (
    MIN_HERMES_CONTEXT_LENGTH,
    _model_context,
    check_whatsapp,
)


def test_model_context_reads_provider_specific_metadata():
    assert _model_context({"model_info": {"llama.context_length": 131072}}) == 131072


def test_hermes_minimum_context_is_explicit():
    assert MIN_HERMES_CONTEXT_LENGTH == 64_000


def test_whatsapp_requires_an_explicit_allowlist(tmp_path, monkeypatch):
    (tmp_path / "creds.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "agent.integration_check._get_json",
        lambda _url: {"status": "connected"},
    )

    result = check_whatsapp(Path(tmp_path), "http://127.0.0.1:3300", None)

    assert result.status == "warn"
    assert "WHATSAPP_ALLOWED_USERS" in result.detail


def test_whatsapp_rejects_wildcard_allowlist_for_acceptance(tmp_path, monkeypatch):
    (tmp_path / "creds.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "agent.integration_check._get_json",
        lambda _url: {"status": "connected"},
    )

    result = check_whatsapp(Path(tmp_path), "http://127.0.0.1:3300", "*", mode="bot")

    assert result.status == "warn"
    assert "wildcard" in result.detail


def test_whatsapp_requires_bot_mode_even_with_allowlist(tmp_path, monkeypatch):
    (tmp_path / "creds.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "agent.integration_check._get_json",
        lambda _url: {"status": "connected"},
    )

    result = check_whatsapp(
        Path(tmp_path), "http://127.0.0.1:3300", "+5592999999999", mode="self-chat"
    )

    assert result.status == "warn"
    assert "WHATSAPP_MODE=bot" in result.detail


def test_whatsapp_requires_e164_allowlist_entries(tmp_path, monkeypatch):
    (tmp_path / "creds.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "agent.integration_check._get_json",
        lambda _url: {"status": "connected"},
    )

    result = check_whatsapp(
        Path(tmp_path), "http://127.0.0.1:3300", "5592999999999", mode="bot"
    )

    assert result.status == "warn"
    assert "E.164" in result.detail


def test_whatsapp_accepts_bot_with_specific_allowlist(tmp_path, monkeypatch):
    (tmp_path / "creds.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "agent.integration_check._get_json",
        lambda _url: {"status": "connected"},
    )

    result = check_whatsapp(
        Path(tmp_path), "http://127.0.0.1:3300", "+5592999999999", mode="bot"
    )

    assert result.status == "ok"


def test_whatsapp_rejects_a_connected_self_chat_process(tmp_path, monkeypatch):
    (tmp_path / "creds.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(
        "agent.integration_check._get_json",
        lambda _url: {"status": "connected"},
    )

    result = check_whatsapp(
        Path(tmp_path),
        "http://127.0.0.1:3300",
        "+5592999999999",
        mode="bot",
        observed_bridge_mode="self-chat",
    )

    assert result.status == "warn"
    assert "self-chat" in result.detail


def test_local_bridge_mode_reads_only_the_process_mode(monkeypatch):
    class Result:
        stdout = "node whatsapp-bridge/bridge.js --port 3300 --mode self-chat --session /private"

    monkeypatch.setattr(
        "agent.integration_check.subprocess.run",
        lambda *args, **kwargs: Result(),
    )

    from agent.integration_check import _observe_local_bridge_mode

    assert _observe_local_bridge_mode("http://127.0.0.1:3300") == "self-chat"
