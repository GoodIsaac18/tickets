"""Servicio central de licencias para Sistema Tickets.

API:
- POST /api/v1/validate                       (cliente emisora/receptora)
- POST /api/v1/support/report                 (cliente emisora/receptora)
- GET  /api/v1/admin/overview                 (panel React)
- GET  /api/v1/admin/installations            (panel React)
- POST /api/v1/admin/global                   (panel React)
- POST /api/v1/admin/installations/block      (panel React)

Panel legacy:
- GET /admin

Autenticación admin:
- Header: X-Admin-Key
- Variable de entorno recomendada: TICKETS_LICENSE_ADMIN_KEY
"""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import threading
import time
import hmac
import hashlib
import base64
from html import escape
from contextlib import closing
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlencode, urlparse

# Logging
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
try:
    from core.logger import get_logger, log_info, log_error
    _logger = get_logger('licencias', 'INFO')
except ImportError:
    _logger = None


UTC = timezone.utc
BASE_DIR = Path(__file__).resolve().parents[3]
RUNTIME_DIR = BASE_DIR / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = RUNTIME_DIR / "licencias.db"
HOST = os.getenv("TICKETS_LICENSE_HOST", "0.0.0.0")
PORT = int(os.getenv("TICKETS_LICENSE_PORT", "8787"))
ADMIN_KEY = os.getenv("TICKETS_LICENSE_ADMIN_KEY", "cambiar-esta-clave")
SIGNING_KEY = os.getenv("TICKETS_LICENSE_SIGNING_KEY", ADMIN_KEY)
TICKETS_MODE = os.getenv("TICKETS_MODE", "desarrollo").strip().lower()
STRICT_SECURITY = os.getenv("TICKETS_STRICT_SECURITY", "0").strip() == "1"
MAX_LIMIT = 1000
MAX_JSON_BYTES_VALIDATE = int(os.getenv("TICKETS_LICENSE_MAX_JSON_VALIDATE", "65536"))
MAX_JSON_BYTES_ADMIN = int(os.getenv("TICKETS_LICENSE_MAX_JSON_ADMIN", "32768"))
MAX_JSON_BYTES_SUPPORT = int(os.getenv("TICKETS_LICENSE_MAX_JSON_SUPPORT", "16384"))
MAX_FORM_BYTES_ADMIN = int(os.getenv("TICKETS_LICENSE_MAX_FORM_ADMIN", "16384"))
VALIDATE_RATE_LIMIT_MAX = int(os.getenv("TICKETS_LICENSE_VALIDATE_RATE_MAX", "60"))
VALIDATE_RATE_LIMIT_WINDOW = int(os.getenv("TICKETS_LICENSE_VALIDATE_RATE_WINDOW", "60"))
ACTIVATION_FAIL_MAX = int(os.getenv("TICKETS_LICENSE_ACTIVATION_FAIL_MAX", "5"))
ACTIVATION_FAIL_WINDOW = int(os.getenv("TICKETS_LICENSE_ACTIVATION_FAIL_WINDOW", "600"))
ACTIVATION_LOCK_SECONDS = int(os.getenv("TICKETS_LICENSE_ACTIVATION_LOCK_SECONDS", "900"))
ACTIVATION_TOKEN_TTL_SECONDS = int(os.getenv("TICKETS_LICENSE_TOKEN_TTL_SECONDS", "43200"))
TRIAL_DURATION_SECONDS = int(os.getenv("TICKETS_LICENSE_TRIAL_SECONDS", str(7 * 24 * 60 * 60)))
TRIAL_LICENSE_KEY = os.getenv("TICKETS_LICENSE_TRIAL_KEY", "KUBO-TRIAL-7D-GRATIS").strip().upper()
CORS_ALLOWED_ORIGINS = tuple(
    origin.strip()
    for origin in os.getenv(
        "TICKETS_LICENSE_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
)

_validate_rate_limit_por_ip: Dict[str, List[float]] = {}
_validate_rate_limit_lock = threading.Lock()
_activation_failures: Dict[str, List[float]] = {}
_activation_lock_until: Dict[str, float] = {}
_activation_guard_lock = threading.Lock()


class PayloadTooLargeError(ValueError):
    """Error de payload excesivo para devolver HTTP 413."""


def _validar_config_seguridad_inicio() -> None:
    advertencias: List[str] = []
    errores: List[str] = []
    modo_estricto = STRICT_SECURITY or TICKETS_MODE == "produccion"

    if ADMIN_KEY == "cambiar-esta-clave" or len(ADMIN_KEY) < 24:
        advertencias.append("ADMIN key débil o por defecto en servidor de licencias.")
        if modo_estricto:
            errores.append("Defina TICKETS_LICENSE_ADMIN_KEY robusta (>=24 caracteres).")

    if not CORS_ALLOWED_ORIGINS:
        advertencias.append("TICKETS_LICENSE_CORS_ORIGINS está vacío.")
        if modo_estricto:
            errores.append("Defina TICKETS_LICENSE_CORS_ORIGINS en producción.")

    if "*" in CORS_ALLOWED_ORIGINS:
        advertencias.append("CORS en wildcard detectado para licencias.")
        if modo_estricto:
            errores.append("No se permite wildcard en TICKETS_LICENSE_CORS_ORIGINS en producción.")

    if HOST in {"0.0.0.0", ""}:
        advertencias.append("Licencias expuesto en todas las interfaces (HOST=0.0.0.0).")

    for warning in advertencias:
        print(f"[LIC-SECURITY][WARN] {warning}")

    if errores:
        for err in errores:
            print(f"[LIC-SECURITY][ERROR] {err}")
        raise RuntimeError("Configuración de seguridad de licencias inválida para producción")


def is_origin_allowed(origin: str) -> bool:
    if not origin:
        return False
    if "*" in CORS_ALLOWED_ORIGINS:
        return True
    return origin in CORS_ALLOWED_ORIGINS


def validate_rate_limited(client_ip: str) -> bool:
    now = time.time()
    threshold = now - max(1, VALIDATE_RATE_LIMIT_WINDOW)

    with _validate_rate_limit_lock:
        stamps = _validate_rate_limit_por_ip.get(client_ip, [])
        stamps = [stamp for stamp in stamps if stamp >= threshold]

        if len(stamps) >= max(1, VALIDATE_RATE_LIMIT_MAX):
            _validate_rate_limit_por_ip[client_ip] = stamps
            return True

        stamps.append(now)
        _validate_rate_limit_por_ip[client_ip] = stamps
        return False


def _activation_guard_subject(installation_id: str, client_ip: str) -> str:
    installation_id = str(installation_id or "").strip()
    if installation_id:
        return f"id:{installation_id}"
    return f"ip:{str(client_ip or '').strip() or 'unknown'}"


def activation_is_temporarily_locked(installation_id: str, client_ip: str) -> int:
    now = time.time()
    subject = _activation_guard_subject(installation_id, client_ip)
    with _activation_guard_lock:
        locked_until = float(_activation_lock_until.get(subject, 0.0))
        if locked_until <= now:
            _activation_lock_until.pop(subject, None)
            return 0
        return max(1, int(locked_until - now))


def register_activation_failure(installation_id: str, client_ip: str) -> int:
    now = time.time()
    threshold = now - max(1, ACTIVATION_FAIL_WINDOW)
    subject = _activation_guard_subject(installation_id, client_ip)
    with _activation_guard_lock:
        failures = [stamp for stamp in _activation_failures.get(subject, []) if stamp >= threshold]
        failures.append(now)
        _activation_failures[subject] = failures
        if len(failures) >= max(1, ACTIVATION_FAIL_MAX):
            locked_until = now + max(5, ACTIVATION_LOCK_SECONDS)
            _activation_lock_until[subject] = locked_until
            _activation_failures.pop(subject, None)
            return max(1, int(locked_until - now))
    return 0


def clear_activation_failures(installation_id: str, client_ip: str) -> None:
    subject = _activation_guard_subject(installation_id, client_ip)
    with _activation_guard_lock:
        _activation_failures.pop(subject, None)
        _activation_lock_until.pop(subject, None)


def utc_now_iso() -> str:
    return datetime.now(tz=UTC).isoformat()


def db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with closing(db()) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS licencia_global (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                blocked INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT 'Servicio disponible',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS instalaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                installation_id TEXT NOT NULL UNIQUE,
                token TEXT NOT NULL UNIQUE,
                empresa TEXT NOT NULL,
                app_id TEXT NOT NULL,
                version TEXT NOT NULL,
                hostname TEXT,
                usuario TEXT,
                mac_hash TEXT,
                fingerprint TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                last_ip TEXT,
                blocked INTEGER NOT NULL DEFAULT 0,
                blocked_reason TEXT,
                total_validations INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_instalaciones_token ON instalaciones(token)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_instalaciones_empresa_app ON instalaciones(empresa, app_id)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS soporte_eventos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                app_id TEXT NOT NULL,
                tipo TEXT NOT NULL,
                mensaje TEXT NOT NULL,
                version TEXT,
                contact TEXT,
                remote_ip TEXT,
                extra_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS licencia_keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                license_key TEXT NOT NULL UNIQUE,
                product TEXT NOT NULL,
                seats_limit INTEGER,
                blocked INTEGER NOT NULL DEFAULT 0,
                expires_at TEXT,
                notes TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS activaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key_id INTEGER NOT NULL,
                product TEXT NOT NULL,
                installation_id TEXT NOT NULL,
                fingerprint TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                revoked_at TEXT,
                revoked_reason TEXT,
                FOREIGN KEY(key_id) REFERENCES licencia_keys(id),
                UNIQUE(key_id, installation_id)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_activaciones_key_active
            ON activaciones(key_id, revoked_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS trial_activations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id TEXT NOT NULL,
                device_key TEXT NOT NULL UNIQUE,
                first_installation_id TEXT NOT NULL,
                last_installation_id TEXT NOT NULL,
                fingerprint TEXT,
                mac_hash TEXT,
                first_seen TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                first_ip TEXT,
                last_ip TEXT,
                expires_at TEXT NOT NULL,
                revoked_at TEXT,
                revoked_reason TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_trial_activations_app_expires
            ON trial_activations(app_id, expires_at)
            """
        )

        cur = conn.execute("SELECT id FROM licencia_global WHERE id = 1")
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO licencia_global(id, blocked, message, updated_at) VALUES(1, 0, ?, ?)",
                ("Servicio disponible", utc_now_iso()),
            )
        conn.commit()


def _normalize_product(app_id: str) -> str:
    v = (app_id or "").strip().lower()
    if v in {"receptora", "kubo"}:
        return "kubo"
    if v in {"emisora", "kubito"}:
        return "kubito"
    return v or "kubito"


def _iso_plus_seconds(seconds: int) -> str:
    return datetime.fromtimestamp(time.time() + max(60, seconds), tz=UTC).isoformat()


def _create_activation_token(installation_id: str, product: str, key_id: int, expires_at: str) -> str:
    payload = f"{installation_id}|{product}|{key_id}|{expires_at}"
    sig = hmac.new(SIGNING_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256).hexdigest()
    raw = f"{payload}|{sig}".encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _build_device_key(product: str, fingerprint: str, mac_hash: str) -> str:
    payload = f"{_normalize_product(product)}|{fingerprint.strip()}|{mac_hash.strip()}"
    return hashlib.sha256(payload.encode("utf-8", errors="ignore")).hexdigest()


def _parse_iso_datetime(value: str) -> datetime | None:
    value = str(value or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
        return parsed.astimezone(UTC)
    except Exception:
        return None


def _trial_record_expired(expires_at: str) -> bool:
    parsed = _parse_iso_datetime(expires_at)
    return bool(parsed and parsed <= datetime.now(tz=UTC))


def _find_trial_activation(
    conn: sqlite3.Connection,
    product: str,
    fingerprint: str,
    mac_hash: str,
) -> sqlite3.Row | None:
    device_key = _build_device_key(product, fingerprint, mac_hash)
    return conn.execute(
        """
        SELECT *
        FROM trial_activations
        WHERE device_key = ?
        LIMIT 1
        """,
        (device_key,),
    ).fetchone()


def _ensure_trial_activation(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    product: str,
    fingerprint: str,
    mac_hash: str,
    client_ip: str,
) -> tuple[sqlite3.Row, bool]:
    now = utc_now_iso()
    device_key = _build_device_key(product, fingerprint, mac_hash)
    trial_row = _find_trial_activation(conn, product, fingerprint, mac_hash)

    if trial_row:
        conn.execute(
            """
            UPDATE trial_activations
            SET last_installation_id = ?, fingerprint = ?, mac_hash = ?, last_seen = ?, last_ip = ?
            WHERE id = ?
            """,
            (
                str(row["installation_id"]),
                fingerprint,
                mac_hash,
                now,
                client_ip,
                int(trial_row["id"]),
            ),
        )
        conn.commit()
        updated = conn.execute("SELECT * FROM trial_activations WHERE id = ?", (int(trial_row["id"]),)).fetchone()
        return updated, False

    expires_at = _iso_plus_seconds(TRIAL_DURATION_SECONDS)
    conn.execute(
        """
        INSERT INTO trial_activations(
            app_id, device_key, first_installation_id, last_installation_id,
            fingerprint, mac_hash, first_seen, last_seen, first_ip, last_ip,
            expires_at, revoked_at, revoked_reason
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)
        """,
        (
            product,
            device_key,
            str(row["installation_id"]),
            str(row["installation_id"]),
            fingerprint,
            mac_hash,
            now,
            now,
            client_ip,
            client_ip,
            expires_at,
        ),
    )
    conn.commit()
    created = conn.execute("SELECT * FROM trial_activations WHERE device_key = ?", (device_key,)).fetchone()
    return created, True


def create_license_key(product: str, seats_limit: int | None, expires_at: str | None, notes: str) -> Dict[str, Any]:
    clean_product = _normalize_product(product)
    key = f"{clean_product.upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"
    now = utc_now_iso()
    seats = seats_limit
    if clean_product == "kubo":
        seats = 1

    with closing(db()) as conn:
        cur = conn.execute(
            """
            INSERT INTO licencia_keys(license_key, product, seats_limit, blocked, expires_at, notes, created_at, updated_at)
            VALUES(?, ?, ?, 0, ?, ?, ?, ?)
            """,
            (key, clean_product, seats, expires_at, notes, now, now),
        )
        conn.commit()

    return {
        "id": int(cur.lastrowid or 0),
        "license_key": key,
        "product": clean_product,
        "seats_limit": seats,
        "expires_at": expires_at,
        "notes": notes,
    }


def _active_seats(conn: sqlite3.Connection, key_id: int) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS n FROM activaciones WHERE key_id = ? AND revoked_at IS NULL",
        (key_id,),
    ).fetchone()
    return int(row["n"] if row else 0)


def _activate_with_key(
    conn: sqlite3.Connection,
    row: sqlite3.Row,
    product: str,
    activation_key: str,
    fingerprint: str,
) -> Tuple[bool, str, str, Dict[str, Any] | None]:
    key_row = conn.execute(
        "SELECT * FROM licencia_keys WHERE license_key = ?",
        (activation_key,),
    ).fetchone()
    if not key_row:
        return False, "activation_key_invalid", "Key de activación inválida.", None

    if bool(key_row["blocked"]):
        return False, "license_key_blocked", "Key de activación bloqueada.", None

    key_product = _normalize_product(str(key_row["product"]))
    if key_product != product:
        return False, "product_mismatch", f"La key no corresponde a {product}.", None

    expires_at = str(key_row["expires_at"] or "").strip()
    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=UTC)
            if exp <= datetime.now(tz=UTC):
                return False, "license_key_expired", "La key de activación está expirada.", None
        except Exception:
            return False, "license_key_expired", "La key de activación tiene expiración inválida.", None

    installation_id = str(row["installation_id"])
    existing = conn.execute(
        """
        SELECT * FROM activaciones
        WHERE key_id = ? AND installation_id = ?
        """,
        (int(key_row["id"]), installation_id),
    ).fetchone()

    now = utc_now_iso()
    if existing and not existing["revoked_at"]:
        conn.execute(
            "UPDATE activaciones SET last_seen = ?, fingerprint = ? WHERE id = ?",
            (now, fingerprint, int(existing["id"])),
        )
        conn.commit()
    else:
        seats_limit = key_row["seats_limit"]
        used = _active_seats(conn, int(key_row["id"]))
        if seats_limit is not None and int(seats_limit) >= 0 and used >= int(seats_limit):
            return False, "seats_limit_reached", "Límite de equipos alcanzado para esta key.", None

        conn.execute(
            """
            INSERT INTO activaciones(key_id, product, installation_id, fingerprint, first_seen, last_seen, revoked_at, revoked_reason)
            VALUES(?, ?, ?, ?, ?, ?, NULL, NULL)
            ON CONFLICT(key_id, installation_id) DO UPDATE SET
                revoked_at = NULL,
                revoked_reason = NULL,
                fingerprint = excluded.fingerprint,
                last_seen = excluded.last_seen
            """,
            (int(key_row["id"]), product, installation_id, fingerprint, now, now),
        )
        conn.commit()

    return True, "activated", "Activación válida.", {
        "key_id": int(key_row["id"]),
        "license_key": str(key_row["license_key"]),
        "product": product,
        "seats_limit": (None if key_row["seats_limit"] is None else int(key_row["seats_limit"])),
    }


def _find_active_activation(conn: sqlite3.Connection, installation_id: str, product: str) -> sqlite3.Row | None:
    return conn.execute(
        """
        SELECT a.*, k.license_key, k.seats_limit, k.blocked AS key_blocked
        FROM activaciones a
        JOIN licencia_keys k ON k.id = a.key_id
        WHERE a.installation_id = ? AND a.product = ? AND a.revoked_at IS NULL
        LIMIT 1
        """,
        (installation_id, product),
    ).fetchone()


def get_global_state(conn: sqlite3.Connection) -> Dict[str, Any]:
    row = conn.execute("SELECT blocked, message, updated_at FROM licencia_global WHERE id = 1").fetchone()
    return {
        "blocked": bool(row["blocked"]),
        "message": row["message"],
        "updated_at": row["updated_at"],
    }


def upsert_installation(conn: sqlite3.Connection, payload: Dict[str, Any], client_ip: str) -> sqlite3.Row:
    installation_id = str(payload.get("installation_id", "")).strip()
    token = str(payload.get("token", "")).strip()

    if not installation_id:
        raise ValueError("installation_id requerido")

    existing = conn.execute(
        "SELECT * FROM instalaciones WHERE installation_id = ?",
        (installation_id,),
    ).fetchone()

    now = utc_now_iso()

    if existing is None:
        if not token:
            token = secrets.token_urlsafe(24)

        conn.execute(
            """
            INSERT INTO instalaciones(
                installation_id, token, empresa, app_id, version, hostname, usuario,
                mac_hash, fingerprint, first_seen, last_seen, last_ip, blocked,
                blocked_reason, total_validations
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, NULL, 1)
            """,
            (
                installation_id,
                token,
                str(payload.get("empresa", "DEFAULT")),
                str(payload.get("app_id", "unknown")),
                str(payload.get("version", "0.0.0")),
                str(payload.get("hostname", "")),
                str(payload.get("usuario", "")),
                str(payload.get("mac_hash", "")),
                str(payload.get("fingerprint", "")),
                now,
                now,
                client_ip,
            ),
        )
    else:
        # Si viene token y no coincide, se respeta el token guardado para evitar suplantación.
        token = str(existing["token"])
        conn.execute(
            """
            UPDATE instalaciones
            SET version = ?, hostname = ?, usuario = ?, mac_hash = ?, fingerprint = ?,
                last_seen = ?, last_ip = ?, total_validations = total_validations + 1
            WHERE installation_id = ?
            """,
            (
                str(payload.get("version", existing["version"])),
                str(payload.get("hostname", existing["hostname"])),
                str(payload.get("usuario", existing["usuario"])),
                str(payload.get("mac_hash", existing["mac_hash"])),
                str(payload.get("fingerprint", existing["fingerprint"])),
                now,
                client_ip,
                installation_id,
            ),
        )

    conn.commit()
    row = conn.execute("SELECT * FROM instalaciones WHERE installation_id = ?", (installation_id,)).fetchone()
    return row


def validate_request(payload: Dict[str, Any], client_ip: str) -> Dict[str, Any]:
    with closing(db()) as conn:
        global_state = get_global_state(conn)
        row = upsert_installation(conn, payload, client_ip)
        product = _normalize_product(str(payload.get("app_id", row["app_id"])))
        activation_key = str(payload.get("activation_key", "")).strip()
        request_trial = bool(payload.get("request_trial", False))
        if activation_key and activation_key.strip().upper() == TRIAL_LICENSE_KEY:
            request_trial = True
            activation_key = ""
        fingerprint = str(payload.get("fingerprint", "")).strip()
        mac_hash = str(payload.get("mac_hash", "")).strip()
        server_time_utc = utc_now_iso()

        if global_state["blocked"]:
            return {
                "allowed": False,
                "reason": "global_blocked",
                "message": global_state["message"],
                "token": row["token"],
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        if bool(row["blocked"]):
            return {
                "allowed": False,
                "reason": "installation_blocked",
                "message": row["blocked_reason"] or "Instalación bloqueada por administrador.",
                "token": row["token"],
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        active_activation = _find_active_activation(conn, str(row["installation_id"]), product)

        if active_activation:
            if bool(active_activation["key_blocked"]):
                return {
                    "allowed": False,
                    "reason": "license_key_blocked",
                    "message": "La key asociada fue bloqueada por administrador.",
                    "token": row["token"],
                    "server_time_utc": server_time_utc,
                    "server_ip": client_ip,
                }
            conn.execute(
                "UPDATE activaciones SET last_seen = ?, fingerprint = ? WHERE id = ?",
                (server_time_utc, fingerprint, int(active_activation["id"])),
            )
            conn.commit()
            expires_at = _iso_plus_seconds(ACTIVATION_TOKEN_TTL_SECONDS)
            activation_token = _create_activation_token(
                str(row["installation_id"]),
                product,
                int(active_activation["key_id"]),
                expires_at,
            )
            return {
                "allowed": True,
                "reason": "ok",
                "message": "Licencia válida.",
                "token": row["token"],
                "activation_token": activation_token,
                "activation_expires_at": expires_at,
                "license_mode": "licensed",
                "license_product": product,
                "license_key": str(active_activation["license_key"]),
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        if activation_key:
            retry_after = activation_is_temporarily_locked(str(row["installation_id"]), client_ip)
            if retry_after > 0:
                if _logger:
                    log_info(
                        _logger,
                        "Bloqueo temporal de activacion",
                        installation_id=str(row["installation_id"]),
                        ip=client_ip,
                        retry_after_seconds=retry_after,
                    )
                return {
                    "allowed": False,
                    "reason": "activation_temporarily_locked",
                    "message": "Demasiados intentos fallidos de activación. Espere antes de reintentar.",
                    "retry_after_seconds": retry_after,
                    "token": row["token"],
                    "server_time_utc": server_time_utc,
                    "server_ip": client_ip,
                }

            ok, reason, message, meta = _activate_with_key(conn, row, product, activation_key, fingerprint)
            if not ok:
                if reason in {"activation_key_invalid", "product_mismatch", "license_key_expired"}:
                    locked_for = register_activation_failure(str(row["installation_id"]), client_ip)
                    if locked_for > 0:
                        if _logger:
                            log_error(
                                _logger,
                                "Bloqueo por fuerza bruta de activacion",
                                installation_id=str(row["installation_id"]),
                                ip=client_ip,
                                reason=reason,
                                locked_for_seconds=locked_for,
                            )
                        return {
                            "allowed": False,
                            "reason": "activation_temporarily_locked",
                            "message": "Demasiados intentos fallidos de activación. Espere antes de reintentar.",
                            "retry_after_seconds": locked_for,
                            "token": row["token"],
                            "server_time_utc": server_time_utc,
                            "server_ip": client_ip,
                        }
                return {
                    "allowed": False,
                    "reason": reason,
                    "message": message,
                    "token": row["token"],
                    "server_time_utc": server_time_utc,
                    "server_ip": client_ip,
                }

            expires_at = _iso_plus_seconds(ACTIVATION_TOKEN_TTL_SECONDS)
            activation_token = _create_activation_token(
                str(row["installation_id"]),
                product,
                int(meta["key_id"] if meta else 0),
                expires_at,
            )

            clear_activation_failures(str(row["installation_id"]), client_ip)

            return {
                "allowed": True,
                "reason": "activated",
                "message": "Licencia activada correctamente.",
                "token": row["token"],
                "activation_token": activation_token,
                "activation_expires_at": expires_at,
                "license_mode": "licensed",
                "license_product": product,
                "license_key": str(meta["license_key"] if meta else ""),
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        trial_row = _find_trial_activation(conn, product, fingerprint, mac_hash)

        if trial_row is None and not request_trial:
            return {
                "allowed": False,
                "reason": "activation_required",
                "message": "Ingresa una key comercial o inicia la prueba gratuita de 7 días.",
                "token": row["token"],
                "license_mode": "trial",
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        trial_row, created = _ensure_trial_activation(conn, row, product, fingerprint, mac_hash, client_ip)

        if trial_row is None:
            return {
                "allowed": False,
                "reason": "trial_error",
                "message": "No se pudo registrar la prueba gratuita.",
                "token": row["token"],
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        revoked_at = str(trial_row["revoked_at"] or "").strip()
        if revoked_at:
            return {
                "allowed": False,
                "reason": "trial_revoked",
                "message": str(trial_row["revoked_reason"] or "La prueba gratuita fue revocada."),
                "token": row["token"],
                "trial_expires_at": str(trial_row["expires_at"]),
                "license_mode": "trial",
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        if _trial_record_expired(str(trial_row["expires_at"])):
            conn.execute(
                """
                UPDATE trial_activations
                SET last_seen = ?, last_ip = ?, last_installation_id = ?, fingerprint = ?, mac_hash = ?
                WHERE id = ?
                """,
                (
                    server_time_utc,
                    client_ip,
                    str(row["installation_id"]),
                    fingerprint,
                    mac_hash,
                    int(trial_row["id"]),
                ),
            )
            conn.commit()
            return {
                "allowed": False,
                "reason": "trial_expired",
                "message": "Tu prueba gratuita de 7 días ya venció. Ingresa una licencia.",
                "token": row["token"],
                "trial_expires_at": str(trial_row["expires_at"]),
                "license_mode": "trial",
                "server_time_utc": server_time_utc,
                "server_ip": client_ip,
            }

        conn.execute(
            """
            UPDATE trial_activations
            SET last_seen = ?, last_ip = ?, last_installation_id = ?, fingerprint = ?, mac_hash = ?
            WHERE id = ?
            """,
            (
                server_time_utc,
                client_ip,
                str(row["installation_id"]),
                fingerprint,
                mac_hash,
                int(trial_row["id"]),
            ),
        )
        conn.commit()

        return {
            "allowed": True,
            "reason": "trial_started" if created else "trial_active",
            "message": "Prueba gratuita activa por 7 días." if created else "Prueba gratuita activa.",
            "token": row["token"],
            "trial_expires_at": str(trial_row["expires_at"]),
            "license_mode": "trial",
            "license_product": product,
            "server_time_utc": server_time_utc,
            "server_ip": client_ip,
        }



def revoke_activation(installation_id: str, reason: str) -> None:
    now = utc_now_iso()
    with closing(db()) as conn:
        conn.execute(
            """
            UPDATE activaciones
            SET revoked_at = ?, revoked_reason = ?
            WHERE installation_id = ? AND revoked_at IS NULL
            """,
            (now, reason, installation_id),
        )
        conn.commit()


def set_global_block(blocked: bool, message: str) -> None:
    with closing(db()) as conn:
        conn.execute(
            "UPDATE licencia_global SET blocked = ?, message = ?, updated_at = ? WHERE id = 1",
            (1 if blocked else 0, message, utc_now_iso()),
        )
        conn.commit()


def set_installation_block(installation_id: str, blocked: bool, reason: str) -> None:
    with closing(db()) as conn:
        conn.execute(
            "UPDATE instalaciones SET blocked = ?, blocked_reason = ? WHERE installation_id = ?",
            (1 if blocked else 0, reason if blocked else None, installation_id),
        )
        conn.commit()


def generate_manual_license(
    empresa: str,
    app_id: str,
    version: str,
    installation_id: str,
    hostname: str,
    usuario: str,
) -> Dict[str, str]:
    now = utc_now_iso()
    clean_installation_id = installation_id.strip() or f"MAN-{secrets.token_hex(8).upper()}"
    clean_empresa = empresa.strip() or "DEFAULT"
    clean_app_id = app_id.strip() or "kubito"
    clean_version = version.strip() or "7.0.0"
    clean_hostname = hostname.strip()
    clean_usuario = usuario.strip()
    token = secrets.token_urlsafe(24)

    with closing(db()) as conn:
        existing = conn.execute(
            "SELECT id FROM instalaciones WHERE installation_id = ?",
            (clean_installation_id,),
        ).fetchone()

        if existing:
            conn.execute(
                """
                UPDATE instalaciones
                SET token = ?, empresa = ?, app_id = ?, version = ?, hostname = ?, usuario = ?,
                    first_seen = COALESCE(first_seen, ?), last_seen = ?, blocked = 0, blocked_reason = NULL
                WHERE installation_id = ?
                """,
                (
                    token,
                    clean_empresa,
                    clean_app_id,
                    clean_version,
                    clean_hostname,
                    clean_usuario,
                    now,
                    now,
                    clean_installation_id,
                ),
            )
        else:
            conn.execute(
                """
                INSERT INTO instalaciones(
                    installation_id, token, empresa, app_id, version, hostname, usuario,
                    mac_hash, fingerprint, first_seen, last_seen, last_ip, blocked,
                    blocked_reason, total_validations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, '', '', ?, ?, 'manual', 0, NULL, 0)
                """,
                (
                    clean_installation_id,
                    token,
                    clean_empresa,
                    clean_app_id,
                    clean_version,
                    clean_hostname,
                    clean_usuario,
                    now,
                    now,
                ),
            )

        conn.commit()

    return {
        "installation_id": clean_installation_id,
        "token": token,
        "empresa": clean_empresa,
        "app_id": clean_app_id,
        "version": clean_version,
    }


def admin_overview() -> Dict[str, Any]:
    with closing(db()) as conn:
        global_state = get_global_state(conn)
        now = utc_now_iso()

        total = conn.execute("SELECT COUNT(*) AS n FROM instalaciones").fetchone()["n"]
        blocked = conn.execute("SELECT COUNT(*) AS n FROM instalaciones WHERE blocked = 1").fetchone()["n"]
        by_app_rows = conn.execute(
            """
            SELECT app_id, COUNT(*) AS n
            FROM instalaciones
            GROUP BY app_id
            ORDER BY n DESC
            """
        ).fetchall()

        recent_rows = conn.execute(
            """
            SELECT installation_id, app_id, hostname, usuario, last_ip, last_seen, blocked, blocked_reason
            FROM instalaciones
            ORDER BY last_seen DESC
            LIMIT 20
            """
        ).fetchall()
        trial_total = conn.execute("SELECT COUNT(*) AS n FROM trial_activations").fetchone()["n"]
        trial_active = conn.execute(
            "SELECT COUNT(*) AS n FROM trial_activations WHERE revoked_at IS NULL AND expires_at > ?",
            (now,),
        ).fetchone()["n"]
        trial_expired = conn.execute(
            "SELECT COUNT(*) AS n FROM trial_activations WHERE revoked_at IS NULL AND expires_at <= ?",
            (now,),
        ).fetchone()["n"]

    return {
        "global": global_state,
        "stats": {
            "total_installations": int(total),
            "blocked_installations": int(blocked),
            "active_installations": int(total) - int(blocked),
            "trial_total": int(trial_total),
            "trial_active": int(trial_active),
            "trial_expired": int(trial_expired),
            "apps": [{"app_id": r["app_id"], "count": int(r["n"])} for r in by_app_rows],
        },
        "recent": [
            {
                "installation_id": r["installation_id"],
                "app_id": r["app_id"],
                "hostname": r["hostname"],
                "usuario": r["usuario"],
                "last_ip": r["last_ip"],
                "last_seen": r["last_seen"],
                "blocked": bool(r["blocked"]),
                "blocked_reason": r["blocked_reason"],
            }
            for r in recent_rows
        ],
    }


def query_installations(
    search: str,
    app_id: str,
    blocked: str,
    limit: int,
    offset: int,
) -> Tuple[List[Dict[str, Any]], int]:
    where: List[str] = []
    params: List[Any] = []

    if search:
        token = f"%{search}%"
        where.append("(installation_id LIKE ? OR hostname LIKE ? OR usuario LIKE ? OR last_ip LIKE ? OR empresa LIKE ?)")
        params.extend([token, token, token, token, token])

    if app_id and app_id.lower() != "all":
        where.append("app_id = ?")
        params.append(app_id)

    if blocked in {"0", "1"}:
        where.append("blocked = ?")
        params.append(int(blocked))

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    with closing(db()) as conn:
        total_row = conn.execute(
            f"SELECT COUNT(*) AS n FROM instalaciones {where_sql}",
            params,
        ).fetchone()

        rows = conn.execute(
            f"""
            SELECT installation_id, token, empresa, app_id, version, hostname, usuario,
                   mac_hash, fingerprint, first_seen, last_seen, last_ip, blocked,
                   blocked_reason, total_validations
            FROM instalaciones
            {where_sql}
            ORDER BY last_seen DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    items = [
        {
            "installation_id": r["installation_id"],
            "token": r["token"],
            "empresa": r["empresa"],
            "app_id": r["app_id"],
            "version": r["version"],
            "hostname": r["hostname"],
            "usuario": r["usuario"],
            "mac_hash": r["mac_hash"],
            "fingerprint": r["fingerprint"],
            "first_seen": r["first_seen"],
            "last_seen": r["last_seen"],
            "last_ip": r["last_ip"],
            "blocked": bool(r["blocked"]),
            "blocked_reason": r["blocked_reason"],
            "total_validations": int(r["total_validations"]),
        }
        for r in rows
    ]
    return items, int(total_row["n"])


def admin_page_html(query: Dict[str, List[str]] | None = None) -> str:
    query = query or {}
    with closing(db()) as conn:
        global_state = get_global_state(conn)
        total = conn.execute("SELECT COUNT(*) AS n FROM instalaciones").fetchone()["n"]
        blocked_count = conn.execute("SELECT COUNT(*) AS n FROM instalaciones WHERE blocked = 1").fetchone()["n"]
        keys_rows = conn.execute(
            """
            SELECT k.id, k.license_key, k.product, k.seats_limit, k.blocked, k.expires_at,
                   (SELECT COUNT(*) FROM activaciones a WHERE a.key_id = k.id AND a.revoked_at IS NULL) AS active_seats
            FROM licencia_keys k
            ORDER BY k.id DESC
            LIMIT 100
            """
        ).fetchall()
        activaciones_rows = conn.execute(
            """
            SELECT a.installation_id, a.product, a.last_seen, a.revoked_at, a.revoked_reason, k.license_key
            FROM activaciones a
            JOIN licencia_keys k ON k.id = a.key_id
            ORDER BY a.last_seen DESC
            LIMIT 300
            """
        ).fetchall()
        rows = conn.execute(
            """
            SELECT installation_id, token, empresa, app_id, version, hostname, usuario,
                   last_ip, last_seen, blocked, blocked_reason, total_validations
            FROM instalaciones
            ORDER BY last_seen DESC
            LIMIT 500
            """
        ).fetchall()

    status_color = "#ef4444" if global_state["blocked"] else "#10b981"
    status_text = "BLOQUEADO" if global_state["blocked"] else "ACTIVO"
    block_toggle = "🔓 Desbloquear" if global_state["blocked"] else "🔒 Bloquear"
    active_count = total - blocked_count
    generated = str(query.get("generated", [""])[0]).strip() == "1"
    generated_installation = escape(str(query.get("installation_id", [""])[0]).strip())
    generated_token = escape(str(query.get("token", [""])[0]).strip())
    generated_empresa = escape(str(query.get("empresa", [""])[0]).strip())
    generated_app = escape(str(query.get("app_id", [""])[0]).strip())
    generated_version = escape(str(query.get("version", [""])[0]).strip())
    key_generated = str(query.get("key_generated", [""])[0]).strip() == "1"
    generated_key = escape(str(query.get("license_key", [""])[0]).strip())
    key_product = escape(str(query.get("key_product", [""])[0]).strip())
    key_seats = escape(str(query.get("key_seats", [""])[0]).strip())

    table_rows = []
    for r in rows:
        is_blocked = bool(r["blocked"])
        block_icon = "🚫" if is_blocked else "✅"
        row_bg = "bg-red-50 hover:bg-red-100" if is_blocked else "hover:bg-slate-50"
        badge_color = "bg-red-100 text-red-700" if is_blocked else "bg-green-100 text-green-700"
        installation_safe = escape(str(r["installation_id"]))
        empresa_safe = escape(str(r["empresa"]))
        app_safe = escape(str(r["app_id"]))
        version_safe = escape(str(r["version"]))
        hostname_safe = escape(str(r["hostname"] or "—"))
        usuario_safe = escape(str(r["usuario"] or "—"))
        ip_safe = escape(str(r["last_ip"] or "—"))
        reason_safe = escape(str(r["blocked_reason"] or "—"))
        seen_date = escape(str(r["last_seen"]).split("T")[0])
        token_safe = escape(str(r["token"] or ""))
        token_short = escape(str(r["token"] or "")[:10] + "..." if r["token"] else "—")
        table_rows.append(
            f'<tr class="{row_bg} transition">'
            f'<td class="px-6 py-3 font-mono text-slate-700">{installation_safe}</td>'
            f'<td class="px-6 py-3"><div class="flex items-center gap-2"><code class="bg-slate-100 px-2 py-1 rounded text-slate-700 text-xs">{token_short}</code><button type="button" data-copy="{token_safe}" class="copy-btn px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300">Copiar</button></div></td>'
            f'<td class="px-6 py-3"><span class="bg-blue-100 text-blue-700 px-2 py-1 rounded text-xs font-semibold">{empresa_safe}</span></td>'
            f'<td class="px-6 py-3"><span class="bg-sky-100 text-sky-700 px-2 py-1 rounded text-xs font-semibold">{app_safe}</span></td>'
            f'<td class="px-6 py-3"><code class="bg-slate-100 px-2 py-1 rounded text-slate-700">{version_safe}</code></td>'
            f'<td class="px-6 py-3 text-slate-600">{hostname_safe}</td>'
            f'<td class="px-6 py-3 text-slate-600">{usuario_safe}</td>'
            f'<td class="px-6 py-3 font-mono text-slate-600 text-xs">{ip_safe}</td>'
            f'<td class="px-6 py-3 text-slate-600 text-xs">{seen_date}</td>'
            f'<td class="px-6 py-3"><span class="{badge_color} px-2 py-1 rounded text-xs font-semibold">{block_icon} {"Bloqueado" if is_blocked else "Activo"}</span></td>'
            f'<td class="px-6 py-3 text-slate-600 text-xs truncate max-w-xs">{reason_safe}</td>'
            f'<td class="px-6 py-3 text-center font-bold text-slate-900">{r["total_validations"]}</td>'
            "</tr>"
        )

    keys_table_rows = []
    for k in keys_rows:
        product = escape(str(k["product"]))
        key_text = escape(str(k["license_key"]))
        seats_limit = "ilimitado" if k["seats_limit"] is None else str(int(k["seats_limit"]))
        seats_used = int(k["active_seats"])
        blocked = bool(k["blocked"])
        expires = escape(str(k["expires_at"] or "—"))
        status_badge = (
            '<span class="px-2 py-1 rounded text-xs font-semibold bg-red-100 text-red-700">Bloqueada</span>'
            if blocked
            else '<span class="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-700">Activa</span>'
        )
        keys_table_rows.append(
            "<tr class=\"hover:bg-slate-50\">"
            f"<td class=\"px-4 py-2 font-mono text-xs\"><div class=\"flex items-center gap-2\"><span>{key_text}</span><button type=\"button\" data-copy=\"{key_text}\" class=\"copy-btn px-2 py-1 text-xs rounded bg-slate-200 hover:bg-slate-300\">Copiar</button></div></td>"
            f"<td class=\"px-4 py-2\">{product}</td>"
            f"<td class=\"px-4 py-2\">{seats_used}/{escape(seats_limit)}</td>"
            f"<td class=\"px-4 py-2 text-xs\">{expires}</td>"
            f"<td class=\"px-4 py-2\">{status_badge}</td>"
            "</tr>"
        )

    activaciones_table_rows = []
    for a in activaciones_rows:
        installation_id = escape(str(a["installation_id"]))
        product = escape(str(a["product"]))
        key_text = escape(str(a["license_key"]))
        last_seen = escape(str(a["last_seen"]).split("T")[0])
        revoked_at = str(a["revoked_at"] or "").strip()
        revoked_reason = escape(str(a["revoked_reason"] or "—"))
        estado = (
            '<span class="px-2 py-1 rounded text-xs font-semibold bg-red-100 text-red-700">Revocada</span>'
            if revoked_at
            else '<span class="px-2 py-1 rounded text-xs font-semibold bg-green-100 text-green-700">Activa</span>'
        )
        activaciones_table_rows.append(
            "<tr class=\"hover:bg-slate-50\">"
            f"<td class=\"px-4 py-2 font-mono text-xs\">{installation_id}</td>"
            f"<td class=\"px-4 py-2\">{product}</td>"
            f"<td class=\"px-4 py-2 font-mono text-xs\">{key_text}</td>"
            f"<td class=\"px-4 py-2 text-xs\">{last_seen}</td>"
            f"<td class=\"px-4 py-2\">{estado}</td>"
            f"<td class=\"px-4 py-2 text-xs\">{revoked_reason}</td>"
            "</tr>"
        )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Panel de Licencias - Kubo</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-100">
  <div class="min-h-screen p-6 md:p-8">
    <div class="max-w-7xl mx-auto">
      <!-- Header -->
      <div class="flex items-center justify-between mb-8">
        <div>
                    <h1 class="text-4xl font-bold text-slate-900">Panel de Licencias</h1>
                    <p class="text-slate-600 mt-1">Control de activaciones Kubo/Kubito</p>
        </div>
                <div class="px-4 py-2 bg-gradient-to-r from-slate-800 to-slate-700 text-white rounded-lg font-semibold shadow-lg">
                    Kubo Suite
        </div>
      </div>

            {f'''<div class="bg-emerald-50 border border-emerald-300 rounded-lg p-4 mb-6">
                <h3 class="text-emerald-900 font-bold mb-2">Licencia generada</h3>
                <p class="text-sm text-emerald-800 mb-3">Guarda estos datos para registrar la instalación en el cliente.</p>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                    <div><span class="font-semibold">Installation ID:</span> <code class="bg-emerald-100 px-1 rounded">{generated_installation}</code></div>
                    <div><span class="font-semibold">Token:</span> <code class="bg-emerald-100 px-1 rounded break-all">{generated_token}</code> <button type="button" data-copy="{generated_token}" class="copy-btn px-2 py-1 text-xs rounded bg-emerald-200 hover:bg-emerald-300">Copiar</button></div>
                    <div><span class="font-semibold">Empresa:</span> {generated_empresa}</div>
                    <div><span class="font-semibold">App:</span> {generated_app} ({generated_version})</div>
                </div>
            </div>''' if generated and generated_installation and generated_token else ''}

            {f'''<div class="bg-cyan-50 border border-cyan-300 rounded-lg p-4 mb-6">
                <h3 class="text-cyan-900 font-bold mb-2">Key comercial generada</h3>
                <div class="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm text-cyan-900">
                    <div><span class="font-semibold">Key:</span> <code class="bg-cyan-100 px-1 rounded break-all">{generated_key}</code> <button type="button" data-copy="{generated_key}" class="copy-btn px-2 py-1 text-xs rounded bg-cyan-200 hover:bg-cyan-300">Copiar</button></div>
                    <div><span class="font-semibold">Producto:</span> {key_product}</div>
                    <div><span class="font-semibold">Seats:</span> {key_seats}</div>
                </div>
            </div>''' if key_generated and generated_key else ''}

      <!-- Stats Dashboard -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500">
          <div class="text-sm font-semibold text-slate-600 uppercase tracking-wide">Total</div>
          <div class="text-4xl font-bold text-slate-900 mt-2">{total}</div>
        </div>
        <div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-green-500">
          <div class="text-sm font-semibold text-slate-600 uppercase tracking-wide">Activas</div>
          <div class="text-4xl font-bold text-green-600 mt-2">{active_count}</div>
        </div>
        <div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-red-500">
          <div class="text-sm font-semibold text-slate-600 uppercase tracking-wide">Bloqueadas</div>
          <div class="text-4xl font-bold text-red-600 mt-2">{blocked_count}</div>
        </div>
      </div>

      <!-- Global Status Card -->
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
          🌐 Estado Global
        </h2>
        <div class="bg-gradient-to-r from-blue-50 to-blue-100 border border-blue-200 rounded-lg p-6 mb-4">
          <div class="flex items-center justify-between mb-4">
            <div>
              <span class="inline-block px-4 py-2 rounded-lg font-semibold text-white bg-gradient-to-r from-{'green-500 to-green-600' if not global_state['blocked'] else 'red-500 to-red-600'}">
                {status_text}
              </span>
                            <p class="text-slate-700 mt-3 text-sm"><strong>Mensaje:</strong> {escape(str(global_state['message']))}</p>
            </div>
          </div>
        </div>
        <form method="post" action="/admin/global" class="flex gap-3 flex-wrap">
          <input type="hidden" name="blocked" value="{0 if global_state['blocked'] else 1}" />
                    <input type="text" name="message" placeholder="Mensaje de estado..." value="{escape(str(global_state['message']))}" 
                 class="flex-1 min-w-64 px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
          <button type="submit" class="px-6 py-2 rounded-lg font-semibold text-white transition transform hover:scale-105 bg-gradient-to-r from-{'green-500 to-green-600 hover:from-green-600 hover:to-green-700' if global_state['blocked'] else 'red-500 to-red-600 hover:from-red-600 hover:to-red-700'}">
            {block_toggle}
          </button>
        </form>
      </div>

            <!-- Manual License Generation -->
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
                    🧩 Generar Licencia Manual
                </h2>
                <p class="text-slate-600 text-sm mb-4">Crea o regenera token para una instalación sin esperar el primer handshake del cliente.</p>
                <form method="post" action="/admin/generate-license" class="grid grid-cols-1 md:grid-cols-3 gap-3">
                    <input type="text" name="empresa" placeholder="Empresa (ej: Kubo Corp)" required
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500" />
                    <select name="app_id" class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500">
                        <option value="kubito">kubito</option>
                        <option value="kubo">kubo</option>
                    </select>
                    <input type="text" name="version" value="7.0.0" placeholder="Version"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500" />
                    <input type="text" name="installation_id" placeholder="Installation ID (opcional)"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 md:col-span-2" />
                    <input type="text" name="hostname" placeholder="Hostname (opcional)"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500" />
                    <input type="text" name="usuario" placeholder="Usuario (opcional)"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-sky-500 md:col-span-2" />
                    <button type="submit" class="px-4 py-2 bg-gradient-to-r from-sky-600 to-sky-700 text-white rounded-lg font-semibold hover:from-sky-700 hover:to-sky-800 transition">
                        Generar licencia
                    </button>
                </form>
            </div>

            <!-- Runtime Settings -->
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-xl font-bold text-slate-900 mb-4 flex items-center gap-2">⚙️ Configuracion Aplicada</h2>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                    <div class="bg-slate-50 rounded-lg p-3"><span class="font-semibold">Host/Puerto:</span> <code>{escape(HOST)}:{PORT}</code></div>
                    <div class="bg-slate-50 rounded-lg p-3"><span class="font-semibold">Modo:</span> <code>{escape(TICKETS_MODE)}</code></div>
                    <div class="bg-slate-50 rounded-lg p-3"><span class="font-semibold">Strict security:</span> <code>{'1' if STRICT_SECURITY else '0'}</code></div>
                    <div class="bg-slate-50 rounded-lg p-3"><span class="font-semibold">CORS permitidos:</span> <code>{escape(', '.join(CORS_ALLOWED_ORIGINS) or '(vacio)')}</code></div>
                    <div class="bg-slate-50 rounded-lg p-3"><span class="font-semibold">Rate validate:</span> <code>{VALIDATE_RATE_LIMIT_MAX}/{VALIDATE_RATE_LIMIT_WINDOW}s</code></div>
                    <div class="bg-slate-50 rounded-lg p-3"><span class="font-semibold">Payload max:</span> <code>validate {MAX_JSON_BYTES_VALIDATE}, admin {MAX_JSON_BYTES_ADMIN}, support {MAX_JSON_BYTES_SUPPORT}</code></div>
                </div>
            </div>

      <!-- Installation Management Card -->
      <div class="bg-white rounded-lg shadow-md p-6 mb-6">
        <h2 class="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">
          🔐 Gestión de Instalaciones
        </h2>
        
        <div class="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <p class="text-amber-900 text-sm">
            💡 Busca una instalación por ID y luego bloqueala o desbloquéala según sea necesario.
          </p>
        </div>

        <!-- Search -->
        <div class="mb-6">
          <input type="text" id="search-install" placeholder="Buscar installation_id..." 
                 class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent" />
        </div>

        <!-- Block Installation -->
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <h3 class="text-sm font-semibold text-slate-700 mb-3">Bloquear Instalación</h3>
            <form method="post" action="/admin/installation" class="space-y-3">
              <input type="text" name="installation_id" placeholder="installation_id" required
                     class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500" />
              <input type="text" name="reason" placeholder="Razón de bloqueo (opcional)"
                     class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500" />
              <input type="hidden" name="blocked" value="1" />
              <button type="submit" class="w-full px-4 py-2 bg-gradient-to-r from-red-500 to-red-600 text-white rounded-lg font-semibold hover:from-red-600 hover:to-red-700 transition">
                🚫 Bloquear
              </button>
            </form>
          </div>
          
          <div>
            <h3 class="text-sm font-semibold text-slate-700 mb-3">Desbloquear Instalación</h3>
            <form method="post" action="/admin/installation" class="space-y-3">
              <input type="text" name="installation_id" placeholder="installation_id" required
                     class="w-full px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500" />
              <input type="hidden" name="blocked" value="0" />
              <input type="hidden" name="reason" value="" />
              <button type="submit" class="w-full px-4 py-2 bg-gradient-to-r from-green-500 to-green-600 text-white rounded-lg font-semibold hover:from-green-600 hover:to-green-700 transition">
                🔓 Desbloquear
              </button>
            </form>
          </div>
        </div>
      </div>

            <!-- License Keys -->
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">🔑 Keys Comerciales</h2>
                <form method="post" action="/admin/license-key" class="grid grid-cols-1 md:grid-cols-4 gap-3 mb-5">
                    <select name="product" class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500">
                        <option value="kubo">kubo (1 equipo)</option>
                        <option value="kubito">kubito (multi-equipo)</option>
                    </select>
                    <input type="number" name="seats_limit" min="1" placeholder="Seats (kubito)"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    <input type="text" name="expires_at" placeholder="Expira ISO opcional"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    <input type="text" name="notes" placeholder="Notas"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500" />
                    <button type="submit" class="md:col-span-4 px-4 py-2 bg-gradient-to-r from-cyan-600 to-cyan-700 text-white rounded-lg font-semibold hover:from-cyan-700 hover:to-cyan-800 transition">
                        Crear key comercial
                    </button>
                </form>
                <div class="overflow-x-auto border border-slate-200 rounded-lg">
                    <table class="w-full text-sm">
                        <thead class="bg-slate-100">
                            <tr>
                                <th class="px-4 py-2 text-left">Key</th>
                                <th class="px-4 py-2 text-left">Producto</th>
                                <th class="px-4 py-2 text-left">Seats</th>
                                <th class="px-4 py-2 text-left">Expira</th>
                                <th class="px-4 py-2 text-left">Estado</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200">{''.join(keys_table_rows)}</tbody>
                    </table>
                </div>
            </div>

            <!-- Activations -->
            <div class="bg-white rounded-lg shadow-md p-6 mb-6">
                <h2 class="text-xl font-bold text-slate-900 mb-6 flex items-center gap-2">🧾 Activaciones y Revocación</h2>
                <form method="post" action="/admin/revoke-activation" class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
                    <input type="text" name="installation_id" placeholder="installation_id a revocar" required
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500" />
                    <input type="text" name="reason" placeholder="Razón de revocación"
                                 class="px-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-rose-500" />
                    <button type="submit" class="px-4 py-2 bg-gradient-to-r from-rose-600 to-rose-700 text-white rounded-lg font-semibold hover:from-rose-700 hover:to-rose-800 transition">
                        Revocar activación
                    </button>
                </form>
                <div class="overflow-x-auto border border-slate-200 rounded-lg">
                    <table class="w-full text-sm">
                        <thead class="bg-slate-100">
                            <tr>
                                <th class="px-4 py-2 text-left">Installation ID</th>
                                <th class="px-4 py-2 text-left">Producto</th>
                                <th class="px-4 py-2 text-left">Key</th>
                                <th class="px-4 py-2 text-left">Último uso</th>
                                <th class="px-4 py-2 text-left">Estado</th>
                                <th class="px-4 py-2 text-left">Razón</th>
                            </tr>
                        </thead>
                        <tbody class="divide-y divide-slate-200">{''.join(activaciones_table_rows)}</tbody>
                    </table>
                </div>
            </div>

      <!-- Installations Table -->
      <div class="bg-white rounded-lg shadow-md overflow-hidden">
        <div class="p-6 border-b border-slate-200">
          <div class="flex items-center justify-between">
            <h2 class="text-xl font-bold text-slate-900 flex items-center gap-2">
              📊 Instalaciones Registradas
            </h2>
            <div class="text-sm text-slate-600">
              Total: <span id="total-records">{total}</span> | Página <span id="current-page">1</span> de <span id="total-pages">1</span>
            </div>
          </div>
        </div>
        
        <div class="overflow-x-auto max-h-screen overflow-y-auto">
          <table class="w-full text-sm">
            <thead class="bg-gradient-to-r from-slate-100 to-slate-50 border-b border-slate-200 sticky top-0">
              <tr>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">ID Instalación</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Token</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Empresa</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">App</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Versión</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Hostname</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Usuario</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">IP Última</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Visto</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Estado</th>
                <th class="px-6 py-3 text-left font-semibold text-slate-700">Razón</th>
                <th class="px-6 py-3 text-center font-semibold text-slate-700">Validaciones</th>
              </tr>
            </thead>
                        <tbody id="installations-tbody" class="divide-y divide-slate-200">
              {''.join(table_rows)}
            </tbody>
          </table>
        </div>

        <div class="p-4 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-4">
          <div class="flex items-center gap-2">
            <label class="text-sm text-slate-600">Filas por página:</label>
            <select id="rows-per-page" class="px-3 py-1 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="10">10</option>
              <option value="20" selected>20</option>
              <option value="50">50</option>
              <option value="100">100</option>
            </select>
          </div>
          
          <div class="flex items-center gap-2">
            <button id="prev-page" class="px-3 py-1 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold text-sm transition">← Anterior</button>
            <div class="flex items-center gap-1">
              <input type="number" id="page-input" min="1" value="1" class="w-16 px-2 py-1 border border-slate-300 rounded-lg text-sm text-center focus:outline-none focus:ring-2 focus:ring-blue-500" />
              <button id="go-page" class="px-3 py-1 rounded-lg bg-blue-500 hover:bg-blue-600 text-white font-semibold text-sm transition">Ir</button>
            </div>
            <button id="next-page" class="px-3 py-1 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 font-semibold text-sm transition">Siguiente →</button>
          </div>
        </div>
      </div>

            <div id="copy-toast" class="fixed bottom-4 right-4 hidden px-4 py-2 rounded-lg bg-slate-900 text-white text-sm shadow-lg">
                Copiado al portapapeles
            </div>
    </div>
  </div>

  <script>
        let currentPage = 1;
        let rowsPerPage = 20;
        let allRows = [];

        function showCopyToast(msg) {{
            const toast = document.getElementById('copy-toast');
            toast.textContent = msg;
            toast.classList.remove('hidden');
            setTimeout(() => toast.classList.add('hidden'), 1400);
        }}

        async function copyText(text) {{
            if (!text) return;
            try {{
                await navigator.clipboard.writeText(text);
                showCopyToast('Copiado');
            }} catch (e) {{
                showCopyToast('No se pudo copiar');
            }}
        }}

        function setupPagination() {{
            allRows = Array.from(document.querySelectorAll('#installations-tbody tr'));
            const totalPages = Math.ceil(allRows.length / rowsPerPage);
            
            document.getElementById('total-records').textContent = allRows.length;
            document.getElementById('total-pages').textContent = totalPages || 1;
            
            updatePageDisplay();
        }}

        function updatePageDisplay() {{
            const totalPages = Math.ceil(allRows.length / rowsPerPage);
            
            if (currentPage < 1) currentPage = 1;
            if (currentPage > totalPages && totalPages > 0) currentPage = totalPages;
            
            const start = (currentPage - 1) * rowsPerPage;
            const end = start + rowsPerPage;
            
            allRows.forEach((row, idx) => {{
                row.style.display = idx >= start && idx < end ? '' : 'none';
            }});
            
            document.getElementById('current-page').textContent = totalPages > 0 ? currentPage : 1;
            document.getElementById('total-pages').textContent = totalPages || 1;
            document.getElementById('page-input').value = currentPage;
            
            document.getElementById('prev-page').disabled = currentPage <= 1;
            document.getElementById('next-page').disabled = currentPage >= totalPages;
        }}

        document.getElementById('rows-per-page').addEventListener('change', (e) => {{
            rowsPerPage = parseInt(e.target.value);
            currentPage = 1;
            updatePageDisplay();
        }});

        document.getElementById('prev-page').addEventListener('click', () => {{
            currentPage--;
            updatePageDisplay();
        }});

        document.getElementById('next-page').addEventListener('click', () => {{
            currentPage++;
            updatePageDisplay();
        }});

        document.getElementById('go-page').addEventListener('click', () => {{
            const page = parseInt(document.getElementById('page-input').value) || 1;
            currentPage = page;
            updatePageDisplay();
        }});

        document.getElementById('page-input').addEventListener('keypress', (e) => {{
            if (e.key === 'Enter') {{
                const page = parseInt(e.target.value) || 1;
                currentPage = page;
                updatePageDisplay();
            }}
        }});

        document.querySelectorAll('.copy-btn').forEach(btn => {{
            btn.addEventListener('click', () => copyText(btn.getAttribute('data-copy') || ''));
        }});

        document.getElementById('search-install').addEventListener('input', (e) => {{
            const query = e.target.value.toLowerCase();
            allRows.forEach(row => {{
                const id = row.cells[0].textContent.toLowerCase();
                row.style.display = id.includes(query) ? '' : 'none';
            }});
        }});

        setupPagination();
  </script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "TicketsLicSrv/1.0"

    def _admin_authorized(self) -> bool:
        return self.headers.get("X-Admin-Key", "") == ADMIN_KEY

    def _cors(self) -> None:
        origin = self.headers.get("Origin", "").strip()
        if origin and is_origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Admin-Key")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")

    def _json(self, status: int, payload: Dict[str, Any]) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html(self, status: int, html: str) -> None:
        data = html.encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self, max_bytes: int) -> Dict[str, Any]:
        raw_len = int(self.headers.get("Content-Length", "0") or 0)
        if raw_len > max_bytes:
            raise PayloadTooLargeError(f"payload_too_large>{max_bytes}")
        raw = self.rfile.read(raw_len) if raw_len > 0 else b"{}"
        if len(raw) > max_bytes:
            raise PayloadTooLargeError(f"payload_too_large>{max_bytes}")
        return json.loads(raw.decode("utf-8", errors="ignore"))

    def _read_form(self, max_bytes: int) -> Dict[str, str]:
        raw_len = int(self.headers.get("Content-Length", "0") or 0)
        if raw_len > max_bytes:
            raise PayloadTooLargeError(f"payload_too_large>{max_bytes}")
        raw = self.rfile.read(raw_len).decode("utf-8", errors="ignore")
        parsed = parse_qs(raw, keep_blank_values=True)
        return {k: (v[0] if v else "") for k, v in parsed.items()}

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/health":
            try:
                with closing(db()) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) as total FROM instalaciones")
                    install_count = cursor.fetchone()[0]
                    
                    health = {
                        "status": "healthy",
                        "timestamp": utc_now_iso(),
                        "service": "licencias",
                        "database": "ok",
                        "installations_count": install_count,
                        "version": "7.0.0"
                    }
                    self._json(HTTPStatus.OK, health)
                    if _logger:
                        log_info(_logger, "Health check OK")
            except Exception as e:
                if _logger:
                    log_error(_logger, f"Health check failed: {e}", exception=e)
                self._json(HTTPStatus.SERVICE_UNAVAILABLE, {"status": "unhealthy", "error": str(e)})
            return

        if path == "/admin":
            self._html(HTTPStatus.OK, admin_page_html(query))
            return

        if path == "/api/v1/public/status":
            with closing(db()) as conn:
                self._json(HTTPStatus.OK, get_global_state(conn))
            return

        if path == "/api/v1/admin/overview":
            if not self._admin_authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            self._json(HTTPStatus.OK, admin_overview())
            return

        if path == "/api/v1/admin/installations":
            if not self._admin_authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return

            search = str(query.get("search", [""])[0]).strip()
            app_id = str(query.get("app_id", ["all"])[0]).strip()
            blocked = str(query.get("blocked", ["all"])[0]).strip()
            try:
                limit = min(MAX_LIMIT, max(1, int(query.get("limit", ["100"])[0])))
                offset = max(0, int(query.get("offset", ["0"])[0]))
            except ValueError:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "bad_pagination"})
                return

            items, total = query_installations(search, app_id, blocked, limit, offset)
            self._json(
                HTTPStatus.OK,
                {
                    "items": items,
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            )
            return

        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/v1/support/report":
            try:
                payload = self._read_json(MAX_JSON_BYTES_SUPPORT)
                app_id = str(payload.get("app_id", "")).strip() or "unknown"
                tipo = str(payload.get("type", "sugerencia")).strip() or "sugerencia"
                mensaje = str(payload.get("message", "")).strip()
                version = str(payload.get("version", "")).strip()
                contact = str(payload.get("contact", "")).strip()
                extra = payload.get("extra", {})

                if not mensaje:
                    self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "message_required"})
                    return

                if len(mensaje) > 4000:
                    self._json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "message_too_long"})
                    return

                with closing(db()) as conn:
                    cur = conn.execute(
                        """
                        INSERT INTO soporte_eventos(created_at, app_id, tipo, mensaje, version, contact, remote_ip, extra_json)
                        VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            utc_now_iso(),
                            app_id,
                            tipo,
                            mensaje,
                            version,
                            contact,
                            self.client_address[0],
                            json.dumps(extra, ensure_ascii=False),
                        ),
                    )
                    conn.commit()
                    event_id = int(cur.lastrowid or 0)

                self._json(HTTPStatus.OK, {"ok": True, "event_id": event_id})
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"ok": False, "error": "payload_too_large"})
            except Exception:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": "support_report_failed"})
            return

        if path == "/api/v1/validate":
            try:
                if validate_rate_limited(self.client_address[0]):
                    self._json(
                        HTTPStatus.TOO_MANY_REQUESTS,
                        {
                            "allowed": False,
                            "reason": "rate_limited",
                            "message": "Demasiadas solicitudes. Intente nuevamente en unos segundos.",
                        },
                    )
                    return

                payload = self._read_json(MAX_JSON_BYTES_VALIDATE)
                result = validate_request(payload, self.client_address[0])
                self._json(HTTPStatus.OK, result)
            except PayloadTooLargeError:
                self._json(
                    HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                    {
                        "allowed": False,
                        "reason": "payload_too_large",
                        "message": f"Payload excede límite de {MAX_JSON_BYTES_VALIDATE} bytes.",
                    },
                )
            except ValueError as exc:
                self._json(HTTPStatus.BAD_REQUEST, {"allowed": False, "reason": "bad_request", "message": str(exc)})
            except Exception:
                self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"allowed": False, "reason": "server_error", "message": "Error interno de licencias"})
            return

        if path == "/admin/global":
            try:
                form = self._read_form(MAX_FORM_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return
            blocked = str(form.get("blocked", "0")) == "1"
            message = str(form.get("message", "Servicio disponible"))
            set_global_block(blocked, message)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/admin")
            self.end_headers()
            return

        if path == "/admin/installation":
            try:
                form = self._read_form(MAX_FORM_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return
            installation_id = str(form.get("installation_id", "")).strip()
            blocked_str = str(form.get("blocked", "0")).strip()
            reason = str(form.get("reason", "")).strip()
            
            blocked = blocked_str == "1"
            
            if not installation_id:
                self.send_response(HTTPStatus.BAD_REQUEST)
                self.send_header("Location", "/admin")
                self.end_headers()
                return
            
            if not blocked and not reason:
                reason = None
            elif blocked and not reason:
                reason = "Instalación bloqueada"
            
            set_installation_block(installation_id, blocked, reason)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/admin")
            self.end_headers()
            return

        if path == "/admin/generate-license":
            try:
                form = self._read_form(MAX_FORM_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return

            empresa = str(form.get("empresa", "")).strip()
            app_id = str(form.get("app_id", "kubito")).strip()
            version = str(form.get("version", "7.0.0")).strip()
            installation_id = str(form.get("installation_id", "")).strip()
            hostname = str(form.get("hostname", "")).strip()
            usuario = str(form.get("usuario", "")).strip()

            if not empresa:
                self.send_response(HTTPStatus.SEE_OTHER)
                self.send_header("Location", "/admin")
                self.end_headers()
                return

            created = generate_manual_license(
                empresa=empresa,
                app_id=app_id,
                version=version,
                installation_id=installation_id,
                hostname=hostname,
                usuario=usuario,
            )
            query_params = urlencode(
                {
                    "generated": "1",
                    "installation_id": created["installation_id"],
                    "token": created["token"],
                    "empresa": created["empresa"],
                    "app_id": created["app_id"],
                    "version": created["version"],
                }
            )
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", f"/admin?{query_params}")
            self.end_headers()
            return

        if path == "/admin/license-key":
            try:
                form = self._read_form(MAX_FORM_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return

            product = str(form.get("product", "kubito")).strip()
            seats_raw = str(form.get("seats_limit", "")).strip()
            expires_at = str(form.get("expires_at", "")).strip() or None
            notes = str(form.get("notes", "")).strip()

            seats_limit = None
            if seats_raw:
                try:
                    seats_limit = max(1, int(seats_raw))
                except ValueError:
                    seats_limit = None

            created = create_license_key(product, seats_limit, expires_at, notes)
            params = urlencode(
                {
                    "key_generated": "1",
                    "license_key": created["license_key"],
                    "key_product": created["product"],
                    "key_seats": "ilimitado" if created["seats_limit"] is None else str(created["seats_limit"]),
                }
            )
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", f"/admin?{params}")
            self.end_headers()
            return

        if path == "/admin/revoke-activation":
            try:
                form = self._read_form(MAX_FORM_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return

            installation_id = str(form.get("installation_id", "")).strip()
            reason = str(form.get("reason", "Revocada por administrador")).strip() or "Revocada por administrador"
            if installation_id:
                revoke_activation(installation_id, reason)
            self.send_response(HTTPStatus.SEE_OTHER)
            self.send_header("Location", "/admin")
            self.end_headers()
            return

        if path == "/api/v1/admin/global":
            if not self._admin_authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                payload = self._read_json(MAX_JSON_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return
            blocked = bool(payload.get("blocked", False))
            message = str(payload.get("message", "Servicio disponible")).strip() or "Servicio disponible"
            set_global_block(blocked, message)
            with closing(db()) as conn:
                self._json(HTTPStatus.OK, {"ok": True, "global": get_global_state(conn)})
            return

        if path == "/api/v1/admin/installations/block":
            if not self._admin_authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                payload = self._read_json(MAX_JSON_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return
            installation_id = str(payload.get("installation_id", "")).strip()
            if not installation_id:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "installation_id_required"})
                return

            blocked = bool(payload.get("blocked", False))
            reason = str(payload.get("reason", "Instalación bloqueada por administrador.")).strip() or "Instalación bloqueada por administrador."
            set_installation_block(installation_id, blocked, reason)
            self._json(HTTPStatus.OK, {"ok": True, "installation_id": installation_id, "blocked": blocked})
            return

        if path == "/api/v1/admin/keys/create":
            if not self._admin_authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                payload = self._read_json(MAX_JSON_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return
            product = str(payload.get("product", "kubito")).strip()
            seats_limit_raw = payload.get("seats_limit", None)
            seats_limit = None
            if seats_limit_raw is not None:
                try:
                    seats_limit = max(1, int(seats_limit_raw))
                except Exception:
                    seats_limit = None
            expires_at = str(payload.get("expires_at", "")).strip() or None
            notes = str(payload.get("notes", "")).strip()
            created = create_license_key(product, seats_limit, expires_at, notes)
            self._json(HTTPStatus.OK, {"ok": True, "key": created})
            return

        if path == "/api/v1/admin/activations/revoke":
            if not self._admin_authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            try:
                payload = self._read_json(MAX_JSON_BYTES_ADMIN)
            except PayloadTooLargeError:
                self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "payload_too_large"})
                return
            installation_id = str(payload.get("installation_id", "")).strip()
            if not installation_id:
                self._json(HTTPStatus.BAD_REQUEST, {"error": "installation_id_required"})
                return
            reason = str(payload.get("reason", "Revocada por administrador")).strip() or "Revocada por administrador"
            revoke_activation(installation_id, reason)
            self._json(HTTPStatus.OK, {"ok": True, "installation_id": installation_id})
            return

        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})


def main() -> None:
    _validar_config_seguridad_inicio()
    init_db()
    print(f"[LICENCIAS] Servicio iniciado en http://{HOST}:{PORT}")
    print("[LICENCIAS] Panel admin: /admin")
    print("[LICENCIAS] API React: /api/v1/admin/*")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.serve_forever()


if __name__ == "__main__":
    main()
