# =============================================================================
# SERVIDOR DE RED OPTIMIZADO - servidor_red.py
# =============================================================================
# Sistema de comunicación LAN con hilos, sockets y detección de equipos
# Optimizado para ejecutarse en segundo plano
# =============================================================================

import json
import socket
import threading
import queue
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional, Callable, Dict, Any, List, Tuple
from pathlib import Path

# =============================================================================
# NOTIFICACIONES DE WINDOWS
# =============================================================================
# Importar sistema de notificaciones del SO
try:
    from notificaciones_windows import (
        mostrar_notificacion_windows,
        notificar_nueva_solicitud as _notif_solicitud,
        notificar_nuevo_ticket as _notif_ticket,
        notificar_equipo_conectado as _notif_equipo_conectado,
        notificar_equipo_desconectado as _notif_equipo_desconectado,
        iniciar_servicio_notificaciones,
        WINOTIFY_DISPONIBLE
    )
    NOTIFICACIONES_DISPONIBLES = WINOTIFY_DISPONIBLE
except ImportError:
    NOTIFICACIONES_DISPONIBLES = False
    def _notif_solicitud(*args, **kwargs): pass
    def _notif_ticket(*args, **kwargs): pass
    def _notif_equipo_conectado(*args, **kwargs): pass
    def _notif_equipo_desconectado(*args, **kwargs): pass
    def iniciar_servicio_notificaciones(): pass

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

PUERTO_HTTP = 5555
MAX_WORKERS = 20
HEARTBEAT_INTERVAL = 30  # segundos
TIMEOUT_EQUIPO = 90  # segundos sin heartbeat = offline

# =============================================================================
# ESTADO GLOBAL
# =============================================================================

_servidor_http_activo = False
_servidor_http: Optional[HTTPServer] = None

# Callbacks
_callback_nuevo_ticket: Optional[Callable] = None
_callback_equipo_conectado: Optional[Callable] = None
_callback_equipo_desconectado: Optional[Callable] = None

# Equipos conectados: {mac_address: {info, ultimo_heartbeat}}
_equipos_conectados: Dict[str, Dict] = {}
_lock_equipos = threading.RLock()

# Cola de mensajes para procesar en segundo plano
_cola_mensajes = queue.Queue()
_procesador_activo = False

# =============================================================================
# SISTEMA DE SOLICITUDES DE ENLACE
# =============================================================================

ARCHIVO_SOLICITUDES = Path(__file__).parent / "solicitudes_enlace.json"
ARCHIVO_EQUIPOS_APROBADOS = Path(__file__).parent / "equipos_aprobados.json"

# Solicitudes pendientes: {mac_address: {info, fecha, estado}}
_solicitudes_pendientes: Dict[str, Dict] = {}
_equipos_aprobados: Dict[str, Dict] = {}
_lock_solicitudes = threading.RLock()

# Callback para nuevas solicitudes
_callback_nueva_solicitud: Optional[Callable] = None


# =============================================================================
# SERVIDOR HTTP THREADED (optimizado para múltiples conexiones)
# =============================================================================

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    """Servidor HTTP con soporte para múltiples conexiones simultáneas."""
    daemon_threads = True
    allow_reuse_address = True


