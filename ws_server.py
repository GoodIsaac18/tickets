# =============================================================================
# SERVIDOR WEBSOCKET — ws_server.py
# =============================================================================
# Módulo independiente de WebSocket (puerto 5556).
# La receptora lo arranca junto con el servidor HTTP.
# Las emisoras se suscriben y reciben eventos push en tiempo real.
# =============================================================================

import asyncio
import json
import threading
import time
import logging
from datetime import datetime
from typing import Optional, Dict, Set

try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    WS_DISPONIBLE = True
except ImportError:
    WS_DISPONIBLE = False
    print("[WS] websockets no instalado — sincronización en tiempo real desactivada")

logger = logging.getLogger("ws_server")

# ──────────────────────────────────────────────────────────────────────────────
# Estado global del servidor WebSocket
# ──────────────────────────────────────────────────────────────────────────────

_ws_loop:   Optional[asyncio.AbstractEventLoop] = None
_ws_server  = None           # websockets.Server (handle para detener)
_ws_thread: Optional[threading.Thread] = None
_iniciado   = False
_puerto_actual = 5556

# Mapa: websocket → metadata del cliente
# metadata = {"usuario_ad": str, "mac_address": str, "conectado_en": str}
_clientes: Dict = {}          # {ws: metadata}
_clientes_lock = threading.Lock()


# ──────────────────────────────────────────────────────────────────────────────
# Eventos soportados
# ──────────────────────────────────────────────────────────────────────────────

EVENTO_TICKET_CREADO    = "ticket_creado"
EVENTO_TICKET_ACTUALIZADO = "ticket_actualizado"
EVENTO_TICKET_CANCELADO = "ticket_cancelado"
EVENTO_TECNICO_CAMBIO   = "tecnico_cambio"
EVENTO_PING             = "ping"
EVENTO_PONG             = "pong"


# ──────────────────────────────────────────────────────────────────────────────
# Serializador JSON
# ──────────────────────────────────────────────────────────────────────────────

