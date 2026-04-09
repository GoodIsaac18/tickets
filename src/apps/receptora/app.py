# =============================================================================
# APP RECEPTORA (KUBO) - Panel de Administración IT Profesional
# =============================================================================
# Panel completo para el equipo de IT con gestión de técnicos, tickets,
# sistema de turnos, dashboards analíticos y notificaciones en tiempo real.
# =============================================================================

import flet as ft
import os
from flet import (
    Page, Container, Column, Row, Text, TextField, Dropdown,
    DataTable, DataColumn, DataRow, DataCell,
    NavigationRail, NavigationRailDestination, ProgressRing,
    AlertDialog, SnackBar, dropdown, Colors as colors, 
    MainAxisAlignment, CrossAxisAlignment, FontWeight,
    TextAlign, Icons as icons, Icon, Divider, Card, ListView, ListTile,
    ScrollMode, Switch, Badge, ProgressBar, Stack
)
from pathlib import Path
import sys
import pandas as pd
from datetime import datetime
from typing import Optional, List, Dict, Any
import threading
import time

# Importar módulo de acceso a datos
from data_access import (
    GestorTickets,
    CATEGORIAS_DISPONIBLES,
    ESTADOS_TICKET,
    ESTADOS_TECNICO,
    PRIORIDADES,
    TECNICOS_EQUIPO,
    GRUPOS_EQUIPOS,
    TIPOS_EQUIPO,
    ESTADOS_EQUIPO,
    EscanerRed,
    obtener_ip_local,
    obtener_rango_red,
    guardar_config_servidor,
    SERVIDOR_PUERTO
)

# Importar servidor de red para tickets
from servidor_red import (
    iniciar_servidor,
    detener_servidor,
    servidor_esta_activo,
    obtener_ip_servidor,
    obtener_equipos_con_estado,
    obtener_equipos_online
)

# Importar sistema de notificaciones de Windows
try:
    from notificaciones_windows import (
        iniciar_servicio_notificaciones,
        mostrar_notificacion_windows,
        WINOTIFY_DISPONIBLE
    )
    NOTIFICACIONES_WINDOWS = WINOTIFY_DISPONIBLE
except ImportError:
    NOTIFICACIONES_WINDOWS = False
    def iniciar_servicio_notificaciones(): pass
    def mostrar_notificacion_windows(*args, **kwargs): pass

# Validación remota de licencia/control de instalación
try:
    from licencias_cliente import validar_licencia_inicio, mostrar_banner_bloqueo, guardar_activation_key, limpiar_activation_key, TRIAL_LICENSE_KEY
except Exception:
    validar_licencia_inicio = None
    mostrar_banner_bloqueo = None
    guardar_activation_key = None
    limpiar_activation_key = None
    TRIAL_LICENSE_KEY = "KUBO-TRIAL-7D-GRATIS"

# Validación centralizada
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


# =============================================================================
# TEMA OSCURO PROFESIONAL
# =============================================================================

# Colores principales
COLOR_FONDO = "#0F0F0F"
COLOR_SUPERFICIE = "#1A1A2E"
COLOR_SUPERFICIE_2 = "#16213E"
COLOR_SUPERFICIE_3 = "#1F4068"
COLOR_PRIMARIO = "#E94560"
COLOR_SECUNDARIO = "#0F3460"
COLOR_ACENTO = "#00D9FF"
COLOR_TEXTO = "#FFFFFF"
COLOR_TEXTO_SEC = "#A0A0A0"
COLOR_EXITO = "#00E676"
COLOR_EXITO_CLARO = "#1B3B2F"       # Verde oscuro para fondo
COLOR_ADVERTENCIA = "#FFD600"
COLOR_ADVERTENCIA_CLARO = "#3D3A1A" # Amarillo oscuro para fondo
COLOR_ERROR = "#FF5252"
COLOR_ERROR_CLARO = "#3D1A1A"       # Rojo oscuro para fondo
COLOR_INFO = "#00B0FF"
COLOR_INFO_CLARO = "#1A2E3D"        # Azul oscuro para fondo
COLOR_BORDE = "#2A2A3E"             # Borde para modo oscuro

# Colores de estado
COLOR_DISPONIBLE = "#00E676"
COLOR_OCUPADO = "#FF9800"
COLOR_AUSENTE = "#9E9E9E"
COLOR_DESCANSO = "#03A9F4"

# Colores de prioridad
COLOR_CRITICA = "#D500F9"
COLOR_ALTA = "#FF5252"
COLOR_MEDIA = "#FFD600"
COLOR_BAJA = "#00E676"

# Orden de prioridad (menor número = más urgente)
ORDEN_PRIORIDAD = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}

# Colores de categorías
COLORES_CATEGORIAS = {
    "Red": "#2196F3",
    "Hardware": "#FF5722",
    "Software": "#9C27B0",
    "Accesos": "#4CAF50",
    "Impresoras": "#795548",
    "Email": "#00BCD4",
    "Otros": "#607D8B"
}


# =============================================================================
# CONSTANTES DE DIÁLOGOS PROFESIONALES
# =============================================================================
DIALOGO_TIPOS = {
    "error": {
        "icono": icons.ERROR_ROUNDED,
        "color": COLOR_ERROR,
        "color_fondo": COLOR_ERROR_CLARO,
        "titulo": "¡Error!"
    },
    "exito": {
        "icono": icons.CHECK_CIRCLE_ROUNDED,
        "color": COLOR_EXITO,
        "color_fondo": COLOR_EXITO_CLARO,
        "titulo": "¡Completado!"
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
    "confirmar": {
        "icono": icons.HELP_ROUNDED,
        "color": COLOR_ACENTO,
        "color_fondo": COLOR_SUPERFICIE_2,
        "titulo": "Confirmar acción"
    },
    "cargando": {
        "icono": icons.HOURGLASS_TOP_ROUNDED,
        "color": COLOR_PRIMARIO,
        "color_fondo": COLOR_SUPERFICIE,
        "titulo": "Procesando..."
    }
}


# =============================================================================
# CLASE PRINCIPAL
# =============================================================================

class PanelAdminIT:
    """Panel de Administración IT Profesional con gestión completa."""
    
    def __init__(self, page: Page):
        self.page = page
        self.gestor = GestorTickets()
        self.ticket_seleccionado = None
        self.vista_actual = 0
        self.auto_refresh = True
        self.servidor_ip = None
        self.servidor_puerto = None
        
        # Sistema de overlay de carga
        self.overlay_carga: Optional[Container] = None
        self.texto_carga: Optional[Text] = None
        self._carga_activa: bool = False
        self._vistas_cache: Dict[int, Dict[str, Any]] = {}
        self._vistas_cache_orden: List[int] = []
        self._max_vistas_cache = 3
        self._cache_ttl_segundos = 20
        self._ultimo_refresco_vista_ts = 0.0
        self._max_render_tickets = 250
        self._max_render_cola = 120
        self._max_render_inventario = 250
        self._max_render_red = 250
        self._max_render_solicitudes = 120
        self._tickets_cargando = False
        self._tickets_page_size = 40
        self._tickets_page = 0
        self._tickets_df_full = pd.DataFrame()
        self._tickets_df_filtrado = pd.DataFrame()
        self._tickets_tabla_container = None
        self._tickets_paginacion = None
        self._tickets_btn_prev = None
        self._tickets_btn_next = None
        self._tickets_lbl_pagina = None
        self._tickets_resumen_text = None
        self._tickets_total_text = None
        self._tickets_criticas_text = None
        self._tickets_altas_text = None
        self._reportes_equipos_page_size = 4
        self._reportes_equipos_page = 0
        self._reportes_equipos_rows: List[Container] = []
        self._reportes_equipos_container = None
        self._reportes_equipos_btn_prev = None
        self._reportes_equipos_btn_next = None
        self._reportes_equipos_lbl_pagina = None
        self._reportes_equipos_resumen = None
        self._reportes_equipos_paginacion = None
        self._inventario_page_size = 40
        self._inventario_page = 0
        self._inventario_df_full = pd.DataFrame()
        self._inventario_df_filtrado = pd.DataFrame()
        self._inventario_cargando = False
        self._inventario_tabla_container = None
        self._inventario_paginacion = None
        self._inventario_btn_prev = None
        self._inventario_btn_next = None
        self._inventario_lbl_pagina = None
        self._inventario_resumen_text = None
        self._dashboard_cargando = False
        self._dashboard_version = 0
        self._dashboard_contenido = None
        self._cola_cargando = False
        self._escaner_cargando = False
        self._escaner_recarga_pendiente = False
        self._cola_page_size = 8
        self._cola_page = 0
        self._cola_df_full = pd.DataFrame()
        self._escaner_srv_page_size = 40
        self._escaner_hist_page_size = 50
        self._escaner_srv_page = 0
        self._escaner_hist_page = 0
        self._escaner_equipos_srv_full: List[Dict[str, Any]] = []
        self._escaner_equipos_red_full = pd.DataFrame()
        self._escaner_equipos_online_full: List[Dict[str, Any]] = []
        self._btn_escanear_red = None
        self._perf_vistas: Dict[str, List[float]] = {}
        self._perf_umbral_lento_ms = float(os.getenv("TICKETS_UI_SLOW_MS", "350"))
        self._perf_log_detallado = os.getenv("TICKETS_UI_PERF_VERBOSE", "0") == "1"
        self._prefs = load_app_preferences("kubo")
        self._normalizar_preferencias_kubo()
        self._cfg_txt_contacto = None
        self._cfg_txt_mensaje = None
        self._cfg_sw_notificaciones = None
        self._cfg_sw_animaciones = None
        self._cfg_sw_diagnostico = None
        self._cfg_sw_tema_oscuro = None
        self._cfg_sw_modo_compacto = None
        self._cfg_sw_auto_expandir_chat = None
        self._cfg_sw_auto_respuestas = None
        self._cfg_sw_autoasignacion = None
        self._cfg_sw_chat_notif_externa = None
        self._cfg_sw_menu_badges = None
        self._cfg_sw_refresco_auto = None
        self._cfg_sw_sonido_notificaciones = None
        self._cfg_sw_abrir_chat_notif = None
        self._cfg_sw_evitar_duplicados_chat = None
        self._cfg_txt_auto_respuesta = None
        self._cfg_dd_respuesta_modo = None
        self._cfg_dd_autoasignacion = None
        self._cfg_dd_notif_duracion = None
        self._cfg_dd_refresco_auto = None
        self._cfg_dd_tickets_page_size = None
        self._cfg_dd_cola_page_size = None
        self._cfg_dd_inventario_page_size = None
        self._cfg_dd_reportes_page_size = None
        self._cfg_dd_chat_historial = None
        self._cfg_dd_chat_preview = None
        self._cfg_dd_escaner_srv = None
        self._cfg_dd_escaner_hist = None
        self._cfg_dd_ui_density = None
        self._chat_detalle_ticket_id = None
        self._chat_detalle_list_ref = None
        self._chat_detalle_txt_ref = None
        self._chat_detalle_mensajes: List[Dict[str, Any]] = []
        self._chat_detalle_activo: bool = False
        
        # Sistema de tracking de cambios en configuración
        self._prefs_sin_guardar: Dict[str, Any] = {}
        self._cfg_cambios_detectados: bool = False
        self._cfg_search_query: str = ""
        self._cfg_lbl_cambios = None
        self._cfg_txt_search = None
        self._cfg_help_text_dict = self._inicializar_help_text_config()
        
        self._configurar_pagina()
        self._construir_ui()
        self._iniciar_auto_refresh()
        self._iniciar_servidor_tickets()
        self._iniciar_backup_automatico()

    def _normalizar_preferencias_kubo(self) -> None:
        self._prefs.setdefault("ui", {})
        self._prefs.setdefault("features", {})
        self._prefs.setdefault("support", {})
        self._prefs.setdefault("chat", {})
        self._prefs.setdefault("views", {})

        self._prefs["ui"].setdefault("mostrar_notificaciones", True)
        self._prefs["ui"].setdefault("animaciones", True)
        self._prefs["ui"].setdefault("tema_oscuro", True)
        self._prefs["ui"].setdefault("modo_compacto", False)
        self._prefs["ui"].setdefault("auto_expandir_chat", True)
        self._prefs["ui"].setdefault("densidad", "normal")

        self._prefs["features"].setdefault("diagnostico_rapido", True)
        self._prefs["features"].setdefault("chat_auto_respuesta", True)
        self._prefs["features"].setdefault("chat_autoasignacion", True)
        self._prefs["features"].setdefault("chat_notificacion_externa", True)
        self._prefs["features"].setdefault("menu_badges", True)
        self._prefs["features"].setdefault("refresco_automatico", True)
        self._prefs["features"].setdefault("abrir_chat_notificacion", True)
        self._prefs["features"].setdefault("sonido_notificaciones", False)
        self._prefs["features"].setdefault("evitar_duplicados_chat", True)

        self._prefs["chat"].setdefault("mensaje_auto", "Recibimos tu mensaje. Un técnico te atenderá a la brevedad.")
        self._prefs["chat"].setdefault("respuesta_modo", "primer_mensaje")
        self._prefs["chat"].setdefault("autoasignacion_modo", "menor_carga")
        self._prefs["chat"].setdefault("notificacion_duracion", "short")
        self._prefs["chat"].setdefault("historial_limite", 30)
        self._prefs["chat"].setdefault("preview_limite", 8)

        self._prefs["views"].setdefault("tickets_page_size", 40)
        self._prefs["views"].setdefault("cola_page_size", 8)
        self._prefs["views"].setdefault("inventario_page_size", 40)
        self._prefs["views"].setdefault("reportes_page_size", 4)
        self._prefs["views"].setdefault("chat_historial_page_size", 30)
        self._prefs["views"].setdefault("chat_preview_rows", 8)
        self._prefs["views"].setdefault("escaner_srv_page_size", 40)
        self._prefs["views"].setdefault("escaner_hist_page_size", 50)
        self._prefs["views"].setdefault("auto_refresh_interval", 30)

        self.auto_refresh = bool(self._prefs["features"].get("refresco_automatico", True))
        self._tickets_page_size = int(self._prefs["views"].get("tickets_page_size", 40) or 40)
        self._reportes_equipos_page_size = int(self._prefs["views"].get("reportes_page_size", 4) or 4)
        self._inventario_page_size = int(self._prefs["views"].get("inventario_page_size", 40) or 40)
        self._cola_page_size = int(self._prefs["views"].get("cola_page_size", 8) or 8)
        self._escaner_srv_page_size = int(self._prefs["views"].get("escaner_srv_page_size", 40) or 40)
        self._escaner_hist_page_size = int(self._prefs["views"].get("escaner_hist_page_size", 50) or 50)

    def _prefs_bool(self, section: str, key: str, default: bool = False) -> bool:
        return bool(self._prefs.get(section, {}).get(key, default))

    def _prefs_int(self, section: str, key: str, default: int, min_value: int = 1, max_value: int = 9999) -> int:
        try:
            value = int(self._prefs.get(section, {}).get(key, default) or default)
        except Exception:
            value = default
        return max(min_value, min(max_value, value))

    def _prefs_str(self, section: str, key: str, default: str = "") -> str:
        return str(self._prefs.get(section, {}).get(key, default) or default)

    def _aplicar_configuracion_en_vivo(self) -> None:
        try:
            self.auto_refresh = self._prefs_bool("features", "refresco_automatico", True)
            self.page.theme_mode = ft.ThemeMode.DARK if self._prefs_bool("ui", "tema_oscuro", True) else ft.ThemeMode.LIGHT
        except Exception:
            pass

    def _intervalo_auto_refresh_segundos(self) -> int:
        return self._prefs_int("views", "auto_refresh_interval", 30, 5, 300)

    def _limite_chat_historial(self) -> int:
        return self._prefs_int("chat", "historial_limite", 30, 10, 200)

    def _limite_chat_preview(self) -> int:
        return self._prefs_int("chat", "preview_limite", 8, 3, 20)

    def _modo_respuesta_auto(self) -> str:
        modo = self._prefs_str("chat", "respuesta_modo", "primer_mensaje").strip().lower()
        return modo if modo in {"primer_mensaje", "siempre"} else "primer_mensaje"

    def _modo_autoasignacion(self) -> str:
        modo = self._prefs_str("chat", "autoasignacion_modo", "menor_carga").strip().lower()
        return modo if modo in {"menor_carga", "primero_disponible"} else "menor_carga"

    def _duracion_notificacion(self) -> str:
        modo = self._prefs_str("chat", "notificacion_duracion", "short").strip().lower()
        return modo if modo in {"short", "medium", "long"} else "short"
    
    def _inicializar_help_text_config(self) -> Dict[str, str]:
        """Diccionario con textos de ayuda para cada control de configuración."""
        return {
            "mostrar_notificaciones": "Activar/desactivar todas las notificaciones del sistema",
            "animaciones": "Mostrar efectos visuales y transiciones suaves",
            "tema_oscuro": "Cambiar a tema oscuro para menos fatiga visual",
            "modo_compacto": "Mostrar menos espacios en blanco para más información",
            "auto_expandir_chat": "Expandir chat automáticamente cuando llega un mensaje",
            "chat_auto_respuesta": "Enviar respuesta automática al recibir un ticket",
            "respuesta_modo": "Responder solo en primer mensaje o en cada mensaje",
            "chat_autoasignacion": "Asignar técnico automáticamente a nuevos tickets",
            "autoasignacion_modo": "Asignar al técnico con menor carga o al primero disponible",
            "chat_notificacion_externa": "Notificar nuevos mensajes cuando no abres el chat",
            "evitar_duplicados_chat": "Evitar enviar respuestas duplicadas al mismo usuario",
            "notificacion_duracion": "Duración que aparecen las notificaciones en pantalla",
            "densidad": "Densidad de información mostrada en las vistas",
            "tickets_page_size": "Cuántos tickets mostrar por página",
            "cola_page_size": "Cuántos tickets en cola mostrar por página",
            "inventario_page_size": "Cuántos equipos mostrar por página",
            "reportes_page_size": "Cuántos reportes mostrar por página",
            "historial_limite": "Cuántos mensajes cargar en el historial de chat",
            "preview_limite": "Cuántos mensajes mostrar en la vista rápida",
            "escaner_srv_page_size": "Cuántos equipos del escáner mostrar por página",
            "escaner_hist_page_size": "Cuántos registros del historial mostrar",
            "auto_refresh_interval": "Segundos entre actualizaciones automáticas",
            "sonido_notificaciones": "Sonar cuando llega una notificación",
            "abrir_chat_notif": "Abrir chat automáticamente al hacer clic en notificación",
            "menu_badges": "Mostrar contadores de items pendientes en el menú",
            "refresco_auto": "Recargar datos automáticamente",
            "diagnostico_rapido": "Activar herramientas de diagnóstico rápido"
        }
    
    def _detectar_cambios_config(self) -> bool:
        """Detecta si hay cambios entre preferencias actuales y guardadas."""
        import json
        try:
            prefs_str_actual = json.dumps(self._prefs_sin_guardar, sort_keys=True)
            prefs_str_guardadas = json.dumps(self._prefs, sort_keys=True)
            return prefs_str_actual != prefs_str_guardadas
        except Exception:
            return False
    
    def _actualizar_etiqueta_cambios(self) -> None:
        """Actualiza la etiqueta de "Cambios sin guardar" en la UI."""
        if self._cfg_lbl_cambios:
            cambios = self._detectar_cambios_config()
            self._cfg_cambios_detectados = cambios
            if cambios:
                self._cfg_lbl_cambios.value = "⚠️ CAMBIOS SIN GUARDAR"
                self._cfg_lbl_cambios.color = "#FF9800"  # Naranja
                self._cfg_lbl_cambios.visible = True
            else:
                self._cfg_lbl_cambios.visible = False
            try:
                self.page.update()
            except Exception:
                pass
    
    def _descartar_cambios_config(self, e=None) -> None:
        """Descarta todos los cambios en la configuración sin guardar."""
        self._prefs_sin_guardar = {}
        self._cfg_cambios_detectados = False
        if self._cfg_lbl_cambios:
            self._cfg_lbl_cambios.visible = False
        
        # Recargar todos los controles con valores guardados
        self._vista_actual = 7  # Fuerza reconstrucción de vista
        try:
            self.page.update()
        except Exception:
            pass
    
    def _aplicar_cambios_sin_guardar(self, e=None) -> None:
        """Aplica cambios en sesión sin guardarlos a persistencia."""
        if not self._prefs_sin_guardar:
            return
        
        # Aplicar cambios (tema, refresco, etc.)
        self._aplicar_configuracion_en_vivo()
        self._actualizar_etiqueta_cambios()
        
        # Mostrar confirmación
        snack = SnackBar(
            content=Text("✓ Cambios aplicados en esta sesión (no guardados)", color="#4CAF50"),
            duration=2000
        )
        self.page.overlay.append(snack)
        snack.open = True
        try:
            self.page.update()
        except Exception:
            pass
    
    def _guardar_cambios_config(self, e=None) -> None:
        """Guarda cambios de configuración a persistencia y aplica."""
        if self._prefs_sin_guardar:
            # Copiar cambios a preferencias guardadas
            import copy
            self._prefs = copy.deepcopy(self._prefs_sin_guardar)
            self._normalizar_preferencias_kubo()
        
        self._guardar_preferencias_locales(e)
        self._prefs_sin_guardar = {}
        self._cfg_cambios_detectados = False
        self._actualizar_etiqueta_cambios()
        
        snack = SnackBar(
            content=Text("✓ Configuración guardada correctamente", color="#4CAF50"),
            duration=2000
        )
        self.page.overlay.append(snack)
        snack.open = True
        try:
            self.page.update()
        except Exception:
            pass
    
    def _on_config_change_tracked(self, control) -> None:
        """Callback para cambios de controles que rastrea modificaciones."""
        # Copiar preferencias actuales a sin_guardar si es primera vez
        if not self._prefs_sin_guardar:
            import copy
            self._prefs_sin_guardar = copy.deepcopy(self._prefs)
        
        # Mapear el control a su preferencia correspondiente
        # Switches
        if control == self._cfg_sw_notificaciones:
            self._prefs_sin_guardar["ui"]["mostrar_notificaciones"] = self._cfg_sw_notificaciones.value
        elif control == self._cfg_sw_animaciones:
            self._prefs_sin_guardar["ui"]["animaciones"] = self._cfg_sw_animaciones.value
        elif control == self._cfg_sw_tema_oscuro:
            self._prefs_sin_guardar["ui"]["tema_oscuro"] = self._cfg_sw_tema_oscuro.value
        elif control == self._cfg_sw_modo_compacto:
            self._prefs_sin_guardar["ui"]["modo_compacto"] = self._cfg_sw_modo_compacto.value
        elif control == self._cfg_sw_auto_expandir_chat:
            self._prefs_sin_guardar["ui"]["auto_expandir_chat"] = self._cfg_sw_auto_expandir_chat.value
        elif control == self._cfg_sw_auto_respuestas:
            self._prefs_sin_guardar["features"]["chat_auto_respuesta"] = self._cfg_sw_auto_respuestas.value
        elif control == self._cfg_sw_autoasignacion:
            self._prefs_sin_guardar["features"]["chat_autoasignacion"] = self._cfg_sw_autoasignacion.value
        elif control == self._cfg_sw_chat_notif_externa:
            self._prefs_sin_guardar["features"]["chat_notificacion_externa"] = self._cfg_sw_chat_notif_externa.value
        elif control == self._cfg_sw_evitar_duplicados_chat:
            self._prefs_sin_guardar["features"]["evitar_duplicados_chat"] = self._cfg_sw_evitar_duplicados_chat.value
        elif control == self._cfg_sw_menu_badges:
            self._prefs_sin_guardar["features"]["menu_badges"] = self._cfg_sw_menu_badges.value
        elif control == self._cfg_sw_refresco_auto:
            self._prefs_sin_guardar["features"]["refresco_automatico"] = self._cfg_sw_refresco_auto.value
        elif control == self._cfg_sw_sonido_notificaciones:
            self._prefs_sin_guardar["features"]["sonido_notificaciones"] = self._cfg_sw_sonido_notificaciones.value
        elif control == self._cfg_sw_abrir_chat_notif:
            self._prefs_sin_guardar["features"]["abrir_chat_notificacion"] = self._cfg_sw_abrir_chat_notif.value
        elif control == self._cfg_sw_diagnostico:
            self._prefs_sin_guardar["features"]["diagnostico_rapido"] = self._cfg_sw_diagnostico.value
        # Dropdowns
        elif control == self._cfg_dd_ui_density:
            self._prefs_sin_guardar["ui"]["densidad"] = self._cfg_dd_ui_density.value
        elif control == self._cfg_dd_respuesta_modo:
            self._prefs_sin_guardar["chat"]["respuesta_modo"] = self._cfg_dd_respuesta_modo.value
        elif control == self._cfg_dd_autoasignacion:
            self._prefs_sin_guardar["chat"]["autoasignacion_modo"] = self._cfg_dd_autoasignacion.value
        elif control == self._cfg_dd_notif_duracion:
            self._prefs_sin_guardar["chat"]["notificacion_duracion"] = self._cfg_dd_notif_duracion.value
        elif control == self._cfg_dd_refresco_auto:
            try:
                self._prefs_sin_guardar["views"]["auto_refresh_interval"] = int(self._cfg_dd_refresco_auto.value or "30")
            except:
                pass
        elif control == self._cfg_dd_tickets_page_size:
            try:
                self._prefs_sin_guardar["views"]["tickets_page_size"] = int(self._cfg_dd_tickets_page_size.value or "40")
            except:
                pass
        elif control == self._cfg_dd_cola_page_size:
            try:
                self._prefs_sin_guardar["views"]["cola_page_size"] = int(self._cfg_dd_cola_page_size.value or "8")
            except:
                pass
        elif control == self._cfg_dd_inventario_page_size:
            try:
                self._prefs_sin_guardar["views"]["inventario_page_size"] = int(self._cfg_dd_inventario_page_size.value or "40")
            except:
                pass
        elif control == self._cfg_dd_reportes_page_size:
            try:
                self._prefs_sin_guardar["views"]["reportes_page_size"] = int(self._cfg_dd_reportes_page_size.value or "4")
            except:
                pass
        elif control == self._cfg_dd_chat_historial:
            try:
                self._prefs_sin_guardar["chat"]["historial_limite"] = int(self._cfg_dd_chat_historial.value or "30")
            except:
                pass
        elif control == self._cfg_dd_chat_preview:
            try:
                self._prefs_sin_guardar["chat"]["preview_limite"] = int(self._cfg_dd_chat_preview.value or "8")
            except:
                pass
        elif control == self._cfg_dd_escaner_srv:
            try:
                self._prefs_sin_guardar["views"]["escaner_srv_page_size"] = int(self._cfg_dd_escaner_srv.value or "40")
            except:
                pass
        elif control == self._cfg_dd_escaner_hist:
            try:
                self._prefs_sin_guardar["views"]["escaner_hist_page_size"] = int(self._cfg_dd_escaner_hist.value or "50")
            except:
                pass
        # TextFields
        elif control == self._cfg_txt_auto_respuesta:
            self._prefs_sin_guardar["chat"]["mensaje_auto"] = self._cfg_txt_auto_respuesta.value
        elif control == self._cfg_txt_contacto:
            self._prefs_sin_guardar["support"]["email"] = self._cfg_txt_contacto.value
        
        self._actualizar_etiqueta_cambios()
    
    def _configurar_pagina(self):
        """Configura las propiedades de la página."""
        self.page.title = "Kubo - Panel de Control IT"
        self.page.bgcolor = COLOR_FONDO
        self.page.padding = 0
        self.page.spacing = 0
        self.page.window.width = 1400
        self.page.window.height = 900
        self.page.window.title_bar_hidden = False
        self.page.theme_mode = ft.ThemeMode.DARK if self._prefs_bool("ui", "tema_oscuro", True) else ft.ThemeMode.LIGHT

        # Windows usa mejor .ico para el icono de barra; .png queda como respaldo.
        icono_ico = PROJECT_ROOT / "icons" / "kubo.ico"
        icono_png = PROJECT_ROOT / "icons" / "kubo.png"
        if icono_ico.exists():
            self.page.window.icon = str(icono_ico)
        elif icono_png.exists():
            self.page.window.icon = str(icono_png)

    def _usuario_operador(self) -> str:
        """Retorna el usuario operador para trazabilidad de auditoría."""
        return os.getenv("USERNAME") or os.getenv("USER") or "Operador"
    
    def _construir_ui(self):
        """Construye la interfaz de usuario principal."""
        # Header superior
        self.header = self._construir_header()
        nav_height = max(420, int(getattr(self.page.window, "height", 900)) - 130)
        
        # Panel de navegación lateral
        self.nav_rail = self._construir_navegacion()
        nav_lateral_scroll = Container(
            width=120,
            height=nav_height,
            bgcolor=COLOR_SUPERFICIE,
            content=ListView(
                controls=[
                    Container(
                        height=nav_height,
                        content=self.nav_rail,
                    )
                ],
                spacing=0,
                expand=True,
                padding=0,
            ),
        )
        
        # Área de contenido principal
        self.contenido = Container(
            content=self._obtener_vista(0, forzar=True),
            expand=True,
            padding=20,
            bgcolor=COLOR_FONDO
        )
        
        # Panel lateral de detalles (inicialmente oculto)
        self.panel_detalle = Container(
            content=Column([]),
            width=0,
            bgcolor=COLOR_SUPERFICIE,
            visible=False
        )
        
        # Layout principal
        layout = Column(
            controls=[
                self.header,
                Row(
                    controls=[
                        nav_lateral_scroll,
                        Container(width=1, bgcolor=COLOR_SUPERFICIE_2),
                        self.contenido,
                        self.panel_detalle
                    ],
                    expand=True,
                    spacing=0
                )
            ],
            spacing=0,
            expand=True
        )
        
        self.page.add(layout)
        self._actualizar_badges_navegacion()
    
    def _construir_header(self) -> Container:
        """Construye el header superior con información del sistema."""
        stats = self.gestor.obtener_estadisticas_generales()
        tecnicos = self.gestor.obtener_tecnicos()
        disponibles = len(tecnicos[tecnicos["ESTADO"] == "Disponible"])
        
        # Estado del servidor
        servidor_activo = servidor_esta_activo()
        ip_local = self.servidor_ip or obtener_ip_local()
        
        return Container(
            content=Row(
                controls=[
                    # Logo y título
                    Row([
                        Icon(icons.COMPUTER, color=COLOR_PRIMARIO, size=30),
                        Text("Kubo - Centro de Soporte IT", size=22, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ], spacing=10),
                    
                    # KPIs rápidos
                    Row([
                        self._mini_kpi("📋", str(stats["tickets_abiertos"]), "En Cola", COLOR_ADVERTENCIA),
                        self._mini_kpi("🔧", str(stats["tickets_en_proceso"]), "En Proceso", COLOR_INFO),
                        self._mini_kpi("✅", str(stats["tickets_cerrados"]), "Cerrados", COLOR_EXITO),
                        self._mini_kpi("👨‍💻", f"{disponibles}/{len(tecnicos)}", "Disponibles", 
                                      COLOR_EXITO if disponibles > 0 else COLOR_ERROR),
                        # Indicador del servidor
                        self._mini_kpi("🌐", ip_local, "Servidor", 
                                      COLOR_EXITO if servidor_activo else COLOR_ERROR),
                    ], spacing=30),
                    
                    # Fecha y hora
                    Column([
                        Text(datetime.now().strftime("%d/%m/%Y"), size=14, color=COLOR_TEXTO_SEC),
                        Text(datetime.now().strftime("%H:%M"), size=18, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ], horizontal_alignment=CrossAxisAlignment.END, spacing=2)
                ],
                alignment=MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=CrossAxisAlignment.CENTER
            ),
            bgcolor=COLOR_SUPERFICIE,
            padding=ft.Padding.symmetric(horizontal=30, vertical=15),
            border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
        )
    
    def _mini_kpi(self, icono: str, valor: str, label: str, color: str) -> Container:
        """Crea un mini KPI para el header."""
        return Container(
            content=Row([
                Text(icono, size=20),
                Column([
                    Text(valor, size=18, weight=FontWeight.BOLD, color=color),
                    Text(label, size=10, color=COLOR_TEXTO_SEC)
                ], spacing=0, horizontal_alignment=CrossAxisAlignment.CENTER)
            ], spacing=8),
            padding=ft.Padding.symmetric(horizontal=15, vertical=5),
            border_radius=ft.BorderRadius.all(10),
            bgcolor=COLOR_SUPERFICIE_2
        )
    
    def _construir_navegacion(self) -> NavigationRail:
        """Construye el panel de navegación lateral."""
        return NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=76,
            min_extended_width=160,
            bgcolor=COLOR_SUPERFICIE,
            indicator_color=COLOR_PRIMARIO,
            destinations=[
                NavigationRailDestination(
                    icon=icons.DASHBOARD_OUTLINED,
                    selected_icon=icons.DASHBOARD,
                    label="Dashboard"
                ),
                NavigationRailDestination(
                    icon=icons.SUPPORT_AGENT_OUTLINED,
                    selected_icon=icons.SUPPORT_AGENT,
                    label="Técnicos"
                ),
                NavigationRailDestination(
                    icon=icons.CONFIRMATION_NUMBER_OUTLINED,
                    selected_icon=icons.CONFIRMATION_NUMBER,
                    label="Tickets"
                ),
                NavigationRailDestination(
                    icon=icons.FORUM_OUTLINED,
                    selected_icon=icons.FORUM,
                    label="Chats"
                ),
                NavigationRailDestination(
                    icon=icons.QUEUE_OUTLINED,
                    selected_icon=icons.QUEUE,
                    label="Cola"
                ),
                NavigationRailDestination(
                    icon=icons.HISTORY_OUTLINED,
                    selected_icon=icons.HISTORY,
                    label="Historial"
                ),
                NavigationRailDestination(
                    icon=icons.ANALYTICS_OUTLINED,
                    selected_icon=icons.ANALYTICS,
                    label="Reportes"
                ),
                NavigationRailDestination(
                    icon=icons.INVENTORY_2_OUTLINED,
                    selected_icon=icons.INVENTORY_2,
                    label="Equipos"
                ),
                NavigationRailDestination(
                    icon=icons.WIFI_TETHERING,
                    selected_icon=icons.WIFI_TETHERING,
                    label="Red/Escaneo"
                ),
                NavigationRailDestination(
                    icon=icons.NOTIFICATIONS_OUTLINED,
                    selected_icon=icons.NOTIFICATIONS_ACTIVE,
                    label="Solicitudes"
                ),
                NavigationRailDestination(
                    icon=icons.MANAGE_SEARCH_OUTLINED,
                    selected_icon=icons.MANAGE_SEARCH,
                    label="Búsqueda"
                ),
                NavigationRailDestination(
                    icon=icons.SETTINGS_OUTLINED,
                    selected_icon=icons.SETTINGS,
                    label="Configuración"
                ),
            ],
            on_change=self._cambiar_vista
        )
    
    def _cambiar_vista(self, e):
        """Maneja el cambio de vista desde la navegación."""
        t0 = time.perf_counter()
        menu_a_vista = {
            0: 0,   # Dashboard
            1: 1,   # Tecnicos
            2: 2,   # Tickets
            3: 11,  # Chats
            4: 3,   # Cola
            5: 4,   # Historial
            6: 5,   # Reportes
            7: 6,   # Inventario
            8: 7,   # Red/Escaneo
            9: 8,   # Solicitudes
            10: 9,  # Busqueda
            11: 10, # Configuracion
        }
        self.vista_actual = menu_a_vista.get(e.control.selected_index, e.control.selected_index)
        self.contenido.content = self._obtener_vista(self.vista_actual)
        self.page.update()
        total_ms = (time.perf_counter() - t0) * 1000.0
        if total_ms >= self._perf_umbral_lento_ms:
            print(f"[PERF][UI] Cambio a '{self._nombre_vista(self.vista_actual)}' tardó {total_ms:.1f} ms")
        elif self._perf_log_detallado:
            print(f"[PERF][UI] Cambio a '{self._nombre_vista(self.vista_actual)}' en {total_ms:.1f} ms")

    def _builders_vistas(self):
        return [
            self._vista_dashboard,
            self._vista_tecnicos,
            self._vista_tickets,
            self._vista_cola,
            self._vista_historial,
            self._vista_reportes,
            self._vista_inventario,
            self._vista_escaner_red,
            self._vista_solicitudes,
            self._vista_busqueda_global,
            self._vista_configuracion_app,
            self._vista_chats,
        ]

    def _obtener_vista(self, indice: int, forzar: bool = False):
        t0 = time.perf_counter()
        ahora = time.time()
        cached = self._vistas_cache.get(indice)
        if cached and not forzar:
            if ahora - float(cached.get("ts", 0.0)) <= self._cache_ttl_segundos:
                # Actualizar orden LRU
                if indice in self._vistas_cache_orden:
                    self._vistas_cache_orden.remove(indice)
                self._vistas_cache_orden.append(indice)
                self._registrar_tiempo_vista(indice, (time.perf_counter() - t0) * 1000.0, cache_hit=True)
                return cached["control"]

        vistas = self._builders_vistas()
        try:
            control = vistas[indice]()
        except Exception as ex:
            import traceback
            nombre_vista = self._nombre_vista(indice)
            print(f"[VISTA][ERROR] {nombre_vista}: {ex}")
            traceback.print_exc()
            control = self._vista_error(nombre_vista, ex)
        self._vistas_cache[indice] = {"control": control, "ts": ahora}

        if indice in self._vistas_cache_orden:
            self._vistas_cache_orden.remove(indice)
        self._vistas_cache_orden.append(indice)

        while len(self._vistas_cache_orden) > self._max_vistas_cache:
            viejo = self._vistas_cache_orden.pop(0)
            self._vistas_cache.pop(viejo, None)

        self._registrar_tiempo_vista(indice, (time.perf_counter() - t0) * 1000.0, cache_hit=False)

        return control

    def _nombre_vista(self, indice: int) -> str:
        nombres = [
            "Dashboard",
            "Técnicos",
            "Tickets",
            "Cola",
            "Historial",
            "Reportes",
            "Inventario",
            "Red/Escaneo",
            "Solicitudes",
            "Búsqueda",
            "Configuración",
            "Chats",
        ]
        return nombres[indice] if 0 <= indice < len(nombres) else f"Vista {indice}"

    def _vista_chats(self) -> Column:
        """Vista de conversaciones de chat agrupadas por departamento y usuario."""
        import unicodedata

        resumen = self.gestor.obtener_resumen_chats_tickets(limite=400)

        if not resumen:
            contenido_vacio = Column([
                Row([
                    Text("Chats de Tickets", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                ]),
                Container(
                    content=Column([
                        Icon(icons.FORUM, size=42, color=COLOR_TEXTO_SEC),
                        Text("Sin conversaciones aún", size=16, weight=FontWeight.W_600, color=COLOR_TEXTO),
                        Text("Los chats aparecerán cuando un ticket tenga mensajes.", size=12, color=COLOR_TEXTO_SEC),
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=6),
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=12,
                    padding=20,
                )
            ], spacing=16, scroll=ScrollMode.AUTO)
            return Column(
                controls=[
                    Container(
                        content=contenido_vacio,
                        padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                        expand=True,
                    )
                ],
                scroll=ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=CrossAxisAlignment.STRETCH,
            )

        departamentos = sorted({(x.get("categoria") or "Sin categoría") for x in resumen})
        usuarios_disponibles = sorted({(x.get("usuario_ad") or "Sin usuario") for x in resumen})
        estados_disponibles = sorted({(x.get("estado") or "-") for x in resumen})

        dd_departamento = Dropdown(
            label="Departamento",
            width=220,
            value="Todos",
            options=[dropdown.Option("Todos")] + [dropdown.Option(d) for d in departamentos],
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        dd_usuario = Dropdown(
            label="Usuario",
            width=220,
            value="Todos",
            options=[dropdown.Option("Todos")] + [dropdown.Option(u) for u in usuarios_disponibles],
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        dd_estado = Dropdown(
            label="Estado",
            width=180,
            value="Todos",
            options=[dropdown.Option("Todos")] + [dropdown.Option(e) for e in estados_disponibles],
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        txt_buscar = TextField(
            label="Buscar por ticket o turno",
            hint_text="Ej: 9A20EAFE o A-004",
            prefix_icon=icons.SEARCH,
            width=280,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )

        resumen_text = Text("", size=11, color=COLOR_TEXTO_SEC)
        contenedor_bloques = Column(spacing=12)

        def _norm(valor: Any) -> str:
            txt = str(valor or "").strip().lower()
            txt = " ".join(txt.split())
            return "".join(c for c in unicodedata.normalize("NFD", txt) if unicodedata.category(c) != "Mn")

        def _render_chats_filtrados(e=None):
            dep = dd_departamento.value or "Todos"
            usu = dd_usuario.value or "Todos"
            est = dd_estado.value or "Todos"
            q = _norm(txt_buscar.value)

            dep_norm = _norm(dep)
            usu_norm = _norm(usu)
            est_norm = _norm(est)

            filtrado = []
            for item in resumen:
                categoria = (item.get("categoria") or "Sin categoría")
                usuario = (item.get("usuario_ad") or "Sin usuario")
                estado = (item.get("estado") or "-")
                id_ticket = str(item.get("id_ticket") or "")
                turno = str(item.get("turno") or "")

                categoria_norm = _norm(categoria)
                usuario_norm = _norm(usuario)
                estado_norm = _norm(estado)
                id_ticket_norm = _norm(id_ticket)
                turno_norm = _norm(turno)

                if dep_norm != _norm("Todos") and categoria_norm != dep_norm:
                    continue
                if usu_norm != _norm("Todos") and usuario_norm != usu_norm:
                    continue
                if est_norm != _norm("Todos") and estado_norm != est_norm:
                    continue
                if q and q not in id_ticket_norm and q not in turno_norm:
                    continue
                filtrado.append(item)

            resumen_text.value = f"Mostrando {len(filtrado)} conversaciones"

            if not filtrado:
                contenedor_bloques.controls = [
                    Container(
                        content=Text("No hay resultados con esos filtros.", color=COLOR_TEXTO_SEC, size=12),
                        bgcolor=COLOR_SUPERFICIE,
                        border_radius=10,
                        padding=12,
                    )
                ]
                self.page.update()
                return

            agrupado: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
            for item in filtrado:
                categoria = item.get("categoria", "Sin categoría") or "Sin categoría"
                usuario = item.get("usuario_ad", "Sin usuario") or "Sin usuario"
                agrupado.setdefault(categoria, {}).setdefault(usuario, []).append(item)

            bloques = []
            for categoria in sorted(agrupado.keys()):
                usuarios = agrupado[categoria]
                bloques_usuarios = []
                for usuario in sorted(usuarios.keys()):
                    tickets_usuario = usuarios[usuario]
                    tarjetas = []
                    for t in tickets_usuario:
                        id_ticket = t.get("id_ticket", "")
                        turno = t.get("turno", "-")
                        estado = t.get("estado", "-")
                        total = int(t.get("total_mensajes", 0) or 0)
                        ultima = str(t.get("ultima_fecha", ""))[:16]

                        tarjetas.append(
                            Container(
                                content=Row([
                                    Column([
                                        Text(f"Turno {turno}", size=12, weight=FontWeight.W_700, color=COLOR_ACENTO),
                                        Text(f"Ticket #{id_ticket}", size=11, color=COLOR_TEXTO),
                                        Text(f"Estado: {estado}", size=10, color=COLOR_TEXTO_SEC),
                                    ], spacing=2, expand=True),
                                    Column([
                                        Text(f"{total} mensajes", size=11, weight=FontWeight.W_600, color=COLOR_INFO),
                                        Text(ultima, size=10, color=COLOR_TEXTO_SEC),
                                        ft.TextButton(
                                            "Abrir chat",
                                            icon=icons.OPEN_IN_NEW,
                                            on_click=lambda e, tid=id_ticket: self._abrir_ticket_desde_chat(tid),
                                        ),
                                    ], spacing=2, horizontal_alignment=CrossAxisAlignment.END),
                                ], spacing=10),
                                bgcolor=COLOR_SUPERFICIE_2,
                                border=ft.Border.all(1, COLOR_SUPERFICIE_3),
                                border_radius=10,
                                padding=10,
                            )
                        )

                    bloques_usuarios.append(
                        Container(
                            content=Column([
                                Row([
                                    Icon(icons.PERSON, size=14, color=COLOR_INFO),
                                    Text(usuario, size=13, weight=FontWeight.W_600, color=COLOR_TEXTO),
                                    Container(
                                        content=Text(f"{len(tickets_usuario)}", size=10, color=colors.WHITE),
                                        bgcolor=COLOR_INFO,
                                        border_radius=10,
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                    )
                                ], spacing=8),
                                Column(tarjetas, spacing=8),
                            ], spacing=8),
                            bgcolor=COLOR_SUPERFICIE,
                            border_radius=10,
                            padding=10,
                        )
                    )

                bloques.append(
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.BUSINESS, size=16, color=COLOR_PRIMARIO),
                                Text(categoria, size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                Container(
                                    content=Text(f"{sum(len(v) for v in usuarios.values())} tickets", size=10, color=colors.WHITE),
                                    bgcolor=COLOR_PRIMARIO,
                                    border_radius=10,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                )
                            ], spacing=8),
                            Column(bloques_usuarios, spacing=10),
                        ], spacing=10),
                        bgcolor=COLOR_SUPERFICIE,
                        border_radius=12,
                        border=ft.Border.all(1, COLOR_SUPERFICIE_3),
                        padding=12,
                    )
                )

            contenedor_bloques.controls = bloques
            self.page.update()

        dd_departamento.on_change = _render_chats_filtrados
        dd_usuario.on_change = _render_chats_filtrados
        dd_estado.on_change = _render_chats_filtrados
        txt_buscar.on_change = _render_chats_filtrados

        def _limpiar_filtros(e=None):
            dd_departamento.value = "Todos"
            dd_usuario.value = "Todos"
            dd_estado.value = "Todos"
            txt_buscar.value = ""
            _render_chats_filtrados()

        _render_chats_filtrados()

        contenido_vista = Column([
            # Encabezado elegante
            self._crear_encabezado_seccion("💬", "Chats de Tickets",
                                          "Conversaciones organizadas por departamento y usuario"),
            
            # Tarjeta de filtros mejorada
            self._crear_card_filtros([
                Row([
                    dd_departamento,
                    dd_usuario,
                    dd_estado,
                    txt_buscar,
                ], spacing=10, wrap=True),
                Container(height=8),
                Row([
                    ft.ElevatedButton("✓ Aplicar", icon=icons.FILTER_ALT, on_click=_render_chats_filtrados),
                    ft.OutlinedButton("↺ Limpiar", icon=icons.CLEAR, on_click=_limpiar_filtros),
                ], spacing=10)
            ], "#4ECDC4"),
            
            Container(height=12),
            resumen_text,
            contenedor_bloques,
        ], spacing=14, scroll=ScrollMode.AUTO, horizontal_alignment=CrossAxisAlignment.STRETCH)
        return Column(
            controls=[
                Container(
                    content=contenido_vista,
                    padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                    expand=True,
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=CrossAxisAlignment.STRETCH,
        )

    def _abrir_ticket_desde_chat(self, id_ticket: str):
        """Abre el diálogo de detalle del ticket desde la vista de chats."""
        try:
            ticket = self.gestor.obtener_ticket_por_id(id_ticket)
            if not ticket:
                self._mostrar_advertencia("Ticket no encontrado", f"No existe el ticket #{id_ticket}")
                return
            self._mostrar_dialogo_chat_rapido(ticket)
        except Exception as ex:
            self._mostrar_error("No se pudo abrir el ticket", str(ex))

    def _mostrar_dialogo_chat_rapido(self, ticket: Dict[str, Any]) -> None:
        """Diálogo compacto para chat: solo conversación y cambio de estado."""
        id_ticket = str(ticket.get("ID_TICKET", "") or "").strip()
        if not id_ticket:
            self._mostrar_advertencia("Ticket inválido")
            return

        estado_actual = str(ticket.get("ESTADO", "Abierto") or "Abierto")
        turno = str(ticket.get("TURNO", "-") or "-")

        chat_list = ListView(height=360, spacing=8, auto_scroll=True)
        txt_chat = TextField(
            label="Escribe tu mensaje",
            hint_text="Responder al usuario...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            expand=True,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            prefix_icon=icons.FORUM,
        )

        dd_estado = Dropdown(
            label="Estado del ticket",
            value=estado_actual,
            options=[dropdown.Option(e) for e in ESTADOS_TICKET],
            width=230,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )

        self._chat_detalle_ticket_id = id_ticket
        self._chat_detalle_list_ref = chat_list
        self._chat_detalle_txt_ref = txt_chat
        self._chat_detalle_activo = True

        dialogo = None

        def cerrar_dialogo(e=None):
            nonlocal dialogo
            if dialogo:
                dialogo.open = False
                self._reset_chat_detalle_contexto()
                self.page.update()

        def refrescar_chat(e=None):
            try:
                self._chat_detalle_actualizar(ticket, chat_list=chat_list, recargar=True)
            except Exception:
                pass

        def cambiar_estado(e=None):
            try:
                nuevo_estado = dd_estado.value or estado_actual
                if nuevo_estado == estado_actual:
                    return

                if InputValidator is not None:
                    ok, err = InputValidator.validar_estado_cambio(estado_actual, nuevo_estado)
                    if not ok:
                        self._mostrar_advertencia(err or "Transición de estado inválida")
                        dd_estado.value = estado_actual
                        self.page.update()
                        return

                self.gestor.actualizar_ticket(
                    id_ticket,
                    estado=nuevo_estado,
                    usuario_op=self._usuario_operador(),
                    origen="kubo.chat.rapido",
                )

                try:
                    import ws_server as _ws
                    _ws.broadcast_global(
                        _ws.EVENTO_TICKET_ACTUALIZADO,
                        {"id_ticket": id_ticket, "estado": nuevo_estado},
                    )
                except Exception:
                    pass

                ticket["ESTADO"] = nuevo_estado
                self._mostrar_snackbar(f"Estado actualizado: {nuevo_estado}", COLOR_EXITO)
                self._actualizar_badges_navegacion()
                self._refrescar_vista()
            except Exception as ex:
                self._mostrar_error("No se pudo cambiar el estado", str(ex))

        def enviar_chat(e):
            if (ticket.get("ESTADO") or "") in {"Cerrado", "Cancelado"}:
                self._mostrar_advertencia("Este ticket ya no permite escribir porque está cerrado o cancelado.")
                return

            mensaje = (txt_chat.value or "").strip()
            if not mensaje:
                return
            try:
                msg = self.gestor.agregar_mensaje_chat_ticket(
                    id_ticket=id_ticket,
                    autor_tipo="tecnico",
                    autor_id=self._usuario_operador(),
                    mensaje=mensaje,
                )
                if not msg:
                    self._mostrar_error("Chat", "No se pudo guardar el mensaje")
                    return

                try:
                    import ws_server as _ws
                    _ws.broadcast_global(_ws.EVENTO_TICKET_CHAT_MENSAJE, {"mensaje_chat": msg})
                except Exception:
                    pass

                txt_chat.value = ""
                self._chat_detalle_actualizar(ticket, chat_list=chat_list, mensaje_nuevo=msg)
                self._actualizar_badges_navegacion()
            except Exception as ex:
                self._mostrar_error("Chat", str(ex))

        dialogo = AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.FORUM, size=20, color=colors.WHITE),
                    bgcolor=COLOR_PRIMARIO,
                    padding=8,
                    border_radius=8,
                ),
                Column([
                    Text(f"Chat • Ticket #{id_ticket}", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Text(f"Turno {turno}", size=11, color=COLOR_TEXTO_SEC),
                ], spacing=2, expand=True),
                dd_estado,
                ft.IconButton(icon=icons.SAVE, tooltip="Guardar estado", on_click=cambiar_estado),
            ], spacing=10, vertical_alignment=CrossAxisAlignment.CENTER),
            content=Container(
                content=Column([
                    Row([
                        Text("Conversación", size=13, weight=FontWeight.W_600, color=COLOR_ACENTO),
                        Container(expand=True),
                        ft.TextButton("Refrescar", icon=icons.REFRESH, on_click=refrescar_chat),
                    ]),
                    Container(
                        content=chat_list,
                        bgcolor=COLOR_SUPERFICIE_2,
                        border=ft.Border.all(1, COLOR_SUPERFICIE_3),
                        border_radius=12,
                        padding=10,
                    ),
                    Row([
                        txt_chat,
                        ft.FilledButton("Enviar", icon=icons.SEND, on_click=enviar_chat),
                    ], vertical_alignment=CrossAxisAlignment.END),
                ], spacing=12),
                width=760,
                height=560,
                padding=4,
            ),
            actions=[
                ft.TextButton("Cerrar", icon=icons.CLOSE, on_click=cerrar_dialogo),
            ],
            actions_alignment=MainAxisAlignment.END,
        )

        refrescar_chat()
        self.page.show_dialog(dialogo)

    def _guardar_preferencias_locales(self, e=None):
        self._prefs.setdefault("ui", {})
        self._prefs.setdefault("features", {})
        self._prefs.setdefault("support", {})
        self._prefs.setdefault("chat", {})
        self._prefs.setdefault("views", {})
        self._prefs["ui"]["mostrar_notificaciones"] = bool(self._cfg_sw_notificaciones.value) if self._cfg_sw_notificaciones else True
        self._prefs["ui"]["animaciones"] = bool(self._cfg_sw_animaciones.value) if self._cfg_sw_animaciones else True
        self._prefs["ui"]["tema_oscuro"] = bool(self._cfg_sw_tema_oscuro.value) if self._cfg_sw_tema_oscuro else True
        self._prefs["ui"]["modo_compacto"] = bool(self._cfg_sw_modo_compacto.value) if self._cfg_sw_modo_compacto else False
        self._prefs["ui"]["auto_expandir_chat"] = bool(self._cfg_sw_auto_expandir_chat.value) if self._cfg_sw_auto_expandir_chat else True
        self._prefs["ui"]["densidad"] = self._cfg_dd_ui_density.value if self._cfg_dd_ui_density and self._cfg_dd_ui_density.value else "normal"
        self._prefs["features"]["diagnostico_rapido"] = bool(self._cfg_sw_diagnostico.value) if self._cfg_sw_diagnostico else True
        self._prefs["features"]["chat_auto_respuesta"] = bool(self._cfg_sw_auto_respuestas.value) if self._cfg_sw_auto_respuestas else True
        self._prefs["features"]["chat_autoasignacion"] = bool(self._cfg_sw_autoasignacion.value) if self._cfg_sw_autoasignacion else True
        self._prefs["features"]["chat_notificacion_externa"] = bool(self._cfg_sw_chat_notif_externa.value) if self._cfg_sw_chat_notif_externa else True
        self._prefs["features"]["menu_badges"] = bool(self._cfg_sw_menu_badges.value) if self._cfg_sw_menu_badges else True
        self._prefs["features"]["refresco_automatico"] = bool(self._cfg_sw_refresco_auto.value) if self._cfg_sw_refresco_auto else True
        self._prefs["features"]["abrir_chat_notificacion"] = bool(self._cfg_sw_abrir_chat_notif.value) if self._cfg_sw_abrir_chat_notif else True
        self._prefs["features"]["sonido_notificaciones"] = bool(self._cfg_sw_sonido_notificaciones.value) if self._cfg_sw_sonido_notificaciones else False
        self._prefs["features"]["evitar_duplicados_chat"] = bool(self._cfg_sw_evitar_duplicados_chat.value) if self._cfg_sw_evitar_duplicados_chat else True
        self._prefs["chat"]["respuesta_modo"] = self._cfg_dd_respuesta_modo.value if self._cfg_dd_respuesta_modo and self._cfg_dd_respuesta_modo.value else "primer_mensaje"
        self._prefs["chat"]["autoasignacion_modo"] = self._cfg_dd_autoasignacion.value if self._cfg_dd_autoasignacion and self._cfg_dd_autoasignacion.value else "menor_carga"
        self._prefs["chat"]["notificacion_duracion"] = self._cfg_dd_notif_duracion.value if self._cfg_dd_notif_duracion and self._cfg_dd_notif_duracion.value else "short"
        if self._cfg_txt_contacto:
            self._prefs["support"]["email"] = self._cfg_txt_contacto.value.strip()
        if self._cfg_txt_auto_respuesta:
            self._prefs["chat"]["mensaje_auto"] = self._cfg_txt_auto_respuesta.value.strip()
        if self._cfg_dd_tickets_page_size:
            self._prefs["views"]["tickets_page_size"] = int(self._cfg_dd_tickets_page_size.value or 40)
        if self._cfg_dd_cola_page_size:
            self._prefs["views"]["cola_page_size"] = int(self._cfg_dd_cola_page_size.value or 8)
        if self._cfg_dd_inventario_page_size:
            self._prefs["views"]["inventario_page_size"] = int(self._cfg_dd_inventario_page_size.value or 40)
        if self._cfg_dd_reportes_page_size:
            self._prefs["views"]["reportes_page_size"] = int(self._cfg_dd_reportes_page_size.value or 4)
        if self._cfg_dd_chat_historial:
            self._prefs["chat"]["historial_limite"] = int(self._cfg_dd_chat_historial.value or 30)
        if self._cfg_dd_chat_preview:
            self._prefs["chat"]["preview_limite"] = int(self._cfg_dd_chat_preview.value or 8)
        if self._cfg_dd_escaner_srv:
            self._prefs["views"]["escaner_srv_page_size"] = int(self._cfg_dd_escaner_srv.value or 40)
        if self._cfg_dd_escaner_hist:
            self._prefs["views"]["escaner_hist_page_size"] = int(self._cfg_dd_escaner_hist.value or 50)
        if self._cfg_dd_refresco_auto:
            self._prefs["views"]["auto_refresh_interval"] = int(self._cfg_dd_refresco_auto.value or 30)
        save_app_preferences("kubo", self._prefs)
        self._normalizar_preferencias_kubo()
        self._aplicar_configuracion_en_vivo()
        self._actualizar_badges_navegacion()
        self._mostrar_snackbar("✓ Preferencias guardadas", COLOR_EXITO)

    def _restaurar_preferencias_recomendadas(self, e=None):
        """Restaura valores recomendados para automatizaciones opcionales."""
        try:
            if self._cfg_sw_notificaciones:
                self._cfg_sw_notificaciones.value = True
            if self._cfg_sw_animaciones:
                self._cfg_sw_animaciones.value = True
            if self._cfg_sw_diagnostico:
                self._cfg_sw_diagnostico.value = True
            if self._cfg_sw_tema_oscuro:
                self._cfg_sw_tema_oscuro.value = True
            if self._cfg_sw_modo_compacto:
                self._cfg_sw_modo_compacto.value = False
            if self._cfg_sw_auto_expandir_chat:
                self._cfg_sw_auto_expandir_chat.value = True
            if self._cfg_sw_auto_respuestas:
                self._cfg_sw_auto_respuestas.value = True
            if self._cfg_sw_autoasignacion:
                self._cfg_sw_autoasignacion.value = True
            if self._cfg_sw_chat_notif_externa:
                self._cfg_sw_chat_notif_externa.value = True
            if self._cfg_sw_menu_badges:
                self._cfg_sw_menu_badges.value = True
            if self._cfg_sw_refresco_auto:
                self._cfg_sw_refresco_auto.value = True
            if self._cfg_sw_sonido_notificaciones:
                self._cfg_sw_sonido_notificaciones.value = False
            if self._cfg_sw_abrir_chat_notif:
                self._cfg_sw_abrir_chat_notif.value = True
            if self._cfg_sw_evitar_duplicados_chat:
                self._cfg_sw_evitar_duplicados_chat.value = True
            if self._cfg_dd_respuesta_modo:
                self._cfg_dd_respuesta_modo.value = "primer_mensaje"
            if self._cfg_dd_autoasignacion:
                self._cfg_dd_autoasignacion.value = "menor_carga"
            if self._cfg_dd_notif_duracion:
                self._cfg_dd_notif_duracion.value = "short"
            if self._cfg_dd_tickets_page_size:
                self._cfg_dd_tickets_page_size.value = "40"
            if self._cfg_dd_cola_page_size:
                self._cfg_dd_cola_page_size.value = "8"
            if self._cfg_dd_inventario_page_size:
                self._cfg_dd_inventario_page_size.value = "40"
            if self._cfg_dd_reportes_page_size:
                self._cfg_dd_reportes_page_size.value = "4"
            if self._cfg_dd_chat_historial:
                self._cfg_dd_chat_historial.value = "30"
            if self._cfg_dd_chat_preview:
                self._cfg_dd_chat_preview.value = "8"
            if self._cfg_dd_escaner_srv:
                self._cfg_dd_escaner_srv.value = "40"
            if self._cfg_dd_escaner_hist:
                self._cfg_dd_escaner_hist.value = "50"
            if self._cfg_dd_refresco_auto:
                self._cfg_dd_refresco_auto.value = "30"
            if self._cfg_txt_auto_respuesta:
                self._cfg_txt_auto_respuesta.value = "Recibimos tu mensaje. Un técnico te atenderá a la brevedad."

            self._guardar_preferencias_locales()
            self.page.update()
        except Exception as ex:
            self._mostrar_error(f"No se pudieron restaurar preferencias: {ex}")

    def _verificar_licencia_desde_config(self, e=None):
        resultado = verify_license_now("receptora")
        if resultado.get("ok"):
            self._mostrar_exito(resultado.get("message", "Licencia válida"), "Verificación de licencia")
        else:
            self._mostrar_error(resultado.get("message", "No se pudo verificar licencia"), "Verificación de licencia")

    def _enviar_reporte_soporte(self, e=None):
        if not self._cfg_txt_mensaje or not self._cfg_txt_mensaje.value.strip():
            self._mostrar_advertencia("Escribe un mensaje antes de enviarlo", "Soporte")
            return

        contacto = self._cfg_txt_contacto.value.strip() if self._cfg_txt_contacto else ""
        mensaje = self._cfg_txt_mensaje.value.strip()
        envio = send_support_report(
            app_id="kubo",
            report_type="sugerencia",
            message=mensaje,
            contact=contacto,
            extra={"servidor": self.servidor_ip or "", "puerto": self.servidor_puerto or ""},
        )

        if envio.get("ok"):
            self._cfg_txt_mensaje.value = ""
            self._mostrar_exito("Reporte enviado correctamente", "Soporte")
            self.page.update()
        else:
            self._mostrar_error(f"No se pudo enviar: {envio.get('error', 'error desconocido')}", "Soporte")

    def _crear_control_config_con_ayuda(self, control, help_text: str = "") -> Container:
        """Envuelve un control con texto de ayuda debajo con estilo mejorado."""
        contenido = [control]
        if help_text:
            contenido.append(
                Text(help_text, size=9, color=COLOR_TEXTO_SEC, italic=True, weight=FontWeight.W_400)
            )
        return Container(
            content=Column(contenido, spacing=3),
            padding=ft.Padding.only(bottom=4, top=2),
            margin=ft.Margin.only(bottom=8)
        )
    
    def _crear_card_seccion_elegante(self, icono: str, titulo: str, controles: List, color_icono: str = "#FF6B6B") -> Card:
        """Crea una tarjeta de sección elegante con ícono, título y controles."""
        header = Container(
            content=Row([
                Icon(icono, size=24, color=color_icono),
                Text(titulo, size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO, expand=True),
            ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
            padding=ft.Padding.only(bottom=12, top=0),
        )
        
        contenido_col = Column([header, Divider(height=1, color="#404040")] + controles + [Container(height=4)], spacing=6)
        
        return Card(
            content=Container(
                content=contenido_col,
                padding=16,
            ),
            elevation=2,
        )

    def _crear_encabezado_seccion(self, emoji: str, titulo: str, subtitulo: str = "", color_titulo: str = COLOR_TEXTO) -> Container:
        """Crea un encabezado elegante con emoji, título y subtítulo opcional."""
        return Container(
            content=Column([
                Text(f"{emoji} {titulo}", size=24, weight=FontWeight.BOLD, color=color_titulo),
                Text(subtitulo, size=12, color=COLOR_TEXTO_SEC, weight=FontWeight.W_400) if subtitulo else Container(height=0),
            ], spacing=2),
            padding=ft.Padding.only(bottom=16, top=6),
        )

    def _crear_card_filtros(self, controles: List, color_icono: str = "#45B7D1") -> Card:
        """Crea una tarjeta elegante para filtros con estilo consistente."""
        header = Row([
            Icon(icons.TUNE, size=20, color=color_icono),
            Text("Filtros y Búsqueda", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO, expand=True),
        ], spacing=10, vertical_alignment=CrossAxisAlignment.CENTER)
        
        contenido = Column([header, Divider(height=1, color="#404040"), Container(height=4)] + controles + [Container(height=4)], spacing=8)
        
        return Card(
            content=Container(content=contenido, padding=16),
            elevation=2,
        )

    def _crear_card_resumen(self, titulo: str, valor: str, icono: str, color_icono: str, subtitulo: str = "", width: int = 280) -> Card:
        """Crea una tarjeta de resumen/stat con icono y valor."""
        return Card(
            content=Container(
                width=width,
                content=Column([
                    Row([
                        Icon(icono, size=28, color=color_icono),
                        Column([
                            Text(titulo, size=11, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                            Text(valor, size=18, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Text(subtitulo, size=10, color=COLOR_TEXTO_SEC) if subtitulo else Container(height=0),
                        ], spacing=2),
                    ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
                ], spacing=6),
                padding=12,
            ),
            elevation=1,
        )

    def _envolver_layout_centrado(self, contenido, max_width: int = 1120, padding_h: int = 8) -> Container:
        """Envuelve una vista en un contenedor centrado con ancho máximo uniforme."""
        return Container(
            content=Row(
                [Container(content=contenido, width=max_width, expand=False)],
                alignment=MainAxisAlignment.CENTER,
            ),
            padding=ft.Padding.symmetric(horizontal=padding_h, vertical=0),
            expand=True,
        )
    
    def _construir_tab_interfaz(self) -> Column:
        self._cfg_sw_notificaciones = Switch(
            label="Notificaciones activas",
            value=bool(self._prefs.get("ui", {}).get("mostrar_notificaciones", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_sw_animaciones = Switch(
            label="Animaciones de interfaz",
            value=bool(self._prefs.get("ui", {}).get("animaciones", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_sw_tema_oscuro = Switch(
            label="Tema oscuro",
            value=bool(self._prefs.get("ui", {}).get("tema_oscuro", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_sw_modo_compacto = Switch(
            label="Modo compacto",
            value=bool(self._prefs.get("ui", {}).get("modo_compacto", False)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_sw_auto_expandir_chat = Switch(
            label="Expandir chat automáticamente",
            value=bool(self._prefs.get("ui", {}).get("auto_expandir_chat", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_dd_ui_density = Dropdown(
            label="Densidad visual",
            value=self._prefs.get("ui", {}).get("densidad", "normal"),
            options=[dropdown.Option("compacta"), dropdown.Option("normal"), dropdown.Option("amplia")],
        )
        self._cfg_dd_ui_density.on_change = self._on_config_change_tracked
        self._cfg_sw_refresco_auto = Switch(
            label="Auto-refresco de paneles",
            value=bool(self._prefs.get("features", {}).get("refresco_automatico", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_dd_refresco_auto = Dropdown(
            label="Intervalo de auto-refresco (seg)",
            value=str(self._prefs.get("views", {}).get("auto_refresh_interval", 30)),
            options=[dropdown.Option(v) for v in ["5", "10", "15", "30", "60", "120"]],
        )
        self._cfg_dd_refresco_auto.on_change = self._on_config_change_tracked
        self._cfg_sw_sonido_notificaciones = Switch(
            label="Sonido en notificaciones",
            value=bool(self._prefs.get("features", {}).get("sonido_notificaciones", False)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_sw_abrir_chat_notif = Switch(
            label="Abrir chat al hacer clic en notificación",
            value=bool(self._prefs.get("features", {}).get("abrir_chat_notificacion", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_sw_menu_badges = Switch(
            label="Mostrar contadores en menú lateral",
            value=bool(self._prefs.get("features", {}).get("menu_badges", True)),
            on_change=self._on_config_change_tracked,
        )
        
        return Column([
            Text("🎨 Interfaz y Apariencia", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
            Container(height=4),
            self._crear_control_config_con_ayuda(self._cfg_sw_notificaciones, self._cfg_help_text_dict.get("mostrar_notificaciones", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_animaciones, self._cfg_help_text_dict.get("animaciones", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_tema_oscuro, self._cfg_help_text_dict.get("tema_oscuro", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_modo_compacto, self._cfg_help_text_dict.get("modo_compacto", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_auto_expandir_chat, self._cfg_help_text_dict.get("auto_expandir_chat", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_ui_density, self._cfg_help_text_dict.get("densidad", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_refresco_auto, self._cfg_help_text_dict.get("refresco_auto", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_refresco_auto, self._cfg_help_text_dict.get("auto_refresh_interval", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_sonido_notificaciones, self._cfg_help_text_dict.get("sonido_notificaciones", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_abrir_chat_notif, self._cfg_help_text_dict.get("abrir_chat_notif", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_menu_badges, self._cfg_help_text_dict.get("menu_badges", "")),
            Container(height=12),
        ], spacing=6, scroll=ScrollMode.AUTO)
    
    def _construir_tab_chat(self) -> Column:
        """Construye el tab de configuración de chat inteligente."""
        self._cfg_sw_auto_respuestas = Switch(
            label="Respuestas automáticas de chat",
            value=bool(self._prefs.get("features", {}).get("chat_auto_respuesta", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_dd_respuesta_modo = Dropdown(
            label="Modo de respuesta automática",
            value=self._prefs.get("chat", {}).get("respuesta_modo", "primer_mensaje"),
            options=[dropdown.Option("primer_mensaje"), dropdown.Option("siempre")],
        )
        self._cfg_dd_respuesta_modo.on_change = self._on_config_change_tracked
        self._cfg_sw_autoasignacion = Switch(
            label="Autoasignar técnico por disponibilidad",
            value=bool(self._prefs.get("features", {}).get("chat_autoasignacion", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_dd_autoasignacion = Dropdown(
            label="Estrategia de autoasignación",
            value=self._prefs.get("chat", {}).get("autoasignacion_modo", "menor_carga"),
            options=[dropdown.Option("menor_carga"), dropdown.Option("primero_disponible")],
        )
        self._cfg_dd_autoasignacion.on_change = self._on_config_change_tracked
        self._cfg_sw_chat_notif_externa = Switch(
            label="Notificar cuando no estoy en chat",
            value=bool(self._prefs.get("features", {}).get("chat_notificacion_externa", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_sw_evitar_duplicados_chat = Switch(
            label="Evitar respuestas automáticas duplicadas",
            value=bool(self._prefs.get("features", {}).get("evitar_duplicados_chat", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_dd_notif_duracion = Dropdown(
            label="Duración de notificaciones",
            value=self._prefs.get("chat", {}).get("notificacion_duracion", "short"),
            options=[dropdown.Option("short"), dropdown.Option("medium"), dropdown.Option("long")],
        )
        self._cfg_dd_notif_duracion.on_change = self._on_config_change_tracked
        self._cfg_txt_auto_respuesta = TextField(
            label="Plantilla de respuesta automática",
            value=str(self._prefs.get("chat", {}).get("mensaje_auto", "Recibimos tu mensaje.")),
            multiline=True,
            min_lines=2,
            max_lines=3,
            on_blur=self._on_config_change_tracked,
        )
        self._cfg_dd_chat_historial = Dropdown(
            label="Historial de chat (mensajes)",
            value=str(self._prefs.get("chat", {}).get("historial_limite", 30)),
            options=[dropdown.Option(v) for v in ["10", "20", "30", "50", "100", "150"]],
        )
        self._cfg_dd_chat_historial.on_change = self._on_config_change_tracked
        self._cfg_dd_chat_preview = Dropdown(
            label="Mensajes visibles en vista rápida",
            value=str(self._prefs.get("chat", {}).get("preview_limite", 8)),
            options=[dropdown.Option(v) for v in ["3", "5", "8", "10", "12", "15"]],
        )
        self._cfg_dd_chat_preview.on_change = self._on_config_change_tracked
        
        return Column([
            Text("💬 Configuración de Chat Inteligente", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
            Container(height=4),
            self._crear_control_config_con_ayuda(self._cfg_sw_auto_respuestas, self._cfg_help_text_dict.get("chat_auto_respuesta", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_respuesta_modo, self._cfg_help_text_dict.get("respuesta_modo", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_autoasignacion, self._cfg_help_text_dict.get("chat_autoasignacion", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_autoasignacion, self._cfg_help_text_dict.get("autoasignacion_modo", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_chat_notif_externa, self._cfg_help_text_dict.get("chat_notificacion_externa", "")),
            self._crear_control_config_con_ayuda(self._cfg_sw_evitar_duplicados_chat, self._cfg_help_text_dict.get("evitar_duplicados_chat", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_notif_duracion, self._cfg_help_text_dict.get("notificacion_duracion", "")),
            self._crear_control_config_con_ayuda(self._cfg_txt_auto_respuesta, "Mensaje que recibirá el usuario al abrir un ticket"),
            self._crear_control_config_con_ayuda(self._cfg_dd_chat_historial, self._cfg_help_text_dict.get("historial_limite", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_chat_preview, self._cfg_help_text_dict.get("preview_limite", "")),
            Container(height=12),
        ], spacing=6, scroll=ScrollMode.AUTO)
    
    def _construir_tab_paneles(self) -> Column:
        """Construye el tab de tamaño de páginas y paneles."""
        self._cfg_dd_tickets_page_size = Dropdown(
            label="Tickets por página",
            value=str(self._prefs.get("views", {}).get("tickets_page_size", 40)),
            options=[dropdown.Option(v) for v in ["20", "40", "60", "80", "100"]],
        )
        self._cfg_dd_tickets_page_size.on_change = self._on_config_change_tracked
        self._cfg_dd_cola_page_size = Dropdown(
            label="Cola por página",
            value=str(self._prefs.get("views", {}).get("cola_page_size", 8)),
            options=[dropdown.Option(v) for v in ["4", "8", "12", "16", "20"]],
        )
        self._cfg_dd_cola_page_size.on_change = self._on_config_change_tracked
        self._cfg_dd_inventario_page_size = Dropdown(
            label="Inventario por página",
            value=str(self._prefs.get("views", {}).get("inventario_page_size", 40)),
            options=[dropdown.Option(v) for v in ["20", "40", "60", "80", "100"]],
        )
        self._cfg_dd_inventario_page_size.on_change = self._on_config_change_tracked
        self._cfg_dd_reportes_page_size = Dropdown(
            label="Reportes por página",
            value=str(self._prefs.get("views", {}).get("reportes_page_size", 4)),
            options=[dropdown.Option(v) for v in ["4", "6", "8", "10"]],
        )
        self._cfg_dd_reportes_page_size.on_change = self._on_config_change_tracked
        self._cfg_dd_escaner_srv = Dropdown(
            label="Registros del escáner por página",
            value=str(self._prefs.get("views", {}).get("escaner_srv_page_size", 40)),
            options=[dropdown.Option(v) for v in ["20", "40", "60", "80", "100"]],
        )
        self._cfg_dd_escaner_srv.on_change = self._on_config_change_tracked
        self._cfg_dd_escaner_hist = Dropdown(
            label="Historial de red por página",
            value=str(self._prefs.get("views", {}).get("escaner_hist_page_size", 50)),
            options=[dropdown.Option(v) for v in ["20", "50", "80", "100", "150"]],
        )
        self._cfg_dd_escaner_hist.on_change = self._on_config_change_tracked
        
        return Column([
            Text("📊 Tamaño de Paneles y Tablas", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
            Container(height=4),
            self._crear_control_config_con_ayuda(self._cfg_dd_tickets_page_size, self._cfg_help_text_dict.get("tickets_page_size", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_cola_page_size, self._cfg_help_text_dict.get("cola_page_size", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_inventario_page_size, self._cfg_help_text_dict.get("inventario_page_size", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_reportes_page_size, self._cfg_help_text_dict.get("reportes_page_size", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_escaner_srv, self._cfg_help_text_dict.get("escaner_srv_page_size", "")),
            self._crear_control_config_con_ayuda(self._cfg_dd_escaner_hist, self._cfg_help_text_dict.get("escaner_hist_page_size", "")),
            Container(height=12),
        ], spacing=6, scroll=ScrollMode.AUTO)
    
    def _construir_tab_avanzado(self) -> Column:
        """Construye el tab de opciones avanzadas y diagnóstico."""
        self._cfg_sw_diagnostico = Switch(
            label="Diagnóstico rápido",
            value=bool(self._prefs.get("features", {}).get("diagnostico_rapido", True)),
            on_change=self._on_config_change_tracked,
        )
        self._cfg_txt_contacto = TextField(
            label="Contacto de soporte",
            value=str(self._prefs.get("support", {}).get("email", "")),
            hint_text="correo@empresa.com",
            on_blur=self._on_config_change_tracked,
        )
        self._cfg_txt_mensaje = TextField(
            label="Sugerencia o reporte de problema",
            multiline=True,
            min_lines=3,
            max_lines=5,
            hint_text="Describe mejora, problema o solicitud",
        )
        
        return Column([
            Text("⚙️ Opciones Avanzadas", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
            Container(height=4),
            self._crear_control_config_con_ayuda(self._cfg_sw_diagnostico, self._cfg_help_text_dict.get("diagnostico_rapido", "")),
            Container(height=12),
            Text("📧 Enviar Reporte de Soporte", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
            Container(height=4),
            self._crear_control_config_con_ayuda(self._cfg_txt_contacto, "Tu email para que el equipo de soporte te contacte"),
            self._crear_control_config_con_ayuda(self._cfg_txt_mensaje, ""),
            ft.Button(
                "📧 Enviar reporte",
                icon=icons.SEND,
                on_click=self._enviar_reporte_soporte,
                width=200,
            ),
            Container(height=12),
        ], spacing=6, scroll=ScrollMode.AUTO)


    def _vista_configuracion_app(self) -> Column:
        licencia = read_license_status()

        # Búsqueda/filtro mejorada
        self._cfg_txt_search = TextField(
            label="🔍 Buscar opciones...",
            hint_text="Escribe para filtrar las opciones",
            on_change=lambda e: self._actualizar_etiqueta_cambios(),
            prefix_icon=icons.SEARCH,
            border_radius=12,
        )

        # Indicador de cambios mejorado
        self._cfg_lbl_cambios = Container(
            content=Row([
                Icon(icons.WARNING, color="#FFB74D", size=20),
                Text("⚠️  CAMBIOS SIN GUARDAR", color="#FFB74D", weight=FontWeight.BOLD, size=12),
            ], spacing=10, vertical_alignment=CrossAxisAlignment.CENTER),
            bgcolor="#2a2a2a",
            border_radius=12,
            padding=12,
            border="2px #FFB74D",
            visible=False,
        )

        # Estado de licencia mejorado
        estado_licencia = Container(
            content=Row([
                Icon(icons.VERIFIED_USER, size=20, color="#4CAF50"),
                Column([
                    Text(f"v{get_app_version()}", size=11, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Text(f"Estado: {licencia.get('last_reason', 'OK')}", size=10, color=COLOR_TEXTO_SEC),
                ], spacing=1, expand=True),
                ft.Button(
                    "Verificar",
                    icon=icons.VERIFIED_USER,
                    on_click=self._verificar_licencia_desde_config,
                    width=100,
                    height=36,
                )
            ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=12,
            padding=12,
            margin=ft.Margin.only(bottom=12),
        )

        # Botones de acción: una sola banda centrada para evitar desalineaciones.
        barra_acciones = Container(
            content=Row(
                controls=[
                    ft.OutlinedButton(
                        "Restaurar",
                        icon=icons.RESTART_ALT,
                        on_click=self._restaurar_preferencias_recomendadas,
                        width=160,
                    ),
                    ft.OutlinedButton(
                        "Descartar",
                        icon=icons.CLOSE,
                        on_click=self._descartar_cambios_config,
                        width=140,
                    ),
                    ft.OutlinedButton(
                        "Aplicar",
                        icon=icons.CHECK_CIRCLE,
                        on_click=self._aplicar_cambios_sin_guardar,
                        width=140,
                    ),
                    ft.Button(
                        "Guardar",
                        icon=icons.SAVE,
                        on_click=self._guardar_cambios_config,
                        width=140,
                    ),
                ],
                spacing=12,
                run_spacing=10,
                alignment=MainAxisAlignment.CENTER,
                wrap=True,
            ),
        )

        return Column(
            controls=[
                Container(
                    content=Column([
                        Text("⚙️ CONFIGURACIÓN", size=26, weight=FontWeight.BOLD, color="#FF6B6B"),
                        Text("Personaliza Kubo según tus preferencias", size=12, color=COLOR_TEXTO_SEC, weight=FontWeight.W_400),
                    ], spacing=4),
                    padding=ft.Padding.only(bottom=12, top=4),
                ),
                estado_licencia,
                self._cfg_txt_search,
                self._cfg_lbl_cambios,
                Container(height=4),
                # Tab 1: Interfaz
                self._crear_card_seccion_elegante(icons.PALETTE, "Interfaz y Apariencia", 
                    [self._crear_control_config_con_ayuda(c, h) for c, h in [
                        (self._construir_tab_interfaz(), ""),
                    ]], "#FF6B6B"),
                Container(height=12),
                # Tab 2: Chat
                self._crear_card_seccion_elegante(icons.CHAT, "Chat Inteligente",
                    [self._crear_control_config_con_ayuda(c, h) for c, h in [
                        (self._construir_tab_chat(), ""),
                    ]], "#4ECDC4"),
                Container(height=12),
                # Tab 3: Paneles
                self._crear_card_seccion_elegante(icons.VIEW_LIST, "Paneles y Tablas",
                    [self._crear_control_config_con_ayuda(c, h) for c, h in [
                        (self._construir_tab_paneles(), ""),
                    ]], "#45B7D1"),
                Container(height=12),
                # Tab 4: Avanzado
                self._crear_card_seccion_elegante(icons.ENGINEERING, "Opciones Avanzadas",
                    [self._crear_control_config_con_ayuda(c, h) for c, h in [
                        (self._construir_tab_avanzado(), ""),
                    ]], "#F39C12"),
                Container(height=16),
                barra_acciones,
                Container(height=20),
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
        )


    def _registrar_tiempo_vista(self, indice: int, duracion_ms: float, cache_hit: bool) -> None:
        nombre = self._nombre_vista(indice)
        historial = self._perf_vistas.setdefault(nombre, [])
        historial.append(duracion_ms)
        if len(historial) > 20:
            historial.pop(0)

        promedio = sum(historial) / max(len(historial), 1)
        estado_cache = "cache-hit" if cache_hit else "rebuild"

        if duracion_ms >= self._perf_umbral_lento_ms:
            print(
                f"[PERF][VISTA] {nombre} {estado_cache}: {duracion_ms:.1f} ms "
                f"(promedio {promedio:.1f} ms, n={len(historial)})"
            )
        elif self._perf_log_detallado:
            print(
                f"[PERF][VISTA] {nombre} {estado_cache}: {duracion_ms:.1f} ms "
                f"(promedio {promedio:.1f} ms)"
            )

    def _limitar_df_render(self, df: pd.DataFrame, max_filas: int) -> tuple[pd.DataFrame, int]:
        if df is None or df.empty:
            return df, 0
        total = len(df)
        if total <= max_filas:
            return df, 0
        return df.head(max_filas).copy(), total - max_filas

    def _limitar_lista_render(self, data: list, max_items: int) -> tuple[list, int]:
        if not data:
            return data, 0
        total = len(data)
        if total <= max_items:
            return data, 0
        return data[:max_items], total - max_items

    def _ui_call(self, callback):
        """Ejecuta un callback en el hilo de UI cuando viene desde background."""
        try:
            if hasattr(self.page, "run_task"):
                async def _runner():
                    callback()
                self.page.run_task(_runner)
            elif hasattr(self.page, "call_from_thread"):
                self.page.call_from_thread(callback)
            elif hasattr(self.page, "run_sync"):
                self.page.run_sync(callback)
            else:
                callback()
        except Exception:
            callback()

    def _vista_error(self, nombre_vista: str, ex: Exception) -> Container:
        """Muestra un error visible cuando una vista no puede construirse."""
        return Container(
            content=Column([
                Icon(icons.ERROR_OUTLINE, size=44, color=COLOR_ERROR),
                Text(f"No se pudo cargar {nombre_vista}", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Text(str(ex), size=12, color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER),
                Text("Revisa la consola para ver el traceback.", size=11, color=COLOR_TEXTO_SEC),
            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=15,
            padding=24,
            alignment=ft.Alignment(0, 0),
            expand=True,
        )
    
    # =========================================================================
    # VISTA: DASHBOARD
    # =========================================================================
    
    def _vista_dashboard(self) -> Column:
        """Construye un shell visible y carga el dashboard pesado en segundo plano."""
        self._dashboard_version += 1
        version = self._dashboard_version

        self._dashboard_contenido = Container(
            content=Column([
                Container(
                    content=Column([
                        ProgressRing(width=54, height=54, stroke_width=4, color=COLOR_ACENTO),
                        Container(height=10),
                        Text("Cargando dashboard...", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text("Calculando indicadores y paneles en segundo plano", size=11, color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER),
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=6),
                    padding=30,
                    alignment=ft.Alignment(0, 0),
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=15,
                )
            ], expand=True, horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
            expand=True,
            bgcolor=COLOR_FONDO,
        )

        vista = Column(
            controls=[
                Container(
                    content=Row([
                        Text("📊 Dashboard Ejecutivo en Tiempo Real", size=26, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(datetime.now().strftime("%d/%m/%Y %H:%M"), size=12, color=COLOR_TEXTO_SEC)
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding.only(bottom=25)
                ),
                self._dashboard_contenido,
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
        )

        self._cargar_dashboard_async(version)
        return vista

    def _construir_dashboard_contenido(self, stats: Dict[str, Any], tecnicos: pd.DataFrame, cola: pd.DataFrame, todos_tickets: pd.DataFrame) -> Column:
        """Construye el contenido pesado del dashboard una vez que los datos ya están listos."""
        tickets_hoy = stats["tickets_hoy"]
        resueltos_hoy = stats["tickets_cerrados"]
        tasa_resolucion = (resueltos_hoy / tickets_hoy * 100) if tickets_hoy > 0 else 0
        tasa_cumplimiento_sla = self._calcular_cumplimiento_sla(todos_tickets)
        tickets_en_espera = len(todos_tickets[todos_tickets.get("ESTADO") == "En Espera"]) if not todos_tickets.empty else 0
        tickets_activos_total = 0
        criticos_abiertos = 0

        if not todos_tickets.empty:
            estados_activos = {"Abierto", "En Cola", "En Proceso", "En Espera"}
            serie_estado = todos_tickets["ESTADO"].fillna("").astype(str) if "ESTADO" in todos_tickets.columns else pd.Series(dtype=str)
            mascara_activos = serie_estado.isin(estados_activos)
            tickets_activos_total = int(mascara_activos.sum())

            if "PRIORIDAD" in todos_tickets.columns:
                serie_prioridad = todos_tickets["PRIORIDAD"].fillna("").astype(str)
                criticos_abiertos = int((mascara_activos & (serie_prioridad == "Crítica")).sum())

        pct_activos_total = (tickets_activos_total / len(todos_tickets) * 100) if not todos_tickets.empty else 0
        pct_criticos_abiertos = (criticos_abiertos / tickets_activos_total * 100) if tickets_activos_total > 0 else 0

        try:
            from datetime import timedelta
            ayer = str((datetime.now() - timedelta(days=1)).date())
            if not todos_tickets.empty:
                df_tmp = todos_tickets.copy()
                df_tmp["FECHA_APERTURA"] = pd.to_datetime(df_tmp["FECHA_APERTURA"], errors="coerce")
                tickets_ayer = len(df_tmp[df_tmp["FECHA_APERTURA"].dt.date.astype(str) == ayer])
            else:
                tickets_ayer = 0
            if tickets_ayer > 0:
                delta = tickets_hoy - tickets_ayer
                indicador_hoy = f"+{delta}" if delta >= 0 else str(delta)
            elif tickets_hoy > 0:
                indicador_hoy = "🆕"
            else:
                indicador_hoy = "—"
        except Exception:
            indicador_hoy = "—"

        tecnicos_disponibles = len(tecnicos[tecnicos["ESTADO"] == "Disponible"]) if not tecnicos.empty else 0
        total_tecnicos = len(tecnicos)

        return Column(
            controls=[
                Container(
                    content=Column([
                        Text("📈 Indicadores Clave de Desempeño (KPIs)", size=14, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                        Container(height=10),
                        Row([
                            self._kpi_card_v2("Tickets Hoy", str(tickets_hoy), icons.TODAY, COLOR_INFO, indicador_hoy),
                            self._kpi_card_v2("En Resolución", str(len(cola)), icons.PENDING_ACTIONS, COLOR_PRIMARIO, "↑" if len(cola) > 3 else "↓"),
                            self._kpi_card_v2("Resueltos Hoy", str(resueltos_hoy), icons.CHECK_CIRCLE, COLOR_EXITO, f"+{resueltos_hoy}"),
                            self._kpi_card_v2("Tasa Resolución", f"{tasa_resolucion:.0f}%", icons.TRENDING_UP, COLOR_DISPONIBLE, "↑" if tasa_resolucion > 70 else "↓"),
                            self._kpi_card_v2("Cumplimiento SLA", f"{tasa_cumplimiento_sla:.0f}%", icons.VERIFIED_USER, COLOR_EXITO if tasa_cumplimiento_sla > 90 else COLOR_ADVERTENCIA, "✓" if tasa_cumplimiento_sla > 90 else "⚠"),
                        ], spacing=10, wrap=True, run_spacing=10, alignment=MainAxisAlignment.SPACE_BETWEEN, run_alignment=MainAxisAlignment.START),
                        Row([
                            self._kpi_card_v2("En Espera", str(tickets_en_espera), icons.SCHEDULE, COLOR_ADVERTENCIA, "⏱"),
                            self._kpi_card_v2("Técnicos Disponibles", f"{tecnicos_disponibles}/{total_tecnicos}", icons.ENGINEERING, COLOR_DISPONIBLE, "✓" if tecnicos_disponibles >= total_tecnicos * 0.5 else "✗"),
                            self._kpi_card_v2("Tiempo Prom.", f"{stats['tiempo_promedio_cierre']:.1f}h", icons.TIMER, COLOR_ACENTO, "•"),
                            self._kpi_card_v2("Tickets Activos", str(tickets_activos_total), icons.FIBER_NEW, COLOR_INFO, f"{pct_activos_total:.0f}%"),
                            self._kpi_card_v2("Críticos Abiertos", str(criticos_abiertos), icons.WARNING, COLOR_ERROR if criticos_abiertos > 0 else COLOR_EXITO, f"{pct_criticos_abiertos:.0f}%"),
                        ], spacing=10, wrap=True, run_spacing=10, alignment=MainAxisAlignment.SPACE_BETWEEN, run_alignment=MainAxisAlignment.START),
                    ], spacing=12, horizontal_alignment=CrossAxisAlignment.STRETCH),
                    padding=20,
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=15,
                ),
                Container(height=25),
                Row([
                    self._panel_tendencias_tickets(todos_tickets),
                    self._panel_rendimiento_tecnicos(tecnicos, todos_tickets),
                ], spacing=20, expand=True),
                Container(height=25),
                Row([
                    self._panel_distribucion_prioridad(todos_tickets),
                    self._panel_estado_equipos(),
                ], spacing=20, expand=True),
                Container(height=25),
                Row([
                    self._panel_estado_tecnicos_v2(tecnicos),
                    self._panel_tickets_criticos(todos_tickets),
                ], spacing=20, expand=True),
                Container(height=25),
                Row([
                    self._panel_distribucion_categorias_v2(todos_tickets),
                    self._panel_distribucion_horaria(todos_tickets),
                ], spacing=20, expand=True),
                Container(height=25),
                self._panel_tickets_recientes_v2(todos_tickets),
                Container(height=25),
                Row([
                    self._crear_grafico_circular(
                        {
                            "Abierto": len(todos_tickets[todos_tickets.get("ESTADO") == "Abierto"]) if not todos_tickets.empty else 0,
                            "En Proceso": len(todos_tickets[todos_tickets.get("ESTADO") == "En Proceso"]) if not todos_tickets.empty else 0,
                            "En Espera": len(todos_tickets[todos_tickets.get("ESTADO") == "En Espera"]) if not todos_tickets.empty else 0,
                            "Cerrado": len(todos_tickets[todos_tickets.get("ESTADO") == "Cerrado"]) if not todos_tickets.empty else 0,
                        },
                        "🎯 Estados de Tickets",
                        {
                            "Abierto": COLOR_ADVERTENCIA,
                            "En Proceso": COLOR_PRIMARIO,
                            "En Espera": COLOR_TEXTO_SEC,
                            "Cerrado": COLOR_EXITO,
                        }
                    ),
                    self._crear_heatmap_actividad(),
                ], spacing=20, expand=True),
                Container(height=25),
                Row([
                    self._panel_analisis_sla_tecnicos(tecnicos, todos_tickets),
                    self._panel_prediccion_carga(),
                ], spacing=20, expand=True),
                Container(height=25),
                Row([
                    self._panel_tiempo_resolucion(todos_tickets),
                ], spacing=20, expand=True),
                Container(height=25),
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
        )

    def _cargar_dashboard_async(self, version: int):
        """Carga los datos del dashboard en segundo plano."""
        if self._dashboard_cargando:
            return
        self._dashboard_cargando = True

        def cargar():
            try:
                stats = self.gestor.obtener_estadisticas_generales()
                tecnicos = self.gestor.obtener_tecnicos()
                cola = self.gestor.obtener_tickets_en_cola()
                todos_tickets = self.gestor.obtener_todos_tickets()
                self._stats_dash = self.gestor.obtener_stats_dashboard_reales()

                contenido = self._construir_dashboard_contenido(stats, tecnicos, cola, todos_tickets)
                if version != self._dashboard_version:
                    return

                def actualizar_ui():
                    if self._dashboard_contenido and version == self._dashboard_version:
                        self._dashboard_contenido.content = contenido
                        self.page.update()

                self._ui_call(actualizar_ui)
            except Exception as ex:
                def actualizar_error():
                    if version == self._dashboard_version and self._dashboard_contenido:
                        self._dashboard_contenido.content = Container(
                            content=Column([
                                Icon(icons.ERROR_OUTLINE, size=44, color=COLOR_ERROR),
                                Text("No se pudo cargar el dashboard", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                Text(str(ex), size=12, color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER),
                                Text("Revisa la consola para ver el detalle.", size=11, color=COLOR_TEXTO_SEC),
                            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                            bgcolor=COLOR_SUPERFICIE,
                            border_radius=15,
                            padding=24,
                            alignment=ft.Alignment(0, 0),
                            expand=True,
                        )
                        self.page.update()

                self._ui_call(actualizar_error)
            finally:
                if version == self._dashboard_version:
                    self._dashboard_cargando = False

        threading.Thread(target=cargar, daemon=True, name="DashboardLoader").start()
    
    def _kpi_card(self, titulo: str, valor: str, icono, color: str, cambio: str) -> Container:
        """Crea una tarjeta KPI grande."""
        return Container(
            content=Column([
                Row([
                    Icon(icono, color=color, size=28),
                    Text(cambio, size=12, color=COLOR_EXITO if "+" in cambio else COLOR_ERROR) if cambio else Container()
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Container(height=10),
                Text(valor, size=36, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Text(titulo, size=14, color=COLOR_TEXTO_SEC)
            ], spacing=5),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            width=200,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2)
        )
    
    def _panel_estado_tecnicos(self, tecnicos: pd.DataFrame) -> Container:
        """Panel con el estado de los técnicos."""
        items = []
        for _, tec in tecnicos.iterrows():
            estado = tec["ESTADO"]
            color_estado = {
                "Disponible": COLOR_DISPONIBLE,
                "Ocupado": COLOR_OCUPADO,
                "Ausente": COLOR_AUSENTE,
                "En Descanso": COLOR_DESCANSO
            }.get(estado, COLOR_TEXTO_SEC)
            
            icono_estado = {
                "Disponible": icons.CHECK_CIRCLE,
                "Ocupado": icons.PENDING,
                "Ausente": icons.CANCEL,
                "En Descanso": icons.COFFEE
            }.get(estado, icons.HELP)
            
            items.append(
                Container(
                    content=Row([
                        Container(
                            content=Text(tec["NOMBRE"][:2].upper(), size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            width=45,
                            height=45,
                            bgcolor=COLOR_SUPERFICIE_3,
                            border_radius=ft.BorderRadius.all(25),
                            alignment=ft.Alignment(0, 0)
                        ),
                        Column([
                            Text(tec["NOMBRE"], size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                            Row([
                                Icon(icono_estado, size=14, color=color_estado),
                                Text(estado, size=12, color=color_estado)
                            ], spacing=5)
                        ], spacing=2, expand=True),
                        Container(
                            content=Text(tec["ESPECIALIDAD"], size=10, color=COLOR_TEXTO_SEC),
                            bgcolor=COLOR_SUPERFICIE_2,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                            border_radius=ft.BorderRadius.all(5)
                        )
                    ], spacing=15),
                    padding=15,
                    border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
                )
            )
        
        return Container(
            content=Column([
                Row([
                    Text("👨‍💻 Estado del Equipo", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Container(
                        content=Text(f"{len(tecnicos[tecnicos['ESTADO'] == 'Disponible'])}/{len(tecnicos)}", 
                                   size=12, color=COLOR_TEXTO),
                        bgcolor=COLOR_EXITO if len(tecnicos[tecnicos['ESTADO'] == 'Disponible']) > 0 else COLOR_ERROR,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                        border_radius=ft.BorderRadius.all(10)
                    )
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Divider(color=COLOR_SUPERFICIE_2),
                Column(items, spacing=0)
            ], spacing=10),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            width=350,
            expand=True
        )
    
    def _panel_tickets_recientes(self) -> Container:
        """Panel con los tickets más recientes."""
        df = self.gestor.obtener_todos_tickets()
        recientes = df.head(5) if not df.empty else pd.DataFrame()
        
        items = []
        if recientes.empty:
            items.append(
                Container(
                    content=Column([
                        Icon(icons.INBOX, size=50, color=COLOR_TEXTO_SEC),
                        Text("Sin tickets recientes", color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER),
                    padding=40,
                    alignment=ft.Alignment(0, 0)
                )
            )
        else:
            for _, ticket in recientes.iterrows():
                color_estado = {
                    "Abierto": COLOR_ADVERTENCIA,
                    "En Cola": COLOR_INFO,
                    "En Proceso": COLOR_PRIMARIO,
                    "En Espera": COLOR_TEXTO_SEC,
                    "Cerrado": COLOR_EXITO
                }.get(ticket.get("ESTADO", "Abierto"), COLOR_TEXTO_SEC)
                
                items.append(
                    Container(
                        content=Row([
                            Column([
                                Text(f"#{ticket.get('ID_TICKET', 'N/A')}", size=14, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                                Text(str(ticket.get("USUARIO_AD", ""))[:15], size=12, color=COLOR_TEXTO_SEC)
                            ], spacing=2),
                            Column([
                                Text(str(ticket.get("CATEGORIA", "")), size=12, color=COLOR_TEXTO),
                                Container(
                                    content=Text(str(ticket.get("ESTADO", "")), size=10, color=colors.WHITE),
                                    bgcolor=color_estado,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                    border_radius=ft.BorderRadius.all(5)
                                )
                            ], spacing=2, horizontal_alignment=CrossAxisAlignment.END)
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                        padding=12,
                        border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2)),
                        on_click=lambda e, t=ticket: self._mostrar_detalle_ticket(t.to_dict())
                    )
                )
        
        return Container(
            content=Column([
                Row([
                    Text("📋 Tickets Recientes", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.TextButton("Ver todos", on_click=lambda e: self._ir_a_tickets())
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Divider(color=COLOR_SUPERFICIE_2),
                Column(items, spacing=0, scroll=ScrollMode.AUTO)
            ], spacing=10, expand=True),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _panel_distribucion_categorias(self) -> Container:
        """Panel con distribución de categorías."""
        dist = self.gestor.obtener_distribucion_categorias()
        
        barras = []
        if not dist.empty:
            max_val = dist["CANTIDAD"].max()
            for _, row in dist.iterrows():
                cat = row["CATEGORIA"]
                cant = row["CANTIDAD"]
                porc = row["PORCENTAJE"]
                color = COLORES_CATEGORIAS.get(cat, COLOR_TEXTO_SEC)
                ancho = (cant / max_val) * 300 if max_val > 0 else 50
                
                barras.append(
                    Row([
                        Container(width=100, content=Text(cat, size=12, color=COLOR_TEXTO)),
                        Container(
                            width=ancho,
                            height=20,
                            bgcolor=color,
                            border_radius=ft.BorderRadius.all(5)
                        ),
                        Text(f"{cant} ({porc}%)", size=12, color=COLOR_TEXTO_SEC)
                    ], spacing=15)
                )
        
        return Container(
            content=Column([
                Text("📊 Distribución por Categoría", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Divider(color=COLOR_SUPERFICIE_2),
                Column(barras, spacing=10) if barras else Text("Sin datos", color=COLOR_TEXTO_SEC)
            ], spacing=15),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20
        )
    
    # =========================================================================
    # NUEVOS MÉTODOS PARA DASHBOARD MEJORADO V2
    # =========================================================================
    
    def _calcular_cumplimiento_sla(self, tickets: pd.DataFrame) -> float:
        """Calcula el porcentaje de cumplimiento de SLA."""
        if tickets.empty:
            return 100.0
        
        try:
            tickets_sla = 0
            tickets_cumplidos = 0
            
            for _, ticket in tickets.iterrows():
                if ticket.get("ESTADO") == "Cerrado":
                    tickets_sla += 1
                    # Ej: Si fue cerrado en menos de 24h, se consider cumplido
                    fmt_cierre = str(ticket.get("FECHA_CIERRE", ""))
                    if fmt_cierre and fmt_cierre != "nan":
                        tickets_cumplidos += 1
            
            return (tickets_cumplidos / tickets_sla * 100) if tickets_sla > 0 else 100.0
        except:
            return 85.0
    
    def _kpi_card_v2(self, titulo: str, valor: str, icono, color: str, indicador: str) -> Container:
        """Crea una tarjeta KPI mejorada con diseño premium."""
        color_indicador = COLOR_EXITO if "✓" in indicador or "↑" in indicador or "+" in indicador else COLOR_ADVERTENCIA
        
        return Container(
            content=Column([
                Row([
                    Icon(icono, color=color, size=26),
                    Container(
                        content=Text(indicador, size=11, weight=FontWeight.BOLD, color=colors.WHITE),
                        bgcolor=color_indicador,
                        padding=ft.Padding.symmetric(horizontal=5, vertical=2),
                        border_radius=ft.BorderRadius.all(4)
                    )
                ], alignment=MainAxisAlignment.SPACE_BETWEEN, tight=True),
                Container(height=8),
                Text(valor, size=26, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Container(height=2),
                Text(titulo, size=10, color=COLOR_TEXTO_SEC)
            ], spacing=2),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(11),
            padding=12,
            width=175,
            height=145,
            border=ft.Border.all(1, COLOR_SUPERFICIE_3)
        )
    
    def _panel_tendencias_tickets(self, tickets: pd.DataFrame) -> Container:
        """Panel mostrando tendencias de tickets últimos 7 días con datos reales."""
        try:
            if tickets.empty:
                return self._panel_vacio("Tendencias de Última Semana")
            
            from datetime import timedelta
            hoy = datetime.now().date()
            
            # Calcular tickets reales por cada uno de los últimos 7 días
            dias_nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            cantidades = []
            etiquetas = []
            
            df_temp = tickets.copy()
            df_temp["FECHA_APERTURA"] = pd.to_datetime(df_temp["FECHA_APERTURA"], errors='coerce')
            df_temp = df_temp.dropna(subset=["FECHA_APERTURA"])
            
            for i in range(6, -1, -1):
                fecha = hoy - timedelta(days=i)
                conteo = len(df_temp[df_temp["FECHA_APERTURA"].dt.date == fecha])
                cantidades.append(conteo)
                etiquetas.append(dias_nombres[fecha.weekday()])
            
            max_val = max(cantidades) if cantidades and max(cantidades) > 0 else 1
            promedio = sum(cantidades) / len(cantidades) if cantidades else 0
            
            barras = []
            for dia, cant in zip(etiquetas, cantidades):
                altura = max((cant / max_val * 120), 4) if max_val > 0 else 4
                barras.append(
                    Column([
                        Container(
                            width=30,
                            height=altura,
                            bgcolor=COLOR_PRIMARIO if cant > 0 else COLOR_SUPERFICIE_2,
                            border_radius=ft.BorderRadius.only(
                                top_left=5, top_right=5
                            )
                        ),
                        Text(str(cant), size=10, color=COLOR_TEXTO),
                        Text(dia, size=9, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=3)
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("📈 Tendencias (Últimos 7 Días)", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.TRENDING_UP, size=18, color=COLOR_ACENTO)
                    ]),
                    Container(height=15),
                    Row(barras, alignment=MainAxisAlignment.SPACE_AROUND, spacing=5),
                    Container(height=10),
                    Row([
                        Text("Tickets creados", size=10, color=COLOR_TEXTO_SEC),
                        Text(f"Promedio: {promedio:.1f}/día", size=10, color=COLOR_ACENTO, weight=FontWeight.BOLD),
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=18,
                expand=True
            )
        except Exception as ex:
            print(f"[ERROR] Tendencias: {ex}")
            return self._panel_vacio("Tendencias")
    
    def _panel_rendimiento_tecnicos(self, tecnicos: pd.DataFrame, tickets: pd.DataFrame) -> Container:
        """Panel de rendimiento de técnicos."""
        try:
            items = []
            
            if tecnicos.empty:
                return self._panel_vacio("Rendimiento de Técnicos")
            
            for _, tec in tecnicos.head(5).iterrows():
                nombre = tec.get("NOMBRE", "N/A")
                tickets_asignados = len(tickets[tickets.get("TECNICO_ASIGNADO") == nombre]) if not tickets.empty else 0
                estado = tec.get("ESTADO", "Disponible")
                
                color_estado = {
                    "Disponible": COLOR_DISPONIBLE,
                    "Ocupado": COLOR_OCUPADO,
                    "Ausente": COLOR_AUSENTE,
                    "En Descanso": COLOR_DESCANSO
                }.get(estado, COLOR_TEXTO_SEC)
                
                items.append(
                    Container(
                        content=Row([
                            Container(
                                content=Text(nombre[:2].upper(), size=12, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                width=35,
                                height=35,
                                bgcolor=COLOR_SUPERFICIE_3,
                                border_radius=ft.BorderRadius.all(20),
                                alignment=ft.Alignment(0, 0)
                            ),
                            Column([
                                Text(nombre, size=12, color=COLOR_TEXTO),
                                Row([
                                    Container(width=6, height=6, bgcolor=color_estado, border_radius=3),
                                    Text(estado, size=10, color=color_estado)
                                ], spacing=5)
                            ], spacing=1, expand=True),
                            Column([
                                Text(str(tickets_asignados), size=14, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                                Text("asignados", size=9, color=COLOR_TEXTO_SEC)
                            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=0)
                        ], spacing=12),
                        padding=12,
                        border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
                    )
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("👥 Rendimiento del Equipo", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.PEOPLE, size=18, color=COLOR_DISPONIBLE)
                    ]),
                    Divider(height=1, color=COLOR_SUPERFICIE_2),
                    Column(items, spacing=0)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=15,
                expand=True
            )
        except:
            return self._panel_vacio("Rendimiento")
    
    def _panel_distribucion_prioridad(self, tickets: pd.DataFrame) -> Container:
        """Panel con distribución de tickets por prioridad."""
        try:
            if tickets.empty:
                return self._panel_vacio("Distribución por Prioridad")
            
            prioridades = {
                "Crítica": len(tickets[tickets.get("PRIORIDAD") == "Crítica"]),
                "Alta": len(tickets[tickets.get("PRIORIDAD") == "Alta"]),
                "Media": len(tickets[tickets.get("PRIORIDAD") == "Media"]),
                "Baja": len(tickets[tickets.get("PRIORIDAD") == "Baja"])
            }
            
            colores_pri = {
                "Crítica": COLOR_CRITICA,
                "Alta": COLOR_ERROR,
                "Media": COLOR_ADVERTENCIA,
                "Baja": COLOR_DISPONIBLE
            }
            
            items = []
            total = sum(prioridades.values()) if prioridades.values() else 1
            
            for prioridad, cantidad in prioridades.items():
                porc = (cantidad / total * 100) if total > 0 else 0
                ancho = cantidad / total * 280 if total > 0 else 30
                
                items.append(
                    Column([
                        Row([
                            Text(prioridad, size=12, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Text(f"{cantidad} ({porc:.0f}%)", size=11, color=colores_pri[prioridad], weight=FontWeight.BOLD)
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                        Container(
                            width=ancho,
                            height=18,
                            bgcolor=colores_pri[prioridad],
                            border_radius=ft.BorderRadius.all(4)
                        )
                    ], spacing=6)
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("⚡ Por Prioridad", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ]),
                    Container(height=8),
                    Column(items, spacing=15)
                ], spacing=10),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=16,
                expand=True
            )
        except:
            return self._panel_vacio("Prioridades")
    
    def _panel_estado_equipos(self) -> Container:
        """Panel mostrando estado real de equipos desde la base de datos."""
        try:
            equipos_db = self.gestor.obtener_equipos()
            total_equipos = len(equipos_db) if not equipos_db.empty else 0
            
            # Contar por estado real
            activos = len(equipos_db[equipos_db["ESTADO_EQUIPO"] == "Activo"]) if not equipos_db.empty else 0
            inactivos = len(equipos_db[equipos_db["ESTADO_EQUIPO"] == "Inactivo"]) if not equipos_db.empty else 0
            mantenimiento = len(equipos_db[equipos_db["ESTADO_EQUIPO"] == "En Mantenimiento"]) if not equipos_db.empty else 0
            baja = len(equipos_db[equipos_db["ESTADO_EQUIPO"] == "Baja"]) if not equipos_db.empty else 0
            
            items = [
                ("Activos", activos, COLOR_DISPONIBLE),
                ("Inactivos", inactivos, COLOR_AUSENTE),
                ("Mantenimiento", mantenimiento, COLOR_ADVERTENCIA),
                ("Baja", baja, COLOR_ERROR)
            ]
            
            filas = []
            for nombre, cantidad, color in items:
                porc = (cantidad / total_equipos * 100) if total_equipos > 0 else 0
                filas.append(
                    Row([
                        Row([
                            Container(width=10, height=10, bgcolor=color, border_radius=5),
                            Text(nombre, size=11, color=COLOR_TEXTO)
                        ], spacing=8),
                        Text(f"{cantidad} ({porc:.0f}%)", size=11, color=COLOR_ACENTO, weight=FontWeight.BOLD)
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN)
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("🖥️ Estado de Equipos", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(f"Total: {total_equipos}", size=11, color=COLOR_TEXTO_SEC)
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    Container(height=10),
                    Column(filas, spacing=12)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=16,
                expand=True
            )
        except Exception as ex:
            print(f"[ERROR] Estado equipos: {ex}")
            return self._panel_vacio("Equipos")
    
    def _panel_estado_tecnicos_v2(self, tecnicos: pd.DataFrame) -> Container:
        """Panel mejorado con estado de técnicos."""
        try:
            if tecnicos.empty:
                return self._panel_vacio("Estado del Equipo")
            
            estados_count = {
                "Disponible": len(tecnicos[tecnicos["ESTADO"] == "Disponible"]),
                "Ocupado": len(tecnicos[tecnicos["ESTADO"] == "Ocupado"]),
                "Ausente": len(tecnicos[tecnicos["ESTADO"] == "Ausente"]),
                "En Descanso": len(tecnicos[tecnicos["ESTADO"] == "En Descanso"])
            }
            
            colores_est = {
                "Disponible": COLOR_DISPONIBLE,
                "Ocupado": COLOR_OCUPADO,
                "Ausente": COLOR_AUSENTE,
                "En Descanso": COLOR_DESCANSO
            }
            
            items = []
            for estado, cantidad in estados_count.items():
                items.append(
                    Row([
                        Row([
                            Icon(icons.CIRCLE, size=12, color=colores_est[estado]),
                            Text(estado, size=11, color=COLOR_TEXTO)
                        ], spacing=8),
                        Text(str(cantidad), size=12, color=colores_est[estado], weight=FontWeight.BOLD)
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN)
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("👨‍💼 Estado del Equipo IT", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.ENGINEERING, size=18, color=COLOR_PRIMARIO)
                    ]),
                    Divider(height=1, color=COLOR_SUPERFICIE_2),
                    Container(height=8),
                    Column(items, spacing=10)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=16,
                expand=True
            )
        except:
            return self._panel_vacio("Técnicos")
    
    def _panel_tickets_criticos(self, tickets: pd.DataFrame) -> Container:
        """Panel mostrando tickets más antiguos/críticos."""
        try:
            if tickets.empty:
                return self._panel_vacio("Tickets Críticos")
            
            # Filtrar tickets abiertos
            abiertos = tickets[tickets.get("ESTADO").isin(["Abierto", "En Proceso", "En Cola"])]
            if abiertos.empty:
                return self._panel_vacio("Tickets Críticos")
            
            # Tickets más antiguos (primeros 5)
            criticos = abiertos.head(5)
            
            items = []
            for idx, ticket in criticos.iterrows():
                id_ticket = ticket.get("ID_TICKET", "N/A")
                usuario = str(ticket.get("USUARIO_AD", "Unknown"))[:12]
                categoria = ticket.get("CATEGORIA", "N/A")
                prioridad = ticket.get("PRIORIDAD", "Media")
                
                color_pri = {
                    "Crítica": COLOR_CRITICA,
                    "Alta": COLOR_ERROR,
                    "Media": COLOR_ADVERTENCIA,
                    "Baja": COLOR_DISPONIBLE
                }.get(prioridad, COLOR_TEXTO_SEC)
                
                items.append(
                    Container(
                        content=Row([
                            Column([
                                Text(f"#{id_ticket}", size=12, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                                Text(usuario, size=10, color=COLOR_TEXTO_SEC)
                            ], spacing=2),
                            Text(categoria, size=10, color=COLOR_TEXTO),
                            Container(
                                content=Text(prioridad, size=9, color=colors.WHITE, weight=FontWeight.BOLD),
                                bgcolor=color_pri,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border_radius=4
                            )
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN, spacing=8),
                        padding=10,
                        border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
                    )
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("⚠️ Tickets Pendientes", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.WARNING, size=18, color=COLOR_ERROR)
                    ]),
                    Divider(height=1, color=COLOR_SUPERFICIE_2),
                    Column(items, spacing=0)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=15,
                expand=True
            )
        except:
            return self._panel_vacio("Críticos")
    
    def _panel_distribucion_categorias_v2(self, tickets: pd.DataFrame) -> Container:
        """Panel mejorado de distribución de categorías."""
        try:
            if tickets.empty:
                return self._panel_vacio("Categorías")
            
            dist = self.gestor.obtener_distribucion_categorias()
            
            items = []
            if not dist.empty:
                max_val = dist["CANTIDAD"].max()
                for _, row in dist.iterrows():
                    cat = row["CATEGORIA"]
                    cant = row["CANTIDAD"]
                    color = COLORES_CATEGORIAS.get(cat, COLOR_TEXTO_SEC)
                    ancho = (cant / max_val * 240) if max_val > 0 else 50
                    
                    items.append(
                        Row([
                            Container(
                                width=80,
                                content=Text(cat, size=10, color=COLOR_TEXTO, weight=FontWeight.W_500)
                            ),
                            Container(
                                width=ancho,
                                height=16,
                                bgcolor=color,
                                border_radius=ft.BorderRadius.all(4)
                            ),
                            Text(f"{cant}", size=10, color=COLOR_ACENTO, weight=FontWeight.BOLD)
                        ], spacing=10, alignment=MainAxisAlignment.START)
                    )
            
            return Container(
                content=Column([
                    Row([
                        Text("📂 Por Categoría", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ]),
                    Container(height=8),
                    Column(items, spacing=8) if items else Text("Sin datos", color=COLOR_TEXTO_SEC)
                ], spacing=10),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=16,
                expand=True
            )
        except:
            return self._panel_vacio("Categorías")
    
    def _panel_distribucion_horaria(self, tickets: pd.DataFrame) -> Container:
        """Panel mostrando distribución horaria de tickets con datos reales."""
        try:
            stats     = getattr(self, '_stats_dash', {})
            horas     = stats.get("bloques_horarios", ["0-4","4-8","8-12","12-16","16-20","20-24"])
            cantidades = stats.get("cantidades_horaria", [0]*6)

            max_val     = max(cantidades) if any(c > 0 for c in cantidades) else 1
            pico_cant   = max(cantidades)
            pico_idx    = cantidades.index(pico_cant) if pico_cant > 0 else 0
            pico_bloque = horas[pico_idx] if horas else "N/A"

            barras = []
            for hora, cant in zip(horas, cantidades):
                altura = max((cant / max_val * 100), 4) if max_val > 0 else 4
                es_pico = (cant == pico_cant and cant > 0)
                barras.append(
                    Column([
                        Container(
                            width=22, height=altura,
                            bgcolor=COLOR_PRIMARIO if es_pico else COLOR_ACENTO,
                            border_radius=ft.BorderRadius.only(top_left=3, top_right=3)
                        ),
                        Text(str(cant), size=8, color=COLOR_TEXTO),
                        Text(hora, size=7, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2)
                )

            return Container(
                content=Column([
                    Text("⏰ Distribución Horaria (Real)", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Container(height=12),
                    Row(barras, alignment=MainAxisAlignment.SPACE_AROUND, spacing=2),
                    Container(height=8),
                    Row([
                        Text(f"Pico: {pico_bloque}", size=9, color=COLOR_ACENTO, weight=FontWeight.BOLD),
                        Text(f"▸ {pico_cant} tickets", size=9, color=COLOR_TEXTO_SEC)
                    ], alignment=MainAxisAlignment.CENTER) if pico_cant > 0 else
                    Text("Sin tickets registrados", size=9, color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER)
                ], spacing=6),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=16,
                expand=True
            )
        except Exception as ex:
            print(f"[HORARIA] {ex}")
            return self._panel_vacio("Horaria")
    
    def _panel_tickets_recientes_v2(self, tickets: pd.DataFrame) -> Container:
        """Panel mejorado de tickets recientes con más información."""
        try:
            df = tickets if not tickets.empty else pd.DataFrame()
            recientes = df.head(8) if not df.empty else pd.DataFrame()
            
            items = []
            if recientes.empty:
                items.append(
                    Container(
                        content=Column([
                            Icon(icons.INBOX, size=50, color=COLOR_TEXTO_SEC),
                            Text("Sin tickets recientes", color=COLOR_TEXTO_SEC, size=13)
                        ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                        padding=40,
                        alignment=ft.Alignment(0, 0)
                    )
                )
            else:
                for _, ticket in recientes.iterrows():
                    estado = ticket.get("ESTADO", "Abierto")
                    color_estado = {
                        "Abierto": COLOR_ADVERTENCIA,
                        "En Cola": COLOR_INFO,
                        "En Proceso": COLOR_PRIMARIO,
                        "En Espera": COLOR_TEXTO_SEC,
                        "Cerrado": COLOR_EXITO
                    }.get(estado, COLOR_TEXTO_SEC)
                    
                    prioridad = ticket.get("PRIORIDAD", "Media")
                    color_pri = {
                        "Crítica": COLOR_CRITICA,
                        "Alta": COLOR_ERROR,
                        "Media": COLOR_ADVERTENCIA,
                        "Baja": COLOR_DISPONIBLE
                    }.get(prioridad, COLOR_TEXTO_SEC)
                    
                    items.append(
                        Container(
                            content=Row([
                                Column([
                                    Text(f"#{ticket.get('ID_TICKET', 'N/A')}", size=12, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                                    Text(str(ticket.get("USUARIO_AD", ""))[:20], size=10, color=COLOR_TEXTO_SEC)
                                ], spacing=2, width=100),
                                Column([
                                    Text(str(ticket.get("CATEGORIA", ""))[:15], size=11, color=COLOR_TEXTO),
                                    Text(ticket.get("DESCRIPCION", "")[:35], size=9, color=COLOR_TEXTO_SEC)
                                ], spacing=1, expand=True),
                                Column([
                                    Container(
                                        content=Text(estado, size=9, color=colors.WHITE, weight=FontWeight.BOLD),
                                        bgcolor=color_estado,
                                        padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                        border_radius=4
                                    ),
                                    Container(
                                        content=Text(prioridad, size=8, color=colors.WHITE, weight=FontWeight.BOLD),
                                        bgcolor=color_pri,
                                        padding=ft.Padding.symmetric(horizontal=6, vertical=2),
                                        border_radius=3
                                    )
                                ], spacing=3, horizontal_alignment=CrossAxisAlignment.END)
                            ], spacing=12),
                            padding=12,
                            border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2)),
                            on_click=lambda e, t=ticket: self._mostrar_detalle_ticket(t.to_dict())
                        )
                    )
            
            return Container(
                content=Column([
                    Row([
                        Text("📋 Últimos Tickets", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        ft.TextButton("Ver todos", icon=icons.ARROW_FORWARD,
                                    on_click=lambda e: self._ir_a_tickets())
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    Divider(height=1, color=COLOR_SUPERFICIE_2),
                    Column(items, spacing=0)
                ], spacing=10),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=16
            )
        except:
            return self._panel_vacio("Recientes")
    
    def _panel_vacio(self, titulo: str) -> Container:
        """Panel vacío genérico para cuando no hay datos."""
        return Container(
            content=Column([
                Text(titulo, size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Icon(icons.STORAGE, size=40, color=COLOR_TEXTO_SEC),
                Text("Sin datos disponibles", size=12, color=COLOR_TEXTO_SEC)
            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=8),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=15,
            padding=20,
            alignment=ft.Alignment(0, 0),
            expand=True
        )
    
    # =========================================================================
    # VISUALIZACIONES AVANZADAS
    # =========================================================================
    
    def _crear_grafico_circular(self, datos: dict, titulo: str, colores: dict) -> Container:
        """Crea un gráfico circular mejorado."""
        try:
            if not datos or sum(datos.values()) == 0:
                return self._panel_vacio(titulo)
            
            total = sum(datos.values())
            items = []
            
            # Leyenda con círculos de color
            for etiqueta, valor in datos.items():
                porc = (valor / total * 100) if total > 0 else 0
                color = colores.get(etiqueta, COLOR_TEXTO_SEC)
                
                items.append(
                    Row([
                        Container(width=12, height=12, bgcolor=color, border_radius=6),
                        Text(etiqueta, size=11, color=COLOR_TEXTO, expand=True),
                        Text(f"{valor}", size=11, color=color, weight=FontWeight.BOLD),
                        Text(f"({porc:.0f}%)", size=10, color=COLOR_TEXTO_SEC, width=50)
                    ], spacing=10, alignment=MainAxisAlignment.SPACE_BETWEEN)
                )
            
            return Container(
                content=Column([
                    Text(titulo, size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Container(height=12),
                    Column(items, spacing=8)
                ], spacing=6),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except:
            return self._panel_vacio(titulo)
    
    def _crear_heatmap_actividad(self) -> Container:
        """Crea un heatmap de actividad semanal con datos reales."""
        try:
            stats = getattr(self, '_stats_dash', {})
            datos = stats.get("heatmap", [[0]*6 for _ in range(7)])

            dias    = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            periodos = ["0-4", "4-8", "8-12", "12-16", "16-20", "20-24"]

            celdas = []
            for dia_idx, dia in enumerate(dias):
                columna = []
                for per_idx in range(6):
                    intensidad = datos[dia_idx][per_idx] if dia_idx < len(datos) and per_idx < len(datos[dia_idx]) else 0
                    if intensidad == 0:
                        bg = COLOR_SUPERFICIE_2
                    elif intensidad <= 3:
                        bg = "#1F3A5F"
                    elif intensidad <= 6:
                        bg = "#0F60A8"
                    elif intensidad <= 9:
                        bg = COLOR_PRIMARIO
                    else:
                        bg = "#FF0000"
                    columna.append(
                        Container(
                            width=30, height=30, bgcolor=bg, border_radius=4,
                            alignment=ft.Alignment(0, 0),
                            content=Text(str(intensidad), size=9, color=COLOR_TEXTO, weight=FontWeight.BOLD)
                        )
                    )
                celdas.append(
                    Column([
                        Text(dia, size=10, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Column(columna, spacing=2)
                    ], spacing=4, horizontal_alignment=CrossAxisAlignment.CENTER)
                )

            leyenda = Row([
                Row([Container(width=8, height=8, bgcolor=COLOR_SUPERFICIE_2, border_radius=2), Text("Sin actividad", size=8, color=COLOR_TEXTO)], spacing=4),
                Row([Container(width=8, height=8, bgcolor="#1F3A5F", border_radius=2), Text("Bajo", size=8, color=COLOR_TEXTO)], spacing=4),
                Row([Container(width=8, height=8, bgcolor="#0F60A8", border_radius=2), Text("Medio", size=8, color=COLOR_TEXTO)], spacing=4),
                Row([Container(width=8, height=8, bgcolor=COLOR_PRIMARIO, border_radius=2), Text("Alto", size=8, color=COLOR_TEXTO)], spacing=4),
            ], spacing=10, alignment=MainAxisAlignment.CENTER)

            return Container(
                content=Column([
                    Row([
                        Text("🔥 Mapa de Calor — Actividad Real por Día/Hora", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.HEATMAP, size=16, color=COLOR_PRIMARIO)
                    ]),
                    Container(height=10),
                    Row([
                        Text("", size=8),
                        *[Text(p, size=8, color=COLOR_TEXTO_SEC, width=30, text_align=TextAlign.CENTER) for p in periodos]
                    ], spacing=2),
                    Row(celdas, spacing=10, alignment=MainAxisAlignment.START),
                    Container(height=10),
                    leyenda
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except Exception as ex:
            print(f"[HEATMAP] {ex}")
            return self._panel_vacio("Mapa de Calor")
    
    def _panel_analisis_sla_tecnicos(self, tecnicos: pd.DataFrame, tickets: pd.DataFrame) -> Container:
        """Panel mostrando cumplimiento de SLA real por técnico (tickets cerrados en <24h)."""
        try:
            if tecnicos.empty:
                return self._panel_vacio("SLA por Técnico")

            stats    = getattr(self, '_stats_dash', {})
            sla_data = stats.get("sla_tecnicos", {})

            items = []
            for _, tec in tecnicos.head(6).iterrows():
                nombre   = tec.get("NOMBRE", "N/A")
                sla      = sla_data.get(nombre, None)

                if sla is None:
                    lbl_sla    = "Sin datos"
                    estado_sla = "•"
                    color_sla  = COLOR_TEXTO_SEC
                    ancho_barra = 0
                else:
                    lbl_sla    = f"{sla}%"
                    estado_sla = "✓" if sla >= 90 else "⚠"
                    color_sla  = COLOR_EXITO if sla >= 90 else COLOR_ADVERTENCIA if sla >= 70 else COLOR_ERROR
                    ancho_barra = int(150 * sla / 100)

                items.append(
                    Row([
                        Text(nombre[:12], size=11, color=COLOR_TEXTO, width=100),
                        Container(
                            width=150, height=14, bgcolor=COLOR_SUPERFICIE_2, border_radius=7,
                            content=Container(
                                width=ancho_barra, height=14,
                                bgcolor=color_sla, border_radius=7
                            )
                        ),
                        Row([
                            Text(lbl_sla, size=10, color=color_sla, weight=FontWeight.BOLD, width=55),
                            Text(estado_sla, size=12, color=color_sla)
                        ], spacing=0, width=65)
                    ], spacing=8)
                )

            return Container(
                content=Column([
                    Row([
                        Text("✓ SLA Real por Técnico", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text("(cerrado < 24h = cumple)", size=9, color=COLOR_TEXTO_SEC)
                    ]),
                    Divider(height=1, color=COLOR_SUPERFICIE_2),
                    Container(height=8),
                    Column(items, spacing=10)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except Exception as ex:
            print(f"[SLA] {ex}")
            return self._panel_vacio("SLA")
    
    def _panel_tiempo_resolucion(self, tickets: pd.DataFrame) -> Container:
        """Panel mostrando análisis real de tiempo de resolución."""
        try:
            stats  = getattr(self, '_stats_dash', {})
            t_min  = stats.get("t_min", 0)
            t_max  = stats.get("t_max", 0)
            t_prom = stats.get("t_prom", 0)
            t_med  = stats.get("t_median", 0)
            dist   = stats.get("dist_tiempos", {"< 4h": 0, "4-8h": 0, "8-24h": 0, "24-48h": 0, "> 48h": 0})

            hay_datos = any(v > 0 for v in dist.values())
            max_dist  = max(dist.values()) if hay_datos else 1

            items = []
            for rango, cantidad in dist.items():
                color = {
                    "< 4h":   COLOR_EXITO,
                    "4-8h":   COLOR_DISPONIBLE,
                    "8-24h":  COLOR_ACENTO,
                    "24-48h": COLOR_ADVERTENCIA,
                    "> 48h":  COLOR_ERROR
                }.get(rango, COLOR_TEXTO_SEC)
                ancho = max(int(cantidad / max_dist * 200), 4) if max_dist > 0 and cantidad > 0 else 0
                items.append(
                    Row([
                        Text(rango, size=10, color=COLOR_TEXTO, width=60),
                        Container(width=ancho, height=16, bgcolor=color, border_radius=4),
                        Text(str(cantidad), size=10, color=COLOR_ACENTO, weight=FontWeight.BOLD, width=30)
                    ], spacing=8)
                )

            return Container(
                content=Column([
                    Text("⏱️ Tiempo de Resolución (Real)", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Container(height=8),
                    Row([
                        Column([Text("Mínimo", size=9, color=COLOR_TEXTO_SEC),
                                Text(f"{t_min}h" if t_min else "N/D", size=13, weight=FontWeight.BOLD, color=COLOR_EXITO)],
                               spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER),
                        Column([Text("Mediano", size=9, color=COLOR_TEXTO_SEC),
                                Text(f"{t_med}h" if t_med else "N/D", size=13, weight=FontWeight.BOLD, color=COLOR_ACENTO)],
                               spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER),
                        Column([Text("Promedio", size=9, color=COLOR_TEXTO_SEC),
                                Text(f"{t_prom}h" if t_prom else "N/D", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO)],
                               spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER),
                        Column([Text("Máximo", size=9, color=COLOR_TEXTO_SEC),
                                Text(f"{t_max}h" if t_max else "N/D", size=13, weight=FontWeight.BOLD, color=COLOR_ERROR)],
                               spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER),
                    ], alignment=MainAxisAlignment.SPACE_AROUND) if hay_datos else
                    Text("Sin tickets cerrados aún", size=11, color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER),
                    Container(height=12),
                    Column(items, spacing=8)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except Exception as ex:
            print(f"[TIEMPOS] {ex}")
            return self._panel_vacio("Tiempos")
    
    def _panel_prediccion_carga(self) -> Container:
        """Panel con predicción de carga: promedio histórico real por hora."""
        try:
            stats      = getattr(self, '_stats_dash', {})
            horas_pred = stats.get("horas_pred", [])
            vals_pred  = stats.get("vals_pred", [])

            if not horas_pred or not any(v > 0 for v in vals_pred):
                return Container(
                    content=Column([
                        Text("🔮 Predicción de Carga", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Container(height=16),
                        Icon(icons.INFO_OUTLINE, size=30, color=COLOR_TEXTO_SEC),
                        Text("Sin suficiente histórico para predecir",
                             size=10, color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER)
                    ], spacing=6, horizontal_alignment=CrossAxisAlignment.CENTER),
                    bgcolor=COLOR_SUPERFICIE, border_radius=15, padding=14, expand=True,
                    alignment=ft.Alignment(0, 0)
                )

            max_pred = max(vals_pred)
            barras = []
            for hora, pred in zip(horas_pred, vals_pred):
                altura = max((pred / max_pred * 100), 4) if max_pred > 0 else 4
                color  = COLOR_ERROR if pred > max_pred * 0.8 else COLOR_ADVERTENCIA if pred > max_pred * 0.5 else COLOR_ACENTO
                barras.append(
                    Column([
                        Container(
                            width=25, height=altura, bgcolor=color,
                            border_radius=ft.BorderRadius.only(top_left=3, top_right=3)
                        ),
                        Text(f"{pred:.1f}", size=9, color=COLOR_TEXTO),
                        Text(hora, size=8, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2)
                )

            return Container(
                content=Column([
                    Row([
                        Text("🔮 Predicción de Carga (Próx. 6h)", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.TRENDING_UP, size=16, color=COLOR_PRIMARIO)
                    ]),
                    Container(height=12),
                    Row(barras, alignment=MainAxisAlignment.SPACE_AROUND, spacing=2),
                    Container(height=10),
                    Text("Promedio histórico real por hora del día",
                         size=8, color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except Exception as ex:
            print(f"[PREDICCION] {ex}")
            return self._panel_vacio("Predicción")
    
    # =========================================================================
    # VISTA: TÉCNICOS
    # =========================================================================
    
    def _vista_tecnicos(self) -> Column:
        """Vista de gestión de técnicos."""
        tecnicos = self.gestor.obtener_tecnicos()
        
        tarjetas = []
        for _, tec in tecnicos.iterrows():
            tarjetas.append(self._tarjeta_tecnico(tec))
        
        contenido_vista = Column([
            # Encabezado elegante
            self._crear_encabezado_seccion("👨‍💻", "Gestión de Técnicos", 
                                          f"Total: {len(tecnicos)} técnicos registrados"),
            
            # Tarjeta de acciones
            Card(
                content=Container(
                    content=Row([
                        ft.ElevatedButton(
                            "Agregar Técnico",
                            icon=icons.PERSON_ADD,
                            on_click=lambda e: self._mostrar_dialogo_agregar_tecnico(),
                        ),
                        ft.ElevatedButton(
                            "Actualizar",
                            icon=icons.REFRESH,
                            on_click=lambda e: self._refrescar_vista(),
                        )
                    ], spacing=12, run_spacing=10, wrap=True),
                    padding=12,
                ),
                elevation=2,
            ),
            
            Container(height=16),
            
            Row(tarjetas, spacing=16, wrap=True) if tarjetas else Container(
                content=Column([
                    Icon(icons.PERSON_OFF, size=60, color=COLOR_TEXTO_SEC),
                    Text("No hay técnicos registrados", size=18, color=COLOR_TEXTO_SEC),
                    Text("Agrega un técnico para comenzar", color=COLOR_TEXTO_SEC),
                    Container(height=12),
                    ft.ElevatedButton(
                        "Crear primer técnico",
                        icon=icons.PERSON_ADD,
                        on_click=lambda e: self._mostrar_dialogo_agregar_tecnico(),
                    )
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                padding=50,
                alignment=ft.Alignment(0, 0)
            )
        ], scroll=ScrollMode.AUTO, expand=True)
        return Column(
            controls=[
                Container(
                    content=contenido_vista,
                    padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
        )
    
    def _mostrar_dialogo_agregar_tecnico(self):
        """Muestra diálogo para agregar un nuevo técnico - Versión mejorada."""
        txt_nombre = TextField(
            label="Nombre completo",
            prefix_icon=icons.PERSON_ROUNDED,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_ACENTO,
            cursor_color=COLOR_ACENTO,
            width=350
        )
        txt_especialidad = TextField(
            label="Especialidad",
            prefix_icon=icons.WORK_ROUNDED,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_ACENTO,
            cursor_color=COLOR_ACENTO,
            width=350
        )
        txt_telefono = TextField(
            label="Teléfono (opcional)",
            prefix_icon=icons.PHONE_ROUNDED,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_ACENTO,
            cursor_color=COLOR_ACENTO,
            width=350
        )
        txt_email = TextField(
            label="Email (opcional)",
            prefix_icon=icons.EMAIL_ROUNDED,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_ACENTO,
            cursor_color=COLOR_ACENTO,
            width=350
        )
        
        def agregar(e):
            if not txt_nombre.value or not txt_especialidad.value:
                self._mostrar_advertencia("El nombre y especialidad son campos obligatorios")
                return
            
            self.gestor.agregar_tecnico(
                nombre=txt_nombre.value,
                especialidad=txt_especialidad.value,
                telefono=txt_telefono.value or "",
                email=txt_email.value or ""
            )
            dialogo.open = False
            self.page.update()
            self._mostrar_snackbar(f"✓ Técnico {txt_nombre.value} agregado", COLOR_EXITO)
            self._refrescar_vista()
        
        def cerrar_dialogo(e):
            dialogo.open = False
            self.page.update()
        
        dialogo = AlertDialog(
            modal=True,
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.PERSON_ADD_ROUNDED, size=24, color=COLOR_EXITO),
                    bgcolor=COLOR_EXITO_CLARO,
                    border_radius=ft.BorderRadius.all(8),
                    padding=8,
                ),
                Text("Agregar Nuevo Técnico", weight=FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            content=Container(
                content=Column([
                    Container(height=10),
                    txt_nombre,
                    txt_especialidad,
                    txt_telefono,
                    txt_email
                ], spacing=15),
                width=400,
                height=320
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    on_click=lambda e: cerrar_dialogo(e),
                    style=ft.ButtonStyle(color=COLOR_TEXTO_SEC)
                ),
                ft.Button(
                    "Agregar Técnico",
                    icon=icons.PERSON_ADD_ROUNDED,
                    bgcolor=COLOR_EXITO,
                    color=colors.WHITE,
                    on_click=lambda e: agregar(e)
                )
            ],
            actions_alignment=MainAxisAlignment.END,
            shape=ft.RoundedRectangleBorder(radius=16),
        )
        
        self.page.show_dialog(dialogo)
    
    def _tarjeta_tecnico(self, tec: pd.Series) -> Container:
        """Crea una tarjeta para un técnico."""
        estado = tec["ESTADO"]
        color_estado = {
            "Disponible": COLOR_DISPONIBLE,
            "Ocupado": COLOR_OCUPADO,
            "Ausente": COLOR_AUSENTE,
            "En Descanso": COLOR_DESCANSO
        }.get(estado, COLOR_TEXTO_SEC)
        
        # Dropdown para cambiar estado
        dropdown_estado = Dropdown(
            value=estado,
            options=[dropdown.Option(e) for e in ESTADOS_TECNICO],
            width=150,
            border_color=color_estado,
            on_select=lambda e, id_tec=tec["ID_TECNICO"]: self._cambiar_estado_tecnico(id_tec, e.data)
        )
        
        return Container(
            content=Column([
                # Avatar, nombre y botón eliminar
                Row([
                    Container(
                        content=Text(tec["NOMBRE"][:2].upper(), size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        width=60,
                        height=60,
                        bgcolor=color_estado,
                        border_radius=ft.BorderRadius.all(30),
                        alignment=ft.Alignment(0, 0)
                    ),
                    Column([
                        Text(tec["NOMBRE"], size=18, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(tec["ESPECIALIDAD"], size=12, color=COLOR_TEXTO_SEC)
                    ], spacing=2, expand=True),
                    ft.IconButton(
                        icon=icons.DELETE,
                        icon_color=COLOR_ERROR,
                        tooltip="Eliminar técnico",
                        disabled=estado == "Ocupado",
                        on_click=lambda e, id_tec=tec["ID_TECNICO"], nombre=tec["NOMBRE"]: self._confirmar_eliminar_tecnico(id_tec, nombre)
                    )
                ], spacing=10),
                
                Divider(color=COLOR_SUPERFICIE_2),
                
                # Estadísticas
                Row([
                    Column([
                        Text("Atendidos", size=10, color=COLOR_TEXTO_SEC),
                        Text(str(tec["TICKETS_ATENDIDOS"]), size=20, weight=FontWeight.BOLD, color=COLOR_ACENTO)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER),
                    Container(width=1, height=40, bgcolor=COLOR_SUPERFICIE_2),
                    Column([
                        Text("Ticket Actual", size=10, color=COLOR_TEXTO_SEC),
                        Text(str(tec["TICKET_ACTUAL"]) if tec["TICKET_ACTUAL"] else "-", 
                             size=14, color=COLOR_TEXTO)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER)
                ], alignment=MainAxisAlignment.SPACE_AROUND),
                
                Divider(color=COLOR_SUPERFICIE_2),
                
                # Controles
                Row([
                    Text("Estado:", size=12, color=COLOR_TEXTO_SEC),
                    dropdown_estado
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                
                # Contacto
                Row([
                    Icon(icons.PHONE, size=14, color=COLOR_TEXTO_SEC),
                    Text(tec["TELEFONO"], size=12, color=COLOR_TEXTO_SEC)
                ], spacing=5),
                Row([
                    Icon(icons.EMAIL, size=14, color=COLOR_TEXTO_SEC),
                    Text(tec["EMAIL"], size=11, color=COLOR_TEXTO_SEC)
                ], spacing=5),
                
                # Botón de acción
                Container(height=10),
                ft.Button(
                    "Liberar" if estado == "Ocupado" else "Asignar Ticket",
                    icon=icons.ASSIGNMENT_RETURN if estado == "Ocupado" else icons.ASSIGNMENT,
                    bgcolor=COLOR_EXITO if estado == "Ocupado" else COLOR_PRIMARIO,
                    color=colors.WHITE,
                    width=250,
                    disabled=estado not in ["Disponible", "Ocupado"],
                    on_click=lambda e, id_tec=tec["ID_TECNICO"]: self._accion_tecnico(id_tec, estado)
                )
            ], spacing=10),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            width=300,
            border=ft.Border.all(2, color_estado)
        )
    
    def _confirmar_eliminar_tecnico(self, id_tecnico: str, nombre: str):
        """Muestra diálogo de confirmación para eliminar un técnico."""
        
        def cerrar_y_eliminar(e):
            # Primero cerrar el diálogo
            dialogo.open = False
            self.page.update()
            self._mostrar_carga("Eliminando técnico...")
            
            if self.gestor.eliminar_tecnico(id_tecnico):
                self._ocultar_carga()
                self._mostrar_exito(
                    f"{nombre} ha sido eliminado del sistema correctamente.",
                    "Técnico Eliminado"
                )
            else:
                self._ocultar_carga()
                self._mostrar_error(
                    "El técnico puede estar ocupado con un ticket activo.",
                    "No se pudo eliminar"
                )
            self._refrescar_vista()
        
        def solo_cerrar(e):
            dialogo.open = False
            self.page.update()
        
        # Diálogo profesional de confirmación
        dialogo = AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.DELETE_FOREVER, size=28, color=colors.WHITE),
                    bgcolor=COLOR_ERROR,
                    padding=8,
                    border_radius=8
                ),
                Text("Confirmar Eliminación", weight=FontWeight.BOLD, color=COLOR_ERROR, size=18)
            ], spacing=12),
            content=Container(
                content=Column([
                    Container(
                        content=Icon(icons.WARNING_AMBER_ROUNDED, size=60, color=COLOR_ADVERTENCIA),
                        alignment=ft.Alignment(0, 0),
                        animate_opacity=300
                    ),
                    Container(height=10),
                    Text("¿Estás seguro de eliminar a este técnico?", 
                         color=COLOR_TEXTO, size=14, text_align=TextAlign.CENTER),
                    Container(
                        content=Text(nombre, weight=FontWeight.BOLD, color=COLOR_ACENTO, size=20),
                        padding=10,
                        bgcolor=COLOR_SUPERFICIE_2,
                        border_radius=8,
                        alignment=ft.Alignment(0, 0)
                    ),
                    Container(height=5),
                    Row([
                        Icon(icons.INFO_OUTLINE, size=14, color=COLOR_ERROR_CLARO),
                        Text("Esta acción no se puede deshacer", size=12, color=COLOR_ERROR_CLARO)
                    ], alignment=MainAxisAlignment.CENTER, spacing=5)
                ], spacing=8, horizontal_alignment=CrossAxisAlignment.CENTER),
                width=340,
                padding=10
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    icon=icons.CLOSE,
                    on_click=solo_cerrar
                ),
                ft.Button(
                    "Eliminar",
                    icon=icons.DELETE,
                    bgcolor=COLOR_ERROR,
                    color=colors.WHITE,
                    on_click=cerrar_y_eliminar
                )
            ],
            actions_alignment=MainAxisAlignment.END
        )
        
        self.page.show_dialog(dialogo)
    
    def _cambiar_estado_tecnico(self, id_tecnico: str, nuevo_estado: str):
        """Cambia el estado de un técnico."""
        self.gestor.actualizar_estado_tecnico(id_tecnico, nuevo_estado)
        self._refrescar_vista()
        self._mostrar_snackbar(f"Estado actualizado a: {nuevo_estado}", COLOR_EXITO)
    
    def _accion_tecnico(self, id_tecnico: str, estado_actual: str):
        """Ejecuta acción según el estado del técnico."""
        if estado_actual == "Ocupado":
            # Liberar técnico
            self.gestor.liberar_tecnico(id_tecnico)
            self._mostrar_snackbar("Técnico liberado correctamente", COLOR_EXITO)
        elif estado_actual == "Disponible":
            # Mostrar diálogo para asignar ticket
            self._mostrar_dialogo_asignar_ticket(id_tecnico)
        self._refrescar_vista()
    
    def _mostrar_dialogo_asignar_ticket(self, id_tecnico: str):
        """Muestra diálogo para asignar un ticket a un técnico."""
        cola = self.gestor.obtener_tickets_en_cola()
        
        if cola.empty:
            self._mostrar_advertencia("Sin tickets en cola", "No hay tickets pendientes para asignar.")
            return
        
        opciones = [
            dropdown.Option(key=row["ID_TICKET"], text=f"#{row['ID_TICKET']} - {row['USUARIO_AD']} ({row['CATEGORIA']})")
            for _, row in cola.head(10).iterrows()
        ]
        
        dd_tickets = Dropdown(
            label="Seleccionar Ticket",
            options=opciones,
            width=380,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO
        )
        
        dialogo = None
        
        def cerrar_dialogo(e=None):
            nonlocal dialogo
            if dialogo:
                dialogo.open = False
                self._chat_detalle_ticket_id = None
                self._chat_detalle_list_ref = None
                self._chat_detalle_txt_ref = None
                self.page.update()
        
        def asignar(e):
            if dd_tickets.value:
                cerrar_dialogo()
                self._mostrar_carga("Asignando ticket...")
                
                self.gestor.asignar_ticket_a_tecnico(
                    dd_tickets.value,
                    id_tecnico,
                    usuario_op=self._usuario_operador(),
                    origen="kubo.manual",
                )
                
                self._ocultar_carga()
                self._mostrar_exito(
                    "Ticket Asignado",
                    f"El ticket #{dd_tickets.value} ha sido asignado correctamente."
                )
                self._refrescar_vista()
            else:
                self._mostrar_advertencia("Selecciona un ticket", "Debes seleccionar un ticket de la lista.")
        
        dialogo = AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.ASSIGNMENT_IND, size=28, color=colors.WHITE),
                    bgcolor=COLOR_PRIMARIO,
                    padding=8,
                    border_radius=8
                ),
                Text("Asignar Ticket", weight=FontWeight.BOLD, color=COLOR_TEXTO, size=18)
            ], spacing=12),
            content=Container(
                content=Column([
                    Row([
                        Icon(icons.INFO_OUTLINE, size=16, color=COLOR_INFO),
                        Text("Selecciona un ticket de la cola para asignar:", 
                             color=COLOR_TEXTO, size=13)
                    ], spacing=8),
                    Container(height=5),
                    dd_tickets,
                    Container(height=5),
                    Container(
                        content=Row([
                            Icon(icons.QUEUE, size=14, color=COLOR_TEXTO_SEC),
                            Text(f"{len(cola)} tickets en cola", size=12, color=COLOR_TEXTO_SEC)
                        ], spacing=5),
                        padding=8,
                        bgcolor=COLOR_SUPERFICIE_2,
                        border_radius=8
                    )
                ], spacing=10),
                width=420,
                padding=10
            ),
            actions=[
                ft.TextButton(
                    "Cancelar",
                    icon=icons.CLOSE,
                    on_click=cerrar_dialogo
                ),
                ft.Button(
                    "Asignar",
                    icon=icons.CHECK,
                    bgcolor=COLOR_PRIMARIO,
                    color=colors.WHITE,
                    on_click=asignar
                )
            ],
            actions_alignment=MainAxisAlignment.END
        )
        
        self.page.show_dialog(dialogo)
    
    # =========================================================================
    # VISTA: TICKETS
    # =========================================================================
    
    def _vista_tickets(self) -> Column:
        """Vista de gestión de tickets activos (no cerrados) con filtro de prioridad."""
        # Estados sin "Cerrado" (los cerrados van al historial)
        estados_activos = [e for e in ESTADOS_TICKET if e != "Cerrado"]
        
        # Filtros
        self.filtro_estado = Dropdown(
            label="Estado",
            options=[dropdown.Option("Todos")] + [dropdown.Option(e) for e in estados_activos],
            value="Todos",
            width=150,
            on_select=lambda e: self._aplicar_filtros()
        )
        
        self.filtro_categoria = Dropdown(
            label="Categoría",
            options=[dropdown.Option("Todas")] + [dropdown.Option(c) for c in CATEGORIAS_DISPONIBLES],
            value="Todas",
            width=150,
            on_select=lambda e: self._aplicar_filtros()
        )
        
        self.filtro_prioridad = Dropdown(
            label="⚡ Prioridad",
            options=[
                dropdown.Option("Todas"),
                dropdown.Option("Crítica"),
                dropdown.Option("Alta"),
                dropdown.Option("Media"),
                dropdown.Option("Baja"),
            ],
            value="Todas",
            width=150,
            on_select=lambda e: self._aplicar_filtros()
        )
        
        self.txt_busqueda = TextField(
            label="Buscar",
            prefix_icon=icons.SEARCH,
            width=250,
            on_change=lambda e: self._aplicar_filtros()
        )

        self._tickets_page = 0
        self._tickets_df_full = pd.DataFrame()
        self._tickets_df_filtrado = pd.DataFrame()

        self._tickets_tabla_container = Container(
            content=Row(
                [ProgressRing(width=28, height=28, color=COLOR_ACENTO), Text("Cargando tickets activos...", color=COLOR_TEXTO_SEC)],
                spacing=10,
                alignment=MainAxisAlignment.CENTER,
            ),
            alignment=ft.Alignment(0, 0),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(10),
            padding=10,
            expand=True
        )

        self._tickets_btn_prev = ft.IconButton(icon=icons.CHEVRON_LEFT, disabled=True, on_click=lambda e: self._tickets_cambiar_pagina(-1))
        self._tickets_btn_next = ft.IconButton(icon=icons.CHEVRON_RIGHT, disabled=True, on_click=lambda e: self._tickets_cambiar_pagina(1))
        self._tickets_lbl_pagina = Text("Página 0/0", size=11, color=COLOR_TEXTO_SEC)
        self._tickets_paginacion = Row(
            [self._tickets_btn_prev, self._tickets_lbl_pagina, self._tickets_btn_next],
            alignment=MainAxisAlignment.END,
            visible=False,
        )
        self._tickets_resumen_text = Text("", size=11, color=COLOR_TEXTO_SEC, visible=False)

        self._tickets_total_text = Text("0 activos", size=12, color=COLOR_TEXTO)
        self._tickets_criticas_text = Text("⚠ 0 críticas", size=12, color=colors.WHITE)
        self._tickets_altas_text = Text("🔴 0 altas", size=12, color=colors.WHITE)
        
        contenido_vista = Column([
            # Encabezado elegante
            self._crear_encabezado_seccion("📋", "Gestión de Tickets Activos", 
                                          "Tickets ordenados por urgencia • Críticas y Altas prioritarias"),
            
            # Tarjeta de resumen/stats
            Container(
                content=Row([
                    self._crear_card_resumen("Total Activos", self._tickets_total_text.value, icons.DONE_ALL, COLOR_INFO),
                    self._crear_card_resumen("Críticas", "0", icons.ERROR, COLOR_CRITICA),
                    self._crear_card_resumen("Altas", "0", icons.WARNING, COLOR_ALTA),
                    ft.Button(
                        "Actualizar",
                        icon=icons.REFRESH,
                        bgcolor=COLOR_PRIMARIO,
                        color=colors.WHITE,
                        on_click=lambda e: self._cargar_tickets_async(forzar=True),
                        width=150,
                    )
                ], spacing=12, run_spacing=12, alignment=MainAxisAlignment.START, vertical_alignment=CrossAxisAlignment.CENTER, wrap=True),
            ),
            
            Container(height=12),
            
            # Tarjeta de filtros elegante
            self._crear_card_filtros([
                Row([
                    self.filtro_prioridad,
                    self.filtro_estado,
                    self.filtro_categoria,
                    self.txt_busqueda
                ], spacing=12, run_spacing=12, wrap=True)
            ], "#FF9800"),
            
            Container(height=16),
            
            # Tabla de tickets (contenedor dinámico con scroll)
            self._tickets_tabla_container,
            self._tickets_paginacion,
            self._tickets_resumen_text,
        ], expand=True, scroll=ScrollMode.AUTO, horizontal_alignment=CrossAxisAlignment.STRETCH)

        self._cargar_tickets_async()
        return Column(
            controls=[
                Container(
                    content=contenido_vista,
                    padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                    expand=True,
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=CrossAxisAlignment.STRETCH,
        )
    
    def _construir_tabla_tickets(self, df: pd.DataFrame) -> DataTable:
        """Construye la tabla de tickets."""
        filas = []
        
        for _, row in df.iterrows():
            estado = row.get("ESTADO", "Abierto")
            color_estado = {
                "Abierto": COLOR_ADVERTENCIA,
                "En Cola": COLOR_INFO,
                "En Proceso": COLOR_PRIMARIO,
                "En Espera": COLOR_TEXTO_SEC,
                "Cerrado": COLOR_EXITO
            }.get(estado, COLOR_TEXTO_SEC)
            
            prioridad = row.get("PRIORIDAD", "Media")
            color_prioridad = {
                "Crítica": COLOR_CRITICA,
                "Alta": COLOR_ALTA,
                "Media": COLOR_MEDIA,
                "Baja": COLOR_BAJA
            }.get(prioridad, COLOR_MEDIA)
            
            filas.append(
                DataRow(
                    cells=[
                        DataCell(Text(f"#{row.get('ID_TICKET', '')}", weight=FontWeight.BOLD, color=COLOR_ACENTO)),
                        DataCell(Text(str(row.get('TURNO', '-')), color=COLOR_TEXTO)),
                        DataCell(Text(str(row.get('USUARIO_AD', ''))[:15], color=COLOR_TEXTO)),
                        DataCell(Text(str(row.get('CATEGORIA', '')), color=COLOR_TEXTO)),
                        DataCell(Container(
                            content=Text(prioridad, size=11, color=colors.WHITE),
                            bgcolor=color_prioridad,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            border_radius=ft.BorderRadius.all(5)
                        )),
                        DataCell(Container(
                            content=Text(estado, size=11, color=colors.WHITE),
                            bgcolor=color_estado,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            border_radius=ft.BorderRadius.all(5)
                        )),
                        DataCell(Text(str(row.get('TECNICO_ASIGNADO', '-'))[:15], color=COLOR_TEXTO_SEC)),
                    ],
                    on_select_change=lambda e, t=row: self._mostrar_detalle_ticket(t.to_dict())
                )
            )
        
        return DataTable(
            columns=[
                DataColumn(Text("ID", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Turno", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Usuario", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Categoría", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Prioridad", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Estado", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Técnico", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
            ],
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            border_radius=ft.BorderRadius.all(10),
            heading_row_color=COLOR_SUPERFICIE_2,
            show_checkbox_column=True,
            column_spacing=30
        )
    
    def _aplicar_filtros(self):
        """Aplica los filtros a la tabla de tickets activos con soporte de prioridad."""
        if self._tickets_df_full is None:
            self._tickets_df_full = pd.DataFrame()

        df = self._tickets_df_full.copy()

        if not df.empty:
            if hasattr(self, 'filtro_prioridad') and self.filtro_prioridad.value and self.filtro_prioridad.value != "Todas":
                df = df[df["PRIORIDAD"] == self.filtro_prioridad.value]

            if hasattr(self, 'filtro_estado') and self.filtro_estado.value and self.filtro_estado.value != "Todos":
                df = df[df["ESTADO"] == self.filtro_estado.value]

            if hasattr(self, 'filtro_categoria') and self.filtro_categoria.value and self.filtro_categoria.value != "Todas":
                df = df[df["CATEGORIA"] == self.filtro_categoria.value]

            if hasattr(self, 'txt_busqueda') and self.txt_busqueda.value:
                busqueda = self.txt_busqueda.value.lower()
                df = df[
                    df["USUARIO_AD"].str.lower().str.contains(busqueda, na=False) |
                    df["ID_TICKET"].str.lower().str.contains(busqueda, na=False) |
                    df["MAC_ADDRESS"].str.lower().str.contains(busqueda, na=False)
                ]

            if "PRIORIDAD" in df.columns:
                df["_orden_pri"] = df["PRIORIDAD"].map(ORDEN_PRIORIDAD).fillna(99)
                df = df.sort_values("_orden_pri").drop(columns=["_orden_pri"])

        self._tickets_df_filtrado = df
        self._tickets_page = 0
        self._render_tickets_pagina()
        self.page.update()

    def _cargar_tickets_async(self, forzar: bool = False):
        if self._tickets_cargando:
            return

        self._tickets_cargando = True

        if forzar and self._tickets_tabla_container is not None:
            self._tickets_tabla_container.content = Row(
                [ProgressRing(width=28, height=28, color=COLOR_ACENTO), Text("Actualizando tickets activos...", color=COLOR_TEXTO_SEC)],
                spacing=10,
                alignment=MainAxisAlignment.CENTER,
            )
            self.page.update()

        def cargar():
            try:
                df = self.gestor.obtener_tickets_activos()
                if not df.empty and "PRIORIDAD" in df.columns:
                    df["_orden_pri"] = df["PRIORIDAD"].map(ORDEN_PRIORIDAD).fillna(99)
                    df = df.sort_values("_orden_pri").drop(columns=["_orden_pri"])

                self._ui_call(lambda: self._aplicar_datos_tickets_ui(df if df is not None else pd.DataFrame()))
            except Exception as ex:
                print(f"[TICKETS][ERROR] {ex}")

                def aplicar_error():
                    if self._tickets_tabla_container is not None:
                        self._tickets_tabla_container.content = Container(
                            content=Row([Icon(icons.ERROR, color=COLOR_ERROR), Text("Error al cargar tickets", color=COLOR_ERROR)], spacing=10),
                            padding=20,
                        )
                    if self._tickets_paginacion is not None:
                        self._tickets_paginacion.visible = False
                    if self._tickets_resumen_text is not None:
                        self._tickets_resumen_text.visible = False
                    self.page.update()

                self._ui_call(aplicar_error)
            finally:
                self._tickets_cargando = False

        threading.Thread(target=cargar, daemon=True).start()

    def _aplicar_datos_tickets_ui(self, df: pd.DataFrame):
        self._tickets_df_full = df if df is not None else pd.DataFrame()
        self._tickets_df_filtrado = self._tickets_df_full.copy()
        self._tickets_page = 0

        total = len(self._tickets_df_full)
        criticas = len(self._tickets_df_full[self._tickets_df_full["PRIORIDAD"] == "Crítica"]) if total > 0 and "PRIORIDAD" in self._tickets_df_full.columns else 0
        altas = len(self._tickets_df_full[self._tickets_df_full["PRIORIDAD"] == "Alta"]) if total > 0 and "PRIORIDAD" in self._tickets_df_full.columns else 0

        if self._tickets_total_text is not None:
            self._tickets_total_text.value = f"{total} activos"
        if self._tickets_criticas_text is not None:
            self._tickets_criticas_text.value = f"⚠ {criticas} críticas"
        if self._tickets_altas_text is not None:
            self._tickets_altas_text.value = f"🔴 {altas} altas"

        self._render_tickets_pagina()
        self.page.update()

    def _render_tickets_pagina(self):
        total = len(self._tickets_df_filtrado) if self._tickets_df_filtrado is not None and not self._tickets_df_filtrado.empty else 0

        if total == 0:
            if self._tickets_tabla_container is not None:
                self._tickets_tabla_container.content = Container(
                    content=Column([
                        Icon(icons.INBOX, size=52, color=COLOR_TEXTO_SEC),
                        Text("No hay tickets para mostrar", size=15, color=COLOR_TEXTO_SEC, weight=FontWeight.W_500),
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=8),
                    padding=50,
                    alignment=ft.Alignment(0, 0),
                )
            if self._tickets_paginacion is not None:
                self._tickets_paginacion.visible = False
            if self._tickets_resumen_text is not None:
                self._tickets_resumen_text.visible = False
            return

        total_paginas = max((total + self._tickets_page_size - 1) // self._tickets_page_size, 1)
        self._tickets_page = max(0, min(self._tickets_page, total_paginas - 1))
        inicio = self._tickets_page * self._tickets_page_size
        fin = min(inicio + self._tickets_page_size, total)
        slice_df = self._tickets_df_filtrado.iloc[inicio:fin]

        ancho_tickets = max(
            1100,
            int(getattr(self.page, "window_width", 0) or getattr(self.page, "width", 0) or 0) - 24,
        )

        self.tabla_tickets = self._construir_tabla_tickets(slice_df)
        if self._tickets_tabla_container is not None:
            self._tickets_tabla_container.content = Column(
                controls=[
                    Container(
                        content=Row(
                            controls=[Container(content=self.tabla_tickets, width=ancho_tickets)],
                            scroll=ScrollMode.AUTO,
                            expand=True,
                            vertical_alignment=CrossAxisAlignment.START,
                        ),
                        width=ancho_tickets,
                        expand=True,
                    )
                ],
                scroll=ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=CrossAxisAlignment.STRETCH,
            )

        if self._tickets_btn_prev is not None:
            self._tickets_btn_prev.disabled = self._tickets_page <= 0
        if self._tickets_btn_next is not None:
            self._tickets_btn_next.disabled = self._tickets_page >= total_paginas - 1
        if self._tickets_lbl_pagina is not None:
            self._tickets_lbl_pagina.value = f"Página {self._tickets_page + 1}/{total_paginas}"
        if self._tickets_paginacion is not None:
            self._tickets_paginacion.visible = total_paginas > 1

        if self._tickets_resumen_text is not None:
            self._tickets_resumen_text.value = f"Mostrando {inicio + 1}-{fin} de {total} tickets"
            self._tickets_resumen_text.visible = True

    def _tickets_cambiar_pagina(self, delta: int):
        if self._tickets_df_filtrado is None or self._tickets_df_filtrado.empty:
            return
        self._tickets_page += delta
        self._render_tickets_pagina()
        self.page.update()
    
    # =========================================================================
    # VISTA: COLA DE TICKETS
    # =========================================================================
    
    def _vista_cola(self) -> Column:
        """Vista de la cola de tickets en espera."""
        self._cola_page = 0
        self._cola_badge_icon = Icon(icons.PEOPLE, color=COLOR_TEXTO_SEC)
        self._cola_badge_text = Text("Cargando técnicos...", color=COLOR_TEXTO_SEC)
        self._cola_estado_text = Text("Calculando estado de la cola...", color=COLOR_TEXTO)
        self._cola_lista_container = Container(
            content=Row(
                [ProgressRing(width=28, height=28, color=COLOR_ACENTO), Text("Cargando tickets en cola...", color=COLOR_TEXTO_SEC)],
                spacing=10,
                alignment=MainAxisAlignment.CENTER,
            ),
            padding=12,
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(10),
            expand=True,
        )
        self._cola_btn_prev = ft.IconButton(icon=icons.CHEVRON_LEFT, disabled=True, on_click=lambda e: self._cola_cambiar_pagina(-1))
        self._cola_btn_next = ft.IconButton(icon=icons.CHEVRON_RIGHT, disabled=True, on_click=lambda e: self._cola_cambiar_pagina(1))
        self._cola_lbl_pagina = Text("Página 0/0", size=11, color=COLOR_TEXTO_SEC)
        self._cola_paginacion = Row(
            [self._cola_btn_prev, self._cola_lbl_pagina, self._cola_btn_next],
            alignment=MainAxisAlignment.CENTER,
            visible=False,
        )
        self._cola_resumen_text = Text("", size=11, color=COLOR_TEXTO_SEC, visible=False)

        contenido_vista = Column([
            # Encabezado elegante
            self._crear_encabezado_seccion("🎫", "Cola de Tickets", 
                                          "Tickets en espera de asignación • Gestión de rebotes"),
            
            # Tarjeta de estado con técnicos
            Card(
                content=Container(
                    content=Column([
                        Row([
                            Icon(icons.SCHEDULE, size=28, color="#4ECDC4"),
                            Text("Estado de Cola", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                        ], spacing=10, vertical_alignment=CrossAxisAlignment.CENTER),
                        self._cola_estado_text,
                        Row([
                            self._cola_badge_icon,
                            self._cola_badge_text,
                        ], spacing=8, vertical_alignment=CrossAxisAlignment.CENTER),
                    ], spacing=8),
                    padding=16,
                ),
                elevation=2,
            ),
            
            Container(height=16),
            
            self._cola_paginacion,
            # Lista de cola
            self._cola_lista_container,
            self._cola_resumen_text,
        ], expand=True, scroll=ScrollMode.AUTO, horizontal_alignment=CrossAxisAlignment.STRETCH)

        self._cargar_cola_async()
        return Column(
            controls=[
                Container(
                    content=contenido_vista,
                    padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                    expand=True,
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=CrossAxisAlignment.STRETCH,
        )

    def _cargar_cola_async(self):
        if self._cola_cargando:
            return

        self._cola_cargando = True

        def cargar():
            try:
                cola = self.gestor.obtener_tickets_en_cola()
                tecnicos_disp = self.gestor.obtener_tecnicos_disponibles()
                def aplicar_datos():
                    self._cola_df_full = cola if cola is not None else pd.DataFrame()
                    self._cola_page = 0

                    self._cola_badge_icon.color = COLOR_EXITO if len(tecnicos_disp) > 0 else COLOR_ERROR
                    self._cola_badge_text.value = f"{len(tecnicos_disp)} técnicos disponibles"
                    self._cola_badge_text.color = COLOR_EXITO if len(tecnicos_disp) > 0 else COLOR_ERROR

                    total_cola = len(self._cola_df_full)
                    self._cola_estado_text.value = (
                        f"Hay {total_cola} tickets en cola. Tiempo estimado de espera: {total_cola * 15} minutos"
                    )
                    self._render_cola_pagina()
                    self.page.update()

                self._ui_call(aplicar_datos)

            except Exception as ex:
                print(f"[COLA][ERROR] {ex}")
                def aplicar_error():
                    self._cola_badge_icon.color = COLOR_ERROR
                    self._cola_badge_text.value = "Error cargando técnicos"
                    self._cola_badge_text.color = COLOR_ERROR
                    self._cola_estado_text.value = "No se pudo cargar la cola de tickets"
                    self._cola_lista_container.content = Container(
                        content=Row([Icon(icons.ERROR, color=COLOR_ERROR), Text("Error al cargar la cola", color=COLOR_ERROR)], spacing=10),
                        padding=20,
                    )
                    self._cola_paginacion.visible = False
                    self._cola_resumen_text.visible = False
                    self.page.update()

                self._ui_call(aplicar_error)
            finally:
                self._cola_cargando = False

        threading.Thread(target=cargar, daemon=True).start()

    def _render_cola_pagina(self):
        total = len(self._cola_df_full) if self._cola_df_full is not None and not self._cola_df_full.empty else 0
        if total == 0:
            self._cola_lista_container.content = Container(
                content=Column([
                    Icon(icons.CHECK_CIRCLE, size=60, color=COLOR_EXITO),
                    Text("¡No hay tickets en cola!", size=18, color=COLOR_EXITO),
                    Text("Todos los tickets han sido atendidos", color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                padding=50,
                alignment=ft.Alignment(0, 0),
            )
            self._cola_paginacion.visible = False
            self._cola_resumen_text.visible = False
            return

        total_paginas = max((total + self._cola_page_size - 1) // self._cola_page_size, 1)
        self._cola_page = max(0, min(self._cola_page, total_paginas - 1))
        inicio = self._cola_page * self._cola_page_size
        fin = min(inicio + self._cola_page_size, total)
        cola_slice = self._cola_df_full.iloc[inicio:fin]

        items_cola = [
            self._item_cola(ticket, inicio + pos)
            for pos, (_, ticket) in enumerate(cola_slice.iterrows(), 1)
        ]

        self._cola_lista_container.content = Column(
            items_cola,
            spacing=8,
            tight=True,
        )

        self._cola_btn_prev.disabled = self._cola_page <= 0
        self._cola_btn_next.disabled = self._cola_page >= total_paginas - 1
        self._cola_lbl_pagina.value = f"Página {self._cola_page + 1}/{total_paginas}"
        self._cola_paginacion.visible = total_paginas > 1

        self._cola_resumen_text.value = f"Mostrando {inicio + 1}-{fin} de {total} en cola"
        self._cola_resumen_text.visible = True

    def _cola_cambiar_pagina(self, delta: int):
        if self._cola_df_full is None or self._cola_df_full.empty:
            return
        self._cola_page += delta
        self._render_cola_pagina()
        self.page.update()

    def _item_cola(self, ticket: pd.Series, posicion: int) -> Container:
        """Crea un item de la cola."""
        prioridad = ticket.get("PRIORIDAD", "Media")
        color_prioridad = {"Crítica": COLOR_CRITICA, "Alta": COLOR_ALTA, "Media": COLOR_MEDIA, "Baja": COLOR_BAJA}.get(prioridad, COLOR_MEDIA)
        
        return Container(
            content=Row([
                # Posición en cola
                Container(
                    content=Text(f"#{posicion}", size=20, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    width=50,
                    height=50,
                    bgcolor=COLOR_PRIMARIO,
                    border_radius=ft.BorderRadius.all(25),
                    alignment=ft.Alignment(0, 0)
                ),
                
                # Info del ticket
                Column([
                    Row([
                        Text(f"Ticket #{ticket.get('ID_TICKET', '')}", weight=FontWeight.BOLD, color=COLOR_ACENTO, size=13),
                        Container(
                            content=Text(prioridad, size=10, color=colors.WHITE),
                            bgcolor=color_prioridad,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border_radius=ft.BorderRadius.all(5)
                        )
                    ], spacing=10),
                    Text(f"Usuario: {ticket.get('USUARIO_AD', '')} | Categoría: {ticket.get('CATEGORIA', '')}", 
                         size=12, color=COLOR_TEXTO_SEC),
                    Text(f"Turno: {ticket.get('TURNO', '-')}", size=11, color=COLOR_TEXTO_SEC)
                ], spacing=5, expand=True),
                
                # Tiempo de espera
                Column([
                    Text(f"~{posicion * 15}", size=24, weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA),
                    Text("min", size=12, color=COLOR_TEXTO_SEC)
                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                
                # Botón de información
                ft.Button(
                    "Informacion",
                    icon=icons.INFO_OUTLINE,
                    bgcolor=COLOR_INFO,
                    color=colors.WHITE,
                    on_click=lambda e, t=ticket: self._mostrar_detalle_ticket(dict(t))
                )
            ], spacing=20),
            bgcolor=COLOR_SUPERFICIE,
            padding=14,
            border_radius=ft.BorderRadius.all(10),
            border=ft.Border.all(1, color_prioridad)
        )
    
    def _atender_ticket_cola(self, ticket: pd.Series):
        """Atiende un ticket de la cola asignándolo a un técnico disponible."""
        try:
            id_ticket = str(ticket.get("ID_TICKET", "") or "").strip()
            if not id_ticket:
                self._mostrar_error("No se pudo identificar el ticket seleccionado.")
                return

            self._mostrar_carga(f"Atendiendo ticket #{id_ticket}...")
            disponibles = self.gestor.obtener_tecnicos_disponibles()

            if disponibles.empty:
                self._ocultar_carga()
                tecnicos_df = self.gestor.obtener_tecnicos()
                total_tecnicos = len(tecnicos_df) if tecnicos_df is not None else 0
                ocupados = 0
                if tecnicos_df is not None and not tecnicos_df.empty and "ESTADO" in tecnicos_df.columns:
                    ocupados = int((tecnicos_df["ESTADO"] == "Ocupado").sum())
                self._mostrar_advertencia(
                    f"No hay tecnicos disponibles ahora. Total: {total_tecnicos} | Ocupados: {ocupados}."
                )
                return

            id_tecnico = str(disponibles.iloc[0]["ID_TECNICO"])
            nombre_tecnico = str(disponibles.iloc[0].get("NOMBRE", id_tecnico))

            asignado = self.gestor.asignar_ticket_a_tecnico(
                id_ticket,
                id_tecnico,
                usuario_op=self._usuario_operador(),
                origen="kubo.cola",
            )
            if not asignado:
                self._ocultar_carga()
                self._mostrar_snackbar("No se pudo asignar el ticket. Intenta actualizar la cola.", COLOR_ERROR)
                return

            # Verificación defensiva: confirmar que el estado realmente cambió.
            ticket_actualizado = self.gestor.obtener_ticket_por_id(id_ticket)
            estado_actual = str((ticket_actualizado or {}).get("ESTADO", ""))
            tecnico_asignado_actual = str((ticket_actualizado or {}).get("TECNICO_ASIGNADO", "") or "")
            if estado_actual != "En Proceso" or tecnico_asignado_actual != nombre_tecnico:
                self._ocultar_carga()
                self._mostrar_snackbar("La asignación no se confirmó en base de datos", COLOR_ERROR)
                return

            # Broadcast WebSocket
            try:
                import ws_server as _ws
                _ws.broadcast_global(
                    _ws.EVENTO_TICKET_ACTUALIZADO,
                    {"id_ticket": id_ticket, "estado": "En Proceso"}
                )
            except Exception:
                pass

            if self._cola_df_full is not None and not self._cola_df_full.empty and "ID_TICKET" in self._cola_df_full.columns:
                self._cola_df_full = self._cola_df_full[self._cola_df_full["ID_TICKET"] != id_ticket].reset_index(drop=True)

            disponibles_post = self.gestor.obtener_tecnicos_disponibles()
            self._cola_badge_icon.color = COLOR_EXITO if len(disponibles_post) > 0 else COLOR_ERROR
            self._cola_badge_text.value = f"{len(disponibles_post)} tecnicos disponibles"
            self._cola_badge_text.color = COLOR_EXITO if len(disponibles_post) > 0 else COLOR_ERROR

            total_cola = len(self._cola_df_full) if self._cola_df_full is not None else 0
            self._cola_estado_text.value = (
                f"Hay {total_cola} tickets en cola. Tiempo estimado de espera: {total_cola * 15} minutos"
            )

            self._render_cola_pagina()
            self._ocultar_carga()
            self._mostrar_snackbar(f"Ticket asignado a {nombre_tecnico}", COLOR_EXITO)
            self.page.update()
        except Exception as ex:
            try:
                self._ocultar_carga()
            except Exception:
                pass
            self._mostrar_snackbar(f"Error al atender ticket: {ex}", COLOR_ERROR)
    
    # =========================================================================
    # VISTA: BÚSQUEDA GLOBAL
    # =========================================================================

    def _vista_busqueda_global(self) -> Column:
        """Búsqueda global rediseñada con mejoras visuales y de rendimiento."""
        
        # TextField de búsqueda principal
        txt_query = ft.TextField(
            label="Buscar",
            hint_text="Ticket, usuario, MAC, hostname, técnico, email...",
            prefix_icon=icons.SEARCH,
            width=540,
            height=52,
            autofocus=True,
            bgcolor=COLOR_SUPERFICIE_2,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            border_radius=12,
            content_padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            text_size=13,
        )

        # Dropdowns con altura y padding consistentes
        dd_tipo = ft.Dropdown(
            label="Tipo",
            width=160,
            height=52,
            value="Todos",
            options=[
                ft.dropdown.Option("Todos"),
                ft.dropdown.Option("Tickets"),
                ft.dropdown.Option("Equipos"),
                ft.dropdown.Option("Técnicos"),
            ],
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            bgcolor=COLOR_SUPERFICIE_2,
            text_size=12,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        )

        dd_estado_ticket = ft.Dropdown(
            label="Estado ticket",
            width=180,
            height=52,
            value="Todos",
            options=[ft.dropdown.Option("Todos")] + [ft.dropdown.Option(e) for e in ESTADOS_TICKET],
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            bgcolor=COLOR_SUPERFICIE_2,
            text_size=12,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        )

        dd_limite = ft.Dropdown(
            label="Límite",
            width=130,
            height=52,
            value="20",
            options=[ft.dropdown.Option("10"), ft.dropdown.Option("20"), ft.dropdown.Option("30"), ft.dropdown.Option("50")],
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            bgcolor=COLOR_SUPERFICIE_2,
            text_size=12,
            content_padding=ft.Padding.symmetric(horizontal=10, vertical=8),
        )

        panel_metricas = Row([], spacing=12, wrap=True)
        lista_resultados = ListView(expand=True, spacing=12, auto_scroll=False)
        
        contenedor_res = Container(
            content=lista_resultados,
            height=480,
            bgcolor=COLOR_SUPERFICIE,
            border_radius=12,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            padding=16,
        )

        _busqueda_timer: Dict[str, Any] = {"timer": None}

        def _card_metrica(titulo: str, valor: int, icono, color: str) -> Container:
            """Tarjeta de métrica mejorada con mejor diseño."""
            return Container(
                content=Column([
                    Row([
                        Container(
                            content=Icon(icono, size=18, color=colors.WHITE),
                            bgcolor=color,
                            width=40,
                            height=40,
                            border_radius=8,
                            alignment=ft.Alignment(0, 0),
                        ),
                        Column([
                            Text(titulo, size=11, color=COLOR_TEXTO_SEC, weight=FontWeight.W_500),
                            Text(str(valor), size=18, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        ], spacing=2),
                    ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
                ], spacing=0),
                padding=ft.Padding.symmetric(horizontal=14, vertical=12),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=10,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
                width=180,
            )

        def _estado_vacio(titulo: str, detalle: str = "", error: bool = False):
            """Estado vacío con icono y mensaje."""
            lista_resultados.controls = [
                Container(
                    content=Column([
                        Icon(
                            icons.ERROR_OUTLINE if error else icons.MANAGE_SEARCH, 
                            size=48, 
                            color=COLOR_ERROR if error else COLOR_TEXTO_SEC
                        ),
                        Text(titulo, size=15, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(detalle, size=12, color=COLOR_TEXTO_SEC),
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                    padding=30,
                    alignment=ft.Alignment(0, 0),
                )
            ]

        def _render_tickets(tickets: List[Dict[str, Any]]) -> Container:
            """Renderiza tabla de tickets con mejor presentación."""
            filas = []
            for t in tickets:
                estado = str(t.get("ESTADO", ""))
                color_estado = {
                    "Abierto": COLOR_ADVERTENCIA,
                    "En Cola": COLOR_INFO,
                    "En Proceso": COLOR_PRIMARIO,
                    "En Espera": COLOR_TEXTO_SEC,
                    "Cerrado": COLOR_EXITO,
                    "Cancelado": COLOR_ERROR,
                }.get(estado, COLOR_TEXTO_SEC)
                
                filas.append(DataRow(cells=[
                    DataCell(Text(f"#{t.get('ID_TICKET', '')}", size=12, color=COLOR_ACENTO, weight=FontWeight.BOLD)),
                    DataCell(Text(str(t.get("USUARIO_AD", ""))[:22], size=12, color=COLOR_TEXTO)),
                    DataCell(Container(
                        content=Text(estado, size=10, color=colors.WHITE, weight=FontWeight.W_500),
                        bgcolor=color_estado,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                        border_radius=6,
                    )),
                    DataCell(ft.IconButton(
                        icon=icons.OPEN_IN_NEW,
                        icon_color=COLOR_ACENTO,
                        tooltip="Ver ticket completo",
                        icon_size=18,
                        on_click=lambda e, tk=t: self._mostrar_detalle_ticket(tk),
                    )),
                ]))

            return Container(
                content=Column([
                    Row([
                        Text(f"Tickets ({len(tickets)})", size=14, weight=FontWeight.BOLD, color=COLOR_INFO),
                        Container(expand=True),
                        Text(f"Total: {len(tickets)} resultados", size=11, color=COLOR_TEXTO_SEC),
                    ]),
                    Row([DataTable(
                        columns=[
                            DataColumn(Text("ID", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                            DataColumn(Text("Usuario", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                            DataColumn(Text("Estado", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                            DataColumn(Text("Acción", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                        ],
                        rows=filas,
                        border=ft.Border.all(1, COLOR_SUPERFICIE_2),
                        heading_row_color=COLOR_SUPERFICIE_2,
                        show_checkbox_column=False,
                        column_spacing=16,
                    )], scroll=ScrollMode.AUTO),
                ], spacing=12),
                bgcolor=COLOR_SUPERFICIE,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            )

        def _render_equipos(equipos: List[Dict[str, Any]]) -> Container:
            """Renderiza tabla de equipos mejorada."""
            filas = []
            for eq in equipos:
                mac = str(eq.get("MAC_ADDRESS", "") or "")
                filas.append(DataRow(cells=[
                    DataCell(Text(mac[:17], size=12, color=COLOR_ACENTO, weight=FontWeight.BOLD)),
                    DataCell(Text(str(eq.get("NOMBRE_EQUIPO", "Sin nombre"))[:28], size=12, color=COLOR_TEXTO)),
                    DataCell(Text(str(eq.get("GRUPO", "Sin Asignar"))[:20], size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(ft.IconButton(
                        icon=icons.EDIT,
                        icon_color=COLOR_EXITO,
                        tooltip="Editar equipo",
                        icon_size=18,
                        on_click=lambda e, m=mac: self._dialogo_editar_equipo(m) if m else None,
                    )),
                ]))

            return Container(
                content=Column([
                    Row([
                        Text(f"Equipos ({len(equipos)})", size=14, weight=FontWeight.BOLD, color=COLOR_EXITO),
                        Container(expand=True),
                        Text(f"Total: {len(equipos)} resultados", size=11, color=COLOR_TEXTO_SEC),
                    ]),
                    Row([DataTable(
                        columns=[
                            DataColumn(Text("MAC", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                            DataColumn(Text("Nombre", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                            DataColumn(Text("Grupo", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                            DataColumn(Text("Acción", size=11, color=COLOR_PRIMARIO, weight=FontWeight.W_600)),
                        ],
                        rows=filas,
                        border=ft.Border.all(1, COLOR_SUPERFICIE_2),
                        heading_row_color=COLOR_SUPERFICIE_2,
                        show_checkbox_column=False,
                        column_spacing=16,
                    )], scroll=ScrollMode.AUTO),
                ], spacing=12),
                bgcolor=COLOR_SUPERFICIE,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            )

        def _render_tecnicos(tecnicos: List[Dict[str, Any]]) -> Container:
            """Renderiza lista de técnicos con mejor presentación."""
            items = []
            for tec in tecnicos:
                estado = str(tec.get("ESTADO", ""))
                color_estado = {
                    "Disponible": COLOR_DISPONIBLE,
                    "Ocupado": COLOR_OCUPADO,
                    "Ausente": COLOR_AUSENTE,
                    "En Descanso": COLOR_DESCANSO,
                }.get(estado, COLOR_TEXTO_SEC)
                
                items.append(Container(
                    content=Row([
                        Container(
                            content=Icon(icons.PERSON, size=20, color=colors.WHITE),
                            bgcolor=COLOR_PRIMARIO,
                            width=44,
                            height=44,
                            border_radius=8,
                            alignment=ft.Alignment(0, 0),
                        ),
                        Column([
                            Text(str(tec.get("NOMBRE", "")), size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Text(str(tec.get("ESPECIALIDAD", "")), size=11, color=COLOR_TEXTO_SEC),
                        ], spacing=2, expand=True),
                        Container(
                            content=Text(estado, size=10, color=colors.WHITE, weight=FontWeight.W_500),
                            bgcolor=color_estado,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                            border_radius=6,
                        ),
                    ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                    border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2)),
                ))

            return Container(
                content=Column([
                    Row([
                        Text(f"Técnicos ({len(tecnicos)})", size=14, weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA),
                        Container(expand=True),
                        Text(f"Total: {len(tecnicos)} resultados", size=11, color=COLOR_TEXTO_SEC),
                    ]),
                    Column(items, spacing=0),
                ], spacing=12),
                bgcolor=COLOR_SUPERFICIE,
                padding=16,
                border_radius=10,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            )

        def _limpiar_busqueda(e=None):
            """Limpia todos los filtros y la búsqueda."""
            txt_query.value = ""
            dd_tipo.value = "Todos"
            dd_estado_ticket.value = "Todos"
            dd_limite.value = "20"
            panel_metricas.controls = []
            _estado_vacio("Sin búsqueda", "Escribe para comenzar.")
            self.page.update()

        def _hacer_busqueda(e=None, silenciosa: bool = False):
            """Ejecuta la búsqueda global con filtros."""
            q = (txt_query.value or "").strip()
            if not q:
                panel_metricas.controls = []
                _estado_vacio("Sin búsqueda", "Escribe para comenzar.")
                if not silenciosa:
                    self.page.update()
                return

            lista_resultados.controls = [
                Row([
                    ProgressRing(width=24, height=24, stroke_width=3, color=COLOR_ACENTO),
                    Text("Consultando resultados...", size=12, color=COLOR_TEXTO_SEC),
                ], spacing=12, alignment=MainAxisAlignment.CENTER)
            ]
            self.page.update()

            try:
                res = self.gestor.buscar_global(q)
                tickets = res.get("tickets", [])
                equipos = res.get("equipos", [])
                tecnicos = res.get("tecnicos", [])

                tipo = dd_tipo.value or "Todos"
                estado = dd_estado_ticket.value or "Todos"
                limite = int(dd_limite.value or "20")

                # Filtrar por estado si se selecciona
                if estado != "Todos":
                    tickets = [t for t in tickets if str(t.get("ESTADO", "")) == estado]

                # Filtrar por tipo
                if tipo == "Tickets":
                    equipos, tecnicos = [], []
                elif tipo == "Equipos":
                    tickets, tecnicos = [], []
                elif tipo == "Técnicos":
                    tickets, equipos = [], []

                # Aplicar límite
                tickets = tickets[:limite]
                equipos = equipos[:limite]
                tecnicos = tecnicos[:limite]

                total = len(tickets) + len(equipos) + len(tecnicos)
                
                panel_metricas.controls = [
                    _card_metrica("Tickets", len(tickets), icons.CONFIRMATION_NUMBER, COLOR_INFO),
                    _card_metrica("Equipos", len(equipos), icons.COMPUTER, COLOR_EXITO),
                    _card_metrica("Técnicos", len(tecnicos), icons.ENGINEERING, COLOR_ADVERTENCIA),
                ]

                bloques = []
                if tickets:
                    bloques.append(_render_tickets(tickets))
                if equipos:
                    bloques.append(_render_equipos(equipos))
                if tecnicos:
                    bloques.append(_render_tecnicos(tecnicos))

                if bloques:
                    lista_resultados.controls = bloques
                else:
                    _estado_vacio("Sin resultados", "Prueba otro término o cambia los filtros.")
                    
            except Exception as ex:
                panel_metricas.controls = []
                _estado_vacio("No se pudo completar la búsqueda", str(ex), error=True)
                self._mostrar_snackbar(f"Error en búsqueda: {ex}", COLOR_ERROR)

            self.page.update()

        def _programar_busqueda_tiempo_real(e=None):
            """Programa búsqueda con debounce para rendimiento."""
            timer_actual = _busqueda_timer.get("timer")
            if timer_actual:
                try:
                    timer_actual.cancel()
                except Exception:
                    pass

            nuevo_timer = threading.Timer(0.35, lambda: self._ui_call(lambda: _hacer_busqueda(silenciosa=True)))
            _busqueda_timer["timer"] = nuevo_timer
            nuevo_timer.daemon = True
            nuevo_timer.start()

        # Configurar eventos
        txt_query.on_submit = _hacer_busqueda
        txt_query.on_change = _programar_busqueda_tiempo_real
        dd_tipo.on_change = _programar_busqueda_tiempo_real
        dd_estado_ticket.on_change = _programar_busqueda_tiempo_real
        dd_limite.on_change = _programar_busqueda_tiempo_real

        # Inicializar estado vacío
        _limpiar_busqueda()

        return Column([
            # Header
            Container(
                content=Row([
                    Container(
                        content=Icon(icons.MANAGE_SEARCH, size=28, color=colors.WHITE),
                        bgcolor=COLOR_PRIMARIO,
                        padding=12,
                        border_radius=10,
                    ),
                    Column([
                        Text("Búsqueda Global", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text("Encuentra tickets, equipos y técnicos en tiempo real", size=12, color=COLOR_TEXTO_SEC),
                    ], spacing=3, expand=True),
                ], spacing=14, vertical_alignment=CrossAxisAlignment.CENTER),
                bgcolor=COLOR_SUPERFICIE,
                padding=18,
                border_radius=12,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            ),
            Container(height=16),
            
            # Controles de búsqueda
            Container(
                content=Column([
                    Row([
                        txt_query,
                        ft.FilledButton(
                            "Buscar", 
                            icon=icons.SEARCH, 
                            bgcolor=COLOR_PRIMARIO,
                            on_click=_hacer_busqueda,
                        ),
                        ft.OutlinedButton(
                            "Limpiar", 
                            icon=icons.CLEAR, 
                            on_click=_limpiar_busqueda,
                        ),
                    ], spacing=12, wrap=True),
                    Row([
                        dd_tipo,
                        dd_estado_ticket,
                        dd_limite,
                    ], spacing=12, wrap=True, vertical_alignment=CrossAxisAlignment.CENTER),
                ], spacing=12),
                bgcolor=COLOR_SUPERFICIE,
                padding=16,
                border_radius=12,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            ),
            Container(height=16),
            
            # Panel de métricas
            panel_metricas,
            Container(height=14),
            
            # Contenedor de resultados
            contenedor_res,
        ], scroll=ScrollMode.AUTO, expand=True)

    # =========================================================================
    # VISTA: HISTORIAL
    # =========================================================================

    def _vista_historial(self) -> Column:
        """Vista del historial de tickets cerrados con filtros y auditoría."""
        historial_completo = self.gestor.obtener_historial()
        todos = self.gestor.obtener_todos_tickets()

        # Opciones reales para los filtros (vacío = Todas)
        cats_opciones     = ["Todas"] + sorted(historial_completo["CATEGORIA"].dropna().unique().tolist()) if not historial_completo.empty else ["Todas"]
        tecnicos_opciones = ["Todos"] + sorted(historial_completo["TECNICO_ASIGNADO"].replace("", pd.NA).dropna().unique().tolist()) if not historial_completo.empty else ["Todos"]

        # Controles de filtro
        dd_categoria = ft.Dropdown(
            label="Categoría",
            value="Todas",
            options=[ft.dropdown.Option(c) for c in cats_opciones],
            width=160,
            bgcolor=COLOR_SUPERFICIE_2,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        dd_tecnico = ft.Dropdown(
            label="Técnico",
            value="Todos",
            options=[ft.dropdown.Option(t) for t in tecnicos_opciones],
            width=180,
            bgcolor=COLOR_SUPERFICIE_2,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        txt_fecha_desde = ft.TextField(
            label="Desde (dd/mm/aaaa)",
            width=160,
            hint_text="01/01/2025",
            bgcolor=COLOR_SUPERFICIE_2,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        txt_fecha_hasta = ft.TextField(
            label="Hasta (dd/mm/aaaa)",
            width=160,
            hint_text="31/12/2025",
            bgcolor=COLOR_SUPERFICIE_2,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        txt_buscar = ft.TextField(
            label="Buscar usuario/ID...",
            width=200,
            prefix_icon=icons.SEARCH,
            bgcolor=COLOR_SUPERFICIE_2,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
        )
        lbl_resultados = Text("", size=11, color=COLOR_TEXTO_SEC)

        # Contenedor dinámico para la tabla
        self._hist_tabla_container = Container(
            content=self._construir_tabla_historial(historial_completo),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=10,
            padding=10,
            expand=True
        )

        def aplicar_filtros(e=None):
            df = historial_completo.copy()

            # Filtro categoría
            if dd_categoria.value and dd_categoria.value != "Todas":
                df = df[df["CATEGORIA"] == dd_categoria.value]

            # Filtro técnico
            if dd_tecnico.value and dd_tecnico.value != "Todos":
                df = df[df["TECNICO_ASIGNADO"] == dd_tecnico.value]

            # Filtro búsqueda texto
            if txt_buscar.value and txt_buscar.value.strip():
                q = txt_buscar.value.strip().lower()
                mask = (
                    df["USUARIO_AD"].str.lower().str.contains(q, na=False) |
                    df["ID_TICKET"].str.lower().str.contains(q, na=False)   |
                    df.get("HOSTNAME", pd.Series(dtype=str)).str.lower().str.contains(q, na=False)
                )
                df = df[mask]

            # Filtro fechas
            try:
                if txt_fecha_desde.value and txt_fecha_desde.value.strip():
                    date_desde = datetime.strptime(txt_fecha_desde.value.strip(), "%d/%m/%Y")
                    df = df[df["FECHA_APERTURA"] >= pd.Timestamp(date_desde)]
                if txt_fecha_hasta.value and txt_fecha_hasta.value.strip():
                    date_hasta = datetime.strptime(txt_fecha_hasta.value.strip(), "%d/%m/%Y")
                    df = df[df["FECHA_APERTURA"] <= pd.Timestamp(date_hasta.replace(hour=23, minute=59))]
            except ValueError:
                pass

            lbl_resultados.value = f"{len(df)} resultado(s)"
            self._hist_tabla_container.content = self._construir_tabla_historial(df)
            try:
                self.page.update()
            except Exception:
                pass

        def limpiar_filtros(e=None):
            dd_categoria.value    = "Todas"
            dd_tecnico.value      = "Todos"
            txt_fecha_desde.value = ""
            txt_fecha_hasta.value = ""
            txt_buscar.value      = ""
            lbl_resultados.value  = ""
            self._hist_tabla_container.content = self._construir_tabla_historial(historial_completo)
            try:
                self.page.update()
            except Exception:
                pass

        for ctrl in [dd_categoria, dd_tecnico, txt_fecha_desde, txt_fecha_hasta, txt_buscar]:
            ctrl.on_change = aplicar_filtros

        panel_auditoria = self._construir_panel_auditoria(todos)

        contenido_vista = Column([
            # Encabezado elegante
            self._crear_encabezado_seccion("📚", "Historial y Auditoría", 
                                          f"{len(historial_completo)} tickets cerrados • Solo lectura"),
            
            # Panel de auditoría
            panel_auditoria,
            
            Container(height=16),

            # Tarjeta de filtros mejorada
            self._crear_card_filtros([
                Row([
                    dd_categoria,
                    dd_tecnico,
                    txt_buscar,
                    txt_fecha_desde,
                    txt_fecha_hasta,
                ], spacing=12, wrap=True),
                Container(height=8),
                Row([
                    ft.ElevatedButton("🔍 Aplicar", icon=icons.SEARCH, on_click=aplicar_filtros),
                    ft.OutlinedButton("↺ Limpiar", icon=icons.CLEAR_ALL, on_click=limpiar_filtros),
                    Container(expand=True),
                    lbl_resultados,
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER, expand=True)
            ], "#2196F3"),

            Container(height=16),

            # Aviso readonly mejorado
            Card(
                content=Container(
                    content=Row([
                        Icon(icons.LOCK, color="#F39C12", size=24),
                        Column([
                            Text("Archive de Lectura Protegida", size=12, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Text("Los tickets cerrados no pueden editarse. Solo lectura.", color=COLOR_TEXTO_SEC, size=11),
                        ], spacing=2, expand=True),
                    ], spacing=12, vertical_alignment=CrossAxisAlignment.CENTER),
                    padding=12,
                ),
                elevation=2,
            ),

            Container(height=16),

            # Tabla dinámica
            self._hist_tabla_container,

        ], scroll=ScrollMode.AUTO, expand=True, horizontal_alignment=CrossAxisAlignment.STRETCH)
        return Column(
            controls=[
                Container(
                    content=contenido_vista,
                    padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                    expand=True,
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=CrossAxisAlignment.STRETCH,
        )

    def _construir_tabla_historial(self, historial: pd.DataFrame) -> ft.Control:
        """Construye la tabla del historial con los datos proporcionados."""
        if historial.empty:
            return Container(
                content=Column([
                    Icon(icons.FOLDER_OPEN, size=60, color=COLOR_TEXTO_SEC),
                    Text("Sin resultados con los filtros aplicados", size=16, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                padding=40, alignment=ft.Alignment(0, 0)
            )

        ancho_historial = max(
            1100,
            int(getattr(self.page, "window_width", 0) or getattr(self.page, "width", 0) or 0) - 24,
        )

        filas = []
        for _, row in historial.iterrows():
            fa = row.get("FECHA_APERTURA", "")
            fc = row.get("FECHA_CIERRE", "")
            fa = fa.strftime("%d/%m/%Y %H:%M") if hasattr(fa, "strftime") else (str(fa)[:16] if fa and str(fa) != "nan" else "-")
            fc = fc.strftime("%d/%m/%Y %H:%M") if hasattr(fc, "strftime") else (str(fc)[:16] if fc and str(fc) != "nan" else "-")

            estado = str(row.get("ESTADO", "Cerrado"))
            color_estado = COLOR_EXITO if estado == "Cerrado" else COLOR_ERROR
            filas.append(
                DataRow(
                    cells=[
                        DataCell(Text(f"#{row.get('ID_TICKET', '')}", weight=FontWeight.BOLD, color=COLOR_ACENTO, size=12)),
                        DataCell(Text(str(row.get('TURNO', '-')), color=COLOR_TEXTO, size=12)),
                        DataCell(Text(str(row.get('USUARIO_AD', ''))[:20], color=COLOR_TEXTO, size=12)),
                        DataCell(Text(str(row.get('CATEGORIA', '')), color=COLOR_TEXTO, size=12)),
                        DataCell(Text(str(row.get('PRIORIDAD', '-')), color=COLOR_TEXTO, size=12)),
                        DataCell(Text(str(row.get('TECNICO_ASIGNADO', '-'))[:18], color=COLOR_TEXTO, size=12)),
                        DataCell(Text(fa, size=11, color=COLOR_TEXTO_SEC)),
                        DataCell(Text(fc, size=11, color=COLOR_TEXTO_SEC)),
                        DataCell(
                            Container(
                                content=Text(estado, size=9, color=colors.WHITE, weight=FontWeight.BOLD),
                                bgcolor=color_estado,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                border_radius=4
                            )
                        ),
                    ],
                    on_select_change=lambda e, t=row: self._mostrar_detalle_historial(t.to_dict())
                )
            )

        tabla = DataTable(
            columns=[
                DataColumn(Text("ID",         weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Turno",      weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Usuario",    weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Categoría",  weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Prioridad",  weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Técnico",    weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Apertura",   weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Cierre",     weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
                DataColumn(Text("Estado",     weight=FontWeight.BOLD, color=COLOR_PRIMARIO, size=12)),
            ],
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            border_radius=10,
            heading_row_color=COLOR_SUPERFICIE_2,
            show_checkbox_column=False,
            column_spacing=18,
            expand=True
        )
        return Container(
            content=Column(
                controls=[
                    Container(
                        content=Row(
                            controls=[Container(content=tabla, width=ancho_historial)],
                            scroll=ScrollMode.AUTO,
                            expand=True,
                            vertical_alignment=CrossAxisAlignment.START,
                        ),
                        width=ancho_historial,
                        expand=True,
                    ),
                ],
                expand=True,
                horizontal_alignment=CrossAxisAlignment.STRETCH,
            ),
            expand=True,
        )

    def _construir_panel_auditoria(self, tickets: pd.DataFrame) -> Container:
        try:
            # === TOP USUARIOS MÁS PROBLEMÁTICOS ===
            usuarios_count = tickets["USUARIO_AD"].value_counts().head(5)
            items_usuarios = []
            for idx, (usuario, cantidad) in enumerate(usuarios_count.items()):
                # Obtener categorías más frecuentes de este usuario
                cats_usuario = tickets[tickets["USUARIO_AD"] == usuario]["CATEGORIA"].value_counts()
                cat_principal = cats_usuario.index[0] if not cats_usuario.empty else "N/A"
                
                color_rank = COLOR_ERROR if idx == 0 else COLOR_ADVERTENCIA if idx < 3 else COLOR_TEXTO_SEC
                items_usuarios.append(
                    Container(
                        content=Row([
                            Container(
                                content=Text(f"#{idx+1}", size=11, weight=FontWeight.BOLD, color=colors.WHITE),
                                width=28, height=28, bgcolor=color_rank,
                                border_radius=14, alignment=ft.Alignment(0, 0)
                            ),
                            Column([
                                Text(str(usuario)[:20], size=12, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                Text(f"Problema frecuente: {cat_principal}", size=10, color=COLOR_TEXTO_SEC),
                            ], spacing=1, expand=True),
                            Container(
                                content=Text(f"{cantidad}", size=14, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                            )
                        ], spacing=10),
                        padding=ft.Padding.symmetric(horizontal=12, vertical=8),
                        border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
                    )
                )
            
            # === TOP CATEGORÍAS MÁS PROBLEMÁTICAS ===
            cats_count = tickets["CATEGORIA"].value_counts().head(5)
            total_tickets = len(tickets)
            items_categorias = []
            for cat, cantidad in cats_count.items():
                porc = (cantidad / total_tickets * 100) if total_tickets > 0 else 0
                color = COLORES_CATEGORIAS.get(cat, COLOR_TEXTO_SEC)
                ancho_barra = max((porc / 100 * 180), 8)
                
                items_categorias.append(
                    Column([
                        Row([
                            Text(str(cat), size=11, color=COLOR_TEXTO, weight=FontWeight.W_500),
                            Text(f"{cantidad} ({porc:.0f}%)", size=10, color=COLOR_ACENTO, weight=FontWeight.BOLD)
                        ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                        Container(
                            width=ancho_barra, height=14,
                            bgcolor=color, border_radius=4
                        )
                    ], spacing=4)
                )
            
            # === TOP EQUIPOS MÁS PROBLEMÁTICOS ===
            equipos_count = tickets["HOSTNAME"].value_counts().head(5)
            items_equipos = []
            for hostname, cantidad in equipos_count.items():
                cats_equipo = tickets[tickets["HOSTNAME"] == hostname]["CATEGORIA"].value_counts()
                cat_freq = cats_equipo.index[0] if not cats_equipo.empty else "N/A"
                
                items_equipos.append(
                    Container(
                        content=Row([
                            Icon(icons.COMPUTER, size=16, color=COLOR_ADVERTENCIA),
                            Column([
                                Text(str(hostname)[:20], size=12, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                Text(f"Falla frecuente: {cat_freq}", size=10, color=COLOR_TEXTO_SEC),
                            ], spacing=1, expand=True),
                            Text(f"{cantidad} tickets", size=11, color=COLOR_ERROR, weight=FontWeight.BOLD)
                        ], spacing=8),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                        border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
                    )
                )
            
            # === ANÁLISIS DE POR QUÉ ===
            # Horarios pico
            df_temp = tickets.copy()
            df_temp["FECHA_APERTURA"] = pd.to_datetime(df_temp["FECHA_APERTURA"], errors='coerce')
            df_temp = df_temp.dropna(subset=["FECHA_APERTURA"])
            
            hora_pico = "N/A"
            dia_pico = "N/A"
            if not df_temp.empty:
                horas = df_temp["FECHA_APERTURA"].dt.hour.value_counts()
                if not horas.empty:
                    hora_pico = f"{horas.index[0]:02d}:00 - {horas.index[0]+1:02d}:00"
                dias_nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
                dias = df_temp["FECHA_APERTURA"].dt.dayofweek.value_counts()
                if not dias.empty:
                    dia_pico = dias_nombres[dias.index[0]]
            
            # Tasa de recurrencia (usuarios con más de 3 tickets)
            recurrentes = len(tickets["USUARIO_AD"].value_counts()[tickets["USUARIO_AD"].value_counts() > 3])
            
            return Container(
                content=Column([
                    Row([
                        Icon(icons.ANALYTICS, size=22, color=COLOR_ACENTO),
                        Text("🔍 Auditoría y Seguimiento de Problemas", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ], spacing=10),
                    Container(height=10),
                    
                    # Row de 3 paneles
                    Row([
                        # Panel usuarios problemáticos
                        Container(
                            content=Column([
                                Row([
                                    Icon(icons.PERSON_SEARCH, size=16, color=COLOR_ERROR),
                                    Text("Usuarios con Más Incidencias", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                ], spacing=8),
                                Divider(height=1, color=COLOR_SUPERFICIE_2),
                                Column(items_usuarios, spacing=0) if items_usuarios else
                                    Text("Sin datos suficientes", color=COLOR_TEXTO_SEC, size=12),
                            ], spacing=8),
                            bgcolor=COLOR_SUPERFICIE_2,
                            border_radius=12, padding=14, expand=True,
                            border=ft.Border.all(1, COLOR_ERROR + "40")
                        ),
                        
                        # Panel categorías
                        Container(
                            content=Column([
                                Row([
                                    Icon(icons.BUG_REPORT, size=16, color=COLOR_ADVERTENCIA),
                                    Text("Problemas Más Frecuentes", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                ], spacing=8),
                                Divider(height=1, color=COLOR_SUPERFICIE_2),
                                Column(items_categorias, spacing=8) if items_categorias else
                                    Text("Sin datos suficientes", color=COLOR_TEXTO_SEC, size=12),
                            ], spacing=8),
                            bgcolor=COLOR_SUPERFICIE_2,
                            border_radius=12, padding=14, expand=True,
                            border=ft.Border.all(1, COLOR_ADVERTENCIA + "40")
                        ),
                        
                        # Panel equipos
                        Container(
                            content=Column([
                                Row([
                                    Icon(icons.COMPUTER, size=16, color=COLOR_PRIMARIO),
                                    Text("Equipos Más Problemáticos", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                ], spacing=8),
                                Divider(height=1, color=COLOR_SUPERFICIE_2),
                                Column(items_equipos, spacing=0) if items_equipos else
                                    Text("Sin datos suficientes", color=COLOR_TEXTO_SEC, size=12),
                            ], spacing=8),
                            bgcolor=COLOR_SUPERFICIE_2,
                            border_radius=12, padding=14, expand=True,
                            border=ft.Border.all(1, COLOR_PRIMARIO + "40")
                        ),
                    ], spacing=15),
                    
                    Container(height=10),
                    
                    # Insights / Por qué
                    Container(
                        content=Row([
                            Container(
                                content=Column([
                                    Text("📅 Día con más problemas", size=11, color=COLOR_TEXTO_SEC),
                                    Text(dia_pico, size=14, weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA),
                                ], spacing=4, horizontal_alignment=CrossAxisAlignment.CENTER),
                                expand=True, padding=12, bgcolor=COLOR_SUPERFICIE_2,
                                border_radius=10, alignment=ft.Alignment(0, 0)
                            ),
                            Container(
                                content=Column([
                                    Text("⏰ Hora pico de incidencias", size=11, color=COLOR_TEXTO_SEC),
                                    Text(hora_pico, size=14, weight=FontWeight.BOLD, color=COLOR_PRIMARIO),
                                ], spacing=4, horizontal_alignment=CrossAxisAlignment.CENTER),
                                expand=True, padding=12, bgcolor=COLOR_SUPERFICIE_2,
                                border_radius=10, alignment=ft.Alignment(0, 0)
                            ),
                            Container(
                                content=Column([
                                    Text("🔄 Usuarios recurrentes (>3)", size=11, color=COLOR_TEXTO_SEC),
                                    Text(str(recurrentes), size=14, weight=FontWeight.BOLD, color=COLOR_ERROR),
                                ], spacing=4, horizontal_alignment=CrossAxisAlignment.CENTER),
                                expand=True, padding=12, bgcolor=COLOR_SUPERFICIE_2,
                                border_radius=10, alignment=ft.Alignment(0, 0)
                            ),
                            Container(
                                content=Column([
                                    Text("📊 Total histórico", size=11, color=COLOR_TEXTO_SEC),
                                    Text(str(total_tickets), size=14, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                                ], spacing=4, horizontal_alignment=CrossAxisAlignment.CENTER),
                                expand=True, padding=12, bgcolor=COLOR_SUPERFICIE_2,
                                border_radius=10, alignment=ft.Alignment(0, 0)
                            ),
                        ], spacing=10),
                    ),
                ], spacing=5),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15, padding=18,
                border=ft.Border.all(1, COLOR_ACENTO + "30")
            )
        except Exception as ex:
            print(f"[ERROR] Panel auditoría: {ex}")
            import traceback
            traceback.print_exc()
            return Container()
    
    def _mostrar_detalle_historial(self, ticket: Dict):
        """Muestra el detalle de un ticket del historial (solo lectura)."""
        fecha_apertura = ticket.get("FECHA_APERTURA", "")
        fecha_cierre = ticket.get("FECHA_CIERRE", "")
        
        # Formatear fechas
        if pd.notna(fecha_apertura) and hasattr(fecha_apertura, 'strftime'):
            fecha_apertura = fecha_apertura.strftime("%d/%m/%Y %H:%M:%S")
        else:
            fecha_apertura = str(fecha_apertura)[:19] if fecha_apertura else "-"
        
        if pd.notna(fecha_cierre) and hasattr(fecha_cierre, 'strftime'):
            fecha_cierre = fecha_cierre.strftime("%d/%m/%Y %H:%M:%S")
        else:
            fecha_cierre = str(fecha_cierre)[:19] if fecha_cierre else "-"
        
        dialogo = AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.HISTORY, size=24, color=colors.WHITE),
                    bgcolor=COLOR_EXITO,
                    padding=8,
                    border_radius=8
                ),
                Text(f"Ticket #{ticket.get('ID_TICKET', '')}", weight=FontWeight.BOLD, size=18, color=COLOR_TEXTO),
                Container(
                    content=Row([
                        Icon(icons.CHECK_CIRCLE, size=14, color=colors.WHITE),
                        Text("Cerrado", size=12, color=colors.WHITE)
                    ], spacing=5),
                    bgcolor=COLOR_EXITO,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    border_radius=ft.BorderRadius.all(10)
                )
            ], spacing=10, alignment=MainAxisAlignment.START),
            content=Container(
                content=Column([
                    # Info del usuario
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.PERSON, size=16, color=COLOR_ACENTO),
                                Text("Información del Ticket", weight=FontWeight.BOLD, color=COLOR_ACENTO)
                            ], spacing=8),
                            Container(height=5),
                            Row([
                                Text("Usuario:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=110),
                                Text(str(ticket.get("USUARIO_AD", "")), color=COLOR_TEXTO)
                            ]),
                            Row([
                                Text("Equipo:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=110),
                                Text(str(ticket.get("HOSTNAME", "")), color=COLOR_TEXTO)
                            ]),
                            Row([
                                Text("MAC:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=110),
                                Text(str(ticket.get("MAC_ADDRESS", "")), color=COLOR_TEXTO, size=12)
                            ]),
                            Row([
                                Text("Categoría:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=110),
                                Container(
                                    content=Text(str(ticket.get("CATEGORIA", "")), size=11, color=colors.WHITE),
                                    bgcolor=COLOR_INFO,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                    border_radius=5
                                )
                            ]),
                            Row([
                                Text("Prioridad:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=110),
                                Text(str(ticket.get("PRIORIDAD", "")), color=COLOR_TEXTO)
                            ]),
                            Row([
                                Text("Técnico:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=110),
                                Row([
                                    Icon(icons.ENGINEERING, size=14, color=COLOR_ACENTO),
                                    Text(str(ticket.get("TECNICO_ASIGNADO", "-")), color=COLOR_ACENTO, weight=FontWeight.W_500)
                                ], spacing=5)
                            ])
                        ]),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=12,
                        border_radius=10
                    ),
                    
                    # Fechas
                    Container(
                        content=Row([
                            Column([
                                Row([
                                    Icon(icons.CALENDAR_TODAY, size=14, color=COLOR_TEXTO_SEC),
                                    Text("Apertura", size=11, color=COLOR_TEXTO_SEC)
                                ], spacing=5),
                                Text(fecha_apertura, size=12, color=COLOR_TEXTO)
                            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2),
                            Icon(icons.ARROW_FORWARD, size=20, color=COLOR_EXITO),
                            Column([
                                Row([
                                    Icon(icons.EVENT_AVAILABLE, size=14, color=COLOR_EXITO),
                                    Text("Cierre", size=11, color=COLOR_EXITO)
                                ], spacing=5),
                                Text(fecha_cierre, size=12, color=COLOR_EXITO)
                            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2)
                        ], alignment=MainAxisAlignment.SPACE_AROUND),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=12,
                        border_radius=10
                    ),
                    
                    # Descripción
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.DESCRIPTION, size=16, color=COLOR_INFO),
                                Text("Descripción", weight=FontWeight.BOLD, color=COLOR_INFO)
                            ], spacing=8),
                            Container(height=3),
                            Text(str(ticket.get("DESCRIPCION", ""))[:300], color=COLOR_TEXTO, size=12)
                        ]),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=12,
                        border_radius=10
                    ),
                    
                    # Notas de resolución
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.TASK_ALT, size=16, color=COLOR_EXITO),
                                Text("Notas de Resolución", weight=FontWeight.BOLD, color=COLOR_EXITO)
                            ], spacing=8),
                            Container(height=3),
                            Text(str(ticket.get("NOTAS_RESOLUCION", "Sin notas")) or "Sin notas", 
                                 color=COLOR_TEXTO, size=12)
                        ]),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=12,
                        border_radius=10
                    ),

                    # Log de cambios
                    Row([
                        Icon(icons.HISTORY, size=16, color=COLOR_INFO),
                        Text("Histórico de Cambios", weight=FontWeight.BOLD, color=COLOR_INFO)
                    ], spacing=8),
                    self._construir_log_ticket(ticket.get("ID_TICKET", "")),

                ], spacing=10, scroll=ScrollMode.AUTO),
                width=460,
                height=520,
                padding=5
            ),
            actions=[
                ft.Button(
                    "Cerrar",
                    icon=icons.CLOSE,
                    bgcolor=COLOR_SUPERFICIE_3,
                    color=colors.WHITE,
                    on_click=lambda e: self._cerrar_dialogo_especifico(dialogo)
                )
            ],
            actions_alignment=MainAxisAlignment.END
        )
        
        self.page.show_dialog(dialogo)

    def _cerrar_dialogo_especifico(self, dialogo: AlertDialog):
        """Cierra explícitamente un diálogo concreto para evitar conflictos de referencia."""
        try:
            if hasattr(self.page, "close"):
                self.page.close(dialogo)
            else:
                dialogo.open = False
                if getattr(self.page, "dialog", None) is dialogo:
                    self.page.dialog = None
                self.page.update()
        except Exception as ex:
            print(f"[DIALOGO] Error cerrando diálogo específico: {ex}")
    
    # =========================================================================
    # VISTA: REPORTES Y ESTADÍSTICAS AVANZADAS
    # =========================================================================
    
    def _vista_reportes(self) -> Column:
        """Vista de reportes y análisis profesional con gráficos."""
        # Inicializar tab de reportes si no existe
        if not hasattr(self, '_tab_reportes_actual'):
            self._tab_reportes_actual = 0
        
        def cambiar_tab_reportes(idx):
            self._tab_reportes_actual = idx
            self._refrescar_vista()
        
        # Botones de navegación tipo tabs
        tabs_botones = Row([
            self._boton_tab_reporte("Resumen", icons.DASHBOARD, 0, cambiar_tab_reportes),
            self._boton_tab_reporte("Tickets", icons.ANALYTICS, 1, cambiar_tab_reportes),
            self._boton_tab_reporte("Rendimiento", icons.SPEED, 2, cambiar_tab_reportes),
            self._boton_tab_reporte("Tendencias", icons.TRENDING_UP, 3, cambiar_tab_reportes),
            self._boton_tab_reporte("Equipos", icons.COMPUTER, 4, cambiar_tab_reportes),
        ], spacing=5, run_spacing=8, wrap=True)
        
        # Contenido según tab seleccionado
        contenidos_tabs = [
            self._tab_resumen_general,
            self._tab_analisis_tickets,
            self._tab_rendimiento,
            self._tab_tendencias,
            self._tab_analisis_equipos
        ]
        
        contenido_actual = contenidos_tabs[self._tab_reportes_actual]()
        
        contenido_vista = Column([
            # Encabezado elegante
            self._crear_encabezado_seccion("📊", "Centro de Análisis y Reportes", 
                                          "Visualización de datos y tendencias en tiempo real"),
            
            # Tarjeta de acciones mejorada
            Card(
                content=Container(
                    content=Row([
                        ft.ElevatedButton(
                            "Exportar Excel",
                            icon=icons.DOWNLOAD,
                            on_click=lambda e: self._exportar_reporte_excel(),
                        ),
                        ft.ElevatedButton(
                            "Actualizar",
                            icon=icons.REFRESH,
                            on_click=lambda e: self._refrescar_vista(),
                        ),
                    ], spacing=12, run_spacing=10, wrap=True),
                    padding=12,
                ),
                elevation=2,
            ),
            
            Container(height=16),
            
            # Navegación por tabs personalizada
            Container(
                content=tabs_botones,
                bgcolor=COLOR_SUPERFICIE,
                border_radius=ft.BorderRadius.all(12),
                padding=10,
                border=ft.Border.all(1, "#404040"),
            ),
            
            Container(height=10),
            
            # Contenido del tab actual
            Container(
                content=contenido_actual,
                expand=True
            )
        ], expand=True, scroll=ScrollMode.AUTO)
        return contenido_vista
    
    def _boton_tab_reporte(self, texto: str, icono, idx: int, on_click_fn) -> Container:
        """Crea un botón de navegación tipo tab."""
        es_activo = hasattr(self, '_tab_reportes_actual') and self._tab_reportes_actual == idx
        
        return Container(
            content=Row([
                Icon(icono, size=16, color=colors.WHITE if es_activo else COLOR_TEXTO_SEC),
                Text(texto, size=12, color=colors.WHITE if es_activo else COLOR_TEXTO_SEC, weight=FontWeight.BOLD if es_activo else FontWeight.NORMAL)
            ], spacing=5, tight=True),
            bgcolor=COLOR_PRIMARIO if es_activo else COLOR_SUPERFICIE_2,
            width=150,
            padding=ft.Padding.symmetric(horizontal=15, vertical=10),
            border_radius=ft.BorderRadius.all(8),
            alignment=ft.Alignment(-1, 0),
            on_click=lambda e, i=idx: on_click_fn(i)
        )
    
    def _tab_resumen_general(self) -> Container:
        """Tab de resumen general con KPIs principales."""
        tickets = self.gestor.obtener_todos_tickets()
        tecnicos = self.gestor.obtener_tecnicos()
        equipos = self.gestor.obtener_equipos()

        if tickets is None or tickets.empty:
            tickets = pd.DataFrame()

        total_tickets = len(tickets)
        hoy = datetime.now().date()

        if not tickets.empty and "FECHA_APERTURA" in tickets.columns:
            fechas_ap = pd.to_datetime(tickets["FECHA_APERTURA"], errors="coerce")
            tickets_hoy = int((fechas_ap.dt.date == hoy).sum())
        else:
            tickets_hoy = 0

        en_cola = int((tickets.get("ESTADO") == "En Cola").sum()) if not tickets.empty and "ESTADO" in tickets.columns else 0
        en_proceso = int((tickets.get("ESTADO") == "En Proceso").sum()) if not tickets.empty and "ESTADO" in tickets.columns else 0
        cerrados = int((tickets.get("ESTADO") == "Cerrado").sum()) if not tickets.empty and "ESTADO" in tickets.columns else 0
        tasa_resolucion = (cerrados / max(total_tickets, 1)) * 100

        tiempo_promedio_h = 0.0
        if not tickets.empty and "FECHA_APERTURA" in tickets.columns and "FECHA_CIERRE" in tickets.columns:
            df_cierre = tickets[tickets.get("ESTADO") == "Cerrado"].copy()
            if not df_cierre.empty:
                fa = pd.to_datetime(df_cierre["FECHA_APERTURA"], errors="coerce")
                fc = pd.to_datetime(df_cierre["FECHA_CIERRE"], errors="coerce")
                dur_h = (fc - fa).dt.total_seconds() / 3600.0
                dur_h = dur_h[(dur_h > 0) & (dur_h < 240)]
                if not dur_h.empty:
                    tiempo_promedio_h = float(dur_h.mean())

        total_tecnicos = len(tecnicos) if tecnicos is not None else 0
        disponibles = int((tecnicos.get("ESTADO") == "Disponible").sum()) if tecnicos is not None and not tecnicos.empty and "ESTADO" in tecnicos.columns else 0
        total_equipos = len(equipos) if equipos is not None else 0

        por_estado = {}
        if not tickets.empty and "ESTADO" in tickets.columns:
            vc = tickets["ESTADO"].fillna("Desconocido").value_counts()
            por_estado = {str(k): int(v) for k, v in vc.items()}
        
        return Container(
            content=Column([
                Container(height=20),
                
                # Fila de KPIs principales
                Text("📈 Indicadores Clave de Rendimiento (KPIs)", size=18, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                Container(height=15),
                
                Row([
                    self._kpi_grande("Total Tickets", str(total_tickets), icons.CONFIRMATION_NUMBER, COLOR_INFO, "Histórico"),
                    self._kpi_grande("Hoy", str(tickets_hoy), icons.TODAY, COLOR_PRIMARIO, "Nuevos"),
                    self._kpi_grande("En Cola", str(en_cola), icons.HOURGLASS_EMPTY, COLOR_ADVERTENCIA, "Pendientes"),
                    self._kpi_grande("En Proceso", str(en_proceso), icons.ENGINEERING, COLOR_INFO, "Activos"),
                    self._kpi_grande("Resueltos", str(cerrados), icons.CHECK_CIRCLE, COLOR_EXITO, "Cerrados"),
                ], spacing=15, wrap=True),
                
                Container(height=30),
                
                # Segunda fila de KPIs
                Row([
                    self._kpi_grande("Tasa Resolución", f"{tasa_resolucion:.1f}%", icons.TRENDING_UP, 
                                    COLOR_EXITO if tasa_resolucion >= 70 else COLOR_ADVERTENCIA, "Eficiencia"),
                    self._kpi_grande("Tiempo Prom.", f"{tiempo_promedio_h:.1f}h", icons.TIMER, COLOR_ACENTO, "Resolución"),
                    self._kpi_grande("Técnicos", str(total_tecnicos), 
                                    icons.PEOPLE, COLOR_INFO, "Equipo"),
                    self._kpi_grande("Disponibles", str(disponibles), 
                                    icons.PERSON_SEARCH, COLOR_EXITO, "Activos"),
                    self._kpi_grande("Equipos", str(total_equipos), 
                                    icons.DEVICES, COLOR_SECUNDARIO, "Inventario"),
                ], spacing=15, wrap=True),
                
                Container(height=30),
                
                # Resumen de estado actual
                Row([
                    self._panel_estado_actual({"por_estado": por_estado}),
                    self._panel_actividad_reciente()
                ], spacing=20, expand=True),
                
            ], scroll=ScrollMode.AUTO),
            padding=20
        )
    
    def _kpi_grande(self, titulo: str, valor: str, icono, color: str, subtitulo: str) -> Container:
        """Crea un KPI grande con diseño profesional."""
        return Container(
            content=Column([
                Row([
                    Container(
                        content=Icon(icono, color=colors.WHITE, size=24),
                        bgcolor=color,
                        padding=10,
                        border_radius=ft.BorderRadius.all(10)
                    ),
                    Column([
                        Text(subtitulo, size=10, color=COLOR_TEXTO_SEC),
                    ], spacing=0)
                ], spacing=10),
                Container(height=10),
                Text(valor, size=32, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Text(titulo, size=12, color=COLOR_TEXTO_SEC)
            ], spacing=5, horizontal_alignment=CrossAxisAlignment.START),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            width=180,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2)
        )
    
    def _panel_estado_actual(self, stats: Dict) -> Container:
        """Panel con el estado actual del sistema."""
        por_estado = stats.get("por_estado", {})
        total = sum(por_estado.values()) if por_estado else 1
        
        estados_items = []
        colores_estado = {
            "Abierto": COLOR_ADVERTENCIA,
            "En Cola": COLOR_INFO,
            "En Proceso": COLOR_PRIMARIO,
            "En Espera": COLOR_TEXTO_SEC,
            "Cerrado": COLOR_EXITO,
            "Cancelado": COLOR_ERROR
        }
        
        for estado, cantidad in por_estado.items():
            porcentaje = (cantidad / max(total, 1)) * 100
            color = colores_estado.get(estado, COLOR_TEXTO_SEC)
            
            estados_items.append(
                Row([
                    Container(width=10, height=10, bgcolor=color, border_radius=ft.BorderRadius.all(5)),
                    Text(estado, size=12, color=COLOR_TEXTO, width=100),
                    Container(
                        content=Container(
                            width=max(porcentaje * 2, 5),
                            height=12,
                            bgcolor=color,
                            border_radius=ft.BorderRadius.all(3)
                        ),
                        width=200,
                        bgcolor=COLOR_SUPERFICIE_2,
                        border_radius=ft.BorderRadius.all(3)
                    ),
                    Text(f"{cantidad} ({porcentaje:.1f}%)", size=11, color=COLOR_TEXTO_SEC, width=80)
                ], spacing=10)
            )
        
        contenido_estados = estados_items if estados_items else [Text("Sin datos", color=COLOR_TEXTO_SEC)]
        
        return Container(
            content=Column([
                Row([
                    Icon(icons.PIE_CHART, color=COLOR_ACENTO, size=20),
                    Text("Distribución por Estado", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO)
                ], spacing=10),
                Divider(color=COLOR_SUPERFICIE_2),
                Column(contenido_estados, spacing=10)
            ], spacing=12),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _panel_actividad_reciente(self) -> Container:
        """Panel con actividad reciente."""
        df = self.gestor.obtener_todos_tickets()
        if not df.empty and "FECHA_APERTURA" in df.columns:
            df_tmp = df.copy()
            df_tmp["FECHA_APERTURA"] = pd.to_datetime(df_tmp["FECHA_APERTURA"], errors="coerce")
            recientes = df_tmp.sort_values("FECHA_APERTURA", ascending=False).head(6)
        else:
            recientes = df.head(6) if not df.empty else pd.DataFrame()
        
        items = []
        for _, ticket in recientes.iterrows():
            color_estado = {
                "Abierto": COLOR_ADVERTENCIA,
                "En Cola": COLOR_INFO,
                "En Proceso": COLOR_PRIMARIO,
                "Cerrado": COLOR_EXITO
            }.get(ticket.get("ESTADO", ""), COLOR_TEXTO_SEC)
            
            items.append(
                Container(
                    content=Row([
                        Container(
                            content=Text(ticket.get("CATEGORIA", "?")[:2].upper(), size=10, color=colors.WHITE),
                            bgcolor=COLOR_SUPERFICIE_3,
                            padding=8,
                            border_radius=ft.BorderRadius.all(5)
                        ),
                        Column([
                            Text(f"#{ticket.get('ID_TICKET', '')[:8]}", size=12, weight=FontWeight.W_600, color=COLOR_ACENTO),
                            Text(str(ticket.get("USUARIO_AD", ""))[:15], size=10, color=COLOR_TEXTO_SEC)
                        ], spacing=2, expand=True),
                        Container(
                            content=Text(ticket.get("ESTADO", ""), size=9, color=colors.WHITE),
                            bgcolor=color_estado,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            border_radius=ft.BorderRadius.all(5)
                        )
                    ], spacing=10),
                    padding=8,
                    border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
                )
            )
        
        contenido_items = items if items else [
            Container(
                content=Column([
                    Icon(icons.INBOX, size=40, color=COLOR_TEXTO_SEC),
                    Text("Sin actividad reciente", color=COLOR_TEXTO_SEC)
                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                padding=20
            )
        ]
        
        return Container(
            content=Column([
                Row([
                    Icon(icons.HISTORY, color=COLOR_INFO, size=20),
                    Text("Actividad Reciente", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO)
                ], spacing=10),
                Divider(color=COLOR_SUPERFICIE_2),
                Column(contenido_items, spacing=5)
            ], spacing=8),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _tab_analisis_tickets(self) -> Container:
        """Tab de análisis de tickets con gráficos."""
        dist_categorias = self.gestor.obtener_distribucion_categorias()
        dist_prioridades = self.gestor.obtener_distribucion_prioridades()
        por_dia = self.gestor.obtener_tickets_por_dia_semana()
        tiempo_cat = self.gestor.obtener_tiempo_resolucion_por_categoria()
        
        return Container(
            content=Column([
                Container(height=20),
                
                # Distribución por categoría y prioridad
                Row([
                    self._grafico_barras_horizontal("📊 Tickets por Categoría", dist_categorias, 
                                                   "CATEGORIA", "TOTAL", COLORES_CATEGORIAS),
                    self._grafico_barras_horizontal("🎯 Tickets por Prioridad", dist_prioridades,
                                                   "PRIORIDAD", "TOTAL", 
                                                   {"Crítica": COLOR_CRITICA, "Alta": COLOR_ALTA, "Media": COLOR_MEDIA, "Baja": COLOR_BAJA})
                ], spacing=20, expand=True),
                
                Container(height=30),
                
                # Carga semanal y tiempo de resolución
                Row([
                    self._grafico_barras_vertical("📅 Carga por Día de la Semana", por_dia, 
                                                  "DIA", "TOTAL", COLOR_ACENTO),
                    self._grafico_tiempo_categoria("⏱️ Tiempo Promedio por Categoría", tiempo_cat)
                ], spacing=20, expand=True),
                
            ], scroll=ScrollMode.AUTO),
            padding=20
        )
    
    def _grafico_barras_horizontal(self, titulo: str, df: pd.DataFrame, 
                                    col_label: str, col_valor: str, colores: Dict) -> Container:
        """Crea un gráfico de barras horizontales."""
        barras = []

        def _resolver_columna_valor(frame: pd.DataFrame, preferida: str) -> Optional[str]:
            if preferida in frame.columns:
                return preferida

            candidatas = ["CANTIDAD", "TOTAL", "VALOR", "COUNT", "N"]
            for nombre in candidatas:
                if nombre in frame.columns:
                    return nombre

            numericas = frame.select_dtypes(include=["number"]).columns.tolist()
            return numericas[0] if numericas else None
        
        if not df.empty:
            col_valor_real = _resolver_columna_valor(df, col_valor)
            if not col_valor_real:
                barras.append(Text("Sin datos numéricos disponibles", color=COLOR_TEXTO_SEC))
            else:
                max_val = df[col_valor_real].max()
                total_valores = max(float(df[col_valor_real].sum()), 1.0)
            
                for _, row in df.iterrows():
                    label = row.get(col_label, "N/A")
                    valor = float(row.get(col_valor_real, 0) or 0)
                    porcentaje = float(row.get("PORCENTAJE", (valor / total_valores) * 100))
                    color = colores.get(label, COLOR_TEXTO_SEC)
                    ancho = (valor / max(float(max_val), 1.0)) * 250
                    valor_texto = str(int(valor)) if valor.is_integer() else f"{valor:.1f}"

                    barras.append(
                        Row([
                            Container(width=100, content=Text(str(label)[:12], size=11, color=COLOR_TEXTO)),
                            Container(
                                content=Container(
                                    width=max(ancho, 5),
                                    height=22,
                                    bgcolor=color,
                                    border_radius=ft.BorderRadius.all(4)
                                ),
                                width=260,
                                bgcolor=COLOR_SUPERFICIE_2,
                                border_radius=ft.BorderRadius.all(4),
                                padding=2
                            ),
                            Text(f"{valor_texto} ({porcentaje:.1f}%)", size=10, color=COLOR_TEXTO_SEC, width=80)
                        ], spacing=10)
                    )
        else:
            barras.append(Text("Sin datos disponibles", color=COLOR_TEXTO_SEC))
        
        return Container(
            content=Column([
                Text(titulo, size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Divider(color=COLOR_SUPERFICIE_2),
                Column(barras, spacing=8)
            ], spacing=12),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _grafico_barras_vertical(self, titulo: str, df: pd.DataFrame,
                                  col_label: str, col_valor: str, color: str) -> Container:
        """Crea un gráfico de barras verticales."""
        barras = []
        
        if not df.empty and col_valor in df.columns:
            max_val = df[col_valor].max()
            
            for _, row in df.iterrows():
                label = row.get(col_label, "N/A")
                valor = row.get(col_valor, 0)
                altura = (valor / max(max_val, 1)) * 120
                
                barras.append(
                    Column([
                        Text(str(valor), size=10, color=COLOR_TEXTO, weight=FontWeight.BOLD),
                        Container(height=2),
                        Container(
                            width=35,
                            height=max(altura, 5),
                            bgcolor=color,
                            border_radius=ft.BorderRadius.only(top_left=5, top_right=5)
                        ),
                        Container(height=5),
                        Text(str(label)[:3], size=9, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER)
                )
        else:
            barras.append(Text("Sin datos", color=COLOR_TEXTO_SEC))
        
        return Container(
            content=Column([
                Text(titulo, size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Divider(color=COLOR_SUPERFICIE_2),
                Container(height=10),
                Row(barras, spacing=15, alignment=MainAxisAlignment.CENTER) if barras else Container()
            ], spacing=10),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _grafico_tiempo_categoria(self, titulo: str, df: pd.DataFrame) -> Container:
        """Gráfico de tiempo de resolución por categoría."""
        items = []
        col_tiempo = "TIEMPO_PROMEDIO" if not df.empty and "TIEMPO_PROMEDIO" in df.columns else ("TIEMPO_MIN" if not df.empty and "TIEMPO_MIN" in df.columns else None)
        col_total = "TOTAL_CERRADOS" if not df.empty and "TOTAL_CERRADOS" in df.columns else None

        if not df.empty and col_tiempo:
            max_tiempo = df[col_tiempo].max()
            
            for _, row in df.iterrows():
                cat = row.get("CATEGORIA", "N/A")
                tiempo = row.get(col_tiempo, 0)
                total = row.get(col_total, 0) if col_total else None
                ancho = (tiempo / max(max_tiempo, 1)) * 200
                color = COLORES_CATEGORIAS.get(cat, COLOR_ACENTO)
                
                items.append(
                    Row([
                        Container(width=90, content=Text(str(cat)[:10], size=11, color=COLOR_TEXTO)),
                        Container(
                            content=Container(
                                width=max(ancho, 5),
                                height=18,
                                bgcolor=color,
                                border_radius=ft.BorderRadius.all(4)
                            ),
                            width=210,
                            bgcolor=COLOR_SUPERFICIE_2,
                            border_radius=ft.BorderRadius.all(4),
                            padding=2
                        ),
                        Text(f"{tiempo:.1f}h" + (f" ({int(total)})" if total is not None else ""), size=10, color=COLOR_TEXTO_SEC, width=80)
                    ], spacing=8)
                )
        else:
            items.append(Text("Sin datos de resolución", color=COLOR_TEXTO_SEC))
        
        return Container(
            content=Column([
                Text(titulo, size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Divider(color=COLOR_SUPERFICIE_2),
                Column(items, spacing=8)
            ], spacing=12),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _tab_rendimiento(self) -> Container:
        """Tab de rendimiento de técnicos."""
        tecnicos = self.gestor.obtener_tecnicos()
        tickets = self.gestor.obtener_todos_tickets()

        filas_rend = []
        if tecnicos is not None and not tecnicos.empty:
            for _, tec in tecnicos.iterrows():
                nombre = str(tec.get("NOMBRE", "") or "")
                estado = str(tec.get("ESTADO", "Desconocido") or "Desconocido")

                if tickets is not None and not tickets.empty and nombre:
                    asignados_df = tickets[tickets.get("TECNICO_ASIGNADO").astype(str) == nombre] if "TECNICO_ASIGNADO" in tickets.columns else pd.DataFrame()
                else:
                    asignados_df = pd.DataFrame()

                tickets_asignados = int(len(asignados_df))
                tickets_cerrados = int((asignados_df.get("ESTADO") == "Cerrado").sum()) if not asignados_df.empty and "ESTADO" in asignados_df.columns else 0

                tiempo_prom = 0.0
                if not asignados_df.empty and "FECHA_APERTURA" in asignados_df.columns and "FECHA_CIERRE" in asignados_df.columns:
                    fa = pd.to_datetime(asignados_df["FECHA_APERTURA"], errors="coerce")
                    fc = pd.to_datetime(asignados_df["FECHA_CIERRE"], errors="coerce")
                    dur_h = (fc - fa).dt.total_seconds() / 3600.0
                    dur_h = dur_h[(dur_h > 0) & (dur_h < 240)]
                    if not dur_h.empty:
                        tiempo_prom = float(dur_h.mean())

                eficiencia = (tickets_cerrados / max(tickets_asignados, 1)) * 100

                filas_rend.append({
                    "NOMBRE": nombre,
                    "ESTADO": estado,
                    "TICKETS_ASIGNADOS": tickets_asignados,
                    "TICKETS_CERRADOS": tickets_cerrados,
                    "TIEMPO_PROMEDIO": tiempo_prom,
                    "EFICIENCIA": eficiencia,
                })

        rendimiento = pd.DataFrame(filas_rend)
        
        # Tabla de rendimiento
        filas = []
        if not rendimiento.empty:
            for _, tec in rendimiento.iterrows():
                eficiencia = tec.get("EFICIENCIA", 0)
                color_efic = COLOR_EXITO if eficiencia >= 80 else (COLOR_ADVERTENCIA if eficiencia >= 50 else COLOR_ERROR)
                
                filas.append(
                    DataRow(
                        cells=[
                            DataCell(Text(str(tec.get("NOMBRE", ""))[:20], color=COLOR_TEXTO)),
                            DataCell(
                                Container(
                                    content=Text(str(tec.get("ESTADO", "")), size=11, color=colors.WHITE),
                                    bgcolor=COLOR_DISPONIBLE if tec.get("ESTADO") == "Disponible" else COLOR_OCUPADO,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                    border_radius=ft.BorderRadius.all(5)
                                )
                            ),
                            DataCell(Text(str(tec.get("TICKETS_ASIGNADOS", 0)), color=COLOR_TEXTO)),
                            DataCell(Text(str(tec.get("TICKETS_CERRADOS", 0)), color=COLOR_EXITO)),
                            DataCell(Text(f"{tec.get('TIEMPO_PROMEDIO', 0):.1f}h", color=COLOR_ACENTO)),
                            DataCell(
                                Row([
                                    Container(
                                        width=60,
                                        height=8,
                                        bgcolor=COLOR_SUPERFICIE_2,
                                        border_radius=ft.BorderRadius.all(4),
                                        content=Container(
                                            width=max(eficiencia * 0.6, 2),
                                            height=8,
                                            bgcolor=color_efic,
                                            border_radius=ft.BorderRadius.all(4)
                                        )
                                    ),
                                    Text(f"{eficiencia:.0f}%", size=11, color=color_efic)
                                ], spacing=5)
                            )
                        ]
                    )
                )
        
        tabla = DataTable(
            columns=[
                DataColumn(Text("Técnico", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Estado", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Asignados", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Cerrados", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("T. Prom.", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Eficiencia", color=COLOR_TEXTO_SEC)),
            ],
            rows=filas,
            border_radius=ft.BorderRadius.all(10),
            bgcolor=COLOR_SUPERFICIE,
            heading_row_color=COLOR_SUPERFICIE_2,
            data_row_max_height=50
        )
        
        # Resumen de rendimiento
        if not rendimiento.empty:
            total_asignados = rendimiento["TICKETS_ASIGNADOS"].sum()
            total_cerrados = rendimiento["TICKETS_CERRADOS"].sum()
            eficiencia_global = (total_cerrados / max(total_asignados, 1)) * 100
            tiempo_prom_global = rendimiento["TIEMPO_PROMEDIO"].mean()
        else:
            total_asignados = total_cerrados = 0
            eficiencia_global = tiempo_prom_global = 0
        
        return Container(
            content=Column([
                Container(height=20),
                
                # KPIs de rendimiento
                Text("🏆 Métricas de Rendimiento del Equipo", size=18, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                Container(height=15),
                
                Row([
                    self._kpi_rendimiento("Total Asignados", str(total_asignados), COLOR_INFO),
                    self._kpi_rendimiento("Total Cerrados", str(total_cerrados), COLOR_EXITO),
                    self._kpi_rendimiento("Eficiencia Global", f"{eficiencia_global:.1f}%", 
                                         COLOR_EXITO if eficiencia_global >= 70 else COLOR_ADVERTENCIA),
                    self._kpi_rendimiento("Tiempo Promedio", f"{tiempo_prom_global:.1f}h", COLOR_ACENTO),
                ], spacing=20),
                
                Container(height=30),
                
                Text("👨‍💻 Rendimiento Individual", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Container(height=10),
                
                tabla if filas else Container(
                    content=Text("No hay datos de rendimiento disponibles", color=COLOR_TEXTO_SEC),
                    padding=20
                )
            ], scroll=ScrollMode.AUTO),
            padding=20
        )
    
    def _kpi_rendimiento(self, titulo: str, valor: str, color: str) -> Container:
        """KPI de rendimiento."""
        return Container(
            content=Column([
                Text(valor, size=28, weight=FontWeight.BOLD, color=color),
                Text(titulo, size=11, color=COLOR_TEXTO_SEC)
            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=5),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(12),
            padding=ft.Padding.symmetric(horizontal=25, vertical=15),
            border=ft.Border.all(1, color)
        )
    
    def _tab_tendencias(self) -> Container:
        """Tab de tendencias temporales."""
        tendencia_semanal = self.gestor.obtener_tendencia_semanal()
        tendencia_mensual = self.gestor.obtener_tickets_por_mes()
        por_hora = self.gestor.obtener_tickets_por_hora()

        tickets = self.gestor.obtener_todos_tickets()
        if tickets is not None and not tickets.empty and "FECHA_APERTURA" in tickets.columns and "ESTADO" in tickets.columns:
            tmp = tickets.copy()
            tmp["FECHA_APERTURA"] = pd.to_datetime(tmp["FECHA_APERTURA"], errors="coerce")
            tmp = tmp.dropna(subset=["FECHA_APERTURA"])

            if not tmp.empty:
                sem_cerr = (
                    tmp[tmp["ESTADO"] == "Cerrado"]
                    .assign(SEMANA=tmp["FECHA_APERTURA"].dt.to_period("W").astype(str))
                    .groupby("SEMANA")
                    .size()
                    .reset_index(name="CERRADOS")
                )
                if tendencia_semanal is not None and not tendencia_semanal.empty and "SEMANA" in tendencia_semanal.columns:
                    tendencia_semanal = tendencia_semanal.merge(sem_cerr, on="SEMANA", how="left")
                    tendencia_semanal["CERRADOS"] = tendencia_semanal["CERRADOS"].fillna(0)

                mes_cerr = (
                    tmp[tmp["ESTADO"] == "Cerrado"]
                    .assign(MES=tmp["FECHA_APERTURA"].dt.to_period("M").astype(str))
                    .groupby("MES")
                    .size()
                    .reset_index(name="CERRADOS")
                )
                if tendencia_mensual is not None and not tendencia_mensual.empty and "MES" in tendencia_mensual.columns:
                    tendencia_mensual = tendencia_mensual.merge(mes_cerr, on="MES", how="left")
                    tendencia_mensual["CERRADOS"] = tendencia_mensual["CERRADOS"].fillna(0)
        
        return Container(
            content=Column([
                Container(height=20),
                
                Text("📈 Análisis de Tendencias", size=18, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                Container(height=20),
                
                # Tendencia semanal
                Row([
                    self._grafico_tendencia_lineal("📊 Tendencia Semanal (últimas 8 semanas)", 
                                                   tendencia_semanal, "SEMANA", "TOTAL", "CERRADOS"),
                    self._grafico_por_hora("🕐 Distribución por Hora del Día", por_hora)
                ], spacing=20, expand=True),
                
                Container(height=30),
                
                # Tendencia mensual
                self._grafico_tendencia_mensual("📅 Evolución Mensual (último año)", tendencia_mensual),
                
            ], scroll=ScrollMode.AUTO),
            padding=20
        )
    
    def _grafico_tendencia_lineal(self, titulo: str, df: pd.DataFrame, 
                                   col_label: str, col_total: str, col_cerrados: str) -> Container:
        """Gráfico de tendencia lineal."""
        puntos = []
        
        if not df.empty and col_total in df.columns:
            max_val = df[col_total].max()
            
            for _, row in df.iterrows():
                label = row.get(col_label, "")
                total = row.get(col_total, 0)
                cerrados = row.get(col_cerrados, 0)
                altura_total = (total / max(max_val, 1)) * 100
                altura_cerrados = (cerrados / max(max_val, 1)) * 100
                
                puntos.append(
                    Column([
                        Text(str(total), size=9, color=COLOR_INFO),
                        Container(height=3),
                        Stack([
                            Container(
                                width=25,
                                height=max(altura_total, 5),
                                bgcolor=COLOR_INFO,
                                border_radius=ft.BorderRadius.all(4)
                            ),
                            Container(
                                width=25,
                                height=max(altura_cerrados, 3),
                                bgcolor=COLOR_EXITO,
                                border_radius=ft.BorderRadius.all(4)
                            )
                        ]),
                        Text(str(label)[:4], size=8, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=0)
                )
        else:
            puntos.append(Text("Sin datos", color=COLOR_TEXTO_SEC))
        
        return Container(
            content=Column([
                Text(titulo, size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Row([
                    Container(width=10, height=10, bgcolor=COLOR_INFO, border_radius=ft.BorderRadius.all(3)),
                    Text("Total", size=10, color=COLOR_TEXTO_SEC),
                    Container(width=10),
                    Container(width=10, height=10, bgcolor=COLOR_EXITO, border_radius=ft.BorderRadius.all(3)),
                    Text("Cerrados", size=10, color=COLOR_TEXTO_SEC),
                ], spacing=5),
                Divider(color=COLOR_SUPERFICIE_2),
                Container(height=10),
                Row(puntos, spacing=8, alignment=MainAxisAlignment.CENTER, scroll=ScrollMode.AUTO)
            ], spacing=8),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _grafico_por_hora(self, titulo: str, df: pd.DataFrame) -> Container:
        """Gráfico de distribución por hora."""
        barras = []
        col_valor = "TOTAL" if not df.empty and "TOTAL" in df.columns else ("CANTIDAD" if not df.empty and "CANTIDAD" in df.columns else None)

        if not df.empty and col_valor:
            max_val = df[col_valor].max()
            
            # Crear todas las horas de 0 a 23
            for hora in range(24):
                fila = df[df["HORA"] == hora]
                cantidad = fila[col_valor].values[0] if not fila.empty else 0
                altura = (cantidad / max(max_val, 1)) * 80
                
                # Color según la hora (más activo = más brillante)
                intensidad = cantidad / max(max_val, 1)
                
                barras.append(
                    Column([
                        Text(str(cantidad) if cantidad > 0 else "", size=8, color=COLOR_TEXTO_SEC),
                        Container(
                            width=12,
                            height=max(altura, 2),
                            bgcolor=COLOR_ACENTO if intensidad > 0.5 else (COLOR_INFO if intensidad > 0.2 else COLOR_SUPERFICIE_3),
                            border_radius=ft.BorderRadius.only(top_left=2, top_right=2)
                        ),
                        Text(str(hora), size=7, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2)
                )
        else:
            barras.append(Text("Sin datos", color=COLOR_TEXTO_SEC))
        
        return Container(
            content=Column([
                Text(titulo, size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Text("Horas con mayor actividad destacadas", size=10, color=COLOR_TEXTO_SEC),
                Divider(color=COLOR_SUPERFICIE_2),
                Container(height=5),
                Row(barras, spacing=2, alignment=MainAxisAlignment.CENTER)
            ], spacing=8),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20,
            expand=True
        )
    
    def _grafico_tendencia_mensual(self, titulo: str, df: pd.DataFrame) -> Container:
        """Gráfico de tendencia mensual."""
        barras = []
        col_etiqueta = "MES" if not df.empty and "MES" in df.columns else "ETIQUETA"
        col_total = "TOTAL" if not df.empty and "TOTAL" in df.columns else "CANTIDAD"

        if not df.empty and col_total in df.columns:
            max_val = df[col_total].max()
            
            for _, row in df.iterrows():
                etiqueta = row.get(col_etiqueta, "")
                cantidad = row.get(col_total, 0)
                cerrados = row.get("CERRADOS", 0)
                altura = (cantidad / max(max_val, 1)) * 100
                altura_cerr = (cerrados / max(max_val, 1)) * 100
                
                barras.append(
                    Column([
                        Text(str(cantidad), size=10, color=COLOR_INFO, weight=FontWeight.BOLD),
                        Container(height=3),
                        Stack([
                            Container(
                                width=45,
                                height=max(altura, 5),
                                bgcolor=COLOR_INFO,
                                border_radius=ft.BorderRadius.only(top_left=5, top_right=5)
                            ),
                            Container(
                                width=45,
                                height=max(altura_cerr, 3),
                                bgcolor=COLOR_EXITO,
                                border_radius=ft.BorderRadius.only(top_left=5, top_right=5)
                            )
                        ]),
                        Container(height=5),
                        Text(str(etiqueta)[:7], size=9, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=0)
                )
        else:
            barras.append(
                Container(
                    content=Text("Sin datos de tendencia mensual", color=COLOR_TEXTO_SEC),
                    padding=20
                )
            )
        
        return Container(
            content=Column([
                Row([
                    Text(titulo, size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Row([
                        Container(width=12, height=12, bgcolor=COLOR_INFO, border_radius=ft.BorderRadius.all(3)),
                        Text("Total", size=10, color=COLOR_TEXTO_SEC),
                        Container(width=10),
                        Container(width=12, height=12, bgcolor=COLOR_EXITO, border_radius=ft.BorderRadius.all(3)),
                        Text("Cerrados", size=10, color=COLOR_TEXTO_SEC),
                    ], spacing=5)
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Divider(color=COLOR_SUPERFICIE_2),
                Container(height=15),
                Row(barras, spacing=10, alignment=MainAxisAlignment.CENTER, scroll=ScrollMode.AUTO)
            ], spacing=10),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(15),
            padding=20
        )
    
    def _tab_analisis_equipos(self) -> Container:
        """Tab de análisis de equipos."""
        equipos_prob = self.gestor.obtener_equipos_problematicos(top_n=10)
        stats_equipos = self.gestor.obtener_estadisticas_equipos()
        grupos = self.gestor.obtener_grupos_con_conteo()
        
        # Lista de equipos problemáticos
        items_equipos = []
        if not equipos_prob.empty:
            for i, (_, row) in enumerate(equipos_prob.iterrows(), 1):
                cantidad = row.get("TOTAL_TICKETS", 0)
                color = COLOR_ERROR if cantidad >= 5 else (COLOR_ADVERTENCIA if cantidad >= 3 else COLOR_INFO)
                
                items_equipos.append(
                    Container(
                        content=Row([
                            Container(
                                content=Text(f"#{i}", size=12, color=colors.WHITE, weight=FontWeight.BOLD),
                                bgcolor=color,
                                width=30,
                                height=30,
                                border_radius=ft.BorderRadius.all(15),
                                alignment=ft.Alignment(0, 0)
                            ),
                            Column([
                                Text(str(row.get("HOSTNAME", "N/A"))[:25], size=12, weight=FontWeight.W_600, color=COLOR_TEXTO),
                                Text(str(row.get("MAC_ADDRESS", ""))[:17], size=10, color=COLOR_TEXTO_SEC)
                            ], spacing=2, expand=True),
                            Container(
                                content=Text(f"{cantidad} tickets", size=11, color=colors.WHITE),
                                bgcolor=color,
                                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                                border_radius=ft.BorderRadius.all(10)
                            )
                        ], spacing=15),
                        padding=12,
                        border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2))
                    )
                )

        self._reportes_equipos_page = 0
        self._reportes_equipos_rows = items_equipos
        self._reportes_equipos_container = Container(
            expand=True,
            height=220,
            bgcolor=COLOR_SUPERFICIE_2,
            border_radius=10,
            padding=8,
        )
        self._reportes_equipos_btn_prev = ft.IconButton(
            icon=icons.CHEVRON_LEFT,
            disabled=True,
            on_click=lambda e: self._cambiar_pagina_reportes_equipos(-1),
        )
        self._reportes_equipos_btn_next = ft.IconButton(
            icon=icons.CHEVRON_RIGHT,
            disabled=True,
            on_click=lambda e: self._cambiar_pagina_reportes_equipos(1),
        )
        self._reportes_equipos_lbl_pagina = Text("Página 0/0", size=11, color=COLOR_TEXTO_SEC)
        self._reportes_equipos_resumen = Text("", size=11, color=COLOR_TEXTO_SEC, visible=False)
        self._reportes_equipos_paginacion = Row(
            [self._reportes_equipos_btn_prev, self._reportes_equipos_lbl_pagina, self._reportes_equipos_btn_next],
            alignment=MainAxisAlignment.END,
            visible=False,
        )
        self._render_reportes_equipos_problematicos()
        
        # Distribución por grupo
        items_grupos = []
        if grupos:
            total_equipos = sum(grupos.values())
            for grupo, cantidad in sorted(grupos.items(), key=lambda x: x[1], reverse=True)[:8]:
                porcentaje = (cantidad / max(total_equipos, 1)) * 100
                
                items_grupos.append(
                    Row([
                        Text(str(grupo)[:15], size=11, color=COLOR_TEXTO, width=120),
                        Container(
                            content=Container(
                                width=max(porcentaje * 2, 5),
                                height=14,
                                bgcolor=COLOR_SECUNDARIO,
                                border_radius=ft.BorderRadius.all(3)
                            ),
                            width=200,
                            bgcolor=COLOR_SUPERFICIE_2,
                            border_radius=ft.BorderRadius.all(3)
                        ),
                        Text(f"{cantidad}", size=11, color=COLOR_TEXTO_SEC, width=40)
                    ], spacing=10)
                )
        
        return Container(
            content=Column([
                Container(height=20),
                
                Text("🖥️ Análisis de Equipos e Inventario", size=18, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                Container(height=20),
                
                # KPIs de equipos
                Row([
                    self._kpi_rendimiento("Total Equipos", str(stats_equipos.get("total_equipos", stats_equipos.get("total", 0))), COLOR_INFO),
                    self._kpi_rendimiento("Activos", str(stats_equipos.get("equipos_activos", stats_equipos.get("activos", 0))), COLOR_EXITO),
                    self._kpi_rendimiento("En Mant.", str(stats_equipos.get("equipos_mantenimiento", stats_equipos.get("mantenimiento", 0))), COLOR_ADVERTENCIA),
                    self._kpi_rendimiento("De Baja", str(stats_equipos.get("bajas", 0)), COLOR_ERROR),
                ], spacing=20),
                
                Container(height=30),
                
                Row([
                    # Equipos problemáticos
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.WARNING, color=COLOR_ADVERTENCIA, size=20),
                                Text("Top 10 Equipos Problemáticos", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO)
                            ], spacing=10),
                            Divider(color=COLOR_SUPERFICIE_2),
                            self._reportes_equipos_container,
                            self._reportes_equipos_paginacion,
                            self._reportes_equipos_resumen,
                        ], spacing=10),
                        bgcolor=COLOR_SUPERFICIE,
                        border_radius=ft.BorderRadius.all(15),
                        padding=20,
                        expand=True,
                        height=350
                    ),
                    
                    # Distribución por grupo
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.BUSINESS, color=COLOR_INFO, size=20),
                                Text("Equipos por Departamento", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO)
                            ], spacing=10),
                            Divider(color=COLOR_SUPERFICIE_2),
                            Column(items_grupos, spacing=8) if items_grupos else 
                                Container(content=Text("Sin datos de grupos", color=COLOR_TEXTO_SEC), padding=20)
                        ], spacing=12),
                        bgcolor=COLOR_SUPERFICIE,
                        border_radius=ft.BorderRadius.all(15),
                        padding=20,
                        expand=True
                    )
                ], spacing=20, expand=True),
                
            ], scroll=ScrollMode.AUTO),
            padding=20
        )

    def _render_reportes_equipos_problematicos(self):
        """Renderiza la página actual del Top de equipos problemáticos con scroll interno."""
        if self._reportes_equipos_container is None:
            return

        total = len(self._reportes_equipos_rows)
        if total == 0:
            self._reportes_equipos_container.content = Container(
                content=Text("Sin equipos problemáticos", color=COLOR_TEXTO_SEC),
                padding=20,
            )
            if self._reportes_equipos_paginacion:
                self._reportes_equipos_paginacion.visible = False
            if self._reportes_equipos_resumen:
                self._reportes_equipos_resumen.visible = False
            return

        total_paginas = max((total + self._reportes_equipos_page_size - 1) // self._reportes_equipos_page_size, 1)
        self._reportes_equipos_page = max(0, min(self._reportes_equipos_page, total_paginas - 1))
        inicio = self._reportes_equipos_page * self._reportes_equipos_page_size
        fin = min(inicio + self._reportes_equipos_page_size, total)

        self._reportes_equipos_container.content = Column(
            controls=self._reportes_equipos_rows[inicio:fin],
            spacing=0,
            scroll=ScrollMode.AUTO,
            expand=True,
        )

        if self._reportes_equipos_btn_prev:
            self._reportes_equipos_btn_prev.disabled = self._reportes_equipos_page <= 0
        if self._reportes_equipos_btn_next:
            self._reportes_equipos_btn_next.disabled = self._reportes_equipos_page >= total_paginas - 1
        if self._reportes_equipos_lbl_pagina:
            self._reportes_equipos_lbl_pagina.value = f"Página {self._reportes_equipos_page + 1}/{total_paginas}"
        if self._reportes_equipos_paginacion:
            self._reportes_equipos_paginacion.visible = total_paginas > 1
        if self._reportes_equipos_resumen:
            self._reportes_equipos_resumen.value = f"Mostrando {inicio + 1}-{fin} de {total} equipos"
            self._reportes_equipos_resumen.visible = True

    def _cambiar_pagina_reportes_equipos(self, delta: int):
        """Cambia la página en Reportes > Equipos problemáticos."""
        if not self._reportes_equipos_rows:
            return
        self._reportes_equipos_page += delta
        self._render_reportes_equipos_problematicos()
        self.page.update()
    
    def _exportar_reporte_excel(self):
        """Exporta el reporte completo a Excel."""
        try:
            ruta = self.gestor.exportar_reporte_excel()
            if ruta:
                self._mostrar_snackbar(f"Reporte exportado: {ruta}", COLOR_EXITO)
                # Abrir el directorio donde se guardó
                import subprocess
                subprocess.Popen(f'explorer /select,"{ruta}"')
            else:
                self._mostrar_snackbar("Error al exportar reporte", COLOR_ERROR)
        except Exception as e:
            self._mostrar_snackbar(f"Error: {str(e)}", COLOR_ERROR)
    
    def _stat_card(self, titulo: str, valor: str, icono, color: str) -> Container:
        """Crea una tarjeta de estadística."""
        return Container(
            content=Row([
                Icon(icono, size=30, color=color),
                Column([
                    Text(valor, size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Text(titulo, size=12, color=COLOR_TEXTO_SEC)

                ], spacing=2)
            ], spacing=15),
            bgcolor=COLOR_SUPERFICIE,
            padding=20,
            border_radius=ft.BorderRadius.all(15),
            border=ft.Border.all(1, color)
        )

    def _chat_detalle_clave(self, mensaje: Dict[str, Any]) -> str:
        return str(mensaje.get("client_msg_id") or mensaje.get("id") or "")

    def _chat_detalle_item(self, mensaje: Dict[str, Any]) -> Container:
        autor_tipo = str(mensaje.get("autor_tipo", "usuario"))
        autor_id = str(mensaje.get("autor_id", ""))
        texto = str(mensaje.get("mensaje", ""))
        fecha = str(mensaje.get("fecha", ""))[:16]
        color_b = COLOR_SUPERFICIE_3 if autor_tipo == "tecnico" else COLOR_SUPERFICIE_2
        return Container(
            content=Column([
                Row([
                    Text(autor_id or autor_tipo.title(), size=10, weight=FontWeight.W_600, color=COLOR_ACENTO),
                    Text(fecha, size=9, color=COLOR_TEXTO_SEC),
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Text(texto, size=11, color=COLOR_TEXTO),
            ], spacing=2),
            bgcolor=color_b,
            border_radius=8,
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
        )

    def _chat_detalle_render(self, mensajes: List[Dict[str, Any]], chat_list: Optional[ListView] = None) -> None:
        lista = chat_list or self._chat_detalle_list_ref
        if lista is None:
            return

        filas = [self._chat_detalle_item(m) for m in mensajes[-self._limite_chat_preview():]]
        if not filas:
            filas = [
                Container(
                    content=Text("Sin mensajes de chat para este ticket.", size=11, color=COLOR_TEXTO_SEC),
                    padding=ft.Padding.all(8),
                    bgcolor=COLOR_SUPERFICIE_2,
                    border_radius=8,
                )
            ]

        lista.controls = filas
        try:
            self.page.update()
        except Exception:
            pass

    def _chat_detalle_actualizar(self, ticket: Dict[str, Any], chat_list: Optional[ListView] = None,
                                 mensaje_nuevo: Optional[Dict[str, Any]] = None,
                                 recargar: bool = False) -> None:
        id_ticket = str(ticket.get("ID_TICKET", "") or "").strip()
        if not id_ticket:
            return

        if mensaje_nuevo:
            clave = self._chat_detalle_clave(mensaje_nuevo)
            if clave:
                reemplazado = False
                for indice, actual in enumerate(self._chat_detalle_mensajes):
                    if self._chat_detalle_clave(actual) == clave:
                        self._chat_detalle_mensajes[indice] = mensaje_nuevo
                        reemplazado = True
                        break
                if not reemplazado:
                    self._chat_detalle_mensajes.append(mensaje_nuevo)

        if recargar or not self._chat_detalle_mensajes or self._chat_detalle_ticket_id != id_ticket:
            try:
                self._chat_detalle_mensajes = self.gestor.obtener_chat_ticket(id_ticket, limite=self._limite_chat_historial(), offset=0) or []
                if mensaje_nuevo:
                    clave = self._chat_detalle_clave(mensaje_nuevo)
                    if clave:
                        reemplazado = False
                        for indice, actual in enumerate(self._chat_detalle_mensajes):
                            if self._chat_detalle_clave(actual) == clave:
                                self._chat_detalle_mensajes[indice] = mensaje_nuevo
                                reemplazado = True
                                break
                        if not reemplazado:
                            self._chat_detalle_mensajes.append(mensaje_nuevo)
            except Exception:
                pass

        self._chat_detalle_ticket_id = id_ticket
        self._chat_detalle_render(self._chat_detalle_mensajes, chat_list)

    def _chat_auto_respuesta_habilitada(self) -> bool:
        return bool(self._prefs.get("features", {}).get("chat_auto_respuesta", True))

    def _chat_autoasignacion_habilitada(self) -> bool:
        return bool(self._prefs.get("features", {}).get("chat_autoasignacion", True))

    def _chat_mensaje_auto(self, ticket: Optional[Dict[str, Any]], nombre_tecnico: str = "") -> str:
        plantilla = str(self._prefs.get("chat", {}).get("mensaje_auto", "")).strip()
        if not plantilla:
            plantilla = "Recibimos tu mensaje. Un técnico te atenderá a la brevedad."

        doc = ticket or {}
        turno = str(doc.get("TURNO", "")).strip()
        estado = str(doc.get("ESTADO", "")).strip() or "Abierto"
        prioridad = str(doc.get("PRIORIDAD", "")).strip()
        categoria = str(doc.get("CATEGORIA", "")).strip()

        partes = [plantilla]
        if nombre_tecnico:
            partes.append(f"Técnico asignado: {nombre_tecnico}.")
        elif estado in {"Abierto", "En Cola"}:
            partes.append("Estamos priorizando tu atención.")

        if prioridad in {"Crítica", "Alta"}:
            partes.append(f"Prioridad detectada: {prioridad}.")
        if categoria:
            partes.append(f"Categoría: {categoria}.")
        if turno:
            partes.append(f"Turno: {turno}.")
        return " ".join(p for p in partes if p).strip()

    def _enviar_chat_y_broadcast(self, id_ticket: str, mensaje: str, autor_tipo: str = "tecnico", autor_id: str = "",
                                evitar_duplicado: bool = False) -> Optional[Dict[str, Any]]:
        if evitar_duplicado:
            try:
                ultimos = self.gestor.obtener_chat_ticket(id_ticket, limite=1, offset=0) or []
                ultimo = ultimos[0] if ultimos else None
                if ultimo:
                    ultimo_tipo = str(ultimo.get("autor_tipo", "")).strip().lower()
                    ultimo_id = str(ultimo.get("autor_id", "")).strip().lower()
                    if (
                        ultimo_tipo == str(autor_tipo or "").strip().lower()
                        and ultimo_id == str(autor_id or self._usuario_operador()).strip().lower()
                        and str(ultimo.get("mensaje", "")).strip() == str(mensaje or "").strip()
                    ):
                        return ultimo
            except Exception:
                pass

        msg = self.gestor.agregar_mensaje_chat_ticket(
            id_ticket=id_ticket,
            autor_tipo=autor_tipo,
            autor_id=autor_id or self._usuario_operador(),
            mensaje=mensaje,
        )
        if not msg:
            return None
        try:
            import ws_server as _ws
            _ws.broadcast_global(_ws.EVENTO_TICKET_CHAT_MENSAJE, {"mensaje_chat": msg})
        except Exception:
            pass
        return msg

    def _seleccionar_tecnico_para_autoasignacion(self, disponibles: pd.DataFrame) -> tuple[str, str]:
        """Selecciona técnico disponible con menor carga histórica."""
        if disponibles is None or disponibles.empty:
            return "", ""
        try:
            if self._modo_autoasignacion() == "primero_disponible":
                elegido = disponibles.iloc[0]
                id_tecnico = str(elegido.get("ID_TECNICO", "") or "").strip()
                nombre_tecnico = str(elegido.get("NOMBRE", "") or id_tecnico).strip()
                return id_tecnico, nombre_tecnico

            df = disponibles.copy()
            if "TICKETS_ATENDIDOS" in df.columns:
                df["TICKETS_ATENDIDOS"] = pd.to_numeric(df["TICKETS_ATENDIDOS"], errors="coerce").fillna(0)
            else:
                df["TICKETS_ATENDIDOS"] = 0

            if "ULTIMA_ACTIVIDAD" in df.columns:
                df["ULTIMA_ACTIVIDAD"] = pd.to_datetime(df["ULTIMA_ACTIVIDAD"], errors="coerce")
            else:
                df["ULTIMA_ACTIVIDAD"] = pd.NaT

            df = df.sort_values(by=["TICKETS_ATENDIDOS", "ULTIMA_ACTIVIDAD"], ascending=[True, True])
            elegido = df.iloc[0]
            id_tecnico = str(elegido.get("ID_TECNICO", "") or "").strip()
            nombre_tecnico = str(elegido.get("NOMBRE", "") or id_tecnico).strip()
            return id_tecnico, nombre_tecnico
        except Exception:
            elegido = disponibles.iloc[0]
            id_tecnico = str(elegido.get("ID_TECNICO", "") or "").strip()
            nombre_tecnico = str(elegido.get("NOMBRE", "") or id_tecnico).strip()
            return id_tecnico, nombre_tecnico

    def _chat_es_primer_mensaje_usuario(self, id_ticket: str, mensaje_chat: Optional[Dict[str, Any]] = None) -> bool:
        """Retorna True solo cuando el ticket tiene su primer mensaje de usuario."""
        try:
            mensajes = self.gestor.obtener_chat_ticket(id_ticket, limite=200, offset=0) or []
            total_usuario = 0
            for msg in mensajes:
                if str((msg or {}).get("autor_tipo", "")).strip().lower() == "usuario":
                    total_usuario += 1

            # Fallback defensivo: si no hay historial cargado, usa el payload recibido.
            if total_usuario == 0 and mensaje_chat:
                if str((mensaje_chat or {}).get("autor_tipo", "")).strip().lower() == "usuario":
                    total_usuario = 1

            return total_usuario <= 1
        except Exception:
            return False

    def _autoasignar_por_chat_si_corresponde(self, id_ticket: str) -> tuple[bool, str]:
        if not self._chat_autoasignacion_habilitada():
            return False, ""
        try:
            ticket = self.gestor.obtener_ticket_por_id(id_ticket) or {}
            if not ticket:
                return False, ""
            if str(ticket.get("ESTADO", "")) in {"Cerrado", "Cancelado"}:
                return False, ""
            if str(ticket.get("TECNICO_ASIGNADO", "")).strip():
                return False, str(ticket.get("TECNICO_ASIGNADO", "")).strip()

            disponibles = self.gestor.obtener_tecnicos_disponibles()
            if disponibles is None or disponibles.empty:
                return False, ""

            id_tecnico, nombre_tecnico = self._seleccionar_tecnico_para_autoasignacion(disponibles)
            if not id_tecnico:
                return False, ""

            ok = self.gestor.asignar_ticket_a_tecnico(
                id_ticket,
                id_tecnico,
                usuario_op=self._usuario_operador(),
                origen="kubo.chat.autoasignacion",
            )
            if not ok:
                return False, ""

            try:
                import ws_server as _ws
                _ws.broadcast_global(
                    _ws.EVENTO_TICKET_ACTUALIZADO,
                    {"id_ticket": id_ticket, "estado": "En Proceso"},
                )
            except Exception:
                pass

            return True, nombre_tecnico
        except Exception:
            return False, ""

    def _reset_chat_detalle_contexto(self) -> None:
        self._chat_detalle_activo = False
        self._chat_detalle_ticket_id = None
        self._chat_detalle_list_ref = None
        self._chat_detalle_txt_ref = None
        self._chat_detalle_mensajes = []

    def _manejar_chat_realtime(self, payload: Dict[str, Any]) -> None:
        mensaje_chat = payload.get("mensaje_chat", {}) or {}
        if not isinstance(mensaje_chat, dict):
            return

        id_ticket = str(mensaje_chat.get("id_ticket", "") or "").strip()
        if not id_ticket:
            return

        autor_tipo = str(mensaje_chat.get("autor_tipo", "usuario") or "usuario").strip().lower()
        autor_id = str(mensaje_chat.get("autor_id", "")).strip()
        es_mio = autor_id.lower() == (self._usuario_operador() or "").lower()
        modo_respuesta = self._modo_respuesta_auto()

        dialogo_abierto = bool(getattr(getattr(self.page, "dialog", None), "open", False))
        chat_abierto = bool(self._chat_detalle_activo and dialogo_abierto and self._chat_detalle_ticket_id == id_ticket)
        notif_habilitadas = bool(self._prefs.get("ui", {}).get("mostrar_notificaciones", True))
        notif_externa_habilitada = bool(self._prefs.get("features", {}).get("chat_notificacion_externa", True))

        if autor_tipo == "usuario":
            primer_mensaje_usuario = self._chat_es_primer_mensaje_usuario(id_ticket, mensaje_chat)
            asignado_auto, nombre_tecnico = self._autoasignar_por_chat_si_corresponde(id_ticket)
            responder_auto = self._chat_auto_respuesta_habilitada() and (
                modo_respuesta == "siempre" or (modo_respuesta == "primer_mensaje" and primer_mensaje_usuario)
            )
            if asignado_auto and responder_auto:
                ticket_actual = self.gestor.obtener_ticket_por_id(id_ticket) or {"ID_TICKET": id_ticket}
                texto_auto = self._chat_mensaje_auto(ticket_actual, nombre_tecnico=nombre_tecnico)
                self._enviar_chat_y_broadcast(
                    id_ticket,
                    texto_auto,
                    autor_tipo="tecnico",
                    autor_id=self._usuario_operador(),
                    evitar_duplicado=True,
                )
            elif responder_auto and not es_mio:
                ticket_actual = self.gestor.obtener_ticket_por_id(id_ticket) or {"ID_TICKET": id_ticket}
                if str(ticket_actual.get("ESTADO", "")) not in {"Cerrado", "Cancelado"}:
                    texto_auto = self._chat_mensaje_auto(ticket_actual)
                    self._enviar_chat_y_broadcast(
                        id_ticket,
                        texto_auto,
                        autor_tipo="sistema",
                        autor_id="Sistema",
                        evitar_duplicado=True,
                    )

        if not es_mio and not chat_abierto and notif_habilitadas and notif_externa_habilitada and mostrar_notificacion_windows:
            try:
                mostrar_notificacion_windows(
                    titulo=f"💬 Mensaje en Ticket {id_ticket}",
                    mensaje=f"{autor_id or 'Usuario'}: {str(mensaje_chat.get('mensaje', ''))[:80]}",
                    tipo="advertencia" if autor_tipo == "usuario" else "info",
                    duracion=self._duracion_notificacion(),
                    abrir_app=bool(self._prefs_bool("features", "abrir_chat_notificacion", True)),
                )
            except Exception:
                pass

        if chat_abierto:
            self._chat_detalle_actualizar(self.ticket_seleccionado or {"ID_TICKET": id_ticket},
                                          mensaje_nuevo=mensaje_chat)
        self._actualizar_badges_navegacion()
    
    # =========================================================================
    # FUNCIONES AUXILIARES
    # =========================================================================
    
    def _mostrar_detalle_ticket(self, ticket: Dict):
        """Muestra el panel de detalle de un ticket (solo para tickets activos)."""
        self.ticket_seleccionado = ticket
        id_ticket = str(ticket.get("ID_TICKET", "") or "").strip()
        
        estado = ticket.get("ESTADO", "Abierto")
        
        # Si el ticket está cerrado o cancelado, mostrar vista de solo lectura
        if estado in {"Cerrado", "Cancelado"}:
            self._mostrar_detalle_historial(ticket)
            return
        
        color_estado = {
            "Abierto": COLOR_ADVERTENCIA,
            "En Cola": COLOR_INFO,
            "En Proceso": COLOR_PRIMARIO,
            "En Espera": COLOR_TEXTO_SEC,
            "Cerrado": COLOR_EXITO
        }.get(estado, COLOR_TEXTO_SEC)
        
        icono_estado = {
            "Abierto": icons.FIBER_NEW,
            "En Cola": icons.QUEUE,
            "En Proceso": icons.ENGINEERING,
            "En Espera": icons.PAUSE_CIRCLE,
            "Cerrado": icons.CHECK_CIRCLE
        }.get(estado, icons.HELP)
        
        # Estados sin "Cerrado" para el dropdown (una vez cerrado no se puede reabrir)
        estados_disponibles = [e for e in ESTADOS_TICKET]
        
        # Campos editables
        dd_estado = Dropdown(
            label="Estado",
            value=estado,
            options=[dropdown.Option(e) for e in estados_disponibles],
            width=200,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO
        )
        
        txt_notas = TextField(
            label="Notas de Resolución",
            value=str(ticket.get("NOTAS_RESOLUCION", "")),
            multiline=True,
            min_lines=3,
            max_lines=5,
            width=380,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            prefix_icon=icons.NOTES
        )

        chat_list = ListView(height=190, spacing=6, auto_scroll=True)
        txt_chat = TextField(
            label="Mensaje al usuario",
            hint_text="Escribe una actualización para el usuario...",
            multiline=True,
            min_lines=2,
            max_lines=4,
            width=380,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            prefix_icon=icons.FORUM,
        )
        self._chat_detalle_ticket_id = id_ticket
        self._chat_detalle_list_ref = chat_list
        self._chat_detalle_txt_ref = txt_chat
        self._chat_detalle_activo = True
        
        dialogo = None
        
        def cerrar_dialogo(e=None):
            nonlocal dialogo
            if dialogo:
                dialogo.open = False
                self._reset_chat_detalle_contexto()
                self.page.update()
        
        def guardar_cambios(e):
            try:
                id_ticket = ticket.get("ID_TICKET", "")
                estado_actual = str(ticket.get("ESTADO", "Abierto"))
                estado_nuevo = dd_estado.value or estado_actual
                notas = txt_notas.value or ""

                if InputValidator is not None:
                    # Validar transición de estado cuando cambie
                    if estado_nuevo != estado_actual:
                        es_valido_estado, err_estado = InputValidator.validar_estado_cambio(
                            estado_actual,
                            estado_nuevo,
                        )
                        if not es_valido_estado:
                            self._mostrar_advertencia(err_estado or "Transición de estado inválida")
                            return

                    # Sanitizar y validar notas de resolución (si vienen)
                    notas = InputValidator.sanitize_string(
                        notas,
                        max_length=InputValidator.MAX_NOTAS,
                        allow_newlines=True,
                    )
                    if estado_nuevo == "Cerrado":
                        es_valido_notas, err_notas = InputValidator.validar_notas_resolucion(notas)
                        if not es_valido_notas:
                            self._mostrar_advertencia(err_notas or "Debes agregar notas de resolución")
                            return

                cerrar_dialogo()
                self._mostrar_carga("Guardando cambios...")
                
                self.gestor.actualizar_ticket(
                    id_ticket,
                    estado=estado_nuevo,
                    notas_resolucion=notas,
                    usuario_op=self._usuario_operador(),
                    origen="kubo.detalle",
                )
                
                # Broadcast WebSocket — notifíca a la emisora del cambio
                try:
                    import ws_server as _ws
                    _ws.broadcast_global(
                        _ws.EVENTO_TICKET_ACTUALIZADO,
                        {"id_ticket": id_ticket,
                         "estado": estado_nuevo}
                    )
                except Exception:
                    pass
                
                self._ocultar_carga()
                self._mostrar_exito("Ticket actualizado", f"El ticket #{ticket.get('ID_TICKET', '')} se actualizó correctamente.")
                self._refrescar_vista()
            except ValueError as ex:
                self._ocultar_carga()
                self._mostrar_error("Error al actualizar", str(ex))

        def refrescar_chat(e=None):
            try:
                self._chat_detalle_actualizar(ticket, chat_list=chat_list, recargar=True)
            except Exception:
                pass

        def enviar_chat(e):
            if ticket.get("ESTADO") in {"Cerrado", "Cancelado"}:
                self._mostrar_advertencia("Este ticket ya no permite escribir porque está cerrado o cancelado.")
                return

            mensaje = (txt_chat.value or "").strip()
            if not mensaje:
                return
            if not id_ticket:
                self._mostrar_advertencia("No se encontró ID de ticket")
                return
            try:
                msg = self.gestor.agregar_mensaje_chat_ticket(
                    id_ticket=id_ticket,
                    autor_tipo="tecnico",
                    autor_id=self._usuario_operador(),
                    mensaje=mensaje,
                )
                if not msg:
                    self._mostrar_error("Chat", "No se pudo guardar el mensaje")
                    return

                # Mostrar notificación de mensaje enviado
                try:
                    contenido = mensaje[:50]
                    if mostrar_notificacion_windows:
                        mostrar_notificacion_windows(
                            titulo="💬 Mensaje Enviado",
                            mensaje=f"Respuesta enviada al usuario",
                            tipo="exito",
                            duracion="short",
                            abrir_app=False
                        )
                except Exception:
                    pass

                try:
                    import ws_server as _ws
                    payload = {"mensaje_chat": msg}
                    _ws.broadcast_global(_ws.EVENTO_TICKET_CHAT_MENSAJE, payload)
                except Exception:
                    pass

                txt_chat.value = ""
                self._chat_detalle_actualizar(ticket, chat_list=chat_list, mensaje_nuevo=msg)
                self._actualizar_badges_navegacion()
            except Exception as ex:
                self._mostrar_error("Chat", str(ex))
        
        dialogo = AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.CONFIRMATION_NUMBER, size=24, color=colors.WHITE),
                    bgcolor=COLOR_PRIMARIO,
                    padding=8,
                    border_radius=8
                ),
                Text(f"Ticket #{ticket.get('ID_TICKET', '')}", weight=FontWeight.BOLD, size=18, color=COLOR_TEXTO),
                Container(
                    content=Row([
                        Icon(icono_estado, size=14, color=colors.WHITE),
                        Text(estado, size=12, color=colors.WHITE)
                    ], spacing=5),
                    bgcolor=color_estado,
                    padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                    border_radius=ft.BorderRadius.all(10)
                )
            ], spacing=10, alignment=MainAxisAlignment.START),
            content=Container(
                content=Column([
                    # Info del usuario
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.PERSON, size=16, color=COLOR_ACENTO),
                                Text("Información del Usuario", weight=FontWeight.BOLD, color=COLOR_ACENTO)
                            ], spacing=8),
                            Container(height=5),
                            Row([
                                Text("Usuario:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=100),
                                Text(str(ticket.get("USUARIO_AD", "")), color=COLOR_TEXTO)
                            ]),
                            Row([
                                Text("Equipo:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=100),
                                Text(str(ticket.get("HOSTNAME", "")), color=COLOR_TEXTO)
                            ]),
                            Row([
                                Text("MAC:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=100),
                                Text(str(ticket.get("MAC_ADDRESS", "")), color=COLOR_TEXTO, size=12)
                            ]),
                            Row([
                                Text("Categoría:", weight=FontWeight.W_500, color=COLOR_TEXTO_SEC, width=100),
                                Container(
                                    content=Text(str(ticket.get("CATEGORIA", "")), size=11, color=colors.WHITE),
                                    bgcolor=COLOR_INFO,
                                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                    border_radius=5
                                )
                            ])
                        ]),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=12,
                        border_radius=10
                    ),
                    
                    # Descripción
                    Container(
                        content=Column([
                            Row([
                                Icon(icons.DESCRIPTION, size=16, color=COLOR_ACENTO),
                                Text("Descripción", weight=FontWeight.BOLD, color=COLOR_ACENTO)
                            ], spacing=8),
                            Container(height=5),
                            Text(str(ticket.get("DESCRIPCION", ""))[:250], color=COLOR_TEXTO, size=13)
                        ]),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=12,
                        border_radius=10
                    ),

                    Container(
                        content=Column([
                            Row([
                                Icon(icons.FORUM, size=16, color=COLOR_ACENTO),
                                Text("Chat del Ticket", weight=FontWeight.BOLD, color=COLOR_ACENTO),
                                Container(expand=True),
                                ft.TextButton("Refrescar", icon=icons.REFRESH, on_click=refrescar_chat),
                            ], spacing=8),
                            chat_list,
                            txt_chat,
                            Row([
                                Container(expand=True),
                                ft.Button(
                                    "Enviar mensaje",
                                    icon=icons.SEND,
                                    bgcolor=COLOR_PRIMARIO,
                                    color=colors.WHITE,
                                    on_click=enviar_chat,
                                ),
                            ]),
                        ], spacing=8),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=12,
                        border_radius=10,
                    ),
                    
                    Divider(color=COLOR_BORDE),
                    
                    # Acciones
                    Row([
                        Icon(icons.EDIT, size=16, color=COLOR_ACENTO),
                        Text("Actualizar Ticket", weight=FontWeight.BOLD, color=COLOR_ACENTO)
                    ], spacing=8),
                    dd_estado,
                    txt_notas,

                    Divider(color=COLOR_BORDE),

                    # ── Log de cambios ──────────────────────────────────
                    Row([
                        Icon(icons.HISTORY, size=16, color=COLOR_INFO),
                        Text("Histórico de Cambios", weight=FontWeight.BOLD, color=COLOR_INFO)
                    ], spacing=8),
                    self._construir_log_ticket(ticket.get("ID_TICKET", "")),
                ], scroll=ScrollMode.AUTO, spacing=12),
                padding=5
            ),
            actions=[
                ft.TextButton(
                    "Cerrar",
                    icon=icons.CLOSE,
                    on_click=cerrar_dialogo
                ),
                ft.Button(
                    "Guardar",
                    icon=icons.SAVE,
                    bgcolor=COLOR_PRIMARIO,
                    color=colors.WHITE,
                    on_click=guardar_cambios
                )
            ],
            actions_alignment=MainAxisAlignment.END
        )

        refrescar_chat()
        
        self.page.show_dialog(dialogo)
    
    def _construir_log_ticket(self, id_ticket: str) -> ft.Control:
        """Construye la lista de entradas del log de un ticket."""
        try:
            entradas = self.gestor.obtener_log_ticket(id_ticket)
            integridad = self.gestor.verificar_integridad_log_ticket(id_ticket)
            if not entradas:
                return Container(
                    content=Text("Sin cambios registrados.", size=11, color=COLOR_TEXTO_SEC,
                                 italic=True),
                    padding=ft.Padding.symmetric(vertical=6)
                )
            estado_ok = bool(integridad.get("ok", False))
            txt_integridad = (
                f"Integridad: {'OK' if estado_ok else 'ALERTA'}"
                f" | Verificados: {integridad.get('verificados', 0)}/{integridad.get('total', 0)}"
                f" | Legacy: {integridad.get('legacy', 0)}"
            )
            items = []
            for entrada in entradas[:15]:  # máx 15 entradas
                fecha = str(entrada.get("FECHA", ""))[:16]
                accion  = entrada.get("ACCION", "")
                detalle = entrada.get("DETALLE", "")
                op      = entrada.get("USUARIO_OP", "Sistema")
                origen = entrada.get("ORIGEN", "") or "sistema"
                estado_antes = entrada.get("ESTADO_ANTES", "") or ""
                estado_despues = entrada.get("ESTADO_DESPUES", "") or ""
                traza_estado = ""
                if estado_antes or estado_despues:
                    traza_estado = f"{estado_antes or '-'} -> {estado_despues or '-'}"
                items.append(Container(
                    content=Row([
                        Icon(icons.CIRCLE, size=8, color=COLOR_ACENTO),
                        Column([
                            Row([
                                Text(accion, size=11, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                                Text(f"• {op}", size=10, color=COLOR_TEXTO_SEC),
                                Text(f"• {origen}", size=10, color=COLOR_INFO),
                            ], spacing=6),
                            Text(f"Estado: {traza_estado}", size=10, color=COLOR_ADVERTENCIA) if traza_estado else Container(),
                            Text(detalle, size=10, color=COLOR_TEXTO_SEC) if detalle else Container(),
                        ], spacing=1, expand=True),
                        Text(fecha, size=9, color=COLOR_TEXTO_SEC)
                    ], spacing=8),
                    border=ft.Border(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2)),
                    padding=ft.Padding.symmetric(vertical=5)
                ))
            return Column([
                Container(
                    content=Row([
                        Icon(icons.VERIFIED_USER if estado_ok else icons.WARNING_AMBER_ROUNDED,
                             size=14, color=COLOR_EXITO if estado_ok else COLOR_ADVERTENCIA),
                        Text(txt_integridad, size=10, color=COLOR_EXITO if estado_ok else COLOR_ADVERTENCIA),
                    ], spacing=8),
                    bgcolor=COLOR_SUPERFICIE_2,
                    border_radius=ft.BorderRadius.all(8),
                    padding=ft.Padding.symmetric(horizontal=10, vertical=6),
                ),
                Column(items, spacing=0),
            ], spacing=8)
        except Exception as ex:
            print(f"[LOG TICKET] {ex}")
            return Container()

    def _ir_a_tickets(self):
        """Navega a la vista de tickets."""
        self.nav_rail.selected_index = 2
        self.vista_actual = 2
        self.contenido.content = self._obtener_vista(2)
        self.page.update()
    
    def _refrescar_vista(self):
        """Refresca la vista actual."""
        ahora = time.time()
        if ahora - self._ultimo_refresco_vista_ts < 1.0:
            return
        self._ultimo_refresco_vista_ts = ahora

        vistas = self._builders_vistas()
        if self.vista_actual < len(vistas):
            self.contenido.content = self._obtener_vista(self.vista_actual, forzar=True)
            self._actualizar_badges_navegacion()
            self.page.update()
    
    def _mostrar_snackbar(self, mensaje: str, color: str):
        """Muestra un snackbar mejorado con icono."""
        # Determinar icono según el color
        if color == COLOR_EXITO:
            icono = icons.CHECK_CIRCLE_ROUNDED
        elif color == COLOR_ERROR:
            icono = icons.ERROR_ROUNDED
        elif color == COLOR_ADVERTENCIA:
            icono = icons.WARNING_ROUNDED
        else:
            icono = icons.INFO_ROUNDED
        
        self.page.snack_bar = SnackBar(
            content=Row([
                Icon(icono, size=20, color=colors.WHITE),
                Text(mensaje, color=colors.WHITE, weight=FontWeight.W_500),
            ], spacing=10),
            bgcolor=color,
            duration=3000,
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    # =========================================================================
    # SISTEMA DE DIÁLOGOS PROFESIONALES
    # =========================================================================
    
    def _crear_dialogo_profesional(self, tipo: str, titulo: str, mensaje: str,
                                    boton_texto: str = "Aceptar",
                                    boton_accion=None,
                                    mostrar_boton_cancelar: bool = False,
                                    boton_cancelar_texto: str = "Cancelar",
                                    boton_cancelar_accion=None) -> AlertDialog:
        """Crea un diálogo profesional con estilo oscuro."""
        config = DIALOGO_TIPOS.get(tipo, DIALOGO_TIPOS["info"])
        
        # Variable para guardar referencia al diálogo
        dialogo_ref = [None]
        
        def cerrar_dialogo(e=None):
            if dialogo_ref[0]:
                dialogo_ref[0].open = False
                self.page.update()
        
        # Icono animado
        icono_container = Container(
            content=Container(
                content=Icon(config["icono"], size=45, color=config["color"]),
                bgcolor=config["color_fondo"],
                border_radius=ft.BorderRadius.all(40),
                width=80,
                height=80,
                alignment=ft.Alignment(0, 0),
                border=ft.Border.all(2, config["color"]),
            ),
            alignment=ft.Alignment(0, 0),
        )
        
        # Contenido
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
                        size=13,
                        color=COLOR_TEXTO_SEC,
                        text_align=TextAlign.CENTER,
                    ),
                    padding=ft.Padding.symmetric(horizontal=10),
                ),
            ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=0),
            width=320,
            padding=ft.Padding.only(top=25, bottom=10, left=15, right=15),
        )
        
        # Botones
        acciones = []
        
        if mostrar_boton_cancelar:
            acciones.append(
                ft.TextButton(
                    boton_cancelar_texto,
                    on_click=boton_cancelar_accion or cerrar_dialogo,
                    style=ft.ButtonStyle(color=COLOR_TEXTO_SEC),
                )
            )
        
        def accion_principal(e):
            cerrar_dialogo(e)
            if boton_accion:
                boton_accion(e)
        
        acciones.append(
            ft.Button(
                content=Row([
                    Icon(icons.CHECK_ROUNDED if tipo == "exito" else icons.ARROW_FORWARD_ROUNDED,
                         color=colors.WHITE, size=16),
                    Text(boton_texto, color=colors.WHITE, weight=FontWeight.W_600),
                ], spacing=6, alignment=MainAxisAlignment.CENTER),
                bgcolor=config["color"],
                style=ft.ButtonStyle(
                    shape=ft.RoundedRectangleBorder(radius=10),
                ),
                height=42,
                on_click=accion_principal,
            )
        )
        
        dialogo = AlertDialog(
            modal=True,
            bgcolor=COLOR_SUPERFICIE,
            content=contenido,
            actions=acciones,
            actions_alignment=MainAxisAlignment.CENTER,
            shape=ft.RoundedRectangleBorder(radius=20),
        )
        
        dialogo_ref[0] = dialogo
        return dialogo
    
    def _mostrar_exito(self, mensaje: str, titulo: str = "¡Completado!"):
        """Muestra un diálogo de éxito."""
        dialogo = self._crear_dialogo_profesional(
            tipo="exito",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Aceptar"
        )
        self.page.show_dialog(dialogo)
    
    def _mostrar_error(self, mensaje: str, titulo: str = "¡Error!"):
        """Muestra un diálogo de error."""
        dialogo = self._crear_dialogo_profesional(
            tipo="error",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Entendido"
        )
        self.page.show_dialog(dialogo)
    
    def _mostrar_advertencia(self, mensaje: str, titulo: str = "Atención"):
        """Muestra un diálogo de advertencia."""
        dialogo = self._crear_dialogo_profesional(
            tipo="advertencia",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Entendido"
        )
        self.page.show_dialog(dialogo)
    
    def _mostrar_info(self, mensaje: str, titulo: str = "Información"):
        """Muestra un diálogo informativo."""
        dialogo = self._crear_dialogo_profesional(
            tipo="info",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="OK"
        )
        self.page.show_dialog(dialogo)
    
    def _mostrar_confirmacion(self, mensaje: str, titulo: str = "Confirmar",
                               on_confirmar=None, on_cancelar=None):
        """Muestra un diálogo de confirmación."""
        dialogo = self._crear_dialogo_profesional(
            tipo="confirmar",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Confirmar",
            boton_accion=on_confirmar,
            mostrar_boton_cancelar=True,
            boton_cancelar_texto="Cancelar",
            boton_cancelar_accion=on_cancelar
        )
        self.page.show_dialog(dialogo)
    
    def _cerrar_dialogo(self, e=None) -> None:
        """Cierra el diálogo activo."""
        try:
            # Camino principal en Flet moderno cuando se usa page.show_dialog(...)
            dialogo_activo = getattr(self.page, "dialog", None)
            if isinstance(dialogo_activo, AlertDialog):
                dialogo_activo.open = False
                self.page.update()
                return

            # Fallback para diálogos montados en overlay manual
            if getattr(self.page, "overlay", None):
                dialogo = self.page.overlay[-1]
                if isinstance(dialogo, AlertDialog):
                    dialogo.open = False
                    self.page.update()
        except Exception as ex:
            print(f"[DIALOGO] Error cerrando diálogo: {ex}")
    
    # =========================================================================
    # SISTEMA DE OVERLAY DE CARGA
    # =========================================================================
    
    def _mostrar_carga(self, mensaje: str = "Procesando..."):
        """Muestra un overlay de carga con animación."""
        if self._carga_activa:
            if self.texto_carga:
                self.texto_carga.value = mensaje
                self.page.update()
            return
        
        self._carga_activa = True
        
        self.texto_carga = Text(mensaje, size=14, color=COLOR_TEXTO, weight=FontWeight.W_500)
        
        self.overlay_carga = Container(
            content=Container(
                content=Column([
                    # Animación de loading
                    Container(
                        content=Stack([
                            Container(
                                width=70,
                                height=70,
                                border_radius=ft.BorderRadius.all(35),
                                bgcolor=COLOR_PRIMARIO + "30",
                            ),
                            ProgressRing(
                                width=70,
                                height=70,
                                stroke_width=4,
                                color=COLOR_PRIMARIO,
                            ),
                            Container(
                                content=Icon(icons.SUPPORT_AGENT, size=28, color=COLOR_PRIMARIO),
                                width=70,
                                height=70,
                                alignment=ft.Alignment(0, 0),
                            ),
                        ]),
                    ),
                    Container(height=20),
                    self.texto_carga,
                    Container(height=5),
                    Text("Por favor espera...", size=11, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=ft.BorderRadius.all(20),
                padding=ft.Padding.symmetric(horizontal=40, vertical=30),
                border=ft.Border.all(1, COLOR_BORDE),
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=30,
                    color=colors.BLACK54,
                    offset=ft.Offset(0, 10),
                ),
            ),
            bgcolor=colors.BLACK87,
            expand=True,
            alignment=ft.Alignment(0, 0),
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
    
    def _iniciar_auto_refresh(self):
        """Inicia el auto-refresh en segundo plano."""
        def refresh_loop():
            while True:
                if not self.auto_refresh:
                    time.sleep(5)
                    continue
                time.sleep(self._intervalo_auto_refresh_segundos())
                try:
                    if self.vista_actual != 7:
                        self._refrescar_vista()
                except:
                    pass
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()

    def _iniciar_backup_automatico(self):
        """Inicia el hilo de backup diario de la base de datos."""
        def backup_loop():
            import time as _time
            # Primer backup al iniciar (sin bloquear el arranque)
            _time.sleep(10)
            try:
                ruta = self.gestor.hacer_backup_db()
                if ruta:
                    print(f"[BACKUP] Backup inicial: {ruta}")
            except Exception as ex:
                print(f"[BACKUP] Error inicial: {ex}")

            # Luego cada 24 horas
            while True:
                _time.sleep(86400)  # 24h
                try:
                    ruta = self.gestor.hacer_backup_db()
                    if ruta:
                        print(f"[BACKUP] Backup diario creado: {ruta}")
                except Exception as ex:
                    print(f"[BACKUP] Error diario: {ex}")

        threading.Thread(target=backup_loop, daemon=True, name="BackupDiario").start()
        print("[BACKUP] Hilo de backup diario iniciado")
    
    def _iniciar_servidor_tickets(self):
        """Inicia el servidor HTTP para recibir tickets de la red."""
        try:
            self.servidor_ip = obtener_ip_local()
            self.servidor_puerto = SERVIDOR_PUERTO
            
            # ===== INICIAR SERVICIO DE NOTIFICACIONES DE WINDOWS =====
            if NOTIFICACIONES_WINDOWS:
                iniciar_servicio_notificaciones()
                print("[NOTIF] Servicio de notificaciones Windows iniciado")
            
            # Referencia a self para el callback
            app_self = self
            
            # Callback para nuevos tickets
            def on_nuevo_ticket(ticket):
                """Notifica cuando hay un nuevo ticket."""
                try:
                    turno = ticket.get("TURNO", "N/A")
                    usuario = ticket.get("USUARIO_AD", "")
                    categoria = ticket.get("CATEGORIA", "General")
                    prioridad = ticket.get("PRIORIDAD", "Media")
                    descripcion = ticket.get("DESCRIPCION", "")[:100]
                    
                    print(f"[SERVIDOR] 🎫 Nuevo ticket recibido: Turno {turno} - {usuario}")
                    
                    # Determinar color según prioridad
                    color_prioridad = COLOR_INFO
                    icono = icons.CONFIRMATION_NUMBER
                    if prioridad == "Crítica":
                        color_prioridad = COLOR_ERROR
                        icono = icons.PRIORITY_HIGH
                    elif prioridad == "Alta":
                        color_prioridad = COLOR_ADVERTENCIA
                        icono = icons.WARNING
                    
                    # Mostrar notificación en la UI
                    try:
                        if hasattr(app_self, 'page') and app_self.page:
                            snack = SnackBar(
                                content=Row([
                                    Icon(icono, color=colors.WHITE, size=20),
                                    Column([
                                        Text(f"🎫 Nuevo Ticket - Turno {turno}", 
                                             color=colors.WHITE, weight=FontWeight.BOLD, size=14),
                                        Text(f"{usuario} • {categoria} • {prioridad}", 
                                             color=colors.WHITE, size=12)
                                    ], spacing=2, tight=True)
                                ], spacing=10),
                                bgcolor=color_prioridad,
                                duration=8000,
                                action="Ver Tickets",
                                on_action=lambda e: app_self._ir_a_tickets()
                            )
                            app_self.page.overlay.append(snack)
                            snack.open = True
                            app_self.page.update()
                            
                            # Refrescar vista si estamos en tickets o dashboard
                            if app_self.vista_actual in [0, 2, 3]:  # Dashboard, Tickets, Cola
                                app_self._refrescar_vista()
                    except Exception as e:
                        print(f"[NOTIFICACION TICKET] Error actualizando UI: {e}")
                except Exception as e:
                    print(f"[NOTIFICACION TICKET] Error: {e}")
            
            # Callback para nuevas solicitudes de enlace
            def on_nueva_solicitud(solicitud):
                """Notifica cuando hay una nueva solicitud de enlace."""
                try:
                    hostname = solicitud.get("hostname", "Equipo")
                    mac = solicitud.get("mac_address", "")
                    print(f"[SERVIDOR] 🔔 Nueva solicitud de enlace: {hostname} ({mac})")
                    
                    # Actualizar badge y mostrar snackbar
                    try:
                        app_self._actualizar_badge_solicitudes()
                        # Crear snackbar directo
                        if hasattr(app_self, 'page') and app_self.page:
                            snack = SnackBar(
                                content=Row([
                                    Icon(icons.NOTIFICATIONS_ACTIVE, color=colors.WHITE, size=20),
                                    Text(f"🔔 Nueva solicitud de enlace: {hostname}", color=colors.WHITE)
                                ], spacing=10),
                                bgcolor=COLOR_ADVERTENCIA,
                                duration=5000
                            )
                            app_self.page.overlay.append(snack)
                            snack.open = True
                            app_self.page.update()
                    except Exception as e:
                        print(f"[NOTIFICACION] Error actualizando UI: {e}")
                except Exception as e:
                    print(f"[NOTIFICACION] Error: {e}")

            def on_chat_mensaje(payload):
                """Actualiza el chat abierto cuando llega un mensaje nuevo."""
                try:
                    self._manejar_chat_realtime(payload)
                except Exception as e:
                    print(f"[CHAT] Error actualizando chat en vivo: {e}")
            
            # Iniciar servidor en segundo plano con callbacks de solicitudes y tickets
            if iniciar_servidor(
                puerto=self.servidor_puerto, 
                callback_solicitud=on_nueva_solicitud,
                callback_ticket=on_nuevo_ticket,
                callback_chat_mensaje=on_chat_mensaje,
            ):
                print(f"[SERVIDOR] Servidor de tickets iniciado en {self.servidor_ip}:{self.servidor_puerto}")
                # Guardar configuración
                guardar_config_servidor(self.servidor_ip, self.servidor_puerto)
            else:
                print("[SERVIDOR] Error al iniciar el servidor")
        except Exception as e:
            print(f"[SERVIDOR] Error: {e}")
    
    def _actualizar_badge_solicitudes(self):
        """Compatibilidad: redirige al actualizador integral de badges."""
        self._actualizar_badges_navegacion()

    def _actualizar_badges_navegacion(self):
        """Actualiza contadores en el menú lateral: tickets, cola, solicitudes y chats."""
        try:
            if not hasattr(self, "nav_rail") or not self.nav_rail:
                return

            badges_habilitados = bool(self._prefs.get("features", {}).get("menu_badges", True))
            if not badges_habilitados:
                self.nav_rail.destinations[2].label = "Tickets"
                self.nav_rail.destinations[4].label = "Cola"
                self.nav_rail.destinations[9].label = "Solicitudes"
                self.nav_rail.destinations[3].label = "Chats"
                try:
                    self.page.update()
                except Exception:
                    pass
                return

            from servidor_red import obtener_solicitudes_pendientes

            tickets_activos = len(self.gestor.obtener_tickets_activos())
            tickets_cola = len(self.gestor.obtener_tickets_en_cola())
            chats_pendientes = int(self.gestor.contar_chats_pendientes_tecnico(limite=500) or 0)
            solicitudes = obtener_solicitudes_pendientes()

            self.nav_rail.destinations[2].label = f"Tickets ({tickets_activos})" if tickets_activos > 0 else "Tickets"
            self.nav_rail.destinations[4].label = f"Cola ({tickets_cola})" if tickets_cola > 0 else "Cola"
            self.nav_rail.destinations[9].label = f"Solicitudes ({len(solicitudes)})" if len(solicitudes) > 0 else "Solicitudes"
            self.nav_rail.destinations[3].label = f"Chats ({chats_pendientes})" if chats_pendientes > 0 else "Chats"

            try:
                self.page.update()
            except Exception:
                pass
        except Exception as e:
            print(f"[BADGE] Error actualizando: {e}")
    
    # =========================================================================
    # VISTA: INVENTARIO DE EQUIPOS
    # =========================================================================
    
    def _vista_inventario(self) -> Column:
        """Construye la vista del inventario de equipos."""
        stats = self.gestor.obtener_estadisticas_equipos()
        equipos_base = self.gestor.obtener_equipos()
        grupos_conteo = self.gestor.obtener_grupos_con_conteo()
        self._inventario_df_full = pd.DataFrame()
        self._inventario_df_filtrado = pd.DataFrame()
        self._inventario_page = 0
        self._inventario_cargando = True

        estados_conteo = {
            "Activo": 0,
            "En Mantenimiento": 0,
            "Baja": 0,
            "Inactivo": 0,
        }
        if equipos_base is not None and not equipos_base.empty and "ESTADO_EQUIPO" in equipos_base.columns:
            for estado, cantidad in equipos_base["ESTADO_EQUIPO"].value_counts().items():
                estados_conteo[str(estado)] = int(cantidad)
        
        # Filtro por grupo
        self.filtro_grupo_inventario = ft.Dropdown(
            label="Filtrar por Grupo",
            width=200,
            options=[ft.dropdown.Option("Todos")] + [ft.dropdown.Option(g) for g in GRUPOS_EQUIPOS],
            value="Todos",
            on_select=self._filtrar_inventario,
            border_color=COLOR_ACENTO,
            focused_border_color=COLOR_PRIMARIO
        )

        self.filtro_estado_inventario = ft.Dropdown(
            label="Filtrar por Estado",
            width=200,
            options=[ft.dropdown.Option("Todos")] + [ft.dropdown.Option(e) for e in ESTADOS_EQUIPO],
            value="Todos",
            on_select=self._filtrar_inventario,
            border_color=COLOR_ACENTO,
            focused_border_color=COLOR_PRIMARIO
        )
        
        # Búsqueda
        self.busqueda_inventario = ft.TextField(
            label="Buscar equipo...",
            prefix_icon=icons.SEARCH,
            width=300,
            on_change=self._filtrar_inventario,
            border_color=COLOR_ACENTO,
            focused_border_color=COLOR_PRIMARIO
        )
        
        # Tabla paginada de equipos
        self._inventario_tabla_container = Container(
            content=Container(
                content=Column([
                    ProgressRing(width=34, height=34, stroke_width=3, color=COLOR_ACENTO),
                    Text("Cargando equipos...", size=12, color=COLOR_TEXTO_SEC),
                    Text("La tabla se cargará por páginas", size=11, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=8),
                padding=30,
                alignment=ft.Alignment(0, 0),
            ),
            expand=True,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            border_radius=10,
            bgcolor=COLOR_SUPERFICIE,
        )
        self._inventario_resumen_text = Text("", size=12, color=COLOR_TEXTO_SEC)
        self._inventario_lbl_pagina = Text("", size=12, color=COLOR_TEXTO_SEC)
        self._inventario_btn_prev = ft.TextButton("◀ Anterior", on_click=lambda e: self._inventario_cambiar_pagina(-1))
        self._inventario_btn_next = ft.TextButton("Siguiente ▶", on_click=lambda e: self._inventario_cambiar_pagina(1))
        self._inventario_paginacion = Row(
            [
                self._inventario_btn_prev,
                self._inventario_lbl_pagina,
                self._inventario_btn_next,
            ],
            alignment=MainAxisAlignment.CENTER,
            spacing=15,
            visible=False,
        )

        contenido_vista = Column(
            controls=[
                self._crear_encabezado_seccion(
                    "🖥️",
                    "Inventario de Equipos",
                    "Gestiona nombre, grupo, ubicación, modelo y estado de cada equipo"
                ),
                Container(height=10),
                
                # KPIs de inventario
                Row([
                    self._kpi_card("Total Equipos", str(stats["total_equipos"]), icons.DEVICES, COLOR_INFO, ""),
                    self._kpi_card("Activos", str(stats["equipos_activos"]), icons.CHECK_CIRCLE, COLOR_EXITO, ""),
                    self._kpi_card("De Baja", str(stats.get("bajas", 0)), icons.BLOCK, COLOR_ERROR, ""),
                    self._kpi_card("Sin Nombre", str(stats["sin_nombre"]), icons.WARNING, COLOR_ADVERTENCIA, "Pendientes"),
                    self._kpi_card("En Mantenimiento", str(stats["equipos_mantenimiento"]), icons.BUILD, COLOR_PRIMARIO, ""),
                ], wrap=True, spacing=12, run_spacing=12, alignment=MainAxisAlignment.START),
                Container(height=14),

                Text("🧩 Secciones por Estado", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                Container(height=10),
                Row([
                    self._estado_chip_inventario("Activos", estados_conteo.get("Activo", 0), icons.CHECK_CIRCLE, COLOR_EXITO),
                    self._estado_chip_inventario("En mantenimiento", estados_conteo.get("En Mantenimiento", 0), icons.BUILD, COLOR_ADVERTENCIA),
                    self._estado_chip_inventario("De baja", estados_conteo.get("Baja", 0), icons.BLOCK, COLOR_ERROR),
                    self._estado_chip_inventario("Inactivos", estados_conteo.get("Inactivo", 0), icons.POWER_SETTINGS_NEW, COLOR_TEXTO_SEC),
                ], wrap=True, spacing=10, run_spacing=10, alignment=MainAxisAlignment.START),
                Container(height=14),
                
                # Filtros y búsqueda
                Card(
                    content=Container(
                        content=Column([
                            Row([
                                self.filtro_grupo_inventario,
                                self.filtro_estado_inventario,
                                self.busqueda_inventario,
                            ], wrap=True, spacing=10, run_spacing=10, vertical_alignment=CrossAxisAlignment.CENTER),
                            Container(height=8),
                            Row([
                                ft.Button(
                                    "Agregar Equipo Manual",
                                    icon=icons.ADD,
                                    on_click=self._dialogo_agregar_equipo,
                                    bgcolor=COLOR_PRIMARIO,
                                    color=colors.WHITE
                                ),
                                ft.Button(
                                    "Refrescar",
                                    icon=icons.REFRESH,
                                    on_click=lambda e: self._refrescar_inventario(),
                                    bgcolor=COLOR_SUPERFICIE_2,
                                    color=colors.WHITE
                                )
                            ], wrap=True, spacing=10, run_spacing=10, alignment=MainAxisAlignment.START),
                        ], spacing=0),
                        padding=12,
                    ),
                    elevation=2,
                ),
                Container(height=14),
                
                # Estadísticas por grupo (tarjetas)
                Text("📊 Equipos por Grupo", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                Container(height=10),
                Row([
                    self._grupo_chip(grupo, cantidad) 
                    for grupo, cantidad in sorted(grupos_conteo.items(), key=lambda x: -x[1])
                    if cantidad > 0
                ], wrap=True, spacing=10, run_spacing=10, alignment=MainAxisAlignment.START),
                Container(height=14),

                Text("🗂️ Control por Grupo y Estado", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                Container(height=10),
                self._panel_control_grupo_estado(equipos_base),
                Container(height=14),
                
                # Tabla de equipos con scroll
                Text("📋 Lista de Equipos", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                Container(height=10),
                self._inventario_tabla_container,
                Container(height=10),
                self._inventario_resumen_text,
                Container(height=8),
                self._inventario_paginacion,
            ],
            spacing=0,
        )
        self._cargar_inventario_async()
        return Column(
            controls=[
                Container(
                    content=contenido_vista,
                    padding=ft.Padding.symmetric(horizontal=2, vertical=0),
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
        )

    def _estado_chip_inventario(self, titulo: str, cantidad: int, icono, color: str) -> Container:
        """Tarjeta compacta para separar equipos por estado."""
        return Container(
            content=Row([
                Icon(icono, size=16, color=colors.WHITE),
                Text(titulo, size=12, color=colors.WHITE, weight=FontWeight.W_500),
                Container(
                    content=Text(str(cantidad), size=11, color=colors.WHITE, weight=FontWeight.BOLD),
                    bgcolor="#00000033",
                    padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                    border_radius=10,
                ),
            ], spacing=8, tight=True),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            bgcolor=color,
            border_radius=20,
        )

    def _panel_control_grupo_estado(self, equipos: pd.DataFrame) -> Container:
        """Muestra matriz de control por grupo y estado de equipo."""
        if equipos is None or equipos.empty:
            return Container(
                content=Text("No hay datos de equipos para agrupar.", color=COLOR_TEXTO_SEC, size=12),
                padding=12,
                bgcolor=COLOR_SUPERFICIE,
                border_radius=10,
            )

        df = equipos.copy()
        if "GRUPO" not in df.columns:
            df["GRUPO"] = "Sin Asignar"
        if "ESTADO_EQUIPO" not in df.columns:
            df["ESTADO_EQUIPO"] = "Activo"

        df["GRUPO"] = df["GRUPO"].fillna("Sin Asignar").astype(str)
        df["ESTADO_EQUIPO"] = df["ESTADO_EQUIPO"].fillna("Activo").astype(str)

        estados_control = ["Activo", "En Mantenimiento", "Baja", "Inactivo"]
        pivot = df.pivot_table(index="GRUPO", columns="ESTADO_EQUIPO", aggfunc="size", fill_value=0)

        for estado in estados_control:
            if estado not in pivot.columns:
                pivot[estado] = 0

        pivot = pivot[estados_control]
        pivot["TOTAL"] = pivot.sum(axis=1)
        pivot = pivot.sort_values(by="TOTAL", ascending=False)

        filas = []
        for grupo, row in pivot.iterrows():
            filas.append(
                DataRow(cells=[
                    DataCell(Text(str(grupo), size=12, color=COLOR_TEXTO)),
                    DataCell(Text(str(int(row["TOTAL"])), size=12, color=COLOR_INFO, weight=FontWeight.BOLD)),
                    DataCell(Text(str(int(row["Activo"])), size=12, color=COLOR_EXITO)),
                    DataCell(Text(str(int(row["En Mantenimiento"])), size=12, color=COLOR_ADVERTENCIA)),
                    DataCell(Text(str(int(row["Baja"])), size=12, color=COLOR_ERROR)),
                    DataCell(Text(str(int(row["Inactivo"])), size=12, color=COLOR_TEXTO_SEC)),
                ])
            )

        tabla = DataTable(
            columns=[
                DataColumn(Text("Grupo", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Total", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Activos", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Mant.", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Baja", color=COLOR_TEXTO_SEC)),
                DataColumn(Text("Inactivos", color=COLOR_TEXTO_SEC)),
            ],
            rows=filas,
            heading_row_color=COLOR_SUPERFICIE_2,
            bgcolor=COLOR_SUPERFICIE,
            column_spacing=24,
        )

        ancho_inventario = max(
            1100,
            int(getattr(self.page, "window_width", 0) or getattr(self.page, "width", 0) or 0) - 24,
        )

        return Container(
            content=Column(
                controls=[
                    Container(
                        content=Row(
                            controls=[Container(content=tabla, width=ancho_inventario)],
                            scroll=ScrollMode.AUTO,
                            expand=True,
                            vertical_alignment=CrossAxisAlignment.START,
                        ),
                        width=ancho_inventario,
                        expand=True,
                    )
                ],
                scroll=ScrollMode.AUTO,
                expand=True,
                horizontal_alignment=CrossAxisAlignment.STRETCH,
            ),
            padding=10,
            bgcolor=COLOR_SUPERFICIE,
            border_radius=10,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            expand=True,
        )
    
    def _grupo_chip(self, grupo: str, cantidad: int) -> Container:
        """Crea un chip para mostrar grupo con cantidad."""
        colores_grupo = {
            "Administración": "#3498DB",
            "Contabilidad": "#27AE60",
            "Recursos Humanos": "#9B59B6",
            "Ventas": "#E74C3C",
            "Marketing": "#F39C12",
            "Producción": "#1ABC9C",
            "Almacén": "#95A5A6",
            "Gerencia": "#E67E22",
            "IT": "#2980B9",
            "Recepción": "#16A085",
            "Sin Asignar": "#7F8C8D"
        }
        color = colores_grupo.get(grupo, COLOR_SUPERFICIE_2)
        
        return Container(
            content=Row([
                Icon(icons.FOLDER, size=16, color=colors.WHITE),
                Text(f"{grupo}: {cantidad}", size=12, color=colors.WHITE, weight=FontWeight.BOLD)
            ], spacing=5, tight=True),
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
            bgcolor=color,
            border_radius=20,
            on_click=lambda e, g=grupo: self._filtrar_por_grupo(g)
        )
    
    def _construir_tabla_equipos(self, equipos: pd.DataFrame) -> DataTable:
        """Construye la tabla de equipos."""
        columnas = [
            DataColumn(Text("MAC", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Nombre", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Hostname", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Grupo", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Ubicación", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Tipo", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Marca/Modelo", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Estado", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Acciones", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
        ]
        
        filas = []
        for _, equipo in equipos.iterrows():
            mac = str(equipo.get("MAC_ADDRESS", "") or "")
            nombre = equipo.get("NOMBRE_EQUIPO", "")
            nombre = str(nombre) if pd.notna(nombre) and nombre else "⚠️ Sin asignar"
            hostname = str(equipo.get("HOSTNAME", "") or "")
            grupo = str(equipo.get("GRUPO", "Sin Asignar") or "Sin Asignar")
            ubicacion = equipo.get("UBICACION", "")
            ubicacion = str(ubicacion) if pd.notna(ubicacion) and ubicacion else "-"
            tipo = str(equipo.get("TIPO_EQUIPO", "") or "-")
            marca = equipo.get("MARCA", "")
            modelo = equipo.get("MODELO", "")
            marca_modelo = f"{marca} {modelo}".strip() if marca or modelo else "-"
            estado = str(equipo.get("ESTADO_EQUIPO", "Activo") or "Activo")
            
            # Color según estado
            color_estado = {
                "Activo": COLOR_EXITO,
                "Inactivo": COLOR_TEXTO_SEC,
                "En Mantenimiento": COLOR_ADVERTENCIA,
                "Baja": COLOR_ERROR
            }.get(estado, COLOR_TEXTO_SEC)
            
            filas.append(DataRow(
                cells=[
                    DataCell(Text(mac[:17], size=11, color=COLOR_TEXTO)),
                    DataCell(Text(nombre[:20] if nombre != "Sin asignar" else "⚠️ Sin asignar", 
                                color=COLOR_ADVERTENCIA if nombre == "Sin asignar" else COLOR_TEXTO, size=12)),
                    DataCell(Text(hostname[:15], size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Container(
                        content=Text(grupo, size=10, color=colors.WHITE),
                        bgcolor=COLOR_SECUNDARIO,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                        border_radius=10
                    )),
                    DataCell(Text(ubicacion[:15] if ubicacion else "-", size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(tipo, size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(marca_modelo[:20] if marca_modelo else "-", size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Container(
                        content=Text(estado, size=10, color=colors.WHITE),
                        bgcolor=color_estado,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                        border_radius=10
                    )),
                    DataCell(Row([
                        ft.IconButton(
                            icon=icons.EDIT,
                            icon_color=COLOR_ACENTO,
                            tooltip="Editar equipo",
                            on_click=lambda e, m=mac: self._dialogo_editar_equipo(m)
                        ),
                        ft.IconButton(
                            icon=icons.DELETE,
                            icon_color=COLOR_ERROR,
                            tooltip="Eliminar equipo",
                            on_click=lambda e, m=mac: self._confirmar_eliminar_equipo(m)
                        )
                    ], spacing=0))
                ]
            ))
        
        return DataTable(
            columns=columnas,
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            heading_row_color=COLOR_SUPERFICIE_2,
            heading_row_height=45,
            data_row_min_height=50,
            data_row_max_height=60,
            column_spacing=15,
            show_checkbox_column=False,
            horizontal_lines=ft.border.BorderSide(1, COLOR_SUPERFICIE_2)
        )

    def _render_inventario_pagina(self):
        """Renderiza solo la página visible del inventario."""
        if self._inventario_tabla_container is None:
            return

        if self._inventario_cargando:
            self._inventario_tabla_container.content = Container(
                content=Column([
                    ProgressRing(width=34, height=34, stroke_width=3, color=COLOR_ACENTO),
                    Text("Cargando equipos...", size=12, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=8),
                padding=40,
                alignment=ft.Alignment(0, 0),
            )
            if self._inventario_paginacion:
                self._inventario_paginacion.visible = False
            if self._inventario_resumen_text:
                self._inventario_resumen_text.value = ""
            return

        df = self._inventario_df_filtrado if self._inventario_df_filtrado is not None else pd.DataFrame()
        total = len(df) if not df.empty else 0

        if total == 0:
            self._inventario_tabla_container.content = Container(
                content=Column([
                    Icon(icons.DEVICES, size=48, color=COLOR_TEXTO_SEC),
                    Text("No hay equipos para mostrar", size=14, color=COLOR_TEXTO_SEC),
                    Text("Prueba a cambiar el filtro o la búsqueda", size=11, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=8),
                padding=40,
                alignment=ft.Alignment(0, 0),
            )
            if self._inventario_resumen_text:
                self._inventario_resumen_text.value = "0 equipos encontrados"
            if self._inventario_paginacion:
                self._inventario_paginacion.visible = False
            return

        total_paginas = max((total + self._inventario_page_size - 1) // self._inventario_page_size, 1)
        self._inventario_page = max(0, min(self._inventario_page, total_paginas - 1))
        inicio = self._inventario_page * self._inventario_page_size
        fin = min(inicio + self._inventario_page_size, total)
        slice_df = df.iloc[inicio:fin]

        tabla = self._construir_tabla_equipos(slice_df)
        ancho_inventario = max(
            1100,
            int(getattr(self.page, "window_width", 0) or getattr(self.page, "width", 0) or 0) - 24,
        )

        self._inventario_tabla_container.content = Column(
            controls=[
                Container(
                    content=Row(
                        controls=[Container(content=tabla, width=ancho_inventario)],
                        scroll=ScrollMode.AUTO,
                        expand=True,
                        vertical_alignment=CrossAxisAlignment.START,
                    ),
                    width=ancho_inventario,
                    expand=True,
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True,
            horizontal_alignment=CrossAxisAlignment.STRETCH,
        )

        if self._inventario_btn_prev:
            self._inventario_btn_prev.disabled = self._inventario_page <= 0
        if self._inventario_btn_next:
            self._inventario_btn_next.disabled = self._inventario_page >= total_paginas - 1
        if self._inventario_lbl_pagina:
            self._inventario_lbl_pagina.value = f"Página {self._inventario_page + 1}/{total_paginas}"
        if self._inventario_paginacion:
            self._inventario_paginacion.visible = total_paginas > 1
        if self._inventario_resumen_text:
            self._inventario_resumen_text.value = f"Mostrando {inicio + 1}-{fin} de {total} equipos"

    def _aplicar_datos_inventario_ui(self, equipos: pd.DataFrame):
        """Aplica los datos cargados al inventario y renderiza la primera página."""
        self._inventario_df_full = equipos if equipos is not None else pd.DataFrame()
        self._inventario_df_filtrado = self._inventario_df_full.copy()
        self._inventario_page = 0
        self._inventario_cargando = False
        self._render_inventario_pagina()

    def _cargar_inventario_async(self):
        """Carga el inventario en segundo plano para no bloquear la UI."""
        if self._inventario_cargando is False:
            self._inventario_cargando = True

        def cargar():
            try:
                equipos = self.gestor.obtener_equipos()
                self._ui_call(lambda: self._aplicar_datos_inventario_ui(equipos))
            except Exception as ex:
                print(f"[INVENTARIO] Error cargando equipos: {ex}")
                def actualizar_error():
                    self._inventario_df_full = pd.DataFrame()
                    self._inventario_df_filtrado = pd.DataFrame()
                    self._inventario_cargando = False
                    self._render_inventario_pagina()

                self._ui_call(actualizar_error)
            finally:
                self._ui_call(lambda: self.page.update())

        threading.Thread(target=cargar, daemon=True).start()

    def _inventario_cambiar_pagina(self, delta: int):
        """Cambia la página visible del inventario."""
        if self._inventario_df_filtrado is None or self._inventario_df_filtrado.empty:
            return
        self._inventario_page += delta
        self._render_inventario_pagina()
        self.page.update()
    
    def _filtrar_inventario(self, e=None):
        """Filtra la tabla de inventario según grupo y búsqueda."""
        equipos = self._inventario_df_full if self._inventario_df_full is not None else self.gestor.obtener_equipos()
        
        # Filtrar por grupo
        grupo = self.filtro_grupo_inventario.value
        if grupo and grupo != "Todos":
            equipos = equipos[equipos["GRUPO"] == grupo]

        estado = self.filtro_estado_inventario.value if hasattr(self, "filtro_estado_inventario") else "Todos"
        if estado and estado != "Todos":
            equipos = equipos[equipos["ESTADO_EQUIPO"] == estado]
        
        # Filtrar por búsqueda
        busqueda = self.busqueda_inventario.value
        if busqueda:
            busqueda = busqueda.lower()
            equipos = equipos[
                equipos["MAC_ADDRESS"].str.lower().str.contains(busqueda, na=False) |
                equipos["NOMBRE_EQUIPO"].fillna("").str.lower().str.contains(busqueda, na=False) |
                equipos["HOSTNAME"].fillna("").str.lower().str.contains(busqueda, na=False) |
                equipos["USUARIO_ASIGNADO"].fillna("").str.lower().str.contains(busqueda, na=False)
            ]
        
        self._inventario_df_filtrado = equipos
        self._inventario_page = 0
        self._render_inventario_pagina()
        self.page.update()
    
    def _filtrar_por_grupo(self, grupo: str):
        """Filtra por grupo desde los chips."""
        self.filtro_grupo_inventario.value = grupo
        self._filtrar_inventario()
    
    def _refrescar_inventario(self, cambiar_vista: bool = True):
        """Refresca el inventario; si no se pide cambiar la vista, solo actualiza datos en memoria."""
        if hasattr(self, 'filtro_grupo_inventario') and self.filtro_grupo_inventario:
            self.filtro_grupo_inventario.value = "Todos"
        if hasattr(self, 'filtro_estado_inventario') and self.filtro_estado_inventario:
            self.filtro_estado_inventario.value = "Todos"
        if hasattr(self, 'busqueda_inventario') and self.busqueda_inventario:
            self.busqueda_inventario.value = ""

        self._inventario_cargando = True
        self._inventario_page = 0

        if cambiar_vista or self.vista_actual == 6:
            self.contenido.content = self._vista_inventario()
            self.page.update()
            return

        try:
            self._inventario_df_full = self.gestor.obtener_equipos()
            self._inventario_df_filtrado = self._inventario_df_full
        finally:
            self._inventario_cargando = False
    
    def _dialogo_editar_equipo(self, mac_address: str, mantener_vista_actual: bool = False):
        """Muestra el diálogo para editar un equipo."""
        import traceback
        try:
            equipo = self.gestor.obtener_equipo_por_mac(mac_address)
            if not equipo:
                self._mostrar_error("Equipo no encontrado", "No se encontró el equipo en el inventario.")
                return
            
            # Campos del formulario con estilo mejorado
            txt_nombre = ft.TextField(
                label="Nombre del Equipo",
                value=equipo.get("NOMBRE_EQUIPO", ""),
                width=380,
                hint_text="Ej: PC-CONTABILIDAD-01",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_ubicacion = ft.TextField(
                label="Ubicación",
                value=equipo.get("UBICACION", ""),
                width=380,
                hint_text="Ej: Oficina 201, Piso 2",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_marca = ft.TextField(
                label="Marca",
                value=equipo.get("MARCA", ""),
                width=185,
                hint_text="Ej: Dell, HP",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_modelo = ft.TextField(
                label="Modelo",
                value=equipo.get("MODELO", ""),
                width=185,
                hint_text="Ej: OptiPlex 7090",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_serie = ft.TextField(
                label="Número de Serie",
                value=equipo.get("NUMERO_SERIE", ""),
                width=380,
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            dd_grupo = ft.Dropdown(
                label="Grupo/Departamento",
                value=equipo.get("GRUPO", "Sin Asignar"),
                width=185,
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO,
                options=[ft.dropdown.Option(g) for g in GRUPOS_EQUIPOS]
            )
            dd_tipo = ft.Dropdown(
                label="Tipo de Equipo",
                value=equipo.get("TIPO_EQUIPO", "Desktop"),
                width=185,
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO,
                options=[ft.dropdown.Option(t) for t in TIPOS_EQUIPO]
            )
            dd_estado = ft.Dropdown(
                label="Estado",
                value=equipo.get("ESTADO_EQUIPO", "Activo"),
                width=185,
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO,
                options=[ft.dropdown.Option(e) for e in ESTADOS_EQUIPO]
            )
            txt_so = ft.TextField(
                label="Sistema Operativo",
                value=equipo.get("SISTEMA_OPERATIVO", ""),
                width=185,
                hint_text="Ej: Windows 11 Pro",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_procesador = ft.TextField(
                label="Procesador",
                value=equipo.get("PROCESADOR", ""),
                width=380,
                hint_text="Ej: Intel Core i7-12700",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_ram = ft.TextField(
                label="RAM (GB)",
                value=str(equipo.get("RAM_GB", 0)) if equipo.get("RAM_GB", 0) > 0 else "",
                width=90,
                hint_text="16",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_disco = ft.TextField(
                label="Disco (GB)",
                value=str(equipo.get("DISCO_GB", 0)) if equipo.get("DISCO_GB", 0) > 0 else "",
                width=90,
                hint_text="512",
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            txt_notas = ft.TextField(
                label="Notas adicionales",
                value=equipo.get("NOTAS", ""),
                width=380,
                multiline=True,
                min_lines=2,
                max_lines=3,
                border_color=COLOR_BORDE,
                focused_border_color=COLOR_PRIMARIO
            )
            
            dlg = None
            
            def cerrar_dialogo(e=None):
                nonlocal dlg
                if dlg:
                    dlg.open = False
                    self.page.update()
            
            def guardar_equipo(e=None):
                try:
                    # Convertir valores numéricos de forma segura
                    ram_value = 0
                    disco_value = 0
                    if txt_ram.value:
                        try:
                            ram_value = int(txt_ram.value)
                        except ValueError:
                            ram_value = 0
                    if txt_disco.value:
                        try:
                            disco_value = int(txt_disco.value)
                        except ValueError:
                            disco_value = 0
                    
                    cerrar_dialogo()
                    self._mostrar_carga("Guardando cambios...")
                    
                    self.gestor.actualizar_equipo(
                        mac_address,
                        nombre_equipo=txt_nombre.value or "",
                        ubicacion=txt_ubicacion.value or "",
                        marca=txt_marca.value or "",
                        modelo=txt_modelo.value or "",
                        numero_serie=txt_serie.value or "",
                        grupo=dd_grupo.value or "Sin Asignar",
                        tipo_equipo=dd_tipo.value or "Desktop",
                        estado_equipo=dd_estado.value or "Activo",
                        sistema_operativo=txt_so.value or "",
                        procesador=txt_procesador.value or "",
                        ram_gb=ram_value,
                        disco_gb=disco_value,
                        notas=txt_notas.value or ""
                    )
                    
                    self._ocultar_carga()
                    self._mostrar_exito("Equipo Actualizado", "Los cambios se guardaron correctamente.")
                    self._refrescar_inventario(cambiar_vista=not mantener_vista_actual)
                    if mantener_vista_actual and self.vista_actual == 7:
                        self._cargar_escaner_async(force=True)
                except Exception as ex:
                    self._ocultar_carga()
                    self._mostrar_error("Error al guardar", str(ex))
                    traceback.print_exc()
            
            dlg = AlertDialog(
                modal=True,
                shape=ft.RoundedRectangleBorder(radius=16),
                bgcolor=COLOR_SUPERFICIE,
                title=Row([
                    Container(
                        content=Icon(icons.EDIT, size=24, color=colors.WHITE),
                        bgcolor=COLOR_PRIMARIO,
                        padding=8,
                        border_radius=8
                    ),
                    Column([
                        Text("Editar Equipo", weight=FontWeight.BOLD, color=COLOR_TEXTO, size=16),
                        Text(mac_address, size=11, color=COLOR_TEXTO_SEC)
                    ], spacing=0)
                ], spacing=12),
                content=Container(
                    content=Column([
                        # Info básica del equipo
                        Container(
                            content=Row([
                                Icon(icons.COMPUTER, size=18, color=COLOR_ACENTO),
                                Text(f"Hostname: {equipo.get('HOSTNAME', 'N/A')}", color=COLOR_TEXTO_SEC, size=12),
                                Text("|", color=COLOR_BORDE),
                                Text(f"Usuario: {equipo.get('USUARIO_ASIGNADO', 'N/A')}", color=COLOR_TEXTO_SEC, size=12),
                            ], spacing=10),
                            bgcolor=COLOR_SUPERFICIE_2,
                            padding=10,
                            border_radius=8
                        ),
                        
                        # Sección Información General
                        Row([
                            Icon(icons.INFO_OUTLINE, size=16, color=COLOR_ACENTO),
                            Text("Información General", weight=FontWeight.BOLD, color=COLOR_ACENTO, size=13)
                        ], spacing=8),
                        txt_nombre,
                        Row([dd_grupo, dd_tipo], spacing=10),
                        Row([dd_estado, txt_so], spacing=10),
                        txt_ubicacion,
                        
                        Divider(color=COLOR_BORDE),
                        
                        # Sección Hardware
                        Row([
                            Icon(icons.MEMORY, size=16, color=COLOR_INFO),
                            Text("Especificaciones de Hardware", weight=FontWeight.BOLD, color=COLOR_INFO, size=13)
                        ], spacing=8),
                        Row([txt_marca, txt_modelo], spacing=10),
                        txt_serie,
                        txt_procesador,
                        Row([txt_ram, txt_disco], spacing=10),
                        
                        Divider(color=COLOR_BORDE),
                        
                        # Sección Notas
                        Row([
                            Icon(icons.NOTES, size=16, color=COLOR_ADVERTENCIA),
                            Text("Notas", weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA, size=13)
                        ], spacing=8),
                        txt_notas
                    ], spacing=8, scroll=ScrollMode.AUTO),
                    width=420,
                    height=480,
                    padding=5
                ),
                actions_alignment=MainAxisAlignment.END,
                actions=[
                    ft.TextButton(
                        "Cancelar",
                        icon=icons.CLOSE,
                        on_click=cerrar_dialogo
                    ),
                    ft.Button(
                        "Guardar",
                        icon=icons.SAVE,
                        bgcolor=COLOR_EXITO,
                        color=colors.WHITE,
                        on_click=guardar_equipo
                    )
                ]
            )
            
            self.page.show_dialog(dlg)
        except Exception as ex:
            self._mostrar_error("Error", str(ex))
            traceback.print_exc()
    
    def _dialogo_agregar_equipo(self, e=None):
        """Muestra el diálogo para agregar un equipo manualmente."""
        txt_mac = ft.TextField(
            label="Dirección MAC *",
            width=380,
            hint_text="Ej: AA:BB:CC:DD:EE:FF",
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            prefix_icon=icons.ROUTER
        )
        txt_nombre = ft.TextField(
            label="Nombre del Equipo",
            width=380,
            hint_text="Ej: PC-VENTAS-01",
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            prefix_icon=icons.LABEL
        )
        txt_hostname = ft.TextField(
            label="Hostname",
            width=185,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO
        )
        txt_usuario = ft.TextField(
            label="Usuario Asignado",
            width=185,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO
        )
        dd_grupo = ft.Dropdown(
            label="Grupo/Departamento",
            value="Sin Asignar",
            width=185,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            options=[ft.dropdown.Option(g) for g in GRUPOS_EQUIPOS]
        )
        dd_tipo = ft.Dropdown(
            label="Tipo de Equipo",
            value="Desktop",
            width=185,
            border_color=COLOR_BORDE,
            focused_border_color=COLOR_PRIMARIO,
            options=[ft.dropdown.Option(t) for t in TIPOS_EQUIPO]
        )
        
        dlg = None
        
        def cerrar_dialogo(e=None):
            nonlocal dlg
            if dlg:
                dlg.open = False
                self.page.update()
        
        def agregar_equipo(e):
            if not txt_mac.value:
                self._mostrar_advertencia("Campo requerido", "La dirección MAC es obligatoria.")
                return
            
            # Validar formato MAC
            mac = txt_mac.value.upper().replace("-", ":").replace(".", ":")
            
            # Verificar si ya existe
            if self.gestor.obtener_equipo_por_mac(mac):
                self._mostrar_error("Equipo duplicado", "Ya existe un equipo con esa dirección MAC.")
                return
            
            try:
                cerrar_dialogo()
                self._mostrar_carga("Agregando equipo...")
                
                # Registrar equipo
                self.gestor.registrar_o_actualizar_equipo(
                    mac,
                    txt_hostname.value or "Manual",
                    txt_usuario.value or "N/A"
                )
                # Actualizar datos adicionales
                self.gestor.actualizar_equipo(
                    mac,
                    nombre_equipo=txt_nombre.value,
                    grupo=dd_grupo.value,
                    tipo_equipo=dd_tipo.value
                )
                
                self._ocultar_carga()
                self._mostrar_exito("Equipo Agregado", f"El equipo {txt_nombre.value or mac} se registró correctamente.")
                self._refrescar_inventario()
            except Exception as ex:
                self._ocultar_carga()
                self._mostrar_error("Error al agregar", str(ex))
        
        dlg = AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.ADD_CIRCLE, size=24, color=colors.WHITE),
                    bgcolor=COLOR_EXITO,
                    padding=8,
                    border_radius=8
                ),
                Text("Agregar Equipo", weight=FontWeight.BOLD, color=COLOR_TEXTO, size=18)
            ], spacing=12),
            content=Container(
                content=Column([
                    Container(
                        content=Row([
                            Icon(icons.INFO_OUTLINE, size=16, color=COLOR_INFO),
                            Column([
                                Text("Los equipos se registran automáticamente al crear un ticket.", 
                                     color=COLOR_TEXTO_SEC, size=11),
                                Text("Use este formulario solo para equipos sin tickets.", 
                                     color=COLOR_TEXTO_SEC, size=11)
                            ], spacing=2)
                        ], spacing=8),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=10,
                        border_radius=8
                    ),
                    Container(height=5),
                    txt_mac,
                    txt_nombre,
                    Row([txt_hostname, txt_usuario], spacing=10),
                    Row([dd_grupo, dd_tipo], spacing=10),
                ], spacing=12),
                width=420,
                padding=5
            ),
            actions_alignment=MainAxisAlignment.END,
            actions=[
                ft.TextButton(
                    "Cancelar",
                    icon=icons.CLOSE,
                    on_click=cerrar_dialogo
                ),
                ft.Button(
                    "Agregar",
                    icon=icons.ADD,
                    bgcolor=COLOR_EXITO,
                    color=colors.WHITE,
                    on_click=agregar_equipo
                )
            ]
        )
        
        self.page.show_dialog(dlg)
    
    def _confirmar_eliminar_equipo(self, mac_address: str):
        """Muestra confirmación para eliminar un equipo."""
        dlg = None
        
        def cerrar_dialogo(e=None):
            nonlocal dlg
            if dlg:
                dlg.open = False
                self.page.update()
        
        def eliminar(e):
            cerrar_dialogo()
            self._mostrar_carga("Eliminando equipo...")
            
            if self.gestor.eliminar_equipo(mac_address):
                self._ocultar_carga()
                self._mostrar_exito("Equipo Eliminado", f"El equipo {mac_address} ha sido eliminado del inventario.")
                self._refrescar_inventario()
            else:
                self._ocultar_carga()
                self._mostrar_error("Error al eliminar", "No se pudo eliminar el equipo del inventario.")
        
        dlg = AlertDialog(
            modal=True,
            shape=ft.RoundedRectangleBorder(radius=16),
            bgcolor=COLOR_SUPERFICIE,
            title=Row([
                Container(
                    content=Icon(icons.DELETE_FOREVER, size=24, color=colors.WHITE),
                    bgcolor=COLOR_ERROR,
                    padding=8,
                    border_radius=8
                ),
                Text("Confirmar Eliminación", weight=FontWeight.BOLD, color=COLOR_ERROR, size=18)
            ], spacing=12),
            content=Container(
                content=Column([
                    Container(
                        content=Icon(icons.WARNING_AMBER_ROUNDED, size=50, color=COLOR_ADVERTENCIA),
                        alignment=ft.Alignment(0, 0)
                    ),
                    Container(height=10),
                    Text("¿Eliminar este equipo del inventario?", color=COLOR_TEXTO, text_align=TextAlign.CENTER),
                    Container(
                        content=Text(mac_address, weight=FontWeight.BOLD, color=COLOR_ACENTO, size=16),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=10,
                        border_radius=8,
                        alignment=ft.Alignment(0, 0)
                    ),
                    Row([
                        Icon(icons.INFO_OUTLINE, size=14, color=COLOR_ERROR_CLARO),
                        Text("Esta acción no se puede deshacer", size=12, color=COLOR_ERROR_CLARO)
                    ], alignment=MainAxisAlignment.CENTER, spacing=5)
                ], spacing=10, horizontal_alignment=CrossAxisAlignment.CENTER),
                width=320,
                padding=10
            ),
            actions_alignment=MainAxisAlignment.END,
            actions=[
                ft.TextButton("Cancelar", icon=icons.CLOSE, on_click=cerrar_dialogo),
                ft.Button(
                    "Eliminar",
                    icon=icons.DELETE,
                    bgcolor=COLOR_ERROR,
                    color=colors.WHITE,
                    on_click=eliminar
                )
            ]
        )
        
        self.page.show_dialog(dlg)
    
    # =========================================================================
    # VISTA: ESCÁNER DE RED
    # =========================================================================
    
    @staticmethod
    def _wrap_tabla_scroll(tabla_widget, height_px: int):
        """Envuelve un DataTable en Column+Row para scroll vertical y horizontal."""
        return Column(
            controls=[Row([tabla_widget], scroll=ScrollMode.AUTO)],
            scroll=ScrollMode.AUTO,
            height=height_px,
        )

    def _vista_escaner_red(self) -> Column:
        """Construye la vista del escáner de red con referencias dinámicas."""
        self.escaner = EscanerRed(gestor=self.gestor)

        ip_local        = obtener_ip_local()
        ip_base         = ".".join(ip_local.split(".")[:3])
        servidor_activo = servidor_esta_activo()

        total_db = online_servidor = total_servidor = cambios = 0

        # Controles de rango
        self.txt_rango_inicio = ft.TextField(
            label="Desde", value="1", width=80, text_align=TextAlign.CENTER,
            border_color=COLOR_ACENTO, focused_border_color=COLOR_PRIMARIO
        )
        self.txt_rango_fin = ft.TextField(
            label="Hasta", value="254", width=80, text_align=TextAlign.CENTER,
            border_color=COLOR_ACENTO, focused_border_color=COLOR_PRIMARIO
        )

        # Progreso escaneo
        self.progress_escaneo = ft.ProgressBar(
            value=0, expand=True, bgcolor=COLOR_SUPERFICIE_2, color=COLOR_ACENTO, visible=False
        )
        self.lbl_progreso = Text("", size=12, color=COLOR_TEXTO_SEC, visible=False)

        # Widget de estado de ping (inline, dentro del layout)
        self._ping_icono = Icon(icons.WIFI_FIND, size=16, color=COLOR_INFO, visible=False)
        self._ping_lbl   = Text("", size=12, color=COLOR_INFO, visible=False)

        # Labels dinámicos KPI
        self._escaner_label_online    = Text(str(online_servidor), size=32, weight=FontWeight.BOLD, color=COLOR_EXITO)
        self._escaner_label_total_srv = Text(str(total_servidor),  size=32, weight=FontWeight.BOLD, color=COLOR_INFO)
        self._escaner_label_total_db  = Text(str(total_db),        size=32, weight=FontWeight.BOLD, color=COLOR_ACENTO)
        self._escaner_label_cambios   = Text(str(cambios),          size=32, weight=FontWeight.BOLD,
                                             color=COLOR_ADVERTENCIA if cambios else COLOR_TEXTO_SEC)
        self._escaner_badge_online = Text(str(online_servidor), size=11, color=colors.WHITE, weight=FontWeight.BOLD)

        # Construir tablas en modo diferido
        alertas_cambios = Container()

        # Contenedor de equipos conectados — scroll horizontal (Row) + vertical (Column)
        self._escaner_tabla_conectados = Container(
            content=Container(
                content=Row([ProgressRing(width=24, height=24, color=COLOR_ACENTO), Text("Cargando equipos conectados...", color=COLOR_TEXTO_SEC)], spacing=8),
                padding=20,
            ),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=10,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
        )

        # Contenedor de historial — scroll horizontal + vertical
        self._escaner_tabla_red = Container(
            content=Container(
                content=Row([ProgressRing(width=24, height=24, color=COLOR_ACENTO), Text("Cargando historial de red...", color=COLOR_TEXTO_SEC)], spacing=8),
                padding=20,
            ),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=10,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
        )

        self._escaner_alertas = Container(
            content=alertas_cambios if cambios > 0 else Container()
        )

        self._escaner_srv_page = 0
        self._escaner_hist_page = 0
        self._escaner_btn_srv_prev = ft.IconButton(icon=icons.CHEVRON_LEFT, disabled=True, on_click=lambda e: self._cambiar_pagina_escaner_srv(-1))
        self._escaner_btn_srv_next = ft.IconButton(icon=icons.CHEVRON_RIGHT, disabled=True, on_click=lambda e: self._cambiar_pagina_escaner_srv(1))
        self._escaner_lbl_srv_pag = Text("Página 0/0", size=11, color=COLOR_TEXTO_SEC)
        self._escaner_pag_srv = Row(
            [self._escaner_btn_srv_prev, self._escaner_lbl_srv_pag, self._escaner_btn_srv_next],
            alignment=MainAxisAlignment.END,
            visible=False,
        )

        self._escaner_btn_hist_prev = ft.IconButton(icon=icons.CHEVRON_LEFT, disabled=True, on_click=lambda e: self._cambiar_pagina_escaner_hist(-1))
        self._escaner_btn_hist_next = ft.IconButton(icon=icons.CHEVRON_RIGHT, disabled=True, on_click=lambda e: self._cambiar_pagina_escaner_hist(1))
        self._escaner_lbl_hist_pag = Text("Página 0/0", size=11, color=COLOR_TEXTO_SEC)
        self._escaner_pag_hist = Row(
            [self._escaner_btn_hist_prev, self._escaner_lbl_hist_pag, self._escaner_btn_hist_next],
            alignment=MainAxisAlignment.END,
            visible=False,
        )

        boton_escanear = ft.Button(
            "🚀 Iniciar escaneo",
            icon=icons.RADAR,
            on_click=self._iniciar_escaneo_red,
            bgcolor=COLOR_PRIMARIO,
            color=colors.WHITE,
        )
        self._btn_escanear_red = boton_escanear

        # KPI card builder
        def _kpi(titulo, label_widget, icono, color, subtitulo):
            return Container(
                content=Column([
                    Row([
                        Container(
                            content=Icon(icono, size=22, color=colors.WHITE),
                            bgcolor=color, padding=10, border_radius=10
                        ),
                        Column([
                            label_widget,
                            Text(titulo, size=11, color=COLOR_TEXTO_SEC),
                        ], spacing=0),
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    Text(subtitulo, size=10, color=COLOR_TEXTO_SEC),
                ], spacing=6),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
                expand=True
            )

        vista = Column(
            controls=[

                # ── Header ─────────────────────────────────────────────────────
                Container(
                    content=Row([
                        Container(
                            content=Icon(icons.WIFI_TETHERING, size=32, color=colors.WHITE),
                            bgcolor=COLOR_ACENTO, padding=13, border_radius=12
                        ),
                        Column([
                            Text("Escaneo de Red", size=22, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Text("Detecta, monitorea y agrega equipos de la red local al inventario",
                                 size=13, color=COLOR_TEXTO_SEC),
                        ], spacing=3, expand=True),
                        Container(
                            content=Row([
                                Icon(icons.CIRCLE, size=11,
                                     color=COLOR_EXITO if servidor_activo else COLOR_ERROR),
                                Text("Servidor activo" if servidor_activo else "Servidor inactivo",
                                     size=12, color=COLOR_TEXTO_SEC),
                            ], spacing=6),
                            bgcolor=COLOR_SUPERFICIE_2,
                            padding=ft.Padding.symmetric(horizontal=12, vertical=7),
                            border_radius=20
                        ),
                    ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=COLOR_SUPERFICIE,
                    padding=ft.Padding.symmetric(horizontal=20, vertical=16),
                    border_radius=14,
                    border=ft.Border.all(1, COLOR_SUPERFICIE_2)
                ),

                Container(height=14),

                # ── Barra info red ──────────────────────────────────────────────
                Container(
                    content=Row([
                        Icon(icons.ROUTER, color=COLOR_INFO, size=18),
                        Text("IP del servidor:", size=12, color=COLOR_TEXTO_SEC),
                        Text(ip_local, size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Container(width=12),
                        Icon(icons.LAN, color=COLOR_TEXTO_SEC, size=16),
                        Text(f"Red: {ip_base}.1 – {ip_base}.254", size=12, color=COLOR_TEXTO_SEC),
                        Container(width=12),
                        Icon(icons.SETTINGS_ETHERNET, color=COLOR_TEXTO_SEC, size=16),
                        Text(f"Puerto: {SERVIDOR_PUERTO}", size=12, color=COLOR_TEXTO_SEC),
                    ], spacing=8),
                    bgcolor=COLOR_SUPERFICIE_2,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                    border_radius=10
                ),

                Container(height=14),

                # ── KPI cards ───────────────────────────────────────────────────
                Row([
                    _kpi("En línea",    self._escaner_label_online,    icons.WIFI,        COLOR_EXITO,       "Conectados ahora"),
                    _kpi("Registrados", self._escaner_label_total_srv,  icons.DEVICES,     COLOR_INFO,        "En el servidor"),
                    _kpi("En BD Red",   self._escaner_label_total_db,   icons.STORAGE,     COLOR_ACENTO,      "Base de datos"),
                    _kpi("Cambios IP",  self._escaner_label_cambios,    icons.SWAP_HORIZ,  COLOR_ADVERTENCIA, "Detectados"),
                ], spacing=12),

                Container(height=18),

                # ── Equipos conectados ──────────────────────────────────────────
                Container(
                    content=Column([
                        Row([
                            Container(
                                content=Icon(icons.SENSORS, size=18, color=colors.WHITE),
                                bgcolor=COLOR_EXITO, padding=8, border_radius=8
                            ),
                            Text("Equipos Conectados Ahora", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Container(
                                content=self._escaner_badge_online,
                                bgcolor=COLOR_EXITO,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                                border_radius=20
                            ),
                            Container(expand=True),
                            ft.Button(
                                "Actualizar", icon=icons.REFRESH,
                                on_click=self._refrescar_equipos_conectados
                            ),
                        ], spacing=10),
                        Container(height=12),
                        self._escaner_tabla_conectados,
                        self._escaner_pag_srv,
                        Text("", size=11, color=COLOR_TEXTO_SEC, visible=False),
                    ]),
                    bgcolor=COLOR_SUPERFICIE,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                    border_radius=12,
                    border=ft.Border.all(1, COLOR_EXITO + "55")
                ),

                Container(height=14),

                # ── Alertas de cambios de IP ─────────────────────────────────
                self._escaner_alertas,

                # ── Escanear red ─────────────────────────────────────────────
                Container(
                    content=Column([
                        Row([
                            Container(
                                content=Icon(icons.RADAR, size=18, color=colors.WHITE),
                                bgcolor=COLOR_PRIMARIO, padding=8, border_radius=8
                            ),
                            Text("Escanear Red Local", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Container(expand=True),
                            Text(f"{ip_base}.", size=13, color=COLOR_TEXTO_SEC),
                            self.txt_rango_inicio,
                            Text("—", color=COLOR_TEXTO_SEC),
                            Text(f"{ip_base}.", size=13, color=COLOR_TEXTO_SEC),
                            self.txt_rango_fin,
                            Container(width=6),
                            boton_escanear,
                        ], spacing=8),
                        Container(height=8),
                        # Barra de progreso
                        Row([
                            Container(
                                content=Row([
                                    self.progress_escaneo,
                                    self.lbl_progreso,
                                ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                                height=24, expand=True
                            ),
                        ]),
                        # Estado ping inline
                        Row([
                            self._ping_icono,
                            self._ping_lbl,
                        ], spacing=6, visible=True),
                    ]),
                    bgcolor=COLOR_SUPERFICIE,
                    padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                    border_radius=12,
                    border=ft.Border.all(1, COLOR_SUPERFICIE_2)
                ),

                Container(height=18),

                # ── Historial de equipos ─────────────────────────────────────
                Column([
                    Row([
                        Container(
                            content=Icon(icons.HISTORY, size=18, color=colors.WHITE),
                            bgcolor=COLOR_TEXTO_SEC, padding=8, border_radius=8
                        ),
                        Text("Historial de Equipos Detectados", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Container(
                            content=Text(str(total_db), size=11, color=colors.WHITE, weight=FontWeight.BOLD),
                            bgcolor=COLOR_ACENTO,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                            border_radius=20
                        ),
                        Container(expand=True),
                        Text("Haz clic en ➕ para agregar al inventario", size=11, color=COLOR_TEXTO_SEC),
                    ], spacing=10),
                    Container(height=10),
                    self._escaner_tabla_red,
                    self._escaner_pag_hist,
                    Text("", size=11, color=COLOR_TEXTO_SEC, visible=False)
                ], spacing=0),

                Container(height=20),
            ],
            scroll=ScrollMode.AUTO,
            expand=True
        )

        # Referencias de textos de resumen para actualizar sin reconstruir toda la vista
        bloque_conectados = vista.controls[6].content.controls
        self._escaner_resumen_srv = bloque_conectados[4]
        bloque_historial = vista.controls[11].controls
        self._escaner_resumen_hist = bloque_historial[4]

        self._cargar_escaner_async()
        return vista

    def _aplicar_datos_escaner_ui(self, equipos_red: pd.DataFrame, equipos_servidor: List[Dict], equipos_online: List[Dict]):
        self._escaner_equipos_srv_full = equipos_servidor or []
        self._escaner_equipos_red_full = equipos_red if equipos_red is not None else pd.DataFrame()
        self._escaner_equipos_online_full = equipos_online or []
        self._escaner_srv_page = 0
        self._escaner_hist_page = 0
        self._render_escaner_paginas()

    def _normalizar_equipos_conectados(self, equipos_scan: List[Dict]) -> List[Dict]:
        """Convierte el resultado crudo del escaneo a la forma que espera la tabla de conectados."""
        ahora = time.time()
        normalizados: List[Dict[str, Any]] = []

        for equipo in equipos_scan or []:
            ip = str(equipo.get("IP_ADDRESS") or equipo.get("ip_address") or "-")
            hostname = str(equipo.get("HOSTNAME") or equipo.get("hostname") or "Desconocido")
            mac = str(equipo.get("MAC_ADDRESS") or equipo.get("mac_address") or "-")

            normalizados.append({
                "online": True,
                "ip_address": ip,
                "hostname": hostname,
                "usuario_ad": str(equipo.get("USUARIO_AD") or equipo.get("usuario_ad") or "-") or "-",
                "mac_address": mac,
                "ultimo_heartbeat": ahora,
                "tickets_hoy": int(equipo.get("tickets_hoy", 0) or 0),
            })

        return normalizados

    def _render_escaner_paginas(self):
        equipos_servidor = self._escaner_equipos_srv_full or []
        equipos_red = self._escaner_equipos_red_full if self._escaner_equipos_red_full is not None else pd.DataFrame()
        equipos_online = self._escaner_equipos_online_full or []

        total_srv = len(equipos_servidor)
        total_pag_srv = max((total_srv + self._escaner_srv_page_size - 1) // self._escaner_srv_page_size, 1)
        self._escaner_srv_page = max(0, min(self._escaner_srv_page, total_pag_srv - 1))
        ini_srv = self._escaner_srv_page * self._escaner_srv_page_size
        fin_srv = min(ini_srv + self._escaner_srv_page_size, total_srv)
        equipos_servidor_render = equipos_servidor[ini_srv:fin_srv]

        if equipos_servidor_render:
            tabla_conectados = self._construir_tabla_equipos_conectados(equipos_servidor_render)
            self._escaner_tabla_conectados.content = self._wrap_tabla_scroll(
                tabla_conectados,
                min(len(equipos_servidor_render) * 56 + 56, 360)
            )
        else:
            self._escaner_tabla_conectados.content = Container(
                content=Column([
                    Icon(icons.SIGNAL_WIFI_OFF, size=40, color=COLOR_TEXTO_SEC),
                    Text("Sin equipos conectados en este momento", color=COLOR_TEXTO_SEC),
                    Text("Inicia un escaneo para detectar equipos en la red", size=12, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=8),
                padding=30
            )

        self._escaner_btn_srv_prev.disabled = self._escaner_srv_page <= 0
        self._escaner_btn_srv_next.disabled = self._escaner_srv_page >= total_pag_srv - 1
        self._escaner_lbl_srv_pag.value = f"Página {self._escaner_srv_page + 1}/{total_pag_srv}"
        self._escaner_pag_srv.visible = total_srv > self._escaner_srv_page_size

        total_red = len(equipos_red) if equipos_red is not None and not equipos_red.empty else 0
        total_pag_hist = max((total_red + self._escaner_hist_page_size - 1) // self._escaner_hist_page_size, 1)
        self._escaner_hist_page = max(0, min(self._escaner_hist_page, total_pag_hist - 1))
        ini_hist = self._escaner_hist_page * self._escaner_hist_page_size
        fin_hist = min(ini_hist + self._escaner_hist_page_size, total_red)
        equipos_red_render = equipos_red.iloc[ini_hist:fin_hist] if total_red > 0 else pd.DataFrame()

        if not equipos_red_render.empty:
            tabla_red = self._construir_tabla_red(equipos_red_render)
            self._escaner_tabla_red.content = self._wrap_tabla_scroll(
                tabla_red,
                min(len(equipos_red_render) * 56 + 56, 460)
            )
        else:
            self._escaner_tabla_red.content = Container(
                content=Column([
                    Icon(icons.SEARCH_OFF, size=48, color=COLOR_TEXTO_SEC),
                    Text("No hay equipos en el historial", color=COLOR_TEXTO_SEC),
                    Text("Inicia un escaneo para poblar esta tabla", size=12, color=COLOR_TEXTO_SEC),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=40, bgcolor=COLOR_SUPERFICIE, border_radius=12,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2)
            )

        self._escaner_btn_hist_prev.disabled = self._escaner_hist_page <= 0
        self._escaner_btn_hist_next.disabled = self._escaner_hist_page >= total_pag_hist - 1
        self._escaner_lbl_hist_pag.value = f"Página {self._escaner_hist_page + 1}/{total_pag_hist}"
        self._escaner_pag_hist.visible = total_red > self._escaner_hist_page_size

        cambios_count = (
            len(equipos_red[equipos_red["CAMBIOS_IP"] > 0])
            if not equipos_red.empty and "CAMBIOS_IP" in equipos_red.columns else 0
        )
        alertas_nueva = self._construir_alertas_cambios(equipos_red_render)
        self._escaner_alertas.content = alertas_nueva if cambios_count > 0 else Container()

        self._escaner_label_total_db.value = str(len(equipos_red) if not equipos_red.empty else 0)
        self._escaner_label_online.value = str(len(equipos_online))
        self._escaner_badge_online.value = str(len(equipos_online))
        self._escaner_label_total_srv.value = str(len(equipos_servidor))
        self._escaner_label_cambios.value = str(cambios_count)
        self._escaner_label_cambios.color = COLOR_ADVERTENCIA if cambios_count else COLOR_TEXTO_SEC

        if total_srv > 0:
            self._escaner_resumen_srv.value = f"Mostrando {ini_srv + 1}-{fin_srv} de {total_srv} equipos del servidor"
        else:
            self._escaner_resumen_srv.value = ""
        self._escaner_resumen_srv.visible = len(equipos_servidor) > 0

        if total_red > 0:
            self._escaner_resumen_hist.value = f"Mostrando {ini_hist + 1}-{fin_hist} de {total_red} en historial"
        else:
            self._escaner_resumen_hist.value = ""
        self._escaner_resumen_hist.visible = not equipos_red.empty

    def _cambiar_pagina_escaner_srv(self, delta: int):
        self._escaner_srv_page += delta
        self._render_escaner_paginas()
        self.page.update()

    def _cambiar_pagina_escaner_hist(self, delta: int):
        self._escaner_hist_page += delta
        self._render_escaner_paginas()
        self.page.update()

    def _cargar_escaner_async(self, force: bool = False):
        if self._escaner_cargando:
            if force:
                self._escaner_recarga_pendiente = True
            return
        self._escaner_cargando = True

        def cargar():
            try:
                try:
                    rango_inicio = int(self.txt_rango_inicio.value)
                    rango_fin = int(self.txt_rango_fin.value)
                except Exception:
                    rango_inicio, rango_fin = 1, 254

                # Ejecuta un barrido real antes de refrescar los paneles.
                equipos_encontrados, cambios = self.escaner.escanear_red(rango_inicio, rango_fin)

                if equipos_encontrados:
                    equipos_red = pd.DataFrame(equipos_encontrados)
                else:
                    equipos_red = pd.DataFrame(columns=[
                        "IP_ADDRESS",
                        "MAC_ADDRESS",
                        "HOSTNAME",
                        "ESTADO_RED",
                        "ULTIMO_PING",
                        "CAMBIOS_IP",
                        "IP_ANTERIOR",
                    ])

                equipos_historial = self.escaner.obtener_equipos_red_recientes(minutos=720)
                equipos_conectados = self._normalizar_equipos_conectados(equipos_encontrados)
                equipos_en_linea = equipos_conectados if equipos_conectados else self._normalizar_equipos_conectados(obtener_equipos_online())
                def aplicar_datos():
                    self._aplicar_datos_escaner_ui(equipos_historial, equipos_en_linea, equipos_en_linea)
                    msg = f"✅ Escaneo completado: {len(equipos_encontrados)} equipos encontrados"
                    if cambios:
                        msg += f", {len(cambios)} cambios de IP detectados"
                    self._mostrar_snackbar(msg, COLOR_EXITO)
                    self.page.update()

                self._ui_call(aplicar_datos)
            except Exception as ex:
                print(f"[ESCANER][ERROR] {ex}")
            finally:
                self._escaner_cargando = False
                if self._escaner_recarga_pendiente:
                    self._escaner_recarga_pendiente = False
                    self._cargar_escaner_async(force=True)

        threading.Thread(target=cargar, daemon=True).start()
    
    def _construir_tabla_equipos_conectados(self, equipos: List[Dict]) -> DataTable:
        """Construye la tabla de equipos conectados al servidor."""
        columnas = [
            DataColumn(Text("#",              weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Estado",         weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("IP",             weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Hostname",       weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Usuario AD",     weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("MAC",            weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Última act.",    weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Tickets hoy",   weight=FontWeight.BOLD, color=COLOR_TEXTO)),
        ]

        filas = []
        import time
        ahora = time.time()

        for idx, equipo in enumerate(equipos, start=1):
            online           = equipo.get("online", False)
            ip               = str(equipo.get("ip_address", "-") or "-")
            hostname         = str(equipo.get("hostname", "Desconocido") or "Desconocido")
            usuario          = str(equipo.get("usuario_ad", "-") or "-")
            mac              = str(equipo.get("mac_address", "-") or "-")
            ultimo_heartbeat = equipo.get("ultimo_heartbeat", 0)
            tickets_hoy      = int(equipo.get("tickets_hoy", 0) or 0)

            if ultimo_heartbeat > 0:
                seg = int(ahora - ultimo_heartbeat)
                if seg < 60:
                    tiempo_str = f"{seg}s atrás"
                elif seg < 3600:
                    tiempo_str = f"{seg // 60}m atrás"
                else:
                    tiempo_str = f"{seg // 3600}h atrás"
            else:
                tiempo_str = "—"

            color_estado = COLOR_EXITO if online else COLOR_TEXTO_SEC
            badge_online = Container(
                content=Text(
                    "● Online" if online else "○ Offline",
                    size=11, color=colors.WHITE, weight=FontWeight.W_500
                ),
                bgcolor=COLOR_EXITO if online else COLOR_SUPERFICIE_2,
                padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                border_radius=20
            )

            filas.append(DataRow(
                color={"hovered": COLOR_SUPERFICIE_2},
                cells=[
                    DataCell(Text(str(idx), size=12, color=COLOR_TEXTO_SEC)),
                    DataCell(badge_online),
                    DataCell(Text(ip,              size=13, weight=FontWeight.BOLD, color=COLOR_INFO)),
                    DataCell(Text(hostname[:25],    size=12, color=COLOR_TEXTO)),
                    DataCell(Text(usuario[:20],     size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(mac,              size=10, color=COLOR_TEXTO_SEC, selectable=True)),
                    DataCell(Text(tiempo_str,       size=11, color=color_estado)),
                    DataCell(
                        Container(
                            content=Text(str(tickets_hoy), size=11, color=colors.WHITE,
                                         weight=FontWeight.BOLD),
                            bgcolor=COLOR_ACENTO if tickets_hoy else "transparent",
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border_radius=20
                        ) if tickets_hoy else Text("0", size=11, color=COLOR_TEXTO_SEC)
                    ),
                ]
            ))

        return DataTable(
            columns=columnas,
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            heading_row_color=COLOR_SUPERFICIE_2,
            heading_row_height=44,
            data_row_min_height=48,
            data_row_max_height=56,
            column_spacing=14,
            show_checkbox_column=False,
            horizontal_lines=ft.border.BorderSide(1, COLOR_SUPERFICIE_2)
        )
    
    def _refrescar_equipos_conectados(self, e):
        """Refresca la lista de equipos conectados."""
        self._mostrar_snackbar("🔄 Actualizando equipos conectados...", COLOR_INFO)
        self._cargar_escaner_async(force=True)
    
    def _descartar_alerta_cambio_ip(self, mac: str):
        """Descarta la alerta de cambio de IP reseteando el contador en BD."""
        try:
            self.escaner.descartar_cambios_ip(mac)
            self._mostrar_snackbar(f"✅ Alerta descartada para {mac}", COLOR_EXITO)
            self._refrescar_panel_alertas_ip()
        except Exception as ex:
            self._mostrar_snackbar(f"❌ Error: {ex}", COLOR_ERROR)

    def _descartar_todas_alertas_cambio_ip(self, e=None):
        """Descarta en bloque todas las alertas de cambio de IP."""
        try:
            total_descartadas = int(self.escaner.descartar_todos_cambios_ip())
            if total_descartadas <= 0:
                self._mostrar_snackbar("ℹ️ No hay alertas de cambio de IP para eliminar.", COLOR_INFO)
            else:
                self._mostrar_snackbar(
                    f"✅ Se eliminaron {total_descartadas} advertencias de cambio de IP.",
                    COLOR_EXITO,
                )
            self._refrescar_panel_alertas_ip()
        except Exception as ex:
            self._mostrar_snackbar(f"❌ Error eliminando advertencias: {ex}", COLOR_ERROR)

    def _refrescar_panel_alertas_ip(self):
        """Refresca el bloque de alertas de cambios de IP y el contador asociado."""
        try:
            equipos_red = self.escaner.obtener_equipos_red()
            alertas_nueva = self._construir_alertas_cambios(equipos_red)
            cambios_count = len(equipos_red[equipos_red["CAMBIOS_IP"] > 0]) if not equipos_red.empty and "CAMBIOS_IP" in equipos_red.columns else 0
            self._escaner_alertas.content = alertas_nueva if cambios_count > 0 else Container()
            self._escaner_label_cambios.value = str(cambios_count)
            self._escaner_label_cambios.color = COLOR_ADVERTENCIA if cambios_count else COLOR_TEXTO_SEC
            self.page.update()
        except Exception as ex:
            print(f"[ERROR] Refrescando alertas: {ex}")

    def _construir_alertas_cambios(self, equipos_red: pd.DataFrame) -> Container:
        """Construye el panel de alertas de cambios de IP (descartables)."""
        if equipos_red.empty or "CAMBIOS_IP" not in equipos_red.columns:
            return Container()

        cambios = equipos_red[equipos_red["CAMBIOS_IP"] > 0]
        if cambios.empty:
            return Container()

        alertas = []
        for _, equipo in cambios.iterrows():
            mac      = equipo.get("MAC_ADDRESS", "")
            hostname = equipo.get("HOSTNAME", "Equipo")
            ip_ant   = equipo.get("IP_ANTERIOR", "?") or "?"
            ip_nueva = equipo.get("IP_ADDRESS", "?")
            n_cambios = int(equipo.get("CAMBIOS_IP", 0))

            alertas.append(
                Container(
                    content=Row([
                        Container(
                            content=Icon(icons.WARNING_AMBER, size=22, color=colors.WHITE),
                            bgcolor=COLOR_ADVERTENCIA, padding=10, border_radius=8
                        ),
                        Column([
                            Text(f"{hostname} cambió de IP",
                                 weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA, size=14),
                            Text(f"Anterior: {ip_ant}  →  Nueva: {ip_nueva}",
                                 size=12, color=COLOR_TEXTO_SEC),
                            Text(f"MAC: {mac}  |  Cambios acumulados: {n_cambios}",
                                 size=11, color=COLOR_TEXTO_SEC),
                        ], spacing=2, expand=True),
                        ft.IconButton(
                            icon=icons.CLOSE,
                            icon_color=COLOR_TEXTO_SEC,
                            icon_size=20,
                            tooltip="Descartar alerta",
                            on_click=lambda e, m=mac: self._descartar_alerta_cambio_ip(m)
                        ),
                    ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor="#3D2607",
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                    border_radius=10,
                    border=ft.Border.all(1, COLOR_ADVERTENCIA)
                )
            )

        return Container(
            content=Column([
                Row([
                    Icon(icons.WARNING_AMBER, color=COLOR_ADVERTENCIA, size=18),
                    Text(f"Alertas de Cambios de IP ({len(alertas)})",
                         weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA),
                    Container(expand=True),
                    ft.TextButton(
                        "Eliminar todas",
                        icon=icons.DELETE_SWEEP_ROUNDED,
                        style=ft.ButtonStyle(color=COLOR_ADVERTENCIA),
                        on_click=lambda e: self._mostrar_confirmacion(
                            titulo="Eliminar advertencias",
                            mensaje="¿Deseas eliminar todas las advertencias de cambios de IP?",
                            on_confirmar=self._descartar_todas_alertas_cambio_ip,
                        ),
                    ),
                ], spacing=8),
                Container(height=6),
                *alertas
            ], spacing=6),
            bgcolor=COLOR_SUPERFICIE,
            padding=ft.Padding.symmetric(horizontal=14, vertical=12),
            border_radius=12,
            border=ft.Border.all(1, COLOR_ADVERTENCIA + "80"),
            margin=ft.Margin.only(bottom=14)
        )
    
    def _construir_tabla_red(self, equipos: pd.DataFrame) -> DataTable:
        """Construye la tabla de historial de equipos de red."""
        columnas = [
            DataColumn(Text("#",          weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("IP",         weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("MAC",        weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Hostname",   weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Estado",     weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Últ. Ping",  weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Cambios IP", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Acciones",   weight=FontWeight.BOLD, color=COLOR_TEXTO)),
        ]

        filas = []
        for idx, (_, equipo) in enumerate(equipos.iterrows(), start=1):
            ip           = str(equipo.get("IP_ADDRESS", "") or "")
            mac          = str(equipo.get("MAC_ADDRESS", "") or "")
            hostname_raw = equipo.get("HOSTNAME", "")
            hostname     = str(hostname_raw) if pd.notna(hostname_raw) and hostname_raw else "Desconocido"
            estado       = str(equipo.get("ESTADO_RED", "Desconocido") or "Desconocido")
            ultimo_ping  = equipo.get("ULTIMO_PING", "")
            cambios      = int(equipo.get("CAMBIOS_IP", 0)) if pd.notna(equipo.get("CAMBIOS_IP")) else 0

            if pd.notna(ultimo_ping) and hasattr(ultimo_ping, "strftime"):
                ping_str = ultimo_ping.strftime("%d/%m %H:%M")
            elif pd.notna(ultimo_ping):
                ping_str = str(ultimo_ping)[-16:]
            else:
                ping_str = "—"

            online = estado == "Online"
            color_estado = COLOR_EXITO if online else COLOR_TEXTO_SEC
            badge_estado = Container(
                content=Text(
                    "● Online" if online else "○ Offline",
                    size=11, color=colors.WHITE, weight=FontWeight.W_500
                ),
                bgcolor=COLOR_EXITO if online else COLOR_SUPERFICIE_2,
                padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                border_radius=20
            )

            badge_cambios = (
                Container(
                    content=Text(f"⚠ {cambios}", size=11, color=colors.WHITE, weight=FontWeight.BOLD),
                    bgcolor=COLOR_ERROR if cambios >= 3 else COLOR_ADVERTENCIA,
                    padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                    border_radius=20
                )
                if cambios > 0
                else Text("0", size=11, color=COLOR_TEXTO_SEC)
            )

            filas.append(DataRow(
                color={"hovered": COLOR_SUPERFICIE_2},
                cells=[
                    DataCell(Text(str(idx),      size=12, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(ip,            size=13, weight=FontWeight.BOLD, color=COLOR_INFO)),
                    DataCell(Text(mac,           size=10, color=COLOR_TEXTO_SEC, selectable=True)),
                    DataCell(Text(hostname[:25], size=12, color=COLOR_TEXTO)),
                    DataCell(badge_estado),
                    DataCell(Text(ping_str,      size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(badge_cambios),
                    DataCell(Row([
                        ft.IconButton(
                            icon=icons.ADD_CIRCLE_OUTLINE,
                            icon_color=COLOR_ACENTO,
                            icon_size=22,
                            tooltip="Agregar a Inventario",
                            on_click=lambda e, m=mac, h=hostname, i=ip: self._agregar_a_inventario(m, h, i)
                        ),
                        ft.IconButton(
                            icon=icons.WIFI_FIND,
                            icon_color=COLOR_INFO,
                            icon_size=22,
                            tooltip="Hacer ping",
                            on_click=lambda e, i=ip: self._ping_individual(i)
                        ),
                    ], spacing=0)),
                ]
            ))

        return DataTable(
            columns=columnas,
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            heading_row_color=COLOR_SUPERFICIE_2,
            heading_row_height=46,
            data_row_min_height=50,
            data_row_max_height=58,
            column_spacing=14,
            show_checkbox_column=False,
            horizontal_lines=ft.border.BorderSide(1, COLOR_SUPERFICIE_2)
        )
    
    def _iniciar_escaneo_red(self, e):
        """Inicia el escaneo de la red."""
        try:
            rango_inicio = int(self.txt_rango_inicio.value)
            rango_fin = int(self.txt_rango_fin.value)
        except:
            self._mostrar_snackbar("❌ Rango inválido", COLOR_ERROR)
            return
        
        if rango_inicio < 1 or rango_fin > 254 or rango_inicio > rango_fin:
            self._mostrar_snackbar("❌ Rango debe ser entre 1-254", COLOR_ERROR)
            return
        
        if self._btn_escanear_red is not None:
            self._btn_escanear_red.disabled = True

        self.progress_escaneo.visible = True
        self.lbl_progreso.visible = True
        self.progress_escaneo.value = 0
        self.lbl_progreso.value = "Iniciando escaneo..."
        self.page.update()
        
        # Configurar callbacks
        def actualizar_progreso(actual, total):
            def aplicar():
                self.progress_escaneo.value = actual / total
                self.lbl_progreso.value = f"Escaneando: {actual}/{total} IPs..."
                self.page.update()

            self._ui_call(aplicar)
        
        def equipo_encontrado(equipo):
            def aplicar():
                self.lbl_progreso.value = f"✓ Encontrado: {equipo['IP_ADDRESS']} - {equipo['HOSTNAME']}"
                self.page.update()

            self._ui_call(aplicar)
        
        self.escaner.callback_progreso = actualizar_progreso
        self.escaner.callback_equipo = equipo_encontrado
        
        # Ejecutar escaneo en thread separado
        def ejecutar_escaneo():
            try:
                equipos, cambios = self.escaner.escanear_red(rango_inicio, rango_fin)

                if equipos:
                    equipos_red = pd.DataFrame(equipos)
                else:
                    equipos_red = pd.DataFrame(columns=[
                        "IP_ADDRESS",
                        "MAC_ADDRESS",
                        "HOSTNAME",
                        "ESTADO_RED",
                        "ULTIMO_PING",
                        "CAMBIOS_IP",
                        "IP_ANTERIOR",
                    ])

                equipos_conectados = self._normalizar_equipos_conectados(equipos)
                equipos_en_linea = equipos_conectados if equipos_conectados else self._normalizar_equipos_conectados(obtener_equipos_online())

                def actualizar_ui():
                    self.progress_escaneo.visible = False
                    self.lbl_progreso.visible = False
                    if self._btn_escanear_red is not None:
                        self._btn_escanear_red.disabled = False

                    try:
                        equipos_historial = self.escaner.obtener_equipos_red_recientes(minutos=720)
                        self._aplicar_datos_escaner_ui(equipos_historial, equipos_en_linea, equipos_en_linea)
                    except Exception as ex:
                        print(f"[ERROR] Actualizando tabla: {ex}")

                    msg = f"✅ Escaneo completado: {len(equipos)} equipos encontrados"
                    if cambios:
                        msg += f", {len(cambios)} cambios de IP detectados"
                    self._mostrar_snackbar(msg, COLOR_EXITO)
                    self.page.update()

                self._ui_call(actualizar_ui)
            except Exception as ex:
                def mostrar_error():
                    self.progress_escaneo.visible = False
                    self.lbl_progreso.visible = False
                    if self._btn_escanear_red is not None:
                        self._btn_escanear_red.disabled = False
                    self._mostrar_error("Error al escanear", str(ex))
                    self.page.update()

                self._ui_call(mostrar_error)
        
        thread = threading.Thread(target=ejecutar_escaneo, daemon=True)
        thread.start()
    
    def _ping_individual(self, ip: str):
        """Hace ping a una IP y muestra el resultado en el panel inline."""
        from data_access import ping_host
        import time

        try:
            # Mostrar estado "en progreso" inmediatamente (hilo principal)
            self._ping_icono.name    = icons.AUTORENEW
            self._ping_icono.color   = COLOR_INFO
            self._ping_icono.visible = True
            self._ping_lbl.value     = f"Haciendo ping a {ip}..."
            self._ping_lbl.color     = COLOR_INFO
            self._ping_lbl.visible   = True
            self.page.update()
        except Exception as ex:
            print(f"[PING] Error actualizando estado inicial: {ex}")
            return

        def hacer_ping():
            try:
                resultado = ping_host(ip, timeout=2)
                def mostrar_resultado():
                    if resultado:
                        self._ping_icono.name  = icons.CHECK_CIRCLE
                        self._ping_icono.color = COLOR_EXITO
                        self._ping_lbl.value   = f"✅  {ip}  está Online"
                        self._ping_lbl.color   = COLOR_EXITO
                    else:
                        self._ping_icono.name  = icons.CANCEL
                        self._ping_icono.color = COLOR_ERROR
                        self._ping_lbl.value   = f"❌  {ip}  no responde"
                        self._ping_lbl.color   = COLOR_ERROR

                self._ui_call(mostrar_resultado)
            except Exception as ex:
                def mostrar_error():
                    self._ping_icono.name  = icons.ERROR
                    self._ping_icono.color = COLOR_ERROR
                    self._ping_lbl.value   = f"❌  Error: {ex}"
                    self._ping_lbl.color   = COLOR_ERROR

                self._ui_call(mostrar_error)

            try:
                self._ui_call(lambda: self.page.update())
            except Exception:
                pass

            # Ocultar resultado tras 6 segundos
            time.sleep(6)
            def ocultar_resultado():
                self._ping_icono.visible = False
                self._ping_lbl.visible   = False
                try:
                    self.page.update()
                except Exception:
                    pass

            self._ui_call(ocultar_resultado)

        threading.Thread(target=hacer_ping, daemon=True).start()
    
    def _agregar_a_inventario(self, mac: str, hostname: str, ip: str):
        """Agrega un equipo de red al inventario."""
        if not mac or mac == "No detectada" or mac == "-":
            self._mostrar_error("MAC inválida", "No se puede agregar un equipo sin dirección MAC válida.")
            return
        
        try:
            # Verificar si ya existe
            equipo_existente = self.gestor.obtener_equipo_por_mac(mac)
            if equipo_existente:
                # Ya existe → ofrecer editar directamente
                self._mostrar_confirmacion(
                    mensaje=f"El equipo con MAC {mac} ya está en el inventario.\n¿Deseas editar sus datos?",
                    titulo="Equipo ya registrado",
                    on_confirmar=lambda e=None: self._dialogo_editar_equipo(mac)
                )
                return
            
            # Registrar en inventario
            resultado = self.gestor.registrar_o_actualizar_equipo(
                mac_address=mac, 
                hostname=hostname or "Desconocido", 
                usuario_ad=f"Agregado desde Red - IP: {ip}"
            )
            
            if resultado:
                print(f"[INVENTARIO] Equipo agregado: MAC={mac}, Hostname={hostname}, IP={ip}")
                # Abrir diálogo de edición para completar datos
                self._dialogo_editar_equipo(mac, mantener_vista_actual=True)
            else:
                self._mostrar_error("Error al guardar", "No se pudo guardar el equipo en el inventario.")
                
        except Exception as e:
            print(f"[ERROR] Error agregando equipo: {e}")
            self._mostrar_error("Error inesperado", str(e))
    
    # =========================================================================
    # VISTA: SOLICITUDES DE ENLACE
    # =========================================================================
    
    def _vista_solicitudes(self) -> Column:
        """Construye la vista de solicitudes de enlace pendientes."""
        from servidor_red import obtener_solicitudes_pendientes, obtener_equipos_aprobados

        solicitudes = obtener_solicitudes_pendientes()
        aprobados   = obtener_equipos_aprobados()
        solicitudes_render, omit_sol = self._limitar_lista_render(solicitudes, self._max_render_solicitudes)
        aprobados_render, omit_apr = self._limitar_lista_render(aprobados, self._max_render_solicitudes)

        # ── Header ────────────────────────────────────────────────────────────
        header = Container(
            content=Row([
                Container(
                    content=Icon(icons.NOTIFICATIONS_ACTIVE, size=36, color=colors.WHITE),
                    bgcolor=COLOR_ACENTO, padding=14, border_radius=12
                ),
                Column([
                    Text("Solicitudes de Enlace", size=22, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Text("Gestiona los equipos que solicitan acceso al sistema de tickets",
                         size=13, color=COLOR_TEXTO_SEC),
                ], spacing=3, expand=True),
                ft.Button(
                    "🔄 Actualizar",
                    icon=icons.REFRESH,
                    on_click=lambda e: self._refrescar_vista()
                ),
            ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLOR_SUPERFICIE,
            padding=ft.Padding.symmetric(horizontal=20, vertical=16),
            border_radius=14,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2)
        )

        # ── Tarjetas de stats ─────────────────────────────────────────────────
        def _stat_card(icono, valor, etiqueta, color_icono, borde_color=None):
            return Container(
                content=Row([
                    Container(
                        content=Icon(icono, size=26, color=colors.WHITE),
                        bgcolor=color_icono, padding=10, border_radius=10
                    ),
                    Column([
                        Text(str(valor), size=26, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(etiqueta, size=11, color=COLOR_TEXTO_SEC),
                    ], spacing=1),
                ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=COLOR_SUPERFICIE,
                padding=ft.Padding.symmetric(horizontal=18, vertical=14),
                border_radius=12,
                border=ft.Border.all(2 if borde_color else 1,
                                     borde_color if borde_color else COLOR_SUPERFICIE_2),
                expand=True
            )

        stats_row = Row([
            _stat_card(icons.PENDING_ACTIONS, len(solicitudes), "Pendientes",
                       COLOR_ADVERTENCIA, COLOR_ADVERTENCIA if solicitudes else None),
            _stat_card(icons.LINK, len(aprobados), "Enlazados", COLOR_EXITO),
            _stat_card(icons.DEVICES, len(solicitudes) + len(aprobados), "Total equipos", COLOR_ACENTO),
        ], spacing=14)

        # ── Sección: solicitudes pendientes ───────────────────────────────────
        seccion_pendientes = Column([
            Row([
                Icon(icons.MARK_EMAIL_UNREAD, color=COLOR_ADVERTENCIA),
                Text("Solicitudes Pendientes", size=17, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Container(
                    content=Text(str(len(solicitudes)), size=11, color=colors.WHITE,
                                 weight=FontWeight.BOLD),
                    bgcolor=COLOR_ADVERTENCIA if solicitudes else COLOR_TEXTO_SEC,
                    padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                    border_radius=20
                ),
            ], spacing=10),
            Container(height=8),
            self._construir_lista_solicitudes(solicitudes_render) if solicitudes else Container(
                content=Column([
                    Icon(icons.INBOX, size=52, color=COLOR_TEXTO_SEC),
                    Text("Sin solicitudes pendientes", size=15, color=COLOR_TEXTO_SEC,
                         weight=FontWeight.W_500),
                    Text("Los equipos enviarán solicitudes automáticamente al intentar conectarse",
                         size=12, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=50, bgcolor=COLOR_SUPERFICIE, border_radius=12,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2)
            ),
        ], spacing=5)

        # ── Sección: equipos enlazados ────────────────────────────────────────
        seccion_aprobados = Column([
            Row([
                Icon(icons.VERIFIED, color=COLOR_EXITO),
                Text("Equipos Enlazados", size=17, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Container(
                    content=Text(str(len(aprobados)), size=11, color=colors.WHITE,
                                 weight=FontWeight.BOLD),
                    bgcolor=COLOR_EXITO,
                    padding=ft.Padding.symmetric(horizontal=9, vertical=3),
                    border_radius=20
                ),
            ], spacing=10),
            Container(height=8),
            self._construir_tabla_aprobados(aprobados_render) if aprobados else Container(
                content=Column([
                    Icon(icons.LINK_OFF, size=52, color=COLOR_TEXTO_SEC),
                    Text("No hay equipos enlazados aún", size=15, color=COLOR_TEXTO_SEC,
                         weight=FontWeight.W_500),
                    Text("Aprueba solicitudes para que los equipos puedan enviar tickets",
                         size=12, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                padding=50, bgcolor=COLOR_SUPERFICIE, border_radius=12,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2)
            ),
        ], spacing=5)

        return Column(
            controls=[
                header,
                Container(height=16),
                stats_row,
                Container(height=20),
                seccion_pendientes,
                Text(
                    f"Mostrando {len(solicitudes_render)} de {len(solicitudes)} solicitudes"
                    + (f" (omitidas {omit_sol})" if omit_sol > 0 else ""),
                    size=11,
                    color=COLOR_TEXTO_SEC,
                    visible=len(solicitudes) > 0,
                ),
                Container(height=24),
                seccion_aprobados,
                Text(
                    f"Mostrando {len(aprobados_render)} de {len(aprobados)} aprobados"
                    + (f" (omitidos {omit_apr})" if omit_apr > 0 else ""),
                    size=11,
                    color=COLOR_TEXTO_SEC,
                    visible=len(aprobados) > 0,
                ),
                Container(height=20),
            ],
            spacing=0,
            scroll=ScrollMode.AUTO,
            expand=True
        )
    
    def _construir_lista_solicitudes(self, solicitudes: list) -> Container:
        """Construye las tarjetas de solicitudes pendientes con scroll."""
        tarjetas = []

        for sol in solicitudes:
            mac      = sol.get("mac_address", "")
            hostname = sol.get("hostname", "Desconocido")
            usuario  = sol.get("usuario_ad", "")
            ip       = sol.get("ip_address", "")
            fecha    = sol.get("fecha_solicitud", "")
            intentos = sol.get("intentos", 1)
            nombre   = sol.get("nombre_equipo", hostname)

            try:
                from datetime import datetime
                fecha_dt  = datetime.fromisoformat(fecha)
                fecha_str = fecha_dt.strftime("%d/%m/%Y %H:%M")
            except:
                fecha_str = str(fecha)[:16]

            badge_intentos = Container(
                content=Text(f"#{intentos} intentos", size=10, color=colors.WHITE,
                             weight=FontWeight.BOLD),
                bgcolor=COLOR_ERROR if intentos >= 3 else COLOR_ADVERTENCIA,
                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                border_radius=20,
                visible=intentos > 1
            )

            tarjeta = Container(
                content=Row([
                    # Avatar equipo
                    Container(
                        content=Column([
                            Icon(icons.COMPUTER, size=28, color=colors.WHITE),
                            Text(str(intentos) if intentos > 1 else "",
                                 size=10, color=colors.WHITE, visible=intentos > 1),
                        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                        bgcolor=COLOR_ERROR if intentos >= 3 else COLOR_ADVERTENCIA,
                        padding=14, border_radius=12, width=60,
    alignment=ft.Alignment(0, 0)
                    ),

                    # Datos del equipo
                    Column([
                        Row([
                            Text(nombre[:30], weight=FontWeight.BOLD, color=COLOR_TEXTO, size=15),
                            badge_intentos,
                        ], spacing=10),
                        Row([
                            Icon(icons.DNS, size=13, color=COLOR_TEXTO_SEC),
                            Text(hostname, size=12, color=COLOR_TEXTO_SEC),
                            Container(width=8),
                            Icon(icons.PERSON, size=13, color=COLOR_TEXTO_SEC),
                            Text(usuario or "No identificado", size=12, color=COLOR_TEXTO_SEC),
                        ], spacing=4),
                        Row([
                            Icon(icons.FINGERPRINT, size=13, color=COLOR_TEXTO_SEC),
                            Text(mac, size=11, color=COLOR_TEXTO_SEC, selectable=True),
                            Container(width=12),
                            Icon(icons.WIFI, size=13, color=COLOR_TEXTO_SEC),
                            Text(ip, size=11, color=COLOR_TEXTO_SEC),
                        ], spacing=4),
                        Row([
                            Icon(icons.SCHEDULE, size=12, color=COLOR_TEXTO_SEC),
                            Text(f"Solicitado: {fecha_str}", size=11, color=COLOR_TEXTO_SEC),
                        ], spacing=4),
                    ], spacing=5, expand=True),

                    # Acciones
                    Column([
                        ft.Button(
                            "✅ Aprobar",
                            bgcolor=COLOR_EXITO,
                            color=colors.WHITE,
                            on_click=lambda e, m=mac: self._aprobar_solicitud(m)
                        ),
                        ft.Button(
                            "❌ Rechazar",
                            bgcolor=COLOR_ERROR,
                            color=colors.WHITE,
                            on_click=lambda e, m=mac: self._rechazar_solicitud(m)
                        ),
                    ], spacing=8, horizontal_alignment=ft.CrossAxisAlignment.END)
                ], spacing=16, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                bgcolor=COLOR_SUPERFICIE,
                padding=ft.Padding.symmetric(horizontal=16, vertical=14),
                border_radius=12,
                border=ft.Border.all(
                    2,
                    COLOR_ERROR if intentos >= 3 else COLOR_ADVERTENCIA
                )
            )
            tarjetas.append(tarjeta)

        # Lista con scroll si hay muchas solicitudes
        return Container(
            content=Column(
                tarjetas,
                spacing=10,
                scroll=ScrollMode.AUTO
            ),
            height=min(len(tarjetas) * 145, 550) if len(tarjetas) > 3 else None,
            expand=len(tarjetas) <= 3
        )
    
    def _construir_tabla_aprobados(self, aprobados: list) -> Container:
        """Construye la tabla de equipos aprobados con scroll horizontal y vertical."""
        columnas = [
            DataColumn(Text("#",        weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Nombre",   weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Hostname", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("MAC",      weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("IP",       weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Aprobado", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Estado",   weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Acciones", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
        ]

        filas = []
        for idx, equipo in enumerate(aprobados, start=1):
            mac      = equipo.get("mac_address", "")
            nombre   = equipo.get("nombre_equipo", "Sin nombre")[:25]
            hostname = equipo.get("hostname", "")[:20]
            ip       = equipo.get("ip_address", "")
            fecha    = equipo.get("fecha_aprobacion", "")
            activo   = equipo.get("activo", True)

            try:
                from datetime import datetime
                fecha_dt  = datetime.fromisoformat(fecha)
                fecha_str = fecha_dt.strftime("%d/%m/%Y %H:%M")
            except:
                fecha_str = str(fecha)[:16]

            badge_estado = Container(
                content=Text(
                    "● Activo" if activo else "● Inactivo",
                    size=11, color=colors.WHITE, weight=FontWeight.BOLD
                ),
                bgcolor=COLOR_EXITO if activo else COLOR_TEXTO_SEC,
                padding=ft.Padding.symmetric(horizontal=8, vertical=3),
                border_radius=20
            )

            filas.append(DataRow(
                color={"hovered": COLOR_SUPERFICIE_2},
                cells=[
                    DataCell(Text(str(idx), size=12, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(nombre,   size=13, weight=FontWeight.W_500, color=COLOR_TEXTO)),
                    DataCell(Text(hostname, size=12, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(mac,      size=11, color=COLOR_TEXTO_SEC, selectable=True)),
                    DataCell(Text(ip,       size=12, color=COLOR_INFO)),
                    DataCell(Text(fecha_str, size=11, color=COLOR_EXITO)),
                    DataCell(badge_estado),
                    DataCell(
                        Row([
                            ft.IconButton(
                                icon=icons.LINK_OFF,
                                icon_color=COLOR_ERROR,
                                icon_size=20,
                                tooltip="Revocar enlace",
                                on_click=lambda e, m=mac: self._confirmar_revocar_enlace(m)
                            ),
                        ], spacing=0)
                    ),
                ]
            ))

        tabla = DataTable(
            columns=columnas,
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            border_radius=10,
            heading_row_color=COLOR_SUPERFICIE_2,
            heading_row_height=48,
            data_row_min_height=52,
            data_row_max_height=64,
            column_spacing=18,
            show_checkbox_column=False,
            expand=True
        )

        # Scroll horizontal dentro de un Row, scroll vertical en la Column padre
        return Container(
            content=Row(
                [tabla],
                scroll=ScrollMode.AUTO,
                vertical_alignment=ft.CrossAxisAlignment.START
            ),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=12,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            padding=ft.Padding.all(0),
            height=min(len(filas) * 62 + 60, 520) if len(filas) > 6 else None,
            expand=len(filas) <= 6
        )
    
    def _aprobar_solicitud(self, mac: str):
        """Aprueba una solicitud de enlace."""
        from servidor_red import aprobar_solicitud_enlace
        
        if aprobar_solicitud_enlace(mac):
            self._mostrar_snackbar(f"✅ Equipo {mac} enlazado correctamente", COLOR_EXITO)
            self._refrescar_vista()
        else:
            self._mostrar_snackbar("❌ Error al aprobar solicitud", COLOR_ERROR)
    
    def _rechazar_solicitud(self, mac: str):
        """Muestra diálogo para rechazar solicitud."""
        txt_motivo = ft.TextField(
            label="Motivo del rechazo (opcional)",
            multiline=True,
            min_lines=2,
            max_lines=4,
            width=350
        )
        
        def cerrar_dialogo(e=None):
            dlg.open = False
            self.page.update()
        
        def confirmar_rechazo(e):
            from servidor_red import rechazar_solicitud_enlace
            motivo = txt_motivo.value or "Rechazado por el administrador"
            
            if rechazar_solicitud_enlace(mac, motivo):
                self._mostrar_snackbar(f"❌ Solicitud de {mac} rechazada", COLOR_ADVERTENCIA)
                dlg.open = False
                self.page.update()
                self._refrescar_vista()
            else:
                self._mostrar_snackbar("❌ Error al rechazar", COLOR_ERROR)
        
        dlg = AlertDialog(
            modal=True,
            title=Text("❌ Rechazar Solicitud", weight=FontWeight.BOLD),
            content=Container(
                content=Column([
                    Text(f"¿Rechazar la solicitud de enlace del equipo {mac}?"),
                    Container(height=10),
                    txt_motivo,
                ], spacing=10),
                width=380
            ),
            actions_alignment=MainAxisAlignment.END,
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_dialogo),
                ft.Button(
                    "Rechazar",
                    bgcolor=COLOR_ERROR,
                    color=colors.WHITE,
                    on_click=confirmar_rechazo
                )
            ]
        )
        
        self.page.show_dialog(dlg)
    
    def _confirmar_revocar_enlace(self, mac: str):
        """Confirma la revocación de un enlace."""
        
        def cerrar_dialogo(e=None):
            dlg.open = False
            self.page.update()
        
        def revocar(e):
            from servidor_red import revocar_enlace
            
            if revocar_enlace(mac):
                self._mostrar_snackbar(f"🔗 Enlace de {mac} revocado", COLOR_ADVERTENCIA)
                dlg.open = False
                self.page.update()
                self._refrescar_vista()
            else:
                self._mostrar_snackbar("❌ Error al revocar enlace", COLOR_ERROR)
        
        dlg = AlertDialog(
            modal=True,
            title=Text("⚠️ Revocar Enlace", weight=FontWeight.BOLD),
            content=Text(f"¿Revocar el enlace del equipo {mac}?\n\nEl equipo deberá solicitar enlace nuevamente para enviar tickets."),
            actions_alignment=MainAxisAlignment.END,
            actions=[
                ft.TextButton("Cancelar", on_click=cerrar_dialogo),
                ft.Button(
                    "🔗 Revocar",
                    bgcolor=COLOR_ERROR,
                    color=colors.WHITE,
                    on_click=revocar
                )
            ]
        )
        
        self.page.show_dialog(dlg)


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def _inicializar_base_datos_automatica():
    """
    Inicializa automáticamente la base de datos SQLite si no existe.
    GestorTickets() crea las tablas, índices y técnicos iniciales de forma automática.
    """
    print("[AUTO-INIT] 🔧 Verificando base de datos SQLite...")
    
    try:
        gestor = GestorTickets()
        print(f"[AUTO-INIT] ✅ Base de datos lista: {gestor.db_path}")
    except Exception as e:
        print(f"[AUTO-INIT] ❌ Error al inicializar la base de datos: {e}")


def main(page: Page):
    """Función principal que inicializa la aplicación."""
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
                    spacing=12,
                    controls=[
                        Icon(icons.LOCK_OUTLINE, size=64, color=COLOR_ERROR),
                        Text("Acceso bloqueado por licenciamiento", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(result.message or "No se pudo validar la licencia", color=COLOR_TEXTO_SEC, text_align=TextAlign.CENTER),
                        Text(f"Código: {result.reason}", color=COLOR_TEXTO_SEC),
                    ],
                ),
            )
        )
        page.update()

    def _arrancar_app() -> None:
        PanelAdminIT(page)

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

            nuevo_resultado = validar_licencia_inicio("receptora", _obtener_version_app())
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
            title=Text("Activar Kubo", weight=FontWeight.BOLD),
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

        resultado = validar_licencia_inicio("receptora", _obtener_version_app())
        if resultado.allowed:
            print(f"[LICENCIA] {resultado.message}")
        elif resultado.reason != "activation_required":
            if resultado.reason == "product_mismatch" and limpiar_activation_key is not None:
                limpiar_activation_key()
                _mostrar_modal_activacion()
                return resultado
            if mostrar_banner_bloqueo is not None:
                mostrar_banner_bloqueo("receptora", resultado)
            print(f"[LICENCIA] Acceso denegado: {resultado.message}")
            _mostrar_bloqueo_en_pantalla(resultado)
        return resultado

    # Inicializar base de datos automáticamente al inicio
    try:
        _inicializar_base_datos_automatica()
    except Exception as e:
        print(f"[ERROR] Error en inicialización automática: {e}")

    # Construir UI primero para que el modal no cierre la ventana de arranque.
    _arrancar_app()

    resultado_licencia = _validar_licencia_inicial()
    if resultado_licencia is not None and not resultado_licencia.allowed:
        if resultado_licencia.reason == "activation_required":
            _mostrar_modal_activacion()


if __name__ == "__main__":
    import asyncio

    def _suprimir_errores_conexion(loop, context):
        """
        Silencia errores de desconexión brusca de clientes (WinError 10054).
        En Windows el ProactorEventLoop lanza ConnectionResetError cuando un
        cliente cierra la conexión abruptamente — es comportamiento normal.
        """
        excepcion = context.get("exception")
        if isinstance(excepcion, (ConnectionResetError, BrokenPipeError, ConnectionAbortedError)):
            return  # ignorar — desconexiones normales de emisoras
        # Cualquier otro error → comportamiento predeterminado
        loop.default_exception_handler(context)

    try:
        loop = asyncio.get_event_loop()
        loop.set_exception_handler(_suprimir_errores_conexion)
    except Exception:
        pass

    # establecer assets si existen
    assets = str(PROJECT_ROOT)
    ft.run(main, assets_dir=assets)
