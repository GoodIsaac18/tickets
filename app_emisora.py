# =============================================================================
# APP EMISORA - Sistema de Tickets para Trabajadores
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
import asyncio
from datetime import datetime
from typing import Optional

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
    HEARTBEAT_INTERVAL
)


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
COLOR_ERROR = "#EF4444"             # Rojo
COLOR_ADVERTENCIA = "#F59E0B"       # Naranja
COLOR_INFO = "#06B6D4"              # Cyan
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
        
        # Vista actual: "principal" o "configuracion"
        self.vista_actual: str = "principal"
        
        # Controles de configuración
        self.txt_ip_servidor: Optional[TextField] = None
        self.txt_puerto_servidor: Optional[TextField] = None
        self.lbl_estado_config: Optional[Text] = None
        self.panel_estado_config: Optional[Container] = None
        
        # Estado
        self.tecnicos_disponibles = []
        self.hay_disponible = False
        self.ticket_activo = None
        
        self._configurar_pagina()
        self._capturar_info_sistema()
        self._inicializar_servidor()  # Después de capturar info para tener MAC
        self._construir_ui()
        self._iniciar_reloj()
    
    def _configurar_pagina(self) -> None:
        """Configura la ventana principal."""
        self.page.title = "🎫 Crear Ticket de Soporte"
        self.page.window.width = 500
        self.page.window.height = 720
        self.page.window.resizable = False
        self.page.bgcolor = COLOR_FONDO
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        
        # Establecer icono de la ventana
        from pathlib import Path
        icono_path = Path(__file__).parent / "icons" / "emisora.png"
        if icono_path.exists():
            self.page.window.icon = str(icono_path)
    
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
        """Actualiza la UI para mostrar el estado del enlace."""
        try:
            if hasattr(self, 'panel_estado_enlace') and self.panel_estado_enlace:
                mostrar_btn_reenviar = False
                
                if self.enlazado:
                    self.panel_estado_enlace.bgcolor = COLOR_EXITO
                    self.txt_estado_enlace.value = "✅ Conectado y enlazado"
                    self.txt_estado_enlace.color = colors.WHITE
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = False
                elif self.estado_enlace == "pendiente":
                    self.panel_estado_enlace.bgcolor = COLOR_ADVERTENCIA
                    self.txt_estado_enlace.value = "⏳ Esperando aprobación del administrador..."
                    self.txt_estado_enlace.color = colors.WHITE
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = True
                elif self.estado_enlace == "rechazado":
                    self.panel_estado_enlace.bgcolor = COLOR_ERROR
                    self.txt_estado_enlace.value = "❌ Solicitud rechazada"
                    self.txt_estado_enlace.color = colors.WHITE
                    mostrar_btn_reenviar = True
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = True
                elif self.estado_enlace == "revocado":
                    self.panel_estado_enlace.bgcolor = COLOR_ERROR
                    self.txt_estado_enlace.value = "🚫 Enlace revocado"
                    self.txt_estado_enlace.color = colors.WHITE
                    mostrar_btn_reenviar = True
                    if hasattr(self, 'btn_enviar') and self.btn_enviar:
                        self.btn_enviar.disabled = True
                else:
                    self.panel_estado_enlace.bgcolor = COLOR_INFO
                    self.txt_estado_enlace.value = "🔄 Conectando al servidor..."
                    self.txt_estado_enlace.color = colors.WHITE
                
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
                        Text("Centro de Soporte", size=22, weight=FontWeight.BOLD, color=colors.WHITE),
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
        """Panel de estado del servicio de soporte."""
        self.tecnicos_disponibles = self.gestor.obtener_tecnicos_disponibles()
        self.hay_disponible = self.gestor.hay_tecnico_disponible()
        
        if self.hay_disponible:
            icono = icons.CHECK_CIRCLE
            color = COLOR_EXITO
            titulo = "Servicio Disponible"
            subtitulo = f"{len(self.tecnicos_disponibles)} técnico(s) listo(s) para atenderte"
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
                        Text(f"{len(self.tecnicos_disponibles)}", size=13, weight=FontWeight.BOLD, color=colors.WHITE),
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
        """Panel que muestra el estado de enlace con el servidor."""
        # Determinar estado inicial
        mostrar_btn_reenviar = False
        if self.enlazado:
            color_fondo = COLOR_EXITO
            texto = "✅ Conectado y enlazado"
        elif self.estado_enlace == "pendiente":
            color_fondo = COLOR_ADVERTENCIA
            texto = "⏳ Esperando aprobación del administrador..."
        elif self.estado_enlace == "rechazado":
            color_fondo = COLOR_ERROR
            texto = "❌ Solicitud rechazada"
            mostrar_btn_reenviar = True
        elif self.estado_enlace == "revocado":
            color_fondo = COLOR_ERROR
            texto = "🚫 Enlace revocado"
            mostrar_btn_reenviar = True
        elif self.servidor_conectado:
            color_fondo = COLOR_INFO
            texto = "🔄 Conectando al servidor..."
        else:
            color_fondo = COLOR_TEXTO_SEC
            texto = "📡 Buscando servidor en la red..."
        
        self.txt_estado_enlace = Text(texto, size=12, color=colors.WHITE, weight=FontWeight.W_500)
        
        # Botón para reenviar solicitud
        self.btn_reenviar_solicitud = ft.TextButton(
            "🔄 Reenviar solicitud",
            on_click=self._reenviar_solicitud_enlace,
            style=ft.ButtonStyle(
                color=colors.WHITE,
                bgcolor=colors.WHITE24,
                padding=ft.Padding.symmetric(horizontal=10, vertical=5),
            ),
            visible=mostrar_btn_reenviar
        )
        
        self.panel_estado_enlace = Container(
            content=Column([
                Row([
                    Icon(icons.LINK, size=18, color=colors.WHITE),
                    self.txt_estado_enlace,
                ], spacing=8, alignment=MainAxisAlignment.CENTER),
                Row([self.btn_reenviar_solicitud], alignment=MainAxisAlignment.CENTER) if mostrar_btn_reenviar else Container()
            ], spacing=5, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=color_fondo,
            padding=ft.Padding.symmetric(horizontal=15, vertical=10),
            margin=ft.Padding.only(left=20, right=20, top=10),
            border_radius=ft.BorderRadius.all(8),
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
            config_path = Path(__file__).parent / "servidor_config.txt"
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
        
        # Construir vista
        contenedor = Column([
            header,
            self.panel_estado_config,
            panel_campos,
            panel_botones,
            panel_info,
        ], spacing=0, expand=True, scroll=ft.ScrollMode.AUTO)
        
        self.page.add(contenedor)
    
    def _crear_panel_mi_ticket(self) -> Optional[Container]:
        """Crea el panel que muestra el ticket activo del usuario."""
        self.ticket_activo = self.gestor.obtener_ticket_activo_usuario(self.usuario_ad)
        
        if not self.ticket_activo:
            return None
        
        estado = self.ticket_activo.get("ESTADO", "Abierto")
        turno = self.ticket_activo.get("TURNO", "-")
        id_ticket = self.ticket_activo.get("ID_TICKET", "-")
        categoria = self.ticket_activo.get("CATEGORIA", "-")
        posicion = self.gestor.obtener_posicion_cola(id_ticket)
        
        # Colores según estado
        colores_estado = {
            "Abierto": (COLOR_ADVERTENCIA, "#FFFBEB", icons.HOURGLASS_EMPTY),
            "En Cola": (COLOR_INFO, "#E0F2FE", icons.QUEUE),
            "En Proceso": (COLOR_PRIMARIO, "#EFF6FF", icons.ENGINEERING),
            "En Espera": (COLOR_TEXTO_SEC, "#F1F5F9", icons.PAUSE_CIRCLE),
        }
        color, color_fondo, icono = colores_estado.get(estado, (COLOR_INFO, "#E0F2FE", icons.INFO))
        
        # Obtener fecha del ticket
        fecha_ticket = self.ticket_activo.get("FECHA_APERTURA", "")
        if fecha_ticket:
            try:
                if hasattr(fecha_ticket, 'strftime'):
                    fecha_str = fecha_ticket.strftime("%d/%m %I:%M %p")
                else:
                    fecha_str = str(fecha_ticket)[:16]
            except:
                fecha_str = "Hoy"
        else:
            fecha_str = "Hoy"
        
        return Container(
            content=Column([
                # Header
                Row([
                    Row([
                        Icon(icons.CONFIRMATION_NUMBER, size=18, color=color),
                        Text("Tu Ticket Activo", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                    ], spacing=8),
                    Container(
                        content=Text(estado, size=10, color=colors.WHITE, weight=FontWeight.W_500),
                        bgcolor=color,
                        padding=ft.Padding.symmetric(horizontal=10, vertical=4),
                        border_radius=ft.BorderRadius.all(10),
                    ),
                ], alignment=MainAxisAlignment.SPACE_BETWEEN),
                
                Container(height=12),
                
                # Turno grande
                Container(
                    content=Row([
                        Column([
                            Text("TURNO", size=10, color=COLOR_TEXTO_SEC),
                            Text(turno, size=36, weight=FontWeight.BOLD, color=color),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER),
                        Container(width=1, height=50, bgcolor=COLOR_BORDE),
                        Column([
                            Text("TICKET", size=10, color=COLOR_TEXTO_SEC),
                            Text(f"#{id_ticket}", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
                        Container(width=1, height=50, bgcolor=COLOR_BORDE),
                        Column([
                            Text("FECHA", size=10, color=COLOR_TEXTO_SEC),
                            Text(fecha_str, size=12, weight=FontWeight.W_600, color=COLOR_TEXTO),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER),
                    ], alignment=MainAxisAlignment.SPACE_AROUND),
                    bgcolor=color_fondo,
                    padding=ft.Padding.all(15),
                    border_radius=ft.BorderRadius.all(10),
                ),
                
                Container(height=10),
                
                # Info adicional
                Row([
                    Icon(icono, size=16, color=color),
                    Text(f"{categoria}", size=12, color=COLOR_TEXTO_SEC),
                    Text("•", color=COLOR_TEXTO_SEC),
                    Text(f"Posición #{posicion}" if posicion else "Atención prioritaria", size=12, color=COLOR_TEXTO_SEC),
                ], spacing=6),
                
                Container(height=15),
                
                # Botón refrescar
                Button(
                    content=Row([
                        Icon(icons.REFRESH, color=color, size=16),
                        Text("Actualizar Estado", color=color, weight=FontWeight.W_500, size=12),
                    ], spacing=6, alignment=MainAxisAlignment.CENTER),
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=8),
                        side=ft.BorderSide(1, color),
                    ),
                    bgcolor=COLOR_TARJETA,
                    on_click=self._refrescar_ticket,
                ),
                
                Container(height=10),
                
                # Botones de acción: Recordatorio y Cancelar
                Row([
                    Button(
                        content=Row([
                            Icon(icons.NOTIFICATIONS_ACTIVE, color=COLOR_ADVERTENCIA, size=16),
                            Text("Recordatorio", color=COLOR_ADVERTENCIA, weight=FontWeight.W_500, size=11),
                        ], spacing=4, alignment=MainAxisAlignment.CENTER),
                        style=ft.ButtonStyle(
                            shape=ft.RoundedRectangleBorder(radius=8),
                            side=ft.BorderSide(1, COLOR_ADVERTENCIA),
                        ),
                        bgcolor=COLOR_TARJETA,
                        on_click=lambda e: self._mostrar_dialogo_recordatorio(),
                        expand=True,
                    ),
                    Container(width=8),
                    Button(
                        content=Row([
                            Icon(icons.CANCEL, color=COLOR_ERROR, size=16),
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
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=15),
        )
    
    def _refrescar_ticket(self, e):
        """Refresca el estado del ticket activo."""
        self.page.controls.clear()
        self._construir_ui()
        self.page.update()
    
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
    
    def _mostrar_mensaje_exito(self, mensaje: str):
        """Muestra un mensaje de éxito."""
        snackbar = SnackBar(
            content=Text(mensaje, color=colors.WHITE),
            bgcolor=COLOR_EXITO,
            duration=3000,
        )
        self.page.overlay.append(snackbar)
        snackbar.open = True
        self.page.update()

    def _construir_ui(self) -> None:
        """Construye la interfaz completa."""
        self.panel_estado = self._crear_panel_estado()
        self.panel_mi_ticket = self._crear_panel_mi_ticket()
        
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
            self._crear_panel_estado_enlace(),  # Panel de estado de enlace
        ]
        
        # Agregar panel de ticket activo si existe
        if self.panel_mi_ticket:
            elementos.append(self.panel_mi_ticket)
        else:
            # Si no hay ticket activo, mostrar el formulario completo
            elementos.extend([
                seccion_info,
                self._crear_info_equipo(),
                self._crear_formulario(),
                self._crear_boton_envio(),
            ])
        
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
        
        if len(descripcion) < 10:
            return False, "La descripción debe tener al menos 10 caracteres"
        
        return True, ""
    
    def _mostrar_dialogo_turno(self, ticket: dict) -> None:
        """Muestra el diálogo con información del turno."""
        turno = ticket.get("TURNO", "N/A")
        id_ticket = ticket.get("ID_TICKET", "N/A")
        posicion = self.gestor.obtener_posicion_cola(id_ticket)
        
        if self.hay_disponible:
            mensaje = "¡Un técnico te atenderá en breve!"
            color_turno = COLOR_EXITO
            icono_estado = icons.ROCKET_LAUNCH
        else:
            mensaje = "Tu ticket está en cola. Te atenderemos pronto."
            color_turno = COLOR_ADVERTENCIA
            icono_estado = icons.SCHEDULE
        
        # Obtener fecha/hora actual formateada
        fecha_hora_actual = datetime.now().strftime("%d/%m/%Y %I:%M %p")
        
        dialogo = AlertDialog(
            modal=True,
            title=Row([
                Icon(icons.CHECK_CIRCLE, color=COLOR_EXITO, size=28),
                Text("¡Ticket Creado!", weight=FontWeight.BOLD, size=18, color=COLOR_EXITO),
            ], spacing=10),
            content=Container(
                content=Column([
                    # Turno grande
                    Container(
                        content=Column([
                            Text("Tu número de turno", size=12, color=COLOR_TEXTO_SEC),
                            Text(turno, size=52, weight=FontWeight.BOLD, color=color_turno),
                            Row([
                                Icon(icono_estado, size=16, color=color_turno),
                                Text(mensaje, size=12, color=COLOR_TEXTO),
                            ], spacing=5, alignment=MainAxisAlignment.CENTER),
                        ], horizontal_alignment=CrossAxisAlignment.CENTER, spacing=5),
                        bgcolor=COLOR_FONDO,
                        border_radius=ft.BorderRadius.all(15),
                        padding=ft.Padding.symmetric(horizontal=30, vertical=20),
                    ),
                    
                    Container(height=15),
                    
                    # Info del ticket
                    Container(
                        content=Row([
                            Column([
                                Text("N° Ticket", size=10, color=COLOR_TEXTO_SEC),
                                Text(f"#{id_ticket}", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                            ], horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
                            Container(width=1, height=35, bgcolor=COLOR_BORDE),
                            Column([
                                Text("Posición", size=10, color=COLOR_TEXTO_SEC),
                                Text(f"#{posicion}" if posicion else "1", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                            ], horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
                            Container(width=1, height=35, bgcolor=COLOR_BORDE),
                            Column([
                                Text("Atención", size=10, color=COLOR_TEXTO_SEC),
                                Text("En breve", size=14, weight=FontWeight.W_600, color=COLOR_TEXTO),
                            ], horizontal_alignment=CrossAxisAlignment.CENTER, expand=True),
                        ]),
                        border=ft.Border.all(1, COLOR_BORDE),
                        border_radius=ft.BorderRadius.all(10),
                        padding=ft.Padding.symmetric(horizontal=10, vertical=12),
                    ),
                    
                    Container(height=8),
                    
                    # Fecha y hora
                    Row([
                        Icon(icons.SCHEDULE, size=14, color=COLOR_TEXTO_SEC),
                        Text(fecha_hora_actual, size=11, color=COLOR_TEXTO_SEC),
                    ], spacing=5, alignment=MainAxisAlignment.CENTER),
                    
                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                width=320,
                padding=ft.Padding.all(5),
            ),
            actions=[
                Button(
                    content=Row([
                        Icon(icons.THUMB_UP, color=colors.WHITE, size=16),
                        Text("Entendido", color=colors.WHITE, weight=FontWeight.W_500),
                    ], spacing=8, alignment=MainAxisAlignment.CENTER),
                    bgcolor=COLOR_PRIMARIO,
                    style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=10)),
                    width=150,
                    height=42,
                    on_click=lambda e: self._cerrar_dialogo(),
                ),
            ],
            actions_alignment=MainAxisAlignment.CENTER,
        )
        
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _mostrar_error(self, mensaje: str) -> None:
        """Muestra un diálogo de error."""
        dialogo = AlertDialog(
            modal=True,
            title=Row([
                Icon(icons.ERROR_OUTLINE, color=COLOR_ERROR, size=24),
                Text("Revisa el formulario", color=COLOR_ERROR, weight=FontWeight.W_600),
            ], spacing=8),
            content=Container(
                content=Text(mensaje, size=14, color=COLOR_TEXTO),
                padding=ft.Padding.only(top=5),
            ),
            actions=[
                ft.TextButton(
                    "Corregir",
                    on_click=lambda e: self._cerrar_dialogo(),
                ),
            ],
            actions_alignment=MainAxisAlignment.END,
        )
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _cerrar_dialogo(self) -> None:
        """Cierra el diálogo activo."""
        if self.page.overlay:
            self.page.overlay[-1].open = False
            self.page.update()
    
    async def _enviar_ticket_async(self) -> None:
        """Proceso asíncrono de envío."""
        try:
            # Actualizar estado
            self.tecnicos_disponibles = self.gestor.obtener_tecnicos_disponibles()
            self.hay_disponible = self.gestor.hay_tecnico_disponible()
            
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
            
            # Intentar enviar por red si está enlazado
            if self.servidor_conectado and self.servidor_ip and self.enlazado:
                try:
                    resultado = enviar_ticket_a_servidor(
                        self.servidor_ip,
                        self.servidor_puerto,
                        datos_ticket
                    )
                    if resultado and resultado.get("success"):
                        ticket = resultado.get("ticket", {})
                        print(f"[CLIENTE] Ticket enviado por red: {ticket.get('ID_TICKET', 'N/A')}")
                except Exception as e:
                    print(f"[CLIENTE] Error de red, guardando local: {e}")
                    # Si falla la red, guardar localmente
                    ticket = self.gestor.crear_ticket(**datos_ticket)
                    print(f"[CLIENTE] Ticket guardado localmente: {ticket.get('ID_TICKET', 'N/A')}")
            else:
                # No hay servidor, crear localmente
                ticket = self.gestor.crear_ticket(**datos_ticket)
                print(f"[CLIENTE] Ticket creado localmente (sin servidor): {ticket.get('ID_TICKET', 'N/A')}")
            
            await asyncio.sleep(0.8)
            
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self._enviando = False  # Resetear flag
            self.page.update()
            
            self._mostrar_dialogo_turno(ticket)
            
            # Reconstruir UI para mostrar el ticket activo
            self.page.controls.clear()
            self._construir_ui()
            self.page.update()
            
        except PermissionError:
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self._enviando = False
            self.page.update()
            self._mostrar_error("El archivo de datos está en uso. Ciérralo e intenta de nuevo.")
            
        except Exception as e:
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self._enviando = False
            self.page.update()
            self._mostrar_error(f"Error: {str(e)}")
    
    def _enviar_ticket(self, e) -> None:
        """Manejador del botón enviar."""
        # Evitar doble envío
        if self._enviando:
            return
        
        # Verificar estado de enlace
        if not self.enlazado:
            if self.estado_enlace == "pendiente":
                self._mostrar_error("⏳ Espera a que el administrador apruebe tu solicitud de enlace")
            elif self.estado_enlace == "rechazado":
                self._mostrar_error("❌ Tu solicitud fue rechazada. Contacta al administrador.")
            else:
                self._mostrar_error("🔗 Debes enlazar tu equipo con el servidor primero")
            return
        
        es_valido, error = self._validar_formulario()
        
        if not es_valido:
            self._mostrar_error(error)
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


def main(page: Page):
    """Punto de entrada de la aplicación."""
    AppEmisora(page)


if __name__ == "__main__":
    ft.run(main)