def _serializar(obj):
    """Serializa objetos Python a JSON (maneja datetime, etc.)."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"No serializable: {type(obj)}")


def _dumps(data: dict) -> str:
    return json.dumps(data, default=_serializar, ensure_ascii=False)


# ──────────────────────────────────────────────────────────────────────────────
# Handler de conexiones WebSocket
# ──────────────────────────────────────────────────────────────────────────────

async def _handler(ws: "WebSocketServerProtocol"):
    """Maneja cada conexión entrante de un cliente WebSocket."""
    ip_cliente = ws.remote_address[0] if ws.remote_address else "?"
    logger.info(f"[WS] Cliente conectado desde {ip_cliente}")

    with _clientes_lock:
        _clientes[ws] = {
            "usuario_ad": "__pendiente__",
            "mac_address": "",
            "conectado_en": datetime.now().isoformat()
        }

    try:
        async for mensaje_raw in ws:
            try:
                msg = json.loads(mensaje_raw)
                accion = msg.get("action", "")

                if accion == "subscribe":
                    # El cliente se identifica
                    usuario_ad  = str(msg.get("usuario_ad", "")).strip().lower()
                    mac_address = str(msg.get("mac_address", "")).strip().lower()
                    with _clientes_lock:
                        _clientes[ws] = {
                            "usuario_ad": usuario_ad,
                            "mac_address": mac_address,
                            "conectado_en": datetime.now().isoformat()
                        }
                    logger.info(f"[WS] Suscripción: {usuario_ad} / {mac_address}")
                    # Confirmar suscripción
                    await ws.send(_dumps({
                        "evento": "subscribed",
                        "mensaje": f"Conectado como {usuario_ad}"
                    }))

                elif accion == EVENTO_PING:
                    await ws.send(_dumps({"evento": EVENTO_PONG}))

            except json.JSONDecodeError:
                pass
            except Exception as e:
                logger.warning(f"[WS] Error procesando mensaje: {e}")

    except Exception:
        pass
    finally:
        with _clientes_lock:
            _clientes.pop(ws, None)
        logger.info(f"[WS] Cliente desconectado desde {ip_cliente}")


# ──────────────────────────────────────────────────────────────────────────────
# Broadcast (thread-safe, llamado desde hilos HTTP / receptora)
# ──────────────────────────────────────────────────────────────────────────────

def broadcast(evento: str, datos: dict,
              usuario_ad: str = "",
              mac_address: str = "",
              solo_propietario: bool = False):
    """
    Envía un evento a clientes suscritos.

    Args:
        evento:          Tipo de evento (EVENTO_* constantes arriba).
        datos:           Payload del evento (dict serializable a JSON).
        usuario_ad:      Si se indica, limita el envío al dueño del ticket.
        mac_address:     Si se indica, también se filtra por MAC.
        solo_propietario: True = solo al dueño del ticket,
                          False = a todos (broadcast global, p.ej. receptora).
    """
    global _ws_loop
    if not WS_DISPONIBLE or _ws_loop is None or not _ws_loop.is_running():
        return

    mensaje = _dumps({
        "evento": evento,
        "timestamp": datetime.now().isoformat(),
        **datos
    })

    # Seleccionar destinatarios
    usuario_low = usuario_ad.strip().lower() if usuario_ad else ""
    mac_low     = mac_address.strip().lower() if mac_address else ""

    with _clientes_lock:
        snapshot = dict(_clientes)

    destinatarios = []
    for ws, meta in snapshot.items():
        if solo_propietario and usuario_low:
            # Solo enviar al usuario propietario del ticket
            if meta.get("usuario_ad", "") == usuario_low:
                destinatarios.append(ws)
        else:
            # Broadcast a todos los suscritos (excepto pendientes de suscripción)
            if meta.get("usuario_ad", "") != "__pendiente__":
                destinatarios.append(ws)

    if not destinatarios:
        return

    async def _enviar_a_todos():
        for ws in destinatarios:
            try:
                await ws.send(mensaje)
            except Exception:
                pass

    asyncio.run_coroutine_threadsafe(_enviar_a_todos(), _ws_loop)


def broadcast_a_usuario(evento: str, datos: dict, usuario_ad: str,
                         mac_address: str = ""):
    """Broadcast dirigido únicamente al usuario propietario del ticket."""
    broadcast(evento, datos, usuario_ad=usuario_ad, mac_address=mac_address,
              solo_propietario=True)


def broadcast_global(evento: str, datos: dict):
    """Broadcast a todos los clientes conectados (para la receptora)."""
    broadcast(evento, datos)


# ──────────────────────────────────────────────────────────────────────────────
# Inicio del servidor
# ──────────────────────────────────────────────────────────────────────────────

def iniciar_ws_server(puerto: int = 5556,
                       host: str = "0.0.0.0",
                       callback_iniciado: Optional[callable] = None):
    """
    Arranca el servidor WebSocket en un hilo daemon.
    Retorna de inmediato; el servidor corre en segundo plano.

    Args:
        puerto:           Puerto WebSocket (default 5556).
        host:             Interfaz de escucha (default todas).
        callback_iniciado: Función opcioal llamada cuando el servidor está listo.
    """
    global _ws_loop, _ws_server, _ws_thread, _iniciado, _puerto_actual

    if not WS_DISPONIBLE:
        logger.warning("[WS] websockets no disponible — servidor no iniciado")
        if callback_iniciado:
            callback_iniciado(False, "websockets no instalado")
        return

    if _iniciado:
        logger.info(f"[WS] Servidor ya corriendo en puerto {_puerto_actual}")
        if callback_iniciado:
            callback_iniciado(True, f"Ya activo en :{_puerto_actual}")
        return

    _puerto_actual = puerto

    def _run_loop():
        global _ws_loop, _ws_server, _iniciado
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        _ws_loop = loop

        async def _main():
            global _ws_server, _iniciado
            try:
                server = await websockets.serve(_handler, host, puerto,
                                                ping_interval=20,
                                                ping_timeout=10)
                _ws_server = server
                _iniciado  = True
                logger.info(f"[WS] Servidor WebSocket escuchando en ws://{host}:{puerto}")
                if callback_iniciado:
                    callback_iniciado(True, f"ws://{host}:{puerto}")
                await server.wait_closed()
            except Exception as e:
                logger.error(f"[WS] Error iniciando servidor: {e}")
                _iniciado = False
                if callback_iniciado:
                    callback_iniciado(False, str(e))

        loop.run_until_complete(_main())

    _ws_thread = threading.Thread(target=_run_loop, name="WebSocket-Server", daemon=True)
    _ws_thread.start()

    # Esperar hasta 3 segundos a que el servidor esté listo
    for _ in range(30):
        if _iniciado:
            break
        time.sleep(0.1)


def detener_ws_server():
    """Detiene el servidor WebSocket."""
    global _ws_server, _iniciado
    if _ws_server and _ws_loop:
        _ws_server.close()
        _iniciado = False
        logger.info("[WS] Servidor detenido")


def esta_activo() -> bool:
    return _iniciado and _ws_loop is not None and _ws_loop.is_running()


def contar_clientes() -> int:
    with _clientes_lock:
        return sum(1 for meta in _clientes.values()
                   if meta.get("usuario_ad", "") != "__pendiente__")
