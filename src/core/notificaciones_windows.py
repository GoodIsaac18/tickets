# =============================================================================
# SISTEMA DE NOTIFICACIONES DE WINDOWS - notificaciones_windows.py
# =============================================================================
# Servicio en segundo plano para notificaciones del sistema operativo
# Funciona incluso cuando la aplicación no está abierta
# =============================================================================

import threading
import time
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Dict, List
import queue

# Intentar importar winotify
try:
    from winotify import Notification, audio
    WINOTIFY_DISPONIBLE = True
except ImportError:
    WINOTIFY_DISPONIBLE = False
    print("[NOTIF] winotify no disponible. Instalar con: pip install winotify")


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

APP_ID = "SoporteTecnico.Tickets"
APP_NAME = "Soporte Técnico IT"
ICONO_APP = None  # Puedes agregar ruta a un .ico

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

# Ruta de la aplicación receptora (para abrir al hacer clic)
RUTA_APP_RECEPTORA = PROJECT_ROOT / "app_receptora.py"
RUTA_PYTHON = PROJECT_ROOT / "python_embed" / "python.exe"

# Archivos de monitoreo
ARCHIVO_SOLICITUDES  = RUNTIME_DIR / "solicitudes_enlace.json"
DB_PATH              = RUNTIME_DIR / "tickets.db"          # SQLite (no Excel)
ARCHIVO_NOTIF_ESTADO = RUNTIME_DIR / "notificaciones_estado.json"

# Cola de notificaciones
_cola_notificaciones = queue.Queue()
_servicio_activo = False
_hilo_servicio: Optional[threading.Thread] = None

# Callback para cuando se hace clic en una notificación
_callback_click: Optional[Callable] = None

# Estado de notificaciones ya mostradas
_notificaciones_mostradas: Dict[str, str] = {}


# =============================================================================
# FUNCIONES DE NOTIFICACIÓN WINDOWS
# =============================================================================

def mostrar_notificacion_windows(
    titulo: str,
    mensaje: str,
    tipo: str = "info",  # info, exito, advertencia, error
    duracion: str = "short",  # short (7s), long (25s)
    abrir_app: bool = True  # Abrir app receptora al hacer clic
) -> bool:
    """
    Muestra una notificación toast en Windows.
    
    Args:
        titulo: Título de la notificación
        mensaje: Mensaje del cuerpo
        tipo: Tipo de notificación (afecta el sonido)
        duracion: short (7 segundos) o long (25 segundos)
        abrir_app: Si True, abre la app receptora al hacer clic
    
    Returns:
        True si se mostró correctamente, False en caso contrario
    """
    if not WINOTIFY_DISPONIBLE:
        print(f"[NOTIF] {titulo}: {mensaje}")
        return False
    
    try:
        notif = Notification(
            app_id=APP_NAME,
            title=titulo,
            msg=mensaje,
            duration=duracion,
            icon=ICONO_APP if ICONO_APP and os.path.exists(ICONO_APP) else ""
        )
        
        # Configurar audio según tipo
        if tipo == "error":
            notif.set_audio(audio.Reminder, loop=False)
        elif tipo == "advertencia":
            notif.set_audio(audio.LoopingAlarm, loop=False)
        elif tipo == "exito":
            notif.set_audio(audio.SMS, loop=False)
        else:
            notif.set_audio(audio.Default, loop=False)
        
        # Agregar acción para abrir la app al hacer clic
        if abrir_app:
            # Construir comando para abrir la app
            if RUTA_PYTHON.exists() and RUTA_APP_RECEPTORA.exists():
                comando = f'"{RUTA_PYTHON}" "{RUTA_APP_RECEPTORA}"'
                notif.add_actions(label="Abrir App", launch=comando)
            else:
                # Intentar con python del sistema
                notif.add_actions(label="Abrir App", launch=f'python "{RUTA_APP_RECEPTORA}"')
        
        notif.show()
        return True
        
    except Exception as e:
        print(f"[NOTIF] Error mostrando notificación: {e}")
        return False


def notificar_nueva_solicitud(solicitud: dict) -> bool:
    """Notifica una nueva solicitud de enlace."""
    hostname = solicitud.get("hostname", "Desconocido")
    usuario = solicitud.get("usuario_ad", "")
    mac = solicitud.get("mac_address", "")[:8]
    
    titulo = "🔗 Nueva Solicitud de Enlace"
    mensaje = f"Equipo: {hostname}\nUsuario: {usuario}\nMAC: {mac}..."
    
    return mostrar_notificacion_windows(titulo, mensaje, tipo="advertencia", duracion="long", abrir_app=True)


