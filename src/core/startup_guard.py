"""Guardas de arranque para aplicaciones desktop/servicios.

Objetivos:
- Evitar instancias duplicadas del mismo entrypoint.
- Validar estructura minima de runtime/config antes de iniciar.
- Aplicar fail-fast de seguridad cuando modo produccion/strict esta activo.
"""

from __future__ import annotations

import atexit
import json
import os
import socket
import time
import uuid
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


class StartupGuardError(RuntimeError):
    """Error de preflight de arranque."""


@dataclass
class _LockHandle:
    app_id: str
    lock_path: Path


_ACTIVE_LOCKS: dict[str, _LockHandle] = {}


def _project_root() -> Path:
    # Permite tests/packaging controlar raiz de forma explicita.
    env_root = os.getenv("TICKETS_PROJECT_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()
    return Path(__file__).resolve().parents[2]


def _runtime_dir() -> Path:
    runtime = _project_root() / "runtime"
    runtime.mkdir(parents=True, exist_ok=True)
    return runtime


def _logs_dir() -> Path:
    logs = _runtime_dir() / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    return logs


def _write_startup_event(app_id: str, event: str, payload: dict[str, Any]) -> None:
    """Persistencia simple JSONL para diagnóstico de arranque."""
    event_path = _logs_dir() / f"startup_{app_id}.jsonl"
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        **payload,
    }
    try:
        with event_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception:
        # El diagnóstico nunca debe bloquear el inicio.
        pass


def _is_port_available(host: str, port: int) -> bool:
    """Verifica si un puerto está libre para bind en el host indicado."""
    bind_host = host if host not in {"", "0.0.0.0"} else "127.0.0.1"
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((bind_host, int(port)))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _profile_bind_target(profile: str | None) -> tuple[str, int] | None:
    if profile == "licencias":
        host = os.getenv("TICKETS_LICENSE_HOST", "0.0.0.0")
        port = int(os.getenv("TICKETS_LICENSE_PORT", "8787"))
        return host, port
    if profile == "receptora":
        host = os.getenv("TICKETS_HTTP_BIND_HOST", "0.0.0.0")
        port = int(os.getenv("TICKETS_HTTP_PORT", "5555"))
        return host, port
    return None


def _validate_profile_runtime(profile: str | None) -> None:
    target = _profile_bind_target(profile)
    if not target:
        return
    host, port = target
    if not _is_port_available(host, port):
        raise StartupGuardError(f"Puerto ocupado para {profile}: {host}:{port}")


def _pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_lock_pid(lock_path: Path) -> int:
    try:
        data = json.loads(lock_path.read_text(encoding="utf-8"))
        return int(data.get("pid", 0))
    except Exception:
        return 0


def _acquire_single_instance(app_id: str) -> _LockHandle:
    lock_dir = _runtime_dir() / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / f"{app_id}.lock"

    if lock_path.exists():
        old_pid = _read_lock_pid(lock_path)
        if old_pid and _pid_running(old_pid):
            raise StartupGuardError(
                f"{app_id} ya esta en ejecucion (pid={old_pid}). Cierre la instancia previa antes de abrir otra."
            )
        # Lock huerfano o invalido
        try:
            lock_path.unlink()
        except OSError as exc:
            raise StartupGuardError(f"No se pudo limpiar lock huerfano de {app_id}: {exc}") from exc

    payload = {
        "app_id": app_id,
        "pid": os.getpid(),
        "started_at": int(time.time()),
    }

    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=True)
    except FileExistsError as exc:
        raise StartupGuardError(f"{app_id} ya esta en ejecucion.") from exc

    return _LockHandle(app_id=app_id, lock_path=lock_path)


def _release_lock(app_id: str) -> None:
    handle = _ACTIVE_LOCKS.pop(app_id, None)
    if not handle:
        return
    try:
        if handle.lock_path.exists():
            handle.lock_path.unlink()
    except OSError:
        # No hacemos fail al cerrar.
        pass


def _validate_required_paths(required_paths: Iterable[str]) -> None:
    base = _project_root()
    missing = [p for p in required_paths if not (base / p).exists()]
    if missing:
        joined = ", ".join(missing)
        raise StartupGuardError(f"Faltan rutas requeridas para iniciar: {joined}")


def _is_strict_mode() -> bool:
    mode = os.getenv("TICKETS_MODE", "desarrollo").strip().lower()
    strict = os.getenv("TICKETS_STRICT_SECURITY", "0").strip() == "1"
    return strict or mode == "produccion"


