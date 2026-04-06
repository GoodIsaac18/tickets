"""Preferencias de app, estado de licencia y reporte de soporte.

Modulo compartido para Kubo y Kubito.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from urllib.request import Request, urlopen

UTC = timezone.utc
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _prefs_path(app_id: str) -> Path:
    safe = "".join(ch for ch in app_id.lower() if ch.isalnum() or ch in ("-", "_")) or "app"
    return RUNTIME_DIR / f"preferencias_{safe}.json"


DEFAULT_PREFERENCES: Dict[str, Any] = {
    "ui": {
        "mostrar_hora": True,
        "mostrar_notificaciones": True,
        "animaciones": True,
    },
    "features": {
        "diagnostico_rapido": True,
        "modo_soporte": False,
    },
    "support": {
        "email": "soporte@kubo.local",
    },
}


def get_app_version() -> str:
    version_json = PROJECT_ROOT / "config" / "version.json"
    data = _read_json(version_json)
    version = str(data.get("version", "")).strip()
    return version or "0.0.0"


def load_app_preferences(app_id: str) -> Dict[str, Any]:
    prefs = json.loads(json.dumps(DEFAULT_PREFERENCES))
    disk = _read_json(_prefs_path(app_id))

    for section, default_values in DEFAULT_PREFERENCES.items():
        current = disk.get(section)
        if isinstance(current, dict):
            prefs[section].update(current)

    if not _prefs_path(app_id).exists():
        save_app_preferences(app_id, prefs)

    return prefs


def save_app_preferences(app_id: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
    merged = json.loads(json.dumps(DEFAULT_PREFERENCES))
    for section, default_values in DEFAULT_PREFERENCES.items():
        current = prefs.get(section)
        if isinstance(current, dict):
            merged[section].update(current)

    _write_json(_prefs_path(app_id), merged)
    return merged


def read_license_status() -> Dict[str, Any]:
    licencia_cfg = _read_json(PROJECT_ROOT / "licencias_config.json")
    licencia_state = _read_json(RUNTIME_DIR / "licencia_estado.json")

    return {
        "enabled": bool(licencia_cfg.get("enabled", True)),
        "server_url": str(licencia_cfg.get("server_url", "http://127.0.0.1:8787")),
        "strict_mode": bool(licencia_cfg.get("strict_mode", True)),
        "installation_id": str(licencia_state.get("installation_id", "")),
        "last_ok_utc": str(licencia_state.get("last_ok_utc", "")),
        "last_reason": str(licencia_state.get("last_reason", "")),
        "license_mode": str(licencia_state.get("license_mode", "")),
        "trial_expires_at": str(licencia_state.get("trial_expires_at", "")),
        "last_server_utc": str(licencia_state.get("last_server_utc", "")),
    }


def verify_license_now(app_id: str) -> Dict[str, Any]:
    try:
        from src.apps.licencias.client import validar_licencia_inicio

        result = validar_licencia_inicio(app_id, get_app_version())
        return {
            "ok": bool(result.allowed),
            "message": str(result.message),
            "reason": str(result.reason),
            "checked_at": datetime.now(tz=UTC).isoformat(),
        }
    except Exception as exc:
        return {
            "ok": False,
            "message": f"Error al verificar licencia: {exc}",
            "reason": "client_error",
            "checked_at": datetime.now(tz=UTC).isoformat(),
        }


def send_support_report(
    app_id: str,
    report_type: str,
    message: str,
    contact: str = "",
    extra: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    licencia = read_license_status()
    server_url = str(licencia.get("server_url", "http://127.0.0.1:8787")).rstrip("/")
    url = f"{server_url}/api/v1/support/report"

    payload = {
        "app_id": app_id,
        "type": report_type,
        "message": message,
        "contact": contact,
        "version": get_app_version(),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "extra": extra or {},
    }

    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=6) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(body) if body else {}
            return {"ok": True, "response": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