def notificar_nuevo_ticket(ticket: dict) -> bool:
    """Notifica un nuevo ticket."""
    turno = ticket.get("TURNO", "N/A")
    categoria = ticket.get("CATEGORIA", "General")
    usuario = ticket.get("USUARIO_AD", "")
    prioridad = ticket.get("PRIORIDAD", "Media")
    
    # Emoji según prioridad
    emoji = "🎫"
    if prioridad == "Crítica":
        emoji = "🚨"
    elif prioridad == "Alta":
        emoji = "⚠️"
    
    titulo = f"{emoji} Nuevo Ticket - Turno {turno}"
    mensaje = f"Categoría: {categoria}\nUsuario: {usuario}\nPrioridad: {prioridad}"
    
    tipo = "error" if prioridad in ["Crítica", "Alta"] else "info"
    return mostrar_notificacion_windows(titulo, mensaje, tipo=tipo, duracion="long", abrir_app=True)


def notificar_equipo_conectado(equipo: dict) -> bool:
    """Notifica cuando un equipo se conecta."""
    hostname = equipo.get("hostname", "Desconocido")
    ip = equipo.get("ip_address", "")
    
    titulo = "🖥️ Equipo Conectado"
    mensaje = f"{hostname}\nIP: {ip}"
    
    return mostrar_notificacion_windows(titulo, mensaje, tipo="info", duracion="short", abrir_app=True)


def notificar_equipo_desconectado(equipo: dict) -> bool:
    """Notifica cuando un equipo se desconecta."""
    hostname = equipo.get("hostname", "Desconocido")
    
    titulo = "📴 Equipo Desconectado"
    mensaje = f"{hostname} ya no está en línea"
    
    return mostrar_notificacion_windows(titulo, mensaje, tipo="advertencia", duracion="short", abrir_app=True)


# =============================================================================
# SERVICIO DE MONITOREO EN SEGUNDO PLANO
# =============================================================================

def _cargar_estado_notificaciones():
    """Carga el estado de notificaciones ya mostradas."""
    global _notificaciones_mostradas
    try:
        if ARCHIVO_NOTIF_ESTADO.exists():
            with open(ARCHIVO_NOTIF_ESTADO, 'r', encoding='utf-8') as f:
                _notificaciones_mostradas = json.load(f)
    except:
        _notificaciones_mostradas = {}


def _guardar_estado_notificaciones():
    """Guarda el estado de notificaciones."""
    try:
        with open(ARCHIVO_NOTIF_ESTADO, 'w', encoding='utf-8') as f:
            json.dump(_notificaciones_mostradas, f)
    except:
        pass


def _monitorear_solicitudes():
    """Monitorea el archivo de solicitudes para nuevas entradas."""
    global _notificaciones_mostradas
    
    try:
        if not ARCHIVO_SOLICITUDES.exists():
            return
        
        with open(ARCHIVO_SOLICITUDES, 'r', encoding='utf-8') as f:
            solicitudes = json.load(f)
        
        for mac, sol in solicitudes.items():
            if sol.get("estado") != "pendiente":
                continue
            
            # Crear clave única
            fecha_sol = sol.get("fecha_solicitud", "")
            clave = f"solicitud_{mac}_{fecha_sol}"
            
            # Si ya notificamos esta, saltar
            if clave in _notificaciones_mostradas:
                continue
            
            # Notificar
            if notificar_nueva_solicitud(sol):
                _notificaciones_mostradas[clave] = datetime.now().isoformat()
                _guardar_estado_notificaciones()
                print(f"[NOTIF] Nueva solicitud notificada: {sol.get('hostname')}")
                
    except Exception as e:
        pass  # Silenciar errores de lectura


def _monitorear_tickets():
    """Monitorea nuevos tickets en la base de datos SQLite."""
    global _notificaciones_mostradas

    try:
        if not DB_PATH.exists():
            return

        import sqlite3
        from datetime import datetime, timedelta

        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(
            "SELECT * FROM tickets WHERE ESTADO IN ('Abierto','En Cola') "
            "ORDER BY FECHA_APERTURA DESC LIMIT 50"
        )
        tickets = cur.fetchall()
        conn.close()

        for row in tickets:
            ticket = dict(row)
            estado = ticket.get("ESTADO", "")
            if estado not in ["Abierto", "En Cola"]:
                continue

            id_ticket = str(ticket.get("ID_TICKET", ""))
            fecha_apertura = str(ticket.get("FECHA_APERTURA", ""))
            clave = f"ticket_{id_ticket}"

            if clave in _notificaciones_mostradas:
                continue

            # Verificar que sea reciente (menos de 5 minutos)
            try:
                fecha_ticket = datetime.fromisoformat(fecha_apertura)
                if datetime.now() - fecha_ticket > timedelta(minutes=5):
                    continue
            except Exception:
                continue

            # Notificar
            if notificar_nuevo_ticket(ticket):
                _notificaciones_mostradas[clave] = datetime.now().isoformat()
                _guardar_estado_notificaciones()
                print(f"[NOTIF] Nuevo ticket notificado: {ticket.get('TURNO')}")

    except Exception:
        pass


