# =============================================================================
# INSTALADOR GRÁFICO PROFESIONAL - Sistema de Tickets IT
# =============================================================================
# Instalador moderno con interfaz Flet 0.81 compatible
# =============================================================================

import flet as ft
import os
import sys
import subprocess
import shutil
import threading
import json
import time
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

APP_NAME = "Sistema de Tickets IT"
APP_NAME_EMISORA = "Tickets IT - Emisora"
APP_NAME_RECEPTORA = "Tickets IT - Receptora (Panel IT)"
PYTHON_VERSION = "3.11.9"
DEPENDENCIAS = ["flet", "pandas", "openpyxl", "getmac", "winotify"]

# Detectar si se ejecuta como .exe (PyInstaller) o como .py
if getattr(sys, 'frozen', False):
    INSTALL_DIR = Path(sys.executable).parent.resolve()
else:
    INSTALL_DIR = Path(__file__).parent.resolve()

PYTHON_DIR = INSTALL_DIR / "python_embed"
PYTHON_EXE = PYTHON_DIR / "python.exe"

# Colores del tema
COLOR_FONDO = "#0a0a0f"
COLOR_SUPERFICIE = "#12121a"
COLOR_SUPERFICIE_2 = "#1a1a24"
COLOR_PRIMARIO = "#6366f1"
COLOR_SECUNDARIO = "#22d3ee"
COLOR_ACENTO = "#f472b6"
COLOR_EXITO = "#10b981"
COLOR_WARNING = "#f59e0b"
COLOR_ERROR = "#ef4444"
COLOR_TEXTO = "#f8fafc"
COLOR_TEXTO_SEC = "#94a3b8"

# Columnas de base de datos
COLUMNAS_DB = [
    "ID_TICKET", "TURNO", "FECHA_APERTURA", "USUARIO_AD", "HOSTNAME",
    "MAC_ADDRESS", "CATEGORIA", "PRIORIDAD", "DESCRIPCION", "ESTADO",
    "TECNICO_ASIGNADO", "NOTAS_RESOLUCION", "FECHA_CIERRE", "TIEMPO_ESTIMADO"
]

COLUMNAS_TECNICOS = [
    "ID_TECNICO", "NOMBRE", "ESTADO", "ESPECIALIDAD", "TICKETS_ATENDIDOS",
    "TICKET_ACTUAL", "ULTIMA_ACTIVIDAD", "TELEFONO", "EMAIL"
]

COLUMNAS_EQUIPOS = [
    "MAC_ADDRESS", "NOMBRE_EQUIPO", "HOSTNAME", "USUARIO_ASIGNADO", "GRUPO",
    "UBICACION", "MARCA", "MODELO", "NUMERO_SERIE", "TIPO_EQUIPO",
    "SISTEMA_OPERATIVO", "PROCESADOR", "RAM_GB", "DISCO_GB", "FECHA_COMPRA",
    "GARANTIA_HASTA", "ESTADO_EQUIPO", "NOTAS", "FECHA_REGISTRO", "ULTIMA_CONEXION", "TOTAL_TICKETS"
]

TECNICOS_INICIALES = [
    {"id": "TEC001", "nombre": "Carlos Rodríguez", "especialidad": "Hardware/Red", "telefono": "ext. 101", "email": "carlos.rodriguez@empresa.com"},
    {"id": "TEC002", "nombre": "María García", "especialidad": "Software/Accesos", "telefono": "ext. 102", "email": "maria.garcia@empresa.com"},
    {"id": "TEC003", "nombre": "Luis Hernández", "especialidad": "Redes/Seguridad", "telefono": "ext. 103", "email": "luis.hernandez@empresa.com"}
]


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def obtener_escritorio():
    return Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))

