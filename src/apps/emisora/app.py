# =============================================================================
# APP EMISORA (KUBITO) - Sistema de Tickets para Trabajadores
# =============================================================================
# Aplicación moderna e intuitiva para crear tickets de soporte técnico
# =============================================================================

import flet as ft
from flet import (
    Page, Container, Column, Row, Text, TextField, Dropdown, 
    Button, ProgressRing, AlertDialog, SnackBar,
    dropdown, Colors as colors, padding, border_radius,
    MainAxisAlignment, CrossAxisAlignment, FontWeight,
    TextAlign, Icons as icons, Icon, Divider, Card
)
from pathlib import Path
import asyncio
import sys
import secrets
import threading
from datetime import datetime
from typing import Optional, Dict, Any

# Importar módulo de acceso a datos
from data_access import (
    GestorTickets, 
    obtener_mac_address, 
    obtener_usuario_ad, 
    obtener_hostname,
    CATEGORIAS_DISPONIBLES,
    PRIORIDADES
)

# Importar cliente de red
from servidor_red import (
    enviar_ticket_a_servidor,
    buscar_servidor_en_red,
    cargar_config_servidor,
    registrar_en_servidor,
    enviar_heartbeat,
    solicitar_enlace,
    verificar_estado_enlace,
    verificar_servidor,
    enviar_recordatorio_ticket,
    cancelar_ticket_servidor,
    obtener_ticket_activo_servidor,
    obtener_tickets_activos_servidor,
    obtener_historial_usuario_servidor,
    enviar_mensaje_chat_ticket_servidor,
    obtener_chat_ticket_servidor,
    obtener_estado_servidor,
    HEARTBEAT_INTERVAL
)

# Sistema de notificaciones de Windows
try:
    from notificaciones_windows import (
        mostrar_notificacion_windows,
        WINOTIFY_DISPONIBLE
    )
except Exception:
    mostrar_notificacion_windows = None
    WINOTIFY_DISPONIBLE = False

# Validación remota de licencia/control de instalación
try:
    from licencias_cliente import validar_licencia_inicio, mostrar_banner_bloqueo, guardar_activation_key, limpiar_activation_key, TRIAL_LICENSE_KEY
except Exception:
    validar_licencia_inicio = None
    mostrar_banner_bloqueo = None
    guardar_activation_key = None
    limpiar_activation_key = None
    TRIAL_LICENSE_KEY = "KUBO-TRIAL-7D-GRATIS"

# Validación local reutilizable
try:
    from src.core.validators import InputValidator
except Exception:
    InputValidator = None

try:
    from src.core.app_preferences import (
        get_app_version,
        load_app_preferences,
        save_app_preferences,
        read_license_status,
        verify_license_now,
        send_support_report,
    )
except Exception:
    def get_app_version() -> str:
        return "0.0.0"

    def load_app_preferences(app_id: str) -> Dict[str, Any]:
        return {"ui": {}, "features": {}, "support": {}}

    def save_app_preferences(app_id: str, prefs: Dict[str, Any]) -> Dict[str, Any]:
        return prefs

    def read_license_status() -> Dict[str, Any]:
        return {}

    def verify_license_now(app_id: str) -> Dict[str, Any]:
        return {"ok": False, "message": "Módulo no disponible"}

    def send_support_report(app_id: str, report_type: str, message: str, contact: str = "", extra: Dict[str, Any] | None = None) -> Dict[str, Any]:
        return {"ok": False, "error": "Módulo no disponible"}

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# PALETA DE COLORES MODERNA
# =============================================================================
COLOR_PRIMARIO = "#2563EB"          # Azul moderno
COLOR_PRIMARIO_HOVER = "#1D4ED8"    # Azul oscuro
COLOR_SECUNDARIO = "#7C3AED"        # Violeta accent
COLOR_FONDO = "#F1F5F9"             # Gris muy claro
COLOR_TARJETA = "#FFFFFF"           # Blanco
COLOR_TEXTO = "#1E293B"             # Gris oscuro
COLOR_TEXTO_SEC = "#64748B"         # Gris medio
COLOR_EXITO = "#10B981"             # Verde esmeralda
COLOR_EXITO_CLARO = "#D1FAE5"       # Verde claro fondo
COLOR_ERROR = "#EF4444"             # Rojo
COLOR_ERROR_CLARO = "#FEE2E2"       # Rojo claro fondo
COLOR_ADVERTENCIA = "#F59E0B"       # Naranja
COLOR_ADVERTENCIA_CLARO = "#FEF3C7" # Naranja claro fondo
COLOR_INFO = "#06B6D4"              # Cyan
COLOR_INFO_CLARO = "#CFFAFE"        # Cyan claro fondo
COLOR_BORDE = "#E2E8F0"             # Gris claro para bordes

# Meses en español
MESES_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

def obtener_fecha_es() -> str:
    """Obtiene la fecha actual en formato español."""
    ahora = datetime.now()
    return f"{ahora.day} de {MESES_ES[ahora.month]}, {ahora.year}"


# =============================================================================
# ICONOS DE CATEGORÍAS
# =============================================================================
ICONOS_CATEGORIA = {
    "Hardware": icons.COMPUTER,
    "Software": icons.APPS,
    "Red/Conectividad": icons.WIFI,
    "Impresora": icons.PRINT,
    "Correo Electrónico": icons.EMAIL,
    "Accesos/Permisos": icons.LOCK,
    "Otro": icons.HELP_OUTLINE
}


# =============================================================================
# CONSTANTES DE DIÁLOGOS
# =============================================================================
DIALOGO_TIPOS = {
    "error": {
        "icono": icons.ERROR_ROUNDED,
        "color": COLOR_ERROR,
        "color_fondo": COLOR_ERROR_CLARO,
        "titulo": "¡Ups! Algo salió mal"
    },
    "exito": {
        "icono": icons.CHECK_CIRCLE_ROUNDED,
        "color": COLOR_EXITO,
        "color_fondo": COLOR_EXITO_CLARO,
        "titulo": "¡Perfecto!"
    },
    "advertencia": {
        "icono": icons.WARNING_ROUNDED,
        "color": COLOR_ADVERTENCIA,
        "color_fondo": COLOR_ADVERTENCIA_CLARO,
        "titulo": "Atención"
    },
    "info": {
        "icono": icons.INFO_ROUNDED,
        "color": COLOR_INFO,
        "color_fondo": COLOR_INFO_CLARO,
        "titulo": "Información"
    },
    "cargando": {
        "icono": icons.HOURGLASS_TOP_ROUNDED,
        "color": COLOR_PRIMARIO,
        "color_fondo": "#EFF6FF",
        "titulo": "Procesando..."
    },
    "conexion": {
        "icono": icons.WIFI_OFF_ROUNDED,
        "color": COLOR_ERROR,
        "color_fondo": COLOR_ERROR_CLARO,
        "titulo": "Error de Conexión"
    }
}


