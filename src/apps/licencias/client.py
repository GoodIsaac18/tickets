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
    "activation_key": "",
}

TRIAL_LICENSE_KEY = os.getenv("TICKETS_LICENSE_TRIAL_KEY", "KUBO-TRIAL-7D-GRATIS").strip().upper()


@dataclass
class LicenseResult:
    allowed: bool
    message: str
    reason: str
    license_mode: Optional[str] = None
    trial_expires_at: Optional[str] = None
    server_time_utc: Optional[str] = None
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


def guardar_activation_key(activation_key: str) -> None:
    """Guarda la key de activacion en estado local para siguiente validacion."""
    key = str(activation_key or "").strip()
    state = _read_json(STATE_PATH)
    state["activation_key"] = key
    _write_json(STATE_PATH, state)


def limpiar_activation_key() -> None:
    """Limpia la key de activacion local cuando se desea forzar reactivacion."""
    state = _read_json(STATE_PATH)
    state.pop("activation_key", None)
    _write_json(STATE_PATH, state)


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


def validar_licencia_inicio(app_id: str, app_version: str, request_trial: bool = False) -> LicenseResult:
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
        "activation_key": str(state.get("activation_key") or config.get("activation_key", "")).strip(),
        "request_trial": bool(request_trial),
    }

    server_url = str(config.get("server_url", "")).rstrip("/")
    endpoint = f"{server_url}/api/v1/validate"

    try:
        data = _post_json(endpoint, payload, timeout_seconds)
    except (URLError, HTTPError, TimeoutError, OSError, ValueError):
        strict_mode = bool(config.get("strict_mode", True))
        if strict_mode:
            if state.get("license_mode") == "trial":
                return LicenseResult(
                    False,
                    "La prueba gratuita requiere validación en línea y no puede continuar sin servidor.",
                    "trial_offline_blocked",
                    license_mode="trial",
                    trial_expires_at=str(state.get("trial_expires_at", "")).strip() or None,
                    device_ip=ip_local,
                    device_mac=mac_local,
                )

            activation_token = str(state.get("activation_token", "")).strip()
            activation_expires_at = str(state.get("activation_expires_at", "")).strip()
            last_ok = state.get("last_ok_utc")
            if activation_token and activation_expires_at and last_ok:
                try:
                    dt = datetime.fromisoformat(last_ok)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=UTC)
                    if _now() - dt <= timedelta(hours=grace_hours):
                        return LicenseResult(
                            True,
                            "Sin conexión con servidor de licencias. En ventana de gracia.",
                            "offline_grace",
                            license_mode="licensed",
                            server_time_utc=str(state.get("last_server_utc", "")).strip() or None,
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
    license_mode = str(data.get("license_mode", "")).strip() or None
    trial_expires_at = str(data.get("trial_expires_at", "")).strip() or None
    server_time_utc = str(data.get("server_time_utc", "")).strip() or None

    if allowed:
        state["token"] = data.get("token") or state.get("token")
        if data.get("activation_token"):
            state["activation_token"] = data.get("activation_token")
        if data.get("activation_expires_at"):
            state["activation_expires_at"] = data.get("activation_expires_at")
        if trial_expires_at:
            state["trial_expires_at"] = trial_expires_at
        if license_mode:
            state["license_mode"] = license_mode
        if server_time_utc:
            state["last_server_utc"] = server_time_utc
        if payload.get("activation_key"):
            state["activation_key"] = payload.get("activation_key")
        state["last_ok_utc"] = server_time_utc or _now().isoformat()
        state["last_reason"] = reason
        state["installation_id"] = installation_id
        _write_json(STATE_PATH, state)
        return LicenseResult(
            True,
            message,
            reason,
            license_mode=license_mode,
            trial_expires_at=trial_expires_at,
            server_time_utc=server_time_utc,
            device_ip=ip_local,
            device_mac=mac_local,
            server_ip=str(data.get("server_ip", "")) or None,
        )

    state["last_reason"] = reason
    state["installation_id"] = installation_id
    if license_mode:
        state["license_mode"] = license_mode
    if trial_expires_at:
        state["trial_expires_at"] = trial_expires_at
    if server_time_utc:
        state["last_server_utc"] = server_time_utc
    if payload.get("activation_key"):
        state["activation_key"] = payload.get("activation_key")
    _write_json(STATE_PATH, state)

    if config.get("strict_mode", True):
        if state.get("license_mode") == "trial" or reason in {"trial_started", "trial_active", "trial_expired"}:
            return LicenseResult(
                False,
                "La prueba gratuita requiere validación en línea y no puede continuar sin servidor.",
                "trial_offline_blocked",
                license_mode="trial",
                trial_expires_at=trial_expires_at,
                server_time_utc=server_time_utc,
                device_ip=ip_local,
                device_mac=mac_local,
                server_ip=str(data.get("server_ip", "")) or None,
            )

        activation_token = str(state.get("activation_token", "")).strip()
        activation_expires_at = str(state.get("activation_expires_at", "")).strip()
        if activation_token and activation_expires_at:
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
                            license_mode="licensed",
                            server_time_utc=server_time_utc,
                            device_ip=ip_local,
                            device_mac=mac_local,
                            server_ip=str(data.get("server_ip", "")) or None,
                        )
                except Exception:
                    pass

    return LicenseResult(
        False,
        message,
        reason,
        license_mode=license_mode,
        trial_expires_at=trial_expires_at,
        server_time_utc=server_time_utc,
        device_ip=ip_local,
        device_mac=mac_local,
        server_ip=str(data.get("server_ip", "")) or None,
    )
