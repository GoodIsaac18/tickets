# =============================================================================
# APP EMISORA - Sistema de Tickets para Trabajadores
# =============================================================================
# Esta aplicación permite a los trabajadores crear tickets de soporte técnico.
# Captura automáticamente la información del sistema (MAC, Usuario AD, Hostname)
# y permite seleccionar la categoría y describir el problema.
# =============================================================================

import flet as ft
from flet import (
    Page, Container, Column, Row, Text, TextField, Dropdown, 
    Button, ProgressRing, AlertDialog, SnackBar,
    dropdown, Colors as colors, padding, alignment, border_radius,
    MainAxisAlignment, CrossAxisAlignment, FontWeight,
    TextAlign, Icons as icons, Icon, Divider
)
import asyncio
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


# =============================================================================
# COLORES CORPORATIVOS
# =============================================================================

# Definición de la paleta de colores corporativa (Azul/Gris)
COLOR_PRIMARIO = "#1565C0"          # Azul corporativo principal
COLOR_SECUNDARIO = "#0D47A1"        # Azul oscuro para hover/accent
COLOR_FONDO = "#F5F5F5"             # Gris claro para fondo
COLOR_TARJETA = "#FFFFFF"           # Blanco para tarjetas
COLOR_TEXTO = "#212121"             # Gris oscuro para texto
COLOR_TEXTO_CLARO = "#757575"       # Gris medio para texto secundario
COLOR_EXITO = "#4CAF50"             # Verde para éxito
COLOR_ERROR = "#F44336"             # Rojo para errores
COLOR_ADVERTENCIA = "#FF9800"       # Naranja para advertencias
COLOR_INFO = "#2196F3"              # Azul info


# =============================================================================
# CLASE PRINCIPAL DE LA APLICACIÓN
# =============================================================================

