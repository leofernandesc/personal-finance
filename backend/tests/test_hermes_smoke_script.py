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