class TicketRequestHandler(BaseHTTPRequestHandler):
    """Manejador de peticiones HTTP optimizado."""
    
    protocol_version = 'HTTP/1.1'
    
    def log_message(self, format, *args):
        pass
    
    def _enviar_json(self, codigo: int, datos: dict):
        contenido = json.dumps(datos, ensure_ascii=False, default=str).encode('utf-8')
        self.send_response(codigo)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(contenido))
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(contenido)
    
    def do_GET(self):
        if self.path == "/ping":
            self._enviar_json(200, {
                "status": "ok",
                "timestamp": datetime.now().isoformat(),
                "equipos_online": len(obtener_equipos_online())
            })
        
        elif self.path == "/estado":
            try:
                from data_access import GestorTickets
                gestor = GestorTickets()
                estado = gestor.obtener_mensaje_estado_sistema()
                self._enviar_json(200, estado)
            except Exception as e:
                self._enviar_json(500, {"error": str(e)})
        
        elif self.path == "/equipos":
            equipos = obtener_equipos_con_estado()
            self._enviar_json(200, {"equipos": equipos})
        
        elif self.path == "/equipos/online":
            equipos = obtener_equipos_online()
            self._enviar_json(200, {"equipos": equipos, "total": len(equipos)})
        
        elif self.path == "/tecnicos":
            try:
                from data_access import GestorTickets
                gestor = GestorTickets()
                tecnicos = gestor.obtener_tecnicos()
                self._enviar_json(200, {"tecnicos": tecnicos.to_dict('records')})
            except Exception as e:
                self._enviar_json(500, {"error": str(e)})
        
        # === ENDPOINTS DE ENLACE ===
        elif self.path == "/enlace/pendientes":
            solicitudes = obtener_solicitudes_pendientes()
            self._enviar_json(200, {"solicitudes": solicitudes, "total": len(solicitudes)})
        
        elif self.path == "/enlace/aprobados":
            aprobados = obtener_equipos_aprobados()
            self._enviar_json(200, {"equipos": aprobados, "total": len(aprobados)})
        
        elif self.path.startswith("/enlace/estado/"):
            mac = self.path.split("/")[-1]
            estado = obtener_estado_enlace(mac)
            self._enviar_json(200, estado)
        
        else:
            self._enviar_json(404, {"error": "Ruta no encontrada"})
    
    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            datos = json.loads(body)
        except:
            self._enviar_json(400, {"error": "JSON inválido"})
            return
        
        if self.path == "/ticket/crear":
            self._crear_ticket(datos)
        elif self.path == "/equipo/registrar":
            self._registrar_equipo(datos)
        elif self.path == "/equipo/heartbeat":
            self._procesar_heartbeat(datos)
        elif self.path == "/ticket/estado":
            self._consultar_ticket(datos)
        # === ENDPOINTS DE ENLACE ===
        elif self.path == "/enlace/solicitar":
            self._solicitar_enlace(datos)
        elif self.path == "/enlace/aprobar":
            self._aprobar_enlace(datos)
        elif self.path == "/enlace/rechazar":
            self._rechazar_enlace(datos)
        elif self.path == "/enlace/revocar":
            self._revocar_enlace(datos)
        # === ENDPOINTS DE TICKET (RECORDATORIO/CANCELAR) ===
        elif self.path == "/ticket/recordatorio":
            self._enviar_recordatorio_ticket(datos)
        elif self.path == "/ticket/cancelar":
            self._cancelar_ticket(datos)
        else:
            self._enviar_json(404, {"error": "Ruta no encontrada"})
    
    def _crear_ticket(self, datos: dict):
        try:
            from data_access import GestorTickets
            gestor = GestorTickets()
            
            ticket = gestor.crear_ticket(
                usuario_ad=datos.get("usuario_ad", ""),
                hostname=datos.get("hostname", ""),
                mac_address=datos.get("mac_address", ""),
                categoria=datos.get("categoria", "Otro"),
                descripcion=datos.get("descripcion", ""),
                prioridad=datos.get("prioridad", "Media")
            )
            
            # ===== NOTIFICACIÓN DE WINDOWS (siempre activa) =====
            if NOTIFICACIONES_DISPONIBLES:
                try:
                    _notif_ticket(ticket)
                    print(f"[SERVIDOR] 🔔 Notificación Windows: Nuevo ticket {ticket.get('TURNO', 'N/A')}")
                except Exception as e:
                    print(f"[SERVIDOR] Error en notificación: {e}")
            
            if _callback_nuevo_ticket:
                _cola_mensajes.put(("ticket", ticket))
            
            self._enviar_json(200, {"success": True, "ticket": ticket})
            
        except Exception as e:
            self._enviar_json(500, {"error": str(e)})
    
    def _registrar_equipo(self, datos: dict):
        try:
            mac = datos.get("mac_address", "")
            if mac:
                registrar_equipo_conectado(
                    mac_address=mac,
                    hostname=datos.get("hostname", ""),
                    usuario_ad=datos.get("usuario_ad", ""),
                    ip_address=self.client_address[0]
                )
            
            self._enviar_json(200, {"success": True})
            
        except Exception as e:
            self._enviar_json(500, {"error": str(e)})
    
    def _procesar_heartbeat(self, datos: dict):
        mac = datos.get("mac_address", "")
        if mac:
            actualizar_heartbeat(mac, self.client_address[0])
        self._enviar_json(200, {"success": True})
    
    def _consultar_ticket(self, datos: dict):
        try:
            from data_access import GestorTickets
            gestor = GestorTickets()
            
            id_ticket = datos.get("id_ticket", "")
            ticket = gestor.obtener_ticket_por_id(id_ticket)
            
            if ticket:
                posicion = gestor.obtener_posicion_cola(id_ticket)
                self._enviar_json(200, {
                    "success": True,
                    "ticket": ticket,
                    "posicion_cola": posicion
                })
            else:
                self._enviar_json(404, {"error": "Ticket no encontrado"})
                
        except Exception as e:
            self._enviar_json(500, {"error": str(e)})
    
    # === MÉTODOS DE ENLACE ===
    
    def _solicitar_enlace(self, datos: dict):
        """Procesa una solicitud de enlace de un equipo."""
        try:
            mac = datos.get("mac_address", "")
            if not mac:
                self._enviar_json(400, {"error": "MAC address requerida"})
                return
            
            # Verificar si ya está aprobado
            if equipo_esta_aprobado(mac):
                self._enviar_json(200, {
                    "success": True, 
                    "estado": "aprobado",
                    "mensaje": "Este equipo ya está enlazado"
                })
                return
            
            # Crear solicitud
            solicitud = crear_solicitud_enlace(
                mac_address=mac,
                hostname=datos.get("hostname", ""),
                usuario_ad=datos.get("usuario_ad", ""),
                ip_address=self.client_address[0],
                nombre_equipo=datos.get("nombre_equipo", "")
            )
            
            self._enviar_json(200, {
                "success": True,
                "estado": "pendiente",
                "mensaje": "Solicitud enviada. Esperando aprobación del administrador.",
                "solicitud": solicitud
            })
            
        except Exception as e:
            self._enviar_json(500, {"error": str(e)})
    
    def _aprobar_enlace(self, datos: dict):
        """Aprueba una solicitud de enlace."""
        try:
            mac = datos.get("mac_address", "")
            if not mac:
                self._enviar_json(400, {"error": "MAC address requerida"})
                return
            
            resultado = aprobar_solicitud_enlace(mac)
            if resultado:
                self._enviar_json(200, {"success": True, "mensaje": "Equipo enlazado correctamente"})
            else:
                self._enviar_json(404, {"error": "Solicitud no encontrada"})
                
        except Exception as e:
            self._enviar_json(500, {"error": str(e)})
    
    def _rechazar_enlace(self, datos: dict):
        """Rechaza una solicitud de enlace."""
        try:
            mac = datos.get("mac_address", "")
            motivo = datos.get("motivo", "Rechazado por el administrador")
            
            if not mac:
                self._enviar_json(400, {"error": "MAC address requerida"})
                return
            
            resultado = rechazar_solicitud_enlace(mac, motivo)
            if resultado:
                self._enviar_json(200, {"success": True, "mensaje": "Solicitud rechazada"})
            else:
                self._enviar_json(404, {"error": "Solicitud no encontrada"})
                
        except Exception as e:
            self._enviar_json(500, {"error": str(e)})
    
    def _revocar_enlace(self, datos: dict):
        """Revoca el enlace de un equipo aprobado."""
        try:
            mac = datos.get("mac_address", "")
            if not mac:
                self._enviar_json(400, {"error": "MAC address requerida"})
                return
            
            resultado = revocar_enlace(mac)
            if resultado:
                self._enviar_json(200, {"success": True, "mensaje": "Enlace revocado"})
            else:
                self._enviar_json(404, {"error": "Equipo no encontrado"})
                
        except Exception as e:
            self._enviar_json(500, {"error": str(e)})
    
    def _enviar_recordatorio_ticket(self, datos: dict):
        """Envía un recordatorio para un ticket existente."""
        try:
            id_ticket = datos.get("id_ticket", "")
            nota = datos.get("nota", "")
            usuario = datos.get("usuario_ad", "")
            
            print(f"[SERVIDOR] Recordatorio recibido - Ticket: {id_ticket}, Usuario: {usuario}")
            
            if not id_ticket:
                self._enviar_json(400, {"error": "ID de ticket requerido"})
                return
            
            from data_access import GestorTickets
            gestor = GestorTickets()
            
            # Verificar que el ticket existe y está activo
            ticket = gestor.obtener_ticket_por_id(id_ticket)
            if not ticket:
                print(f"[SERVIDOR] Ticket {id_ticket} no encontrado")
                self._enviar_json(404, {"error": "Ticket no encontrado"})
                return
            
            estado_ticket = ticket.get("ESTADO", "")
            print(f"[SERVIDOR] Estado del ticket: {estado_ticket}")
            
            if estado_ticket in ["Cerrado", "Cancelado"]:
                self._enviar_json(400, {"error": "El ticket ya está cerrado o cancelado"})
                return
            
            # Registrar el recordatorio en el historial del ticket
            historial_actual = ticket.get("HISTORIAL", "") or ""
            fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            nuevo_historial = f"[{fecha_hora}] RECORDATORIO enviado por {usuario}"
            if nota:
                nuevo_historial += f": {nota}"
            nuevo_historial += f"\n{historial_actual}"
            
            gestor.actualizar_ticket(id_ticket, historial=nuevo_historial)
            
            # Notificación de Windows
            if NOTIFICACIONES_DISPONIBLES:
                try:
                    from winotify import Notification, audio
                    notif = Notification(
                        app_id="Soporte Técnico",
                        title=f"⏰ Recordatorio - Ticket #{ticket.get('TURNO', 'N/A')}",
                        msg=f"{usuario} solicita atención.\n{nota if nota else 'Sin nota adicional'}",
                        duration="long"
                    )
                    notif.set_audio(audio.Reminder, loop=False)
                    notif.show()
                except Exception as e:
                    print(f"[SERVIDOR] Error en notificación recordatorio: {e}")
            
            # Agregar a la cola de mensajes para la UI
            if _callback_nuevo_ticket:
                _cola_mensajes.put(("recordatorio", {
                    "ticket": ticket,
                    "nota": nota,
                    "usuario": usuario
                }))
            
            self._enviar_json(200, {
                "success": True,
                "mensaje": "Recordatorio enviado correctamente"
            })
            
        except Exception as e:
            import traceback
            print(f"[SERVIDOR] ERROR en recordatorio: {e}")
            traceback.print_exc()
            self._enviar_json(500, {"error": str(e)})
    
    def _cancelar_ticket(self, datos: dict):
        """Cancela un ticket existente."""
        try:
            id_ticket = datos.get("id_ticket", "")
            nota = datos.get("nota", "")
            usuario = datos.get("usuario_ad", "")
            
            if not id_ticket:
                self._enviar_json(400, {"error": "ID de ticket requerido"})
                return
            
            from data_access import GestorTickets
            gestor = GestorTickets()
            
            # Verificar que el ticket existe y está activo
            ticket = gestor.obtener_ticket_por_id(id_ticket)
            if not ticket:
                self._enviar_json(404, {"error": "Ticket no encontrado"})
                return
            
            if ticket.get("ESTADO") in ["Cerrado", "Cancelado"]:
                self._enviar_json(400, {"error": "El ticket ya está cerrado o cancelado"})
                return
            
            # Actualizar historial y estado
            historial_actual = ticket.get("HISTORIAL", "") or ""
            fecha_hora = datetime.now().strftime("%d/%m/%Y %H:%M")
            nuevo_historial = f"[{fecha_hora}] CANCELADO por el usuario {usuario}"
            if nota:
                nuevo_historial += f": {nota}"
            nuevo_historial += f"\n{historial_actual}"
            
            gestor.actualizar_ticket(
                id_ticket, 
                estado="Cancelado",
                fecha_cierre=datetime.now(),
                historial=nuevo_historial
            )
            
            # Notificación de Windows
            if NOTIFICACIONES_DISPONIBLES:
                try:
                    from winotify import Notification, audio
                    notif = Notification(
                        app_id="Soporte Técnico",
                        title=f"❌ Ticket Cancelado - #{ticket.get('TURNO', 'N/A')}",
                        msg=f"{usuario} canceló su solicitud.\n{nota if nota else 'Sin motivo especificado'}",
                        duration="short"
                    )
                    notif.set_audio(audio.Default, loop=False)
                    notif.show()
                except Exception as e:
                    print(f"[SERVIDOR] Error en notificación cancelación: {e}")
            
            # Agregar a la cola de mensajes para la UI
            if _callback_nuevo_ticket:
                _cola_mensajes.put(("cancelacion", {
                    "ticket": ticket,
                    "nota": nota,
                    "usuario": usuario
                }))
            
            self._enviar_json(200, {
                "success": True,
                "mensaje": "Ticket cancelado correctamente"
            })
            
        except Exception as e:
            import traceback
            print(f"[SERVIDOR] ERROR en cancelación: {e}")
            traceback.print_exc()
            self._enviar_json(500, {"error": str(e)})
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()