class AppEmisora:
    """
    Aplicación moderna para emisión de tickets de soporte técnico.
    Diseño intuitivo con guía paso a paso.
    """
    
    def __init__(self, page: Page):
        self.page = page
        self.gestor = GestorTickets()
        
        # Información del sistema
        self.mac_address: str = ""
        self.usuario_ad: str = ""
        self.hostname: str = ""
        
        # Configuración del servidor
        self.servidor_ip: str = ""
        self.servidor_puerto: int = 5555
        self.servidor_conectado: bool = False
        self.enlazado: bool = False  # Si fue aprobado por el admin
        self.estado_enlace: str = "sin_solicitud"  # pendiente, aprobado, rechazado
        self._solicitud_enviada: bool = False  # Flag para evitar duplicados
        self._conectando: bool = False  # Flag para evitar conexiones simultáneas
        
        # Referencias a controles
        self.txt_descripcion: Optional[TextField] = None
        self.dropdown_categoria: Optional[Dropdown] = None
        self.dropdown_prioridad: Optional[Dropdown] = None
        self.btn_enviar: Optional[Button] = None
        self._enviando: bool = False  # Flag para evitar doble envío
        self.progress_ring: Optional[ProgressRing] = None
        self.panel_estado: Optional[Container] = None
        self.lbl_hora: Optional[Text] = None
        self.panel_mi_ticket: Optional[Container] = None
        self.contenedor_principal: Optional[Column] = None
        
        # Sistema de overlay de carga
        self.overlay_carga: Optional[Container] = None
        self.texto_carga: Optional[Text] = None
        self._carga_activa: bool = False
        
        # Vista actual: "principal" o "configuracion"
        self.vista_actual: str = "principal"
        
        # Controles de configuración
        self.txt_ip_servidor: Optional[TextField] = None
        self.txt_puerto_servidor: Optional[TextField] = None
        self.lbl_estado_config: Optional[Text] = None
        self.panel_estado_config: Optional[Container] = None
        self.pref_switch_notificaciones = None
        self.pref_switch_animaciones = None
        self.pref_switch_diagnostico = None
        self.pref_txt_contacto: Optional[TextField] = None
        self.pref_txt_soporte: Optional[TextField] = None
        self._prefs = load_app_preferences("kubito")
        
        # Estado
        self.tecnicos_disponibles = []
        self.hay_disponible = False
        self.ticket_activo = None
        
        # Para actualizaciones de chat en tiempo real (optimistic update)
        self._chat_id_ticket = None
        self._chat_mensajes = []
        self._chat_mensajes_ids = set()
        self._chat_container_ref = None  # Referencia al contenedor del chat para actualizar

        # Configuración de historial en "Mis Tickets"
        self._historial_page_size: int = 4
        
        self._configurar_pagina()
        self._capturar_info_sistema()
        self._inicializar_servidor()  # Después de capturar info para tener MAC
        self._construir_ui()
        self._iniciar_reloj()
    
    def _configurar_pagina(self) -> None:
        """Configura la ventana principal."""
        self.page.title = "Kubito - Crear Ticket de Soporte"
        self.page.window.width = 500
        self.page.window.height = 720
        self.page.window.resizable = False
        self.page.bgcolor = COLOR_FONDO
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Windows usa mejor .ico para el icono de barra; .png queda como respaldo.
        icono_ico = PROJECT_ROOT / "icons" / "kubito.ico"
        icono_png = PROJECT_ROOT / "icons" / "kubito.png"
        if icono_ico.exists():
            self.page.window.icon = str(icono_ico)
        elif icono_png.exists():
            self.page.window.icon = str(icono_png)
    
    def _capturar_info_sistema(self) -> None:
        """Captura automática de información del equipo."""
        self.mac_address = obtener_mac_address()
        self.usuario_ad = obtener_usuario_ad()
        self.hostname = obtener_hostname()
    
    def _iniciar_reloj(self):
        """Inicia actualización del reloj cada minuto."""
        async def actualizar_reloj():
            while True:
                if self.lbl_hora:
                    self.lbl_hora.value = datetime.now().strftime("%I:%M %p")
                    self.page.update()
                await asyncio.sleep(60)
        self.page.run_task(actualizar_reloj)
    
    def _inicializar_servidor(self):
        """Inicializa la conexión con el servidor de tickets y solicita enlace."""
        # Evitar conexiones simultáneas
        if self._conectando:
            return
        self._conectando = True
        
        def conectar_servidor():
            try:
                # Intentar cargar configuración guardada (devuelve tupla)
                ip_guardada, puerto = cargar_config_servidor()
                
                print(f"[CLIENTE] Intentando conectar...")
                print(f"[CLIENTE] Config guardada: IP={ip_guardada}, Puerto={puerto}")
                
                if ip_guardada:
                    # Verificar que el servidor responde
                    if verificar_servidor(ip_guardada, puerto, timeout=3):
                        self.servidor_ip = ip_guardada
                        self.servidor_puerto = puerto
                        self.servidor_conectado = True
                        print(f"[CLIENTE] ✓ Conectado a servidor guardado: {ip_guardada}:{puerto}")
                    else:
                        print(f"[CLIENTE] ✗ Servidor {ip_guardada}:{puerto} no responde")
                        # Intentar buscar en la red
                        self.servidor_conectado = False
                
                # Si no hay config o el servidor guardado no responde, buscar en la red
                if not self.servidor_conectado:
                    print(f"[CLIENTE] Buscando servidor en la red...")
                    servidor = buscar_servidor_en_red()
                    if servidor:
                        self.servidor_ip = servidor["ip"]
                        self.servidor_puerto = servidor["puerto"]
                        self.servidor_conectado = True
                        print(f"[CLIENTE] ✓ Servidor encontrado: {servidor['ip']}:{servidor['puerto']}")
                    else:
                        print(f"[CLIENTE] ✗ No se encontró servidor en la red")
                
                if self.servidor_conectado:
                    # Verificar estado de enlace
                    estado = verificar_estado_enlace(
                        self.servidor_ip,
                        self.servidor_puerto,
                        self.mac_address
                    )
                    
                    self.estado_enlace = estado.get("estado", "sin_solicitud")
                    self.enlazado = estado.get("puede_enviar_tickets", False)
                    
                    if self.enlazado:
                        # Ya está aprobado - enlace permanente
                        print(f"[CLIENTE] Conectado y enlazado a {self.servidor_ip}:{self.servidor_puerto}")
                        self._solicitud_enviada = True
                    elif self.estado_enlace == "pendiente":
                        print(f"[CLIENTE] Solicitud pendiente de aprobación")
                        self._solicitud_enviada = True
                    elif self.estado_enlace == "rechazado":
                        print(f"[CLIENTE] Solicitud rechazada por el administrador")
                        self._solicitud_enviada = True
                    elif self.estado_enlace == "revocado":
                        # El admin revocó el enlace - NO enviar solicitud automática
                        print(f"[CLIENTE] Enlace revocado por el administrador. Contacte a IT.")
                        self._solicitud_enviada = True
                    elif self.estado_enlace == "sin_solicitud" and not self._solicitud_enviada:
                        # Solo enviar solicitud si es la primera vez (sin_solicitud)
                        self._solicitud_enviada = True
                        resultado = solicitar_enlace(
                            self.servidor_ip,
                            self.servidor_puerto,
                            self.mac_address,
                            self.hostname,
                            self.usuario_ad,
                            self.hostname
                        )
                        self.estado_enlace = resultado.get("estado", "pendiente")
                        self.enlazado = (self.estado_enlace == "aprobado")
                        print(f"[CLIENTE] Solicitud enviada - Estado: {self.estado_enlace}")
                    
                    # Actualizar UI con estado de enlace
                    self._actualizar_estado_enlace_ui()
                    
                    # Iniciar heartbeat solo si está enlazado
                    if self.enlazado:
                        self._iniciar_heartbeat()
                    elif self.estado_enlace == "pendiente":
                        # Verificar estado periódicamente si está pendiente
                        self._iniciar_verificacion_enlace()
                else:
                    print("[CLIENTE] Modo local - servidor no encontrado")
                    
            except Exception as e:
                print(f"[CLIENTE] Error: {e}")
                self.servidor_conectado = False
            finally:
                self._conectando = False
        
        # Ejecutar en segundo plano para no bloquear UI
        import threading
        threading.Thread(target=conectar_servidor, daemon=True).start()
    
    def _iniciar_verificacion_enlace(self):
        """Verifica periódicamente el estado del enlace si está pendiente."""
        import threading
        import time
        
        def verificar_loop():
            while self.servidor_conectado and not self.enlazado and self.estado_enlace == "pendiente":
                try:
                    estado = verificar_estado_enlace(
                        self.servidor_ip,
                        self.servidor_puerto,
                        self.mac_address
                    )
                    
                    nuevo_estado = estado.get("estado", "pendiente")
                    self.enlazado = estado.get("puede_enviar_tickets", False)
                    
                    if nuevo_estado != self.estado_enlace:
                        self.estado_enlace = nuevo_estado
                        self._actualizar_estado_enlace_ui()
                        
                        if self.enlazado:
                            print("[CLIENTE] ¡Enlace aprobado!")
                            self._iniciar_heartbeat()
                            break
                        elif nuevo_estado == "rechazado":
                            print("[CLIENTE] Enlace rechazado")
                            break
                            
                except Exception as e:
                    print(f"[CLIENTE] Error verificando enlace: {e}")
                
                time.sleep(10)  # Verificar cada 10 segundos
        
        threading.Thread(target=verificar_loop, daemon=True, name="VerificarEnlace").start()
    
    def _actualizar_estado_enlace_ui(self):
        """Actualiza la UI para mostrar el estado del enlace - Versión mejorada."""
        try:
            if hasattr(self, 'panel_estado_enlace') and self.panel_estado_enlace:
                mostrar_btn_reenviar = False
                
                if self.enlazado:
                    self.panel_estado_enlace.bgcolor = COLOR_EXITO
                    self.txt_estado_enlace.value = "Conectado y enlazado"
                    if hasattr(self, 'txt_subtexto_enlace'):
                        self.txt_subtexto_enlace.value = "Puedes crear tickets"
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = False
                elif self.estado_enlace == "pendiente":
                    self.panel_estado_enlace.bgcolor = COLOR_ADVERTENCIA
                    self.txt_estado_enlace.value = "Esperando aprobación"
                    if hasattr(self, 'txt_subtexto_enlace'):
                        self.txt_subtexto_enlace.value = "El administrador debe aprobar tu equipo"
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = True
                elif self.estado_enlace == "rechazado":
                    self.panel_estado_enlace.bgcolor = COLOR_ERROR
                    self.txt_estado_enlace.value = "Solicitud rechazada"
                    if hasattr(self, 'txt_subtexto_enlace'):
                        self.txt_subtexto_enlace.value = "Contacta al administrador"
                    mostrar_btn_reenviar = True
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = True
                elif self.estado_enlace == "revocado":
                    self.panel_estado_enlace.bgcolor = COLOR_ERROR
                    self.txt_estado_enlace.value = "Acceso revocado"
                    if hasattr(self, 'txt_subtexto_enlace'):
                        self.txt_subtexto_enlace.value = "Tu acceso fue revocado"
                    mostrar_btn_reenviar = True
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = True
                else:
                    self.panel_estado_enlace.bgcolor = COLOR_INFO
                    self.txt_estado_enlace.value = "Conectando al servidor"
                    if hasattr(self, 'txt_subtexto_enlace'):
                        self.txt_subtexto_enlace.value = "Estableciendo conexión..."
                
                # Actualizar visibilidad del botón de reenviar
                if hasattr(self, 'btn_reenviar_solicitud') and self.btn_reenviar_solicitud:
                    self.btn_reenviar_solicitud.visible = mostrar_btn_reenviar
                
                self.page.update()
        except Exception as e:
            print(f"[UI] Error actualizando estado: {e}")
    
    def _iniciar_heartbeat(self):
        """Envía heartbeat al servidor periódicamente."""
        import threading
        import time
        
        def heartbeat_loop():
            while self.servidor_conectado:
                try:
                    if not enviar_heartbeat(self.servidor_ip, self.servidor_puerto, self.mac_address):
                        self.servidor_conectado = False
                        # Intentar reconectar
                        self._inicializar_servidor()
                        break
                except:
                    pass
                time.sleep(HEARTBEAT_INTERVAL)
        
        threading.Thread(target=heartbeat_loop, daemon=True, name="Heartbeat").start()
        
        # Iniciar auto-refresco de tickets (fallback polling) y listener WebSocket
        self._iniciar_auto_refresco_tickets()
        self._iniciar_ws_listener()
    
    def _iniciar_auto_refresco_tickets(self):
        """Inicia un loop que refresca el estado de los tickets cada 5 segundos de forma silenciosa."""
        import threading
        import time
        
        # Usar lock para evitar race condition al verificar/setear el flag
        if getattr(self, '_auto_refresco_activo', False):
            print("[AUTO-REFRESCO] Ya hay un loop corriendo, ignorando")
            return
        
        self._auto_refresco_activo = True
        print("[AUTO-REFRESCO] Iniciando loop de auto-refresco")
        
        def _auto_refresco_loop():
            time.sleep(3)  # Esperar antes del primer refresco
            fallos_consecutivos = 0
            
            while self._auto_refresco_activo:
                try:
                    # Verificar condiciones básicas
                    if not self.servidor_conectado:
                        print("[AUTO-REFRESCO] Servidor desconectado, esperando...")
                        time.sleep(5)
                        continue
                    
                    if not self.enlazado or not self.servidor_ip:
                        time.sleep(5)
                        continue
                    
                    if not hasattr(self, '_tickets_content') or not self._tickets_content:
                        time.sleep(5)
                        continue
                    
                    # Consultar tickets activos desde el servidor (timeout aumentado)
                    resultado = obtener_tickets_activos_servidor(
                        self.servidor_ip, self.servidor_puerto, self.usuario_ad, self.mac_address
                    )
                    
                    if not resultado.get("success"):
                        fallos_consecutivos += 1
                        error_msg = resultado.get("error", "desconocido")
                        print(f"[AUTO-REFRESCO] Fallo #{fallos_consecutivos}: {error_msg}")
                        time.sleep(5)
                        continue
                    
                    # Éxito - resetear contador de fallos
                    fallos_consecutivos = 0
                    tickets_nuevos = resultado.get("tickets", [])
                    
                    # Actualizar la UI con datos frescos del servidor
                    try:
                        self._tickets_content.controls.clear()
                        
                        if len(tickets_nuevos) > 1:
                            self.ticket_activo = tickets_nuevos[-1]
                            if hasattr(self, '_form_section') and self._form_section.controls:
                                self._form_section.controls.clear()
                            self._tickets_content.controls.append(
                                self._build_panel_tickets_duplicados(tickets_nuevos)
                            )
                        elif len(tickets_nuevos) == 1:
                            self.ticket_activo = tickets_nuevos[0]
                            panel_activo = self._build_panel_ticket_activo(tickets_nuevos[0])
                            self._tickets_content.controls.append(panel_activo)
                            if hasattr(self, '_form_section') and self._form_section.controls:
                                self._form_section.controls.clear()
                        else:
                            self.ticket_activo = None
                            self._tickets_content.controls.append(
                                Container(
                                    content=Column([
                                        Row([
                                            Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                                            Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                        ], spacing=10),
                                        Container(height=12),
                                        Container(
                                            content=Row([
                                                Icon(icons.CHECK_CIRCLE_OUTLINE, size=28, color=COLOR_EXITO),
                                                Column([
                                                    Text("No tienes tickets activos", size=14,
                                                         weight=FontWeight.W_600, color=COLOR_TEXTO),
                                                    Text("Puedes crear uno nuevo con el formulario de abajo",
                                                         size=12, color=COLOR_TEXTO_SEC),
                                                ], spacing=2, expand=True),
                                            ], spacing=12),
                                            bgcolor="#F0FDF4",
                                            padding=ft.Padding.all(14),
                                            border_radius=ft.BorderRadius.all(10),
                                            border=ft.Border.all(1, "#BBF7D0"),
                                        ),
                                    ]),
                                    bgcolor=COLOR_TARJETA,
                                    border_radius=ft.BorderRadius.all(12),
                                    padding=ft.Padding.all(20),
                                    margin=ft.Padding.only(left=20, right=20, top=15),
                                )
                            )
                            if hasattr(self, '_form_section') and not self._form_section.controls:
                                self._form_section.controls = [
                                    self._crear_info_equipo(),
                                    self._crear_formulario(),
                                    self._crear_boton_envio(),
                                ]
                        
                        # Historial solo cada 3 ciclos para no sobrecargar
                        ciclo = getattr(self, '_ciclo_refresco', 0) + 1
                        self._ciclo_refresco = ciclo
                        if ciclo % 3 == 0:
                            try:
                                res_hist = obtener_historial_usuario_servidor(
                                    self.servidor_ip, self.servidor_puerto, self.usuario_ad, 15, self.mac_address
                                )
                                if res_hist.get("success"):
                                    historial = res_hist.get("tickets", [])
                                    ids_activos = [t.get("ID_TICKET", "") for t in tickets_nuevos]
                                    historial_pasado = [t for t in historial if t.get("ID_TICKET", "") not in ids_activos]
                                    if historial_pasado:
                                        panel_hist = self._build_panel_historial(historial_pasado)
                                        self._tickets_content.controls.append(panel_hist)
                            except:
                                pass
                        
                        self.page.update()
                    except Exception as ex_ui:
                        print(f"[AUTO-REFRESCO] Error construyendo UI: {ex_ui}")
                        import traceback
                        traceback.print_exc()
                    
                except Exception as ex:
                    print(f"[AUTO-REFRESCO] Error general: {ex}")
                    import traceback
                    traceback.print_exc()
                
                # Polling cada 30s (fallback; WebSocket cubre actualizaciones en tiempo real)
                time.sleep(30)
            
            self._auto_refresco_activo = False
            print("[AUTO-REFRESCO] Loop finalizado")
        
        threading.Thread(target=_auto_refresco_loop, daemon=True, name="AutoRefrescoTickets").start()
    
    def _detener_auto_refresco_tickets(self):
        """Detiene el loop de auto-refresco y el listener WebSocket."""
        self._auto_refresco_activo = False
        self._ws_listener_activo = False
    
    def _iniciar_ws_listener(self):
        """
        Conecta al servidor WebSocket (puerto 5556) y recibe eventos push.
        Cuando llega un evento ticket_creado / ticket_cancelado / ticket_actualizado,
        fuerza un refresco del panel de tickets.
        """
        import json as _json
        import time as _time

        try:
            import websockets as _ws_lib
            import asyncio as _asyncio
        except ImportError:
            print("[WS-CLIENTE] websockets no instalado — listener desactivado")
            return

        self._ws_listener_activo = True
        if not hasattr(self, "_ws_ui_refresh_lock"):
            self._ws_ui_refresh_lock = threading.Lock()

        EVENTOS_REFRESCO = {
            "ticket_creado", "ticket_actualizado", "ticket_cancelado", "ticket_chat_mensaje"
        }

        def _refrescar_ui_desde_ws():
            """Ejecuta un refresco visual (mismo código que el auto-refresco)."""
            # Evita refrescos en paralelo que pueden duplicar el panel visual.
            if not self._ws_ui_refresh_lock.acquire(blocking=False):
                return
            try:
                if not self.servidor_conectado or not self.enlazado or not self.servidor_ip:
                    return
                if not hasattr(self, '_tickets_content') or not self._tickets_content:
                    return

                resultado = obtener_tickets_activos_servidor(
                    self.servidor_ip, self.servidor_puerto, self.usuario_ad, self.mac_address
                )
                if not resultado.get("success"):
                    return

                tickets_nuevos = resultado.get("tickets", [])
                self._tickets_content.controls.clear()

                if len(tickets_nuevos) > 1:
                    self.ticket_activo = tickets_nuevos[-1]
                    if hasattr(self, '_form_section') and self._form_section.controls:
                        self._form_section.controls.clear()
                    self._tickets_content.controls.append(
                        self._build_panel_tickets_duplicados(tickets_nuevos)
                    )
                elif len(tickets_nuevos) == 1:
                    self.ticket_activo = tickets_nuevos[0]
                    self._tickets_content.controls.append(
                        self._build_panel_ticket_activo(tickets_nuevos[0])
                    )
                    if hasattr(self, '_form_section') and self._form_section.controls:
                        self._form_section.controls.clear()
                else:
                    self.ticket_activo = None

                self.page.update()
            except Exception as _e:
                print(f"[WS-CLIENTE] Error actualizando UI: {_e}")
            finally:
                try:
                    self._ws_ui_refresh_lock.release()
                except Exception:
                    pass

        async def _ws_loop():
            uri = f"ws://{self.servidor_ip}:5556"
            while self._ws_listener_activo:
                try:
                    async with _ws_lib.connect(uri, open_timeout=5,
                                               ping_interval=20, ping_timeout=10) as ws:
                        # Suscribirse con la identidad del usuario
                        await ws.send(_json.dumps({
                            "action": "subscribe",
                            "usuario_ad": self.usuario_ad,
                            "mac_address": self.mac_address
                        }))
                        print(f"[WS-CLIENTE] Conectado a {uri} como {self.usuario_ad}")

                        async for raw in ws:
                            if not self._ws_listener_activo:
                                break
                            try:
                                msg = _json.loads(raw)
                                evento = msg.get("evento", "")
                                if evento == "ticket_chat_mensaje":
                                    print(f"[WS-CLIENTE] Evento de chat recibido — actualizando solo el chat")
                                    msg_data = msg.get("mensaje_chat", {}) or {}
                                    id_ticket_evento = str(msg_data.get("id_ticket", self._chat_id_ticket or "")).strip()
                                    autor_id = str(msg_data.get("autor_id", "")).strip()
                                    es_mio = autor_id.lower() == (self.usuario_ad or "").lower()

                                    if id_ticket_evento:
                                        chat_abierto = self._chat_id_ticket == id_ticket_evento

                                        if not es_mio and not chat_abierto:
                                            try:
                                                contenido = str(msg_data.get("mensaje", ""))[:80]
                                                if mostrar_notificacion_windows:
                                                    mostrar_notificacion_windows(
                                                        titulo=f"💬 Mensaje en Ticket {id_ticket_evento}",
                                                        mensaje=f"{autor_id or 'IT'}: {contenido}",
                                                        tipo="info",
                                                        duracion="short",
                                                        abrir_app=False,
                                                    )
                                            except Exception:
                                                pass

                                        if chat_abierto:
                                            self._chat_id_ticket = id_ticket_evento
                                            self._actualizar_chat_ui(id_ticket_evento, mensaje_chat=msg_data)
                                elif evento in EVENTOS_REFRESCO:
                                    # Para otros eventos (ticket_creado, etc), refrescar todo
                                    print(f"[WS-CLIENTE] Evento recibido: {evento} — refrescando UI")
                                    _refrescar_ui_desde_ws()
                            except Exception:
                                pass

                except Exception as _ce:
                    if self._ws_listener_activo:
                        print(f"[WS-CLIENTE] Conexión cerrada ({_ce}), reintentando en 5s...")
                        await _asyncio.sleep(5)

        def _run_ws():
            loop = _asyncio.new_event_loop()
            _asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_ws_loop())
            finally:
                loop.close()

        threading.Thread(target=_run_ws, daemon=True, name="WS-Listener").start()
        print("[WS-CLIENTE] Listener iniciado")
    
    def _crear_header(self) -> Container:
        """Crea el encabezado principal con gradiente visual."""
        hora_actual = datetime.now().strftime("%I:%M %p")
        fecha_actual = obtener_fecha_es()
        
        self.lbl_hora = Text(hora_actual, size=16, weight=FontWeight.BOLD, color=colors.WHITE)
        
        # Botón de configuración
        btn_config = ft.IconButton(
            icon=icons.SETTINGS,
            icon_color=colors.WHITE70,
            icon_size=20,
            tooltip="Configuración de conexión",
            on_click=self._abrir_configuracion,
        )
        
        return Container(
            content=Column([
                # Barra superior con hora y configuración
                Row([
                    Row([
                        Icon(icons.ACCESS_TIME, size=16, color=colors.WHITE70),
                        self.lbl_hora,
                    ], spacing=5),
                    Row([
                        Text(fecha_actual, size=12, color=colors.WHITE70),
                        btn_config,
                    ], spacing=5),
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                
                Container(height=15),
                
                # Título principal
                Row([
                    Container(
                        content=Icon(icons.SUPPORT_AGENT, size=35, color=COLOR_PRIMARIO),
                        bgcolor=colors.WHITE,
                        border_radius=ft.BorderRadius.all(12),
                        padding=ft.Padding.all(10),
                    ),
                    Column([
                        Text("Kubito - Centro de Soporte", size=22, weight=FontWeight.BOLD, color=colors.WHITE),
                        Text("Crea un ticket y te ayudamos", size=13, color=colors.WHITE70),
                    ], spacing=2),
                ], spacing=15),
            ]),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[COLOR_PRIMARIO, COLOR_SECUNDARIO],
            ),
            padding=ft.Padding.symmetric(horizontal=25, vertical=20),
            border_radius=ft.BorderRadius.only(bottom_left=25, bottom_right=25),
        )
    
    def _crear_panel_estado(self) -> Container:
        """Panel de estado del servicio de soporte (consulta al servidor si está conectado)."""
        # Intentar obtener estado real del servidor
        if self.servidor_conectado and self.servidor_ip:
            try:
                estado_srv = obtener_estado_servidor(self.servidor_ip, self.servidor_puerto)
                self.hay_disponible = estado_srv.get("hay_disponible", False)
                nombres_tec = estado_srv.get("tecnicos_disponibles", [])
                self.tecnicos_disponibles = nombres_tec
            except Exception:
                self.tecnicos_disponibles = []
                self.hay_disponible = False
        else:
            # Fallback local (solo funciona en la receptora)
            try:
                tecs = self.gestor.obtener_tecnicos_disponibles()
                self.tecnicos_disponibles = tecs if isinstance(tecs, list) else tecs.values.tolist() if hasattr(tecs, 'values') else []
                self.hay_disponible = len(self.tecnicos_disponibles) > 0
            except Exception:
                self.tecnicos_disponibles = []
                self.hay_disponible = False
        
        cant_tec = len(self.tecnicos_disponibles) if isinstance(self.tecnicos_disponibles, list) else 0
        
        if self.hay_disponible:
            icono = icons.CHECK_CIRCLE
            color = COLOR_EXITO
            titulo = "Servicio Disponible"
            subtitulo = f"{cant_tec} técnico(s) listo(s) para atenderte"
            color_fondo = "#ECFDF5"
        else:
            icono = icons.HOURGLASS_TOP
            color = COLOR_ADVERTENCIA
            titulo = "Técnicos Ocupados"
            subtitulo = "Tu ticket será atendido en cuanto haya disponibilidad"
            color_fondo = "#FFFBEB"
        
        return Container(
            content=Row([
                Container(
                    content=Icon(icono, size=28, color=color),
                    bgcolor=color_fondo,
                    border_radius=ft.BorderRadius.all(10),
                    padding=ft.Padding.all(10),
                ),
                Column([
                    Text(titulo, size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                    Text(subtitulo, size=11, color=COLOR_TEXTO_SEC),
                ], spacing=2, expand=True),
                Container(
                    content=Row([
                        Icon(icons.PEOPLE, size=14, color=colors.WHITE),
                        Text(f"{cant_tec}", size=13, weight=FontWeight.BOLD, color=colors.WHITE),
                    ], spacing=4),
                    bgcolor=color,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                    border_radius=ft.BorderRadius.all(20),
                ),
            ], spacing=12),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=15),
        )
    
    def _reenviar_solicitud_enlace(self, e=None):
        """Reenvía la solicitud de enlace al servidor."""
        if not self.servidor_conectado:
            return
        
        def reenviar():
            try:
                # Resetear flags para permitir nueva solicitud
                self._solicitud_enviada = False
                self.estado_enlace = "sin_solicitud"
                
                # Enviar nueva solicitud
                resultado = solicitar_enlace(
                    self.servidor_ip,
                    self.servidor_puerto,
                    self.mac_address,
                    self.hostname,
                    self.usuario_ad,
                    self.hostname
                )
                
                self.estado_enlace = resultado.get("estado", "pendiente")
                self.enlazado = (self.estado_enlace == "aprobado")
                self._solicitud_enviada = True
                
                print(f"[CLIENTE] Solicitud reenviada - Estado: {self.estado_enlace}")
                
                # Actualizar UI
                self._actualizar_estado_enlace_ui()
                
                # Si está pendiente, iniciar verificación periódica
                if self.estado_enlace == "pendiente":
                    self._iniciar_verificacion_enlace()
                    
            except Exception as ex:
                print(f"[CLIENTE] Error al reenviar solicitud: {ex}")
        
        import threading
        threading.Thread(target=reenviar, daemon=True).start()
    
    def _crear_panel_estado_enlace(self) -> Container:
        """Panel que muestra el estado de enlace con el servidor - Versión mejorada."""
        # Determinar estado inicial con iconos mejorados
        mostrar_btn_reenviar = False
        icono = icons.LINK_ROUNDED
        
        if self.enlazado:
            color_fondo = COLOR_EXITO
            color_fondo_claro = COLOR_EXITO_CLARO
            texto = "Conectado y enlazado"
            icono = icons.CHECK_CIRCLE_ROUNDED
            subtexto = "Puedes crear tickets"
        elif self.estado_enlace == "pendiente":
            color_fondo = COLOR_ADVERTENCIA
            color_fondo_claro = COLOR_ADVERTENCIA_CLARO
            texto = "Esperando aprobación"
            icono = icons.HOURGLASS_TOP_ROUNDED
            subtexto = "El administrador debe aprobar tu equipo"
        elif self.estado_enlace == "rechazado":
            color_fondo = COLOR_ERROR
            color_fondo_claro = COLOR_ERROR_CLARO
            texto = "Solicitud rechazada"
            icono = icons.CANCEL_ROUNDED
            subtexto = "Contacta al administrador"
            mostrar_btn_reenviar = True
        elif self.estado_enlace == "revocado":
            color_fondo = COLOR_ERROR
            color_fondo_claro = COLOR_ERROR_CLARO
            texto = "Acceso revocado"
            icono = icons.BLOCK_ROUNDED
            subtexto = "Tu acceso fue revocado"
            mostrar_btn_reenviar = True
        elif self.servidor_conectado:
            color_fondo = COLOR_INFO
            color_fondo_claro = COLOR_INFO_CLARO
            texto = "Conectando al servidor"
            icono = icons.SYNC_ROUNDED
            subtexto = "Estableciendo conexión..."
        else:
            color_fondo = COLOR_TEXTO_SEC
            color_fondo_claro = "#F1F5F9"
            texto = "Buscando servidor"
            icono = icons.WIFI_FIND_ROUNDED
            subtexto = "Escaneando la red local..."
        
        self.txt_estado_enlace = Text(texto, size=13, color=colors.WHITE, weight=FontWeight.W_600)
        self.txt_subtexto_enlace = Text(subtexto, size=10, color=colors.WHITE70)
        
        # Botón para reenviar solicitud (mejorado)
        self.btn_reenviar_solicitud = Button(
            content=Row([
                Icon(icons.REFRESH_ROUNDED, size=14, color=colors.WHITE),
                Text("Reintentar", size=11, color=colors.WHITE, weight=FontWeight.W_500),
            ], spacing=5, alignment=MainAxisAlignment.CENTER),
            bgcolor=colors.WHITE24,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=8),
                padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            ),
            height=32,
            on_click=self._reenviar_solicitud_enlace,
            visible=mostrar_btn_reenviar
        )
        
        self.panel_estado_enlace = Container(
            content=Row([
                # Icono con fondo circular
                Container(
                    content=Icon(icono, size=22, color=color_fondo),
                    bgcolor=colors.WHITE,
                    border_radius=ft.BorderRadius.all(20),
                    width=38,
                    height=38,
                    alignment=ft.Alignment(0, 0),
                ),
                # Textos
                Column([
                    self.txt_estado_enlace,
                    self.txt_subtexto_enlace,
                ], spacing=1, expand=True),
                # Botón si aplica
                self.btn_reenviar_solicitud if mostrar_btn_reenviar else Container(),
            ], spacing=12),
            bgcolor=color_fondo,
            padding=ft.Padding.symmetric(horizontal=15, vertical=12),
            margin=ft.Padding.only(left=20, right=20, top=10),
            border_radius=ft.BorderRadius.all(12),
            animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
        )
        
        return self.panel_estado_enlace
    
    def _crear_info_equipo(self) -> Container:
        """Panel con información del equipo (solo lectura)."""
        def crear_campo(icono, etiqueta, valor):
            return Row([
                Container(
                    content=Icon(icono, size=16, color=COLOR_PRIMARIO),
                    bgcolor="#EFF6FF",
                    border_radius=ft.BorderRadius.all(6),
                    padding=ft.Padding.all(6),
                ),
                Column([
                    Text(etiqueta, size=10, color=COLOR_TEXTO_SEC),
                    Text(valor, size=13, weight=FontWeight.W_500, color=COLOR_TEXTO, selectable=True),
                ], spacing=0, expand=True),
            ], spacing=10)
        
        return Container(
            content=Column([
                Row([
                    Icon(icons.INFO_OUTLINE, size=18, color=COLOR_PRIMARIO),
                    Text("Tu Información", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                    Container(expand=True),
                    Container(
                        content=Text("Detectado automáticamente", size=9, color=COLOR_TEXTO_SEC),
                        bgcolor=COLOR_FONDO,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        border_radius=ft.BorderRadius.all(10),
                    ),
                ], spacing=8),
                Container(height=8),
                crear_campo(icons.PERSON, "Usuario", self.usuario_ad),
                crear_campo(icons.COMPUTER, "Equipo", self.hostname),
                crear_campo(icons.LAN, "Dirección MAC", self.mac_address),
            ], spacing=10),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=10),
        )
    
    def _crear_formulario(self) -> Container:
        """Formulario para crear el ticket."""
        # Dropdown de categoría
        self.dropdown_categoria = Dropdown(
            label="¿Qué tipo de problema tienes?",
            hint_text="Selecciona una categoría",
            options=[dropdown.Option(cat) for cat in CATEGORIAS_DISPONIBLES],
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=15, vertical=12),
            text_size=14,
        )
        
        # Dropdown de prioridad
        self.dropdown_prioridad = Dropdown(
            label="¿Qué tan urgente es?",
            hint_text="Selecciona la prioridad",
            options=[
                dropdown.Option("Baja", disabled=False),
                dropdown.Option("Media", disabled=False),
                dropdown.Option("Alta", disabled=False),
                dropdown.Option("Crítica", disabled=False),
            ],
            value="Media",
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            border_radius=10,
            content_padding=ft.Padding.symmetric(horizontal=15, vertical=12),
            text_size=14,
        )
        
        # Campo de descripción
        self.txt_descripcion = TextField(
            label="Describe tu problema",
            hint_text="Cuéntanos con detalle qué está pasando para poder ayudarte mejor...",
            multiline=True,
            min_lines=4,
            max_lines=6,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            border_radius=10,
            content_padding=ft.Padding.all(15),
            text_size=14,
        )
        
        return Container(
            content=Column([
                Row([
                    Container(
                        content=Text("2", size=12, weight=FontWeight.BOLD, color=colors.WHITE),
                        bgcolor=COLOR_PRIMARIO,
                        border_radius=ft.BorderRadius.all(15),
                        width=24,
                        height=24,
                        alignment=ft.Alignment(0, 0),
                    ),
                    Text("Cuéntanos el Problema", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                ], spacing=10),
                Container(height=12),
                self.dropdown_categoria,
                Container(height=12),
                self.dropdown_prioridad,
                Container(height=12),
                self.txt_descripcion,
                Container(height=5),
                Text("* Todos los campos son requeridos", size=10, color=COLOR_TEXTO_SEC, italic=True),
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(18),
            margin=ft.Padding.only(left=20, right=20, top=10),
        )
    
    def _crear_boton_envio(self) -> Container:
        """Botón de envío con animación."""
        self.progress_ring = ProgressRing(
            width=18,
            height=18,
            stroke_width=2,
            color=colors.WHITE,
            visible=False,
        )
        
        self.btn_enviar = Button(
            content=Row([
                Icon(icons.SEND_ROUNDED, color=colors.WHITE, size=20),
                Text("Crear Ticket", color=colors.WHITE, weight=FontWeight.W_600, size=15),
                self.progress_ring,
            ], spacing=10, alignment=MainAxisAlignment.CENTER),
            bgcolor=COLOR_PRIMARIO,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=12),
                overlay_color=COLOR_PRIMARIO_HOVER,
            ),
            width=220,
            height=50,
            on_click=self._enviar_ticket,
        )
        
        return Container(
            content=self.btn_enviar,
            alignment=ft.Alignment(0, 0),
            margin=ft.Padding.only(top=15, bottom=10),
        )
    
    def _crear_footer(self) -> Container:
        """Pie de página."""
        return Container(
            content=Row([
                Icon(icons.VERIFIED_USER, size=14, color=COLOR_TEXTO_SEC),
                Text("Departamento de TI", size=11, color=COLOR_TEXTO_SEC),
                Text("•", color=COLOR_TEXTO_SEC),
                Text("Soporte 24/7", size=11, color=COLOR_TEXTO_SEC),
            ], spacing=6, alignment=MainAxisAlignment.CENTER),
            margin=ft.Padding.only(bottom=15),
        )
    
    # =========================================================================
    # CONFIGURACIÓN DE CONEXIÓN
    # =========================================================================
    
    def _abrir_configuracion(self, e=None):
        """Abre la vista de configuración de conexión."""
        self.vista_actual = "configuracion"
        self.page.controls.clear()
        self._construir_vista_configuracion()
        self.page.update()
    
    def _cerrar_configuracion(self, e=None):
        """Cierra la vista de configuración y vuelve a la principal."""
        self.vista_actual = "principal"
        self.page.controls.clear()
        self._construir_ui()
        self.page.update()
    
    def _guardar_config_servidor(self, ip: str, puerto: int) -> bool:
        """Guarda la configuración del servidor en archivo."""
        try:
            from pathlib import Path
            config_path = RUNTIME_DIR / "servidor_config.txt"
            with open(config_path, "w") as f:
                f.write(f"{ip}:{puerto}")
            return True
        except Exception as e:
            print(f"Error guardando config: {e}")
            return False
    
    def _detectar_servidor_auto(self, e=None):
        """Detecta automáticamente el servidor en la red."""
        self._actualizar_estado_config("🔄 Buscando servidor en la red...", COLOR_INFO)
        
        def buscar():
            try:
                servidor = buscar_servidor_en_red(timeout=2)
                if servidor:
                    self.txt_ip_servidor.value = servidor["ip"]
                    self.txt_puerto_servidor.value = str(servidor["puerto"])
                    self._actualizar_estado_config(
                        f"✅ Servidor encontrado: {servidor['ip']}:{servidor['puerto']}", 
                        COLOR_EXITO
                    )
                else:
                    self._actualizar_estado_config(
                        "❌ No se encontró servidor en la red", 
                        COLOR_ERROR
                    )
                self.page.update()
            except Exception as ex:
                self._actualizar_estado_config(f"❌ Error: {str(ex)}", COLOR_ERROR)
                self.page.update()
        
        import threading
        threading.Thread(target=buscar, daemon=True).start()
    
    def _probar_conexion(self, e=None):
        """Prueba la conexión con el servidor configurado."""
        ip = self.txt_ip_servidor.value.strip() if self.txt_ip_servidor.value else ""
        puerto_str = self.txt_puerto_servidor.value.strip() if self.txt_puerto_servidor.value else "5555"
        
        if not ip:
            self._actualizar_estado_config("⚠️ Ingresa una dirección IP", COLOR_ADVERTENCIA)
            return
        
        try:
            puerto = int(puerto_str)
        except ValueError:
            self._actualizar_estado_config("⚠️ Puerto inválido", COLOR_ADVERTENCIA)
            return
        
        self._actualizar_estado_config(f"🔄 Probando conexión a {ip}:{puerto}...", COLOR_INFO)
        
        def probar():
            try:
                if verificar_servidor(ip, puerto, timeout=5):
                    self._actualizar_estado_config(
                        f"✅ Conexión exitosa a {ip}:{puerto}", 
                        COLOR_EXITO
                    )
                else:
                    self._actualizar_estado_config(
                        f"❌ No se pudo conectar a {ip}:{puerto}", 
                        COLOR_ERROR
                    )
                self.page.update()
            except Exception as ex:
                self._actualizar_estado_config(f"❌ Error: {str(ex)}", COLOR_ERROR)
                self.page.update()
        
        import threading
        threading.Thread(target=probar, daemon=True).start()
    
    def _guardar_y_conectar(self, e=None):
        """Guarda la configuración y conecta al servidor."""
        ip = self.txt_ip_servidor.value.strip() if self.txt_ip_servidor.value else ""
        puerto_str = self.txt_puerto_servidor.value.strip() if self.txt_puerto_servidor.value else "5555"
        
        if not ip:
            self._actualizar_estado_config("⚠️ Ingresa una dirección IP", COLOR_ADVERTENCIA)
            return
        
        try:
            puerto = int(puerto_str)
        except ValueError:
            self._actualizar_estado_config("⚠️ Puerto inválido", COLOR_ADVERTENCIA)
            return
        
        self._actualizar_estado_config(f"🔄 Conectando a {ip}:{puerto}...", COLOR_INFO)
        
        def conectar():
            try:
                if verificar_servidor(ip, puerto, timeout=5):
                    # Guardar configuración
                    self._guardar_config_servidor(ip, puerto)
                    
                    # Actualizar estado
                    self.servidor_ip = ip
                    self.servidor_puerto = puerto
                    self.servidor_conectado = True
                    
                    self._actualizar_estado_config(
                        f"✅ Conectado y configuración guardada", 
                        COLOR_EXITO
                    )
                    
                    # Verificar estado de enlace
                    estado = verificar_estado_enlace(
                        self.servidor_ip,
                        self.servidor_puerto,
                        self.mac_address
                    )
                    
                    self.estado_enlace = estado.get("estado", "sin_solicitud")
                    self.enlazado = estado.get("puede_enviar_tickets", False)
                    
                    # Si no hay solicitud, enviar una
                    if self.estado_enlace == "sin_solicitud" and not self._solicitud_enviada:
                        self._solicitud_enviada = True
                        resultado = solicitar_enlace(
                            self.servidor_ip,
                            self.servidor_puerto,
                            self.mac_address,
                            self.hostname,
                            self.usuario_ad,
                            self.hostname
                        )
                        self.estado_enlace = resultado.get("estado", "pendiente")
                        self.enlazado = (self.estado_enlace == "aprobado")
                    
                    self.page.update()
                    
                    # Esperar un momento y volver a la vista principal
                    import time
                    time.sleep(1.5)
                    self._cerrar_configuracion()
                else:
                    self._actualizar_estado_config(
                        f"❌ No se pudo conectar a {ip}:{puerto}", 
                        COLOR_ERROR
                    )
                    self.page.update()
            except Exception as ex:
                self._actualizar_estado_config(f"❌ Error: {str(ex)}", COLOR_ERROR)
                self.page.update()
        
        import threading
        threading.Thread(target=conectar, daemon=True).start()
    
    def _actualizar_estado_config(self, mensaje: str, color: str):
        """Actualiza el panel de estado en la configuración."""
        if self.lbl_estado_config:
            self.lbl_estado_config.value = mensaje
        if self.panel_estado_config:
            self.panel_estado_config.bgcolor = color
        try:
            self.page.update()
        except:
            pass

    def _guardar_preferencias_locales(self, e=None):
        """Guarda preferencias locales del usuario para Kubito."""
        self._prefs.setdefault("ui", {})
        self._prefs.setdefault("features", {})
        self._prefs.setdefault("support", {})

        self._prefs["ui"]["mostrar_notificaciones"] = bool(self.pref_switch_notificaciones.value) if self.pref_switch_notificaciones else True
        self._prefs["ui"]["animaciones"] = bool(self.pref_switch_animaciones.value) if self.pref_switch_animaciones else True
        self._prefs["features"]["diagnostico_rapido"] = bool(self.pref_switch_diagnostico.value) if self.pref_switch_diagnostico else True
        if self.pref_txt_contacto:
            self._prefs["support"]["email"] = self.pref_txt_contacto.value.strip()

        save_app_preferences("kubito", self._prefs)
        self._actualizar_estado_config("✓ Preferencias guardadas", COLOR_EXITO)

    def _verificar_licencia_manual(self, e=None):
        """Permite validación manual de licencia desde configuración."""
        resultado = verify_license_now("emisora")
        if resultado.get("ok"):
            self._mostrar_mensaje_exito(resultado.get("message", "Licencia válida"), "Verificación de licencia")
        else:
            self._mostrar_error(resultado.get("message", "No se pudo verificar licencia"), "Verificación de licencia")

    def _enviar_reporte_soporte(self, e=None):
        """Envía sugerencias/errores al servidor de licencias."""
        if not self.pref_txt_soporte or not self.pref_txt_soporte.value.strip():
            self._mostrar_advertencia("Escribe un mensaje antes de enviarlo", "Soporte")
            return

        contact = self.pref_txt_contacto.value.strip() if self.pref_txt_contacto else ""
        mensaje = self.pref_txt_soporte.value.strip()

        envio = send_support_report(
            app_id="kubito",
            report_type="sugerencia",
            message=mensaje,
            contact=contact,
            extra={"hostname": self.hostname, "usuario": self.usuario_ad},
        )

        if envio.get("ok"):
            self.pref_txt_soporte.value = ""
            self._mostrar_mensaje_exito("Reporte enviado correctamente", "Soporte")
            self.page.update()
        else:
            self._mostrar_error(f"No se pudo enviar: {envio.get('error', 'error desconocido')}", "Soporte")
    
    def _construir_vista_configuracion(self) -> None:
        """Construye la vista de configuración de conexión."""
        # Header de configuración
        header = Container(
            content=Column([
                Row([
                    ft.IconButton(
                        icon=icons.ARROW_BACK,
                        icon_color=colors.WHITE,
                        icon_size=24,
                        tooltip="Volver",
                        on_click=self._cerrar_configuracion,
                    ),
                    Text("Configuración de Conexión", size=18, weight=FontWeight.BOLD, color=colors.WHITE),
                    Container(width=40),  # Espaciador
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            ]),
            gradient=ft.LinearGradient(
                begin=ft.Alignment(-1, -1),
                end=ft.Alignment(1, 1),
                colors=[COLOR_PRIMARIO, COLOR_SECUNDARIO],
            ),
            padding=ft.Padding.symmetric(horizontal=15, vertical=15),
            border_radius=ft.BorderRadius.only(bottom_left=25, bottom_right=25),
        )
        
        # Estado actual de conexión
        if self.servidor_conectado:
            estado_texto = f"✅ Conectado a {self.servidor_ip}:{self.servidor_puerto}"
            color_estado = COLOR_EXITO
        else:
            estado_texto = "❌ Sin conexión al servidor"
            color_estado = COLOR_ERROR
        
        self.lbl_estado_config = Text(estado_texto, size=13, color=colors.WHITE, weight=FontWeight.W_500)
        
        self.panel_estado_config = Container(
            content=Row([
                Icon(icons.WIFI, size=20, color=colors.WHITE),
                self.lbl_estado_config,
            ], spacing=10, alignment=MainAxisAlignment.CENTER),
            bgcolor=color_estado,
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=15),
            border_radius=ft.BorderRadius.all(12),
        )
        
        # Campos de configuración
        self.txt_ip_servidor = TextField(
            label="Dirección IP del Servidor",
            hint_text="Ej: 192.168.1.100",
            value=self.servidor_ip if self.servidor_ip else "",
            prefix_icon=icons.COMPUTER,
            border_radius=12,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            text_size=14,
        )
        
        self.txt_puerto_servidor = TextField(
            label="Puerto",
            hint_text="5555",
            value=str(self.servidor_puerto) if self.servidor_puerto else "5555",
            prefix_icon=icons.NUMBERS,
            border_radius=12,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            text_size=14,
            width=150,
        )
        
        panel_campos = Container(
            content=Column([
                Text("Servidor de Tickets", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                Container(height=10),
                self.txt_ip_servidor,
                Container(height=10),
                Row([
                    self.txt_puerto_servidor,
                    Container(expand=True),
                ]),
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(20),
            margin=ft.Padding.only(left=20, right=20, top=15),
        )
        
        # Botones de acción
        btn_detectar = Button(
            content=Row([
                Icon(icons.SEARCH, color=colors.WHITE, size=18),
                Text("Detectar Automáticamente", color=colors.WHITE, weight=FontWeight.W_500, size=13),
            ], spacing=8, alignment=MainAxisAlignment.CENTER),
            bgcolor=COLOR_INFO,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            height=45,
            on_click=self._detectar_servidor_auto,
        )
        
        btn_probar = Button(
            content=Row([
                Icon(icons.WIFI_FIND, color=COLOR_PRIMARIO, size=18),
                Text("Probar Conexión", color=COLOR_PRIMARIO, weight=FontWeight.W_500, size=13),
            ], spacing=8, alignment=MainAxisAlignment.CENTER),
            bgcolor=COLOR_TARJETA,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
                side=ft.BorderSide(1, COLOR_PRIMARIO),
            ),
            height=45,
            on_click=self._probar_conexion,
        )
        
        btn_guardar = Button(
            content=Row([
                Icon(icons.SAVE, color=colors.WHITE, size=18),
                Text("Guardar y Conectar", color=colors.WHITE, weight=FontWeight.W_500, size=13),
            ], spacing=8, alignment=MainAxisAlignment.CENTER),
            bgcolor=COLOR_EXITO,
            style=ft.ButtonStyle(
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            height=50,
            on_click=self._guardar_y_conectar,
        )
        
        panel_botones = Container(
            content=Column([
                btn_detectar,
                Container(height=10),
                btn_probar,
                Container(height=15),
                btn_guardar,
            ]),
            margin=ft.Padding.only(left=20, right=20, top=15),
        )
        
        # Info adicional
        panel_info = Container(
            content=Column([
                Row([
                    Icon(icons.INFO_OUTLINE, size=16, color=COLOR_INFO),
                    Text("Información de conexión", size=13, weight=FontWeight.W_600, color=COLOR_TEXTO),
                ], spacing=8),
                Container(height=8),
                Text(
                    "• La detección automática busca el servidor en tu red local.\n"
                    "• Si conoces la IP del servidor, ingresala manualmente.\n"
                    "• El puerto por defecto es 5555.\n"
                    "• Asegúrate de que el firewall permita la conexión.",
                    size=11,
                    color=COLOR_TEXTO_SEC,
                ),
                Container(height=10),
                Row([
                    Icon(icons.COMPUTER, size=14, color=COLOR_TEXTO_SEC),
                    Text(f"Tu equipo: {self.hostname}", size=11, color=COLOR_TEXTO_SEC),
                ], spacing=5),
                Row([
                    Icon(icons.FINGERPRINT, size=14, color=COLOR_TEXTO_SEC),
                    Text(f"MAC: {self.mac_address}", size=11, color=COLOR_TEXTO_SEC),
                ], spacing=5),
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=15, bottom=20),
        )

        licencia = read_license_status()
        panel_version_licencia = Container(
            content=Column([
                Text("Producto y Licencia", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                Container(height=6),
                Text(f"Versión: {get_app_version()}", size=12, color=COLOR_TEXTO_SEC),
                Text(f"Servidor licencias: {licencia.get('server_url', 'N/D')}", size=12, color=COLOR_TEXTO_SEC),
                Text(f"Última razón: {licencia.get('last_reason', 'N/D')}", size=12, color=COLOR_TEXTO_SEC),
                Container(height=10),
                Button(
                    content=Row([
                        Icon(icons.VERIFIED_USER, color=colors.WHITE, size=16),
                        Text("Verificar licencia", color=colors.WHITE, size=12),
                    ], spacing=8),
                    bgcolor=COLOR_PRIMARIO,
                    on_click=self._verificar_licencia_manual,
                ),
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=10),
        )

        self.pref_switch_notificaciones = ft.Switch(
            label="Notificaciones activas",
            value=bool(self._prefs.get("ui", {}).get("mostrar_notificaciones", True)),
            on_change=self._guardar_preferencias_locales,
        )
        self.pref_switch_animaciones = ft.Switch(
            label="Animaciones de interfaz",
            value=bool(self._prefs.get("ui", {}).get("animaciones", True)),
            on_change=self._guardar_preferencias_locales,
        )
        self.pref_switch_diagnostico = ft.Switch(
            label="Diagnóstico rápido",
            value=bool(self._prefs.get("features", {}).get("diagnostico_rapido", True)),
            on_change=self._guardar_preferencias_locales,
        )

        panel_preferencias = Container(
            content=Column([
                Text("Preferencias de Kubito", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                Container(height=6),
                self.pref_switch_notificaciones,
                self.pref_switch_animaciones,
                self.pref_switch_diagnostico,
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=10),
        )

        self.pref_txt_contacto = TextField(
            label="Contacto (email o teléfono)",
            value=str(self._prefs.get("support", {}).get("email", "")),
            border_radius=12,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            on_blur=self._guardar_preferencias_locales,
        )
        self.pref_txt_soporte = TextField(
            label="Sugerencia o reporte",
            hint_text="Describe mejora, problema o solicitud",
            multiline=True,
            min_lines=3,
            max_lines=5,
            border_radius=12,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )

        panel_soporte = Container(
            content=Column([
                Text("Soporte y sugerencias", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                Container(height=8),
                self.pref_txt_contacto,
                Container(height=8),
                self.pref_txt_soporte,
                Container(height=10),
                Button(
                    content=Row([
                        Icon(icons.SEND_ROUNDED, color=colors.WHITE, size=16),
                        Text("Enviar reporte", color=colors.WHITE, size=12),
                    ], spacing=8),
                    bgcolor=COLOR_INFO,
                    on_click=self._enviar_reporte_soporte,
                ),
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=10, bottom=20),
        )
        
        # Construir vista
        contenedor = Column([
            header,
            self.panel_estado_config,
            panel_campos,
            panel_botones,
            panel_info,
            panel_version_licencia,
            panel_preferencias,
            panel_soporte,
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
        
        self.page.add(contenedor)
    
    # =========================================================================
    # SECCIÓN "MIS TICKETS" — Panel completo con activo + historial
    # =========================================================================
    
    def _crear_seccion_mis_tickets(self) -> Container:
        """
        Crea la sección completa 'Mis Tickets' con:
        - Ticket activo (si existe) con acciones
        - Historial de tickets anteriores
        """
        import threading
        
        # Contenedor dinámico que se llenará desde thread
        self._tickets_content = Column([], spacing=0)
        
        # Mostrar loading inicial
        self._tickets_content.controls = [
            Container(
                content=Column([
                    Row([
                        Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                        Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ], spacing=10),
                    Container(height=15),
                    Row([
                        ft.ProgressRing(width=20, height=20, stroke_width=2, color=COLOR_PRIMARIO),
                        Text("Cargando tus tickets...", size=13, color=COLOR_TEXTO_SEC),
                    ], spacing=10, alignment=MainAxisAlignment.CENTER),
                    Container(height=15),
                ]),
                bgcolor=COLOR_TARJETA,
                border_radius=ft.BorderRadius.all(12),
                padding=ft.Padding.all(20),
                margin=ft.Padding.only(left=20, right=20, top=15),
            )
        ]
        
        # Cargar datos en background (fase 1: tickets, fase 2: historial en paralelo)
        def cargar_tickets():
            tickets_activos = []
            servidor_respondio = False
            
            # 1) Obtener tickets activos desde el servidor (timeout corto: 5s)
            if self.servidor_conectado and self.servidor_ip and self.enlazado:
                try:
                    resultado = obtener_tickets_activos_servidor(
                        self.servidor_ip, self.servidor_puerto, self.usuario_ad, self.mac_address
                    )
                    servidor_respondio = resultado.get("success", False)
                    if servidor_respondio:
                        tickets_activos = resultado.get("tickets", [])
                    print(f"[CARGA] Servidor respondió: {servidor_respondio}, tickets: {len(tickets_activos)}")
                except Exception as e:
                    print(f"[CARGA] Error obteniendo tickets del servidor: {e}")
            
            # Fallback: si el servidor NO responde, mostrar el ticket recién creado
            # (self.ticket_activo es fresco tras creación; el auto-refresco lo corregirá si fue cancelado)
            if not tickets_activos and not servidor_respondio:
                if self.ticket_activo:
                    print(f"[CARGA] Usando ticket en memoria: {self.ticket_activo.get('ID_TICKET', '?')}")
                    tickets_activos = [self.ticket_activo]
                else:
                    try:
                        todos_activos = self.gestor.obtener_tickets_activos_usuario(self.usuario_ad, self.mac_address)
                        tickets_activos = todos_activos if todos_activos else []
                        print(f"[CARGA] Fallback Excel local: {len(tickets_activos)} tickets")
                    except:
                        pass
            
            # 2) Mostrar tickets INMEDIATAMENTE (sin esperar historial)
            _actualizar_panel_tickets(tickets_activos)
            
            # 3) Cargar historial en segundo plano
            def _cargar_historial():
                historial = []
                if self.servidor_conectado and self.servidor_ip and self.enlazado:
                    try:
                        res_hist = obtener_historial_usuario_servidor(
                            self.servidor_ip, self.servidor_puerto, self.usuario_ad, 15, self.mac_address
                        )
                        if res_hist.get("success"):
                            historial = res_hist.get("tickets", [])
                    except:
                        pass
                if not historial:
                    try:
                        historial = self.gestor.obtener_tickets_usuario(self.usuario_ad, 15, self.mac_address) or []
                    except:
                        pass
                
                if historial:
                    ids_activos = [t.get("ID_TICKET", "") for t in tickets_activos]
                    historial_pasado = [t for t in historial if t.get("ID_TICKET", "") not in ids_activos]
                    if historial_pasado:
                        try:
                            panel_hist = self._build_panel_historial(historial_pasado)
                            self._tickets_content.controls.append(panel_hist)
                            self.page.update()
                        except:
                            pass
            
            import threading as _th
            _th.Thread(target=_cargar_historial, daemon=True).start()
        
        def _actualizar_panel_tickets(tickets_activos: list):
            """Actualiza el panel de tickets en la UI (thread-safe)."""
            try:
                self._tickets_content.controls.clear()
                
                if len(tickets_activos) > 1:
                    self.ticket_activo = tickets_activos[-1]
                    if hasattr(self, '_form_section') and self._form_section.controls:
                        self._form_section.controls.clear()
                    self._tickets_content.controls.append(
                        self._build_panel_tickets_duplicados(tickets_activos)
                    )
                    
                elif len(tickets_activos) == 1:
                    self.ticket_activo = tickets_activos[0]
                    if hasattr(self, '_form_section') and self._form_section.controls:
                        self._form_section.controls.clear()
                    panel_activo = self._build_panel_ticket_activo(tickets_activos[0])
                    self._tickets_content.controls.append(panel_activo)
                    
                else:
                    self.ticket_activo = None
                    self._tickets_content.controls.append(
                        Container(
                            content=Column([
                                Row([
                                    Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                                    Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                ], spacing=10),
                                Container(height=12),
                                Container(
                                    content=Row([
                                        Icon(icons.CHECK_CIRCLE_OUTLINE, size=28, color=COLOR_EXITO),
                                        Column([
                                            Text("No tienes tickets activos", size=14,
                                                 weight=FontWeight.W_600, color=COLOR_TEXTO),
                                            Text("Puedes crear uno nuevo con el formulario de abajo",
                                                 size=12, color=COLOR_TEXTO_SEC),
                                        ], spacing=2, expand=True),
                                    ], spacing=12),
                                    bgcolor="#F0FDF4",
                                    padding=ft.Padding.all(14),
                                    border_radius=ft.BorderRadius.all(10),
                                    border=ft.Border.all(1, "#BBF7D0"),
                                ),
                            ]),
                            bgcolor=COLOR_TARJETA,
                            border_radius=ft.BorderRadius.all(12),
                            padding=ft.Padding.all(20),
                            margin=ft.Padding.only(left=20, right=20, top=15),
                        )
                    )
                    if hasattr(self, '_form_section') and not self._form_section.controls:
                        self._form_section.controls = [
                            self._crear_info_equipo(),
                            self._crear_formulario(),
                            self._crear_boton_envio(),
                        ]
                
                self.page.update()
            except Exception as ex:
                print(f"[CARGA] Error construyendo panel de tickets: {ex}")
                import traceback
                traceback.print_exc()
                # Mostrar error en lugar de pantalla en blanco
                try:
                    self._tickets_content.controls.clear()
                    self._tickets_content.controls.append(
                        Container(
                            content=Column([
                                Row([
                                    Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                                    Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                ], spacing=10),
                                Container(height=8),
                                Container(
                                    content=Row([
                                        Icon(icons.WARNING_AMBER_ROUNDED, size=22, color=COLOR_ADVERTENCIA),
                                        Column([
                                            Text("Error al cargar tickets", size=13, weight=FontWeight.W_600, color=COLOR_TEXTO),
                                            Text("Presiona Actualizar para reintentar", size=11, color=COLOR_TEXTO_SEC),
                                        ], spacing=2, expand=True),
                                    ], spacing=10),
                                    bgcolor="#FFFBEB",
                                    padding=ft.Padding.all(12),
                                    border_radius=ft.BorderRadius.all(10),
                                    border=ft.Border.all(1, COLOR_ADVERTENCIA),
                                ),
                            ]),
                            bgcolor=COLOR_TARJETA,
                            border_radius=ft.BorderRadius.all(12),
                            padding=ft.Padding.all(18),
                            margin=ft.Padding.only(left=20, right=20, top=15),
                        )
                    )
                    self.page.update()
                except:
                    pass
        
        threading.Thread(target=cargar_tickets, daemon=True).start()
        
        # Iniciar auto-refresco si estamos enlazados
        if self.enlazado and self.servidor_conectado:
            self._iniciar_auto_refresco_tickets()
        
        return Container(content=self._tickets_content)
    
    def _chat_mensaje_clave(self, mensaje: Dict[str, Any]) -> str:
        return str(mensaje.get("client_msg_id") or mensaje.get("id") or "")

    def _chat_upsert_mensaje_local(self, mensaje: Dict[str, Any]) -> bool:
        """Inserta o reemplaza un mensaje en la cache local del chat."""
        if not isinstance(mensaje, dict):
            return False

        clave = self._chat_mensaje_clave(mensaje)
        if clave:
            for indice, actual in enumerate(self._chat_mensajes):
                if self._chat_mensaje_clave(actual) == clave:
                    self._chat_mensajes[indice] = mensaje
                    return False

        self._chat_mensajes.append(mensaje)
        return True

    def _render_chat_rows(self, mensajes_chat: list[Dict[str, Any]]) -> list[Container]:
        filas = []
        for m in mensajes_chat[-8:]:
            autor_tipo = str(m.get("autor_tipo", "usuario"))
            autor_id = str(m.get("autor_id", ""))
            mensaje = str(m.get("mensaje", ""))
            fecha_m = str(m.get("fecha", ""))[:16]
            es_mio = autor_id.lower() == (self.usuario_ad or "").lower()
            color_chip = "#E0F2FE" if es_mio else "#F1F5F9"
            color_texto = COLOR_PRIMARIO if es_mio else COLOR_TEXTO
            etiqueta = "Tú" if es_mio else ("IT" if autor_tipo == "tecnico" else autor_id or "Usuario")
            filas.append(
                Container(
                    content=Column([
                        Row([
                            Text(etiqueta, size=10, weight=FontWeight.W_600, color=color_texto),
                            Text(fecha_m, size=9, color=COLOR_TEXTO_SEC),
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                        Text(mensaje, size=11, color=COLOR_TEXTO),
                    ], spacing=2),
                    bgcolor=color_chip,
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                )
            )
        if not filas:
            filas = [
                Container(
                    content=Text("Sin mensajes todavía. Puedes escribir al equipo IT.", 
                               size=11, color=COLOR_TEXTO_SEC),
                    bgcolor="#F8FAFC",
                    border=ft.Border.all(1, COLOR_BORDE),
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.all(8),
                )
            ]
        return filas

    def _actualizar_chat_ui(self, id_ticket: str, mensaje_chat: Optional[Dict[str, Any]] = None,
                            recargar: bool = False) -> None:
        """Actualiza SOLO el chat sin reconstruir todo el panel.
        Carga los mensajes del servidor y actualiza el contenedor del chat."""
        if not self._chat_container_ref:
            return
        
        try:
            if mensaje_chat:
                self._chat_upsert_mensaje_local(mensaje_chat)

            if recargar or not self._chat_mensajes or self._chat_id_ticket != id_ticket:
                mensajes_chat = []
                if self.servidor_conectado and self.servidor_ip and self.enlazado:
                    res_chat = obtener_chat_ticket_servidor(
                        self.servidor_ip,
                        self.servidor_puerto,
                        id_ticket=id_ticket,
                        limite=30,
                        offset=0,
                    )
                    if res_chat.get("success"):
                        mensajes_chat = res_chat.get("mensajes", []) or []
                    else:
                        # Fallback local cuando la consulta remota falle.
                        mensajes_chat = self.gestor.obtener_chat_ticket(id_ticket, limite=30, offset=0) or []
                else:
                    mensajes_chat = self.gestor.obtener_chat_ticket(id_ticket, limite=30, offset=0) or []

                if mensaje_chat:
                    clave_local = self._chat_mensaje_clave(mensaje_chat)
                    if clave_local:
                        reemplazado = False
                        for indice, actual in enumerate(mensajes_chat):
                            if self._chat_mensaje_clave(actual) == clave_local:
                                mensajes_chat[indice] = mensaje_chat
                                reemplazado = True
                                break
                        if not reemplazado:
                            mensajes_chat.append(mensaje_chat)
                self._chat_mensajes = mensajes_chat

            self._chat_id_ticket = id_ticket

            chat_rows = self._render_chat_rows(self._chat_mensajes)

            # Actualizar el contenedor del chat (Column con los mensajes)
            if self._chat_container_ref and hasattr(self._chat_container_ref, 'content'):
                if isinstance(self._chat_container_ref.content, Column):
                    self._chat_container_ref.content.controls.clear()
                    self._chat_container_ref.content.controls.extend(chat_rows)
                    try:
                        self.page.update()
                    except:
                        pass
        except Exception as e:
            print(f"[CHAT] Error actualizando chat: {e}")
    
    def _build_panel_ticket_activo(self, ticket: dict) -> Container:
        """Construye el panel visual del ticket activo con acciones."""
        estado = ticket.get("ESTADO", "Abierto")
        turno = ticket.get("TURNO", "-")
        id_ticket = ticket.get("ID_TICKET", "-")
        categoria = ticket.get("CATEGORIA", "-")
        descripcion = ticket.get("DESCRIPCION", "")
        tecnico = ticket.get("TECNICO_ASIGNADO", "")
        
        posicion = 0
        try:
            posicion = self.gestor.obtener_posicion_cola(id_ticket)
        except:
            pass
        
        # Colores según estado
        colores_estado = {
            "Abierto": (COLOR_ADVERTENCIA, "#FFFBEB", icons.HOURGLASS_EMPTY, "En espera de asignación"),
            "En Cola": (COLOR_INFO, "#E0F2FE", icons.QUEUE, f"Posición #{posicion}" if posicion else "En cola"),
            "En Proceso": (COLOR_PRIMARIO, "#EFF6FF", icons.ENGINEERING, f"Atendido por {tecnico}" if tecnico else "Un técnico te atiende"),
            "En Espera": (COLOR_TEXTO_SEC, "#F1F5F9", icons.PAUSE_CIRCLE, "Esperando información"),
        }
        color, color_fondo, icono, estado_desc = colores_estado.get(
            estado, (COLOR_INFO, "#E0F2FE", icons.INFO, estado)
        )
        
        # Formato de fecha
        fecha_ticket = ticket.get("FECHA_APERTURA", "")
        fecha_str = "Hoy"
        if fecha_ticket:
            try:
                if hasattr(fecha_ticket, 'strftime'):
                    fecha_str = fecha_ticket.strftime("%d/%m %I:%M %p")
                else:
                    fecha_str = str(fecha_ticket)[:16]
            except:
                fecha_str = "Hoy"

        # Cargar historial de chat reciente del ticket
        chat_editable = estado not in {"Cerrado", "Cancelado"}
        mensajes_chat = []
        if self.servidor_conectado and self.servidor_ip and self.enlazado and id_ticket and id_ticket != "-":
            try:
                res_chat = obtener_chat_ticket_servidor(
                    self.servidor_ip,
                    self.servidor_puerto,
                    id_ticket=id_ticket,
                    limite=30,
                    offset=0,
                )
                if res_chat.get("success"):
                    mensajes_chat = res_chat.get("mensajes", []) or []
            except Exception:
                mensajes_chat = []
        elif id_ticket and id_ticket != "-":
            try:
                mensajes_chat = self.gestor.obtener_chat_ticket(id_ticket, limite=30, offset=0) or []
            except Exception:
                mensajes_chat = []

        txt_chat = TextField(
            hint_text="Escribe un mensaje para IT...",
            multiline=True,
            min_lines=1,
            max_lines=3,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            dense=True,
            expand=True,
            disabled=not chat_editable,
        )

        chat_rows = []
        for m in mensajes_chat[-8:]:
            autor_tipo = str(m.get("autor_tipo", "usuario"))
            autor_id = str(m.get("autor_id", ""))
            mensaje = str(m.get("mensaje", ""))
            fecha_m = str(m.get("fecha", ""))[:16]
            es_mio = autor_id.lower() == (self.usuario_ad or "").lower()
            color_chip = "#E0F2FE" if es_mio else "#F1F5F9"
            color_texto = COLOR_PRIMARIO if es_mio else COLOR_TEXTO
            etiqueta = "Tú" if es_mio else ("IT" if autor_tipo == "tecnico" else autor_id or "Usuario")
            chat_rows.append(
                Container(
                    content=Column([
                        Row([
                            Text(etiqueta, size=10, weight=FontWeight.W_600, color=color_texto),
                            Text(fecha_m, size=9, color=COLOR_TEXTO_SEC),
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                        Text(mensaje, size=11, color=COLOR_TEXTO),
                    ], spacing=2),
                    bgcolor=color_chip,
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.symmetric(horizontal=8, vertical=6),
                )
            )
        if not chat_rows:
            chat_rows = [
                Container(
                    content=Text("Sin mensajes todavía. Puedes escribir al equipo IT.", size=11, color=COLOR_TEXTO_SEC),
                    bgcolor="#F8FAFC",
                    border=ft.Border.all(1, COLOR_BORDE),
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.all(8),
                )
            ]

        def _enviar_chat(e):
            if not chat_editable:
                self._mostrar_advertencia("Este ticket ya no permite escribir porque está cerrado o cancelado.")
                return

            mensaje = (txt_chat.value or "").strip()
            if not mensaje:
                return
            enviar_por_red = bool(self.servidor_conectado and self.servidor_ip and self.enlazado)

            # OPTIMISTIC UPDATE: Agregar el mensaje localmente sin esperar al servidor
            ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            client_msg_id = secrets.token_hex(8)
            mensaje_local = {
                "id": f"temp-{client_msg_id}",  # ID temporal, será reemplazado por el servidor
                "client_msg_id": client_msg_id,
                "id_ticket": id_ticket,
                "fecha": ahora,
                "autor_tipo": "usuario",
                "autor_id": self.usuario_ad,
                "mensaje": mensaje,
            }
            
            # Agregar o reemplazar el mensaje a la lista local
            self._chat_upsert_mensaje_local(mensaje_local)
            self._chat_id_ticket = id_ticket
            
            # Limpiar campo de texto INMEDIATAMENTE
            txt_chat.value = ""
            try:
                self.page.update()
            except:
                pass
            
            # Actualizar el UI del chat sin reconstruir todo el panel
            self._actualizar_chat_ui(id_ticket, mensaje_chat=mensaje_local)

            if not enviar_por_red:
                # Modo local: persistir en DB para no perder el mensaje.
                try:
                    msg_local_db = self.gestor.agregar_mensaje_chat_ticket(
                        id_ticket=id_ticket,
                        autor_tipo="usuario",
                        autor_id=self.usuario_ad,
                        mensaje=mensaje,
                    )
                    if msg_local_db:
                        self._actualizar_chat_ui(id_ticket, mensaje_chat=msg_local_db)
                    self._mostrar_info("Mensaje guardado en modo local. Se sincronizará al reconectar.", "Chat sin conexión")
                except Exception as ex:
                    self._mostrar_error("Error de chat", f"No se pudo guardar en local: {ex}")
                return
            
            # Enviar el mensaje al servidor de forma asincrónica (sin bloquear)
            def _send_async():
                try:
                    resultado = enviar_mensaje_chat_ticket_servidor(
                        self.servidor_ip,
                        self.servidor_puerto,
                        id_ticket=id_ticket,
                        mensaje=mensaje,
                        autor_id=self.usuario_ad,
                        autor_tipo="usuario",
                        client_msg_id=client_msg_id,
                    )
                    if resultado.get("success"):
                        # El servidor responde — sincroniza solo el mensaje afectado
                        mensaje_servidor = resultado.get("mensaje_chat") or {}
                        if isinstance(mensaje_servidor, dict):
                            mensaje_servidor.setdefault("client_msg_id", client_msg_id)
                            self._actualizar_chat_ui(id_ticket, mensaje_chat=mensaje_servidor)
                    else:
                        # Error: mostrar notificación pero el mensaje se mantiene localmente
                        self._mostrar_error("Error de chat", resultado.get("error", "No se pudo enviar mensaje"))
                except Exception as ex:
                    self._mostrar_error("Error de chat", str(ex))

            import threading as _th
            _th.Thread(target=_send_async, daemon=True).start()
        
        # Crear el contenedor del chat y almacenar referencia
        chat_container = Container(
            content=Column(chat_rows, spacing=6, scroll=ft.ScrollMode.AUTO),
            bgcolor="#FFFFFF",
            border=ft.Border.all(1, COLOR_BORDE),
            border_radius=ft.BorderRadius.all(10),
            padding=ft.Padding.all(8),
            height=170,
        )
        self._chat_container_ref = chat_container
        self._chat_id_ticket = id_ticket
        self._chat_mensajes = mensajes_chat
        
        return Container(
            content=Column([
                # Header con título y badge de estado
                Row([
                    Row([
                        Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                        Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ], spacing=10),
                    Container(
                        content=Row([
                            Container(
                                width=8, height=8,
                                border_radius=ft.BorderRadius.all(4),
                                bgcolor=color,
                            ),
                            Text(estado, size=11, color=color, weight=FontWeight.W_600),
                        ], spacing=5),
                        bgcolor=color_fondo,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                        border_radius=ft.BorderRadius.all(12),
                    ),
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                
                Container(height=12),
                
                # Card con turno, ticket, fecha
                Container(
                    content=Row([
                        Column([
                            Text("TURNO", size=9, color=COLOR_TEXTO_SEC, weight=FontWeight.W_500),
                            Text(str(turno), size=32, weight=FontWeight.BOLD, color=color),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
                        Container(width=1, height=50, bgcolor=COLOR_BORDE),
                        Column([
                            Text("TICKET", size=9, color=COLOR_TEXTO_SEC, weight=FontWeight.W_500),
                            Text(f"#{id_ticket}", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
                        Container(width=1, height=50, bgcolor=COLOR_BORDE),
                        Column([
                            Text("FECHA", size=9, color=COLOR_TEXTO_SEC, weight=FontWeight.W_500),
                            Text(fecha_str, size=11, weight=FontWeight.W_600, color=COLOR_TEXTO),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
                    ], alignment=MainAxisAlignment.SPACE_AROUND),
                    bgcolor=color_fondo,
                    padding=ft.Padding.all(14),
                    border_radius=ft.BorderRadius.all(10),
                ),
                
                Container(height=10),
                
                # Estado descriptivo + categoría
                Row([
                    Icon(icono, size=16, color=color),
                    Text(estado_desc, size=12, color=COLOR_TEXTO, weight=FontWeight.W_500),
                    Text("•", color=COLOR_TEXTO_SEC),
                    Icon(ICONOS_CATEGORIA.get(categoria, icons.HELP_OUTLINE), size=14, color=COLOR_TEXTO_SEC),
                    Text(categoria, size=12, color=COLOR_TEXTO_SEC),
                ], spacing=6),
                
                # Descripción resumida
                Container(
                    content=Text(
                        (descripcion[:80] + "...") if len(str(descripcion)) > 80 else str(descripcion),
                        size=12, color=COLOR_TEXTO_SEC, italic=True,
                    ),
                    padding=ft.Padding.only(top=8),
                ) if descripcion else Container(),

                Container(height=12),

                Row([
                    Icon(icons.FORUM, size=15, color=COLOR_PRIMARIO),
                    Text("Chat con IT", size=12, weight=FontWeight.W_600, color=COLOR_TEXTO),
                ], spacing=6),

                chat_container,

                Row([
                    txt_chat,
                    Button(
                        content=Row([
                            Icon(icons.SEND, color=colors.WHITE, size=14),
                            Text("Enviar", color=colors.WHITE, size=11, weight=FontWeight.W_500),
                        ], spacing=4),
                        bgcolor=COLOR_PRIMARIO,
                        on_click=_enviar_chat,
                        disabled=not chat_editable,
                    ),
                ], spacing=8, vertical_alignment=CrossAxisAlignment.END),
                
                Container(height=14),
                
                # === BOTONES DE ACCIÓN ===
                Row([
                    # Actualizar
                    Button(
                        content=Row([
                            Icon(icons.REFRESH, color=COLOR_PRIMARIO, size=15),
                            Text("Actualizar", color=COLOR_PRIMARIO, weight=FontWeight.W_500, size=11),
                        ], spacing=4, alignment=MainAxisAlignment.CENTER),
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            side=ft.BorderSide(1, COLOR_PRIMARIO),
                        ),
                        bgcolor=COLOR_TARJETA,
                        on_click=self._refrescar_ticket,
                        expand=True,
                    ),
                    Container(width=6),
                    # Recordatorio
                    Button(
                        content=Row([
                            Icon(icons.NOTIFICATIONS_ACTIVE, color=COLOR_ADVERTENCIA, size=15),
                            Text("Recordar", color=COLOR_ADVERTENCIA, weight=FontWeight.W_500, size=11),
                        ], spacing=4, alignment=MainAxisAlignment.CENTER),
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            side=ft.BorderSide(1, COLOR_ADVERTENCIA),
                        ),
                        bgcolor=COLOR_TARJETA,
                        on_click=lambda e: self._mostrar_dialogo_recordatorio(),
                        expand=True,
                    ),
                    Container(width=6),
                    # Cancelar
                    Button(
                        content=Row([
                            Icon(icons.CANCEL, color=COLOR_ERROR, size=15),
                            Text("Cancelar", color=COLOR_ERROR, weight=FontWeight.W_500, size=11),
                        ], spacing=4, alignment=MainAxisAlignment.CENTER),
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            side=ft.BorderSide(1, COLOR_ERROR),
                        ),
                        bgcolor=COLOR_TARJETA,
                        on_click=lambda e: self._mostrar_dialogo_cancelar(),
                        expand=True,
                    ),
                ], spacing=0),
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(2, color),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(18),
            margin=ft.Padding.only(left=20, right=20, top=15),
        )
    
    def _build_panel_tickets_duplicados(self, tickets: list) -> Container:
        """Construye panel de alerta cuando hay múltiples tickets activos.
        El usuario debe elegir cuál conservar y cancelar los demás."""
        
        # Construir tarjetas de cada ticket
        tarjetas = []
        for t in tickets:
            estado = t.get("ESTADO", "Abierto")
            turno = t.get("TURNO", "-")
            id_ticket = t.get("ID_TICKET", "-")
            categoria = t.get("CATEGORIA", "-")
            descripcion = str(t.get("DESCRIPCION", ""))[:60]
            if len(str(t.get("DESCRIPCION", ""))) > 60:
                descripcion += "..."
            
            fecha_ticket = t.get("FECHA_APERTURA", "")
            fecha_str = ""
            if fecha_ticket:
                try:
                    if hasattr(fecha_ticket, 'strftime'):
                        fecha_str = fecha_ticket.strftime("%d/%m %I:%M %p")
                    else:
                        fecha_str = str(fecha_ticket)[:16]
                except:
                    fecha_str = str(fecha_ticket)[:16]
            
            color_map = {
                "Abierto": COLOR_ADVERTENCIA,
                "En Cola": COLOR_INFO,
                "En Proceso": COLOR_PRIMARIO,
                "En Espera": COLOR_TEXTO_SEC,
            }
            color_e = color_map.get(estado, COLOR_INFO)
            
            # Closure para capturar valores correctamente
            def _crear_acciones(ticket_conservar, ticket_id_conservar):
                def on_conservar(e):
                    self._resolver_tickets_duplicados(ticket_conservar, tickets)
                return on_conservar
            
            tarjeta = Container(
                content=Column([
                    Row([
                        Container(
                            content=Text(f"T{turno}", size=14, weight=FontWeight.BOLD,
                                        color=colors.WHITE),
                            bgcolor=color_e,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                            border_radius=ft.BorderRadius.all(8),
                        ),
                        Column([
                            Text(f"#{id_ticket}", size=11, color=COLOR_TEXTO_SEC),
                            Text(estado, size=10, color=color_e, weight=FontWeight.W_600),
                        ], spacing=1, expand=True),
                        Text(fecha_str, size=10, color=COLOR_TEXTO_SEC),
                    ], spacing=10, vertical_alignment=CrossAxisAlignment.CENTER),
                    Container(height=4),
                    Row([
                        Icon(ICONOS_CATEGORIA.get(categoria, icons.HELP_OUTLINE), 
                             size=13, color=COLOR_TEXTO_SEC),
                        Text(categoria, size=11, color=COLOR_TEXTO_SEC),
                    ], spacing=4),
                    Text(descripcion, size=11, color=COLOR_TEXTO_SEC, italic=True) if descripcion else Container(),
                    Container(height=6),
                    Button(
                        content=Row([
                            Icon(icons.CHECK_CIRCLE, color=colors.WHITE, size=14),
                            Text("Conservar este", color=colors.WHITE, weight=FontWeight.W_500, size=11),
                        ], spacing=4, alignment=MainAxisAlignment.CENTER),
                        bgcolor=COLOR_PRIMARIO,
                        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                        on_click=_crear_acciones(t, id_ticket),
                        width=200,
                        height=32,
                    ),
                ], spacing=2),
                bgcolor=COLOR_TARJETA,
                border=ft.Border.all(1, COLOR_BORDE),
                border_radius=ft.BorderRadius.all(10),
                padding=ft.Padding.all(12),
            )
            tarjetas.append(tarjeta)
        
        return Container(
            content=Column([
                # Header con alerta
                Row([
                    Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                    Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                ], spacing=10),
                Container(height=10),
                # Banner de advertencia
                Container(
                    content=Row([
                        Icon(icons.WARNING_AMBER, size=28, color=COLOR_ERROR),
                        Column([
                            Text(f"Tienes {len(tickets)} tickets abiertos", size=14,
                                 weight=FontWeight.W_600, color=COLOR_ERROR),
                            Text("Solo puedes tener 1 ticket activo. Elige cuál conservar.",
                                 size=12, color=COLOR_TEXTO_SEC),
                            Text("Los demás serán cancelados automáticamente.",
                                 size=11, color=COLOR_TEXTO_SEC, italic=True),
                        ], spacing=2, expand=True),
                    ], spacing=12),
                    bgcolor=COLOR_ERROR_CLARO,
                    padding=ft.Padding.all(14),
                    border_radius=ft.BorderRadius.all(10),
                    border=ft.Border.all(1, COLOR_ERROR),
                ),
                Container(height=12),
                # Lista de tickets
                *tarjetas,
            ]),
            bgcolor=COLOR_TARJETA,
            border=ft.Border.all(2, COLOR_ERROR),
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(18),
            margin=ft.Padding.only(left=20, right=20, top=15),
        )
    
    def _resolver_tickets_duplicados(self, ticket_conservar: dict, todos_tickets: list):
        """Cancela todos los tickets excepto el elegido por el usuario."""
        import threading
        
        id_conservar = ticket_conservar.get("ID_TICKET", "")
        
        # Mostrar loading
        if hasattr(self, '_tickets_content') and self._tickets_content:
            self._tickets_content.controls.clear()
            self._tickets_content.controls.append(
                Container(
                    content=Column([
                        Row([
                            Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                            Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        ], spacing=10),
                        Container(height=15),
                        Row([
                            ft.ProgressRing(width=20, height=20, stroke_width=2, color=COLOR_PRIMARIO),
                            Text("Cancelando tickets duplicados...", size=13, color=COLOR_TEXTO_SEC),
                        ], spacing=10, alignment=MainAxisAlignment.CENTER),
                        Container(height=15),
                    ]),
                    bgcolor=COLOR_TARJETA,
                    border_radius=ft.BorderRadius.all(12),
                    padding=ft.Padding.all(20),
                    margin=ft.Padding.only(left=20, right=20, top=15),
                )
            )
            try:
                self.page.update()
            except:
                pass
        
        def _cancelar_duplicados():
            cancelados = 0
            for t in todos_tickets:
                tid = t.get("ID_TICKET", "")
                if tid and tid != id_conservar:
                    try:
                        if self.servidor_conectado and self.servidor_ip:
                            cancelar_ticket_servidor(
                                self.servidor_ip, self.servidor_puerto,
                                tid, self.usuario_ad,
                                "Cancelado automáticamente: ticket duplicado"
                            )
                            cancelados += 1
                    except Exception as ex:
                        print(f"[CLIENTE] Error cancelando ticket duplicado {tid}: {ex}")
            
            print(f"[CLIENTE] Cancelados {cancelados} tickets duplicados, conservado: {id_conservar}")
            
            # Actualizar estado y UI
            self.ticket_activo = ticket_conservar
            try:
                self.page.controls.clear()
                self._construir_ui()
                self.page.update()
            except Exception as ex:
                print(f"[CLIENTE] Error reconstruyendo UI: {ex}")
        
        threading.Thread(target=_cancelar_duplicados, daemon=True).start()
    
    def _build_panel_historial(self, tickets: list) -> Container:
        """Construye el panel de historial de tickets anteriores."""
        tickets_historial = list(tickets[:50])
        page_size = self._historial_page_size if self._historial_page_size > 0 else 4
        pagina_actual = 0

        color_map = {
            "Cerrado": (COLOR_EXITO, icons.CHECK_CIRCLE),
            "Cancelado": (COLOR_ERROR, icons.CANCEL),
            "Abierto": (COLOR_ADVERTENCIA, icons.HOURGLASS_EMPTY),
            "En Cola": (COLOR_INFO, icons.QUEUE),
            "En Proceso": (COLOR_PRIMARIO, icons.ENGINEERING),
            "En Espera": (COLOR_TEXTO_SEC, icons.PAUSE_CIRCLE),
        }

        lista_historial = ft.ListView(spacing=0, padding=0, height=190)
        txt_paginacion = Text("", size=10, color=COLOR_TEXTO_SEC)
        btn_prev = Button(
            content=Row([
                Icon(icons.CHEVRON_LEFT, size=16, color=COLOR_TEXTO_SEC),
                Text("Anterior", size=11, color=COLOR_TEXTO_SEC),
            ], spacing=4),
            bgcolor="#F8FAFC",
            height=34,
        )
        btn_next = Button(
            content=Row([
                Text("Siguiente", size=11, color=COLOR_TEXTO_SEC),
                Icon(icons.CHEVRON_RIGHT, size=16, color=COLOR_TEXTO_SEC),
            ], spacing=4),
            bgcolor="#F8FAFC",
            height=34,
        )

        def _fila_historial(t: dict, idx_global: int) -> Container:
            estado = t.get("ESTADO", "?")
            turno = t.get("TURNO", "-")
            categoria = t.get("CATEGORIA", "-")
            fecha = t.get("FECHA_APERTURA", "")

            fecha_str = ""
            if fecha:
                try:
                    if hasattr(fecha, "strftime"):
                        fecha_str = fecha.strftime("%d/%m/%y")
                    else:
                        fecha_str = str(fecha)[:10]
                except Exception:
                    fecha_str = str(fecha)[:10]

            color_e, icono_e = color_map.get(estado, (COLOR_TEXTO_SEC, icons.CIRCLE))

            return Container(
                content=Row([
                    Icon(icono_e, size=16, color=color_e),
                    Container(
                        content=Text(f"T{turno}", size=11, weight=FontWeight.BOLD, color=COLOR_PRIMARIO),
                        bgcolor="#EFF6FF",
                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                        border_radius=ft.BorderRadius.all(4),
                    ),
                    Text(categoria, size=12, color=COLOR_TEXTO, expand=True),
                    Text(estado, size=10, color=color_e, weight=FontWeight.W_500),
                    Text(fecha_str, size=10, color=COLOR_TEXTO_SEC),
                ], spacing=8, vertical_alignment=CrossAxisAlignment.CENTER),
                padding=ft.Padding.symmetric(vertical=8, horizontal=6),
                border_radius=ft.BorderRadius.all(6),
                bgcolor="#FAFAFA" if idx_global % 2 == 0 else "transparent",
            )

        def _render_pagina() -> None:
            nonlocal pagina_actual
            total = len(tickets_historial)
            total_paginas = max(1, (total + page_size - 1) // page_size)
            pagina_actual = max(0, min(pagina_actual, total_paginas - 1))

            inicio = pagina_actual * page_size
            fin = min(inicio + page_size, total)

            lista_historial.controls.clear()
            for idx_global, t in enumerate(tickets_historial[inicio:fin], start=inicio):
                lista_historial.controls.append(_fila_historial(t, idx_global))

            if total == 0:
                txt_paginacion.value = "Sin historial"
            else:
                txt_paginacion.value = f"Mostrando {inicio + 1}-{fin} de {total} | Página {pagina_actual + 1}/{total_paginas}"

            btn_prev.disabled = pagina_actual <= 0
            btn_next.disabled = pagina_actual >= (total_paginas - 1)

            if self.page:
                self.page.update()

        def _pagina_anterior(e):
            nonlocal pagina_actual
            pagina_actual -= 1
            _render_pagina()

        def _pagina_siguiente(e):
            nonlocal pagina_actual
            pagina_actual += 1
            _render_pagina()

        btn_prev.on_click = _pagina_anterior
        btn_next.on_click = _pagina_siguiente

        panel = Container(
            content=Column([
                Row([
                    Icon(icons.HISTORY, size=16, color=COLOR_TEXTO_SEC),
                    Text("Historial de Tickets", size=13, weight=FontWeight.W_600, color=COLOR_TEXTO),
                    Container(expand=True),
                    Container(
                        content=Text(f"{len(tickets_historial)}", size=10, color=COLOR_PRIMARIO, weight=FontWeight.BOLD),
                        bgcolor="#EFF6FF",
                        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                        border_radius=ft.BorderRadius.all(10),
                    ),
                ], spacing=8),
                Container(height=6),
                Divider(height=1, color=COLOR_BORDE),
                Container(height=6),
                Container(
                    content=lista_historial,
                    bgcolor="#FFFFFF",
                    border=ft.Border.all(1, "#EEF2F7"),
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.symmetric(horizontal=4, vertical=2),
                ),
                Container(height=8),
                Row([
                    btn_prev,
                    Container(expand=True),
                    txt_paginacion,
                    Container(expand=True),
                    btn_next,
                ], vertical_alignment=CrossAxisAlignment.CENTER),
            ]),
            bgcolor=COLOR_TARJETA,
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.all(16),
            margin=ft.Padding.only(left=20, right=20, top=10, bottom=5),
        )

        _render_pagina()
        return panel
    
    def _refrescar_ticket(self, e):
        """Refresca el estado del ticket activo consultando al servidor.
        Solo actualiza la sección de tickets (no reconstruye toda la UI)."""
        import threading

        # Guardar referencia al ticket actual por si el servidor falla
        ticket_respaldo = self.ticket_activo

        # Mostrar loading en la sección de tickets
        if hasattr(self, '_tickets_content') and self._tickets_content:
            self._tickets_content.controls.clear()
            self._tickets_content.controls.append(
                Container(
                    content=Column([
                        Row([
                            Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                            Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        ], spacing=10),
                        Container(height=15),
                        Row([
                            ft.ProgressRing(width=20, height=20, stroke_width=2, color=COLOR_PRIMARIO),
                            Text("Actualizando ticket...", size=13, color=COLOR_TEXTO_SEC),
                        ], spacing=10, alignment=MainAxisAlignment.CENTER),
                        Container(height=15),
                    ]),
                    bgcolor=COLOR_TARJETA,
                    border_radius=ft.BorderRadius.all(12),
                    padding=ft.Padding.all(20),
                    margin=ft.Padding.only(left=20, right=20, top=15),
                )
            )
            try:
                self.page.update()
            except:
                pass

        def _refrescar_async():
            tickets_activos = []
            servidor_respondio = False

            # 1) Consultar tickets activos desde el servidor
            if self.servidor_conectado and self.servidor_ip and self.enlazado:
                try:
                    resultado = obtener_tickets_activos_servidor(
                        self.servidor_ip, self.servidor_puerto, self.usuario_ad, self.mac_address
                    )
                    servidor_respondio = resultado.get("success", False)
                    if servidor_respondio:
                        tickets_activos = resultado.get("tickets", [])
                except Exception as ex:
                    print(f"[CLIENTE] Error refrescando tickets: {ex}")
            
            # Fallback: si el servidor NO responde, usar ticket actual o consultar Excel
            if not tickets_activos and not servidor_respondio:
                if ticket_respaldo:
                    tickets_activos = [ticket_respaldo]
                else:
                    try:
                        todos = self.gestor.obtener_tickets_activos_usuario(self.usuario_ad, self.mac_address)
                        tickets_activos = todos if todos else []
                    except:
                        pass

            # 2) Mostrar tickets INMEDIATAMENTE (sin esperar historial)
            _mostrar_tickets_en_panel(tickets_activos)
            
            # 3) Historial en paralelo
            def _cargar_historial_refresh():
                historial = []
                if self.servidor_conectado and self.servidor_ip and self.enlazado:
                    try:
                        res_hist = obtener_historial_usuario_servidor(
                            self.servidor_ip, self.servidor_puerto, self.usuario_ad, 15, self.mac_address
                        )
                        if res_hist.get("success"):
                            historial = res_hist.get("tickets", [])
                    except:
                        pass
                if not historial:
                    try:
                        historial = self.gestor.obtener_tickets_usuario(self.usuario_ad, 15, self.mac_address) or []
                    except:
                        pass
                if historial:
                    ids_activos = [t.get("ID_TICKET", "") for t in tickets_activos]
                    historial_pasado = [t for t in historial if t.get("ID_TICKET", "") not in ids_activos]
                    if historial_pasado:
                        try:
                            panel_hist = self._build_panel_historial(historial_pasado)
                            self._tickets_content.controls.append(panel_hist)
                            self.page.update()
                        except:
                            pass

            import threading as _th2
            _th2.Thread(target=_cargar_historial_refresh, daemon=True).start()

        def _mostrar_tickets_en_panel(tickets_activos: list):
            """Actualiza el panel de tickets (shared helper para refresh)."""
            try:
                if not hasattr(self, '_tickets_content') or not self._tickets_content:
                    return
                
                self._tickets_content.controls.clear()

                if len(tickets_activos) > 1:
                    self.ticket_activo = tickets_activos[-1]
                    if hasattr(self, '_form_section') and self._form_section.controls:
                        self._form_section.controls.clear()
                    self._tickets_content.controls.append(
                        self._build_panel_tickets_duplicados(tickets_activos)
                    )
                elif len(tickets_activos) == 1:
                    self.ticket_activo = tickets_activos[0]
                    panel_activo = self._build_panel_ticket_activo(tickets_activos[0])
                    self._tickets_content.controls.append(panel_activo)
                    if hasattr(self, '_form_section') and self._form_section.controls:
                        self._form_section.controls.clear()
                else:
                    self.ticket_activo = None
                    self._tickets_content.controls.append(
                        Container(
                            content=Column([
                                Row([
                                    Icon(icons.CONFIRMATION_NUMBER, size=20, color=COLOR_PRIMARIO),
                                    Text("Mis Tickets", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                ], spacing=10),
                                Container(height=12),
                                Container(
                                    content=Row([
                                        Icon(icons.CHECK_CIRCLE_OUTLINE, size=28, color=COLOR_EXITO),
                                        Column([
                                            Text("No tienes tickets activos", size=14,
                                                 weight=FontWeight.W_600, color=COLOR_TEXTO),
                                            Text("Puedes crear uno nuevo con el formulario de abajo",
                                                 size=12, color=COLOR_TEXTO_SEC),
                                        ], spacing=2, expand=True),
                                    ], spacing=12),
                                    bgcolor="#F0FDF4",
                                    padding=ft.Padding.all(14),
                                    border_radius=ft.BorderRadius.all(10),
                                    border=ft.Border.all(1, "#BBF7D0"),
                                ),
                            ]),
                            bgcolor=COLOR_TARJETA,
                            border_radius=ft.BorderRadius.all(12),
                            padding=ft.Padding.all(20),
                            margin=ft.Padding.only(left=20, right=20, top=15),
                        )
                    )
                    if hasattr(self, '_form_section') and not self._form_section.controls:
                        self._form_section.controls = [
                            self._crear_info_equipo(),
                            self._crear_formulario(),
                            self._crear_boton_envio(),
                        ]

                self.page.update()
            except Exception as ex:
                print(f"[CLIENTE] Error actualizando sección de tickets: {ex}")
                import traceback
                traceback.print_exc()

        threading.Thread(target=_refrescar_async, daemon=True).start()
    
    def _mostrar_dialogo_recordatorio(self):
        """Muestra diálogo para enviar recordatorio con nota opcional."""
        if not self.ticket_activo:
            return
        
        txt_nota = TextField(
            label="Nota (opcional)",
            hint_text="Escribe un mensaje para el técnico...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_ADVERTENCIA,
        )
        
        def enviar_recordatorio(e):
            self._cerrar_dialogo()
            self._procesar_recordatorio(txt_nota.value or "")
        
        dialogo = AlertDialog(
            modal=True,
            title=Row([
                Icon(icons.NOTIFICATIONS_ACTIVE, color=COLOR_ADVERTENCIA, size=24),
                Text("Enviar Recordatorio", weight=FontWeight.W_600, size=16, color=COLOR_TEXTO),
            ], spacing=10),
            content=Container(
                content=Column([
                    Text(
                        f"Se enviará un recordatorio para tu ticket #{self.ticket_activo.get('TURNO', 'N/A')}",
                        size=13,
                        color=COLOR_TEXTO_SEC,
                    ),
                    Container(height=10),
                    txt_nota,
                ]),
                width=320,
                padding=ft.Padding.all(5),
            ),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: self._cerrar_dialogo()),
                Button(
                    content=Row([
                        Icon(icons.SEND, color=colors.WHITE, size=16),
                        Text("Enviar", color=colors.WHITE, weight=FontWeight.W_500),
                    ], spacing=6, alignment=MainAxisAlignment.CENTER),
                    bgcolor=COLOR_ADVERTENCIA,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=enviar_recordatorio,
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _procesar_recordatorio(self, nota: str):
        """Envía el recordatorio al servidor."""
        if not self.ticket_activo:
            return
        
        id_ticket = self.ticket_activo.get("ID_TICKET", "")
        
        # Mostrar indicador de progreso
        snackbar = SnackBar(
            content=Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=colors.WHITE),
                Text("Enviando recordatorio...", color=colors.WHITE),
            ], spacing=10),
            bgcolor=COLOR_ADVERTENCIA,
            duration=10000,
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
        
        try:
            if self.servidor_conectado and self.servidor_ip:
                resultado = enviar_recordatorio_ticket(
                    self.servidor_ip,
                    self.servidor_puerto,
                    id_ticket,
                    self.usuario_ad,
                    nota
                )
                
                snackbar.open = False
                self.page.update()
                
                if resultado.get("success"):
                    self._mostrar_mensaje_exito("✅ Recordatorio enviado correctamente")
                else:
                    self._mostrar_error(f"Error: {resultado.get('error', 'No se pudo enviar')}")
            else:
                snackbar.open = False
                self.page.update()
                self._mostrar_error("No hay conexión con el servidor")
        except Exception as e:
            snackbar.open = False
            self.page.update()
            self._mostrar_error(f"Error: {str(e)}")
    
    def _mostrar_dialogo_cancelar(self):
        """Muestra diálogo para cancelar el ticket con nota opcional."""
        if not self.ticket_activo:
            return
        
        txt_nota = TextField(
            label="Motivo (opcional)",
            hint_text="¿Por qué deseas cancelar el ticket?",
            multiline=True,
            min_lines=2,
            max_lines=4,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_ERROR,
        )
        
        def confirmar_cancelacion(e):
            self._cerrar_dialogo()
            self._procesar_cancelacion(txt_nota.value or "")
        
        dialogo = AlertDialog(
            modal=True,
            title=Row([
                Icon(icons.WARNING_AMBER, color=COLOR_ERROR, size=24),
                Text("Cancelar Ticket", weight=FontWeight.W_600, size=16, color=COLOR_ERROR),
            ], spacing=10),
            content=Container(
                content=Column([
                    Text(
                        f"¿Estás seguro de cancelar tu ticket #{self.ticket_activo.get('TURNO', 'N/A')}?",
                        size=13,
                        color=COLOR_TEXTO,
                    ),
                    Text(
                        "Esta acción no se puede deshacer.",
                        size=12,
                        color=COLOR_TEXTO_SEC,
                        italic=True,
                    ),
                    Container(height=10),
                    txt_nota,
                ]),
                width=320,
                padding=ft.Padding.all(5),
            ),
            actions=[
                ft.TextButton("Volver", on_click=lambda e: self._cerrar_dialogo()),
                Button(
                    content=Row([
                        Icon(icons.CANCEL, color=colors.WHITE, size=16),
                        Text("Cancelar Ticket", color=colors.WHITE, weight=FontWeight.W_500),
                    ], spacing=6, alignment=MainAxisAlignment.CENTER),
                    bgcolor=COLOR_ERROR,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)),
                    on_click=confirmar_cancelacion,
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _procesar_cancelacion(self, nota: str):
        """Cancela el ticket en el servidor."""
        if not self.ticket_activo:
            return
        
        id_ticket = self.ticket_activo.get("ID_TICKET", "")
        
        # Mostrar indicador de progreso
        snackbar = SnackBar(
            content=Row([
                ft.ProgressRing(width=16, height=16, stroke_width=2, color=colors.WHITE),
                Text("Cancelando ticket...", color=colors.WHITE),
            ], spacing=10),
            bgcolor=COLOR_ERROR,
            duration=10000,
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()
        
        try:
            if self.servidor_conectado and self.servidor_ip:
                resultado = cancelar_ticket_servidor(
                    self.servidor_ip,
                    self.servidor_puerto,
                    id_ticket,
                    self.usuario_ad,
                    nota
                )
                
                snackbar.open = False
                self.page.update()
                
                if resultado.get("success"):
                    self._mostrar_mensaje_exito("✅ Ticket cancelado correctamente")
                    # Refrescar UI para quitar el panel del ticket
                    self.ticket_activo = None
                    self.page.controls.clear()
                    self._construir_ui()
                    self.page.update()
                else:
                    self._mostrar_error(f"Error: {resultado.get('error', 'No se pudo cancelar')}")
            else:
                snackbar.open = False
                self.page.update()
                self._mostrar_error("No hay conexión con el servidor")
        except Exception as e:
            snackbar.open = False
            self.page.update()
            self._mostrar_error(f"Error: {str(e)}")
    
    # =========================================================================
    # SISTEMA DE DIÁLOGOS MEJORADOS
    # =========================================================================
    
    def _crear_dialogo_profesional(self, tipo: str, titulo: str, mensaje: str, 
                                    boton_texto: str = "Entendido",
                                    boton_accion = None,
                                    mostrar_boton_secundario: bool = False,
                                    boton_secundario_texto: str = "Cancelar",
                                    boton_secundario_accion = None) -> AlertDialog:
        """Crea un diálogo profesional con animaciones y estilo moderno."""
        config = DIALOGO_TIPOS.get(tipo, DIALOGO_TIPOS["info"])
        
        # Icono animado grande
        icono_container = Container(
            content=Container(
                content=Icon(config["icono"], size=50, color=config["color"]),
                bgcolor=config["color_fondo"],
                border_radius=ft.BorderRadius.all(50),
                width=90,
                height=90,
                alignment=ft.Alignment(0, 0),
                animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
            ),
            alignment=ft.Alignment(0, 0),
        )
        
        # Contenido del diálogo
        contenido = Container(
            content=Column([
                icono_container,
                Container(height=15),
                Text(
                    titulo,
                    size=18,
                    weight=FontWeight.BOLD,
                    color=COLOR_TEXTO,
                    text_align=TextAlign.CENTER,
                ),
                Container(height=8),
                Container(
                    content=Text(
                        mensaje,
                        size=14,
                        color=COLOR_TEXTO_SEC,
                        text_align=TextAlign.CENTER,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10),
                ),
            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=0),
            width=300,
            padding=ft.Padding.only(top=20, bottom=10, left=10, right=10),
        )
        
        # Botones
        acciones = []
        
        # Botón secundario (si aplica)
        if mostrar_boton_secundario:
            acciones.append(
                Button(
                    content=Text(boton_secundario_texto, color=COLOR_TEXTO_SEC, weight=FontWeight.W_500),
                    bgcolor=colors.TRANSPARENT,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        overlay_color=COLOR_BORDE,
                    ),
                    height=45,
                    on_click=boton_secundario_accion or (lambda e: self._cerrar_dialogo()),
                )
            )
        
        # Botón principal
        acciones.append(
            Button(
                content=Row([
                    Icon(icons.CHECK_ROUNDED if tipo == "exito" else icons.ARROW_FORWARD_ROUNDED, 
                         color=colors.WHITE, size=18),
                    Text(boton_texto, color=colors.WHITE, weight=FontWeight.W_600),
                ], spacing=8, alignment=MainAxisAlignment.CENTER),
                bgcolor=config["color"],
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                    overlay_color=colors.WHITE24,
                ),
                width=140,
                height=45,
                on_click=boton_accion or (lambda e: self._cerrar_dialogo()),
            )
        )
        
        return AlertDialog(
            modal=True,
            content=contenido,
            actions=acciones,
            actions_alignment=MainAxisAlignment.CENTER,
            shape=ft.RoundedRectangleBorder(radius=20),
        )
    
    def _mostrar_mensaje_exito(self, mensaje: str, titulo: str = "¡Listo!"):
        """Muestra un diálogo de éxito profesional."""
        dialogo = self._crear_dialogo_profesional(
            tipo="exito",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Continuar"
        )
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _mostrar_advertencia(self, mensaje: str, titulo: str = "Atención"):
        """Muestra un diálogo de advertencia."""
        dialogo = self._crear_dialogo_profesional(
            tipo="advertencia",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Entendido"
        )
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _mostrar_info(self, mensaje: str, titulo: str = "Información"):
        """Muestra un diálogo informativo."""
        dialogo = self._crear_dialogo_profesional(
            tipo="info",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="OK"
        )
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    # =========================================================================
    # SISTEMA DE OVERLAY DE CARGA
    # =========================================================================
    
    def _mostrar_carga(self, mensaje: str = "Procesando..."):
        """Muestra un overlay de carga con animación."""
        if self._carga_activa:
            # Solo actualizar el mensaje si ya está activo
            if self.texto_carga:
                self.texto_carga.value = mensaje
                self.page.update()
            return
        
        self._carga_activa = True
        
        # Crear texto de carga
        self.texto_carga = Text(mensaje, size=14, color=COLOR_TEXTO, weight=FontWeight.W_500)
        
        # Crear overlay
        self.overlay_carga = Container(
            content=Container(
                content=Column([
                    # Animación de loading
                    Container(
                        content=ft.Stack([
                            # Círculo de fondo
                            Container(
                                width=70,
                                height=70,
                                border_radius=ft.BorderRadius.all(35),
                                bgcolor=COLOR_PRIMARIO + "15",
                            ),
                            # Progress ring
                            ProgressRing(
                                width=70,
                                height=70,
                                stroke_width=4,
                                color=COLOR_PRIMARIO,
                            ),
                            # Icono central
                            Container(
                                content=Icon(icons.SUPPORT_AGENT, size=28, color=COLOR_PRIMARIO),
                                width=70,
                                height=70,
                                alignment=ft.Alignment(0, 0),
                            ),
                        ]),
                        animate=ft.Animation(500, ft.AnimationCurve.EASE_IN_OUT),
                    ),
                    Container(height=20),
                    self.texto_carga,
                    Container(height=5),
                    Text("Por favor espera...", size=11, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                bgcolor=COLOR_TARJETA,
                border_radius=ft.BorderRadius.all(20),
                padding=ft.Padding.symmetric(horizontal=40, vertical=30),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=30,
                    color=colors.BLACK12,
                    offset=ft.Offset(0, 10),
                ),
            ),
            bgcolor=colors.BLACK54,
            expand=True,
            alignment=ft.Alignment(0, 0),
            animate_opacity=ft.Animation(200, ft.AnimationCurve.EASE_IN),
        )
        
        self.page.overlay.append(self.overlay_carga)
        self.page.update()
    
    def _ocultar_carga(self):
        """Oculta el overlay de carga."""
        if not self._carga_activa:
            return
        
        self._carga_activa = False
        
        if self.overlay_carga and self.overlay_carga in self.page.overlay:
            self.page.overlay.remove(self.overlay_carga)
            self.overlay_carga = None
            self.texto_carga = None
            self.page.update()

    def _construir_ui(self) -> None:
        """Construye la interfaz completa."""
        self.panel_estado = self._crear_panel_estado()
        
        # Sección 1: Información del equipo
        seccion_info = Container(
            content=Column([
                Container(
                    content=Row([
                        Container(
                            content=Text("1", size=12, weight=FontWeight.BOLD, color=colors.WHITE),
                            bgcolor=COLOR_PRIMARIO,
                            border_radius=ft.BorderRadius.all(15),
                            width=24,
                            height=24,
                            alignment=ft.Alignment(0, 0),
                        ),
                        Text("Tu Información", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                    ], spacing=10),
                    margin=ft.Padding.only(left=20, right=20, top=15, bottom=0),
                ),
            ]),
        )
        
        # Lista de elementos a mostrar
        elementos = [
            self._crear_header(),
            self.panel_estado,
            self._crear_panel_estado_enlace(),
        ]
        
        # Siempre mostrar sección "Mis Tickets"
        elementos.append(self._crear_seccion_mis_tickets())
        
        # Formulario envuelto en contenedor togglable (cargar_tickets puede ocultarlo)
        self._form_section = Column([], spacing=0)
        if not self.ticket_activo:
            self._form_section.controls = [
                seccion_info,
                self._crear_info_equipo(),
                self._crear_formulario(),
                self._crear_boton_envio(),
            ]
        elementos.append(Container(content=self._form_section))
        
        elementos.append(self._crear_footer())
        
        self.contenedor_principal = Column(elementos, spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
        self.page.add(self.contenedor_principal)
    
    def _validar_formulario(self) -> tuple[bool, str]:
        """Valida el formulario."""
        if not self.dropdown_categoria.value:
            return False, "Selecciona una categoría para continuar"
        
        descripcion = self.txt_descripcion.value.strip() if self.txt_descripcion.value else ""
        if not descripcion:
            return False, "Describe el problema que tienes"

        if InputValidator is not None:
            es_valido, error = InputValidator.validar_ticket({
                "descripcion": descripcion,
                "categoria": self.dropdown_categoria.value,
                "prioridad": self.dropdown_prioridad.value or "Media",
                "usuario_ad": self.usuario_ad,
                "hostname": self.hostname,
            })
            if not es_valido:
                return False, error or "Datos inválidos"
        
        return True, ""
    
    def _mostrar_dialogo_turno(self, ticket: dict) -> None:
        """Muestra el diálogo con información del turno - Versión mejorada."""
        turno = ticket.get("TURNO", "N/A")
        id_ticket = ticket.get("ID_TICKET", "N/A")
        categoria = ticket.get("CATEGORIA", "General")
        posicion = self.gestor.obtener_posicion_cola(id_ticket)
        
        if self.hay_disponible:
            mensaje = "¡Un técnico te atenderá en breve!"
            color_turno = COLOR_EXITO
            icono_estado = icons.ROCKET_LAUNCH_ROUNDED
            estado_texto = "Prioridad Alta"
        else:
            mensaje = "Tu ticket está en cola"
            color_turno = COLOR_ADVERTENCIA
            icono_estado = icons.HOURGLASS_TOP_ROUNDED
            estado_texto = f"Posición #{posicion}" if posicion else "En cola"
        
        # Obtener fecha/hora actual formateada
        fecha_hora_actual = datetime.now().strftime("%d/%m/%Y • %I:%M %p")
        
        dialogo = AlertDialog(
            modal=True,
            content=Container(
                content=Column([
                    # Icono de éxito animado
                    Container(
                        content=ft.Stack([
                            # Círculo de fondo con gradiente
                            Container(
                                width=100,
                                height=100,
                                border_radius=ft.BorderRadius.all(50),
                                gradient=ft.LinearGradient(
                                    begin=ft.Alignment(-1, -1),
                                    end=ft.Alignment(1, 1),
                                    colors=[COLOR_EXITO_CLARO, "#A7F3D0"],
                                ),
                            ),
                            # Icono check
                            Container(
                                content=Icon(icons.CHECK_ROUNDED, size=55, color=COLOR_EXITO),
                                width=100,
                                height=100,
                                alignment=ft.Alignment(0, 0),
                            ),
                        ]),
                        animate=ft.Animation(500, ft.AnimationCurve.BOUNCE_OUT),
                    ),
                    
                    Container(height=15),
                    
                    Text(
                        "¡Ticket Creado!",
                        size=22,
                        weight=FontWeight.BOLD,
                        color=COLOR_EXITO,
                    ),
                    
                    Container(height=5),
                    
                    Text(
                        mensaje,
                        size=13,
                        color=COLOR_TEXTO_SEC,
                    ),
                    
                    Container(height=20),
                    
                    # Tarjeta de turno
                    Container(
                        content=Column([
                            Text("TU NÚMERO DE TURNO", size=10, color=COLOR_TEXTO_SEC, weight=FontWeight.W_500),
                            Container(height=5),
                            Row([
                                Container(
                                    content=Text(turno, size=48, weight=FontWeight.BOLD, color=color_turno),
                                    animate=ft.Animation(300, ft.AnimationCurve.EASE_OUT),
                                ),
                            ], alignment=MainAxisAlignment.CENTER),
                            Container(height=5),
                            Container(
                                content=Row([
                                    Icon(icono_estado, size=14, color=colors.WHITE),
                                    Text(estado_texto, size=11, color=colors.WHITE, weight=FontWeight.W_500),
                                ], spacing=5, alignment=MainAxisAlignment.CENTER),
                                bgcolor=color_turno,
                                border_radius=ft.BorderRadius.all(15),
                                padding=ft.Padding.symmetric(horizontal=12, vertical=5),
                            ),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER),
                        bgcolor=COLOR_FONDO,
                        border_radius=ft.BorderRadius.all(15),
                        padding=ft.Padding.symmetric(horizontal=25, vertical=18),
                        border=ft.Border.all(1, COLOR_BORDE),
                    ),
                    
                    Container(height=15),
                    
                    # Info del ticket en grid
                    Container(
                        content=Row([
                            # Columna 1: N° Ticket
                            Container(
                                content=Column([
                                    Icon(icons.CONFIRMATION_NUMBER_ROUNDED, size=18, color=COLOR_PRIMARIO),
                                    Text("N° Ticket", size=9, color=COLOR_TEXTO_SEC),
                                    Text(f"#{id_ticket[:8]}..." if len(str(id_ticket)) > 8 else f"#{id_ticket}", 
                                         size=11, weight=FontWeight.W_600, color=COLOR_TEXTO),
                                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2),
                                expand=True,
                            ),
                            Container(width=1, height=45, bgcolor=COLOR_BORDE),
                            # Columna 2: Categoría
                            Container(
                                content=Column([
                                    Icon(ICONOS_CATEGORIA.get(categoria, icons.HELP_OUTLINE), size=18, color=COLOR_SECUNDARIO),
                                    Text("Categoría", size=9, color=COLOR_TEXTO_SEC),
                                    Text(categoria[:10] + "..." if len(categoria) > 10 else categoria, 
                                         size=11, weight=FontWeight.W_600, color=COLOR_TEXTO),
                                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2),
                                expand=True,
                            ),
                            Container(width=1, height=45, bgcolor=COLOR_BORDE),
                            # Columna 3: Hora
                            Container(
                                content=Column([
                                    Icon(icons.ACCESS_TIME_ROUNDED, size=18, color=COLOR_INFO),
                                    Text("Hora", size=9, color=COLOR_TEXTO_SEC),
                                    Text(datetime.now().strftime("%I:%M %p"), size=11, weight=FontWeight.W_600, color=COLOR_TEXTO),
                                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2),
                                expand=True,
                            ),
                        ]),
                        border=ft.Border.all(1, COLOR_BORDE),
                        border_radius=ft.BorderRadius.all(12),
                        padding=ft.Padding.symmetric(horizontal=8, vertical=12),
                    ),
                    
                    Container(height=10),
                    
                    # Fecha
                    Row([
                        Icon(icons.CALENDAR_TODAY_ROUNDED, size=12, color=COLOR_TEXTO_SEC),
                        Text(fecha_hora_actual, size=10, color=COLOR_TEXTO_SEC),
                    ], spacing=5, alignment=MainAxisAlignment.CENTER),
                    
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=0),
                width=320,
                padding=ft.Padding.only(top=25, bottom=15, left=15, right=15),
            ),
            actions=[
                Button(
                    content=Row([
                        Icon(icons.CHECK_CIRCLE_ROUNDED, color=colors.WHITE, size=18),
                        Text("Entendido", color=colors.WHITE, weight=FontWeight.W_600, size=14),
                    ], spacing=8, alignment=MainAxisAlignment.CENTER),
                    bgcolor=COLOR_EXITO,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=12),
                        overlay_color=colors.WHITE24,
                    ),
                    width=180,
                    height=48,
                    on_click=lambda e: self._cerrar_dialogo(),
                ),
            ],
            actions_alignment=MainAxisAlignment.CENTER,
            shape=ft.RoundedRectangleBorder(radius=25),
        )
        
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _mostrar_error(self, mensaje: str, titulo: str = "¡Ups! Algo salió mal") -> None:
        """Muestra un diálogo de error profesional con animaciones."""
        # Detectar tipo de error para personalizar
        if "conexión" in mensaje.lower() or "servidor" in mensaje.lower() or "red" in mensaje.lower():
            tipo = "conexion"
            titulo = "Error de Conexión"
        elif "formulario" in mensaje.lower() or "campo" in mensaje.lower() or "selecciona" in mensaje.lower():
            tipo = "advertencia"
            titulo = "Revisa el formulario"
        else:
            tipo = "error"
        
        dialogo = self._crear_dialogo_profesional(
            tipo=tipo,
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Entendido"
        )
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _mostrar_error_conexion(self, mensaje: str = "No se pudo conectar con el servidor") -> None:
        """Muestra un diálogo específico de error de conexión."""
        config = DIALOGO_TIPOS["conexion"]
        
        dialogo = AlertDialog(
            modal=True,
            content=Container(
                content=Column([
                    # Icono animado
                    Container(
                        content=Container(
                            content=ft.Stack([
                                Container(
                                    content=Icon(icons.CLOUD_OFF_ROUNDED, size=40, color=config["color"]),
                                    width=80,
                                    height=80,
                                    alignment=ft.Alignment(0, 0),
                                ),
                                Container(
                                    content=Icon(icons.WIFI_OFF_ROUNDED, size=20, color=COLOR_ERROR),
                                    width=80,
                                    height=80,
                                    alignment=ft.Alignment(0.5, 0.5),
                                ),
                            ]),
                            bgcolor=config["color_fondo"],
                            border_radius=ft.BorderRadius.all(40),
                            width=80,
                            height=80,
                        ),
                    ),
                    Container(height=15),
                    Text("Sin Conexión", size=18, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Container(height=8),
                    Text(
                        mensaje,
                        size=13,
                        color=COLOR_TEXTO_SEC,
                        text_align=TextAlign.CENTER,
                    ),
                    Container(height=15),
                    # Sugerencias
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.LIGHTBULB_OUTLINE, size=14, color=COLOR_ADVERTENCIA),
                                Text("Sugerencias:", size=12, weight=FontWeight.W_600, color=COLOR_TEXTO),
                            ], spacing=5),
                            Container(height=5),
                            Text("• Verifica tu conexión de red", size=11, color=COLOR_TEXTO_SEC),
                            Text("• Revisa la configuración del servidor", size=11, color=COLOR_TEXTO_SEC),
                            Text("• Contacta al administrador de IT", size=11, color=COLOR_TEXTO_SEC),
                        ]),
                        bgcolor=COLOR_ADVERTENCIA_CLARO,
                        border_radius=ft.BorderRadius.all(10),
                        padding=ft.Padding.all(12),
                    ),
                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                width=300,
                padding=ft.Padding.all(20),
            ),
            actions=[
                Button(
                    content=Row([
                        Icon(icons.SETTINGS, color=COLOR_PRIMARIO, size=16),
                        Text("Configurar", color=COLOR_PRIMARIO, weight=FontWeight.W_500),
                    ], spacing=5, alignment=MainAxisAlignment.CENTER),
                    bgcolor=colors.TRANSPARENT,
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        side=ft.BorderSide(1, COLOR_PRIMARIO),
                    ),
                    height=42,
                    on_click=lambda e: self._ir_a_configuracion_desde_error(),
                ),
                Button(
                    content=Row([
                        Icon(icons.REFRESH, color=colors.WHITE, size=16),
                        Text("Reintentar", color=colors.WHITE, weight=FontWeight.W_500),
                    ], spacing=5, alignment=MainAxisAlignment.CENTER),
                    bgcolor=COLOR_PRIMARIO,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    height=42,
                    on_click=lambda e: self._reintentar_conexion_desde_error(),
                ),
            ],
            actions_alignment=MainAxisAlignment.CENTER,
            shape=ft.RoundedRectangleBorder(radius=20),
        )
        
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _ir_a_configuracion_desde_error(self):
        """Cierra el diálogo y abre configuración."""
        self._cerrar_dialogo()
        self._abrir_configuracion()
    
    def _reintentar_conexion_desde_error(self):
        """Cierra el diálogo y reintenta la conexión."""
        self._cerrar_dialogo()
        self._mostrar_carga("Reintentando conexión...")
        
        def reintentar():
            import time
            time.sleep(0.5)
            self._ocultar_carga()
            self._inicializar_servidor()
            self._actualizar_estado_enlace_ui()
        
        import threading
        threading.Thread(target=reintentar, daemon=True).start()
    
    def _cerrar_dialogo(self) -> None:
        """Cierra el diálogo activo."""
        if self.page.overlay:
            self.page.overlay[-1].open = False
            self.page.update()
    
    async def _enviar_ticket_async(self) -> None:
        """Proceso asíncrono de envío con animaciones mejoradas."""
        try:
            # Mostrar overlay de carga
            self._mostrar_carga("Creando tu ticket...")
            
            await asyncio.sleep(0.3)  # Pequeña pausa para mostrar animación
            
            # Actualizar mensaje de carga
            if self.texto_carga:
                self.texto_carga.value = "Verificando disponibilidad..."
                self.page.update()
            
            # Actualizar estado de técnicos (del servidor si está conectado)
            if self.servidor_conectado and self.servidor_ip:
                try:
                    estado_srv = obtener_estado_servidor(self.servidor_ip, self.servidor_puerto)
                    self.hay_disponible = estado_srv.get("hay_disponible", False)
                    self.tecnicos_disponibles = estado_srv.get("tecnicos_disponibles", [])
                except Exception:
                    self.hay_disponible = False
                    self.tecnicos_disponibles = []
            else:
                self.tecnicos_disponibles = self.gestor.obtener_tecnicos_disponibles()
                self.hay_disponible = self.gestor.hay_tecnico_disponible()
            
            await asyncio.sleep(0.3)
            
            # Datos del ticket
            datos_ticket = {
                "usuario_ad": self.usuario_ad,
                "hostname": self.hostname,
                "mac_address": self.mac_address,
                "categoria": self.dropdown_categoria.value,
                "descripcion": self.txt_descripcion.value.strip(),
                "prioridad": self.dropdown_prioridad.value or "Media"
            }
            
            ticket = None
            
            # Actualizar mensaje
            if self.texto_carga:
                self.texto_carga.value = "Enviando al servidor..."
                self.page.update()
            
            # DEBUG: Mostrar estado de conexión
            print(f"[CLIENTE] === DEBUG ENVÍO TICKET ===")
            print(f"[CLIENTE] servidor_conectado: {self.servidor_conectado}")
            print(f"[CLIENTE] servidor_ip: {self.servidor_ip}")
            print(f"[CLIENTE] enlazado: {self.enlazado}")
            
            # Intentar enviar por red si está enlazado
            if self.servidor_conectado and self.servidor_ip and self.enlazado:
                try:
                    print(f"[CLIENTE] Enviando ticket a {self.servidor_ip}:{self.servidor_puerto}...")
                    resultado = enviar_ticket_a_servidor(
                        self.servidor_ip,
                        self.servidor_puerto,
                        datos_ticket
                    )
                    print(f"[CLIENTE] Resultado del servidor: {resultado}")
                    if resultado and resultado.get("success"):
                        ticket = resultado.get("ticket", {})
                        print(f"[CLIENTE] ✅ Ticket enviado por red: {ticket.get('ID_TICKET', 'N/A')}")
                    else:
                        print(f"[CLIENTE] ❌ Error del servidor: {resultado}")
                except Exception as e:
                    print(f"[CLIENTE] ❌ Error de red, guardando local: {e}")
                    import traceback
                    traceback.print_exc()
                    if self.texto_carga:
                        self.texto_carga.value = "Guardando localmente..."
                        self.page.update()
                    ticket = self.gestor.crear_ticket(**datos_ticket)
                    print(f"[CLIENTE] Ticket guardado localmente: {ticket.get('ID_TICKET', 'N/A')}")
            else:
                print(f"[CLIENTE] ⚠️ No conectado/enlazado, guardando local")
                if self.texto_carga:
                    self.texto_carga.value = "Guardando ticket..."
                    self.page.update()
                ticket = self.gestor.crear_ticket(**datos_ticket)
                print(f"[CLIENTE] Ticket creado localmente (sin servidor): {ticket.get('ID_TICKET', 'N/A')}")
            
            # Mensaje final
            if self.texto_carga:
                self.texto_carga.value = "¡Ticket creado!"
                self.page.update()
            
            await asyncio.sleep(0.5)
            
            # Ocultar overlay y restaurar botón
            self._ocultar_carga()
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self._enviando = False
            self.page.update()
            
            # Guardar ticket activo en memoria
            self.ticket_activo = ticket
            
            # Mostrar diálogo de turno
            self._mostrar_dialogo_turno(ticket)
            
            # Reconstruir UI para mostrar el ticket activo
            self.page.controls.clear()
            self._construir_ui()
            self.page.update()
            
        except PermissionError:
            self._ocultar_carga()
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self._enviando = False
            self.page.update()
            self._mostrar_error(
                "El archivo de datos está siendo usado por otro programa. "
                "Ciérralo e intenta nuevamente.",
                titulo="Archivo en uso"
            )
            
        except Exception as e:
            self._ocultar_carga()
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self._enviando = False
            self.page.update()
            self._mostrar_error(f"Ocurrió un error inesperado: {str(e)}")
    
    def _enviar_ticket(self, e) -> None:
        """Manejador del botón enviar."""
        # Evitar doble envío
        if self._enviando:
            return
        
        # Verificar estado de enlace
        if not self.enlazado:
            if self.estado_enlace == "pendiente":
                self._mostrar_advertencia(
                    "Tu solicitud de enlace está pendiente de aprobación. "
                    "Un administrador debe aprobar tu equipo antes de poder enviar tickets.",
                    titulo="Esperando aprobación"
                )
            elif self.estado_enlace == "rechazado":
                self._mostrar_error(
                    "Tu solicitud de enlace fue rechazada por el administrador. "
                    "Contacta al departamento de IT para más información.",
                    titulo="Acceso denegado"
                )
            elif self.estado_enlace == "revocado":
                self._mostrar_error(
                    "Tu acceso ha sido revocado por el administrador. "
                    "Contacta al departamento de IT si necesitas recuperar el acceso.",
                    titulo="Acceso revocado"
                )
            else:
                self._mostrar_error_conexion(
                    "Debes conectarte al servidor y enlazar tu equipo antes de crear tickets."
                )
            return
        
        es_valido, error = self._validar_formulario()
        
        if not es_valido:
            self._mostrar_advertencia(error, titulo="Revisa el formulario")
            return
        
        # Marcar como enviando
        self._enviando = True
        self.progress_ring.visible = True
        self.btn_enviar.disabled = True
        self.page.update()
        
        self.page.run_task(self._enviar_ticket_async)
    
    def _limpiar_formulario(self) -> None:
        """Limpia el formulario."""
        self.dropdown_categoria.value = None
        self.dropdown_prioridad.value = "Media"
        self.txt_descripcion.value = ""
        self.page.update()


def _verificar_configuracion_inicial():
    """Verifica y crea archivos de configuración si son necesarios."""
    from pathlib import Path
    
    base_path = PROJECT_ROOT
    config_file = RUNTIME_DIR / "servidor_config.txt"
    
    print("[AUTO-INIT] 🔧 Verificando configuración...")
    
    # Crear archivo de configuración vacío si no existe
    if not config_file.exists():
        try:
            config_file.write_text("")
            print("[AUTO-INIT] ✅ Archivo de configuración creado")
        except Exception as e:
            print(f"[AUTO-INIT] ⚠️  No se pudo crear configuración: {e}")
    else:
        print("[AUTO-INIT] ✓ Configuración OK")
    
    print("[AUTO-INIT] ✅ Verificación completada")


def main(page: Page):
    """Punto de entrada de la aplicación."""
    def _obtener_version_app() -> str:
        try:
            version_path = PROJECT_ROOT / "version.txt"
            return version_path.read_text(encoding="utf-8").strip() or "0.0.0"
        except Exception:
            return "0.0.0"

    def _mostrar_bloqueo_en_pantalla(result) -> None:
        page.clean()
        page.add(
            Container(
                expand=True,
                alignment=ft.Alignment(0, 0),
                content=Column(
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=10,
                    controls=[
                        Icon(icons.LOCK_OUTLINE, size=56, color=COLOR_ERROR),
                        Text("Kubito bloqueado por licencia", size=22, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(result.message or "No se pudo validar licencia", color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER),
                        Text(f"Código: {result.reason}", color=COLOR_TEXTO_SEC),
                    ],
                ),
            )
        )
        page.update()

    def _arrancar_app() -> None:
        AppEmisora(page)

    def _mostrar_modal_activacion() -> None:
        key_input = TextField(
            label="Key gratis de 7 días",
            value=TRIAL_LICENSE_KEY,
            hint_text="KUBO-TRIAL-7D-GRATIS",
            password=False,
            can_reveal_password=True,
            width=420,
        )
        estado = Text(f"La key gratis ya está lista: {TRIAL_LICENSE_KEY}", size=12, color=COLOR_TEXTO_SEC)

        def activar(_):
            key = (key_input.value or "").strip()
            if not key:
                estado.value = "Debes ingresar una key válida."
                estado.color = COLOR_ERROR
                page.update()
                return

            if guardar_activation_key is not None:
                guardar_activation_key(key)

            nuevo_resultado = validar_licencia_inicio("emisora", _obtener_version_app())
            if nuevo_resultado.allowed:
                dlg.open = False
                page.update()
                print(f"[LICENCIA] {nuevo_resultado.message}")
                return

            estado.value = nuevo_resultado.message or "No se pudo activar la licencia."
            estado.color = COLOR_ERROR
            page.update()

        async def salir(_):
            await page.window.close()

        dlg = AlertDialog(
            modal=True,
            title=Text("Activar Kubito", weight=FontWeight.BOLD),
            content=Column(
                tight=True,
                spacing=10,
                controls=[
                    Text("Este equipo aún no está activado."),
                    key_input,
                    estado,
                ],
            ),
            actions=[
                ft.TextButton("Salir", on_click=salir),
                ft.FilledButton("Activar", on_click=activar),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        page.show_dialog(dlg)

    def _validar_licencia_inicial() -> Any:
        if validar_licencia_inicio is None:
            return None

        resultado = validar_licencia_inicio("emisora", _obtener_version_app())
        if resultado.allowed:
            print(f"[LICENCIA] {resultado.message}")
        elif resultado.reason != "activation_required":
            if resultado.reason == "product_mismatch" and limpiar_activation_key is not None:
                limpiar_activation_key()
                _mostrar_modal_activacion()
                return resultado
            if mostrar_banner_bloqueo is not None:
                mostrar_banner_bloqueo("emisora", resultado)
            print(f"[LICENCIA] Acceso denegado: {resultado.message}")
            _mostrar_bloqueo_en_pantalla(resultado)
        return resultado

    # Verificar configuración al inicio
    try:
        _verificar_configuracion_inicial()
    except Exception as e:
        print(f"[ERROR] Error en verificación inicial: {e}")

    _arrancar_app()

    resultado_licencia = _validar_licencia_inicial()
    if resultado_licencia is not None and not resultado_licencia.allowed:
        if resultado_licencia.reason == "activation_required":
            _mostrar_modal_activacion()


if __name__ == "__main__":
    # asegurarse de que el directorio de iconos esté en assets
    assets = str(PROJECT_ROOT)
    ft.run(main, assets_dir=assets)
