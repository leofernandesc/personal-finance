import os
import re
import subprocess
from pathlib import Path


def test_local_hermes_smoke_stops_before_starting_when_profile_is_stale(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    source_manifest = (repo_root / "agent/plugin.yaml").read_text(encoding="utf-8")
    version_match = re.search(r'^version: "([^"]+)"$', source_manifest, re.MULTILINE)
    assert version_match

    profile_home = tmp_path / "profile"
    plugin_dir = profile_home / "plugins" / "personal-finance"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        f'version: "{version_match.group(1)}-stale"\n', encoding="utf-8"
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "hermes-was-started"
    fake_hermes = fake_bin / "hermes"
    fake_hermes.write_text('#!/bin/sh\nprintf started > "$HERMES_TEST_MARKER"\n', encoding="utf-8")
    fake_hermes.chmod(0o755)

    environment = {
        "PATH": f"{fake_bin}:{os.defpath}",
        "HERMES_PROFILE_HOME": str(profile_home),
        "HERMES_TEST_MARKER": str(marker),
    }
    result = subprocess.run(
        ["bash", str(repo_root / "scripts/hermes_local_smoke.sh")],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "plugin do perfil desatualizado" in result.stderr
    assert "hermes plugins install" in result.stderr
    assert not marker.exists()


def test_local_hermes_smoke_limits_output_and_enables_read_only_mode(tmp_path):
    repo_root = Path(__file__).resolve().parents[2]
    source_manifest = (repo_root / "agent/plugin.yaml").read_text(encoding="utf-8")
    version_match = re.search(r'^version: "([^"]+)"$', source_manifest, re.MULTILINE)
    assert version_match

    profile_home = tmp_path / "profile"
    plugin_dir = profile_home / "plugins" / "personal-finance"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "plugin.yaml").write_text(
        f'version: "{version_match.group(1)}"\n', encoding="utf-8"
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    marker = tmp_path / "hermes-environment"
    fake_hermes = fake_bin / "hermes"
    fake_hermes.write_text(
        '#!/bin/sh\nprintf "%s %s\\n" "$PERSONAL_FINANCE_READ_ONLY" '
        '"$HERMES_MAX_TOKENS" > "$HERMES_TEST_MARKER"\n'
        'printf "%s\\n" "$@" >> "$HERMES_TEST_MARKER"\n',
        encoding="utf-8",
    )
    fake_hermes.chmod(0o755)

    environment = {
        "PATH": f"{fake_bin}:{os.defpath}",
        "HERMES_PROFILE_HOME": str(profile_home),
        "HERMES_TEST_MARKER": str(marker),
        "AGENT_SHARED_SECRET": "test-only-placeholder-secret",
    }
    result = subprocess.run(
        ["bash", str(repo_root / "scripts/hermes_local_smoke.sh")],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    first_run_args = marker.read_text(encoding="utf-8").splitlines()
    assert first_run_args[:1] == ["1 512"]
    assert first_run_args[first_run_args.index("--toolsets") + 1] == "personal_finance"

    marker.unlink()
    environment["HERMES_SMOKE_MAX_TOKENS"] = "128"
    custom_limit = subprocess.run(
        ["bash", str(repo_root / "scripts/hermes_local_smoke.sh")],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert custom_limit.returncode == 0, custom_limit.stderr
    custom_run_args = marker.read_text(encoding="utf-8").splitlines()
    assert custom_run_args[:1] == ["1 128"]
    assert custom_run_args[custom_run_args.index("--toolsets") + 1] == "personal_finance"

    marker.unlink()
    environment["HERMES_SMOKE_MAX_TOKENS"] = "2049"
    invalid_limit = subprocess.run(
        ["bash", str(repo_root / "scripts/hermes_local_smoke.sh")],
        cwd=repo_root,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert invalid_limit.returncode == 1
    assert "inteiro entre 1 e 2048" in invalid_limit.stderr
    assert not marker.exists()
