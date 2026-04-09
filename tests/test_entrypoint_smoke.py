"""Smoke tests de entrypoints con TICKETS_SMOKE_STARTUP.

Valida preflight sin levantar UI/servidores completos.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON_EMBED = ROOT / "python_embed" / "python.exe"


def _run_smoke(script_name: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["TICKETS_SMOKE_STARTUP"] = "1"
    env.setdefault("TICKETS_LICENSE_ADMIN_KEY", "test-admin-key-very-strong-123456")
    return subprocess.run(
        [str(PYTHON_EMBED), str(ROOT / script_name)],
        capture_output=True,
        text=True,
        env=env,
        timeout=20,
    )


def test_kubo_entrypoint_smoke_ok():
    res = _run_smoke("kubo.py")
    assert res.returncode == 0, res.stdout + "\n" + res.stderr


def test_kubito_entrypoint_smoke_ok():
    res = _run_smoke("kubito.py")
    assert res.returncode == 0, res.stdout + "\n" + res.stderr


def test_licencias_entrypoint_smoke_ok():
    res = _run_smoke("app_licencias.py")
    assert res.returncode == 0, res.stdout + "\n" + res.stderr