def build_startup_report(
    app_id: str,
    required_paths: Iterable[str] | None = None,
    security_profile: str | None = None,
) -> dict[str, Any]:
    """Construye un snapshot diagnóstico de preflight de arranque."""
    base = _project_root()
    req = list(required_paths or ())
    checks = {p: (base / p).exists() for p in req}
    run_id = os.getenv("TICKETS_STARTUP_RUN_ID", "") or uuid.uuid4().hex[:12]
    os.environ["TICKETS_STARTUP_RUN_ID"] = run_id
    bind_target = _profile_bind_target(security_profile)
    port_available = None
    if bind_target:
        port_available = _is_port_available(bind_target[0], bind_target[1])

    report = {
        "app_id": app_id,
        "run_id": run_id,
        "pid": os.getpid(),
        "cwd": str(Path.cwd()),
        "project_root": str(base),
        "strict_mode": _is_strict_mode(),
        "single_instance": os.getenv("TICKETS_SINGLE_INSTANCE", "1").strip() != "0",
        "security_profile": security_profile or "none",
        "required_paths": checks,
        "bind_target": f"{bind_target[0]}:{bind_target[1]}" if bind_target else "n/a",
        "bind_available": port_available,
        "env": {
            "TICKETS_MODE": os.getenv("TICKETS_MODE", ""),
            "TICKETS_STRICT_SECURITY": os.getenv("TICKETS_STRICT_SECURITY", ""),
            "TICKETS_HTTP_REQUIRE_API_KEY": os.getenv("TICKETS_HTTP_REQUIRE_API_KEY", ""),
            "TICKETS_HTTP_CORS_ORIGINS": os.getenv("TICKETS_HTTP_CORS_ORIGINS", ""),
            "TICKETS_LICENSE_CORS_ORIGINS": os.getenv("TICKETS_LICENSE_CORS_ORIGINS", ""),
            "TICKETS_LICENSE_HOST": os.getenv("TICKETS_LICENSE_HOST", ""),
            "TICKETS_LICENSE_PORT": os.getenv("TICKETS_LICENSE_PORT", ""),
        },
    }
    return report


def _validate_production_security(profile: str | None) -> None:
    if not profile or not _is_strict_mode():
        return

    if profile == "receptora":
        require_api = os.getenv("TICKETS_HTTP_REQUIRE_API_KEY", "0").strip()
        api_key = os.getenv("TICKETS_HTTP_API_KEY", "")
        cors = os.getenv("TICKETS_HTTP_CORS_ORIGINS", "")

        if require_api != "1":
            raise StartupGuardError("Modo produccion: TICKETS_HTTP_REQUIRE_API_KEY debe ser 1.")
        if len(api_key) < 24:
            raise StartupGuardError("Modo produccion: TICKETS_HTTP_API_KEY debe tener >=24 caracteres.")
        if not cors or "*" in cors:
            raise StartupGuardError("Modo produccion: TICKETS_HTTP_CORS_ORIGINS no puede ser vacio ni wildcard.")

    if profile == "licencias":
        admin_key = os.getenv("TICKETS_LICENSE_ADMIN_KEY", "")
        cors = os.getenv("TICKETS_LICENSE_CORS_ORIGINS", "")
        if len(admin_key) < 24:
            raise StartupGuardError("Modo produccion: TICKETS_LICENSE_ADMIN_KEY debe tener >=24 caracteres.")
        if not cors or "*" in cors:
            raise StartupGuardError("Modo produccion: TICKETS_LICENSE_CORS_ORIGINS no puede ser vacio ni wildcard.")


def bootstrap_entrypoint(
    app_id: str,
    required_paths: Iterable[str] | None = None,
    security_profile: str | None = None,
) -> None:
    """Aplica preflight y lock de instancia para un entrypoint."""
    if app_id in _ACTIVE_LOCKS:
        _write_startup_event(app_id, "startup_skip_already_active", {"app_id": app_id})
        return

    report = build_startup_report(app_id, required_paths=required_paths, security_profile=security_profile)
    _write_startup_event(app_id, "startup_preflight", report)

    try:
        _validate_required_paths(required_paths or ())
        _validate_production_security(security_profile)
        _validate_profile_runtime(security_profile)
    except Exception as exc:
        _write_startup_event(app_id, "startup_preflight_error", {"app_id": app_id, "error": str(exc)})
        raise

    single_instance = os.getenv("TICKETS_SINGLE_INSTANCE", "1").strip() != "0"
    if single_instance:
        try:
            _ACTIVE_LOCKS[app_id] = _acquire_single_instance(app_id)
            atexit.register(_release_lock, app_id)
        except Exception as exc:
            _write_startup_event(app_id, "startup_lock_error", {"app_id": app_id, "error": str(exc)})
            raise

    _write_startup_event(app_id, "startup_ok", {"app_id": app_id})
