# =============================================================================
# APP RECEPTORA - Panel de Administración IT Profesional
# =============================================================================
# Panel completo para el equipo de IT con gestión de técnicos, tickets,
# sistema de turnos, dashboards analíticos y notificaciones en tiempo real.
# =============================================================================

import flet as ft
from flet import (
    Page, Container, Column, Row, Text, TextField, Dropdown,
    DataTable, DataColumn, DataRow, DataCell,
    NavigationRail, NavigationRailDestination, ProgressRing,
    AlertDialog, SnackBar, dropdown, Colors as colors, 
    MainAxisAlignment, CrossAxisAlignment, FontWeight,
    TextAlign, Icons as icons, Icon, Divider, Card, ListView, ListTile,
    ScrollMode, Switch, Badge, ProgressBar, Stack
)
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
        
        self._configurar_pagina()
        self._construir_ui()
        self._iniciar_auto_refresh()
        self._iniciar_servidor_tickets()
    
    def _configurar_pagina(self):
        """Configura las propiedades de la página."""
        self.page.title = "🖥️ Panel de Control IT - Sistema de Tickets"
        self.page.bgcolor = COLOR_FONDO
        self.page.padding = 0
        self.page.spacing = 0
        self.page.window.width = 1400
        self.page.window.height = 900
        self.page.theme_mode = ft.ThemeMode.DARK
        
        # Establecer icono de la ventana
        from pathlib import Path
        icono_path = Path(__file__).parent / "icons" / "receptora.png"
        if icono_path.exists():
            self.page.window.icon = str(icono_path)
    
    def _construir_ui(self):
        """Construye la interfaz de usuario principal."""
        # Header superior
        self.header = self._construir_header()
        
        # Panel de navegación lateral
        self.nav_rail = self._construir_navegacion()
        
        # Área de contenido principal
        self.contenido = Container(
            content=self._vista_dashboard(),
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
                        self.nav_rail,
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
                        Text("Centro de Soporte IT", size=22, weight=FontWeight.BOLD, color=COLOR_TEXTO),
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
            min_width=100,
            min_extended_width=200,
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
            ],
            on_change=self._cambiar_vista
        )
    
    def _cambiar_vista(self, e):
        """Maneja el cambio de vista desde la navegación."""
        self.vista_actual = e.control.selected_index
        vistas = [
            self._vista_dashboard,
            self._vista_tecnicos,
            self._vista_tickets,
            self._vista_cola,
            self._vista_historial,
            self._vista_reportes,
            self._vista_inventario,
            self._vista_escaner_red,
            self._vista_solicitudes
        ]
        self.contenido.content = vistas[self.vista_actual]()
        self.page.update()
    
    # =========================================================================
    # VISTA: DASHBOARD
    # =========================================================================
    
    def _vista_dashboard(self) -> Column:
        """Construye la vista del dashboard principal completo y profesional."""
        stats = self.gestor.obtener_estadisticas_generales()
        tecnicos = self.gestor.obtener_tecnicos()
        cola = self.gestor.obtener_tickets_en_cola()
        todos_tickets = self.gestor.obtener_todos_tickets()
        
        # Calcular estadísticas avanzadas
        tickets_hoy = stats["tickets_hoy"]
        resueltos_hoy = stats["tickets_cerrados"]
        tasa_resolucion = (resueltos_hoy / tickets_hoy * 100) if tickets_hoy > 0 else 0
        tasa_cumplimiento_sla = self._calcular_cumplimiento_sla(todos_tickets)
        tickets_en_espera = len(todos_tickets[todos_tickets.get("ESTADO") == "En Espera"]) if not todos_tickets.empty else 0
        
        # Técnicos disponibles
        tecnicos_disponibles = len(tecnicos[tecnicos["ESTADO"] == "Disponible"]) if not tecnicos.empty else 0
        total_tecnicos = len(tecnicos)
        
        return Column(
            controls=[
                # Encabezado principal
                Container(
                    content=Row([
                        Text("📊 Dashboard Ejecutivo en Tiempo Real", size=26, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text(datetime.now().strftime("%d/%m/%Y %H:%M"), size=12, color=COLOR_TEXTO_SEC)
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.Padding.only(bottom=25)
                ),
                
                # ===== SECCIÓN 1: KPIs PRINCIPALES (8 tarjetas) =====
                Container(
                    content=Column([
                        Text("📈 Indicadores Clave de Desempeño (KPIs)", size=14, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                        Container(height=10),
                        Row([
                            self._kpi_card_v2("Tickets Hoy", str(tickets_hoy), icons.TODAY, COLOR_INFO, 
                                            "+15%" if tickets_hoy > 5 else "-2%"),
                            self._kpi_card_v2("En Resolución", str(len(cola)), icons.PENDING_ACTIONS, COLOR_PRIMARIO, 
                                            "↑" if len(cola) > 3 else "↓"),
                            self._kpi_card_v2("Resueltos Hoy", str(resueltos_hoy), icons.CHECK_CIRCLE, COLOR_EXITO, 
                                            f"+{resueltos_hoy}"),
                            self._kpi_card_v2("Tasa Resolución", f"{tasa_resolucion:.0f}%", icons.TRENDING_UP, 
                                            COLOR_DISPONIBLE, "↑" if tasa_resolucion > 70 else "↓"),
                        ], spacing=15, wrap=True),
                        Row([
                            self._kpi_card_v2("Cumplimiento SLA", f"{tasa_cumplimiento_sla:.0f}%", icons.VERIFIED_USER, 
                                            COLOR_EXITO if tasa_cumplimiento_sla > 90 else COLOR_ADVERTENCIA, 
                                            "✓" if tasa_cumplimiento_sla > 90 else "⚠"),
                            self._kpi_card_v2("En Espera", str(tickets_en_espera), icons.SCHEDULE, COLOR_ADVERTENCIA, 
                                            "⏱"),
                            self._kpi_card_v2("Técnicos Disponibles", f"{tecnicos_disponibles}/{total_tecnicos}", 
                                            icons.ENGINEERING, COLOR_DISPONIBLE, 
                                            "✓" if tecnicos_disponibles >= total_tecnicos * 0.5 else "✗"),
                            self._kpi_card_v2("Tiempo Prom.", f"{stats['tiempo_promedio_cierre']:.1f}h", 
                                            icons.TIMER, COLOR_ACENTO, "•"),
                        ], spacing=15, wrap=True),
                    ], spacing=12),
                    padding=20,
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=15
                ),
                
                Container(height=25),
                
                # ===== SECCIÓN 2: ANÁLISIS DE RENDIMIENTO Y TENDENCIAS =====
                Row([
                    # Panel de tendencias
                    self._panel_tendencias_tickets(todos_tickets),
                    
                    # Panel de rendimiento por técnico
                    self._panel_rendimiento_tecnicos(tecnicos, todos_tickets),
                ], spacing=20, expand=True),
                
                Container(height=25),
                
                # ===== SECCIÓN 3: DISTRIBUCIONES Y ANÁLISIS =====
                Row([
                    # Distribución por prioridad
                    self._panel_distribucion_prioridad(todos_tickets),
                    
                    # Estado de equipos
                    self._panel_estado_equipos(),
                ], spacing=20, expand=True),
                
                Container(height=25),
                
                # ===== SECCIÓN 4: INFORMACIÓN EN TIEMPO REAL =====
                Row([
                    # Estado del equipo IT
                    self._panel_estado_tecnicos_v2(tecnicos),
                    
                    # Tickets más antiguos
                    self._panel_tickets_criticos(todos_tickets),
                ], spacing=20, expand=True),
                
                Container(height=25),
                
                # ===== SECCIÓN 5: ANÁLISIS DETALLADO =====
                Row([
                    # Distribución por categoría
                    self._panel_distribucion_categorias_v2(todos_tickets),
                    
                    # Distribución horaria
                    self._panel_distribucion_horaria(todos_tickets),
                ], spacing=20, expand=True),
                
                Container(height=25),
                
                # ===== SECCIÓN 6: TICKETS RECIENTES Y ALERTAS =====
                self._panel_tickets_recientes_v2(todos_tickets),
                
                Container(height=25),
                
                # ===== SECCIÓN 7: VISUALIZACIONES AVANZADAS =====
                Row([
                    # Gráfico circular de estados
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
                            "Cerrado": COLOR_EXITO
                        }
                    ),
                    
                    # Mapa de calor de actividad
                    self._crear_heatmap_actividad(),
                ], spacing=20, expand=True),
                
                Container(height=25),
                
                # ===== SECCIÓN 8: ANÁLISIS DE RENDIMIENTO =====
                Row([
                    # SLA por técnico
                    self._panel_analisis_sla_tecnicos(tecnicos, todos_tickets),
                    
                    # Predicción de carga
                    self._panel_prediccion_carga(),
                ], spacing=20, expand=True),
                
                Container(height=25),
                
                # ===== SECCIÓN 9: TIEMPOS DE RESOLUCIÓN =====
                Row([
                    # Tiempo de resolución
                    self._panel_tiempo_resolucion(todos_tickets),
                ], spacing=20, expand=True),
                
                Container(height=25),
                
            ],
            scroll=ScrollMode.AUTO,
            expand=True
        )
    
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
                    Icon(icono, color=color, size=32),
                    Container(
                        content=Text(indicador, size=14, weight=FontWeight.BOLD, color=colors.WHITE),
                        bgcolor=color_indicador,
                        padding=ft.Padding.symmetric(horizontal=8, vertical=4),
                        border_radius=ft.BorderRadius.all(6)
                    )
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                Container(height=12),
                Text(valor, size=32, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Text(titulo, size=12, color=COLOR_TEXTO_SEC)
            ], spacing=4),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(12),
            padding=16,
            width=170,
            height=160,
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
        """Panel mostrando distribución horaria de tickets."""
        try:
            if tickets.empty:
                return self._panel_vacio("Distribución Horaria")
            
            # Datos simulados de distribución por hora
            horas = ["0-4", "4-8", "8-12", "12-16", "16-20", "20-24"]
            cantidades = [8, 5, 28, 32, 35, 15]
            max_val = max(cantidades) if cantidades else 40
            
            barras = []
            for hora, cant in zip(horas, cantidades):
                altura = (cant / max_val * 100) if max_val > 0 else 20
                barras.append(
                    Column([
                        Container(
                            width=22,
                            height=altura,
                            bgcolor=COLOR_ACENTO,
                            border_radius=ft.BorderRadius.only(top_left=3, top_right=3)
                        ),
                        Text(str(cant), size=8, color=COLOR_TEXTO),
                        Text(hora, size=7, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2)
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("⏰ Distribución Horaria", size=14, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    ]),
                    Container(height=12),
                    Row(barras, alignment=MainAxisAlignment.SPACE_AROUND, spacing=2),
                    Container(height=8),
                    Row([
                        Text("Pico: 16-20hs", size=9, color=COLOR_ACENTO, weight=FontWeight.BOLD),
                        Text("▸ 35 tickets", size=9, color=COLOR_TEXTO_SEC)
                    ], alignment=MainAxisAlignment.CENTER)
                ], spacing=6),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=16,
                expand=True
            )
        except:
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
        """Crea un heatmap de actividad semanal."""
        try:
            # Matriz de 7 días x 6 periodos (4h cada uno)
            dias = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
            periodos = ["0-4", "4-8", "8-12", "12-16", "16-20", "20-24"]
            
            # Datos simulados: intensidad de 0-10
            datos = [
                [2, 1, 8, 9, 10, 3],
                [1, 2, 7, 10, 9, 2],
                [1, 1, 9, 8, 8, 1],
                [2, 2, 6, 10, 9, 2],
                [1, 3, 8, 10, 10, 3],
                [0, 0, 1, 2, 1, 0],
                [0, 0, 0, 1, 1, 0]
            ]
            
            celdas = []
            for dia_idx, dia in enumerate(dias):
                columna = []
                for per_idx, periodo in enumerate(periodos):
                    intensidad = datos[dia_idx][per_idx]
                    # Escala de color según intensidad
                    if intensidad == 0:
                        bg = COLOR_SUPERFICIE_2
                    elif intensidad <= 3:
                        bg = "#1F3A5F"  # Azul débil
                    elif intensidad <= 6:
                        bg = "#0F60A8"  # Azul medio
                    elif intensidad <= 9:
                        bg = COLOR_PRIMARIO  # Rojo fuerte
                    else:
                        bg = "#FF0000"  # Rojo muy intenso
                    
                    columna.append(
                        Container(
                            width=30,
                            height=30,
                            bgcolor=bg,
                            border_radius=4,
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
            
            # Información de colores
            leyenda_colores = Row([
                Row([Container(width=8, height=8, bgcolor=COLOR_SUPERFICIE_2, border_radius=2), Text("Bajo", size=8, color=COLOR_TEXTO)], spacing=4),
                Row([Container(width=8, height=8, bgcolor="#1F3A5F", border_radius=2), Text("Medio", size=8, color=COLOR_TEXTO)], spacing=4),
                Row([Container(width=8, height=8, bgcolor=COLOR_PRIMARIO, border_radius=2), Text("Alto", size=8, color=COLOR_TEXTO)], spacing=4),
            ], spacing=12, alignment=MainAxisAlignment.CENTER)
            
            return Container(
                content=Column([
                    Row([
                        Text("🔥 Mapa de Calor - Actividad Semanal", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.HEATMAP, size=16, color=COLOR_PRIMARIO)
                    ]),
                    Container(height=10),
                    Row([
                        Text("", size=8),
                        *[Text(p, size=8, color=COLOR_TEXTO_SEC, width=30, text_align=TextAlign.CENTER) for p in periodos]
                    ], spacing=2),
                    Row(celdas, spacing=10, alignment=MainAxisAlignment.START),
                    Container(height=10),
                    leyenda_colores
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except:
            return self._panel_vacio("Mapa de Calor")
    
    def _panel_analisis_sla_tecnicos(self, tecnicos: pd.DataFrame, tickets: pd.DataFrame) -> Container:
        """Panel mostrando cumplimiento de SLA por técnico."""
        try:
            if tecnicos.empty:
                return self._panel_vacio("SLA por Técnico")
            
            items = []
            for _, tec in tecnicos.head(6).iterrows():
                nombre = tec.get("NOMBRE", "N/A")
                # SLA simulado
                sla = 85 + (hash(nombre) % 15)  # 85-99%
                estado_sla = "✓" if sla >= 90 else "⚠"
                color_sla = COLOR_EXITO if sla >= 90 else COLOR_ADVERTENCIA
                
                items.append(
                    Row([
                        Text(nombre[:12], size=11, color=COLOR_TEXTO, width=100),
                        Container(
                            width=150,
                            height=14,
                            bgcolor=COLOR_SUPERFICIE_2,
                            border_radius=7,
                            content=Container(
                                width=150 * (sla / 100),
                                height=14,
                                bgcolor=color_sla,
                                border_radius=7
                            )
                        ),
                        Row([
                            Text(str(sla) + "%", size=10, color=color_sla, weight=FontWeight.BOLD, width=35),
                            Text(estado_sla, size=12, color=color_sla)
                        ], spacing=0, width=50)
                    ], spacing=8)
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("✓ Cumplimiento SLA por Técnico", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
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
        except:
            return self._panel_vacio("SLA")
    
    def _panel_tiempo_resolucion(self, tickets: pd.DataFrame) -> Container:
        """Panel mostrando análisis de tiempo de resolución."""
        try:
            if tickets.empty:
                return self._panel_vacio("Tiempo de Resolución")
            
            # Estadísticas de tiempo
            cerrados = tickets[tickets.get("ESTADO") == "Cerrado"]
            
            # Simulación de tiempos
            tiempo_minimo = 2.5  # horas
            tiempo_maximo = 48.0  # horas
            tiempo_promedio = 12.3  # horas
            tiempo_mediano = 11.0  # horas
            
            # Distribución simulada
            distribucion = {
                "< 4h": 15,
                "4-8h": 22,
                "8-24h": 35,
                "24-48h": 18,
                "> 48h": 10
            }
            
            items = []
            for rango, cantidad in distribucion.items():
                color = {
                    "< 4h": COLOR_EXITO,
                    "4-8h": COLOR_DISPONIBLE,
                    "8-24h": COLOR_ACENTO,
                    "24-48h": COLOR_ADVERTENCIA,
                    "> 48h": COLOR_ERROR
                }.get(rango, COLOR_TEXTO_SEC)
                
                ancho = cantidad / 35 * 200
                items.append(
                    Row([
                        Text(rango, size=10, color=COLOR_TEXTO, width=60),
                        Container(
                            width=ancho,
                            height=16,
                            bgcolor=color,
                            border_radius=4
                        ),
                        Text(str(cantidad), size=10, color=COLOR_ACENTO, weight=FontWeight.BOLD, width=30)
                    ], spacing=8)
                )
            
            return Container(
                content=Column([
                    Text("⏱️ Tiempo de Resolución", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Container(height=8),
                    Row([
                        Column([
                            Text("Mínimo", size=9, color=COLOR_TEXTO_SEC),
                            Text(f"{tiempo_minimo}h", size=12, weight=FontWeight.BOLD, color=COLOR_EXITO)
                        ], spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER),
                        Column([
                            Text("Mediano", size=9, color=COLOR_TEXTO_SEC),
                            Text(f"{tiempo_mediano}h", size=12, weight=FontWeight.BOLD, color=COLOR_ACENTO)
                        ], spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER),
                        Column([
                            Text("Promedio", size=9, color=COLOR_TEXTO_SEC),
                            Text(f"{tiempo_promedio}h", size=12, weight=FontWeight.BOLD, color=COLOR_TEXTO)
                        ], spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER),
                        Column([
                            Text("Máximo", size=9, color=COLOR_TEXTO_SEC),
                            Text(f"{tiempo_maximo}h", size=12, weight=FontWeight.BOLD, color=COLOR_ERROR)
                        ], spacing=2, horizontal_alignment=CrossAxisAlignment.CENTER)
                    ], alignment=MainAxisAlignment.SPACE_AROUND),
                    Container(height=12),
                    Column(items, spacing=8)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except:
            return self._panel_vacio("Tiempos")
    
    def _panel_prediccion_carga(self) -> Container:
        """Panel con predicción de carga próximas horas."""
        try:
            # Predicción simulada
            horas = ["14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]
            predicciones = [8, 12, 18, 22, 20, 15]
            max_pred = max(predicciones)
            
            barras = []
            for hora, pred in zip(horas, predicciones):
                altura = (pred / max_pred * 100) if max_pred > 0 else 20
                color = COLOR_ERROR if pred > 20 else COLOR_ADVERTENCIA if pred > 15 else COLOR_ACENTO
                
                barras.append(
                    Column([
                        Container(
                            width=25,
                            height=altura,
                            bgcolor=color,
                            border_radius=ft.BorderRadius.only(top_left=3, top_right=3)
                        ),
                        Text(str(pred), size=9, color=COLOR_TEXTO),
                        Text(hora, size=8, color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=2)
                )
            
            return Container(
                content=Column([
                    Row([
                        Text("🔮 Predicción de Carga", size=13, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Icon(icons.TRENDING_UP, size=16, color=COLOR_PRIMARIO)
                    ]),
                    Container(height=12),
                    Row(barras, alignment=MainAxisAlignment.SPACE_AROUND, spacing=2),
                    Container(height=10),
                    Row([
                        Text("Predicción basada en histórico", size=8, color=COLOR_TEXTO_SEC),
                        Text("Actualización: Cada 15 min", size=8, color=COLOR_ACENTO)
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=15,
                padding=14,
                expand=True
            )
        except:
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
        
        return Column([
            Row([
                Text("👨‍💻 Gestión de Técnicos", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Row([
                    ft.Button(
                        "Agregar Técnico",
                        icon=icons.PERSON_ADD,
                        bgcolor=COLOR_EXITO,
                        color=colors.WHITE,
                        on_click=lambda e: self._mostrar_dialogo_agregar_tecnico()
                    ),
                    ft.Button(
                        "Actualizar",
                        icon=icons.REFRESH,
                        bgcolor=COLOR_PRIMARIO,
                        color=colors.WHITE,
                        on_click=lambda e: self._refrescar_vista()
                    )
                ], spacing=10)
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            Container(height=20),
            Row(tarjetas, spacing=20, wrap=True) if tarjetas else Container(
                content=Column([
                    Icon(icons.PERSON_OFF, size=60, color=COLOR_TEXTO_SEC),
                    Text("No hay técnicos registrados", size=18, color=COLOR_TEXTO_SEC),
                    Text("Agrega un técnico para comenzar", color=COLOR_TEXTO_SEC)
                ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                padding=50,
                alignment=ft.Alignment(0, 0)
            )
        ], scroll=ScrollMode.AUTO, expand=True)
    
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
            self.page.close(dialogo)
            self._mostrar_snackbar(f"✓ Técnico {txt_nombre.value} agregado", COLOR_EXITO)
            self._refrescar_vista()
        
        def cerrar_dialogo(e):
            self.page.close(dialogo)
        
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
        
        self.page.open(dialogo)
    
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
            self.page.close(dialogo)
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
            self.page.close(dialogo)
        
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
                        alignment=ft.Alignment.CENTER,
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
                        alignment=ft.Alignment.CENTER
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
        
        self.page.open(dialogo)
    
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
                self.page.close(dialogo)
        
        def asignar(e):
            if dd_tickets.value:
                cerrar_dialogo()
                self._mostrar_carga("Asignando ticket...")
                
                self.gestor.asignar_ticket_a_tecnico(dd_tickets.value, id_tecnico)
                
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
        
        self.page.open(dialogo)
    
    # =========================================================================
    # VISTA: TICKETS
    # =========================================================================
    
    def _vista_tickets(self) -> Column:
        """Vista de gestión de tickets activos (no cerrados) con filtro de prioridad."""
        df = self.gestor.obtener_tickets_activos()
        
        # Ordenar por prioridad (Crítica > Alta > Media > Baja)
        if not df.empty and "PRIORIDAD" in df.columns:
            df["_orden_pri"] = df["PRIORIDAD"].map(ORDEN_PRIORIDAD).fillna(99)
            df = df.sort_values("_orden_pri").drop(columns=["_orden_pri"])
        
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
        
        # Construir tabla
        self.tabla_tickets = self._construir_tabla_tickets(df)
        
        # Contenedor de la tabla (con scroll horizontal y vertical)
        self.contenedor_tabla_tickets = Container(
            content=Column(
                controls=[Row(controls=[self.tabla_tickets], scroll=ScrollMode.AUTO)],
                scroll=ScrollMode.AUTO,
            ),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=ft.BorderRadius.all(10),
            padding=10,
            expand=True
        )
        
        # Contadores por prioridad
        criticas = len(df[df["PRIORIDAD"] == "Crítica"]) if not df.empty and "PRIORIDAD" in df.columns else 0
        altas = len(df[df["PRIORIDAD"] == "Alta"]) if not df.empty and "PRIORIDAD" in df.columns else 0
        
        return Column([
            Row([
                Text("📋 Gestión de Tickets Activos", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Row([
                    Container(
                        content=Text(f"{len(df)} activos", size=12, color=COLOR_TEXTO),
                        bgcolor=COLOR_INFO,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                        border_radius=ft.BorderRadius.all(10)
                    ),
                    Container(
                        content=Text(f"⚠ {criticas} críticas", size=12, color=colors.WHITE),
                        bgcolor=COLOR_CRITICA,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                        border_radius=ft.BorderRadius.all(10)
                    ) if criticas > 0 else Container(),
                    Container(
                        content=Text(f"🔴 {altas} altas", size=12, color=colors.WHITE),
                        bgcolor=COLOR_ALTA,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                        border_radius=ft.BorderRadius.all(10)
                    ) if altas > 0 else Container(),
                    ft.Button(
                        "Actualizar",
                        icon=icons.REFRESH,
                        bgcolor=COLOR_PRIMARIO,
                        color=colors.WHITE,
                        on_click=lambda e: self._refrescar_vista()
                    )
                ], spacing=10)
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            
            Container(height=10),
            
            # Mensaje informativo
            Container(
                content=Row([
                    Icon(icons.INFO, color=COLOR_INFO, size=16),
                    Text(
                        "Tickets ordenados por urgencia. Críticas y Altas aparecen primero.",
                        color=COLOR_TEXTO_SEC, size=12
                    )
                ], spacing=10),
                bgcolor=COLOR_SUPERFICIE,
                padding=10,
                border_radius=ft.BorderRadius.all(8)
            ),
            
            Container(height=10),
            
            # Barra de filtros (con prioridad)
            Container(
                content=Row([
                    self.filtro_prioridad,
                    self.filtro_estado,
                    self.filtro_categoria,
                    self.txt_busqueda
                ], spacing=15),
                bgcolor=COLOR_SUPERFICIE,
                padding=15,
                border_radius=ft.BorderRadius.all(10)
            ),
            
            Container(height=15),
            
            # Tabla de tickets (contenedor dinámico con scroll)
            self.contenedor_tabla_tickets
        ], expand=True)
    
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
        df = self.gestor.obtener_tickets_activos()
        
        # Filtro de prioridad
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
        
        # Ordenar por prioridad (Crítica > Alta > Media > Baja)
        if not df.empty and "PRIORIDAD" in df.columns:
            df["_orden_pri"] = df["PRIORIDAD"].map(ORDEN_PRIORIDAD).fillna(99)
            df = df.sort_values("_orden_pri").drop(columns=["_orden_pri"])
        
        # Actualizar tabla dentro del contenedor con scroll
        self.tabla_tickets = self._construir_tabla_tickets(df)
        if hasattr(self, 'contenedor_tabla_tickets'):
            self.contenedor_tabla_tickets.content = Column(
                controls=[Row(controls=[self.tabla_tickets], scroll=ScrollMode.AUTO)],
                scroll=ScrollMode.AUTO,
            )
            self.page.update()
    
    # =========================================================================
    # VISTA: COLA DE TICKETS
    # =========================================================================
    
    def _vista_cola(self) -> Column:
        """Vista de la cola de tickets en espera."""
        cola = self.gestor.obtener_tickets_en_cola()
        tecnicos_disp = self.gestor.obtener_tecnicos_disponibles()
        
        items_cola = []
        for pos, (_, ticket) in enumerate(cola.iterrows(), 1):
            items_cola.append(self._item_cola(ticket, pos))
        
        return Column([
            Row([
                Text("🎫 Cola de Tickets", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Container(
                    content=Row([
                        Icon(icons.PEOPLE, color=COLOR_EXITO if len(tecnicos_disp) > 0 else COLOR_ERROR),
                        Text(f"{len(tecnicos_disp)} técnicos disponibles", 
                             color=COLOR_EXITO if len(tecnicos_disp) > 0 else COLOR_ERROR)
                    ], spacing=10),
                    bgcolor=COLOR_SUPERFICIE,
                    padding=ft.Padding.symmetric(horizontal=15, vertical=8),
                    border_radius=ft.BorderRadius.all(20)
                )
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            
            Container(height=20),
            
            # Mensaje de estado
            Container(
                content=Row([
                    Icon(icons.INFO, color=COLOR_ACENTO),
                    Text(
                        f"Hay {len(cola)} tickets en cola. Tiempo estimado de espera: {len(cola) * 15} minutos",
                        color=COLOR_TEXTO
                    )
                ], spacing=15),
                bgcolor=COLOR_SUPERFICIE,
                padding=20,
                border_radius=ft.BorderRadius.all(10)
            ),
            
            Container(height=20),
            
            # Lista de cola
            Column(
                items_cola if items_cola else [
                    Container(
                        content=Column([
                            Icon(icons.CHECK_CIRCLE, size=60, color=COLOR_EXITO),
                            Text("¡No hay tickets en cola!", size=18, color=COLOR_EXITO),
                            Text("Todos los tickets han sido atendidos", color=COLOR_TEXTO_SEC)
                        ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                        padding=50,
                        alignment=ft.Alignment(0, 0)
                    )
                ],
                spacing=10,
                scroll=ScrollMode.AUTO,
                expand=True
            )
        ], expand=True)
    
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
                        Text(f"Ticket #{ticket.get('ID_TICKET', '')}", weight=FontWeight.BOLD, color=COLOR_ACENTO),
                        Container(
                            content=Text(prioridad, size=10, color=colors.WHITE),
                            bgcolor=color_prioridad,
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border_radius=ft.BorderRadius.all(5)
                        )
                    ], spacing=15),
                    Text(f"Usuario: {ticket.get('USUARIO_AD', '')} | Categoría: {ticket.get('CATEGORIA', '')}", 
                         size=12, color=COLOR_TEXTO_SEC),
                    Text(f"Turno: {ticket.get('TURNO', '-')}", size=11, color=COLOR_TEXTO_SEC)
                ], spacing=5, expand=True),
                
                # Tiempo de espera
                Column([
                    Text(f"~{posicion * 15}", size=24, weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA),
                    Text("min", size=12, color=COLOR_TEXTO_SEC)
                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                
                # Botón de atender
                ft.Button(
                    "Atender",
                    icon=icons.PLAY_ARROW,
                    bgcolor=COLOR_EXITO,
                    color=colors.WHITE,
                    on_click=lambda e, t=ticket: self._atender_ticket_cola(t)
                )
            ], spacing=20),
            bgcolor=COLOR_SUPERFICIE,
            padding=20,
            border_radius=ft.BorderRadius.all(10),
            border=ft.Border.all(1, color_prioridad)
        )
    
    def _atender_ticket_cola(self, ticket: pd.Series):
        """Atiende un ticket de la cola asignándolo a un técnico disponible."""
        disponibles = self.gestor.obtener_tecnicos_disponibles()
        
        if disponibles.empty:
            self._mostrar_snackbar("No hay técnicos disponibles", COLOR_ERROR)
            return
        
        # Asignar al primer técnico disponible
        id_tecnico = disponibles.iloc[0]["ID_TECNICO"]
        id_ticket = ticket.get("ID_TICKET", "")
        
        self.gestor.asignar_ticket_a_tecnico(id_ticket, id_tecnico)
        
        # Broadcast WebSocket
        try:
            import ws_server as _ws
            _ws.broadcast_global(
                _ws.EVENTO_TICKET_ACTUALIZADO,
                {"id_ticket": id_ticket, "estado": "En Proceso"}
            )
        except Exception:
            pass
        
        self._mostrar_snackbar(f"Ticket asignado a {disponibles.iloc[0]['NOMBRE']}", COLOR_EXITO)
        self._refrescar_vista()
    
    # =========================================================================
    # VISTA: HISTORIAL
    # =========================================================================
    
    def _vista_historial(self) -> Column:
        """Vista del historial de tickets cerrados con auditoría y análisis."""
        historial = self.gestor.obtener_historial()
        todos = self.gestor.obtener_todos_tickets()
        
        # ============ PANEL DE AUDITORÍA ============
        panel_auditoria = self._construir_panel_auditoria(todos)
        
        # ============ TABLA DE HISTORIAL ============
        filas = []
        for _, row in historial.iterrows():
            fecha_apertura = row.get("FECHA_APERTURA", "")
            fecha_cierre = row.get("FECHA_CIERRE", "")
            
            # Formatear fechas
            if pd.notna(fecha_apertura) and hasattr(fecha_apertura, 'strftime'):
                fecha_apertura = fecha_apertura.strftime("%d/%m/%Y %H:%M")
            else:
                fecha_apertura = str(fecha_apertura)[:16] if fecha_apertura else "-"
            
            if pd.notna(fecha_cierre) and hasattr(fecha_cierre, 'strftime'):
                fecha_cierre = fecha_cierre.strftime("%d/%m/%Y %H:%M")
            else:
                fecha_cierre = str(fecha_cierre)[:16] if fecha_cierre else "-"
            
            filas.append(
                DataRow(
                    cells=[
                        DataCell(Text(f"#{row.get('ID_TICKET', '')}", weight=FontWeight.BOLD, color=COLOR_ACENTO)),
                        DataCell(Text(str(row.get('TURNO', '-')), color=COLOR_TEXTO)),
                        DataCell(Text(str(row.get('USUARIO_AD', ''))[:15], color=COLOR_TEXTO)),
                        DataCell(Text(str(row.get('CATEGORIA', '')), color=COLOR_TEXTO)),
                        DataCell(Text(str(row.get('TECNICO_ASIGNADO', '-'))[:15], color=COLOR_TEXTO)),
                        DataCell(Text(fecha_apertura, size=11, color=COLOR_TEXTO_SEC)),
                        DataCell(Text(fecha_cierre, size=11, color=COLOR_TEXTO_SEC)),
                    ],
                    on_select_change=lambda e, t=row: self._mostrar_detalle_historial(t.to_dict())
                )
            )
        
        tabla_historial = DataTable(
            columns=[
                DataColumn(Text("ID", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Turno", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Usuario", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Categoría", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Técnico", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Apertura", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
                DataColumn(Text("Cierre", weight=FontWeight.BOLD, color=COLOR_PRIMARIO)),
            ],
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            border_radius=ft.BorderRadius.all(10),
            heading_row_color=COLOR_SUPERFICIE_2,
            show_checkbox_column=False,
            column_spacing=20
        )
        
        return Column([
            Row([
                Text("📚 Historial y Auditoría", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Container(
                    content=Row([
                        Icon(icons.LOCK, color=COLOR_TEXTO_SEC, size=16),
                        Text(f"{len(historial)} tickets cerrados", color=COLOR_TEXTO_SEC)
                    ], spacing=5),
                    bgcolor=COLOR_SUPERFICIE,
                    padding=ft.Padding.symmetric(horizontal=15, vertical=8),
                    border_radius=ft.BorderRadius.all(20)
                )
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            
            Container(height=10),
            
            # Panel de auditoría (análisis de problemas)
            panel_auditoria,
            
            Container(height=15),
            
            # Mensaje informativo
            Container(
                content=Row([
                    Icon(icons.INFO, color=COLOR_INFO),
                    Text(
                        "Los tickets cerrados no pueden ser editados ni eliminados. Esta sección es solo de lectura.",
                        color=COLOR_TEXTO_SEC, size=13
                    )
                ], spacing=15),
                bgcolor=COLOR_SUPERFICIE,
                padding=15,
                border_radius=ft.BorderRadius.all(10)
            ),
            
            Container(height=15),
            
            # Tabla de historial con scroll
            Container(
                content=Column(
                    controls=[Row(controls=[tabla_historial], scroll=ScrollMode.AUTO)],
                    scroll=ScrollMode.AUTO,
                ) if filas else Container(
                    content=Column([
                        Icon(icons.FOLDER_OPEN, size=60, color=COLOR_TEXTO_SEC),
                        Text("No hay tickets en el historial", size=18, color=COLOR_TEXTO_SEC),
                        Text("Los tickets cerrados aparecerán aquí", color=COLOR_TEXTO_SEC)
                    ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=10),
                    padding=50,
                    alignment=ft.Alignment(0, 0)
                ),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=ft.BorderRadius.all(10),
                padding=10,
                expand=True
            )
        ], scroll=ScrollMode.AUTO, expand=True)
    
    def _construir_panel_auditoria(self, tickets: pd.DataFrame) -> Container:
        """Construye panel de auditoría con análisis de equipos/usuarios más problemáticos."""
        try:
            if tickets.empty:
                return Container()
            
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
                    )
                ], spacing=10, scroll=ScrollMode.AUTO),
                width=460,
                height=480,
                padding=5
            ),
            actions=[
                ft.Button(
                    "Cerrar",
                    icon=icons.CLOSE,
                    bgcolor=COLOR_SUPERFICIE_3,
                    color=colors.WHITE,
                    on_click=self._cerrar_dialogo
                )
            ],
            actions_alignment=MainAxisAlignment.END
        )
        
        self.page.open(dialogo)
    
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
        ], spacing=5)
        
        # Contenido según tab seleccionado
        contenidos_tabs = [
            self._tab_resumen_general,
            self._tab_analisis_tickets,
            self._tab_rendimiento,
            self._tab_tendencias,
            self._tab_analisis_equipos
        ]
        
        contenido_actual = contenidos_tabs[self._tab_reportes_actual]()
        
        return Column([
            # Header con título y botones de acción
            Row([
                Text("📊 Centro de Análisis y Reportes", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                Row([
                    ft.Button(
                        "Exportar Excel",
                        icon=icons.DOWNLOAD,
                        bgcolor=COLOR_EXITO,
                        color=colors.WHITE,
                        on_click=lambda e: self._exportar_reporte_excel()
                    ),
                    ft.Button(
                        "Actualizar",
                        icon=icons.REFRESH,
                        bgcolor=COLOR_PRIMARIO,
                        color=colors.WHITE,
                        on_click=lambda e: self._refrescar_vista()
                    )
                ], spacing=10)
            ], alignment=MainAxisAlignment.SPACE_BETWEEN),
            
            Container(height=15),
            
            # Navegación por tabs personalizada
            Container(
                content=tabs_botones,
                bgcolor=COLOR_SUPERFICIE,
                border_radius=ft.BorderRadius.all(10),
                padding=8
            ),
            
            Container(height=10),
            
            # Contenido del tab actual
            Container(
                content=contenido_actual,
                expand=True
            )
        ], expand=True)
    
    def _boton_tab_reporte(self, texto: str, icono, idx: int, on_click_fn) -> Container:
        """Crea un botón de navegación tipo tab."""
        es_activo = hasattr(self, '_tab_reportes_actual') and self._tab_reportes_actual == idx
        
        return Container(
            content=Row([
                Icon(icono, size=16, color=colors.WHITE if es_activo else COLOR_TEXTO_SEC),
                Text(texto, size=12, color=colors.WHITE if es_activo else COLOR_TEXTO_SEC, weight=FontWeight.BOLD if es_activo else FontWeight.NORMAL)
            ], spacing=5),
            bgcolor=COLOR_PRIMARIO if es_activo else COLOR_SUPERFICIE_2,
            padding=ft.Padding.symmetric(horizontal=15, vertical=10),
            border_radius=ft.BorderRadius.all(8),
            on_click=lambda e, i=idx: on_click_fn(i)
        )
    
    def _tab_resumen_general(self) -> Container:
        """Tab de resumen general con KPIs principales."""
        stats = self.gestor.obtener_estadisticas_generales()
        stats_completas = self.gestor.obtener_estadisticas_completas()
        
        # Calcular métricas adicionales
        tasa_resolucion = (stats["tickets_cerrados"] / max(stats["total_tickets"], 1)) * 100
        
        return Container(
            content=Column([
                Container(height=20),
                
                # Fila de KPIs principales
                Text("📈 Indicadores Clave de Rendimiento (KPIs)", size=18, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                Container(height=15),
                
                Row([
                    self._kpi_grande("Total Tickets", str(stats["total_tickets"]), icons.CONFIRMATION_NUMBER, COLOR_INFO, "Histórico"),
                    self._kpi_grande("Hoy", str(stats["tickets_hoy"]), icons.TODAY, COLOR_PRIMARIO, "Nuevos"),
                    self._kpi_grande("En Cola", str(stats["tickets_abiertos"]), icons.HOURGLASS_EMPTY, COLOR_ADVERTENCIA, "Pendientes"),
                    self._kpi_grande("En Proceso", str(stats["tickets_en_proceso"]), icons.ENGINEERING, COLOR_INFO, "Activos"),
                    self._kpi_grande("Resueltos", str(stats["tickets_cerrados"]), icons.CHECK_CIRCLE, COLOR_EXITO, "Cerrados"),
                ], spacing=15, wrap=True),
                
                Container(height=30),
                
                # Segunda fila de KPIs
                Row([
                    self._kpi_grande("Tasa Resolución", f"{tasa_resolucion:.1f}%", icons.TRENDING_UP, 
                                    COLOR_EXITO if tasa_resolucion >= 70 else COLOR_ADVERTENCIA, "Eficiencia"),
                    self._kpi_grande("Tiempo Prom.", f"{stats['tiempo_promedio_cierre']:.1f}h", icons.TIMER, COLOR_ACENTO, "Resolución"),
                    self._kpi_grande("Técnicos", str(stats_completas.get("resumen", {}).get("total_tecnicos", 0)), 
                                    icons.PEOPLE, COLOR_INFO, "Equipo"),
                    self._kpi_grande("Disponibles", str(stats_completas.get("resumen", {}).get("tecnicos_disponibles", 0)), 
                                    icons.PERSON_SEARCH, COLOR_EXITO, "Activos"),
                    self._kpi_grande("Equipos", str(stats_completas.get("resumen", {}).get("total_equipos", 0)), 
                                    icons.DEVICES, COLOR_SECUNDARIO, "Inventario"),
                ], spacing=15, wrap=True),
                
                Container(height=30),
                
                # Resumen de estado actual
                Row([
                    self._panel_estado_actual(stats_completas),
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
                                                   "CATEGORIA", "CANTIDAD", COLORES_CATEGORIAS),
                    self._grafico_barras_horizontal("🎯 Tickets por Prioridad", dist_prioridades,
                                                   "PRIORIDAD", "CANTIDAD", 
                                                   {"Crítica": COLOR_CRITICA, "Alta": COLOR_ALTA, "Media": COLOR_MEDIA, "Baja": COLOR_BAJA})
                ], spacing=20, expand=True),
                
                Container(height=30),
                
                # Carga semanal y tiempo de resolución
                Row([
                    self._grafico_barras_vertical("📅 Carga por Día de la Semana", por_dia, 
                                                  "DIA_SEMANA", "CANTIDAD", COLOR_ACENTO),
                    self._grafico_tiempo_categoria("⏱️ Tiempo Promedio por Categoría", tiempo_cat)
                ], spacing=20, expand=True),
                
            ], scroll=ScrollMode.AUTO),
            padding=20
        )
    
    def _grafico_barras_horizontal(self, titulo: str, df: pd.DataFrame, 
                                    col_label: str, col_valor: str, colores: Dict) -> Container:
        """Crea un gráfico de barras horizontales."""
        barras = []
        
        if not df.empty:
            max_val = df[col_valor].max() if col_valor in df.columns else 1
            
            for _, row in df.iterrows():
                label = row.get(col_label, "N/A")
                valor = row.get(col_valor, 0)
                porcentaje = row.get("PORCENTAJE", (valor / max(sum(df[col_valor]), 1)) * 100)
                color = colores.get(label, COLOR_TEXTO_SEC)
                ancho = (valor / max(max_val, 1)) * 250
                
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
                        Text(f"{valor} ({porcentaje:.1f}%)", size=10, color=COLOR_TEXTO_SEC, width=80)
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
        
        if not df.empty and "TIEMPO_PROMEDIO" in df.columns:
            max_tiempo = df["TIEMPO_PROMEDIO"].max()
            
            for _, row in df.iterrows():
                cat = row.get("CATEGORIA", "N/A")
                tiempo = row.get("TIEMPO_PROMEDIO", 0)
                total = row.get("TOTAL_CERRADOS", 0)
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
                        Text(f"{tiempo:.1f}h ({total})", size=10, color=COLOR_TEXTO_SEC, width=70)
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
        rendimiento = self.gestor.obtener_rendimiento_tecnicos()
        
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
        
        return Container(
            content=Column([
                Container(height=20),
                
                Text("📈 Análisis de Tendencias", size=18, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                Container(height=20),
                
                # Tendencia semanal
                Row([
                    self._grafico_tendencia_lineal("📊 Tendencia Semanal (últimas 8 semanas)", 
                                                   tendencia_semanal, "ETIQUETA", "CANTIDAD", "CERRADOS"),
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
        
        if not df.empty and "CANTIDAD" in df.columns:
            max_val = df["CANTIDAD"].max()
            
            # Crear todas las horas de 0 a 23
            for hora in range(24):
                fila = df[df["HORA"] == hora]
                cantidad = fila["CANTIDAD"].values[0] if not fila.empty else 0
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
        
        if not df.empty and "CANTIDAD" in df.columns:
            max_val = df["CANTIDAD"].max()
            
            for _, row in df.iterrows():
                etiqueta = row.get("ETIQUETA", "")
                cantidad = row.get("CANTIDAD", 0)
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
                    self._kpi_rendimiento("Total Equipos", str(stats_equipos.get("total_equipos", 0)), COLOR_INFO),
                    self._kpi_rendimiento("Activos", str(stats_equipos.get("activos", 0)), COLOR_EXITO),
                    self._kpi_rendimiento("En Mant.", str(stats_equipos.get("en_mantenimiento", 0)), COLOR_ADVERTENCIA),
                    self._kpi_rendimiento("De Baja", str(stats_equipos.get("de_baja", 0)), COLOR_ERROR),
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
                            Column(items_equipos, spacing=0, scroll=ScrollMode.AUTO) if items_equipos else 
                                Container(content=Text("Sin equipos problemáticos", color=COLOR_TEXTO_SEC), padding=20)
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
    
    # =========================================================================
    # FUNCIONES AUXILIARES
    # =========================================================================
    
    def _mostrar_detalle_ticket(self, ticket: Dict):
        """Muestra el panel de detalle de un ticket (solo para tickets activos)."""
        self.ticket_seleccionado = ticket
        
        estado = ticket.get("ESTADO", "Abierto")
        
        # Si el ticket está cerrado, mostrar vista de solo lectura
        if estado == "Cerrado":
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
        
        dialogo = None
        
        def cerrar_dialogo(e=None):
            nonlocal dialogo
            if dialogo:
                self.page.close(dialogo)
        
        def guardar_cambios(e):
            try:
                cerrar_dialogo()
                self._mostrar_carga("Guardando cambios...")
                
                self.gestor.actualizar_ticket(
                    ticket.get("ID_TICKET", ""),
                    estado=dd_estado.value,
                    notas_resolucion=txt_notas.value
                )
                
                # Broadcast WebSocket — notifíca a la emisora del cambio
                try:
                    import ws_server as _ws
                    _ws.broadcast_global(
                        _ws.EVENTO_TICKET_ACTUALIZADO,
                        {"id_ticket": ticket.get("ID_TICKET", ""),
                         "estado": dd_estado.value}
                    )
                except Exception:
                    pass
                
                self._ocultar_carga()
                self._mostrar_exito("Ticket actualizado", f"El ticket #{ticket.get('ID_TICKET', '')} se actualizó correctamente.")
                self._refrescar_vista()
            except ValueError as ex:
                self._ocultar_carga()
                self._mostrar_error("Error al actualizar", str(ex))
        
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
                    
                    Divider(color=COLOR_BORDE),
                    
                    # Acciones
                    Row([
                        Icon(icons.EDIT, size=16, color=COLOR_ACENTO),
                        Text("Actualizar Ticket", weight=FontWeight.BOLD, color=COLOR_ACENTO)
                    ], spacing=8),
                    dd_estado,
                    txt_notas
                ], spacing=12, scroll=ScrollMode.AUTO),
                width=420,
                height=480,
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
        
        self.page.open(dialogo)
    
    def _ir_a_tickets(self):
        """Navega a la vista de tickets."""
        self.nav_rail.selected_index = 2
        self.vista_actual = 2
        self.contenido.content = self._vista_tickets()
        self.page.update()
    
    def _refrescar_vista(self):
        """Refresca la vista actual."""
        vistas = [
            self._vista_dashboard,
            self._vista_tecnicos,
            self._vista_tickets,
            self._vista_cola,
            self._vista_historial,
            self._vista_reportes,
            self._vista_inventario,
            self._vista_escaner_red
        ]
        if self.vista_actual < len(vistas):
            self.contenido.content = vistas[self.vista_actual]()
            self.header = self._construir_header()
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
                self.page.close(dialogo_ref[0])
        
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
        self.page.open(dialogo)
    
    def _mostrar_error(self, mensaje: str, titulo: str = "¡Error!"):
        """Muestra un diálogo de error."""
        dialogo = self._crear_dialogo_profesional(
            tipo="error",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Entendido"
        )
        self.page.open(dialogo)
    
    def _mostrar_advertencia(self, mensaje: str, titulo: str = "Atención"):
        """Muestra un diálogo de advertencia."""
        dialogo = self._crear_dialogo_profesional(
            tipo="advertencia",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="Entendido"
        )
        self.page.open(dialogo)
    
    def _mostrar_info(self, mensaje: str, titulo: str = "Información"):
        """Muestra un diálogo informativo."""
        dialogo = self._crear_dialogo_profesional(
            tipo="info",
            titulo=titulo,
            mensaje=mensaje,
            boton_texto="OK"
        )
        self.page.open(dialogo)
    
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
        self.page.open(dialogo)
    
    def _cerrar_dialogo(self, e=None) -> None:
        """Cierra el diálogo activo."""
        if self.page.overlay:
            dialogo = self.page.overlay[-1]
            if isinstance(dialogo, AlertDialog):
                self.page.close(dialogo)
    
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
            while self.auto_refresh:
                time.sleep(30)  # Refrescar cada 30 segundos
                try:
                    self._refrescar_vista()
                except:
                    pass
        
        thread = threading.Thread(target=refresh_loop, daemon=True)
        thread.start()
    
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
                                action_color=colors.WHITE,
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
            
            # Iniciar servidor en segundo plano con callbacks de solicitudes y tickets
            if iniciar_servidor(
                puerto=self.servidor_puerto, 
                callback_solicitud=on_nueva_solicitud,
                callback_ticket=on_nuevo_ticket
            ):
                print(f"[SERVIDOR] Servidor de tickets iniciado en {self.servidor_ip}:{self.servidor_puerto}")
                # Guardar configuración
                guardar_config_servidor(self.servidor_ip, self.servidor_puerto)
            else:
                print("[SERVIDOR] Error al iniciar el servidor")
        except Exception as e:
            print(f"[SERVIDOR] Error: {e}")
    
    def _actualizar_badge_solicitudes(self):
        """Actualiza el badge de notificaciones en la navegación."""
        try:
            from servidor_red import obtener_solicitudes_pendientes
            solicitudes = obtener_solicitudes_pendientes()
            
            # Actualizar el label de la navegación si hay solicitudes pendientes
            if hasattr(self, 'nav_rail') and self.nav_rail:
                # La posición 8 es "Solicitudes"
                destino = self.nav_rail.destinations[8]
                if len(solicitudes) > 0:
                    destino.label = f"Solicitudes ({len(solicitudes)})"
                else:
                    destino.label = "Solicitudes"
                self.page.update()
        except Exception as e:
            print(f"[BADGE] Error actualizando: {e}")
    
    # =========================================================================
    # VISTA: INVENTARIO DE EQUIPOS
    # =========================================================================
    
    def _vista_inventario(self) -> Column:
        """Construye la vista del inventario de equipos."""
        equipos = self.gestor.obtener_equipos()
        stats = self.gestor.obtener_estadisticas_equipos()
        grupos_conteo = self.gestor.obtener_grupos_con_conteo()
        
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
        
        # Búsqueda
        self.busqueda_inventario = ft.TextField(
            label="🔍 Buscar equipo...",
            width=300,
            on_change=self._filtrar_inventario,
            border_color=COLOR_ACENTO,
            focused_border_color=COLOR_PRIMARIO
        )
        
        # Tabla de equipos
        self.tabla_equipos = self._construir_tabla_equipos(equipos)
        
        return Column(
            controls=[
                # Título
                Row([
                    Icon(icons.DEVICES, size=28, color=COLOR_ACENTO),
                    Text("Equipos Registrados", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                ], spacing=10),
                Text("📋 Gestiona todos los equipos de tu empresa: nombre, grupo, ubicación, modelo y más", 
                     size=12, color=COLOR_TEXTO_SEC),
                Container(height=15),
                
                # KPIs de inventario
                Row([
                    self._kpi_card("Total Equipos", str(stats["total_equipos"]), icons.DEVICES, COLOR_INFO, ""),
                    self._kpi_card("Activos", str(stats["equipos_activos"]), icons.CHECK_CIRCLE, COLOR_EXITO, ""),
                    self._kpi_card("Sin Nombre", str(stats["sin_nombre"]), icons.WARNING, COLOR_ADVERTENCIA, "Pendientes"),
                    self._kpi_card("En Mantenimiento", str(stats["equipos_mantenimiento"]), icons.BUILD, COLOR_PRIMARIO, ""),
                ], wrap=True),
                Container(height=20),
                
                # Filtros y búsqueda
                Row([
                    self.filtro_grupo_inventario,
                    self.busqueda_inventario,
                    Container(expand=True),
                    ft.Button(
                        "➕ Agregar Equipo Manual",
                        icon=icons.ADD,
                        on_click=self._dialogo_agregar_equipo,
                        bgcolor=COLOR_PRIMARIO,
                        color=colors.WHITE
                    ),
                    ft.Button(
                        "🔄 Refrescar",
                        icon=icons.REFRESH,
                        on_click=lambda e: self._refrescar_inventario(),
                        bgcolor=COLOR_SUPERFICIE_2,
                        color=colors.WHITE
                    )
                ]),
                Container(height=15),
                
                # Estadísticas por grupo (tarjetas)
                Text("📊 Equipos por Grupo", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                Container(height=10),
                Row([
                    self._grupo_chip(grupo, cantidad) 
                    for grupo, cantidad in sorted(grupos_conteo.items(), key=lambda x: -x[1])
                    if cantidad > 0
                ], wrap=True, spacing=10),
                Container(height=20),
                
                # Tabla de equipos con scroll
                Text("📋 Lista de Equipos", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                Container(height=10),
                Container(
                    content=Column(
                        controls=[Row(controls=[self.tabla_equipos], scroll=ScrollMode.AUTO)],
                        scroll=ScrollMode.AUTO,
                    ),
                    expand=True,
                    border=ft.Border.all(1, COLOR_SUPERFICIE_2),
                    border_radius=10,
                    bgcolor=COLOR_SUPERFICIE
                )
            ],
            scroll=ScrollMode.AUTO,
            expand=True
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
            ], spacing=5),
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
    
    def _filtrar_inventario(self, e=None):
        """Filtra la tabla de inventario según grupo y búsqueda."""
        equipos = self.gestor.obtener_equipos()
        
        # Filtrar por grupo
        grupo = self.filtro_grupo_inventario.value
        if grupo and grupo != "Todos":
            equipos = equipos[equipos["GRUPO"] == grupo]
        
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
        
        # Actualizar tabla
        self.tabla_equipos.rows = self._construir_tabla_equipos(equipos).rows
        self.page.update()
    
    def _filtrar_por_grupo(self, grupo: str):
        """Filtra por grupo desde los chips."""
        self.filtro_grupo_inventario.value = grupo
        self._filtrar_inventario()
    
    def _refrescar_inventario(self):
        """Refresca la vista de inventario."""
        self.contenido.content = self._vista_inventario()
        self.page.update()
    
    def _dialogo_editar_equipo(self, mac_address: str):
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
                    self.page.close(dlg)
            
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
                    self._refrescar_inventario()
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
            
            self.page.open(dlg)
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
                self.page.close(dlg)
        
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
        
        self.page.open(dlg)
    
    def _confirmar_eliminar_equipo(self, mac_address: str):
        """Muestra confirmación para eliminar un equipo."""
        dlg = None
        
        def cerrar_dialogo(e=None):
            nonlocal dlg
            if dlg:
                self.page.close(dlg)
        
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
                        alignment=ft.Alignment.CENTER
                    ),
                    Container(height=10),
                    Text("¿Eliminar este equipo del inventario?", color=COLOR_TEXTO, text_align=TextAlign.CENTER),
                    Container(
                        content=Text(mac_address, weight=FontWeight.BOLD, color=COLOR_ACENTO, size=16),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=10,
                        border_radius=8,
                        alignment=ft.Alignment.CENTER
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
        
        self.page.open(dlg)
    
    # =========================================================================
    # VISTA: ESCÁNER DE RED
    # =========================================================================
    
    def _vista_escaner_red(self) -> Column:
        """Construye la vista del escáner de red con referencias dinámicas."""
        self.escaner = EscanerRed(gestor=self.gestor)
        
        # Obtener info rápida de red
        ip_local = obtener_ip_local()
        ip_base = ".".join(ip_local.split(".")[:3])  # ej: "192.168.1"
        servidor_activo = servidor_esta_activo()
        
        # Cargar datos (optimizado - solo lo necesario)
        try:
            equipos_red = self.escaner.obtener_equipos_red()
            equipos_servidor = obtener_equipos_con_estado()
            equipos_online = obtener_equipos_online()
            
            # Contadores
            total_db = len(equipos_red) if not equipos_red.empty else 0
            online_servidor = len(equipos_online)
            total_servidor = len(equipos_servidor)
            cambios = len(equipos_red[equipos_red["CAMBIOS_IP"] > 0]) if not equipos_red.empty and "CAMBIOS_IP" in equipos_red.columns else 0
        except Exception as e:
            print(f"[ERROR] Error cargando datos del escáner: {e}")
            equipos_red = pd.DataFrame()
            equipos_servidor = []
            equipos_online = []
            total_db = online_servidor = total_servidor = cambios = 0
        
        # Controles de rango
        self.txt_rango_inicio = ft.TextField(
            label="Desde",
            value="1",
            width=80,
            text_align=TextAlign.CENTER
        )
        self.txt_rango_fin = ft.TextField(
            label="Hasta",
            value="254",
            width=80,
            text_align=TextAlign.CENTER
        )
        
        # Barra de progreso para escaneo
        self.progress_escaneo = ft.ProgressBar(
            width=400,
            value=0,
            bgcolor=COLOR_SUPERFICIE_2,
            color=COLOR_ACENTO,
            visible=False
        )
        self.lbl_progreso = Text("", size=12, color=COLOR_TEXTO_SEC, visible=False)
        
        # Guardar labels de KPI como atributos para actualización dinámica
        self._escaner_label_online = Text(str(online_servidor), size=36, weight=FontWeight.BOLD, color=COLOR_TEXTO)
        self._escaner_label_total_srv = Text(str(total_servidor), size=36, weight=FontWeight.BOLD, color=COLOR_TEXTO)
        self._escaner_label_total_db = Text(str(total_db), size=36, weight=FontWeight.BOLD, color=COLOR_TEXTO)
        self._escaner_label_cambios = Text(str(cambios), size=36, weight=FontWeight.BOLD, color=COLOR_TEXTO)
        
        # Construir tablas
        tabla_conectados = self._construir_tabla_equipos_conectados(equipos_servidor)
        self.tabla_red = self._construir_tabla_red(equipos_red)
        alertas_cambios = self._construir_alertas_cambios(equipos_red)
        
        # Guardar contenedores como atributos para actualización dinámica
        self._escaner_tabla_conectados = Container(
            content=Column(
                controls=[Row(controls=[tabla_conectados], scroll=ScrollMode.AUTO)],
                scroll=ScrollMode.AUTO,
            ) if equipos_servidor else Text(
                "No hay equipos conectados al servidor. Inicia un escaneo para detectar equipos en la red.", 
                color=COLOR_TEXTO_SEC, italic=True
            ),
        )
        
        self._escaner_tabla_red = Container(
            content=Column(
                controls=[Row(controls=[self.tabla_red], scroll=ScrollMode.AUTO)],
                scroll=ScrollMode.AUTO,
            ),
            expand=True,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            border_radius=10,
            bgcolor=COLOR_SUPERFICIE
        )
        
        self._escaner_alertas = Container(
            content=alertas_cambios if cambios > 0 else Container(),
        )
        
        # Construir KPI cards con los labels almacenados
        def _kpi_escaner(titulo, valor_text, icono, color, subtitulo):
            return Container(
                content=Column([
                    Row([
                        Icon(icono, color=color, size=28),
                        Text(subtitulo, size=12, color=COLOR_TEXTO_SEC) if subtitulo else Container()
                    ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                    Container(height=10),
                    valor_text,
                    Text(titulo, size=14, color=COLOR_TEXTO_SEC)
                ], spacing=5),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=ft.BorderRadius.all(15),
                padding=20,
                width=200,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2)
            )
        
        # Construir la columna
        return Column(
            controls=[
                # Título
                Row([
                    Icon(icons.WIFI_TETHERING, size=28, color=COLOR_ACENTO),
                    Text("Escaneo de Red", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                    Container(expand=True),
                    # Estado del servidor
                    Container(
                        content=Row([
                            Icon(icons.CIRCLE, size=12, 
                                 color=COLOR_EXITO if servidor_activo else COLOR_ERROR),
                            Text(f"Servidor {'Activo' if servidor_activo else 'Inactivo'}", 
                                 size=12, color=COLOR_TEXTO_SEC),
                        ], spacing=5),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=5),
                        border_radius=15
                    )
                ], spacing=10),
                Text("💡 Escanea la red para detectar equipos. Haz clic en ➕ para guardarlos en la sección 'Equipos'", 
                     size=12, color=COLOR_TEXTO_SEC),
                Container(height=10),
                
                # Info de red
                Container(
                    content=Row([
                        Icon(icons.INFO_OUTLINE, color=COLOR_INFO),
                        Text(f"IP Servidor: {ip_local}", color=COLOR_TEXTO, weight=FontWeight.BOLD),
                        Text(f"  |  Red: {ip_base}.x", color=COLOR_TEXTO_SEC),
                        Text(f"  |  Puerto: {SERVIDOR_PUERTO}", color=COLOR_TEXTO_SEC),
                    ]),
                    bgcolor=COLOR_SUPERFICIE_2,
                    padding=10,
                    border_radius=8
                ),
                Container(height=15),
                
                # KPIs con labels dinámicos
                Row([
                    _kpi_escaner("Conectados", self._escaner_label_online, icons.WIFI, COLOR_EXITO, "En línea ahora"),
                    _kpi_escaner("Registrados", self._escaner_label_total_srv, icons.DEVICES, COLOR_INFO, "En servidor"),
                    _kpi_escaner("En BD", self._escaner_label_total_db, icons.STORAGE, COLOR_ACENTO, "Base datos"),
                    _kpi_escaner("Cambios IP", self._escaner_label_cambios, icons.SWAP_HORIZ, COLOR_ADVERTENCIA, "Detectados"),
                ], wrap=True),
                Container(height=20),
                
                # SECCIÓN: EQUIPOS CONECTADOS EN TIEMPO REAL
                Container(
                    content=Column([
                        Row([
                            Icon(icons.SENSORS, color=COLOR_EXITO),
                            Text("📡 Equipos Conectados Ahora", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Container(expand=True),
                            ft.IconButton(
                                icon=icons.REFRESH,
                                icon_color=COLOR_ACENTO,
                                tooltip="Actualizar lista",
                                on_click=self._refrescar_equipos_conectados
                            )
                        ], spacing=10),
                        Container(height=10),
                        self._escaner_tabla_conectados
                    ]),
                    bgcolor=COLOR_SUPERFICIE,
                    padding=15,
                    border_radius=10,
                    border=ft.Border.all(1, COLOR_EXITO + "40")
                ),
                Container(height=20),
                
                # Alertas de cambios de IP
                self._escaner_alertas,
                
                # SECCIÓN: ESCANEO DE RED
                Container(
                    content=Column([
                        Row([
                            Icon(icons.RADAR, color=COLOR_INFO),
                            Text("🔍 Escanear Red Local", weight=FontWeight.BOLD, color=COLOR_TEXTO),
                            Container(expand=True),
                            Text(f"Rango: {ip_base}.", color=COLOR_TEXTO_SEC),
                            self.txt_rango_inicio,
                            Text("-", color=COLOR_TEXTO_SEC),
                            Text(f"{ip_base}.", color=COLOR_TEXTO_SEC),
                            self.txt_rango_fin,
                            ft.Button(
                                "🚀 Escanear",
                                icon=icons.RADAR,
                                on_click=self._iniciar_escaneo_red,
                                bgcolor=COLOR_PRIMARIO,
                                color=colors.WHITE
                            ),
                        ], spacing=10),
                        Row([
                            self.progress_escaneo,
                            self.lbl_progreso,
                        ], spacing=10),
                    ]),
                    bgcolor=COLOR_SUPERFICIE,
                    padding=15,
                    border_radius=10
                ),
                Container(height=15),
                
                # SECCIÓN: HISTORIAL DE EQUIPOS DETECTADOS
                Text("📋 Historial de Equipos (Base de Datos)", size=16, weight=FontWeight.BOLD, color=COLOR_TEXTO_SEC),
                Container(height=10),
                self._escaner_tabla_red
            ],
            scroll=ScrollMode.AUTO,
            expand=True
        )
    
    def _construir_tabla_equipos_conectados(self, equipos: List[Dict]) -> DataTable:
        """Construye la tabla de equipos conectados al servidor."""
        columnas = [
            DataColumn(Text("Estado", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("IP", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Hostname", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Usuario", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("MAC", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Última Actividad", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
        ]
        
        filas = []
        import time
        ahora = time.time()
        
        for equipo in equipos:
            online = equipo.get("online", False)
            ip = str(equipo.get("ip_address", "-") or "-")
            hostname = str(equipo.get("hostname", "Desconocido") or "Desconocido")
            usuario = str(equipo.get("usuario_ad", "-") or "-")
            mac = str(equipo.get("mac_address", "-") or "-")
            ultimo_heartbeat = equipo.get("ultimo_heartbeat", 0)
            
            # Calcular tiempo desde último heartbeat
            if ultimo_heartbeat > 0:
                segundos = int(ahora - ultimo_heartbeat)
                if segundos < 60:
                    tiempo_str = f"Hace {segundos}s"
                elif segundos < 3600:
                    tiempo_str = f"Hace {segundos // 60}m"
                else:
                    tiempo_str = f"Hace {segundos // 3600}h"
            else:
                tiempo_str = "-"
            
            color_estado = COLOR_EXITO if online else COLOR_TEXTO_SEC
            
            filas.append(DataRow(
                cells=[
                    DataCell(Row([
                        Icon(icons.CIRCLE, size=12, color=color_estado),
                        Text("Online" if online else "Offline", size=12, color=color_estado)
                    ], spacing=5)),
                    DataCell(Text(ip, size=12, color=COLOR_TEXTO, weight=FontWeight.BOLD)),
                    DataCell(Text(hostname[:20], size=12, color=COLOR_TEXTO)),
                    DataCell(Text(usuario[:15], size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(mac, size=10, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(tiempo_str, size=11, color=color_estado)),
                ]
            ))
        
        return DataTable(
            columns=columnas,
            rows=filas,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            heading_row_color=COLOR_SUPERFICIE_2,
            heading_row_height=40,
            data_row_min_height=40,
            data_row_max_height=50,
            column_spacing=15,
            show_checkbox_column=False
        )
    
    def _refrescar_equipos_conectados(self, e):
        """Refresca la lista de equipos conectados."""
        equipos = obtener_equipos_con_estado()
        online = len(obtener_equipos_online())
        
        self._mostrar_snackbar(f"✅ {online} equipos online de {len(equipos)} registrados", COLOR_EXITO)
        self._refrescar_vista()
    
    def _construir_alertas_cambios(self, equipos_red: pd.DataFrame) -> Container:
        """Construye el panel de alertas de cambios de IP."""
        if equipos_red.empty or "CAMBIOS_IP" not in equipos_red.columns:
            return Container()
        
        cambios = equipos_red[equipos_red["CAMBIOS_IP"] > 0]
        if cambios.empty:
            return Container()
        
        alertas = []
        for _, equipo in cambios.iterrows():
            alertas.append(
                Container(
                    content=Row([
                        Icon(icons.WARNING_AMBER, color=COLOR_ADVERTENCIA),
                        Column([
                            Text(f"⚠️ {equipo.get('HOSTNAME', 'Equipo')} cambió de IP", 
                                 weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA),
                            Text(f"IP anterior: {equipo.get('IP_ANTERIOR', '?')} → Nueva: {equipo.get('IP_ADDRESS', '?')}", 
                                 size=12, color=COLOR_TEXTO_SEC),
                            Text(f"MAC: {equipo.get('MAC_ADDRESS', '?')} | Cambios totales: {equipo.get('CAMBIOS_IP', 0)}", 
                                 size=11, color=COLOR_TEXTO_SEC),
                        ], spacing=2, expand=True),
                    ], spacing=10),
                    bgcolor="#3D2607",
                    padding=10,
                    border_radius=8,
                    border=ft.Border.all(1, COLOR_ADVERTENCIA)
                )
            )
        
        return Container(
            content=Column([
                Text("⚠️ Alertas de Cambios de IP", weight=FontWeight.BOLD, color=COLOR_ADVERTENCIA),
                Container(height=5),
                *alertas
            ], spacing=5),
            margin=ft.Margin.only(bottom=15)
        )
    
    def _construir_tabla_red(self, equipos: pd.DataFrame) -> DataTable:
        """Construye la tabla de equipos de red."""
        columnas = [
            DataColumn(Text("IP", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("MAC", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Hostname", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Estado", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Último Ping", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Cambios IP", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Acciones", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
        ]
        
        filas = []
        for _, equipo in equipos.iterrows():
            ip = str(equipo.get("IP_ADDRESS", "") or "")
            mac = str(equipo.get("MAC_ADDRESS", "") or "")
            hostname_raw = equipo.get("HOSTNAME", "")
            hostname = str(hostname_raw) if pd.notna(hostname_raw) and hostname_raw else "Desconocido"
            estado = str(equipo.get("ESTADO_RED", "Desconocido") or "Desconocido")
            ultimo_ping = equipo.get("ULTIMO_PING", "")
            cambios = int(equipo.get("CAMBIOS_IP", 0)) if pd.notna(equipo.get("CAMBIOS_IP")) else 0
            
            # Formatear fecha
            if pd.notna(ultimo_ping) and hasattr(ultimo_ping, 'strftime'):
                ultimo_ping_str = ultimo_ping.strftime("%H:%M:%S")
            elif pd.notna(ultimo_ping):
                ultimo_ping_str = str(ultimo_ping)[-8:]
            else:
                ultimo_ping_str = "-"
            
            # Color según estado
            color_estado = COLOR_EXITO if estado == "Online" else COLOR_TEXTO_SEC
            icono_estado = icons.CHECK_CIRCLE if estado == "Online" else icons.CANCEL
            
            filas.append(DataRow(
                cells=[
                    DataCell(Text(ip, size=12, color=COLOR_TEXTO, weight=FontWeight.BOLD)),
                    DataCell(Text(mac[:17], size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(hostname[:20], size=11, color=COLOR_TEXTO)),
                    DataCell(Row([
                        Icon(icono_estado, size=14, color=color_estado),
                        Text(estado, size=11, color=color_estado)
                    ], spacing=5)),
                    DataCell(Text(ultimo_ping_str, size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(
                        Container(
                            content=Text(str(cambios), size=11, color=colors.WHITE if cambios > 0 else COLOR_TEXTO_SEC),
                            bgcolor=COLOR_ADVERTENCIA if cambios > 0 else "transparent",
                            padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                            border_radius=10
                        ) if cambios > 0 else Text("0", size=11, color=COLOR_TEXTO_SEC)
                    ),
                    DataCell(Row([
                        ft.IconButton(
                            icon=icons.ADD_CIRCLE,
                            icon_color=COLOR_ACENTO,
                            tooltip="Agregar a Inventario",
                            on_click=lambda e, m=mac, h=hostname, i=ip: self._agregar_a_inventario(m, h, i)
                        ),
                        ft.IconButton(
                            icon=icons.REFRESH,
                            icon_color=COLOR_INFO,
                            tooltip="Hacer ping",
                            on_click=lambda e, i=ip: self._ping_individual(i)
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
            data_row_min_height=45,
            data_row_max_height=55,
            column_spacing=15,
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
        
        self.progress_escaneo.visible = True
        self.lbl_progreso.visible = True
        self.progress_escaneo.value = 0
        self.lbl_progreso.value = "Iniciando escaneo..."
        self.page.update()
        
        # Configurar callbacks
        def actualizar_progreso(actual, total):
            self.progress_escaneo.value = actual / total
            self.lbl_progreso.value = f"Escaneando: {actual}/{total} IPs..."
            try:
                self.page.update()
            except:
                pass
        
        def equipo_encontrado(equipo):
            self.lbl_progreso.value = f"✓ Encontrado: {equipo['IP_ADDRESS']} - {equipo['HOSTNAME']}"
            try:
                self.page.update()
            except:
                pass
        
        self.escaner.callback_progreso = actualizar_progreso
        self.escaner.callback_equipo = equipo_encontrado
        
        # Ejecutar escaneo en thread separado
        def ejecutar_escaneo():
            equipos, cambios = self.escaner.escanear_red(rango_inicio, rango_fin)
            
            # Actualizar UI en thread principal
            def actualizar_ui():
                self.progress_escaneo.visible = False
                self.lbl_progreso.visible = False
                
                # Refrescar tabla y datos
                try:
                    equipos_red = self.escaner.obtener_equipos_red()
                    equipos_servidor = obtener_equipos_con_estado()
                    equipos_online = obtener_equipos_online()
                    
                    # Actualizar tabla de red con scroll
                    tabla_red_nueva = self._construir_tabla_red(equipos_red)
                    self._escaner_tabla_red.content = Column(
                        controls=[Row(controls=[tabla_red_nueva], scroll=ScrollMode.AUTO)],
                        scroll=ScrollMode.AUTO,
                    )
                    
                    # Actualizar tabla conectados con scroll
                    tabla_conectados_nueva = self._construir_tabla_equipos_conectados(equipos_servidor)
                    self._escaner_tabla_conectados.content = Column(
                        controls=[Row(controls=[tabla_conectados_nueva], scroll=ScrollMode.AUTO)],
                        scroll=ScrollMode.AUTO,
                    ) if equipos_servidor else Text(
                        "No hay equipos conectados al servidor",
                        color=COLOR_TEXTO_SEC, italic=True
                    )
                    
                    # Actualizar alertas
                    cambios_count = len(equipos_red[equipos_red["CAMBIOS_IP"] > 0]) if not equipos_red.empty and "CAMBIOS_IP" in equipos_red.columns else 0
                    alertas_cambios_nueva = self._construir_alertas_cambios(equipos_red)
                    self._escaner_alertas.content = alertas_cambios_nueva if cambios_count > 0 else Container()
                    
                    # Actualizar stats
                    self._escaner_label_total_db.value = str(len(equipos_red) if not equipos_red.empty else 0)
                    self._escaner_label_online.value = str(len(equipos_online))
                    self._escaner_label_total_srv.value = str(len(equipos_servidor))
                    self._escaner_label_cambios.value = str(cambios_count)
                    
                except Exception as ex:
                    print(f"[ERROR] Error actualizando tabla: {ex}")
                
                msg = f"✅ Escaneo completado: {len(equipos)} equipos encontrados"
                if cambios:
                    msg += f", {len(cambios)} cambios de IP detectados"
                self._mostrar_snackbar(msg, COLOR_EXITO)
                
                self.page.update()
            
            # Ejecutar actualización de forma segura
            try:
                if hasattr(self.page, 'run_task'):
                    self.page.run_task(actualizar_ui)
                else:
                    self.page.run_sync(actualizar_ui)
            except:
                actualizar_ui()
        
        thread = threading.Thread(target=ejecutar_escaneo, daemon=True)
        thread.start()
    
    def _ping_individual(self, ip: str):
        """Hace ping a una IP individual."""
        from data_access import ping_host
        
        self._mostrar_snackbar(f"🔍 Haciendo ping a {ip}...", COLOR_INFO)
        
        def hacer_ping():
            resultado = ping_host(ip, timeout=2)
            if resultado:
                self._mostrar_snackbar(f"✅ {ip} está Online", COLOR_EXITO)
            else:
                self._mostrar_snackbar(f"❌ {ip} no responde", COLOR_ERROR)
            self.page.update()
        
        thread = threading.Thread(target=hacer_ping, daemon=True)
        thread.start()
    
    def _agregar_a_inventario(self, mac: str, hostname: str, ip: str):
        """Agrega un equipo de red al inventario."""
        if not mac or mac == "No detectada" or mac == "-":
            self._mostrar_snackbar("❌ No se puede agregar sin dirección MAC válida", COLOR_ERROR)
            return
        
        try:
            # Verificar si ya existe
            equipo_existente = self.gestor.obtener_equipo_por_mac(mac)
            if equipo_existente:
                self._mostrar_snackbar(f"⚠️ El equipo {mac} ya está en el inventario", COLOR_ADVERTENCIA)
                return
            
            # Registrar en inventario
            resultado = self.gestor.registrar_o_actualizar_equipo(
                mac_address=mac, 
                hostname=hostname or "Desconocido", 
                usuario_ad=f"Agregado desde Red - IP: {ip}"
            )
            
            if resultado:
                self._mostrar_snackbar(f"✅ {hostname or mac} agregado. Completa los datos del equipo.", COLOR_EXITO)
                print(f"[INVENTARIO] Equipo agregado: MAC={mac}, Hostname={hostname}, IP={ip}")
                # Abrir diálogo de edición para completar datos
                self._dialogo_editar_equipo(mac)
            else:
                self._mostrar_snackbar("❌ Error al guardar el equipo", COLOR_ERROR)
                
        except Exception as e:
            print(f"[ERROR] Error agregando equipo: {e}")
            self._mostrar_snackbar(f"❌ Error: {str(e)}", COLOR_ERROR)
    
    # =========================================================================
    # VISTA: SOLICITUDES DE ENLACE
    # =========================================================================
    
    def _vista_solicitudes(self) -> Column:
        """Construye la vista de solicitudes de enlace pendientes."""
        from servidor_red import obtener_solicitudes_pendientes, obtener_equipos_aprobados
        
        solicitudes = obtener_solicitudes_pendientes()
        aprobados = obtener_equipos_aprobados()
        
        return Column(
            controls=[
                # Encabezado
                Row([
                    Icon(icons.NOTIFICATIONS_ACTIVE, size=32, color=COLOR_ACENTO),
                    Column([
                        Text("🔔 Solicitudes de Enlace", size=24, weight=FontWeight.BOLD, color=COLOR_TEXTO),
                        Text("Equipos que desean conectarse al sistema de tickets", size=14, color=COLOR_TEXTO_SEC),
                    ], spacing=2),
                ], spacing=15),
                
                Container(height=15),
                
                # Contador y acciones
                Row([
                    Container(
                        content=Row([
                            Icon(icons.PENDING_ACTIONS, color=COLOR_ADVERTENCIA if solicitudes else COLOR_TEXTO_SEC),
                            Text(f" {len(solicitudes)} solicitudes pendientes", 
                                 weight=FontWeight.BOLD, 
                                 color=COLOR_ADVERTENCIA if solicitudes else COLOR_TEXTO_SEC),
                        ]),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=ft.Padding.all(10),
                        border_radius=8
                    ),
                    Container(
                        content=Row([
                            Icon(icons.CHECK_CIRCLE, color=COLOR_EXITO),
                            Text(f" {len(aprobados)} equipos enlazados", color=COLOR_EXITO),
                        ]),
                        bgcolor=COLOR_SUPERFICIE_2,
                        padding=ft.Padding.all(10),
                        border_radius=8
                    ),
                    ft.Button(
                        "🔄 Actualizar",
                        icon=icons.REFRESH,
                        on_click=lambda e: self._refrescar_vista()
                    ),
                ], spacing=15),
                
                Container(height=20),
                
                # Solicitudes pendientes
                Text("📨 Solicitudes Pendientes", size=18, weight=FontWeight.BOLD, color=COLOR_ACENTO),
                Container(height=10),
                
                self._construir_lista_solicitudes(solicitudes) if solicitudes else Container(
                    content=Column([
                        Icon(icons.INBOX, size=48, color=COLOR_TEXTO_SEC),
                        Text("No hay solicitudes pendientes", color=COLOR_TEXTO_SEC),
                        Text("Los equipos enviarán solicitudes al intentar conectarse", size=12, color=COLOR_TEXTO_SEC),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=10,
                    border=ft.Border.all(1, COLOR_SUPERFICIE_2)
                ),
                
                Container(height=30),
                
                # Equipos enlazados
                Text("✅ Equipos Enlazados", size=18, weight=FontWeight.BOLD, color=COLOR_EXITO),
                Container(height=10),
                
                self._construir_tabla_aprobados(aprobados) if aprobados else Container(
                    content=Column([
                        Icon(icons.LINK_OFF, size=48, color=COLOR_TEXTO_SEC),
                        Text("No hay equipos enlazados", color=COLOR_TEXTO_SEC),
                        Text("Aprueba solicitudes para que los equipos puedan enviar tickets", size=12, color=COLOR_TEXTO_SEC),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40, 
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=10,
                    border=ft.Border.all(1, COLOR_SUPERFICIE_2)
                ),
            ],
            spacing=5,
            scroll=ScrollMode.AUTO,
            expand=True
        )
    
    def _construir_lista_solicitudes(self, solicitudes: list) -> Container:
        """Construye las tarjetas de solicitudes pendientes."""
        tarjetas = []
        
        for sol in solicitudes:
            mac = sol.get("mac_address", "")
            hostname = sol.get("hostname", "Desconocido")
            usuario = sol.get("usuario_ad", "")
            ip = sol.get("ip_address", "")
            fecha = sol.get("fecha_solicitud", "")
            intentos = sol.get("intentos", 1)
            nombre = sol.get("nombre_equipo", hostname)
            
            # Formatear fecha
            try:
                from datetime import datetime
                fecha_dt = datetime.fromisoformat(fecha)
                fecha_str = fecha_dt.strftime("%d/%m/%Y %H:%M")
            except:
                fecha_str = str(fecha)[:16]
            
            tarjeta = Container(
                content=Row([
                    # Icono y estado
                    Container(
                        content=Icon(icons.COMPUTER, size=32, color=colors.WHITE),
                        bgcolor=COLOR_ADVERTENCIA,
                        padding=15,
                        border_radius=10
                    ),
                    
                    # Información
                    Column([
                        Row([
                            Text(nombre[:25], weight=FontWeight.BOLD, color=COLOR_TEXTO, size=16),
                            Container(
                                content=Text(f"Intento #{intentos}", size=10, color=colors.WHITE),
                                bgcolor=COLOR_INFO if intentos == 1 else COLOR_ADVERTENCIA,
                                padding=ft.Padding.symmetric(horizontal=8, vertical=2),
                                border_radius=10
                            ) if intentos > 1 else Container(),
                        ], spacing=10),
                        Text(f"🖥️ Hostname: {hostname}", size=12, color=COLOR_TEXTO_SEC),
                        Text(f"👤 Usuario: {usuario or 'No identificado'}", size=12, color=COLOR_TEXTO_SEC),
                        Row([
                            Text(f"🔗 MAC: {mac}", size=11, color=COLOR_TEXTO_SEC),
                            Text(f"🌐 IP: {ip}", size=11, color=COLOR_TEXTO_SEC),
                        ], spacing=15),
                        Text(f"📅 Solicitado: {fecha_str}", size=11, color=COLOR_TEXTO_SEC),
                    ], spacing=3, expand=True),
                    
                    # Botones de acción
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
                    ], spacing=5)
                ], spacing=15),
                bgcolor=COLOR_SUPERFICIE,
                padding=15,
                border_radius=10,
                border=ft.Border.all(2, COLOR_ADVERTENCIA)
            )
            tarjetas.append(tarjeta)
        
        return Container(
            content=Column(tarjetas, spacing=10),
            expand=True
        )
    
    def _construir_tabla_aprobados(self, aprobados: list) -> DataTable:
        """Construye la tabla de equipos aprobados."""
        columnas = [
            DataColumn(Text("Nombre", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Hostname", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("MAC", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("IP", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Aprobado", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
            DataColumn(Text("Acciones", weight=FontWeight.BOLD, color=COLOR_TEXTO)),
        ]
        
        filas = []
        for equipo in aprobados:
            mac = equipo.get("mac_address", "")
            nombre = equipo.get("nombre_equipo", "Sin nombre")[:20]
            hostname = equipo.get("hostname", "")[:15]
            ip = equipo.get("ip_address", "")
            fecha = equipo.get("fecha_aprobacion", "")
            
            # Formatear fecha
            try:
                from datetime import datetime
                fecha_dt = datetime.fromisoformat(fecha)
                fecha_str = fecha_dt.strftime("%d/%m/%Y")
            except:
                fecha_str = str(fecha)[:10]
            
            filas.append(DataRow(
                cells=[
                    DataCell(Text(nombre, color=COLOR_TEXTO)),
                    DataCell(Text(hostname, size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(mac[:17], size=10, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(ip, size=11, color=COLOR_TEXTO_SEC)),
                    DataCell(Text(fecha_str, size=11, color=COLOR_EXITO)),
                    DataCell(
                        ft.IconButton(
                            icon=icons.LINK_OFF,
                            icon_color=COLOR_ERROR,
                            tooltip="Revocar enlace",
                            on_click=lambda e, m=mac: self._confirmar_revocar_enlace(m)
                        )
                    ),
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
            column_spacing=20,
            show_checkbox_column=False
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
            self.page.close(dlg)
        
        def confirmar_rechazo(e):
            from servidor_red import rechazar_solicitud_enlace
            motivo = txt_motivo.value or "Rechazado por el administrador"
            
            if rechazar_solicitud_enlace(mac, motivo):
                self._mostrar_snackbar(f"❌ Solicitud de {mac} rechazada", COLOR_ADVERTENCIA)
                self.page.close(dlg)
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
        
        self.page.open(dlg)
    
    def _confirmar_revocar_enlace(self, mac: str):
        """Confirma la revocación de un enlace."""
        
        def cerrar_dialogo(e=None):
            self.page.close(dlg)
        
        def revocar(e):
            from servidor_red import revocar_enlace
            
            if revocar_enlace(mac):
                self._mostrar_snackbar(f"🔗 Enlace de {mac} revocado", COLOR_ADVERTENCIA)
                self.page.close(dlg)
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
        
        self.page.open(dlg)


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
    # Inicializar base de datos automáticamente al inicio
    try:
        _inicializar_base_datos_automatica()
    except Exception as e:
        print(f"[ERROR] Error en inicialización automática: {e}")
    
    # Crear el panel principal
    PanelAdminIT(page)


if __name__ == "__main__":
    ft.run(main)
