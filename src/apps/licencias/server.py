"""Servicio central de licencias para Sistema Tickets.

API:
- POST /api/v1/validate                       (cliente emisora/receptora)
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
from contextlib import closing
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qs, urlparse

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
TICKETS_MODE = os.getenv("TICKETS_MODE", "desarrollo").strip().lower()
STRICT_SECURITY = os.getenv("TICKETS_STRICT_SECURITY", "0").strip() == "1"
MAX_LIMIT = 1000
MAX_JSON_BYTES_VALIDATE = int(os.getenv("TICKETS_LICENSE_MAX_JSON_VALIDATE", "65536"))
MAX_JSON_BYTES_ADMIN = int(os.getenv("TICKETS_LICENSE_MAX_JSON_ADMIN", "32768"))
MAX_FORM_BYTES_ADMIN = int(os.getenv("TICKETS_LICENSE_MAX_FORM_ADMIN", "16384"))
VALIDATE_RATE_LIMIT_MAX = int(os.getenv("TICKETS_LICENSE_VALIDATE_RATE_MAX", "60"))
VALIDATE_RATE_LIMIT_WINDOW = int(os.getenv("TICKETS_LICENSE_VALIDATE_RATE_WINDOW", "60"))
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


class PayloadTooLargeError(ValueError):
    """Error de payload excesivo para devolver HTTP 413."""


def _validar_config_seguridad_inicio() -> None:
    advertencias: List[str] = []
    errores: List[str] = []

    if ADMIN_KEY == "cambiar-esta-clave" or len(ADMIN_KEY) < 24:
        advertencias.append("ADMIN key débil o por defecto en servidor de licencias.")
        if STRICT_SECURITY or TICKETS_MODE == "produccion":
            errores.append("Defina TICKETS_LICENSE_ADMIN_KEY robusta (>=24 caracteres).")

    if not CORS_ALLOWED_ORIGINS:
        advertencias.append("TICKETS_LICENSE_CORS_ORIGINS está vacío.")

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

        cur = conn.execute("SELECT id FROM licencia_global WHERE id = 1")
        if cur.fetchone() is None:
            conn.execute(
                "INSERT INTO licencia_global(id, blocked, message, updated_at) VALUES(1, 0, ?, ?)",
                ("Servicio disponible", utc_now_iso()),
            )
        conn.commit()


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

        if global_state["blocked"]:
            return {
                "allowed": False,
                "reason": "global_blocked",
                "message": global_state["message"],
                "token": row["token"],
                "server_ip": client_ip,
            }

        if bool(row["blocked"]):
            return {
                "allowed": False,
                "reason": "installation_blocked",
                "message": row["blocked_reason"] or "Instalación bloqueada por administrador.",
                "token": row["token"],
                "server_ip": client_ip,
            }

        return {
            "allowed": True,
            "reason": "ok",
            "message": "Licencia válida.",
            "token": row["token"],
            "server_ip": client_ip,
        }


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


def admin_overview() -> Dict[str, Any]:
    with closing(db()) as conn:
        global_state = get_global_state(conn)

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

    return {
        "global": global_state,
        "stats": {
            "total_installations": int(total),
            "blocked_installations": int(blocked),
            "active_installations": int(total) - int(blocked),
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


def admin_page_html() -> str:
    with closing(db()) as conn:
        global_state = get_global_state(conn)
        rows = conn.execute(
            """
            SELECT installation_id, token, empresa, app_id, version, hostname, usuario,
                   last_ip, last_seen, blocked, blocked_reason, total_validations
            FROM instalaciones
            ORDER BY last_seen DESC
            LIMIT 500
            """
        ).fetchall()

    status_text = "BLOQUEADO" if global_state["blocked"] else "ACTIVO"
    block_toggle = "DESBLOQUEAR GLOBAL" if global_state["blocked"] else "BLOQUEAR GLOBAL"

    table_rows = []
    for r in rows:
        block_state = "SI" if r["blocked"] else "NO"
        table_rows.append(
            "<tr>"
            f"<td>{r['installation_id']}</td>"
            f"<td>{r['empresa']}</td>"
            f"<td>{r['app_id']}</td>"
            f"<td>{r['version']}</td>"
            f"<td>{r['hostname'] or ''}</td>"
            f"<td>{r['usuario'] or ''}</td>"
            f"<td>{r['last_ip'] or ''}</td>"
            f"<td>{r['last_seen']}</td>"
            f"<td>{block_state}</td>"
            f"<td>{r['blocked_reason'] or ''}</td>"
            f"<td>{r['total_validations']}</td>"
            "</tr>"
        )

    return f"""
<!doctype html>
<html lang=\"es\">
<head>
  <meta charset=\"utf-8\" />
  <title>Panel de Licencias - Tickets</title>
  <style>
    body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f6f8fb; color: #111; }}
    h1 {{ margin: 0 0 12px; }}
    .card {{ background: white; border-radius: 10px; padding: 16px; margin-bottom: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    button {{ padding: 8px 12px; border: 0; border-radius: 8px; background: #1f6feb; color: white; cursor: pointer; }}
    input {{ padding: 8px; min-width: 320px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
    th, td {{ border: 1px solid #ddd; padding: 6px; text-align: left; }}
    th {{ background: #eef3fb; position: sticky; top: 0; }}
    .scroll {{ max-height: 540px; overflow: auto; }}
  </style>
</head>
<body>
  <h1>Panel de Licencias - Tickets</h1>

  <div class=\"card\">
    <p><b>Estado Global:</b> {status_text} | <b>Mensaje:</b> {global_state['message']}</p>
    <form method=\"post\" action=\"/admin/global\">
      <input type=\"hidden\" name=\"blocked\" value=\"{0 if global_state['blocked'] else 1}\" />
      <input name=\"message\" placeholder=\"Mensaje de bloqueo\" value=\"{global_state['message']}\" />
      <button type=\"submit\">{block_toggle}</button>
    </form>
  </div>

  <div class=\"card\">
    <h3>Bloqueo por Instalación</h3>
    <form method=\"post\" action=\"/admin/installation\">
      <input name=\"installation_id\" placeholder=\"installation_id\" required />
      <input name=\"reason\" placeholder=\"Razón de bloqueo\" />
      <input type=\"hidden\" name=\"blocked\" value=\"1\" />
      <button type=\"submit\">Bloquear instalación</button>
    </form>
    <br/>
    <form method=\"post\" action=\"/admin/installation\">
      <input name=\"installation_id\" placeholder=\"installation_id\" required />
      <input type=\"hidden\" name=\"blocked\" value=\"0\" />
      <button type=\"submit\">Desbloquear instalación</button>
    </form>
  </div>

  <div class=\"card\">
    <h3>Instalaciones Registradas (max 500)</h3>
    <div class=\"scroll\">
      <table>
        <thead>
          <tr>
            <th>installation_id</th><th>empresa</th><th>app</th><th>version</th><th>hostname</th><th>usuario</th><th>ip</th><th>last_seen</th><th>blocked</th><th>reason</th><th>validaciones</th>
          </tr>
        </thead>
        <tbody>
          {''.join(table_rows)}
        </tbody>
      </table>
    </div>
  </div>
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
                        "version": "6.0.0"
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
            self._html(HTTPStatus.OK, admin_page_html())
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
            blocked = str(form.get("blocked", "0")) == "1"
            reason = str(form.get("reason", "Instalación bloqueada"))
            if installation_id:
                set_installation_block(installation_id, blocked, reason)
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