class AppEmisora:
    """
    Aplicación de escritorio para que los trabajadores emitan tickets
    de soporte técnico. Captura automáticamente la información del equipo
    y permite describir el problema a reportar.
    """
    
    def __init__(self, page: Page):
        """
        Constructor de la aplicación.
        
        Args:
            page: Objeto Page de Flet que representa la ventana principal.
        """
        self.page = page
        self.gestor = GestorTickets()
        
        # Información del sistema (capturada silenciosamente al inicio)
        self.mac_address: str = ""
        self.usuario_ad: str = ""
        self.hostname: str = ""
        
        # Referencias a controles de la interfaz
        self.txt_descripcion: Optional[TextField] = None
        self.dropdown_categoria: Optional[Dropdown] = None
        self.dropdown_prioridad: Optional[Dropdown] = None
        self.btn_enviar: Optional[Button] = None
        self.progress_ring: Optional[ProgressRing] = None
        self.container_info_sistema: Optional[Container] = None
        self.container_estado_servicio: Optional[Container] = None
        self.lbl_estado_tecnicos: Optional[Text] = None
        
        # Configurar la página
        self._configurar_pagina()
        
        # Capturar información del sistema
        self._capturar_info_sistema()
        
        # Construir la interfaz
        self._construir_ui()
    
    def _configurar_pagina(self) -> None:
        """
        Configura las propiedades de la ventana principal.
        Define tamaño, título, colores y comportamiento.
        """
        self.page.title = "Sistema de Tickets - Soporte Técnico"
        self.page.window.width = 450
        self.page.window.height = 650
        self.page.window.resizable = False  # Ventana de tamaño fijo
        self.page.window.center()           # Centrar en pantalla
        self.page.bgcolor = COLOR_FONDO
        self.page.padding = 0
        
        # Configurar el tema
        self.page.theme_mode = ft.ThemeMode.LIGHT
    
    def _capturar_info_sistema(self) -> None:
        """
        Módulo de Captura Silenciosa.
        
        Captura la información del sistema de forma automática al iniciar:
        - Dirección MAC (usando getmac)
        - Usuario de Active Directory (usando os.getlogin)
        - Hostname del equipo
        
        Esta información no puede ser editada por el usuario.
        """
        # Obtener MAC Address usando getmac (compatible Windows/macOS)
        self.mac_address = obtener_mac_address()
        
        # Obtener usuario de Active Directory
        self.usuario_ad = obtener_usuario_ad()
        
        # Obtener nombre de red del equipo
        self.hostname = obtener_hostname()
        
        print(f"[INFO] Sistema capturado - MAC: {self.mac_address}, Usuario: {self.usuario_ad}, Host: {self.hostname}")
    
    def _construir_ui(self) -> None:
        """
        Construye toda la interfaz de usuario de la aplicación.
        Organiza los elementos en un diseño limpio y corporativo.
        """
        # =================================================================
        # ENCABEZADO
        # =================================================================
        encabezado = Container(
            content=Column(
                controls=[
                    Row(
                        controls=[
                            Icon(icons.SUPPORT_AGENT, size=40, color=colors.WHITE),
                            Text(
                                "Crear Ticket de Soporte",
                                size=24,
                                weight=FontWeight.BOLD,
                                color=colors.WHITE
                            )
                        ],
                        alignment=MainAxisAlignment.CENTER,
                        spacing=10
                    ),
                    Text(
                        "Complete el formulario para reportar un problema",
                        size=14,
                        color=colors.WHITE70,
                        text_align=TextAlign.CENTER
                    )
                ],
                horizontal_alignment=CrossAxisAlignment.CENTER,
                spacing=5
            ),
            bgcolor=COLOR_PRIMARIO,
            padding=padding.symmetric(vertical=25, horizontal=20),
            width=450
        )
        
        # =================================================================
        # ESTADO DEL SERVICIO DE SOPORTE
        # =================================================================
        self._actualizar_estado_servicio()
        self.container_estado_servicio = self._crear_panel_estado()
        
        # =================================================================
        # INFORMACIÓN DEL SISTEMA (Solo lectura - No editable)
        # =================================================================
        self.container_info_sistema = Container(
            content=Column(
                controls=[
                    Text(
                        "Información del Equipo",
                        size=16,
                        weight=FontWeight.W_600,
                        color=COLOR_TEXTO
                    ),
                    Divider(height=1, color=colors.GREY_300),
                    # Usuario AD
                    Row(
                        controls=[
                            Icon(icons.PERSON, size=20, color=COLOR_PRIMARIO),
                            Text("Usuario:", size=13, color=COLOR_TEXTO_CLARO, width=80),
                            Text(
                                self.usuario_ad,
                                size=13,
                                weight=FontWeight.W_500,
                                color=COLOR_TEXTO
                            )
                        ],
                        spacing=10
                    ),
                    # Hostname
                    Row(
                        controls=[
                            Icon(icons.COMPUTER, size=20, color=COLOR_PRIMARIO),
                            Text("Equipo:", size=13, color=COLOR_TEXTO_CLARO, width=80),
                            Text(
                                self.hostname,
                                size=13,
                                weight=FontWeight.W_500,
                                color=COLOR_TEXTO
                            )
                        ],
                        spacing=10
                    ),
                    # MAC Address
                    Row(
                        controls=[
                            Icon(icons.ROUTER, size=20, color=COLOR_PRIMARIO),
                            Text("MAC:", size=13, color=COLOR_TEXTO_CLARO, width=80),
                            Text(
                                self.mac_address,
                                size=13,
                                weight=FontWeight.W_500,
                                color=COLOR_TEXTO,
                                selectable=True  # Permitir copiar pero no editar
                            )
                        ],
                        spacing=10
                    )
                ],
                spacing=8
            ),
            bgcolor=COLOR_TARJETA,
            border_radius=border_radius.all(10),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=15)
        )
        
        # =================================================================
        # FORMULARIO DE ENTRADA
        # =================================================================
        # Dropdown para seleccionar categoría
        self.dropdown_categoria = Dropdown(
            label="Categoría del Problema",
            hint_text="Seleccione una categoría",
            options=[dropdown.Option(cat) for cat in CATEGORIAS_DISPONIBLES],
            border_color=COLOR_PRIMARIO,
            focused_border_color=COLOR_SECUNDARIO,
            width=380,
            text_size=14
        )
        
        # Dropdown para seleccionar prioridad
        self.dropdown_prioridad = Dropdown(
            label="Prioridad",
            hint_text="Seleccione la urgencia",
            options=[dropdown.Option(p) for p in PRIORIDADES],
            value="Media",
            border_color=COLOR_PRIMARIO,
            focused_border_color=COLOR_SECUNDARIO,
            width=380,
            text_size=14
        )
        
        # Campo de texto para descripción
        self.txt_descripcion = TextField(
            label="Descripción del Problema",
            hint_text="Describa detalladamente el problema que está experimentando...",
            multiline=True,
            min_lines=5,
            max_lines=8,
            border_color=COLOR_PRIMARIO,
            focused_border_color=COLOR_SECUNDARIO,
            width=380,
            text_size=14
        )
        
        # Contenedor del formulario
        formulario = Container(
            content=Column(
                controls=[
                    Text(
                        "Detalles del Problema",
                        size=16,
                        weight=FontWeight.W_600,
                        color=COLOR_TEXTO
                    ),
                    Divider(height=1, color=colors.GREY_300),
                    self.dropdown_categoria,
                    self.dropdown_prioridad,
                    self.txt_descripcion
                ],
                spacing=15,
                horizontal_alignment=CrossAxisAlignment.CENTER
            ),
            bgcolor=COLOR_TARJETA,
            border_radius=border_radius.all(10),
            padding=ft.Padding.all(15),
            margin=ft.Padding.only(left=20, right=20, top=15)
        )
        
        # =================================================================
        # BOTÓN DE ENVÍO CON ANIMACIÓN DE CARGA
        # =================================================================
        # ProgressRing para animación de carga (inicialmente oculto)
        self.progress_ring = ProgressRing(
            width=20,
            height=20,
            stroke_width=2,
            color=colors.WHITE,
            visible=False
        )
        
        # Botón de envío principal
        self.btn_enviar = Button(
            content=Row(
                controls=[
                    Icon(icons.SEND, color=colors.WHITE),
                    Text("Enviar Ticket", color=colors.WHITE, weight=FontWeight.W_500),
                    self.progress_ring
                ],
                spacing=10,
                alignment=MainAxisAlignment.CENTER
            ),
            bgcolor=COLOR_PRIMARIO,
            width=200,
            height=50,
            on_click=self._enviar_ticket
        )
        
        # Contenedor del botón
        boton_container = Container(
            content=self.btn_enviar,
            alignment=ft.Alignment.CENTER,
            margin=ft.Padding.only(top=20, bottom=20)
        )
        
        # =================================================================
        # PIE DE PÁGINA
        # =================================================================
        pie_pagina = Container(
            content=Text(
                "© 2024 - Departamento de TI",
                size=12,
                color=COLOR_TEXTO_CLARO,
                text_align=TextAlign.CENTER
            ),
            alignment=ft.Alignment.CENTER,
            margin=ft.Padding.only(bottom=15)
        )
        
        # =================================================================
        # ENSAMBLAR LA INTERFAZ COMPLETA
        # =================================================================
        self.page.add(
            Column(
                controls=[
                    encabezado,
                    self.container_estado_servicio,
                    self.container_info_sistema,
                    formulario,
                    boton_container,
                    pie_pagina
                ],
                spacing=0,
                expand=True,
                scroll=ft.ScrollMode.AUTO
            )
        )
    
    def _actualizar_estado_servicio(self) -> None:
        """
        Actualiza la información del estado del servicio de soporte.
        Verifica si hay técnicos disponibles.
        """
        self.tecnicos_disponibles = self.gestor.obtener_tecnicos_disponibles()
        self.hay_disponible = self.gestor.hay_tecnico_disponible()
        self.mensaje_estado = self.gestor.obtener_mensaje_estado_sistema()
    
    def _crear_panel_estado(self) -> Container:
        """
        Crea el panel de estado del servicio de soporte.
        Muestra si los técnicos están disponibles u ocupados.
        """
        # Determinar color e icono según disponibilidad
        if self.hay_disponible:
            color_estado = COLOR_EXITO
            icono = icons.CHECK_CIRCLE
            texto_estado = "Servicio Disponible"
        else:
            color_estado = COLOR_ADVERTENCIA
            icono = icons.WARNING
            texto_estado = "Técnicos Ocupados"
        
        num_disponibles = len(self.tecnicos_disponibles) if hasattr(self, 'tecnicos_disponibles') else 0
        
        return Container(
            content=Row(
                controls=[
                    Icon(icono, size=24, color=color_estado),
                    Column(
                        controls=[
                            Text(
                                texto_estado,
                                size=14,
                                weight=FontWeight.W_600,
                                color=color_estado
                            ),
                            Text(
                                self.mensaje_estado if hasattr(self, 'mensaje_estado') else "",
                                size=11,
                                color=COLOR_TEXTO_CLARO
                            )
                        ],
                        spacing=2,
                        expand=True
                    ),
                    Container(
                        content=Text(
                            f"{num_disponibles}/2",
                            size=14,
                            weight=FontWeight.BOLD,
                            color=colors.WHITE
                        ),
                        bgcolor=color_estado,
                        padding=ft.Padding.symmetric(horizontal=12, vertical=6),
                        border_radius=border_radius.all(15)
                    )
                ],
                spacing=10,
                alignment=MainAxisAlignment.START
            ),
            bgcolor=COLOR_TARJETA,
            border_radius=border_radius.all(10),
            padding=ft.Padding.all(12),
            margin=ft.Padding.only(left=20, right=20, top=10),
            border=ft.Border.all(1, color_estado)
        )
    
    def _mostrar_dialogo_turno(self, ticket: dict) -> None:
        """
        Muestra un diálogo con la información del turno asignado.
        """
        turno = ticket.get("TURNO", "N/A")
        id_ticket = ticket.get("ID_TICKET", "N/A")
        posicion = self.gestor.obtener_posicion_cola(id_ticket)
        
        # Determinar mensaje según disponibilidad
        if self.hay_disponible:
            mensaje_principal = "¡Un técnico lo atenderá pronto!"
            color_turno = COLOR_EXITO
        else:
            mensaje_principal = "⚠️ Todos los técnicos están ocupados\nLe atenderemos en cuanto estemos disponibles."
            color_turno = COLOR_ADVERTENCIA
        
        tiempo_estimado = posicion * 15 if posicion else 15  # 15 min por ticket
        
        dialogo = AlertDialog(
            modal=True,
            title=Row(
                controls=[
                    Icon(icons.CONFIRMATION_NUMBER, color=COLOR_PRIMARIO, size=30),
                    Text("Ticket Registrado", weight=FontWeight.BOLD, size=20)
                ],
                spacing=10
            ),
            content=Container(
                content=Column(
                    controls=[
                        # Número de turno grande
                        Container(
                            content=Column(
                                controls=[
                                    Text("Su turno es:", size=14, color=COLOR_TEXTO_CLARO, text_align=TextAlign.CENTER),
                                    Text(
                                        turno,
                                        size=48,
                                        weight=FontWeight.BOLD,
                                        color=color_turno,
                                        text_align=TextAlign.CENTER
                                    ),
                                ],
                                horizontal_alignment=CrossAxisAlignment.CENTER,
                                spacing=5
                            ),
                            alignment=ft.Alignment.CENTER,
                            padding=ft.Padding.all(20),
                            bgcolor=COLOR_FONDO,
                            border_radius=border_radius.all(15),
                            width=250
                        ),
                        
                        # Información adicional
                        Container(height=10),
                        Text(mensaje_principal, size=14, color=COLOR_TEXTO, text_align=TextAlign.CENTER),
                        Container(height=5),
                        
                        # Detalles
                        Row(
                            controls=[
                                Column([
                                    Text("Ticket:", size=11, color=COLOR_TEXTO_CLARO),
                                    Text(f"#{id_ticket}", size=13, weight=FontWeight.W_600, color=COLOR_TEXTO)
                                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                                Container(width=1, height=40, bgcolor=colors.GREY_300),
                                Column([
                                    Text("Posición:", size=11, color=COLOR_TEXTO_CLARO),
                                    Text(f"#{posicion}" if posicion else "-", size=13, weight=FontWeight.W_600, color=COLOR_TEXTO)
                                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                                Container(width=1, height=40, bgcolor=colors.GREY_300),
                                Column([
                                    Text("Espera est.:", size=11, color=COLOR_TEXTO_CLARO),
                                    Text(f"~{tiempo_estimado} min", size=13, weight=FontWeight.W_600, color=COLOR_TEXTO)
                                ], horizontal_alignment=CrossAxisAlignment.CENTER),
                            ],
                            alignment=MainAxisAlignment.SPACE_AROUND
                        ),
                        
                        Container(height=10),
                        Text(
                            "Guarde su número de turno. Le notificaremos cuando sea su momento.",
                            size=11,
                            color=COLOR_TEXTO_CLARO,
                            text_align=TextAlign.CENTER
                        )
                    ],
                    horizontal_alignment=CrossAxisAlignment.CENTER,
                    spacing=5
                ),
                width=300,
                padding=ft.Padding.all(10)
            ),
            actions=[
                Button(
                    "Entendido",
                    bgcolor=COLOR_PRIMARIO,
                    color=colors.WHITE,
                    on_click=lambda e: self._cerrar_dialogo()
                )
            ],
            actions_alignment=MainAxisAlignment.CENTER
        )
        
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _mostrar_error(self, mensaje: str) -> None:
        """
        Muestra un diálogo de alerta con un mensaje de error.
        
        Args:
            mensaje: Texto del error a mostrar.
        """
        dialogo = AlertDialog(
            modal=True,
            title=Text("Error de Validación", color=COLOR_ERROR),
            content=Text(mensaje),
            actions=[
                ft.TextButton(
                    "Aceptar",
                    on_click=lambda e: self._cerrar_dialogo()
                )
            ],
            actions_alignment=MainAxisAlignment.END
        )
        self.page.overlay.append(dialogo)
        dialogo.open = True
        self.page.update()
    
    def _cerrar_dialogo(self) -> None:
        """
        Cierra el diálogo activo.
        """
        if self.page.overlay:
            self.page.overlay[-1].open = False
            self.page.update()
    
    def _mostrar_snackbar(self, mensaje: str, es_exito: bool = True) -> None:
        """
        Muestra una notificación SnackBar en la parte inferior.
        
        Args:
            mensaje: Texto a mostrar.
            es_exito: True para mensaje de éxito, False para error.
        """
        self.page.snack_bar = SnackBar(
            content=Text(
                mensaje,
                color=colors.WHITE
            ),
            bgcolor=COLOR_EXITO if es_exito else COLOR_ERROR,
            duration=4000
        )
        self.page.snack_bar.open = True
        self.page.update()
    
    def _validar_formulario(self) -> tuple[bool, str]:
        """
        Valida que todos los campos obligatorios estén completos.
        
        Returns:
            Tupla con (es_valido, mensaje_error)
        """
        # Validar categoría
        if not self.dropdown_categoria.value:
            return False, "Por favor, seleccione una categoría para el problema."
        
        # Validar descripción
        descripcion = self.txt_descripcion.value.strip() if self.txt_descripcion.value else ""
        if not descripcion:
            return False, "Por favor, describa el problema que está experimentando."
        
        if len(descripcion) < 10:
            return False, "La descripción debe tener al menos 10 caracteres."
        
        return True, ""
    
    async def _enviar_ticket_async(self) -> None:
        """
        Proceso asíncrono de envío del ticket.
        Maneja la animación de carga y el envío real.
        """
        try:
            # Actualizar estado de servicio antes de crear
            self._actualizar_estado_servicio()
            
            # Crear el ticket usando el gestor de datos
            ticket = self.gestor.crear_ticket(
                usuario_ad=self.usuario_ad,
                hostname=self.hostname,
                mac_address=self.mac_address,
                categoria=self.dropdown_categoria.value,
                descripcion=self.txt_descripcion.value.strip(),
                prioridad=self.dropdown_prioridad.value or "Media"
            )
            
            # Pequeña pausa para mostrar la animación
            await asyncio.sleep(1)
            
            # Ocultar animación de carga
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            
            # Actualizar panel de estado
            self._actualizar_estado_servicio()
            self.container_estado_servicio.content = self._crear_panel_estado().content
            self.container_estado_servicio.border = self._crear_panel_estado().border
            
            self.page.update()
            
            # Mostrar diálogo con información del turno
            self._mostrar_dialogo_turno(ticket)
            
            # Limpiar el formulario
            self._limpiar_formulario()
            
        except PermissionError as e:
            # Error de archivo bloqueado
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self.page.update()
            
            self._mostrar_error(
                "El archivo de base de datos está siendo utilizado.\n"
                "Por favor, ciérrelo e intente nuevamente."
            )
            
        except Exception as e:
            # Cualquier otro error
            self.progress_ring.visible = False
            self.btn_enviar.disabled = False
            self.page.update()
            
            self._mostrar_error(f"Error inesperado: {str(e)}")
    
    def _enviar_ticket(self, e) -> None:
        """
        Manejador del evento click del botón enviar.
        Valida el formulario y procesa el envío.
        
        Args:
            e: Evento de click.
        """
        # Validar formulario
        es_valido, mensaje_error = self._validar_formulario()
        
        if not es_valido:
            self._mostrar_error(mensaje_error)
            return
        
        # Mostrar animación de carga
        self.progress_ring.visible = True
        self.btn_enviar.disabled = True
        self.page.update()
        
        # Ejecutar envío asíncrono
        self.page.run_task(self._enviar_ticket_async)
    
    def _limpiar_formulario(self) -> None:
        """
        Limpia los campos del formulario después de un envío exitoso.
        """
        self.dropdown_categoria.value = None
        self.dropdown_prioridad.value = "Media"
        self.txt_descripcion.value = ""
        self.page.update()


# =============================================================================
# FUNCIÓN PRINCIPAL - PUNTO DE ENTRADA
# =============================================================================

def main(page: Page):
    """
    Función principal que inicializa la aplicación.
    
    Args:
        page: Objeto Page proporcionado por Flet.
    """
    AppEmisora(page)


# =============================================================================
# EJECUTAR APLICACIÓN
# =============================================================================

if __name__ == "__main__":
    # Iniciar la aplicación Flet
    ft.run(main)