# =============================================================================
# GESTIÓN DE EQUIPOS CONECTADOS
# =============================================================================

def registrar_equipo_conectado(mac_address: str, hostname: str = "", 
                                usuario_ad: str = "", ip_address: str = ""):
    """Registra un equipo como conectado."""
    with _lock_equipos:
        ahora = time.time()
        
        es_nuevo = mac_address not in _equipos_conectados
        
        equipo_info = {
            "mac_address": mac_address,
            "hostname": hostname,
            "usuario_ad": usuario_ad,
            "ip_address": ip_address,
            "ultimo_heartbeat": ahora,
            "primera_conexion": _equipos_conectados.get(mac_address, {}).get("primera_conexion", ahora),
            "online": True
        }
        
        _equipos_conectados[mac_address] = equipo_info
        
        if es_nuevo and _callback_equipo_conectado:
            _cola_mensajes.put(("equipo_conectado", equipo_info))
        
        # Guardar en base de datos
        _guardar_equipo_db(equipo_info)


def _guardar_equipo_db(equipo: dict):
    """Guarda el equipo en la base de datos en segundo plano."""
    def guardar():
        try:
            from data_access import EscanerRed
            escaner = EscanerRed()
            escaner._actualizar_base_datos([{
                "IP_ADDRESS": equipo.get("ip_address", ""),
                "MAC_ADDRESS": equipo.get("mac_address", ""),
                "HOSTNAME": equipo.get("hostname", "")
            }])
        except:
            pass
    
    threading.Thread(target=guardar, daemon=True).start()


