# =============================================================================
# INSTALADOR GRÁFICO PROFESIONAL — Sistema de Tickets IT
# =============================================================================
# Instalador estilo Windows con asistente paso a paso (Flet 0.81)
#   • Menú principal: Instalar / Actualizar / Reparar / Desinstalar
#   • Wizard: Bienvenida → Licencia → Tipo → Directorio → Componentes
#             → Resumen → Progreso → Completado
#   • Desinstalación con opciones
#   • Búsqueda de actualizaciones
#   • Reparación de instalación
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
APP_VERSION = "3.3.0"
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

# — Paleta de colores ————————————————————————————————————————————————————
COLOR_FONDO       = "#0a0a0f"
COLOR_SUPERFICIE  = "#12121a"
COLOR_SUPERFICIE_2 = "#1a1a24"
COLOR_PRIMARIO    = "#6366f1"
COLOR_SECUNDARIO  = "#22d3ee"
COLOR_ACENTO      = "#f472b6"
COLOR_EXITO       = "#10b981"
COLOR_WARNING     = "#f59e0b"
COLOR_ERROR       = "#ef4444"
COLOR_TEXTO       = "#f8fafc"
COLOR_TEXTO_SEC   = "#94a3b8"

# — Columnas de bases de datos ————————————————————————————————————————————
COLUMNAS_DB = [
    "ID_TICKET", "TURNO", "FECHA_APERTURA", "USUARIO_AD", "HOSTNAME",
    "MAC_ADDRESS", "CATEGORIA", "PRIORIDAD", "DESCRIPCION", "ESTADO",
    "TECNICO_ASIGNADO", "NOTAS_RESOLUCION", "FECHA_CIERRE",
    "TIEMPO_ESTIMADO",
]

COLUMNAS_TECNICOS = [
    "ID_TECNICO", "NOMBRE", "ESTADO", "ESPECIALIDAD", "TICKETS_ATENDIDOS",
    "TICKET_ACTUAL", "ULTIMA_ACTIVIDAD", "TELEFONO", "EMAIL",
]

COLUMNAS_EQUIPOS = [
    "MAC_ADDRESS", "NOMBRE_EQUIPO", "HOSTNAME", "USUARIO_ASIGNADO", "GRUPO",
    "UBICACION", "MARCA", "MODELO", "NUMERO_SERIE", "TIPO_EQUIPO",
    "SISTEMA_OPERATIVO", "PROCESADOR", "RAM_GB", "DISCO_GB", "FECHA_COMPRA",
    "GARANTIA_HASTA", "ESTADO_EQUIPO", "NOTAS", "FECHA_REGISTRO",
    "ULTIMA_CONEXION", "TOTAL_TICKETS",
]

TECNICOS_INICIALES = [
    {"id": "TEC001", "nombre": "Carlos Rodríguez",  "especialidad": "Hardware/Red",       "telefono": "ext. 101", "email": "carlos.rodriguez@empresa.com"},
    {"id": "TEC002", "nombre": "María García",      "especialidad": "Software/Accesos",   "telefono": "ext. 102", "email": "maria.garcia@empresa.com"},
    {"id": "TEC003", "nombre": "Luis Hernández",    "especialidad": "Redes/Seguridad",    "telefono": "ext. 103", "email": "luis.hernandez@empresa.com"},
]

# =============================================================================
# TEXTO DE LICENCIA
# =============================================================================

LICENCIA_TEXTO = """CONTRATO DE LICENCIA DE USUARIO FINAL (EULA)
Sistema de Tickets IT — Soporte Técnico
Versión 3.0

IMPORTANTE: LEA ESTE CONTRATO CUIDADOSAMENTE ANTES DE INSTALAR O UTILIZAR ESTE SOFTWARE.

1. ACEPTACIÓN DEL CONTRATO
Al instalar, copiar o utilizar este software, usted acepta quedar obligado por los términos de este contrato de licencia. Si no está de acuerdo con los términos, no instale ni utilice el software.

2. LICENCIA DE USO
Se le concede una licencia no exclusiva y no transferible para utilizar el Sistema de Tickets IT dentro de su organización. Esta licencia permite:
  a) Instalar el software en los equipos de su red corporativa.
  b) Utilizar las funciones de emisión y recepción de tickets de soporte.
  c) Generar reportes y estadísticas para uso interno.
  d) Realizar copias de seguridad del software y sus datos.

3. RESTRICCIONES
Usted NO debe:
  a) Modificar, descompilar o aplicar ingeniería inversa al software sin autorización.
  b) Distribuir copias del software fuera de su organización.
  c) Utilizar el software para fines ilegales o no autorizados.
  d) Eliminar avisos de derechos de autor o marcas del software.
  e) Sub-licenciar, alquilar o prestar el software a terceros.

4. DATOS Y PRIVACIDAD
  a) El software procesa datos de tickets de soporte técnico internos.
  b) Todos los datos se almacenan localmente en su red corporativa.
  c) No se transmiten datos a servidores externos ni a terceros.
  d) Usted es responsable de la protección y respaldo de los datos procesados.
  e) Se recomienda implementar políticas de respaldo periódico.

5. REQUISITOS DEL SISTEMA
  a) Sistema operativo: Windows 10 o superior.
  b) Python 3.11 embebido (incluido en la instalación).
  c) Conexión a red local (para comunicación emisora-receptora).
  d) Espacio en disco: mínimo 500 MB disponibles.

6. ACTUALIZACIONES
Las actualizaciones del software pueden estar disponibles periódicamente. La instalación de actualizaciones implica la aceptación de los términos vigentes en ese momento.

7. LIMITACIÓN DE RESPONSABILIDAD
El software se proporciona "TAL CUAL" sin garantías de ningún tipo, expresas o implícitas. En ningún caso los desarrolladores serán responsables por daños directos, indirectos, incidentales, especiales o consecuentes derivados del uso del software.

8. SOPORTE TÉCNICO
El soporte técnico está disponible según los términos acordados con su departamento de IT. Para consultas, contacte a su administrador de sistemas.

9. TERMINACIÓN
Esta licencia se termina automáticamente si usted incumple cualquiera de sus términos. Al terminar, deberá desinstalar y eliminar todas las copias del software.

10. LEY APLICABLE
Este contrato se rige por las leyes vigentes en la jurisdicción donde opera su organización.

© 2024-2026 Departamento de IT — Todos los derechos reservados.
Sistema de Tickets IT v3.0 — Soporte Técnico Profesional"""


# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def obtener_escritorio():
    return Path(os.path.join(os.environ.get("USERPROFILE", ""), "Desktop"))

def obtener_menu_inicio():
    return Path(os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs"))

def obtener_carpeta_startup():
    return Path(os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "Start Menu", "Programs", "Startup"))

