"""Cliente de licenciamiento remoto para apps Tickets.

Este modulo registra una instalacion la primera vez y valida estado al iniciar.
Si no hay conectividad, aplica una ventana de gracia configurable.
"""

from __future__ import annotations

import hashlib
import json
import os
import socket
import sys
import ctypes
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


UTC = timezone.utc


def _app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


APP_DIR = _app_dir()
RUNTIME_DIR = APP_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_PATH = APP_DIR / "licencias_config.json"
STATE_PATH = RUNTIME_DIR / "licencia_estado.json"


DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "server_url": "http://127.0.0.1:8787",
    "offline_grace_hours": 24,
    "timeout_seconds": 5,
    "empresa": "DEFAULT",
    "strict_mode": True,
}


@dataclass
class LicenseResult:
    allowed: bool
    message: str
    reason: str
    device_ip: Optional[str] = None
    device_mac: Optional[str] = None
    server_ip: Optional[str] = None


def _now() -> datetime:
    return datetime.now(tz=UTC)


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_config() -> Dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    disk = _read_json(CONFIG_PATH)
    config.update(disk)

    if not CONFIG_PATH.exists():
        _write_json(CONFIG_PATH, config)

    return config


def _installation_id(state: Dict[str, Any]) -> str:
    installation_id = state.get("installation_id")
    if isinstance(installation_id, str) and installation_id.strip():
        return installation_id
    installation_id = str(uuid.uuid4())
    state["installation_id"] = installation_id
    return installation_id


def _safe_mac() -> str:
    try:
        from getmac import get_mac_address  # type: ignore

        mac = get_mac_address() or "unknown"
        return mac
    except Exception:
        return "unknown"


def _safe_local_ip() -> str:
    try:
        # Evita 127.0.0.1 cuando hay red activa.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "unknown"


def mostrar_banner_bloqueo(app_id: str, result: LicenseResult) -> None:
    titulo = f"Sistema Tickets - {app_id.capitalize()} bloqueada"
    motivo = result.message or "Acceso denegado por política de licencias."
    ip_local = result.device_ip or _safe_local_ip()
    mac_local = result.device_mac or _safe_mac()
    ip_servidor = result.server_ip or "no disponible"

    cuerpo = (
        "Esta aplicación fue bloqueada por el administrador.\n\n"
        f"IP local: {ip_local}\n"
        f"MAC local: {mac_local}\n"
        f"IP vista por servidor: {ip_servidor}\n"
        f"Razón: {motivo}\n"
        f"Código: {result.reason}"
    )

    try:
        ctypes.windll.user32.MessageBoxW(0, cuerpo, titulo, 0x10)
    except Exception:
        # Fallback para entornos sin UI.
        print(f"[BLOQUEO] {titulo}")
        print(cuerpo)


def _machine_fingerprint() -> str:
    raw = "|".join(
        [
            os.getenv("COMPUTERNAME", ""),
            os.getenv("USERNAME", ""),
            socket.gethostname(),
            _safe_mac(),
            str(uuid.getnode()),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def _post_json(url: str, payload: Dict[str, Any], timeout_seconds: int) -> Dict[str, Any]:
    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(req, timeout=timeout_seconds) as response:
        body = response.read().decode("utf-8", errors="ignore")
        if not body:
            return {}
        return json.loads(body)


def validar_licencia_inicio(app_id: str, app_version: str) -> LicenseResult:
    config = _load_config()

    if not config.get("enabled", True):
        return LicenseResult(True, "Licenciamiento deshabilitado por configuración local.", "disabled")

    state = _read_json(STATE_PATH)
    installation_id = _installation_id(state)
    fingerprint = _machine_fingerprint()
    mac_local = _safe_mac()
    ip_local = _safe_local_ip()
    timeout_seconds = int(config.get("timeout_seconds", 5))
    grace_hours = int(config.get("offline_grace_hours", 24))

    payload = {
        "empresa": str(config.get("empresa", "DEFAULT")),
        "app_id": app_id,
        "version": app_version,
        "installation_id": installation_id,
        "hostname": os.getenv("COMPUTERNAME", socket.gethostname()),
        "usuario": os.getenv("USERNAME", "desconocido"),
        "mac_hash": hashlib.sha256(mac_local.encode("utf-8", errors="ignore")).hexdigest(),
        "fingerprint": fingerprint,
        "token": state.get("token", ""),
    }

    server_url = str(config.get("server_url", "")).rstrip("/")
    endpoint = f"{server_url}/api/v1/validate"

    try:
        data = _post_json(endpoint, payload, timeout_seconds)
    except (URLError, HTTPError, TimeoutError, OSError, ValueError):
        strict_mode = bool(config.get("strict_mode", True))
        if strict_mode:
            last_ok = state.get("last_ok_utc")
            if last_ok:
                try:
                    dt = datetime.fromisoformat(last_ok)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    if _now() - dt <= timedelta(hours=grace_hours):
                        return LicenseResult(
                            True,
                            "Sin conexión con servidor de licencias. En ventana de gracia.",
                            "offline_grace",
                            device_ip=ip_local,
                            device_mac=mac_local,
                        )
                except Exception:
                    pass
            return LicenseResult(
                False,
                "No se pudo validar licencia y no hay ventana de gracia disponible.",
                "offline_blocked",
                device_ip=ip_local,
                device_mac=mac_local,
            )

        return LicenseResult(
            True,
            "Servidor de licencias no disponible (modo no estricto).",
            "offline_allowed",
            device_ip=ip_local,
            device_mac=mac_local,
        )

    allowed = bool(data.get("allowed", False))
    message = str(data.get("message", "Sin mensaje del servidor."))
    reason = str(data.get("reason", "unknown"))

    if allowed:
        state["token"] = data.get("token") or state.get("token")
        state["last_ok_utc"] = _now().isoformat()
        state["last_reason"] = reason
        state["installation_id"] = installation_id
        _write_json(STATE_PATH, state)
        return LicenseResult(
            True,
            message,
            reason,
            device_ip=ip_local,
            device_mac=mac_local,
            server_ip=str(data.get("server_ip", "")) or None,
        )

    state["last_reason"] = reason
    state["installation_id"] = installation_id
    _write_json(STATE_PATH, state)
    return LicenseResult(
        False,
        message,
        reason,
        device_ip=ip_local,
        device_mac=mac_local,
        server_ip=str(data.get("server_ip", "")) or None,
    )
