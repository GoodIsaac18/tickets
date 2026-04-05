"""Tests de seguridad para API de licencias."""

import json
import socket
import threading
import time
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from src.apps.licencias import server as ls


def _free_port() -> int:
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _request(method: str, url: str, payload: dict | None = None, headers: dict | None = None, timeout: int = 4):
    body = None
    req_headers = headers or {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        req_headers = {"Content-Type": "application/json", **req_headers}
    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status, res.read().decode("utf-8", errors="ignore"), dict(res.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="ignore"), dict(exc.headers)


@pytest.fixture
def lic_server(tmp_path):
    old_db_path = ls.DB_PATH
    old_admin_key = ls.ADMIN_KEY
    old_cors = ls.CORS_ALLOWED_ORIGINS
    old_rl_max = ls.VALIDATE_RATE_LIMIT_MAX
    old_rl_window = ls.VALIDATE_RATE_LIMIT_WINDOW
    old_validate_max = ls.MAX_JSON_BYTES_VALIDATE

    ls.DB_PATH = tmp_path / "licencias_test.db"
    ls.ADMIN_KEY = "test-admin-key"
    ls.CORS_ALLOWED_ORIGINS = ("http://localhost:5173",)
    ls.VALIDATE_RATE_LIMIT_MAX = 5
    ls.VALIDATE_RATE_LIMIT_WINDOW = 60
    ls.MAX_JSON_BYTES_VALIDATE = 1024
    ls._validate_rate_limit_por_ip.clear()  # type: ignore[attr-defined]

    ls.init_db()
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), ls.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            status, _, _ = _request("GET", f"{base_url}/health", timeout=1)
            if status == 200:
                break
        except Exception:
            pass
    yield base_url

    server.shutdown()
    server.server_close()

    ls.DB_PATH = old_db_path
    ls.ADMIN_KEY = old_admin_key
    ls.CORS_ALLOWED_ORIGINS = old_cors
    ls.VALIDATE_RATE_LIMIT_MAX = old_rl_max
    ls.VALIDATE_RATE_LIMIT_WINDOW = old_rl_window
    ls.MAX_JSON_BYTES_VALIDATE = old_validate_max
    ls._validate_rate_limit_por_ip.clear()  # type: ignore[attr-defined]


def test_validate_rate_limit_returns_429(lic_server):
    url = f"{lic_server}/api/v1/validate"
    payload = {
        "installation_id": "rl-test",
        "empresa": "TEST",
        "app_id": "emisora",
        "version": "1.0",
    }

    statuses = []
    for _ in range(6):
        status, _, _ = _request("POST", url, payload=payload)
        statuses.append(status)

    assert statuses[:5] == [200, 200, 200, 200, 200]
    assert statuses[5] == 429


def test_validate_payload_too_large_returns_413(lic_server):
    url = f"{lic_server}/api/v1/validate"
    payload = {
        "installation_id": "big-test",
        "empresa": "TEST",
        "app_id": "emisora",
        "version": "1.0",
        "fingerprint": "A" * 4000,
    }

    status, _, _ = _request("POST", url, payload=payload)
    assert status == 413


def test_cors_only_allows_configured_origin(lic_server):
    status_ok, _, headers_ok = _request(
        "GET",
        f"{lic_server}/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert status_ok == 200
    assert headers_ok.get("Access-Control-Allow-Origin") == "http://localhost:5173"

    status_bad, _, headers_bad = _request(
        "GET",
        f"{lic_server}/health",
        headers={"Origin": "http://evil.local"},
    )
    assert status_bad == 200
    assert "Access-Control-Allow-Origin" not in headers_bad