def actualizar_heartbeat(mac_address: str, ip_address: str = ""):
    """Actualiza el último heartbeat de un equipo."""
    with _lock_equipos:
        if mac_address in _equipos_conectados:
            _equipos_conectados[mac_address]["ultimo_heartbeat"] = time.time()
            _equipos_conectados[mac_address]["online"] = True
            if ip_address:
                _equipos_conectados[mac_address]["ip_address"] = ip_address
        else:
            # Equipo nuevo por heartbeat
            registrar_equipo_conectado(mac_address, ip_address=ip_address)


def obtener_equipos_online() -> List[Dict]:
    """Obtiene la lista de equipos online."""
    with _lock_equipos:
        ahora = time.time()
        return [
            info.copy() for mac, info in _equipos_conectados.items()
            if ahora - info.get("ultimo_heartbeat", 0) < TIMEOUT_EQUIPO
        ]


def obtener_equipos_con_estado() -> List[Dict]:
    """Obtiene todos los equipos (memoria + DB) con su estado."""
    with _lock_equipos:
        ahora = time.time()
        equipos = {}
        
        # Primero los de memoria
        for mac, info in _equipos_conectados.items():
            equipo = info.copy()
            equipo["online"] = (ahora - info.get("ultimo_heartbeat", 0)) < TIMEOUT_EQUIPO
            equipos[mac] = equipo
        
        # Luego los de la base de datos
        try:
            from data_access import EscanerRed
            escaner = EscanerRed()
            df = escaner.obtener_equipos_red()
            
            for _, row in df.iterrows():
                mac = row.get("MAC_ADDRESS", "")
                if mac and mac not in equipos:
                    equipos[mac] = {
                        "mac_address": mac,
                        "hostname": row.get("HOSTNAME", ""),
                        "ip_address": row.get("IP_ADDRESS", ""),
                        "usuario_ad": row.get("USUARIO_AD", ""),
                        "nombre_equipo": row.get("NOMBRE_EQUIPO", ""),
                        "grupo": row.get("GRUPO", ""),
                        "online": False,
                        "ultimo_heartbeat": 0
                    }
        except:
            pass
        
        return list(equipos.values())


def verificar_equipos_timeout():
    """Verifica equipos sin heartbeat y los marca como offline."""
    with _lock_equipos:
        ahora = time.time()
        
        for mac, info in _equipos_conectados.items():
            era_online = info.get("online", True)
            es_online = (ahora - info.get("ultimo_heartbeat", 0)) < TIMEOUT_EQUIPO
            info["online"] = es_online
            
            if era_online and not es_online and _callback_equipo_desconectado:
                _cola_mensajes.put(("equipo_desconectado", info.copy()))


# =============================================================================
# GESTIÓN DE SOLICITUDES DE ENLACE
# =============================================================================

def _cargar_solicitudes():
    """Carga las solicitudes pendientes desde archivo."""
    global _solicitudes_pendientes
    try:
        if ARCHIVO_SOLICITUDES.exists():
            with open(ARCHIVO_SOLICITUDES, 'r', encoding='utf-8') as f:
                _solicitudes_pendientes = json.load(f)
    except:
        _solicitudes_pendientes = {}


