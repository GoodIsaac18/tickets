"""Runner simple de pytest para usar con coverage.py.

Ejecutar como archivo evita problemas de resolucion de modulo con el entorno embebido.
"""

from __future__ import annotations

import site
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EMBED_SITE = ROOT / "python_embed" / "Lib" / "site-packages"

if EMBED_SITE.exists():
    sys.path.insert(0, str(EMBED_SITE))

# Evitar que pytest se importe desde el user-site global del perfil Windows.
site.ENABLE_USER_SITE = False
sys.path = [path for path in sys.path if "AppData\\Roaming\\Python" not in path]

import pytest


def main() -> int:
    return pytest.main([str(ROOT / "tests"), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())
