"""Tests de endpoints HTTP: health y rate limiting (429)."""
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

# Agregar src al path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core import servidor_red as sr


@pytest.fixture
def puerto_libre():
    s = socket.socket()
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def servidor_tickets(puerto_libre):
    # Backup de configuración global
    old_max = sr.RATE_LIMIT_MAX_PETICIONES
    old_window = sr.RATE_LIMIT_VENTANA

    sr.RATE_LIMIT_MAX_PETICIONES = 100
    sr.RATE_LIMIT_VENTANA = 60
    sr._rate_limit_por_ip.clear()  # type: ignore[attr-defined]

    ok = sr.iniciar_servidor(puerto=puerto_libre)
    assert ok is True

    # Espera breve de arranque
    deadline = time.time() + 8
    ip = sr.obtener_ip_local()
    url = f"http://{ip}:{puerto_libre}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status == 200:
                    break
        except Exception:
            pass
    else:
        pytest.fail("Servidor tickets no respondió health a tiempo")

    yield ip, puerto_libre

    # Teardown
    sr.detener_servidor()
    sr.RATE_LIMIT_MAX_PETICIONES = old_max
    sr.RATE_LIMIT_VENTANA = old_window


def test_health_endpoint_responde_ok(servidor_tickets):
    ip, port = servidor_tickets
    with urllib.request.urlopen(f"http://{ip}:{port}/health", timeout=3) as r:
        assert r.status == 200
        body = r.read().decode("utf-8")
        assert "healthy" in body or "degraded" in body


def test_rate_limit_retorna_429(puerto_libre):
    old_max = sr.RATE_LIMIT_MAX_PETICIONES
    old_window = sr.RATE_LIMIT_VENTANA

    # Muy bajo para forzar 429 rápido
    sr.RATE_LIMIT_MAX_PETICIONES = 1
    sr.RATE_LIMIT_VENTANA = 60
    sr._rate_limit_por_ip.clear()  # type: ignore[attr-defined]

    ok = sr.iniciar_servidor(puerto=puerto_libre)
    assert ok is True

    ip = sr.obtener_ip_local()
    url = f"http://{ip}:{puerto_libre}/ping"

    try:
        # Primera petición: OK
        with urllib.request.urlopen(url, timeout=3) as r:
            assert r.status == 200

        # Segunda petición: debe disparar 429
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(url, timeout=3)
        assert exc.value.code == 429
    finally:
        sr.detener_servidor()
        sr.RATE_LIMIT_MAX_PETICIONES = old_max
        sr.RATE_LIMIT_VENTANA = old_window


def test_post_requiere_api_key_cuando_esta_habilitada(puerto_libre):
    old_require = sr.REQUIRE_API_KEY
    old_key = sr.API_KEY
    old_header = sr.API_KEY_HEADER

    sr.REQUIRE_API_KEY = True
    sr.API_KEY = "test-key"
    sr.API_KEY_HEADER = "X-Tickets-Key"

    ok = sr.iniciar_servidor(puerto=puerto_libre, host="127.0.0.1")
    assert ok is True

    url = f"http://127.0.0.1:{puerto_libre}/ticket/crear"
    body = b'{"usuario_ad":"u","hostname":"h","mac_address":"AA:BB:CC:DD:EE:11","categoria":"Hardware","descripcion":"desc","prioridad":"Media"}'

    try:
        # Sin API key -> 401
        req1 = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(req1, timeout=3)
        assert exc.value.code == 401

        # Con API key -> no debe ser 401
        req2 = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "X-Tickets-Key": "test-key"},
            method="POST",
        )
        with urllib.request.urlopen(req2, timeout=3) as r:
            assert r.status in (200, 400)
    finally:
        sr.detener_servidor()
        sr.REQUIRE_API_KEY = old_require
        sr.API_KEY = old_key
        sr.API_KEY_HEADER = old_header


def test_cors_restringido_por_origen(puerto_libre):
    old_cors = sr.CORS_ALLOWED_ORIGINS
    sr.CORS_ALLOWED_ORIGINS = ("http://localhost:5173",)

    ok = sr.iniciar_servidor(puerto=puerto_libre, host="127.0.0.1")
    assert ok is True
    url = f"http://127.0.0.1:{puerto_libre}/ping"

    try:
        req_ok = urllib.request.Request(url, headers={"Origin": "http://localhost:5173"}, method="GET")
        with urllib.request.urlopen(req_ok, timeout=3) as r_ok:
            assert r_ok.status == 200
            assert r_ok.headers.get("Access-Control-Allow-Origin") == "http://localhost:5173"

        req_bad = urllib.request.Request(url, headers={"Origin": "http://evil.local"}, method="GET")
        with urllib.request.urlopen(req_bad, timeout=3) as r_bad:
            assert r_bad.status == 200
            assert r_bad.headers.get("Access-Control-Allow-Origin") is None
    finally:
        sr.detener_servidor()
        sr.CORS_ALLOWED_ORIGINS = old_cors