def _guardar_solicitudes():
    """Guarda las solicitudes pendientes a archivo."""
    try:
        with open(ARCHIVO_SOLICITUDES, 'w', encoding='utf-8') as f:
            json.dump(_solicitudes_pendientes, f, ensure_ascii=False, indent=2)
    except:
        pass


def _cargar_equipos_aprobados():
    """Carga los equipos aprobados desde archivo."""
    global _equipos_aprobados
    try:
        if ARCHIVO_EQUIPOS_APROBADOS.exists():
            with open(ARCHIVO_EQUIPOS_APROBADOS, 'r', encoding='utf-8') as f:
                _equipos_aprobados = json.load(f)
    except:
        _equipos_aprobados = {}


def _guardar_equipos_aprobados():
    """Guarda los equipos aprobados a archivo."""
    try:
        with open(ARCHIVO_EQUIPOS_APROBADOS, 'w', encoding='utf-8') as f:
            json.dump(_equipos_aprobados, f, ensure_ascii=False, indent=2)
    except:
        pass


def crear_solicitud_enlace(mac_address: str, hostname: str = "", 
                           usuario_ad: str = "", ip_address: str = "",
                           nombre_equipo: str = "") -> Dict:
    """Crea una nueva solicitud de enlace."""
    with _lock_solicitudes:
        ahora = datetime.now()
        
        # Verificar si es primera solicitud o si es reintento después de rechazo/revocación
        solicitud_anterior = _solicitudes_pendientes.get(mac_address, {})
        estado_anterior = solicitud_anterior.get("estado", "")
        es_nueva = mac_address not in _solicitudes_pendientes
        es_reenvio = estado_anterior in ["rechazado", "revocado"]  # Reenvío después de rechazo/revocación
        
        solicitud = {
            "mac_address": mac_address,
            "hostname": hostname,
            "usuario_ad": usuario_ad,
            "ip_address": ip_address,
            "nombre_equipo": nombre_equipo or hostname,
            "fecha_solicitud": ahora.isoformat(),
            "estado": "pendiente",
            "intentos": solicitud_anterior.get("intentos", 0) + 1,
            "reenvio": es_reenvio  # Marcar si es un reenvío
        }
        
        _solicitudes_pendientes[mac_address] = solicitud
        _guardar_solicitudes()
        
        # ===== NOTIFICACIÓN DE WINDOWS (para nuevas y reenvíos) =====
        if (es_nueva or es_reenvio) and NOTIFICACIONES_DISPONIBLES:
            try:
                _notif_solicitud(solicitud)
                tipo_msg = "Nueva solicitud" if es_nueva else "Reenvío de solicitud"
                print(f"[SERVIDOR] 🔔 Notificación Windows: {tipo_msg} de {hostname}")
            except Exception as e:
                print(f"[SERVIDOR] Error en notificación: {e}")
        
        # Notificar al callback si existe (para nuevas y reenvíos)
        if _callback_nueva_solicitud and (es_nueva or es_reenvio):
            _cola_mensajes.put(("nueva_solicitud", solicitud))
        
        return solicitud


def obtener_solicitudes_pendientes() -> List[Dict]:
    """Obtiene la lista de solicitudes pendientes."""
    with _lock_solicitudes:
        return [s.copy() for s in _solicitudes_pendientes.values() if s.get("estado") == "pendiente"]


def obtener_estado_enlace(mac_address: str) -> Dict:
    """Obtiene el estado de enlace de un equipo."""
    with _lock_solicitudes:
        # Primero verificar si está aprobado
        if mac_address in _equipos_aprobados:
            return {
                "estado": "aprobado",
                "fecha_aprobacion": _equipos_aprobados[mac_address].get("fecha_aprobacion"),
                "puede_enviar_tickets": True
            }
        
        # Verificar si tiene solicitud pendiente
        if mac_address in _solicitudes_pendientes:
            sol = _solicitudes_pendientes[mac_address]
            return {
                "estado": sol.get("estado", "pendiente"),
                "fecha_solicitud": sol.get("fecha_solicitud"),
                "motivo_rechazo": sol.get("motivo_rechazo"),
                "puede_enviar_tickets": False
            }
        
        # No tiene solicitud
        return {
            "estado": "sin_solicitud",
            "puede_enviar_tickets": False,
            "mensaje": "Debe solicitar enlace con el servidor"
        }


def aprobar_solicitud_enlace(mac_address: str) -> bool:
    """Aprueba una solicitud de enlace."""
    with _lock_solicitudes:
        if mac_address not in _solicitudes_pendientes:
            return False
        
        solicitud = _solicitudes_pendientes.pop(mac_address)
        ahora = datetime.now()
        
        _equipos_aprobados[mac_address] = {
            "mac_address": mac_address,
            "hostname": solicitud.get("hostname", ""),
            "usuario_ad": solicitud.get("usuario_ad", ""),
            "nombre_equipo": solicitud.get("nombre_equipo", ""),
            "ip_address": solicitud.get("ip_address", ""),
            "fecha_solicitud": solicitud.get("fecha_solicitud"),
            "fecha_aprobacion": ahora.isoformat(),
            "estado": "aprobado"
        }
        
        _guardar_solicitudes()
        _guardar_equipos_aprobados()
        
        # También registrar en la base de datos de equipos
        try:
            from data_access import GestorTickets
            gestor = GestorTickets()
            gestor.registrar_o_actualizar_equipo(
                mac_address=mac_address,
                hostname=solicitud.get("hostname", ""),
                usuario_ad=solicitud.get("usuario_ad", ""),
                ip_address=solicitud.get("ip_address", "")
            )
        except:
            pass
        
        return True