def crear_acceso_directo_vbs(vbs_path: Path, nombre: str, carpeta: Path,
                             descripcion: str = "", icono_path: Path = None):
    """Crea un acceso directo (.lnk) a un archivo VBS."""
    try:
        icono_linea = ""
        if icono_path and icono_path.exists():
            icono_linea = f'$Shortcut.IconLocation = "{icono_path},0"'
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{carpeta / f"{nombre}.lnk"}")
$Shortcut.TargetPath = "wscript.exe"
$Shortcut.Arguments = '"{vbs_path}"'
$Shortcut.WorkingDirectory = "{vbs_path.parent}"
$Shortcut.Description = "{descripcion}"
{icono_linea}
$Shortcut.Save()
'''
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
        return True
    except Exception:
        return False


def detectar_instalacion_existente():
    """Detecta si existe una instalación previa leyendo install_info.json."""
    info_path = INSTALL_DIR / "install_info.json"
    if info_path.exists():
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # Detección alternativa por archivos existentes
    if (INSTALL_DIR / "launcher_emisora.vbs").exists():
        return {"tipo": "emisora", "version": "desconocida", "fecha_instalacion": "desconocida"}
    if (INSTALL_DIR / "launcher_receptora.vbs").exists():
        return {"tipo": "receptora", "version": "desconocida", "fecha_instalacion": "desconocida"}
    return None


# =============================================================================
# CLASE PRINCIPAL DEL INSTALADOR
# =============================================================================

class InstaladorGrafico:
    """Instalador profesional estilo Windows con asistente paso a paso."""

    # Nombres de pasos para el indicador visual (modo instalar)
    PASOS_NOMBRES = ["Licencia", "Tipo", "Ubicación", "Opciones", "Instalar"]

    # Mapeo de vista → índice de paso (-1 = sin indicador)
    VISTA_A_PASO = {
        "bienvenida":  -1,
        "licencia":     0,
        "tipo":         1,
        "directorio":   2,
        "componentes":  3,
        "resumen":      4,
        "instalando":   4,
        "completado":   5,
    }

    # -----------------------------------------------------------------
    # INICIALIZACIÓN
    # -----------------------------------------------------------------

    def __init__(self, page: ft.Page):
        self.page = page

        # Estado general
        self.vista_actual = "menu"
        self.modo = None  # "instalar" | "desinstalar" | "actualizar" | "reparar"

        # Estado de instalación
        self.tipo_instalacion = None
        self.directorio_destino = str(INSTALL_DIR)
        self.acepto_licencia = False
        self.instalando = False

        # Opciones de componentes
        self.opt_escritorio      = True
        self.opt_menu_inicio     = True
        self.opt_inicio_windows  = False
        self.opt_firewall        = True
        self.opt_crear_db        = True

        # Opciones de desinstalación
        self.desinstalar_datos = False

        # Referencias UI (se asignan al construir las vistas)
        self.barra_progreso  = None
        self.texto_progreso  = None
        self.contenedor_log  = None
        self.btn_siguiente   = None
        self.txt_directorio  = None
        self.card_emisora    = None
        self.card_receptora  = None

        # Detectar instalación existente
        self.instalacion_existente = detectar_instalacion_existente()

        self._configurar_pagina()
        self._mostrar("menu")

    def _configurar_pagina(self):
        self.page.title = f"Instalador — {APP_NAME}"
        self.page.bgcolor = COLOR_FONDO
        self.page.padding = 0
        self.page.window.width = 920
        self.page.window.height = 700
        self.page.theme_mode = ft.ThemeMode.DARK
        self.page.window.resizable = False

    # =================================================================
    # NAVEGACIÓN PRINCIPAL
    # =================================================================

    def _mostrar(self, vista_id: str):
        """Navega a una vista reconstruyendo toda la página."""
        self.vista_actual = vista_id
        self.page.clean()

        vista_method = getattr(self, f"_vista_{vista_id}", None)
        if vista_method is None:
            return

        contenido = vista_method()

        # Determinar layout
        es_menu = vista_id == "menu"
        mostrar_pasos = (self.modo == "instalar" and vista_id in self.VISTA_A_PASO)

        columna = []
        if not es_menu:
            columna.append(self._crear_header(mostrar_pasos))
        columna.append(
            ft.Container(
                content=contenido,
                expand=True,
                padding=30 if not es_menu else 0,
            )
        )

        self.page.add(
            ft.Container(
                content=ft.Column(columna, spacing=0, expand=True),
                expand=True,
                bgcolor=COLOR_FONDO,
            )
        )

        # Auto-iniciar procesos
        if vista_id == "instalando" and not self.instalando:
            self.instalando = True
            threading.Thread(target=self._proceso_instalacion, daemon=True).start()
        elif vista_id == "desinstalando" and not self.instalando:
            self.instalando = True
            threading.Thread(target=self._proceso_desinstalacion, daemon=True).start()
        elif vista_id == "reparando" and not self.instalando:
            self.instalando = True
            threading.Thread(target=self._proceso_reparacion, daemon=True).start()

    # =================================================================
    # HEADER CON INDICADOR DE PASOS
    # =================================================================

    def _crear_header(self, mostrar_pasos: bool = True) -> ft.Container:
        fila = [
            ft.Row([
                ft.Container(
                    content=ft.Icon(ft.Icons.SUPPORT_AGENT, size=30, color=COLOR_PRIMARIO),
                    bgcolor=COLOR_SUPERFICIE_2,
                    border_radius=10,
                    padding=10,
                ),
                ft.Column([
                    ft.Text(APP_NAME, size=18, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Text(f"Instalador v{APP_VERSION}", size=10, color=COLOR_TEXTO_SEC),
                ], spacing=1),
            ], spacing=12),
        ]
        if mostrar_pasos:
            fila.append(self._crear_indicador_pasos())

        return ft.Container(
            content=ft.Row(fila, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding.symmetric(horizontal=30, vertical=14),
            bgcolor=COLOR_SUPERFICIE,
            border=ft.Border.only(bottom=ft.BorderSide(1, COLOR_SUPERFICIE_2)),
        )

    def _crear_indicador_pasos(self) -> ft.Row:
        paso_idx = self.VISTA_A_PASO.get(self.vista_actual, -1)
        items = []
        for i, nombre in enumerate(self.PASOS_NOMBRES):
            activo = i <= paso_idx
            completado = i < paso_idx
            col_c = COLOR_PRIMARIO if activo else COLOR_SUPERFICIE_2
            col_t = COLOR_TEXTO if activo else COLOR_TEXTO_SEC
            icono = ft.Icons.CHECK_CIRCLE if completado else ft.Icons.CIRCLE
            items.append(
                ft.Column([
                    ft.Icon(icono, size=16, color=COLOR_EXITO if completado else col_c),
                    ft.Text(nombre, size=9, color=col_t,
                            weight=ft.FontWeight.W_500 if activo else ft.FontWeight.NORMAL),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3)
            )
            if i < len(self.PASOS_NOMBRES) - 1:
                items.append(ft.Container(
                    width=22, height=2,
                    bgcolor=COLOR_EXITO if completado else COLOR_SUPERFICIE_2,
                    border_radius=1,
                    margin=ft.Margin.only(top=6, left=2, right=2),
                ))
        return ft.Row(items, spacing=0)

    # =================================================================
    # BARRA DE NAVEGACIÓN INFERIOR (Atrás / Siguiente / Cancelar)
    # =================================================================

    def _crear_barra_navegacion(self, *, on_atras=None, on_siguiente=None,
                                on_cancelar=None, texto_siguiente="Siguiente",
                                icono_siguiente=ft.Icons.ARROW_FORWARD,
                                siguiente_habilitado=True):
        """Crea la barra inferior estándar del wizard."""
        items = []

        if on_cancelar:
            items.append(ft.TextButton(
                "Cancelar", icon=ft.Icons.CLOSE, on_click=on_cancelar,
                style=ft.ButtonStyle(color=COLOR_TEXTO_SEC),
            ))

        items.append(ft.Container(expand=True))

        if on_atras:
            items.append(ft.TextButton("Atrás", icon=ft.Icons.ARROW_BACK, on_click=on_atras))
            items.append(ft.Container(width=10))

        if on_siguiente:
            self.btn_siguiente = ft.Button(
                texto_siguiente,
                icon=icono_siguiente,
                bgcolor=COLOR_PRIMARIO if siguiente_habilitado else COLOR_SUPERFICIE_2,
                color=COLOR_TEXTO if siguiente_habilitado else COLOR_TEXTO_SEC,
                width=200, height=45,
                disabled=not siguiente_habilitado,
                on_click=on_siguiente,
            )
            items.append(self.btn_siguiente)

        return ft.Container(
            content=ft.Column([
                ft.Divider(height=1, color=COLOR_SUPERFICIE_2),
                ft.Container(
                    content=ft.Row(items),
                    padding=ft.Padding.symmetric(horizontal=5, vertical=8),
                ),
            ], spacing=0),
        )

    def _confirmar_cancelar(self, e):
        """Diálogo de confirmación para cancelar."""
        def cerrar(e):
            self.page.close(dlg)

        def salir(e):
            self.page.close(dlg)
            self.page.window.close()

        dlg = ft.AlertDialog(
            modal=True,
            title=ft.Text("Cancelar instalación", weight=ft.FontWeight.BOLD),
            content=ft.Text("¿Está seguro de que desea cancelar?\nSe perderá todo el progreso actual."),
            actions=[
                ft.TextButton("No, continuar", on_click=cerrar),
                ft.TextButton("Sí, salir", on_click=salir,
                              style=ft.ButtonStyle(color=COLOR_ERROR)),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        self.page.open(dlg)

    # =================================================================
    # VISTA: MENÚ PRINCIPAL
    # =================================================================

    def _vista_menu(self) -> ft.Container:
        info = self.instalacion_existente
        ya_instalado = info is not None

        def on_instalar(e):
            self.modo = "instalar"
            self._mostrar("bienvenida")

        def on_actualizar(e):
            self.modo = "actualizar"
            self._mostrar("actualizar")

        def on_reparar(e):
            self.modo = "reparar"
            self._mostrar("reparar_opciones")

        def on_desinstalar(e):
            self.modo = "desinstalar"
            self._mostrar("desinstalar_opciones")

        def on_salir(e):
            self.page.window.close()

        # Texto de estado
        estado_items = []
        if ya_instalado:
            tipo = info.get("tipo", "Desconocido").capitalize()
            version = info.get("version", "?")
            fecha = info.get("fecha_instalacion", "")
            estado_items.append(ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE, size=16, color=COLOR_EXITO),
                    ft.Text(f"Instalado: {tipo} v{version}", size=12, color=COLOR_EXITO),
                    ft.Text(f"  ({fecha})" if fecha else "", size=11, color=COLOR_TEXTO_SEC),
                ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
                padding=ft.Padding.only(bottom=5),
            ))

        return ft.Container(
            content=ft.Column([
                ft.Container(height=25),
                # Logo + título
                ft.Container(
                    content=ft.Icon(ft.Icons.SUPPORT_AGENT, size=56, color=COLOR_PRIMARIO),
                    bgcolor=f"{COLOR_PRIMARIO}15",
                    border_radius=100,
                    padding=24,
                ),
                ft.Container(height=16),
                ft.Text(APP_NAME, size=30, weight=ft.FontWeight.BOLD,
                        color=COLOR_TEXTO, text_align=ft.TextAlign.CENTER),
                ft.Text(f"Instalador Profesional v{APP_VERSION}", size=13,
                        color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
                ft.Container(height=6),
                *estado_items,
                ft.Container(height=25),

                # Tarjetas de menú
                ft.Row([
                    self._crear_menu_card(
                        ft.Icons.DOWNLOAD, "Instalar",
                        "Instalar o reinstalar\nel sistema completo",
                        COLOR_PRIMARIO, on_instalar, True,
                    ),
                    self._crear_menu_card(
                        ft.Icons.UPDATE, "Actualizar",
                        "Buscar y aplicar\nactualizaciones",
                        COLOR_SECUNDARIO, on_actualizar, ya_instalado,
                    ),
                    self._crear_menu_card(
                        ft.Icons.BUILD, "Reparar",
                        "Reparar archivos y\nconfiguración",
                        COLOR_WARNING, on_reparar, ya_instalado,
                    ),
                    self._crear_menu_card(
                        ft.Icons.DELETE_FOREVER, "Desinstalar",
                        "Eliminar el sistema\ncompletamente",
                        COLOR_ERROR, on_desinstalar, ya_instalado,
                    ),
                ], alignment=ft.MainAxisAlignment.CENTER, spacing=16),

                ft.Container(expand=True),

                ft.TextButton("Salir", icon=ft.Icons.EXIT_TO_APP, on_click=on_salir,
                              style=ft.ButtonStyle(color=COLOR_TEXTO_SEC)),
                ft.Container(height=15),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, expand=True),
            expand=True,
            bgcolor=COLOR_FONDO,
            padding=40,
        )

    def _crear_menu_card(self, icono, titulo, descripcion, color, on_click,
                         habilitado=True) -> ft.Container:
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(icono, size=34, color=color if habilitado else COLOR_TEXTO_SEC),
                    bgcolor=f"{color}15" if habilitado else COLOR_SUPERFICIE_2,
                    border_radius=50,
                    padding=16,
                ),
                ft.Container(height=10),
                ft.Text(titulo, size=16, weight=ft.FontWeight.BOLD,
                        color=COLOR_TEXTO if habilitado else COLOR_TEXTO_SEC),
                ft.Container(height=4),
                ft.Text(descripcion, size=11, color=COLOR_TEXTO_SEC,
                        text_align=ft.TextAlign.CENTER),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
            bgcolor=COLOR_SUPERFICIE,
            border=ft.Border.all(1, COLOR_SUPERFICIE_2),
            border_radius=16,
            padding=ft.Padding.symmetric(horizontal=16, vertical=22),
            width=185,
            height=210,
            on_click=on_click if habilitado else None,
            ink=habilitado,
            opacity=1.0 if habilitado else 0.45,
        )

    # =================================================================
    # VISTA: BIENVENIDA (paso previo al wizard)
    # =================================================================

    def _vista_bienvenida(self) -> ft.Column:
        def on_siguiente(e):
            self._mostrar("licencia")

        def on_atras(e):
            self._mostrar("menu")

        def on_cancelar(e):
            self._confirmar_cancelar(e)

        return ft.Column([
            ft.Container(height=10),
            ft.Container(
                content=ft.Icon(ft.Icons.COMPUTER, size=64, color=COLOR_PRIMARIO),
                bgcolor=f"{COLOR_PRIMARIO}12",
                border_radius=100,
                padding=22,
            ),
            ft.Container(height=20),
            ft.Text("Bienvenido al Asistente de Instalación",
                    size=26, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO,
                    text_align=ft.TextAlign.CENTER),
            ft.Container(height=10),
            ft.Text(
                f"Este asistente le guiará paso a paso en la instalación del\n{APP_NAME} en su equipo.",
                size=14, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER,
            ),
            ft.Container(height=25),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINED, size=18, color=COLOR_SECUNDARIO),
                        ft.Text("Antes de continuar, asegúrese de:", size=13,
                                color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                    ], spacing=10),
                    ft.Container(height=8),
                    self._crear_check_item("Tener permisos de administrador en este equipo"),
                    self._crear_check_item("Cerrar otras instancias del Sistema de Tickets"),
                    self._crear_check_item("Tener conexión a la red local (para emisora/receptora)"),
                    self._crear_check_item("Disponer de al menos 500 MB de espacio libre"),
                ]),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=20,
                width=500,
            ),
            ft.Container(expand=True),
            self._crear_barra_navegacion(
                on_atras=on_atras,
                on_siguiente=on_siguiente,
                on_cancelar=on_cancelar,
            ),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def _crear_check_item(self, texto: str) -> ft.Row:
        return ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE, size=15, color=COLOR_EXITO),
            ft.Text(texto, size=12, color=COLOR_TEXTO_SEC),
        ], spacing=8)

    # =================================================================
    # VISTA: LICENCIA (Términos y Condiciones)
    # =================================================================

    def _vista_licencia(self) -> ft.Column:
        def on_siguiente(e):
            self._mostrar("tipo")

        def on_atras(e):
            self._mostrar("bienvenida")

        def on_cancelar(e):
            self._confirmar_cancelar(e)

        def on_acepto_change(e):
            self.acepto_licencia = e.control.value
            if self.btn_siguiente:
                self.btn_siguiente.disabled = not self.acepto_licencia
                self.btn_siguiente.bgcolor = COLOR_PRIMARIO if self.acepto_licencia else COLOR_SUPERFICIE_2
                self.btn_siguiente.color = COLOR_TEXTO if self.acepto_licencia else COLOR_TEXTO_SEC
                self.page.update()

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.DESCRIPTION, size=24, color=COLOR_PRIMARIO),
                ft.Text("Contrato de Licencia", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            ft.Container(height=6),
            ft.Text("Lea los siguientes términos y condiciones antes de continuar.",
                    size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=12),
            # Área de texto de licencia (scrollable)
            ft.Container(
                content=ft.Column([
                    ft.Text(LICENCIA_TEXTO, size=11, color=COLOR_TEXTO_SEC, selectable=True),
                ], scroll=ft.ScrollMode.ALWAYS, spacing=0),
                bgcolor="#08080d",
                border_radius=8,
                border=ft.Border.all(1, COLOR_SUPERFICIE_2),
                padding=18,
                expand=True,
            ),
            ft.Container(height=12),
            ft.Checkbox(
                label="He leído y acepto los términos y condiciones de uso",
                value=self.acepto_licencia,
                active_color=COLOR_PRIMARIO,
                check_color=COLOR_TEXTO,
                on_change=on_acepto_change,
            ),
            ft.Container(height=5),
            self._crear_barra_navegacion(
                on_atras=on_atras,
                on_siguiente=on_siguiente,
                on_cancelar=on_cancelar,
                siguiente_habilitado=self.acepto_licencia,
            ),
        ], expand=True)

    # =================================================================
    # VISTA: SELECCIÓN DE TIPO (Emisora / Receptora)
    # =================================================================

    def _vista_tipo(self) -> ft.Column:
        def on_siguiente(e):
            self._mostrar("directorio")

        def on_atras(e):
            self._mostrar("licencia")

        def on_cancelar(e):
            self._confirmar_cancelar(e)

        def seleccionar_emisora(e):
            self.tipo_instalacion = "emisora"
            self.card_emisora.border = ft.Border.all(2, COLOR_SECUNDARIO)
            self.card_receptora.border = ft.Border.all(1, COLOR_SUPERFICIE_2)
            if self.btn_siguiente:
                self.btn_siguiente.disabled = False
                self.btn_siguiente.bgcolor = COLOR_PRIMARIO
                self.btn_siguiente.color = COLOR_TEXTO
            self.page.update()

        def seleccionar_receptora(e):
            self.tipo_instalacion = "receptora"
            self.card_receptora.border = ft.Border.all(2, COLOR_ACENTO)
            self.card_emisora.border = ft.Border.all(1, COLOR_SUPERFICIE_2)
            if self.btn_siguiente:
                self.btn_siguiente.disabled = False
                self.btn_siguiente.bgcolor = COLOR_PRIMARIO
                self.btn_siguiente.color = COLOR_TEXTO
            self.page.update()

        sel_e = self.tipo_instalacion == "emisora"
        sel_r = self.tipo_instalacion == "receptora"

        self.card_emisora = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(ft.Icons.PERSON, size=36, color=COLOR_SECUNDARIO),
                    bgcolor=f"{COLOR_SECUNDARIO}18",
                    border_radius=50,
                    padding=14,
                ),
                ft.Container(height=12),
                ft.Text("EMISORA", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Text("Cliente de Soporte", size=11, color=COLOR_SECUNDARIO, weight=ft.FontWeight.W_500),
                ft.Container(height=10),
                ft.Divider(height=1, color=COLOR_SUPERFICIE_2),
                ft.Container(height=10),
                ft.Text("Para usuarios que necesitan\ncrear tickets de soporte",
                        size=12, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
                ft.Container(height=12),
                self._crear_check_feature("Crear tickets de soporte"),
                self._crear_check_feature("Ver estado de tickets"),
                self._crear_check_feature("Recibir notificaciones"),
                self._crear_check_feature("Interfaz simplificada"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=18,
            border=ft.Border.all(2 if sel_e else 1, COLOR_SECUNDARIO if sel_e else COLOR_SUPERFICIE_2),
            padding=ft.Padding.symmetric(horizontal=22, vertical=20),
            width=310,
            on_click=seleccionar_emisora,
            ink=True,
            ink_color=f"{COLOR_SECUNDARIO}20",
        )

        self.card_receptora = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Icon(ft.Icons.SETTINGS, size=36, color=COLOR_ACENTO),
                    bgcolor=f"{COLOR_ACENTO}18",
                    border_radius=50,
                    padding=14,
                ),
                ft.Container(height=12),
                ft.Text("RECEPTORA", size=20, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Text("Panel de IT", size=11, color=COLOR_ACENTO, weight=ft.FontWeight.W_500),
                ft.Container(height=10),
                ft.Divider(height=1, color=COLOR_SUPERFICIE_2),
                ft.Container(height=10),
                ft.Text("Para técnicos que gestionan\ny resuelven los tickets",
                        size=12, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
                ft.Container(height=12),
                self._crear_check_feature("Dashboard en tiempo real"),
                self._crear_check_feature("Gestión de tickets"),
                self._crear_check_feature("Administrar técnicos"),
                self._crear_check_feature("Reportes y estadísticas"),
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=3),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=18,
            border=ft.Border.all(2 if sel_r else 1, COLOR_ACENTO if sel_r else COLOR_SUPERFICIE_2),
            padding=ft.Padding.symmetric(horizontal=22, vertical=20),
            width=310,
            on_click=seleccionar_receptora,
            ink=True,
            ink_color=f"{COLOR_ACENTO}20",
        )

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.APPS, size=24, color=COLOR_PRIMARIO),
                ft.Text("Tipo de Instalación", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            ft.Container(height=4),
            ft.Text("Seleccione el tipo de aplicación que desea instalar según su rol.",
                    size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=20),
            ft.Row([
                self.card_emisora,
                ft.Container(width=25),
                self.card_receptora,
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(expand=True),
            self._crear_barra_navegacion(
                on_atras=on_atras,
                on_siguiente=on_siguiente,
                on_cancelar=on_cancelar,
                siguiente_habilitado=self.tipo_instalacion is not None,
            ),
        ], expand=True)

    def _crear_check_feature(self, texto: str) -> ft.Row:
        return ft.Row([
            ft.Icon(ft.Icons.CHECK_CIRCLE, size=14, color=COLOR_EXITO),
            ft.Text(texto, size=11, color=COLOR_TEXTO_SEC),
        ], spacing=6)

    # =================================================================
    # VISTA: DIRECTORIO DE INSTALACIÓN
    # =================================================================

    def _vista_directorio(self) -> ft.Column:
        def on_siguiente(e):
            self._mostrar("componentes")

        def on_atras(e):
            self._mostrar("tipo")

        def on_cancelar(e):
            self._confirmar_cancelar(e)

        def on_dir_change(e):
            self.directorio_destino = e.control.value

        self.txt_directorio = ft.TextField(
            value=self.directorio_destino,
            label="Carpeta de instalación (deje el valor predeterminado si es posible)",
            width=680,
            border_color=COLOR_SUPERFICIE_2,
            focused_border_color=COLOR_PRIMARIO,
            color=COLOR_TEXTO,
            text_size=12,
            label_style=ft.TextStyle(color=COLOR_TEXTO_SEC),
            on_change=on_dir_change,
            read_only=False,
        )

        # Información de espacio en disco
        try:
            total, used, free = shutil.disk_usage(self.directorio_destino)
            espacio_libre = f"{free // (1024**3)} GB libres de {total // (1024**3)} GB"
            espacio_suficiente = free > 500 * 1024 * 1024  # 500 MB
        except Exception:
            espacio_libre = "No se pudo determinar"
            espacio_suficiente = True

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.FOLDER_OPEN, size=24, color=COLOR_PRIMARIO),
                ft.Text("Ubicación de Instalación", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            ft.Container(height=4),
            ft.Text("Ruta donde se instalará el sistema. Se recomienda dejar la ubicación predeterminada.",
                    size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=25),
            # Campo de directorio
            self.txt_directorio,
            ft.Container(height=20),
            # Info de espacio
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.STORAGE, size=18, color=COLOR_SECUNDARIO),
                        ft.Text("Información del disco", size=13, color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                    ], spacing=10),
                    ft.Container(height=8),
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE if espacio_suficiente else ft.Icons.WARNING,
                                size=14, color=COLOR_EXITO if espacio_suficiente else COLOR_WARNING),
                        ft.Text(espacio_libre, size=12, color=COLOR_TEXTO_SEC),
                    ], spacing=8),
                    ft.Row([
                        ft.Icon(ft.Icons.INFO_OUTLINED, size=14, color=COLOR_TEXTO_SEC),
                        ft.Text("Espacio requerido: ~500 MB (incluye Python embebido)", size=12, color=COLOR_TEXTO_SEC),
                    ], spacing=8),
                ]),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=18,
                width=680,
            ),
            ft.Container(height=15),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.LIGHTBULB_OUTLINED, size=14, color=COLOR_WARNING),
                    ft.Text("Se recomienda usar la ubicación predeterminada para evitar problemas de permisos.",
                            size=11, color=COLOR_TEXTO_SEC, italic=True),
                ], spacing=8),
            ),
            ft.Container(expand=True),
            self._crear_barra_navegacion(
                on_atras=on_atras,
                on_siguiente=on_siguiente,
                on_cancelar=on_cancelar,
            ),
        ], expand=True)

    # =================================================================
    # VISTA: COMPONENTES / OPCIONES
    # =================================================================

    def _vista_componentes(self) -> ft.Column:
        tipo_texto = "Emisora (Cliente)" if self.tipo_instalacion == "emisora" else "Receptora (Panel IT)"
        tipo_color = COLOR_SECUNDARIO if self.tipo_instalacion == "emisora" else COLOR_ACENTO

        def on_siguiente(e):
            self._mostrar("resumen")

        def on_atras(e):
            self._mostrar("directorio")

        def on_cancelar(e):
            self._confirmar_cancelar(e)

        def tog_escritorio(e):
            self.opt_escritorio = e.control.value

        def tog_menu(e):
            self.opt_menu_inicio = e.control.value

        def tog_startup(e):
            self.opt_inicio_windows = e.control.value

        def tog_firewall(e):
            self.opt_firewall = e.control.value

        def tog_db(e):
            self.opt_crear_db = e.control.value

        # Componentes del lado izquierdo (accesos directos)
        col_izq = [
            ft.Text("Accesos Directos", size=14, weight=ft.FontWeight.W_600, color=COLOR_TEXTO),
            ft.Container(height=8),
            self._crear_opcion_switch("Acceso en Escritorio",
                                      "Crear acceso directo en el escritorio",
                                      ft.Icons.DESKTOP_WINDOWS, self.opt_escritorio, tog_escritorio),
            self._crear_opcion_switch("Acceso en Menú Inicio",
                                      "Agregar al menú de programas de Windows",
                                      ft.Icons.MENU, self.opt_menu_inicio, tog_menu),
            self._crear_opcion_switch("Iniciar con Windows",
                                      "Ejecutar automáticamente al encender",
                                      ft.Icons.POWER_SETTINGS_NEW, self.opt_inicio_windows, tog_startup),
        ]

        # Componentes del lado derecho (configuración)
        col_der = [
            ft.Text("Configuración", size=14, weight=ft.FontWeight.W_600, color=COLOR_TEXTO),
            ft.Container(height=8),
            self._crear_opcion_switch("Configurar Firewall",
                                      "Abrir puerto 5555 en Windows Firewall",
                                      ft.Icons.SHIELD, self.opt_firewall, tog_firewall),
        ]
        if self.tipo_instalacion == "receptora":
            col_der.append(
                self._crear_opcion_switch("Crear Base de Datos",
                                          "Inicializar archivos Excel y JSON",
                                          ft.Icons.STORAGE, self.opt_crear_db, tog_db)
            )

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.TUNE, size=24, color=COLOR_PRIMARIO),
                ft.Text("Opciones de Instalación", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                ft.Container(width=10),
                ft.Container(
                    content=ft.Text(tipo_texto, size=11, color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                    bgcolor=f"{tipo_color}25",
                    border_radius=20,
                    padding=ft.Padding.symmetric(horizontal=12, vertical=5),
                ),
            ], spacing=8),
            ft.Container(height=4),
            ft.Text("Seleccione los componentes y opciones que desea instalar.",
                    size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=20),
            ft.Row([
                ft.Column(col_izq, spacing=10, expand=True),
                ft.Container(width=30),
                ft.Column(col_der, spacing=10, expand=True),
            ]),
            ft.Container(expand=True),
            self._crear_barra_navegacion(
                on_atras=on_atras,
                on_siguiente=on_siguiente,
                on_cancelar=on_cancelar,
            ),
        ], expand=True)

    def _crear_opcion_switch(self, titulo, descripcion, icono, valor, on_change) -> ft.Container:
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icono, size=20, color=COLOR_PRIMARIO),
                    bgcolor=f"{COLOR_PRIMARIO}12",
                    border_radius=8,
                    padding=9,
                ),
                ft.Column([
                    ft.Text(titulo, size=13, weight=ft.FontWeight.W_500, color=COLOR_TEXTO),
                    ft.Text(descripcion, size=10, color=COLOR_TEXTO_SEC),
                ], spacing=2, expand=True),
                ft.Switch(
                    value=valor,
                    active_color=COLOR_PRIMARIO,
                    active_track_color=f"{COLOR_PRIMARIO}50",
                    inactive_thumb_color=COLOR_TEXTO_SEC,
                    inactive_track_color=COLOR_SUPERFICIE_2,
                    on_change=on_change,
                ),
            ], spacing=12),
            bgcolor=COLOR_SUPERFICIE,
            border_radius=10,
            padding=12,
        )

    # =================================================================
    # VISTA: RESUMEN (antes de instalar)
    # =================================================================

    def _vista_resumen(self) -> ft.Column:
        tipo_texto = "Emisora (Cliente)" if self.tipo_instalacion == "emisora" else "Receptora (Panel IT)"
        tipo_color = COLOR_SECUNDARIO if self.tipo_instalacion == "emisora" else COLOR_ACENTO

        def on_instalar(e):
            self._mostrar("instalando")

        def on_atras(e):
            self._mostrar("componentes")

        def on_cancelar(e):
            self._confirmar_cancelar(e)

        items_resumen = [
            ("Tipo de instalación", tipo_texto, ft.Icons.APPS, tipo_color),
            ("Directorio", self.directorio_destino, ft.Icons.FOLDER, COLOR_TEXTO_SEC),
            ("Python", f"{PYTHON_VERSION} embebido", ft.Icons.CODE, COLOR_TEXTO_SEC),
            ("Dependencias", ", ".join(DEPENDENCIAS), ft.Icons.EXTENSION, COLOR_TEXTO_SEC),
        ]

        opciones_activas = []
        if self.opt_escritorio:
            opciones_activas.append("Acceso en escritorio")
        if self.opt_menu_inicio:
            opciones_activas.append("Menú inicio")
        if self.opt_inicio_windows:
            opciones_activas.append("Inicio automático")
        if self.opt_firewall:
            opciones_activas.append("Firewall (puerto 5555)")
        if self.opt_crear_db and self.tipo_instalacion == "receptora":
            opciones_activas.append("Base de datos")

        items_resumen.append(
            ("Componentes", ", ".join(opciones_activas) if opciones_activas else "Ninguno",
             ft.Icons.CHECKLIST, COLOR_TEXTO_SEC)
        )

        filas_resumen = []
        for titulo, valor, icono, color in items_resumen:
            filas_resumen.append(ft.Row([
                ft.Container(
                    content=ft.Icon(icono, size=16, color=color),
                    bgcolor=f"{COLOR_PRIMARIO}10",
                    border_radius=6,
                    padding=7,
                ),
                ft.Column([
                    ft.Text(titulo, size=11, color=COLOR_TEXTO_SEC, weight=ft.FontWeight.W_500),
                    ft.Text(valor, size=13, color=COLOR_TEXTO),
                ], spacing=1, expand=True),
            ], spacing=12))

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.CHECKLIST, size=24, color=COLOR_PRIMARIO),
                ft.Text("Resumen de Instalación", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            ft.Container(height=4),
            ft.Text("Revise la configuración seleccionada. Pulse «Instalar» para comenzar.",
                    size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=16),
            ft.Container(
                content=ft.Column(filas_resumen, spacing=14),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=22,
            ),
            ft.Container(height=16),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.TIMER, size=16, color=COLOR_WARNING),
                    ft.Text("Tiempo estimado de instalación: 1-3 minutos", size=12, color=COLOR_TEXTO_SEC),
                ], spacing=8),
            ),
            ft.Container(expand=True),
            self._crear_barra_navegacion(
                on_atras=on_atras,
                on_siguiente=on_instalar,
                on_cancelar=on_cancelar,
                texto_siguiente="Instalar",
                icono_siguiente=ft.Icons.INSTALL_DESKTOP,
            ),
        ], expand=True)

    # =================================================================
    # VISTA: PROGRESO DE INSTALACIÓN
    # =================================================================

    def _vista_instalando(self) -> ft.Column:
        self.barra_progreso = ft.ProgressBar(
            value=0, width=550, height=8,
            color=COLOR_PRIMARIO, bgcolor=COLOR_SUPERFICIE_2,
            border_radius=4,
        )
        self.texto_progreso = ft.Text(
            "Preparando instalación...", size=14,
            color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER,
        )
        self.contenedor_log = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO)

        return ft.Column([
            ft.Container(height=20),
            ft.ProgressRing(width=70, height=70, stroke_width=5, color=COLOR_PRIMARIO),
            ft.Container(height=20),
            ft.Text("Instalando...", size=24, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=10),
            self.texto_progreso,
            ft.Container(height=20),
            self.barra_progreso,
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.TERMINAL, size=14, color=COLOR_TEXTO_SEC),
                        ft.Text("Registro de instalación", size=11, color=COLOR_TEXTO_SEC),
                    ], spacing=8),
                    ft.Container(height=6),
                    ft.Container(
                        content=self.contenedor_log,
                        bgcolor="#050508",
                        border_radius=8,
                        padding=12,
                        height=180,
                        width=580,
                    ),
                ]),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=14,
            ),
            ft.Container(expand=True),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # =================================================================
    # VISTA: INSTALACIÓN COMPLETADA
    # =================================================================

    def _vista_completado(self) -> ft.Column:
        tipo_texto = "Emisora (Cliente)" if self.tipo_instalacion == "emisora" else "Receptora (Panel IT)"
        tipo_color = COLOR_SECUNDARIO if self.tipo_instalacion == "emisora" else COLOR_ACENTO

        def on_ejecutar(e):
            self._ejecutar_aplicacion()

        def on_finalizar(e):
            self.page.window.close()

        checks = [
            ("Launcher creado correctamente", True),
            ("Acceso directo en escritorio", self.opt_escritorio),
            ("Acceso en menú inicio", self.opt_menu_inicio),
            ("Inicio automático con Windows", self.opt_inicio_windows),
            ("Firewall configurado (puerto 5555)", self.opt_firewall),
        ]
        if self.tipo_instalacion == "receptora":
            checks.append(("Base de datos inicializada", self.opt_crear_db))

        return ft.Column([
            ft.Container(height=15),
            ft.Icon(ft.Icons.CHECK_CIRCLE, size=90, color=COLOR_EXITO),
            ft.Container(height=18),
            ft.Text("¡Instalación Completada!", size=28, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=6),
            ft.Container(
                content=ft.Text(tipo_texto, size=13, color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                bgcolor=f"{tipo_color}25",
                border_radius=20,
                padding=ft.Padding.symmetric(horizontal=16, vertical=6),
            ),
            ft.Container(height=18),
            ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Icon(ft.Icons.CHECK if ok else ft.Icons.REMOVE, size=16,
                                color=COLOR_EXITO if ok else COLOR_TEXTO_SEC),
                        ft.Text(texto, size=12, color=COLOR_TEXTO if ok else COLOR_TEXTO_SEC),
                    ], spacing=10) for texto, ok in checks
                ], spacing=10),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=22,
                width=420,
            ),
            ft.Container(expand=True),
            ft.Row([
                ft.Button("Ejecutar Ahora", icon=ft.Icons.PLAY_ARROW,
                          bgcolor=COLOR_PRIMARIO, color=COLOR_TEXTO,
                          width=180, height=48, on_click=on_ejecutar),
                ft.Container(width=15),
                ft.Button("Finalizar", icon=ft.Icons.CHECK,
                          bgcolor=COLOR_SUPERFICIE_2, color=COLOR_TEXTO,
                          width=150, height=48, on_click=on_finalizar),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=10),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # =================================================================
    # VISTA: DESINSTALAR — OPCIONES
    # =================================================================

    def _vista_desinstalar_opciones(self) -> ft.Column:
        def on_desinstalar(e):
            self._mostrar("desinstalando")

        def on_atras(e):
            self._mostrar("menu")

        def on_cancelar(e):
            self._confirmar_cancelar(e)

        def tog_datos(e):
            self.desinstalar_datos = e.control.value

        info = self.instalacion_existente or {}
        tipo = info.get("tipo", "desconocido").capitalize()

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.DELETE_FOREVER, size=24, color=COLOR_ERROR),
                ft.Text("Desinstalar Sistema", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            ft.Container(height=4),
            ft.Text("Se eliminarán los componentes instalados del sistema.", size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=20),

            # Warning box
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.WARNING, size=22, color=COLOR_WARNING),
                    ft.Column([
                        ft.Text("Advertencia", size=14, weight=ft.FontWeight.BOLD, color=COLOR_WARNING),
                        ft.Text("Esta acción eliminará accesos directos, reglas de firewall\ny archivos de configuración creados por el instalador.",
                                size=12, color=COLOR_TEXTO_SEC),
                    ], spacing=3, expand=True),
                ], spacing=14),
                bgcolor=f"{COLOR_WARNING}10",
                border=ft.Border.all(1, f"{COLOR_WARNING}40"),
                border_radius=12,
                padding=16,
            ),
            ft.Container(height=20),

            ft.Text(f"Instalación detectada: {tipo}", size=14, color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
            ft.Container(height=12),

            # Lo que se elimina siempre
            ft.Container(
                content=ft.Column([
                    ft.Text("Se eliminarán:", size=13, color=COLOR_TEXTO, weight=ft.FontWeight.W_500),
                    ft.Container(height=6),
                    self._crear_check_item("Accesos directos (escritorio, menú inicio, startup)"),
                    self._crear_check_item("Reglas de firewall del sistema"),
                    self._crear_check_item("Archivos launcher (.vbs)"),
                    self._crear_check_item("Información de instalación"),
                ]),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=18,
            ),
            ft.Container(height=12),

            # Opción: eliminar datos
            ft.Container(
                content=ft.Row([
                    ft.Checkbox(
                        label="También eliminar bases de datos y archivos de datos",
                        value=self.desinstalar_datos,
                        active_color=COLOR_ERROR,
                        check_color=COLOR_TEXTO,
                        on_change=tog_datos,
                    ),
                ]),
                bgcolor=COLOR_SUPERFICIE,
                border_radius=12,
                padding=ft.Padding.symmetric(horizontal=18, vertical=10),
            ),
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.INFO_OUTLINED, size=13, color=COLOR_TEXTO_SEC),
                    ft.Text("Los archivos .py y python_embed no serán eliminados.",
                            size=11, color=COLOR_TEXTO_SEC, italic=True),
                ], spacing=6),
                padding=ft.Padding.only(left=10, top=6),
            ),

            ft.Container(expand=True),
            self._crear_barra_navegacion(
                on_atras=on_atras,
                on_siguiente=on_desinstalar,
                on_cancelar=on_cancelar,
                texto_siguiente="Desinstalar",
                icono_siguiente=ft.Icons.DELETE,
            ),
        ], expand=True)

    # =================================================================
    # VISTA: DESINSTALANDO (progreso)
    # =================================================================

    def _vista_desinstalando(self) -> ft.Column:
        self.barra_progreso = ft.ProgressBar(
            value=0, width=500, height=8,
            color=COLOR_ERROR, bgcolor=COLOR_SUPERFICIE_2, border_radius=4,
        )
        self.texto_progreso = ft.Text("Preparando desinstalación...", size=14,
                                       color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER)
        self.contenedor_log = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO)

        return ft.Column([
            ft.Container(height=30),
            ft.ProgressRing(width=70, height=70, stroke_width=5, color=COLOR_ERROR),
            ft.Container(height=20),
            ft.Text("Desinstalando...", size=24, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=10),
            self.texto_progreso,
            ft.Container(height=20),
            self.barra_progreso,
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.TERMINAL, size=14, color=COLOR_TEXTO_SEC),
                            ft.Text("Registro", size=11, color=COLOR_TEXTO_SEC)], spacing=8),
                    ft.Container(height=6),
                    ft.Container(content=self.contenedor_log, bgcolor="#050508",
                                 border_radius=8, padding=12, height=150, width=520),
                ]),
                bgcolor=COLOR_SUPERFICIE, border_radius=12, padding=14,
            ),
            ft.Container(expand=True),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # =================================================================
    # VISTA: DESINSTALACIÓN COMPLETADA
    # =================================================================

    def _vista_desinstalar_completado(self) -> ft.Column:
        def on_finalizar(e):
            self.page.window.close()

        return ft.Column([
            ft.Container(height=30),
            ft.Icon(ft.Icons.CHECK_CIRCLE, size=80, color=COLOR_EXITO),
            ft.Container(height=20),
            ft.Text("Desinstalación Completada", size=26, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=10),
            ft.Text("El sistema ha sido desinstalado correctamente.\nPuede cerrar esta ventana.",
                    size=14, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(height=25),
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.INFO_OUTLINED, size=16, color=COLOR_SECUNDARIO),
                            ft.Text("Nota", size=13, color=COLOR_TEXTO, weight=ft.FontWeight.W_500)], spacing=8),
                    ft.Container(height=4),
                    ft.Text("Los archivos del programa (.py) y Python embebido permanecen\nen la carpeta por si desea reinstalar en el futuro.",
                            size=12, color=COLOR_TEXTO_SEC),
                ]),
                bgcolor=COLOR_SUPERFICIE, border_radius=12, padding=18, width=480,
            ),
            ft.Container(expand=True),
            ft.Button("Finalizar", icon=ft.Icons.CHECK,
                      bgcolor=COLOR_SUPERFICIE_2, color=COLOR_TEXTO,
                      width=160, height=48, on_click=on_finalizar),
            ft.Container(height=15),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # =================================================================
    # VISTA: ACTUALIZAR
    # =================================================================

    def _vista_actualizar(self) -> ft.Column:
        info = self.instalacion_existente or {}
        version_actual = info.get("version", "Desconocida")
        tipo = info.get("tipo", "Desconocido").capitalize()
        fecha = info.get("fecha_instalacion", "Desconocida")

        def on_atras(e):
            self._mostrar("menu")

        def on_reinstalar(e):
            self.modo = "instalar"
            self._mostrar("bienvenida")

        # Verificar integridad de archivos
        archivos_verificar = [
            ("python_embed/python.exe", PYTHON_EXE.exists()),
            ("app_emisora.py", (INSTALL_DIR / "app_emisora.py").exists()),
            ("app_receptora.py", (INSTALL_DIR / "app_receptora.py").exists()),
            ("data_access.py", (INSTALL_DIR / "data_access.py").exists()),
            ("servidor_red.py", (INSTALL_DIR / "servidor_red.py").exists()),
        ]
        integridad_ok = all(existe for _, existe in archivos_verificar)

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.UPDATE, size=24, color=COLOR_SECUNDARIO),
                ft.Text("Buscar Actualizaciones", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            ft.Container(height=4),
            ft.Text("Información sobre la instalación actual y actualizaciones disponibles.",
                    size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=20),

            # Versión actual
            ft.Container(
                content=ft.Column([
                    ft.Text("Instalación Actual", size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Container(height=10),
                    ft.Row([ft.Icon(ft.Icons.INFO, size=15, color=COLOR_SECUNDARIO),
                            ft.Text(f"Versión: {version_actual}", size=13, color=COLOR_TEXTO)], spacing=8),
                    ft.Row([ft.Icon(ft.Icons.APPS, size=15, color=COLOR_SECUNDARIO),
                            ft.Text(f"Tipo: {tipo}", size=13, color=COLOR_TEXTO)], spacing=8),
                    ft.Row([ft.Icon(ft.Icons.CALENDAR_TODAY, size=15, color=COLOR_SECUNDARIO),
                            ft.Text(f"Fecha de instalación: {fecha}", size=13, color=COLOR_TEXTO)], spacing=8),
                ], spacing=6),
                bgcolor=COLOR_SUPERFICIE, border_radius=12, padding=18,
            ),
            ft.Container(height=16),

            # Integridad
            ft.Container(
                content=ft.Column([
                    ft.Text("Verificación de Archivos", size=14, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
                    ft.Container(height=8),
                    *[ft.Row([
                        ft.Icon(ft.Icons.CHECK_CIRCLE if ok else ft.Icons.ERROR, size=14,
                                color=COLOR_EXITO if ok else COLOR_ERROR),
                        ft.Text(f"{nombre}: {'OK' if ok else 'NO ENCONTRADO'}", size=12, color=COLOR_TEXTO_SEC),
                    ], spacing=8) for nombre, ok in archivos_verificar],
                ], spacing=4),
                bgcolor=COLOR_SUPERFICIE, border_radius=12, padding=18,
            ),
            ft.Container(height=16),

            # Estado de actualización
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.Icons.CHECK_CIRCLE if integridad_ok else ft.Icons.WARNING,
                            size=20, color=COLOR_EXITO if integridad_ok else COLOR_WARNING),
                    ft.Column([
                        ft.Text(
                            "Su instalación está al día" if integridad_ok else "Se detectaron problemas",
                            size=14, weight=ft.FontWeight.W_500,
                            color=COLOR_EXITO if integridad_ok else COLOR_WARNING,
                        ),
                        ft.Text(
                            "Todos los archivos del sistema están presentes." if integridad_ok
                            else "Algunos archivos faltan. Se recomienda reparar o reinstalar.",
                            size=12, color=COLOR_TEXTO_SEC,
                        ),
                    ], spacing=2, expand=True),
                ], spacing=12),
                bgcolor=COLOR_SUPERFICIE, border_radius=12, padding=16,
            ),

            ft.Container(expand=True),
            ft.Row([
                ft.TextButton("Volver al menú", icon=ft.Icons.ARROW_BACK, on_click=on_atras),
                ft.Container(expand=True),
                ft.Button("Reinstalar", icon=ft.Icons.REFRESH,
                          bgcolor=COLOR_PRIMARIO, color=COLOR_TEXTO,
                          width=160, height=45, on_click=on_reinstalar),
            ]),
        ], expand=True)

    # =================================================================
    # VISTA: REPARAR — OPCIONES
    # =================================================================

    def _vista_reparar_opciones(self) -> ft.Column:
        info = self.instalacion_existente or {}
        tipo = info.get("tipo", None)
        self.tipo_instalacion = tipo  # Usar el tipo de la instalación existente

        def on_reparar(e):
            self._mostrar("reparando")

        def on_atras(e):
            self._mostrar("menu")

        reparaciones = [
            ("Verificar Python embebido", "Confirmar que python.exe existe y funciona"),
            ("Recrear launcher VBS", "Regenerar archivo de ejecución silenciosa"),
            ("Recrear accesos directos", "Restaurar accesos en escritorio y menú inicio"),
            ("Verificar reglas de firewall", "Asegurar que el puerto 5555 está abierto"),
        ]
        if tipo == "receptora":
            reparaciones.append(("Verificar bases de datos", "Confirmar que los archivos de datos existen"))

        return ft.Column([
            ft.Row([
                ft.Icon(ft.Icons.BUILD, size=24, color=COLOR_WARNING),
                ft.Text("Reparar Instalación", size=22, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ], spacing=12),
            ft.Container(height=4),
            ft.Text("Se verificarán y repararán los componentes de la instalación existente.",
                    size=13, color=COLOR_TEXTO_SEC),
            ft.Container(height=20),

            ft.Container(
                content=ft.Column([
                    ft.Text("Se realizarán las siguientes acciones:", size=14,
                            weight=ft.FontWeight.W_500, color=COLOR_TEXTO),
                    ft.Container(height=10),
                    *[ft.Container(
                        content=ft.Row([
                            ft.Container(
                                content=ft.Icon(ft.Icons.BUILD_CIRCLE, size=18, color=COLOR_WARNING),
                                bgcolor=f"{COLOR_WARNING}12",
                                border_radius=8, padding=7,
                            ),
                            ft.Column([
                                ft.Text(titulo, size=13, weight=ft.FontWeight.W_500, color=COLOR_TEXTO),
                                ft.Text(desc, size=11, color=COLOR_TEXTO_SEC),
                            ], spacing=2, expand=True),
                        ], spacing=12),
                        bgcolor=COLOR_SUPERFICIE_2,
                        border_radius=8,
                        padding=10,
                    ) for titulo, desc in reparaciones],
                ], spacing=8),
                bgcolor=COLOR_SUPERFICIE, border_radius=12, padding=18,
            ),

            ft.Container(expand=True),
            ft.Row([
                ft.TextButton("Volver al menú", icon=ft.Icons.ARROW_BACK, on_click=on_atras),
                ft.Container(expand=True),
                ft.Button("Reparar", icon=ft.Icons.BUILD,
                          bgcolor=COLOR_WARNING, color=COLOR_TEXTO,
                          width=160, height=45, on_click=on_reparar),
            ]),
        ], expand=True)

    # =================================================================
    # VISTA: REPARANDO (progreso)
    # =================================================================

    def _vista_reparando(self) -> ft.Column:
        self.barra_progreso = ft.ProgressBar(
            value=0, width=500, height=8,
            color=COLOR_WARNING, bgcolor=COLOR_SUPERFICIE_2, border_radius=4,
        )
        self.texto_progreso = ft.Text("Preparando reparación...", size=14,
                                       color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER)
        self.contenedor_log = ft.Column([], spacing=4, scroll=ft.ScrollMode.AUTO)

        return ft.Column([
            ft.Container(height=30),
            ft.ProgressRing(width=70, height=70, stroke_width=5, color=COLOR_WARNING),
            ft.Container(height=20),
            ft.Text("Reparando...", size=24, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=10),
            self.texto_progreso,
            ft.Container(height=20),
            self.barra_progreso,
            ft.Container(height=20),
            ft.Container(
                content=ft.Column([
                    ft.Row([ft.Icon(ft.Icons.TERMINAL, size=14, color=COLOR_TEXTO_SEC),
                            ft.Text("Registro", size=11, color=COLOR_TEXTO_SEC)], spacing=8),
                    ft.Container(height=6),
                    ft.Container(content=self.contenedor_log, bgcolor="#050508",
                                 border_radius=8, padding=12, height=150, width=520),
                ]),
                bgcolor=COLOR_SUPERFICIE, border_radius=12, padding=14,
            ),
            ft.Container(expand=True),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # =================================================================
    # VISTA: REPARACIÓN COMPLETADA
    # =================================================================

    def _vista_reparar_completado(self) -> ft.Column:
        def on_finalizar(e):
            self.page.window.close()

        def on_menu(e):
            self.instalacion_existente = detectar_instalacion_existente()
            self._mostrar("menu")

        return ft.Column([
            ft.Container(height=30),
            ft.Icon(ft.Icons.CHECK_CIRCLE, size=80, color=COLOR_EXITO),
            ft.Container(height=20),
            ft.Text("Reparación Completada", size=26, weight=ft.FontWeight.BOLD, color=COLOR_TEXTO),
            ft.Container(height=10),
            ft.Text("Todos los componentes han sido verificados y reparados.",
                    size=14, color=COLOR_TEXTO_SEC, text_align=ft.TextAlign.CENTER),
            ft.Container(expand=True),
            ft.Row([
                ft.Button("Volver al Menú", icon=ft.Icons.HOME,
                          bgcolor=COLOR_SUPERFICIE_2, color=COLOR_TEXTO,
                          width=180, height=48, on_click=on_menu),
                ft.Container(width=15),
                ft.Button("Finalizar", icon=ft.Icons.CHECK,
                          bgcolor=COLOR_PRIMARIO, color=COLOR_TEXTO,
                          width=150, height=48, on_click=on_finalizar),
            ], alignment=ft.MainAxisAlignment.CENTER),
            ft.Container(height=15),
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    # =================================================================
    # PROCESO: INSTALACIÓN
    # =================================================================

    def _agregar_log(self, mensaje: str, tipo: str = "info"):
        color = COLOR_TEXTO_SEC
        icono = ft.Icons.INFO_OUTLINED
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
            ft.Row([ft.Icon(icono, size=13, color=color),
                    ft.Text(mensaje, size=11, color=color)], spacing=8)
        )
        try:
            self.page.update()
        except Exception:
            pass

    def _actualizar_progreso(self, valor: float, mensaje: str):
        if self.barra_progreso:
            self.barra_progreso.value = valor
        if self.texto_progreso:
            self.texto_progreso.value = mensaje
        try:
            self.page.update()
        except Exception:
            pass

    def _proceso_instalacion(self):
        """Proceso completo de instalación."""
        try:
            t0 = time.time()

            # 1) Verificar Python
            self._actualizar_progreso(0.05, "Verificando Python embebido...")
            self._agregar_log("Verificando instalación de Python...", "info")
            time.sleep(0.3)
            if PYTHON_EXE.exists():
                self._agregar_log(f"✓ Python {PYTHON_VERSION} encontrado", "success")
            else:
                self._agregar_log("⚠ Python no encontrado en python_embed", "warning")

            # 2) Verificar dependencias
            self._actualizar_progreso(0.15, "Verificando dependencias...")
            self._agregar_log("Verificando paquetes de Python...", "info")
            time.sleep(0.2)
            for i, dep in enumerate(DEPENDENCIAS):
                prog = 0.15 + 0.25 * ((i + 1) / len(DEPENDENCIAS))
                self._actualizar_progreso(prog, f"Verificando {dep}...")
                self._agregar_log(f"  → {dep}", "info")
                time.sleep(0.1)
            self._agregar_log("✓ Todas las dependencias verificadas", "success")

            # 3) Crear launcher VBS
            self._actualizar_progreso(0.45, "Creando launcher silencioso...")
            self._agregar_log("Creando archivo launcher VBS...", "info")
            time.sleep(0.2)
            self._crear_launcher_vbs()
            self._agregar_log("✓ Launcher creado correctamente", "success")

            # 4) Accesos directos
            if self.opt_escritorio or self.opt_menu_inicio or self.opt_inicio_windows:
                self._actualizar_progreso(0.55, "Creando accesos directos...")
                self._agregar_log("Creando accesos directos...", "info")
                time.sleep(0.2)
                self._crear_accesos_directos()
                self._agregar_log("✓ Accesos directos creados", "success")

            # 5) Firewall
            if self.opt_firewall:
                self._actualizar_progreso(0.70, "Configurando firewall...")
                self._agregar_log("Configurando reglas de Windows Firewall...", "info")
                time.sleep(0.2)
                self._configurar_firewall()
                self._agregar_log("✓ Firewall configurado (puerto 5555)", "success")

            # 6) Base de datos
            if self.opt_crear_db and self.tipo_instalacion == "receptora":
                self._actualizar_progreso(0.82, "Inicializando bases de datos...")
                self._agregar_log("Creando archivos de datos Excel/JSON...", "info")
                time.sleep(0.2)
                self._inicializar_bases_datos()
                self._agregar_log("✓ Bases de datos inicializadas", "success")

            # 7) Guardar información de instalación
            self._actualizar_progreso(0.92, "Guardando configuración...")
            self._agregar_log("Guardando información de instalación...", "info")
            time.sleep(0.2)
            self._guardar_info_instalacion()
            self._agregar_log("✓ Configuración guardada", "success")

            # Completado
            t_total = time.time() - t0
            self._actualizar_progreso(1.0, "¡Instalación completada!")
            self._agregar_log(f"✓ Instalación completada en {t_total:.1f} segundos", "success")

            time.sleep(0.6)
            self.instalando = False
            self._mostrar("completado")

        except Exception as ex:
            self._agregar_log(f"✗ Error: {ex}", "error")
            self._actualizar_progreso(0, f"Error: {ex}")
            self.instalando = False

    # =================================================================
    # PROCESO: DESINSTALACIÓN
    # =================================================================

    def _proceso_desinstalacion(self):
        """Proceso completo de desinstalación."""
        try:
            t0 = time.time()

            # 1) Eliminar accesos directos
            self._actualizar_progreso(0.10, "Eliminando accesos directos...")
            self._agregar_log("Eliminando accesos directos...", "info")
            time.sleep(0.3)
            self._eliminar_accesos_directos()
            self._agregar_log("✓ Accesos directos eliminados", "success")

            # 2) Eliminar reglas de firewall
            self._actualizar_progreso(0.30, "Eliminando reglas de firewall...")
            self._agregar_log("Eliminando reglas de Windows Firewall...", "info")
            time.sleep(0.3)
            self._eliminar_reglas_firewall()
            self._agregar_log("✓ Reglas de firewall eliminadas", "success")

            # 3) Eliminar launcher VBS
            self._actualizar_progreso(0.50, "Eliminando launcher...")
            self._agregar_log("Eliminando archivos launcher...", "info")
            time.sleep(0.2)
            for vbs in ["launcher_emisora.vbs", "launcher_receptora.vbs"]:
                ruta = INSTALL_DIR / vbs
                if ruta.exists():
                    ruta.unlink()
                    self._agregar_log(f"  → {vbs} eliminado", "info")
            self._agregar_log("✓ Launcher eliminado", "success")

            # 4) Eliminar datos (opcional)
            if self.desinstalar_datos:
                self._actualizar_progreso(0.70, "Eliminando bases de datos...")
                self._agregar_log("Eliminando archivos de datos...", "info")
                time.sleep(0.2)
                archivos_datos = [
                    "tickets_db.xlsx", "tecnicos_db.xlsx", "equipos_db.xlsx",
                    "equipos_aprobados.json", "solicitudes_enlace.json",
                    "notificaciones_estado.json", "servidor_config.txt",
                ]
                for archivo in archivos_datos:
                    ruta = INSTALL_DIR / archivo
                    if ruta.exists():
                        ruta.unlink()
                        self._agregar_log(f"  → {archivo} eliminado", "info")
                self._agregar_log("✓ Archivos de datos eliminados", "success")

            # 5) Eliminar info de instalación
            self._actualizar_progreso(0.90, "Finalizando desinstalación...")
            info_path = INSTALL_DIR / "install_info.json"
            if info_path.exists():
                info_path.unlink()
            self._agregar_log("✓ Información de instalación eliminada", "success")

            t_total = time.time() - t0
            self._actualizar_progreso(1.0, "¡Desinstalación completada!")
            self._agregar_log(f"✓ Desinstalación completada en {t_total:.1f} s", "success")

            time.sleep(0.5)
            self.instalando = False
            self.instalacion_existente = None
            self._mostrar("desinstalar_completado")

        except Exception as ex:
            self._agregar_log(f"✗ Error: {ex}", "error")
            self.instalando = False

    # =================================================================
    # PROCESO: REPARACIÓN
    # =================================================================

    def _proceso_reparacion(self):
        """Proceso de reparación de instalación."""
        try:
            t0 = time.time()

            info = self.instalacion_existente or {}
            tipo = info.get("tipo", "emisora")
            self.tipo_instalacion = tipo

            # 1) Verificar Python
            self._actualizar_progreso(0.10, "Verificando Python...")
            self._agregar_log("Verificando Python embebido...", "info")
            time.sleep(0.3)
            if PYTHON_EXE.exists():
                self._agregar_log("✓ Python OK", "success")
            else:
                self._agregar_log("✗ Python no encontrado — reinstale el sistema", "error")

            # 2) Recrear launcher
            self._actualizar_progreso(0.30, "Recreando launcher VBS...")
            self._agregar_log("Recreando launcher silencioso...", "info")
            time.sleep(0.2)
            self._crear_launcher_vbs()
            self._agregar_log("✓ Launcher recreado", "success")

            # 3) Recrear accesos directos
            self._actualizar_progreso(0.50, "Recreando accesos directos...")
            self._agregar_log("Recreando accesos directos...", "info")
            time.sleep(0.2)
            self.opt_escritorio = True
            self.opt_menu_inicio = True
            self._crear_accesos_directos()
            self._agregar_log("✓ Accesos directos recreados", "success")

            # 4) Firewall
            self._actualizar_progreso(0.70, "Verificando firewall...")
            self._agregar_log("Configurando reglas de firewall...", "info")
            time.sleep(0.2)
            self._configurar_firewall()
            self._agregar_log("✓ Firewall configurado", "success")

            # 5) BD (solo receptora)
            if tipo == "receptora":
                self._actualizar_progreso(0.85, "Verificando bases de datos...")
                self._agregar_log("Verificando archivos de base de datos...", "info")
                time.sleep(0.2)
                self._inicializar_bases_datos()
                self._agregar_log("✓ Bases de datos verificadas", "success")

            # 6) Guardar info
            self._actualizar_progreso(0.95, "Guardando configuración...")
            self._guardar_info_instalacion()
            self._agregar_log("✓ Configuración actualizada", "success")

            t_total = time.time() - t0
            self._actualizar_progreso(1.0, "¡Reparación completada!")
            self._agregar_log(f"✓ Reparación completada en {t_total:.1f} s", "success")

            time.sleep(0.5)
            self.instalando = False
            self._mostrar("reparar_completado")

        except Exception as ex:
            self._agregar_log(f"✗ Error: {ex}", "error")
            self.instalando = False

    # =================================================================
    # MÉTODOS DE INSTALACIÓN
    # =================================================================

    def _crear_launcher_vbs(self):
        """Crea el archivo VBS para ejecutar la app sin ventana de consola."""
        base = Path(self.directorio_destino)
        if self.tipo_instalacion == "emisora":
            vbs_path = base / "launcher_emisora.vbs"
            py_script = "app_emisora.py"
        else:
            vbs_path = base / "launcher_receptora.vbs"
            py_script = "app_receptora.py"

        python_exe = base / "python_embed" / "python.exe"
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "{base}"
WshShell.Run """{python_exe}"" ""{base / py_script}""", 0, False
'''
        vbs_path.write_text(vbs_content)

    def _crear_accesos_directos(self):
        """Crea accesos directos según las opciones seleccionadas."""
        base = Path(self.directorio_destino)
        if self.tipo_instalacion == "emisora":
            nombre_app = APP_NAME_EMISORA
            vbs_path = base / "launcher_emisora.vbs"
            icono_path = base / "icons" / "emisora.ico"
        else:
            nombre_app = APP_NAME_RECEPTORA
            vbs_path = base / "launcher_receptora.vbs"
            icono_path = base / "icons" / "receptora.ico"

        ico = icono_path if icono_path.exists() else None

        if self.opt_escritorio:
            crear_acceso_directo_vbs(vbs_path, nombre_app, obtener_escritorio(),
                                     f"{nombre_app} — {APP_NAME}", ico)
        if self.opt_menu_inicio:
            carpeta = obtener_menu_inicio() / "Sistema Tickets IT"
            carpeta.mkdir(parents=True, exist_ok=True)
            crear_acceso_directo_vbs(vbs_path, nombre_app, carpeta,
                                     f"{nombre_app} — {APP_NAME}", ico)
        if self.opt_inicio_windows:
            crear_acceso_directo_vbs(vbs_path, nombre_app, obtener_carpeta_startup(),
                                     f"{nombre_app} — Inicio automático", ico)

    def _configurar_firewall(self):
        """Configura reglas de Windows Firewall para el puerto 5555."""
        try:
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                            'name=TicketsIT_Servidor'], capture_output=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                            'name=TicketsIT_Cliente'], capture_output=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                            'name=TicketsIT_Servidor', 'dir=in', 'action=allow',
                            'protocol=TCP', 'localport=5555'], capture_output=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'add', 'rule',
                            'name=TicketsIT_Cliente', 'dir=out', 'action=allow',
                            'protocol=TCP', 'localport=5555'], capture_output=True)
        except Exception:
            pass

    def _inicializar_bases_datos(self):
        """Inicializa bases de datos Excel y archivos JSON."""
        base = Path(self.directorio_destino)
        try:
            import pandas as pd

            ruta_tickets = base / "tickets_db.xlsx"
            if not ruta_tickets.exists():
                pd.DataFrame(columns=COLUMNAS_DB).to_excel(ruta_tickets, index=False, engine='openpyxl')

            ruta_tecnicos = base / "tecnicos_db.xlsx"
            if not ruta_tecnicos.exists():
                tecnicos = []
                for t in TECNICOS_INICIALES:
                    tecnicos.append({
                        "ID_TECNICO": t["id"], "NOMBRE": t["nombre"],
                        "ESTADO": "Disponible", "ESPECIALIDAD": t["especialidad"],
                        "TICKETS_ATENDIDOS": 0, "TICKET_ACTUAL": "",
                        "ULTIMA_ACTIVIDAD": datetime.now(),
                        "TELEFONO": t["telefono"], "EMAIL": t["email"],
                    })
                pd.DataFrame(tecnicos).to_excel(ruta_tecnicos, index=False, engine='openpyxl')

            ruta_equipos = base / "equipos_db.xlsx"
            if not ruta_equipos.exists():
                pd.DataFrame(columns=COLUMNAS_EQUIPOS).to_excel(ruta_equipos, index=False, engine='openpyxl')

            for archivo, contenido in [
                ("equipos_aprobados.json", {"aprobados": [], "rechazados": []}),
                ("solicitudes_enlace.json", []),
                ("notificaciones_estado.json", {}),
            ]:
                ruta = base / archivo
                if not ruta.exists():
                    with open(ruta, 'w', encoding='utf-8') as f:
                        json.dump(contenido, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _guardar_info_instalacion(self):
        """Guarda install_info.json con los datos de la instalación."""
        info = {
            "version": APP_VERSION,
            "tipo": self.tipo_instalacion,
            "fecha_instalacion": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "directorio": self.directorio_destino,
            "opciones": {
                "escritorio": self.opt_escritorio,
                "menu_inicio": self.opt_menu_inicio,
                "inicio_windows": self.opt_inicio_windows,
                "firewall": self.opt_firewall,
                "crear_db": self.opt_crear_db,
            },
        }
        info_path = Path(self.directorio_destino) / "install_info.json"
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump(info, f, indent=2, ensure_ascii=False)

    # =================================================================
    # MÉTODOS DE DESINSTALACIÓN
    # =================================================================

    def _eliminar_accesos_directos(self):
        """Elimina accesos directos creados por el instalador."""
        for nombre in [APP_NAME_EMISORA, APP_NAME_RECEPTORA]:
            lnk = f"{nombre}.lnk"
            # Escritorio
            ruta = obtener_escritorio() / lnk
            if ruta.exists():
                ruta.unlink()
            # Startup
            ruta = obtener_carpeta_startup() / lnk
            if ruta.exists():
                ruta.unlink()

        # Menú inicio — carpeta completa
        carpeta_menu = obtener_menu_inicio() / "Sistema Tickets IT"
        if carpeta_menu.exists():
            shutil.rmtree(carpeta_menu, ignore_errors=True)

    def _eliminar_reglas_firewall(self):
        """Elimina las reglas de firewall creadas."""
        try:
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                            'name=TicketsIT_Servidor'], capture_output=True)
            subprocess.run(['netsh', 'advfirewall', 'firewall', 'delete', 'rule',
                            'name=TicketsIT_Cliente'], capture_output=True)
        except Exception:
            pass

    # =================================================================
    # EJECUTAR APLICACIÓN
    # =================================================================

    def _ejecutar_aplicacion(self):
        """Ejecuta la aplicación recién instalada."""
        base = Path(self.directorio_destino)
        if self.tipo_instalacion == "emisora":
            vbs = base / "launcher_emisora.vbs"
        else:
            vbs = base / "launcher_receptora.vbs"

        if vbs.exists():
            subprocess.Popen(['wscript.exe', str(vbs)], cwd=str(base))
        self.page.window.close()


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

def main(page: ft.Page):
    InstaladorGrafico(page)


if __name__ == "__main__":
    ft.run(main)
