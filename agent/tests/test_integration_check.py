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