def rechazar_solicitud_enlace(mac_address: str, motivo: str = "") -> bool:
    """Rechaza una solicitud de enlace."""
    with _lock_solicitudes:
        if mac_address not in _solicitudes_pendientes:
            return False
        
        _solicitudes_pendientes[mac_address]["estado"] = "rechazado"
        _solicitudes_pendientes[mac_address]["motivo_rechazo"] = motivo
        _solicitudes_pendientes[mac_address]["fecha_rechazo"] = datetime.now().isoformat()
        
        _guardar_solicitudes()
        return True


def revocar_enlace(mac_address: str) -> bool:
    """Revoca el enlace de un equipo aprobado."""
    with _lock_solicitudes:
        if mac_address not in _equipos_aprobados:
            return False
        
        equipo = _equipos_aprobados.pop(mac_address)
        
        # Mover a solicitudes como revocado
        _solicitudes_pendientes[mac_address] = {
            **equipo,
            "estado": "revocado",
            "fecha_revocacion": datetime.now().isoformat()
        }
        
        _guardar_solicitudes()
        _guardar_equipos_aprobados()
        return True


def equipo_esta_aprobado(mac_address: str) -> bool:
    """Verifica si un equipo está aprobado para comunicarse."""
    with _lock_solicitudes:
        return mac_address in _equipos_aprobados


def obtener_equipos_aprobados() -> List[Dict]:
    """Obtiene la lista de equipos aprobados."""
    with _lock_solicitudes:
        return list(_equipos_aprobados.values())


def registrar_callback_nueva_solicitud(callback: Callable):
    """Registra un callback para nuevas solicitudes de enlace."""
    global _callback_nueva_solicitud
    _callback_nueva_solicitud = callback


# =============================================================================
# PROCESADOR DE MENSAJES EN SEGUNDO PLANO
# =============================================================================

def _procesador_cola():
    """Procesa mensajes en segundo plano."""
    global _procesador_activo
    _procesador_activo = True
    
    while _procesador_activo:
        try:
            tipo, datos = _cola_mensajes.get(timeout=1)
            
            if tipo == "ticket" and _callback_nuevo_ticket:
                try:
                    _callback_nuevo_ticket(datos)
                except:
                    pass
            
            elif tipo == "equipo_conectado" and _callback_equipo_conectado:
                try:
                    _callback_equipo_conectado(datos)
                except:
                    pass
            
            elif tipo == "equipo_desconectado" and _callback_equipo_desconectado:
                try:
                    _callback_equipo_desconectado(datos)
                except:
                    pass
            
            elif tipo == "nueva_solicitud" and _callback_nueva_solicitud:
                try:
                    _callback_nueva_solicitud(datos)
                except:
                    pass
                    
        except queue.Empty:
            continue
        except:
            pass


def _monitor_heartbeat():
    """Monitor de heartbeat para detectar desconexiones."""
    while _servidor_http_activo:
        verificar_equipos_timeout()
        time.sleep(HEARTBEAT_INTERVAL)


# =============================================================================
# FUNCIONES DEL SERVIDOR
# =============================================================================