def _loop_monitoreo():
    """Loop principal del servicio de monitoreo."""
    global _servicio_activo
    
    print("[NOTIF] Servicio de notificaciones iniciado")
    _cargar_estado_notificaciones()
    
    ultimo_check_solicitudes = 0
    ultimo_check_tickets = 0
    
    while _servicio_activo:
        try:
            ahora = time.time()
            
            # Verificar solicitudes cada 3 segundos
            if ahora - ultimo_check_solicitudes >= 3:
                _monitorear_solicitudes()
                ultimo_check_solicitudes = ahora
            
            # Verificar tickets cada 5 segundos
            if ahora - ultimo_check_tickets >= 5:
                _monitorear_tickets()
                ultimo_check_tickets = ahora
            
            # Procesar cola de notificaciones manuales
            try:
                while not _cola_notificaciones.empty():
                    tipo, datos = _cola_notificaciones.get_nowait()
                    
                    if tipo == "solicitud":
                        notificar_nueva_solicitud(datos)
                    elif tipo == "ticket":
                        notificar_nuevo_ticket(datos)
                    elif tipo == "equipo_conectado":
                        notificar_equipo_conectado(datos)
                    elif tipo == "equipo_desconectado":
                        notificar_equipo_desconectado(datos)
                    elif tipo == "custom":
                        mostrar_notificacion_windows(**datos)
            except:
                pass
            
            time.sleep(1)
            
        except Exception as e:
            print(f"[NOTIF] Error en loop: {e}")
            time.sleep(5)
    
    print("[NOTIF] Servicio de notificaciones detenido")


def iniciar_servicio_notificaciones():
    """Inicia el servicio de notificaciones en segundo plano."""
    global _servicio_activo, _hilo_servicio
    
    if _servicio_activo:
        print("[NOTIF] El servicio ya está activo")
        return True
    
    _servicio_activo = True
    _hilo_servicio = threading.Thread(
        target=_loop_monitoreo,
        daemon=True,
        name="ServicioNotificaciones"
    )
    _hilo_servicio.start()
    return True


def detener_servicio_notificaciones():
    """Detiene el servicio de notificaciones."""
    global _servicio_activo
    _servicio_activo = False
    print("[NOTIF] Deteniendo servicio...")


def esta_servicio_activo() -> bool:
    """Verifica si el servicio está activo."""
    return _servicio_activo


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def encolar_notificacion(tipo: str, datos: dict):
    """Encola una notificación para mostrarla."""
    _cola_notificaciones.put((tipo, datos))


def notificar_personalizado(titulo: str, mensaje: str, tipo: str = "info"):
    """Encola una notificación personalizada."""
    _cola_notificaciones.put(("custom", {
        "titulo": titulo,
        "mensaje": mensaje,
        "tipo": tipo
    }))


def limpiar_historial_notificaciones():
    """Limpia el historial de notificaciones mostradas."""
    global _notificaciones_mostradas
    _notificaciones_mostradas = {}
    _guardar_estado_notificaciones()
    print("[NOTIF] Historial limpiado")


# =============================================================================
# EJECUCIÓN STANDALONE
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SERVICIO DE NOTIFICACIONES - Sistema de Tickets IT")
    print("=" * 60)
    
    if not WINOTIFY_DISPONIBLE:
        print("\n[ERROR] winotify no está instalado.")
        print("Ejecuta: pip install winotify")
        sys.exit(1)
    
    # Mostrar notificación de inicio
    mostrar_notificacion_windows(
        titulo="🔔 Servicio de Notificaciones",
        mensaje="El sistema de notificaciones está activo",
        tipo="exito",
        duracion="short"
    )
    
    # Iniciar servicio
    iniciar_servicio_notificaciones()
    
    print("\nServicio ejecutándose en segundo plano...")
    print("Presiona Ctrl+C para detener\n")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nDeteniendo servicio...")
        detener_servicio_notificaciones()
        time.sleep(1)
        print("Servicio detenido.")