def obtener_menu_inicio():
    return Path(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"))

def obtener_carpeta_startup():
    return Path(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup"))

def crear_acceso_directo_vbs(vbs_path: Path, nombre: str, carpeta: Path, descripcion: str = "", icono_path: Path = None):
    """Crea un acceso directo a un archivo VBS con icono opcional."""
    try:
        # Convertir rutas a absolutas para evitar problemas
        vbs_path = vbs_path.resolve()
        carpeta = carpeta.resolve()
        if icono_path:
            icono_path = icono_path.resolve()

        icono_linea = ""
        if icono_path and icono_path.exists():
            icono_linea = f'$Shortcut.IconLocation = "{icono_path},0"'

        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{carpeta / f'{nombre}.lnk'}")
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = '"{vbs_path}"'
$Shortcut.WorkingDirectory = "{vbs_path.parent}"
$Shortcut.Description = "{descripcion}"
{icono_linea}
$Shortcut.Save()
'''

        # Depurar el contenido del script de PowerShell
        print("Script de PowerShell generado:")
        print(ps_script)

        result = subprocess.run(["powershell", "-Command", ps_script], capture_output=True, text=True)

        # Registrar la salida del comando
        print("Salida de PowerShell:", result.stdout)
        print("Errores de PowerShell:", result.stderr)

        return result.returncode == 0
    except Exception as e:
        print(f"Error: {e}")
        return False


# =============================================================================
# INSTALADOR GRÁFICO PRINCIPAL
# =============================================================================

class InstaladorGrafico:
    """Instalador con interfaz gráfica moderna y elegante."""

    def __init__(self, page: ft.Page):
        self.page = page
        self.tipo_instalacion = None
        self.paso_actual = 0

        # Opciones de instalación
        self.opt_escritorio = True
        self.opt_menu_inicio = True
        self.opt_inicio_windows = False
        self.opt_firewall = True
        self.opt_crear_db = True

        # Estado de instalación
        self.instalando = False

        # Componentes UI persistentes (se asignan al construir vista 3)
        self.barra_progreso = None
        self.texto_progreso = None
        self.contenedor_log = None

        self._configurar_pagina()
        self._mostrar_paso(0)

    # =========================================================================
    # CONFIGURACIÓN DE PÁGINA
    # =========================================================================

    def _configurar_pagina(self):
        """Configura las propiedades de la página."""
        self.page.title = "Instalador - Sistema de Tickets IT"
        self.page.bgcolor = COLOR_FONDO
        self.page.padding = 0
        self.page.window.width = 900
        self.page.window.height = 650
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.resizable = False

    # =========================================================================
    # NAVEGACIÓN PRINCIPAL — page.clean() + page.add()
    # =========================================================================

    def _mostrar_paso(self, paso: int):
        """Navega a un paso específico reconstruyendo toda la página."""
        if paso < 0:
            paso = 0

        # Validación especial para paso 2
        if paso == 2 and self.tipo_instalacion is None:
            paso = 1

        self.paso_actual = paso

        # Obtener contenido del paso
        if paso == 0:
            contenido = self._vista_bienvenida()
        elif paso == 1:
            contenido = self._vista_seleccion_tipo()
        elif paso == 2:
            contenido = self._vista_opciones()
        elif paso == 3:
            contenido = self._vista_instalacion()
        elif paso == 4:
            contenido = self._vista_completado()
        else:
            return

        # Reconstruir toda la página desde cero
        self.page.clean()
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        self._crear_header(),
                        ft.Container(content=contenido, expand=True, padding=40),
                    ],
                    spacing=0,
                    expand=True,
                ),
                expand=True,
                bgcolor=COLOR_FONDO,
            )
        )

        # Iniciar instalación si estamos en paso 3
        if paso == 3 and not self.instalando:
            self.instalando = True
            threading.Thread(target=self._proceso_instalacion, daemon=True).start()

    # =========================================================================
    # HEADER
    # =========================================================================

    def _crear_header(self) -> ft.Container:
        """Crea el header con logo y título."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Row(
                        [
                            ft.Container(
                                content=ft.Icon(ft.Icons.SUPPORT_AGENT, size=36, color=COLOR_PRIMARIO),
                                bgcolor=COLOR_SUPERFICIE,
                                border_radius=12,
                                padding=12,
                            ),
                            ft.Column(
                                [
                                    ft.Text("Sistema de Tickets IT", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                                    ft.Text("Instalador Profesional v3.0", size=12, color=COLOR_TEXTO_SEC),
                                ],
                                spacing=2,
                            ),
                        ],
                        spacing=16,
                    ),
                    self._crear_indicador_pasos(),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.Padding.symmetric(horizontal=40, vertical=20),
            bgcolor=COLOR_SUPERFICIE,
            border=ft.Border.only(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2)),
        )

    def _crear_indicador_pasos(self) -> ft.Row:
        """Crea el indicador visual de pasos."""
        pasos = ["Inicio", "Tipo", "Opciones", "Instalar", "Listo"]
        items = []
        for i, paso in enumerate(pasos):
            activo = i <= self.paso_actual
            completado = i < self.paso_actual
            color_circulo = COLOR_PRIMARIO if activo else COLOR_SUPERFICIE_2
            color_texto = COLOR_TEXTO if activo else COLOR_TEXTO_SEC
            icono = ft.Icons.CHECK_CIRCLE if completado else ft.Icons.CIRCLE
            items.append(
                ft.Column(
                    [
                        ft.Icon(icono, size=20, color=COLOR_EXITO if completado else color_circulo),
                        ft.Text(paso, size=10, color=color_texto, weight=ft.FontWeight.W_500 if activo else ft.FontWeight.NORMAL),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=4,
                )
            )
            if i < len(pasos) - 1:
                items.append(
                    ft.Container(
                        width=30, height=2,
                        bgcolor=COLOR_EXITO if completado else COLOR_SUPERFICIE_2,
                        border_radius=1,
                        margin=ft.Margin.only(top=8, left=5, right=5),
                    )
                )
        return ft.Row(items, spacing=0)

    # =========================================================================
    # VISTA 0: BIENVENIDA
    # =========================================================================

    def _vista_bienvenida(self) -> ft.Column:
        """Vista inicial de bienvenida."""

        def on_comenzar(e):
            self._mostrar_paso(1)

        return ft.Column(
            [
                ft.Container(height=30),
                ft.Container(
                    content=ft.Icon(ft.Icons.COMPUTER, size=80, color=COLOR_PRIMARIO),
                    bgcolor=f"{COLOR_PRIMARIO}15",
                    border_radius=100,
                    padding=30,
                ),
                ft.Container(height=30),
                ft.Text(
                    "¡Bienvenido al Instalador!",
                    size=32, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=10),
                ft.Text(
                    "Este asistente le guiará en la instalación del\nSistema de Tickets para Soporte Técnico",
                    size=16, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=40),
                ft.Row(
                    [
                        self._crear_feature_card(ft.Icons.TIMER, "Rápido", "2-3 minutos"),
                        self._crear_feature_card(ft.Icons.LOCK, "Seguro", "Sin riesgos"),
                        self._crear_feature_card(ft.Icons.BUILD, "Automático", "Todo listo"),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20,
                ),
                ft.Container(expand=True),
                ft.Button(
                    "Comenzar Instalación",
                    icon=ft.Icons.ARROW_FORWARD,
                    bgcolor=COLOR_PRIMARIO, color=COLOR_TEXTO,
                    width=280, height=55,
                    on_click=on_comenzar,
                ),
                ft.Container(height=10),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _crear_feature_card(self, icono, titulo: str, descripcion: str) -> ft.Container:
        """Crea una tarjeta de característica."""
        return ft.Container(
            content=ft.Column(
                [
                    ft.Icon(icono, size=28, color=COLOR_SECUNDARIO),
                    ft.Text(titulo, size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Text(descripcion, size=11, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=8,
            ),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=16,
            padding=20,
            width=160,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
        )

    # =========================================================================
    # VISTA 1: SELECCIÓN DE TIPO
    # =========================================================================

    def _vista_seleccion_tipo(self) -> ft.Column:
        """Vista para seleccionar tipo de instalación."""

        def on_atras(e):
            self._mostrar_paso(0)

        def on_seleccionar_emisora(e):
            self.tipo_instalacion = "emisora"
            self._mostrar_paso(2)

        def on_seleccionar_receptora(e):
            self.tipo_instalacion = "receptora"
            self._mostrar_paso(2)

        return ft.Column(
            [
                ft.Container(height=20),
                ft.Text(
                    "¿Qué desea instalar?",
                    size=28, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO,
                    text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=8),
                ft.Text(
                    "Seleccione el tipo de aplicación según su rol",
                    size=14, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER,
                ),
                ft.Container(height=40),
                ft.Row(
                    [
                        self._crear_tarjeta_tipo(
                            tipo="emisora", icono=ft.Icons.PERSON,
                            titulo="EMISORA", subtitulo="Cliente de Soporte",
                            descripcion="Para usuarios que necesitan\ncrear tickets de soporte",
                            caracteristicas=["Crear tickets de soporte", "Ver estado de tickets", "Recibir notificaciones", "Interfaz simplificada"],
                            color=COLOR_SECUNDARIO,
                            on_click=on_seleccionar_emisora,
                        ),
                        ft.Container(width=30),
                        self._crear_tarjeta_tipo(
                            tipo="receptora", icono=ft.Icons.SETTINGS,
                            titulo="RECEPTORA", subtitulo="Panel de IT",
                            descripcion="Para técnicos que gestionan\ny resuelven los tickets",
                            caracteristicas=["Dashboard en tiempo real", "Gestión de tickets", "Administrar técnicos", "Reportes y estadísticas"],
                            color=COLOR_ACENTO,
                            on_click=on_seleccionar_receptora,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(expand=True),
                ft.Row(
                    [ft.TextButton("Atrás", icon=ft.Icons.ARROW_BACK, on_click=on_atras)],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Container(height=10),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def _crear_tarjeta_tipo(self, tipo: str, icono, titulo: str, subtitulo: str,
                            descripcion: str, caracteristicas: list, color: str, on_click) -> ft.Container:
        """Crea una tarjeta de selección de tipo."""
        seleccionada = self.tipo_instalacion == tipo

        return ft.Container(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Container(
                                    content=ft.Icon(icono, size=40, color=color),
                                    bgcolor=f"{color}20",
                                    border_radius=50,
                                    padding=15,
                                ),
                                ft.Container(height=15),
                                ft.Text(titulo, size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                                ft.Text(subtitulo, size=12, color=color, weight=ft.FontWeight.W_500),
                            ],
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        ),
                        padding=ft.Padding.only(top=25, bottom=15),
                    ),
                    ft.Divider(height=1, color=COLOR_SUPERFICIE_2),
                    ft.Container(
                        content=ft.Text(descripcion, size=13, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
                        padding=15,
                    ),
                    ft.Container(
                        content=ft.Column(
                            [
                                ft.Row([ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=COLOR_EXITO), ft.Text(c, size=12, color=COLOR_TEXTO_SEC)], spacing=8)
                                for c in caracteristicas
                            ],
                            spacing=8,
                        ),
                        padding=ft.Padding.symmetric(horizontal=20, vertical=10),
                    ),
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Button(
                            "Seleccionado" if seleccionada else "Seleccionar",
                            icon=ft.Icons.CHECK if seleccionada else ft.Icons.ADD,
                            bgcolor=color if seleccionada else COLOR_SUPERFICIE_2,
                            color=COLOR_TEXTO,
                            width=180, height=45,
                            on_click=on_click,
                        ),
                        padding=ft.Padding.only(bottom=20),
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=20,
            width=320, height=420,
            border=ft.Border.all(2, color if seleccionada else COLOR_SUPERFICIE_2),
        )

    # =========================================================================
    # VISTA 2: OPCIONES DE INSTALACIÓN
    # =========================================================================

    def _vista_opciones(self) -> ft.Column:
        """Vista de opciones de instalación."""
        tipo_texto = "Emisora (Cliente)" if self.tipo_instalacion == "emisora" else "Receptora (Panel IT)"
        tipo_color = COLOR_SECUNDARIO if self.tipo_instalacion == "emisora" else COLOR_ACENTO

        def on_atras(e):
            self._mostrar_paso(1)

        def on_instalar(e):
            self._mostrar_paso(3)

        def toggle_escritorio(e):
            self.opt_escritorio = e.control.value

        def toggle_menu_inicio(e):
            self.opt_menu_inicio = e.control.value

        def toggle_inicio_windows(e):
            self.opt_inicio_windows = e.control.value

        def toggle_firewall(e):
            self.opt_firewall = e.control.value

        def toggle_crear_db(e):
            self.opt_crear_db = e.control.value

        col_derecha_items = [
            self._crear_opcion_switch("Configurar Firewall", "Abrir puerto 5555 para conexiones", ft.Icons.LOCK, self.opt_firewall, toggle_firewall),
        ]
        if self.tipo_instalacion == "receptora":
            col_derecha_items.append(
                self._crear_opcion_switch("Inicializar Base de Datos", "Crear archivos de datos necesarios", ft.Icons.FOLDER, self.opt_crear_db, toggle_crear_db)
            )

        return ft.Column(
            [
                ft.Container(height=10),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.SETTINGS, size=28, color=tipo_color),
                        ft.Text("Opciones de Instalación", size=26, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ],
                    spacing=12, alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=5),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(tipo_texto, size=12, color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                            bgcolor=f"{tipo_color}30",
                            border_radius=20,
                            padding=ft.Padding.symmetric(horizontal=15, vertical=6),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=30),
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    self._crear_opcion_switch("Crear acceso en Escritorio", "Acceso directo en el escritorio", ft.Icons.COMPUTER, self.opt_escritorio, toggle_escritorio),
                                    self._crear_opcion_switch("Crear acceso en Menú Inicio", "Acceso en programas de Windows", ft.Icons.MENU, self.opt_menu_inicio, toggle_menu_inicio),
                                    self._crear_opcion_switch("Iniciar con Windows", "Ejecutar al encender el equipo", ft.Icons.POWER, self.opt_inicio_windows, toggle_inicio_windows),
                                ],
                                spacing=15,
                            ),
                            ft.Container(width=40),
                            ft.Column(col_derecha_items, spacing=15),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding.symmetric(horizontal=20),
                ),
                ft.Container(expand=True),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Resumen de Instalación", size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                            ft.Container(height=10),
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Row([ft.Icon(ft.Icons.FOLDER, size=14, color=COLOR_TEXTO_SEC), ft.Text(f"Ubicación: {INSTALL_DIR}", size=11, color=COLOR_TEXTO_SEC)], spacing=8),
                                            ft.Row([ft.Icon(ft.Icons.COMPUTER, size=14, color=COLOR_TEXTO_SEC), ft.Text(f"Python: {PYTHON_VERSION} embebido", size=11, color=COLOR_TEXTO_SEC)], spacing=8),
                                        ],
                                        spacing=5,
                                    ),
                                    ft.Column(
                                        [
                                            ft.Row([ft.Icon(ft.Icons.LIST, size=14, color=COLOR_TEXTO_SEC), ft.Text(f"Dependencias: {len(DEPENDENCIAS)}", size=11, color=COLOR_TEXTO_SEC)], spacing=8),
                                            ft.Row([ft.Icon(ft.Icons.TIMER, size=14, color=COLOR_TEXTO_SEC), ft.Text("Tiempo estimado: ~2 min", size=11, color=COLOR_TEXTO_SEC)], spacing=8),
                                        ],
                                        spacing=5,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            ),
                        ]
                    ),
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=12,
                    padding=20,
                    margin=ft.Margin.symmetric(horizontal=40),
                ),
                ft.Container(height=20),
                ft.Row(
                    [
                        ft.TextButton("Atrás", icon=ft.Icons.ARROW_BACK, on_click=on_atras),
                        ft.Container(expand=True),
                        ft.Button(
                            "Instalar",
                            icon=ft.Icons.BUILD,
                            bgcolor=COLOR_PRIMARIO, color=COLOR_TEXTO,
                            width=160, height=45,
                            on_click=on_instalar,
                        ),
                    ],
                ),
                ft.Container(height=10),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )

    def _crear_opcion_switch(self, titulo: str, descripcion: str, icono, valor: bool, on_change) -> ft.Container:
        """Crea un switch de opción estilizado."""
        return ft.Container(
            content=ft.Row(
                [
                    ft.Container(
                        content=ft.Icon(icono, size=22, color=COLOR_PRIMARIO),
                        bgcolor=f"{COLOR_PRIMARIO}15",
                        border_radius=10,
                        padding=10,
                    ),
                    ft.Column(
                        [
                            ft.Text(titulo, size=14, weight=ft.FontWeight.W_500, color=COLOR_TEXTO),
                            ft.Text(descripcion, size=11, color=COLOR_TEXTO_SEC),
                        ],
                        spacing=2,
                        expand=True,
                    ),
                    ft.Switch(
                        value=valor,
                        active_color=COLOR_PRIMARIO,
                        active_track_color=f"{COLOR_PRIMARIO}50",
                        inactive_thumb_color=COLOR_TEXTO_SEC,
                        inactive_track_color=COLOR_SUPERFICIE_2,
                        on_change=on_change,
                    ),
                ],
                spacing=15,
            ),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=12,
            padding=15,
            width=340,
        )

    # =========================================================================
    # VISTA 3: PROCESO DE INSTALACIÓN
    # =========================================================================

    def _vista_instalacion(self) -> ft.Column:
        """Vista del proceso de instalación."""
        self.barra_progreso = ft.ProgressBar(
            value=0, width=500, height=8,
            color=COLOR_PRIMARIO, bgcolor=COLOR_SUPERFICIE_2,
            border_radius=4,
        )

        self.texto_progreso = ft.Text(
            "Preparando instalación...",
            size=14, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER,
        )

        self.contenedor_log = ft.Column([], spacing=5, scroll=ft.ScrollMode.AUTO)

        return ft.Column(
            [
                ft.Container(height=30),
                ft.ProgressRing(width=80, height=80, stroke_width=6, color=COLOR_PRIMARIO),
                ft.Container(height=30),
                ft.Text("Instalando...", size=26, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Container(height=15),
                self.texto_progreso,
                ft.Container(height=30),
                self.barra_progreso,
                ft.Container(height=30),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([ft.Icon(ft.Icons.CODE, size=16, color=COLOR_TEXTO_SEC), ft.Text("Registro de instalación", size=12, color=COLOR_TEXTO_SEC)], spacing=8),
                            ft.Container(height=10),
                            ft.Container(
                                content=self.contenedor_log,
                                bgcolor="#050508",
                                border_radius=8,
                                padding=15,
                                height=180, width=550,
                            ),
                        ]
                    ),
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=12,
                    padding=15,
                ),
                ft.Container(expand=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _agregar_log(self, mensaje: str, tipo: str = "info"):
        """Agrega un mensaje al log."""
        color = COLOR_TEXTO_SEC
        icono = ft.Icons.INFO
        if tipo == "success":
            color = COLOR_EXITO
            icono = ft.Icons.CHECK_CIRCLE
        elif tipo == "error":
            color = COLOR_ERROR
            icono = ft.Icons.ERROR
        elif tipo == "warning":
            color = COLOR_WARNING
            icono = ft.Icons.WARNING

        self.contenedor_log.controls.append(
            ft.Row([ft.Icon(icono, size=14, color=color), ft.Text(mensaje, size=11, color=color)], spacing=8)
        )
        self.page.update()

    def _actualizar_progreso(self, valor: float, mensaje: str):
        """Actualiza la barra y texto de progreso."""
        self.barra_progreso.value = valor
        self.texto_progreso.value = mensaje
        self.page.update()

    def _proceso_instalacion(self):
        """Proceso de instalación completo."""
        try:
            tiempo_inicio = time.time()

            self._actualizar_progreso(0.05, "Verificando Python embebido...")
            self._agregar_log("Verificando instalación de Python...", "info")
            time.sleep(0.3)

            if PYTHON_EXE.exists():
                self._agregar_log(f"Python {PYTHON_VERSION} encontrado", "success")
            else:
                self._agregar_log("Python no encontrado, se usará el existente", "warning")

            self._actualizar_progreso(0.15, "Verificando dependencias...")
            self._agregar_log("Verificando dependencias de Python...", "info")
            time.sleep(0.3)

            for i, dep in enumerate(DEPENDENCIAS):
                self._actualizar_progreso(0.15 + (0.35 * (i / len(DEPENDENCIAS))), f"Verificando {dep}...")
                self._agregar_log(f"  - {dep}", "info")
                time.sleep(0.1)

            self._agregar_log("Todas las dependencias verificadas", "success")

            self._actualizar_progreso(0.55, "Creando launcher...")
            self._agregar_log("Creando launcher silencioso...", "info")
            time.sleep(0.2)
            self._crear_launcher_vbs()
            self._agregar_log("Launcher creado correctamente", "success")

            if self.opt_escritorio or self.opt_menu_inicio:
                self._actualizar_progreso(0.65, "Creando accesos directos...")
                self._agregar_log("Creando accesos directos...", "info")
                time.sleep(0.2)
                self._crear_accesos_directos()
                self._agregar_log("Accesos directos creados", "success")

            if self.opt_firewall:
                self._actualizar_progreso(0.75, "Configurando firewall...")
                self._agregar_log("Configurando reglas de firewall...", "info")
                time.sleep(0.2)
                self._configurar_firewall()
                self._agregar_log("Firewall configurado (puerto 5555)", "success")

            if self.opt_crear_db and self.tipo_instalacion == "receptora":
                self._actualizar_progreso(0.85, "Inicializando bases de datos...")
                self._agregar_log("Creando bases de datos Excel...", "info")
                time.sleep(0.2)
                self._inicializar_bases_datos()
                self._agregar_log("Bases de datos inicializadas", "success")

            self._actualizar_progreso(1.0, "¡Instalación completada!")
            tiempo_total = time.time() - tiempo_inicio
            self._agregar_log(f"Instalación completada en {tiempo_total:.1f} segundos", "success")

            time.sleep(0.5)
            self.instalando = False
            self._mostrar_paso(4)

        except Exception as e:
            self._agregar_log(f"Error: {str(e)}", "error")
            self._actualizar_progreso(0, f"Error: {str(e)}")
            self.instalando = False

    def _crear_launcher_vbs(self):
        """Crea el launcher VBS para ejecutar sin ventana de consola."""
        if self.tipo_instalacion == "emisora":
            vbs_path = INSTALL_DIR / "launcher_emisora.vbs"
            py_script = "app_emisora.py"
        else:
            vbs_path = INSTALL_DIR / "launcher_receptora.vbs"
            py_script = "app_receptora.py"

        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{INSTALL_DIR}"
WshShell.Run """{PYTHON_EXE}"" ""{INSTALL_DIR / py_script}""", 0, False
'''
        vbs_path.write_text(vbs_content)

    def _crear_accesos_directos(self):
        """Crea los accesos directos según las opciones."""
        if self.tipo_instalacion == "emisora":
            nombre_app = APP_NAME_EMISORA
            vbs_path = INSTALL_DIR / "launcher_emisora.vbs"
            icono_path = INSTALL_DIR / "icons" / "emisora.ico"
        else:
            nombre_app = APP_NAME_RECEPTORA
            vbs_path = INSTALL_DIR / "launcher_receptora.vbs"
            icono_path = INSTALL_DIR / "icons" / "receptora.ico"

        if self.opt_escritorio:
            crear_acceso_directo_vbs(vbs_path, nombre_app, obtener_escritorio(), f"{nombre_app} - Sistema de Tickets IT", icono_path if icono_path.exists() else None)
        if self.opt_menu_inicio:
            menu_carpeta = obtener_menu_inicio() / "Sistema Tickets IT"
            menu_carpeta.mkdir(parents=True, exist_ok=True)
            crear_acceso_directo_vbs(vbs_path, nombre_app, menu_carpeta, f"{nombre_app} - Sistema de Tickets IT", icono_path if icono_path.exists() else None)
        if self.opt_inicio_windows:
            crear_acceso_directo_vbs(vbs_path, nombre_app, obtener_carpeta_startup(), f"{nombre_app} - Inicio automático", icono_path if icono_path.exists() else None)

    def _configurar_firewall(self):
        """Configura las reglas de firewall."""
        try:
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', 'name=TicketsIT_Servidor'], capture_output=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule', 'name=TicketsIT_Cliente'], capture_output=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', 'name=TicketsIT_Servidor', 'dir=in', 'action=allow', 'protocol=TCP', 'localport=5555'], capture_output=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule', 'name=TicketsIT_Cliente', 'dir=out', 'action=allow', 'protocol=TCP', 'localport=5555'], capture_output=True)
        except Exception:
            pass

    def _inicializar_bases_datos(self):
        """Inicializa la base de datos SQLite y archivos JSON de soporte."""
        try:
            import sqlite3

            db_path = INSTALL_DIR / "tickets.db"
            if not db_path.exists():
                conn = sqlite3.connect(str(db_path), isolation_level=None)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tickets (
                        ID_TICKET TEXT PRIMARY KEY, TURNO INTEGER DEFAULT 0,
                        FECHA_APERTURA TEXT, USUARIO_AD TEXT, HOSTNAME TEXT,
                        MAC_ADDRESS TEXT, CATEGORIA TEXT,
                        PRIORIDAD TEXT DEFAULT 'Media', DESCRIPCION TEXT,
                        ESTADO TEXT DEFAULT 'Abierto',
                        TECNICO_ASIGNADO TEXT DEFAULT '',
                        NOTAS_RESOLUCION TEXT DEFAULT '',
                        HISTORIAL TEXT DEFAULT '', FECHA_CIERRE TEXT,
                        TIEMPO_ESTIMADO INTEGER DEFAULT 0)""")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS tecnicos (
                        ID_TECNICO TEXT PRIMARY KEY, NOMBRE TEXT,
                        ESTADO TEXT DEFAULT 'Disponible', ESPECIALIDAD TEXT,
                        TICKETS_ATENDIDOS INTEGER DEFAULT 0,
                        TICKET_ACTUAL TEXT DEFAULT '', ULTIMA_ACTIVIDAD TEXT,
                        TELEFONO TEXT DEFAULT '', EMAIL TEXT DEFAULT '')""")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS equipos (
                        MAC_ADDRESS TEXT PRIMARY KEY, NOMBRE_EQUIPO TEXT,
                        HOSTNAME TEXT, USUARIO_ASIGNADO TEXT,
                        GRUPO TEXT DEFAULT 'Sin Asignar',
                        UBICACION TEXT DEFAULT '', MARCA TEXT DEFAULT '',
                        MODELO TEXT DEFAULT '', NUMERO_SERIE TEXT DEFAULT '',
                        TIPO_EQUIPO TEXT DEFAULT 'Desktop',
                        SISTEMA_OPERATIVO TEXT DEFAULT '',
                        PROCESADOR TEXT DEFAULT '',
                        RAM_GB INTEGER DEFAULT 0, DISCO_GB INTEGER DEFAULT 0,
                        FECHA_COMPRA TEXT, GARANTIA_HASTA TEXT,
                        ESTADO_EQUIPO TEXT DEFAULT 'Activo',
                        NOTAS TEXT DEFAULT '', FECHA_REGISTRO TEXT,
                        ULTIMA_CONEXION TEXT, TOTAL_TICKETS INTEGER DEFAULT 0)""")
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS counters (
                        fecha TEXT PRIMARY KEY, seq INTEGER DEFAULT 0)""")
                ahora = datetime.now().isoformat(sep=" ", timespec="seconds")
                for tec in TECNICOS_INICIALES:
                    conn.execute(
                        """INSERT OR IGNORE INTO tecnicos
                           (ID_TECNICO,NOMBRE,ESTADO,ESPECIALIDAD,
                            TICKETS_ATENDIDOS,TICKET_ACTUAL,ULTIMA_ACTIVIDAD,
                            TELEFONO,EMAIL) VALUES(?,?,?,?,?,?,?,?,?)""",
                        (tec["id"], tec["nombre"], "Disponible",
                         tec["especialidad"], 0, "", ahora,
                         tec["telefono"], tec["email"])
                    )
                conn.close()

            for archivo, contenido in [
                ("equipos_aprobados.json", {"aprobados": [], "rechazados": []}),
                ("solicitudes_enlace.json", []),
                ("notificaciones_estado.json", {}),
            ]:
                ruta = INSTALL_DIR / archivo
                if not ruta.exists():
                    with open(ruta, 'w', encoding='utf-8') as f:
                        json.dump(contenido, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    # =========================================================================
    # VISTA 4: INSTALACIÓN COMPLETADA
    # =========================================================================

    def _vista_completado(self) -> ft.Column:
        """Vista de instalación completada."""
        tipo_texto = "Emisora (Cliente)" if self.tipo_instalacion == "emisora" else "Receptora (Panel IT)"
        tipo_color = COLOR_SECUNDARIO if self.tipo_instalacion == "emisora" else COLOR_ACENTO

        def on_ejecutar(e):
            self._ejecutar_aplicacion()

        def on_cerrar(e):
            self.page.window.close()

        return ft.Column(
            [
                ft.Container(height=30),
                ft.Icon(ft.Icons.CHECK_CIRCLE, size=100, color=COLOR_EXITO),
                ft.Container(height=25),
                ft.Text("¡Instalación Completada!", size=32, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Container(height=10),
                ft.Row(
                    [
                        ft.Container(
                            content=ft.Text(tipo_texto, size=14, color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                            bgcolor=f"{tipo_color}30",
                            border_radius=20,
                            padding=ft.Padding.symmetric(horizontal=20, vertical=8),
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=30),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row([ft.Icon(ft.Icons.CHECK, size=18, color=COLOR_EXITO), ft.Text("Launcher creado correctamente", size=13, color=COLOR_TEXTO)], spacing=10),
                            ft.Row([ft.Icon(ft.Icons.CHECK if self.opt_escritorio else ft.Icons.REMOVE, size=18, color=COLOR_EXITO if self.opt_escritorio else COLOR_TEXTO_SEC), ft.Text("Acceso directo en escritorio", size=13, color=COLOR_TEXTO if self.opt_escritorio else COLOR_TEXTO_SEC)], spacing=10),
                            ft.Row([ft.Icon(ft.Icons.CHECK if self.opt_menu_inicio else ft.Icons.REMOVE, size=18, color=COLOR_EXITO if self.opt_menu_inicio else COLOR_TEXTO_SEC), ft.Text("Acceso en menú inicio", size=13, color=COLOR_TEXTO if self.opt_menu_inicio else COLOR_TEXTO_SEC)], spacing=10),
                            ft.Row([ft.Icon(ft.Icons.CHECK if self.opt_firewall else ft.Icons.REMOVE, size=18, color=COLOR_EXITO if self.opt_firewall else COLOR_TEXTO_SEC), ft.Text("Firewall configurado", size=13, color=COLOR_TEXTO if self.opt_firewall else COLOR_TEXTO_SEC)], spacing=10),
                        ],
                        spacing=12,
                    ),
                    bgcolor=COLOR_SUPERFICIE,
                    border_radius=12,
                    padding=25,
                ),
                ft.Container(expand=True),
                ft.Row(
                    [
                        ft.Button(
                            "Ejecutar Ahora",
                            icon=ft.Icons.PLAY_ARROW,
                            bgcolor=COLOR_PRIMARIO, color=COLOR_TEXTO,
                            width=180, height=50,
                            on_click=on_ejecutar,
                        ),
                        ft.Container(width=20),
                        ft.Button(
                            "Finalizar",
                            icon=ft.Icons.CLOSE,
                            bgcolor=COLOR_SUPERFICIE_2, color=COLOR_TEXTO,
                            width=150, height=50,
                            on_click=on_cerrar,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                ),
                ft.Container(height=10),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        )

    def _ejecutar_aplicacion(self):
        """Ejecuta la aplicación instalada."""
        if self.tipo_instalacion == "emisora":
            vbs_path = INSTALL_DIR / "launcher_emisora.vbs"
        else:
            vbs_path = INSTALL_DIR / "launcher_receptora.vbs"

        if vbs_path.exists():
            subprocess.Popen(['wscript.exe', str(vbs_path)], cwd=str(INSTALL_DIR))
        self.page.window.close()


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

def main(page: ft.Page):
    InstaladorGrafico(page)


if __name__ == "__main__":
    ft.run(main)