def obtener_ip_local() -> str:
    """Obtiene la IP local del equipo."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            hostname = socket.gethostname()
            return socket.gethostbyname(hostname)
        except:
            return "127.0.0.1"


obtener_ip_servidor = obtener_ip_local


def iniciar_servidor(puerto: int = PUERTO_HTTP,
                     callback_ticket: Callable = None,
                     callback_equipo: Callable = None,
                     callback_desconexion: Callable = None,
                     callback_solicitud: Callable = None) -> bool:
    """
    Inicia el servidor de tickets en segundo plano.
    
    Returns:
        True si el servidor se inició correctamente.
    """
    global _servidor_http_activo, _servidor_http
    global _callback_nuevo_ticket, _callback_equipo_conectado, _callback_equipo_desconectado
    global _callback_nueva_solicitud
    
    if _servidor_http_activo:
        return True
    
    _callback_nuevo_ticket = callback_ticket
    _callback_equipo_conectado = callback_equipo
    _callback_equipo_desconectado = callback_desconexion
    _callback_nueva_solicitud = callback_solicitud
    
    # Cargar solicitudes y equipos aprobados
    _cargar_solicitudes()
    _cargar_equipos_aprobados()
    
    try:
        ip = obtener_ip_local()
        
        _servidor_http = ThreadedHTTPServer((ip, puerto), TicketRequestHandler)
        _servidor_http_activo = True
        
        # Guardar configuración
        config_path = Path(__file__).parent / "servidor_config.txt"
        with open(config_path, "w") as f:
            f.write(f"{ip}:{puerto}")
        
        # Iniciar threads en segundo plano
        threading.Thread(target=_servidor_http.serve_forever, daemon=True, name="HTTP-Server").start()
        threading.Thread(target=_procesador_cola, daemon=True, name="Msg-Processor").start()
        threading.Thread(target=_monitor_heartbeat, daemon=True, name="Heartbeat-Monitor").start()
        
        print(f"[SERVIDOR] Escuchando en {ip}:{puerto}")
        return True
        
    except Exception as e:
        print(f"[ERROR] No se pudo iniciar servidor: {e}")
        _servidor_http_activo = False
        return False


def detener_servidor():
    """Detiene el servidor."""
    global _servidor_http_activo, _servidor_http, _procesador_activo
    
    _procesador_activo = False
    
    if _servidor_http:
        _servidor_http.shutdown()
        _servidor_http_activo = False
        print("[SERVIDOR] Detenido")


def servidor_esta_activo() -> bool:
    return _servidor_http_activo


# =============================================================================
# CLIENTE - Funciones para conectar al servidor
# =============================================================================

import urllib.request
import urllib.error


def cargar_config_servidor() -> Tuple[Optional[str], int]:
    """Carga la configuración del servidor."""
    try:
        config_path = Path(__file__).parent / "servidor_config.txt"
        if config_path.exists():
            with open(config_path, "r") as f:
                contenido = f.read().strip()
                ip, puerto = contenido.split(":")
                return ip, int(puerto)
    except:
        pass
    return None, PUERTO_HTTP


def verificar_servidor(ip: str, puerto: int = PUERTO_HTTP, timeout: int = 3) -> bool:
    """Verifica si el servidor está disponible."""
    try:
        url = f"http://{ip}:{puerto}/ping"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status == 200
    except:
        return False


def buscar_servidor_en_red(puerto: int = PUERTO_HTTP, timeout: int = 1) -> Optional[Dict]:
    """
    Busca el servidor en la red local.
    
    Returns:
        Dict con ip y puerto, o None si no se encuentra.
    """
    # Intentar config guardada
    ip_guardada, puerto_guardado = cargar_config_servidor()
    if ip_guardada and verificar_servidor(ip_guardada, puerto_guardado, timeout):
        return {"ip": ip_guardada, "puerto": puerto_guardado}
    
    # Escanear la red en paralelo
    ip_local = obtener_ip_local()
    base = ".".join(ip_local.split(".")[:3])
    
    encontrado = {"ip": None, "puerto": puerto}
    lock = threading.Lock()
    
    def verificar_ip(ip):
        if verificar_servidor(ip, puerto, timeout):
            with lock:
                if encontrado["ip"] is None:
                    encontrado["ip"] = ip
    
    # Probar IPs comunes primero
    ips_prioritarias = [f"{base}.{i}" for i in [1, 2, 10, 100, 200, 254]]
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(verificar_ip, ips_prioritarias)
    
    if encontrado["ip"]:
        return encontrado
    
    # Si no, escanear todo el rango
    with ThreadPoolExecutor(max_workers=50) as executor:
        executor.map(verificar_ip, [f"{base}.{i}" for i in range(1, 255)])
    
    return encontrado if encontrado["ip"] else None


def enviar_ticket_a_servidor(ip: str, puerto: int, datos_ticket: dict) -> dict:
    """Envía un ticket al servidor."""
    try:
        url = f"http://{ip}:{puerto}/ticket/crear"
        data = json.dumps(datos_ticket).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
            
    except urllib.error.URLError as e:
        return {"success": False, "error": f"No se pudo conectar: {e}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def registrar_en_servidor(ip: str, puerto: int, mac: str, hostname: str, usuario: str) -> bool:
    """Registra el equipo en el servidor."""
    try:
        url = f"http://{ip}:{puerto}/equipo/registrar"
        data = json.dumps({
            "mac_address": mac,
            "hostname": hostname,
            "usuario_ad": usuario
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.status == 200
    except:
        return False


def enviar_heartbeat(ip: str, puerto: int, mac: str) -> bool:
    """Envía un heartbeat al servidor."""
    try:
        url = f"http://{ip}:{puerto}/equipo/heartbeat"
        data = json.dumps({"mac_address": mac}).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=3) as response:
            return response.status == 200
    except:
        return False


def solicitar_enlace(ip: str, puerto: int, mac: str, hostname: str = "", 
                     usuario: str = "", nombre_equipo: str = "") -> Dict:
    """Solicita enlace con el servidor."""
    try:
        url = f"http://{ip}:{puerto}/enlace/solicitar"
        data = json.dumps({
            "mac_address": mac,
            "hostname": hostname,
            "usuario_ad": usuario,
            "nombre_equipo": nombre_equipo or hostname
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"success": False, "error": str(e), "estado": "error"}


def verificar_estado_enlace(ip: str, puerto: int, mac: str) -> Dict:
    """Verifica el estado del enlace de un equipo."""
    try:
        url = f"http://{ip}:{puerto}/enlace/estado/{mac}"
        req = urllib.request.Request(url)
        
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"estado": "error", "error": str(e), "puede_enviar_tickets": False}


def enviar_recordatorio_ticket(ip: str, puerto: int, id_ticket: str, 
                               usuario_ad: str = "", nota: str = "") -> Dict:
    """Envía un recordatorio para un ticket existente."""
    try:
        url = f"http://{ip}:{puerto}/ticket/recordatorio"
        data = json.dumps({
            "id_ticket": id_ticket,
            "usuario_ad": usuario_ad,
            "nota": nota
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"success": False, "error": str(e)}


def cancelar_ticket_servidor(ip: str, puerto: int, id_ticket: str, 
                             usuario_ad: str = "", nota: str = "") -> Dict:
    """Cancela un ticket existente en el servidor."""
    try:
        url = f"http://{ip}:{puerto}/ticket/cancelar"
        data = json.dumps({
            "id_ticket": id_ticket,
            "usuario_ad": usuario_ad,
            "nota": nota
        }).encode('utf-8')
        
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return {"success": False, "error": str(e)}


class ClienteServidor:
    """Cliente para conectar al servidor con sistema de enlace y heartbeat automático."""
    
    def __init__(self, mac_address: str, hostname: str = "", usuario_ad: str = "", nombre_equipo: str = ""):
        self.mac_address = mac_address
        self.hostname = hostname
        self.usuario_ad = usuario_ad
        self.nombre_equipo = nombre_equipo or hostname
        self.servidor_ip: Optional[str] = None
        self.servidor_puerto: int = PUERTO_HTTP
        self.conectado: bool = False
        self.enlazado: bool = False  # Si fue aprobado por el admin
        self.estado_enlace: str = "sin_solicitud"  # pendiente, aprobado, rechazado
        self._activo: bool = False
        self._callback_estado: Optional[Callable] = None
    
    def set_callback_estado(self, callback: Callable):
        """Establece callback para cambios de estado del enlace."""
        self._callback_estado = callback
    
    def conectar(self) -> bool:
        """Busca y conecta al servidor."""
        servidor = buscar_servidor_en_red()
        
        if servidor:
            self.servidor_ip = servidor["ip"]
            self.servidor_puerto = servidor["puerto"]
            self.conectado = True
            
            # Verificar estado de enlace
            self._verificar_enlace()
            
            # Iniciar heartbeat
            self._iniciar_heartbeat()
            print(f"[CLIENTE] Conectado a {self.servidor_ip}:{self.servidor_puerto}")
            return True
        
        print("[CLIENTE] No se encontró servidor")
        return False
    
    def solicitar_enlace(self) -> Dict:
        """Envía solicitud de enlace al servidor."""
        if not self.conectado:
            return {"success": False, "error": "Sin conexión al servidor"}
        
        resultado = solicitar_enlace(
            self.servidor_ip,
            self.servidor_puerto,
            self.mac_address,
            self.hostname,
            self.usuario_ad,
            self.nombre_equipo
        )
        
        if resultado.get("success"):
            self.estado_enlace = resultado.get("estado", "pendiente")
            self.enlazado = (self.estado_enlace == "aprobado")
            
            if self._callback_estado:
                self._callback_estado(self.estado_enlace, resultado.get("mensaje", ""))
        
        return resultado
    
    def _verificar_enlace(self):
        """Verifica el estado del enlace con el servidor."""
        if not self.servidor_ip:
            return
        
        estado = verificar_estado_enlace(
            self.servidor_ip,
            self.servidor_puerto,
            self.mac_address
        )
        
        nuevo_estado = estado.get("estado", "sin_solicitud")
        estado_cambio = (nuevo_estado != self.estado_enlace)
        
        self.estado_enlace = nuevo_estado
        self.enlazado = estado.get("puede_enviar_tickets", False)
        
        if estado_cambio and self._callback_estado:
            mensaje = estado.get("mensaje", "")
            if nuevo_estado == "aprobado":
                mensaje = "¡Enlace aprobado! Ya puede enviar tickets."
            elif nuevo_estado == "rechazado":
                mensaje = estado.get("motivo_rechazo", "Solicitud rechazada")
            self._callback_estado(nuevo_estado, mensaje)
    
    def _iniciar_heartbeat(self):
        """Inicia el envío de heartbeat y verificación de enlace en segundo plano."""
        self._activo = True
        
        def heartbeat_loop():
            while self._activo and self.conectado:
                # Enviar heartbeat
                if not enviar_heartbeat(self.servidor_ip, self.servidor_puerto, self.mac_address):
                    self.conectado = False
                    self.conectar()
                
                # Verificar estado de enlace periódicamente
                if not self.enlazado:
                    self._verificar_enlace()
                
                time.sleep(HEARTBEAT_INTERVAL)
        
        threading.Thread(target=heartbeat_loop, daemon=True, name="Heartbeat").start()
    
    def desconectar(self):
        """Detiene la conexión."""
        self._activo = False
        self.conectado = False
    
    def puede_enviar_tickets(self) -> bool:
        """Verifica si puede enviar tickets (está enlazado)."""
        return self.conectado and self.enlazado
    
    def enviar_ticket(self, categoria: str, descripcion: str, prioridad: str = "Media") -> dict:
        """Envía un ticket al servidor."""
        if not self.conectado and not self.conectar():
            return {"success": False, "error": "Sin conexión al servidor"}
        
        if not self.enlazado:
            return {
                "success": False, 
                "error": "Equipo no enlazado. Solicite enlace y espere aprobación.",
                "estado_enlace": self.estado_enlace
            }
        
        return enviar_ticket_a_servidor(
            self.servidor_ip,
            self.servidor_puerto,
            {
                "mac_address": self.mac_address,
                "hostname": self.hostname,
                "usuario_ad": self.usuario_ad,
                "categoria": categoria,
                "descripcion": descripcion,
                "prioridad": prioridad
            }
        )


# =============================================================================
# PRUEBA
# =============================================================================

if __name__ == "__main__":
    print("=" * 50)
    print("SERVIDOR DE TICKETS OPTIMIZADO")
    print("=" * 50)
    
    def on_ticket(ticket):
        print(f"[TICKET] {ticket.get('ID', 'N/A')}")
    
    def on_equipo(equipo):
        print(f"[+] {equipo.get('hostname', 'N/A')} - {equipo.get('ip_address', 'N/A')}")
    
    def on_desconexion(equipo):
        print(f"[-] {equipo.get('hostname', 'N/A')}")
    
    if iniciar_servidor(callback_ticket=on_ticket, callback_equipo=on_equipo, callback_desconexion=on_desconexion):
        ip = obtener_ip_local()
        print(f"\nServidor: http://{ip}:{PUERTO_HTTP}")
        print("\nEndpoints: /ping, /equipos, /equipos/online, /ticket/crear")
        print("Ctrl+C para detener...")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            detener_servidor()
