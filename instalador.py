# =============================================================================
# INSTALADOR PROFESIONAL - Sistema de Tickets IT
# =============================================================================
# Instalador con interfaz gráfica para elegir Emisora o Receptora
# Instala dependencias, crea accesos directos y configura el sistema
# =============================================================================

import os
import sys
import subprocess
import shutil
import ctypes
import winreg
import urllib.request
import zipfile
import threading
import json
from pathlib import Path
from datetime import datetime

# =============================================================================
# CONFIGURACIÓN
# =============================================================================

APP_NAME = "Sistema de Tickets IT"
APP_NAME_EMISORA = "Tickets IT - Emisora"
APP_NAME_RECEPTORA = "Tickets IT - Receptora (Panel IT)"
PYTHON_VERSION = "3.11.9"
PYTHON_ZIP_NAME = f"python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{PYTHON_ZIP_NAME}"
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"

# Estructura de las bases de datos (para formateo)
COLUMNAS_DB = [
    "ID_TICKET", "TURNO", "FECHA_APERTURA", "USUARIO_AD", "HOSTNAME",
    "MAC_ADDRESS", "CATEGORIA", "PRIORIDAD", "DESCRIPCION", "ESTADO",
    "TECNICO_ASIGNADO", "NOTAS_RESOLUCION", "FECHA_CIERRE", "TIEMPO_ESTIMADO", "SATISFACCION"
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
    {"id": "TEC002", "nombre": "María García", "especialidad": "Software/Accesos", "telefono": "ext. 102", "email": "maria.garcia@empresa.com"}
]

DEPENDENCIAS = ["flet", "pandas", "openpyxl", "getmac", "winotify"]

# Directorio de instalación (donde está este script)
INSTALL_DIR = Path(__file__).parent.resolve()
PYTHON_DIR = INSTALL_DIR / "python_embed"
PYTHON_EXE = PYTHON_DIR / "python.exe"

# =============================================================================
# FUNCIONES DE UTILIDAD
# =============================================================================

def es_admin():
    """Verifica si se ejecuta como administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def obtener_escritorio():
    """Obtiene la ruta del escritorio del usuario."""
    return Path(os.path.join(os.environ["USERPROFILE"], "Desktop"))


def obtener_menu_inicio():
    """Obtiene la ruta del menú inicio del usuario."""
    return Path(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs"))


def obtener_carpeta_startup():
    """Obtiene la carpeta de inicio automático de Windows."""
    return Path(os.path.join(os.environ["APPDATA"], "Microsoft", "Windows", "Start Menu", "Programs", "Startup"))


def crear_acceso_directo(destino: Path, nombre: str, carpeta: Path, argumentos: str = "", icono: str = None, descripcion: str = ""):
    """Crea un acceso directo de Windows (.lnk)."""
    try:
        import win32com.client
        shell = win32com.client.Dispatch('WScript.Shell')
        acceso = shell.CreateShortCut(str(carpeta / f"{nombre}.lnk"))
        acceso.Targetpath = str(destino)
        acceso.Arguments = argumentos
        acceso.WorkingDirectory = str(destino.parent)
        acceso.Description = descripcion
        if icono:
            acceso.IconLocation = icono
        acceso.save()
        return True
    except ImportError:
        # Alternativa: usar PowerShell
        ps_script = f'''
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("{carpeta / f'{nombre}.lnk'}")
$Shortcut.TargetPath = "{destino}"
$Shortcut.Arguments = "{argumentos}"
$Shortcut.WorkingDirectory = "{destino.parent}"
$Shortcut.Description = "{descripcion}"
$Shortcut.Save()
'''
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
        return True
    except Exception as e:
        print(f"Error creando acceso directo: {e}")
        return False


def crear_acceso_directo_vbs(vbs_path: Path, nombre: str, carpeta: Path, descripcion: str = "", icono_path: Path = None):
    """Crea un acceso directo a un archivo VBS con icono opcional."""
    try:
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
        subprocess.run(["powershell", "-Command", ps_script], capture_output=True)
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False


# =============================================================================
# INTERFAZ DEL INSTALADOR (CONSOLA CON COLORES)
# =============================================================================

class InstaladorConsola:
    """Instalador con interfaz de consola interactiva."""
    
    def __init__(self):
        self.tipo_instalacion = None  # "emisora" o "receptora"
        self.crear_acceso_escritorio = True
        self.crear_acceso_menu = True
        self.iniciar_con_windows = False
        self.abrir_firewall = True
        self.instalacion_existente = {"emisora": False, "receptora": False}
        
    def limpiar_pantalla(self):
        os.system('cls')
        
    def color(self, texto, color_code):
        """Aplica color al texto usando códigos ANSI."""
        return f"\033[{color_code}m{texto}\033[0m"
    
    def verde(self, texto):
        return self.color(texto, "92")
    
    def azul(self, texto):
        return self.color(texto, "94")
    
    def amarillo(self, texto):
        return self.color(texto, "93")
    
    def rojo(self, texto):
        return self.color(texto, "91")
    
    def cyan(self, texto):
        return self.color(texto, "96")
    
    def mostrar_banner(self):
        """Muestra el banner del instalador."""
        self.limpiar_pantalla()
        # Habilitar colores ANSI en Windows
        os.system('')
        
        banner = f"""
{self.cyan('╔══════════════════════════════════════════════════════════════════╗')}
{self.cyan('║')}                                                                  {self.cyan('║')}
{self.cyan('║')}     {self.azul('████████╗██╗ ██████╗██╗  ██╗███████╗████████╗███████╗')}     {self.cyan('║')}
{self.cyan('║')}     {self.azul('╚══██╔══╝██║██╔════╝██║ ██╔╝██╔════╝╚══██╔══╝██╔════╝')}     {self.cyan('║')}
{self.cyan('║')}     {self.azul('   ██║   ██║██║     █████╔╝ █████╗     ██║   ███████╗')}     {self.cyan('║')}
{self.cyan('║')}     {self.azul('   ██║   ██║██║     ██╔═██╗ ██╔══╝     ██║   ╚════██║')}     {self.cyan('║')}
{self.cyan('║')}     {self.azul('   ██║   ██║╚██████╗██║  ██╗███████╗   ██║   ███████║')}     {self.cyan('║')}
{self.cyan('║')}     {self.azul('   ╚═╝   ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚══════╝')}     {self.cyan('║')}
{self.cyan('║')}                                                                  {self.cyan('║')}
{self.cyan('║')}           {self.verde('SISTEMA DE TICKETS PARA SOPORTE TÉCNICO')}              {self.cyan('║')}
{self.cyan('║')}                      {self.amarillo('INSTALADOR v3.0')}                           {self.cyan('║')}
{self.cyan('║')}                                                                  {self.cyan('║')}
{self.cyan('╚══════════════════════════════════════════════════════════════════╝')}
"""
        print(banner)
    
    def detectar_instalaciones(self):
        """Detecta si hay instalaciones existentes de Emisora y/o Receptora."""
        escritorio = obtener_escritorio()
        menu = obtener_menu_inicio() / "Sistema Tickets IT"
        startup = obtener_carpeta_startup()
        
        # Detectar Emisora
        emisora_vbs = INSTALL_DIR / "launcher_emisora.vbs"
        emisora_escritorio = escritorio / f"{APP_NAME_EMISORA}.lnk"
        emisora_menu = menu / f"{APP_NAME_EMISORA}.lnk"
        emisora_startup = startup / f"{APP_NAME_EMISORA}.lnk"
        
        self.instalacion_existente["emisora"] = (
            emisora_vbs.exists() or 
            emisora_escritorio.exists() or 
            emisora_menu.exists() or
            emisora_startup.exists()
        )
        
        # Detectar Receptora
        receptora_vbs = INSTALL_DIR / "launcher_receptora.vbs"
        receptora_escritorio = escritorio / f"{APP_NAME_RECEPTORA}.lnk"
        receptora_menu = menu / f"{APP_NAME_RECEPTORA}.lnk"
        receptora_startup = startup / f"{APP_NAME_RECEPTORA}.lnk"
        
        self.instalacion_existente["receptora"] = (
            receptora_vbs.exists() or 
            receptora_escritorio.exists() or 
            receptora_menu.exists() or
            receptora_startup.exists()
        )
        
        return self.instalacion_existente["emisora"] or self.instalacion_existente["receptora"]
    
    def mostrar_menu_principal(self):
        """Muestra el menú principal con opción de desinstalar."""
        hay_instalacion = self.detectar_instalaciones()
        
        print(f"""
{self.amarillo('¿Qué desea hacer?')}
""")
        
        if hay_instalacion:
            estado_emisora = self.verde("✓ Instalada") if self.instalacion_existente["emisora"] else self.rojo("✗ No instalada")
            estado_receptora = self.verde("✓ Instalada") if self.instalacion_existente["receptora"] else self.rojo("✗ No instalada")
            
            print(f"""  {self.cyan('Estado actual:')}
      • Emisora:   {estado_emisora}
      • Receptora: {estado_receptora}
""")
        
        print(f"""  {self.verde('[1]')} {self.cyan('INSTALAR')} - Instalar Emisora o Receptora
  {self.verde('[2]')} {self.cyan('DESINSTALAR')} - Eliminar aplicaciones instaladas
  {self.verde('[3]')} {self.cyan('REINSTALAR')} - Reinstalar conservando datos
  {self.verde('[4]')} {self.cyan('FORMATEAR')} - Eliminar todo e instalar limpio
  
  {self.rojo('[0]')} Salir
""")
    
    def desinstalar_aplicacion(self, tipo):
        """Desinstala una aplicación específica (emisora o receptora)."""
        if tipo == "emisora":
            nombre_app = APP_NAME_EMISORA
            vbs_path = INSTALL_DIR / "launcher_emisora.vbs"
        else:
            nombre_app = APP_NAME_RECEPTORA
            vbs_path = INSTALL_DIR / "launcher_receptora.vbs"
        
        escritorio = obtener_escritorio()
        menu = obtener_menu_inicio() / "Sistema Tickets IT"
        startup = obtener_carpeta_startup()
        
        acciones = []
        
        # Eliminar launcher VBS
        if vbs_path.exists():
            try:
                vbs_path.unlink()
                acciones.append(f"Launcher {tipo}")
            except:
                pass
        
        # Eliminar acceso del escritorio
        acceso_escritorio = escritorio / f"{nombre_app}.lnk"
        if acceso_escritorio.exists():
            try:
                acceso_escritorio.unlink()
                acciones.append("Acceso escritorio")
            except:
                pass
        
        # Eliminar acceso del menú inicio
        acceso_menu = menu / f"{nombre_app}.lnk"
        if acceso_menu.exists():
            try:
                acceso_menu.unlink()
                acciones.append("Acceso menú inicio")
            except:
                pass
        
        # Eliminar entrada de startup
        acceso_startup = startup / f"{nombre_app}.lnk"
        if acceso_startup.exists():
            try:
                acceso_startup.unlink()
                acciones.append("Inicio automático")
            except:
                pass
        
        return acciones
    
    def ejecutar_desinstalacion(self):
        """Muestra menú de desinstalación y ejecuta la acción."""
        self.mostrar_banner()
        
        if not self.instalacion_existente["emisora"] and not self.instalacion_existente["receptora"]:
            print(f"""
{self.amarillo('No hay aplicaciones instaladas para desinstalar.')}

  El sistema no detectó ninguna instalación previa de:
  • Soporte Técnico - Emisora
  • Soporte Técnico - Receptora
""")
            input(f"\n  {self.verde('Presione Enter para volver...')}")
            return
        
        estado_emisora = self.verde("✓ Instalada") if self.instalacion_existente["emisora"] else self.rojo("✗ No instalada")
        estado_receptora = self.verde("✓ Instalada") if self.instalacion_existente["receptora"] else self.rojo("✗ No instalada")
        
        print(f"""
{self.cyan('═' * 60)}
{self.rojo('  DESINSTALADOR - SISTEMA DE TICKETS')}
{self.cyan('═' * 60)}

{self.amarillo('Estado de instalaciones:')}
  • Emisora:   {estado_emisora}
  • Receptora: {estado_receptora}

{self.amarillo('¿Qué desea desinstalar?')}

  {self.verde('[1]')} Desinstalar {self.cyan('EMISORA')} únicamente
  {self.verde('[2]')} Desinstalar {self.cyan('RECEPTORA')} únicamente
  {self.verde('[3]')} Desinstalar {self.cyan('AMBAS')} aplicaciones
  
  {self.rojo('[0]')} Cancelar

{self.amarillo('NOTA:')} Los datos (tickets, equipos aprobados, etc.) NO se eliminarán.
""")
        
        opcion = input("  Seleccione una opción: ").strip()
        
        if opcion == "0":
            return
        
        apps_a_desinstalar = []
        if opcion == "1" and self.instalacion_existente["emisora"]:
            apps_a_desinstalar.append("emisora")
        elif opcion == "2" and self.instalacion_existente["receptora"]:
            apps_a_desinstalar.append("receptora")
        elif opcion == "3":
            if self.instalacion_existente["emisora"]:
                apps_a_desinstalar.append("emisora")
            if self.instalacion_existente["receptora"]:
                apps_a_desinstalar.append("receptora")
        
        if not apps_a_desinstalar:
            print(f"\n  {self.amarillo('La aplicación seleccionada no está instalada.')}")
            input(f"\n  {self.verde('Presione Enter para volver...')}")
            return
        
        # Confirmar
        print(f"\n{self.rojo('¡ATENCIÓN!')} Se desinstalarán: {', '.join(apps_a_desinstalar).upper()}")
        confirmar = input(f"\n  Escriba {self.verde('SI')} para confirmar: ").strip().upper()
        
        if confirmar != "SI":
            print(f"\n  {self.amarillo('Desinstalación cancelada.')}")
            input(f"\n  {self.verde('Presione Enter para volver...')}")
            return
        
        # Ejecutar desinstalación
        print(f"\n{self.cyan('═' * 60)}")
        print(f"{self.verde('  DESINSTALANDO...')}")
        print(f"{self.cyan('═' * 60)}\n")
        
        for app in apps_a_desinstalar:
            acciones = self.desinstalar_aplicacion(app)
            nombre = APP_NAME_EMISORA if app == "emisora" else APP_NAME_RECEPTORA
            if acciones:
                print(f"  {self.verde('✓')} {nombre} desinstalada")
                for accion in acciones:
                    print(f"      - {accion} eliminado")
            else:
                print(f"  {self.amarillo('!')} {nombre} - no había componentes que eliminar")
        
        # Eliminar regla de firewall
        print(f"\n  {self.verde('→')} Eliminando regla de firewall...")
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=TicketsIT_Servidor"],
            capture_output=True
        )
        
        # Eliminar carpeta del menú inicio si está vacía
        menu = obtener_menu_inicio() / "Sistema Tickets IT"
        try:
            if menu.exists() and not any(menu.iterdir()):
                menu.rmdir()
                print(f"  {self.verde('✓')} Carpeta del menú inicio eliminada")
        except:
            pass
        
        print(f"""
{self.cyan('═' * 60)}
{self.verde('  DESINSTALACIÓN COMPLETADA')}
{self.cyan('═' * 60)}

  Los archivos del programa permanecen en:
  {self.cyan(str(INSTALL_DIR))}
  
  Puede eliminarlos manualmente si lo desea.
""")
        input(f"\n  {self.verde('Presione Enter para finalizar...')}")
    
    def ejecutar_formateo(self):
        """Elimina todo (datos incluidos) y crea bases de datos nuevas."""
        self.mostrar_banner()
        
        print(f"""
{self.cyan('═' * 60)}
{self.rojo('  FORMATEO COMPLETO - ¡PRECAUCIÓN!')}
{self.cyan('═' * 60)}

{self.amarillo('Esta acción eliminará TODOS los datos:')}

  • Accesos directos y configuraciones
  • Archivo de tickets (historial completo)
  • Base de datos de técnicos
  • Base de datos de equipos/inventario
  • Equipos aprobados/rechazados
  • Solicitudes de enlace pendientes
  • Configuración del servidor
  
{self.rojo('¡ESTA ACCIÓN NO SE PUEDE DESHACER!')}

Después del formateo, se crearán bases de datos NUEVAS y vacías.
""")
        
        confirmar1 = input(f"  Escriba {self.verde('FORMATEAR')} para continuar: ").strip().upper()
        
        if confirmar1 != "FORMATEAR":
            print(f"\n  {self.amarillo('Operación cancelada.')}")
            input(f"\n  {self.verde('Presione Enter para volver...')}")
            return
        
        print(f"\n{self.rojo('¿Está COMPLETAMENTE SEGURO?')}")
        confirmar2 = input(f"  Escriba {self.verde('SI')} para confirmar el formateo: ").strip().upper()
        
        if confirmar2 != "SI":
            print(f"\n  {self.amarillo('Operación cancelada.')}")
            input(f"\n  {self.verde('Presione Enter para volver...')}")
            return
        
        print(f"\n{self.cyan('═' * 60)}")
        print(f"{self.rojo('  FORMATEANDO...')}")
        print(f"{self.cyan('═' * 60)}\n")
        
        # Desinstalar ambas apps
        if self.instalacion_existente["emisora"]:
            self.desinstalar_aplicacion("emisora")
            print(f"  {self.verde('✓')} Emisora desinstalada")
        
        if self.instalacion_existente["receptora"]:
            self.desinstalar_aplicacion("receptora")
            print(f"  {self.verde('✓')} Receptora desinstalada")
        
        # Eliminar todos los archivos de datos
        archivos_datos = [
            "tickets_db.xlsx",      # Base de datos de tickets
            "tecnicos_db.xlsx",     # Base de datos de técnicos
            "equipos_db.xlsx",      # Base de datos de equipos/inventario
            "equipos_aprobados.json",
            "solicitudes_enlace.json",
            "notificaciones_estado.json",
            "servidor_config.txt",
            "desinstalar.bat"
        ]
        
        print(f"\n  {self.amarillo('Eliminando archivos de datos...')}")
        for archivo in archivos_datos:
            ruta = INSTALL_DIR / archivo
            if ruta.exists():
                try:
                    ruta.unlink()
                    print(f"  {self.verde('✓')} {archivo} eliminado")
                except:
                    print(f"  {self.amarillo('!')} No se pudo eliminar {archivo}")
        
        # Eliminar regla de firewall
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name=TicketsIT_Servidor"],
            capture_output=True
        )
        print(f"  {self.verde('✓')} Regla de firewall eliminada")
        
        # Recrear bases de datos nuevas
        print(f"\n  {self.amarillo('Creando bases de datos nuevas...')}")
        self._crear_bases_datos_nuevas()
        
        print(f"""
{self.cyan('═' * 60)}
{self.verde('  FORMATEO COMPLETADO')}
{self.cyan('═' * 60)}

  El sistema ha sido formateado completamente.
  Se han creado bases de datos nuevas y vacías.
  
  Está listo para una instalación limpia.
""")
        
        continuar = input(f"  ¿Desea instalar ahora? ({self.verde('S')}/{self.rojo('N')}): ").strip().upper()
        
        if continuar == "S":
            self.ejecutar()
        else:
            input(f"\n  {self.verde('Presione Enter para finalizar...')}")
    
    def _crear_bases_datos_nuevas(self):
        """Crea las bases de datos Excel y JSON nuevas y vacías."""
        try:
            import pandas as pd
            
            # 1. Crear tickets_db.xlsx vacío con encabezados
            ruta_tickets = INSTALL_DIR / "tickets_db.xlsx"
            df_tickets = pd.DataFrame(columns=COLUMNAS_DB)
            df_tickets.to_excel(ruta_tickets, index=False, engine='openpyxl')
            print(f"  {self.verde('✓')} tickets_db.xlsx creado (vacío)")
            
            # 2. Crear tecnicos_db.xlsx con técnicos iniciales
            ruta_tecnicos = INSTALL_DIR / "tecnicos_db.xlsx"
            tecnicos_iniciales = []
            for tec in TECNICOS_INICIALES:
                tecnicos_iniciales.append({
                    "ID_TECNICO": tec["id"],
                    "NOMBRE": tec["nombre"],
                    "ESTADO": "Disponible",
                    "ESPECIALIDAD": tec["especialidad"],
                    "TICKETS_ATENDIDOS": 0,
                    "TICKET_ACTUAL": "",
                    "ULTIMA_ACTIVIDAD": datetime.now(),
                    "TELEFONO": tec["telefono"],
                    "EMAIL": tec["email"]
                })
            df_tecnicos = pd.DataFrame(tecnicos_iniciales)
            df_tecnicos.to_excel(ruta_tecnicos, index=False, engine='openpyxl')
            print(f"  {self.verde('✓')} tecnicos_db.xlsx creado (con técnicos iniciales)")
            
            # 3. Crear equipos_db.xlsx vacío con encabezados
            ruta_equipos = INSTALL_DIR / "equipos_db.xlsx"
            df_equipos = pd.DataFrame(columns=COLUMNAS_EQUIPOS)
            df_equipos.to_excel(ruta_equipos, index=False, engine='openpyxl')
            print(f"  {self.verde('✓')} equipos_db.xlsx creado (vacío)")
            
            # 4. Crear equipos_aprobados.json vacío
            ruta_equipos_json = INSTALL_DIR / "equipos_aprobados.json"
            with open(ruta_equipos_json, 'w', encoding='utf-8') as f:
                json.dump({"aprobados": [], "rechazados": []}, f, indent=2, ensure_ascii=False)
            print(f"  {self.verde('✓')} equipos_aprobados.json creado")
            
            # 5. Crear solicitudes_enlace.json vacío
            ruta_solicitudes = INSTALL_DIR / "solicitudes_enlace.json"
            with open(ruta_solicitudes, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            print(f"  {self.verde('✓')} solicitudes_enlace.json creado")
            
            # 6. Crear notificaciones_estado.json vacío
            ruta_notif = INSTALL_DIR / "notificaciones_estado.json"
            with open(ruta_notif, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2, ensure_ascii=False)
            print(f"  {self.verde('✓')} notificaciones_estado.json creado")
            
        except ImportError:
            print(f"  {self.amarillo('!')} pandas no instalado - las bases de datos se crearán al iniciar la aplicación")
        except Exception as e:
            print(f"  {self.amarillo('!')} Error creando bases de datos: {e}")
    
    def ejecutar_reinstalacion(self):
        """Reinstala conservando los datos."""
        self.mostrar_banner()
        
        print(f"""
{self.cyan('═' * 60)}
{self.amarillo('  REINSTALACIÓN - Conservará sus datos')}
{self.cyan('═' * 60)}

  Esta acción reinstalará las aplicaciones seleccionadas
  conservando todos los datos existentes:
  
  • Tickets existentes
  • Equipos aprobados
  • Configuraciones
""")
        
        if not self.instalacion_existente["emisora"] and not self.instalacion_existente["receptora"]:
            print(f"\n  {self.amarillo('No hay aplicaciones instaladas para reinstalar.')}")
            print(f"  Use la opción {self.verde('INSTALAR')} para una nueva instalación.")
            input(f"\n  {self.verde('Presione Enter para volver...')}")
            return
        
        estado_emisora = self.verde("✓") if self.instalacion_existente["emisora"] else self.rojo("✗")
        estado_receptora = self.verde("✓") if self.instalacion_existente["receptora"] else self.rojo("✗")
        
        print(f"""
{self.amarillo('¿Qué desea reinstalar?')}

  {self.verde('[1]')} Reinstalar {self.cyan('EMISORA')} {estado_emisora}
  {self.verde('[2]')} Reinstalar {self.cyan('RECEPTORA')} {estado_receptora}
  {self.verde('[3]')} Reinstalar {self.cyan('AMBAS')}
  
  {self.rojo('[0]')} Cancelar
""")
        
        opcion = input("  Seleccione una opción: ").strip()
        
        if opcion == "0":
            return
        
        # Determinar qué reinstalar
        reinstalar_emisora = opcion in ["1", "3"]
        reinstalar_receptora = opcion in ["2", "3"]
        
        if reinstalar_emisora:
            if self.instalacion_existente["emisora"]:
                self.desinstalar_aplicacion("emisora")
            self.tipo_instalacion = "emisora"
            if not self.configurar_opciones():
                return
            self.ejecutar_instalacion()
        
        if reinstalar_receptora:
            if self.instalacion_existente["receptora"]:
                self.desinstalar_aplicacion("receptora")
            self.tipo_instalacion = "receptora"
            if not self.configurar_opciones():
                return
            self.ejecutar_instalacion()

    def mostrar_menu_tipo(self):
        """Muestra el menú para elegir tipo de instalación."""
        print(f"""
{self.amarillo('¿Qué tipo de aplicación desea instalar?')}

  {self.verde('[1]')} {self.cyan('EMISORA')} - Para trabajadores/usuarios
      → Permite crear y enviar tickets de soporte
      → Se conecta automáticamente al servidor IT
      → Interfaz simple y fácil de usar

  {self.verde('[2]')} {self.cyan('RECEPTORA')} - Para el equipo de IT
      → Panel de administración completo
      → Recibe y gestiona tickets de soporte
      → Dashboard con estadísticas y métricas
      → Gestión de técnicos y equipos

  {self.rojo('[0]')} Cancelar instalación
""")
    
    def mostrar_opciones(self):
        """Muestra las opciones de instalación."""
        tipo = "EMISORA (Trabajadores)" if self.tipo_instalacion == "emisora" else "RECEPTORA (Panel IT)"
        
        print(f"""
{self.cyan('═' * 60)}
{self.verde(f'  Instalación seleccionada: {tipo}')}
{self.cyan('═' * 60)}

{self.amarillo('Opciones de instalación:')}

  {self.verde('[1]')} Crear acceso directo en Escritorio: {self.estado_opcion(self.crear_acceso_escritorio)}
  {self.verde('[2]')} Crear acceso en Menú Inicio: {self.estado_opcion(self.crear_acceso_menu)}
  {self.verde('[3]')} Iniciar automáticamente con Windows: {self.estado_opcion(self.iniciar_con_windows)}
  {self.verde('[4]')} Configurar Firewall de Windows: {self.estado_opcion(self.abrir_firewall)}

  {self.verde('[I]')} {self.cyan('INICIAR INSTALACIÓN')}
  {self.rojo('[C]')} Cancelar

{self.amarillo('Presione el número para cambiar la opción o I para instalar:')}
""")
    
    def estado_opcion(self, valor):
        return self.verde("✓ SÍ") if valor else self.rojo("✗ NO")
    
    def seleccionar_tipo(self):
        """Permite al usuario seleccionar el tipo de instalación."""
        while True:
            self.mostrar_banner()
            self.mostrar_menu_tipo()
            
            opcion = input(f"  {self.amarillo('Seleccione una opción [1/2/0]:')} ").strip()
            
            if opcion == "1":
                self.tipo_instalacion = "emisora"
                return True
            elif opcion == "2":
                self.tipo_instalacion = "receptora"
                return True
            elif opcion == "0":
                return False
            else:
                print(f"\n  {self.rojo('Opción no válida. Intente de nuevo.')}")
                input("  Presione Enter para continuar...")
    
    def configurar_opciones(self):
        """Permite configurar las opciones de instalación."""
        while True:
            self.mostrar_banner()
            self.mostrar_opciones()
            
            opcion = input("  ").strip().upper()
            
            if opcion == "1":
                self.crear_acceso_escritorio = not self.crear_acceso_escritorio
            elif opcion == "2":
                self.crear_acceso_menu = not self.crear_acceso_menu
            elif opcion == "3":
                self.iniciar_con_windows = not self.iniciar_con_windows
            elif opcion == "4":
                self.abrir_firewall = not self.abrir_firewall
            elif opcion == "I":
                return True
            elif opcion == "C":
                return False
    
    def mostrar_progreso(self, mensaje, porcentaje=None):
        """Muestra mensaje de progreso."""
        if porcentaje is not None:
            barra = "█" * int(porcentaje / 5) + "░" * (20 - int(porcentaje / 5))
            print(f"\r  [{self.cyan(barra)}] {porcentaje:3}% - {mensaje}", end="", flush=True)
        else:
            print(f"  {self.verde('→')} {mensaje}")
    
    def instalar_python(self):
        """Descarga e instala Python embebido."""
        if PYTHON_EXE.exists():
            self.mostrar_progreso("Python ya está instalado ✓")
            return True
        
        self.mostrar_progreso("Descargando Python embebido...")
        
        try:
            # Crear directorio
            PYTHON_DIR.mkdir(parents=True, exist_ok=True)
            
            zip_path = INSTALL_DIR / PYTHON_ZIP_NAME
            
            # Descargar Python
            def reportar_progreso(block_num, block_size, total_size):
                if total_size > 0:
                    porcentaje = min(100, int(block_num * block_size * 100 / total_size))
                    self.mostrar_progreso("Descargando Python...", porcentaje)
            
            urllib.request.urlretrieve(PYTHON_URL, zip_path, reportar_progreso)
            print()  # Nueva línea después de la barra de progreso
            
            # Extraer
            self.mostrar_progreso("Extrayendo Python...")
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(PYTHON_DIR)
            
            # Eliminar zip
            zip_path.unlink()
            
            # Configurar para habilitar pip y site-packages
            self.mostrar_progreso("Configurando Python...")
            
            # Crear sitecustomize.py
            (PYTHON_DIR / "sitecustomize.py").write_text("import site\nsite.main()\n")
            
            # Modificar python311._pth
            pth_content = """python311.zip
.
..
Lib
Lib\\site-packages
import site
"""
            (PYTHON_DIR / "python311._pth").write_text(pth_content)
            
            # Crear directorios necesarios
            (PYTHON_DIR / "Lib" / "site-packages").mkdir(parents=True, exist_ok=True)
            (PYTHON_DIR / "Scripts").mkdir(parents=True, exist_ok=True)
            
            # Descargar e instalar pip
            self.mostrar_progreso("Instalando pip...")
            get_pip_path = PYTHON_DIR / "get-pip.py"
            urllib.request.urlretrieve(GET_PIP_URL, get_pip_path)
            
            subprocess.run(
                [str(PYTHON_EXE), str(get_pip_path), "--no-warn-script-location"],
                capture_output=True,
                cwd=str(INSTALL_DIR)
            )
            
            self.mostrar_progreso("Python instalado correctamente ✓")
            return True
            
        except Exception as e:
            print(f"\n  {self.rojo(f'Error instalando Python: {e}')}")
            return False
    
    def instalar_dependencias(self):
        """Instala las dependencias de Python."""
        self.mostrar_progreso("Instalando dependencias...")
        
        try:
            # Actualizar pip
            subprocess.run(
                [str(PYTHON_EXE), "-m", "pip", "install", "--upgrade", "pip", "--quiet", "--no-warn-script-location"],
                capture_output=True,
                cwd=str(INSTALL_DIR)
            )
            
            total = len(DEPENDENCIAS)
            for i, dep in enumerate(DEPENDENCIAS, 1):
                porcentaje = int(i * 100 / total)
                self.mostrar_progreso(f"Instalando {dep}...", porcentaje)
                
                resultado = subprocess.run(
                    [str(PYTHON_EXE), "-m", "pip", "install", dep, "--quiet", "--no-warn-script-location"],
                    capture_output=True,
                    cwd=str(INSTALL_DIR)
                )
            
            print()  # Nueva línea
            self.mostrar_progreso("Dependencias instaladas correctamente ✓")
            return True
            
        except Exception as e:
            print(f"\n  {self.rojo(f'Error instalando dependencias: {e}')}")
            return False
    
    def crear_launcher_vbs(self):
        """Crea los archivos VBS para ejecución silenciosa."""
        if self.tipo_instalacion == "emisora":
            vbs_path = INSTALL_DIR / "launcher_emisora.vbs"
            bat_name = "ejecutar_emisora.bat"
        else:
            vbs_path = INSTALL_DIR / "launcher_receptora.vbs"
            bat_name = "ejecutar_receptora.bat"
        
        vbs_content = f'''Set WshShell = CreateObject("WScript.Shell")
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath
WshShell.Run Chr(34) & strPath & "\\{bat_name}" & Chr(34), 0, False
Set WshShell = Nothing
'''
        vbs_path.write_text(vbs_content)
        self.mostrar_progreso(f"Launcher creado: {vbs_path.name} ✓")
        return vbs_path
    
    def crear_accesos_directos(self):
        """Crea los accesos directos configurados."""
        if self.tipo_instalacion == "emisora":
            nombre_app = APP_NAME_EMISORA
            vbs_path = INSTALL_DIR / "launcher_emisora.vbs"
            icono_path = INSTALL_DIR / "icons" / "emisora.ico"
        else:
            nombre_app = APP_NAME_RECEPTORA
            vbs_path = INSTALL_DIR / "launcher_receptora.vbs"
            icono_path = INSTALL_DIR / "icons" / "receptora.ico"
        
        # Acceso en escritorio
        if self.crear_acceso_escritorio:
            escritorio = obtener_escritorio()
            if crear_acceso_directo_vbs(vbs_path, nombre_app, escritorio, f"Inicia {nombre_app}", icono_path):
                self.mostrar_progreso(f"Acceso directo creado en Escritorio ✓")
            else:
                self.mostrar_progreso(self.amarillo("No se pudo crear acceso en Escritorio"))
        
        # Acceso en menú inicio
        if self.crear_acceso_menu:
            menu = obtener_menu_inicio()
            carpeta_menu = menu / "Sistema Tickets IT"
            carpeta_menu.mkdir(parents=True, exist_ok=True)
            
            if crear_acceso_directo_vbs(vbs_path, nombre_app, carpeta_menu, f"Inicia {nombre_app}", icono_path):
                self.mostrar_progreso(f"Acceso directo creado en Menú Inicio ✓")
            else:
                self.mostrar_progreso(self.amarillo("No se pudo crear acceso en Menú Inicio"))
        
        # Inicio automático con Windows
        if self.iniciar_con_windows:
            startup = obtener_carpeta_startup()
            if crear_acceso_directo_vbs(vbs_path, nombre_app, startup, f"Inicia {nombre_app} automáticamente", icono_path):
                self.mostrar_progreso(f"Configurado para iniciar con Windows ✓")
            else:
                self.mostrar_progreso(self.amarillo("No se pudo configurar inicio automático"))
    
    def configurar_firewall(self):
        """Configura el firewall de Windows para permitir conexiones."""
        if not self.abrir_firewall:
            return
        
        self.mostrar_progreso("Configurando Firewall de Windows...")
        
        try:
            # Eliminar reglas anteriores si existen
            subprocess.run(
                ["netsh", "advfirewall", "firewall", "delete", "rule", "name=TicketsIT_Servidor"],
                capture_output=True
            )
            
            # Crear regla para permitir conexiones entrantes en el puerto 5555
            resultado = subprocess.run([
                "netsh", "advfirewall", "firewall", "add", "rule",
                "name=TicketsIT_Servidor",
                "dir=in",
                "action=allow",
                "protocol=TCP",
                "localport=5555",
                "enable=yes",
                "profile=any"
            ], capture_output=True)
            
            if resultado.returncode == 0:
                self.mostrar_progreso("Firewall configurado correctamente ✓")
            else:
                self.mostrar_progreso(self.amarillo("Ejecute como administrador para configurar el Firewall"))
                
        except Exception as e:
            self.mostrar_progreso(self.amarillo(f"No se pudo configurar Firewall: {e}"))
    
    def crear_desinstalador(self):
        """Crea un script de desinstalación."""
        desinstalar_bat = INSTALL_DIR / "desinstalar.bat"
        
        if self.tipo_instalacion == "emisora":
            nombre_app = APP_NAME_EMISORA
        else:
            nombre_app = APP_NAME_RECEPTORA
        
        contenido = f'''@echo off
chcp 65001 >nul 2>&1
title Desinstalador - {APP_NAME}

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              DESINSTALADOR - SISTEMA DE TICKETS            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo ¿Está seguro de que desea desinstalar {nombre_app}?
echo.
echo Esto eliminará:
echo   - Accesos directos del escritorio
echo   - Accesos directos del menú inicio
echo   - Configuración de inicio automático
echo.
echo Los archivos de datos (tickets, equipos) NO se eliminarán.
echo.
set /p confirmar="Escriba SI para confirmar: "

if /i "%confirmar%"=="SI" (
    echo.
    echo Eliminando accesos directos...
    
    del "%USERPROFILE%\\Desktop\\{nombre_app}.lnk" 2>nul
    del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Sistema Tickets IT\\{nombre_app}.lnk" 2>nul
    del "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Startup\\{nombre_app}.lnk" 2>nul
    rmdir "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs\\Sistema Tickets IT" 2>nul
    
    echo Eliminando reglas de firewall...
    netsh advfirewall firewall delete rule name=TicketsIT_Servidor 2>nul
    
    echo.
    echo ════════════════════════════════════════════════════════════
    echo   DESINSTALACIÓN COMPLETADA
    echo ════════════════════════════════════════════════════════════
    echo.
    echo Los archivos del programa permanecen en:
    echo {INSTALL_DIR}
    echo.
    echo Puede eliminarlos manualmente si lo desea.
) else (
    echo.
    echo Desinstalación cancelada.
)

echo.
pause
'''
        desinstalar_bat.write_text(contenido, encoding='utf-8')
        self.mostrar_progreso("Desinstalador creado ✓")
    
    def ejecutar_instalacion(self):
        """Ejecuta el proceso de instalación completo."""
        self.mostrar_banner()
        
        tipo = "EMISORA" if self.tipo_instalacion == "emisora" else "RECEPTORA"
        print(f"""
{self.cyan('═' * 60)}
{self.verde(f'  INSTALANDO: {tipo}')}
{self.cyan('═' * 60)}
""")
        
        pasos = [
            ("Instalando Python embebido...", self.instalar_python),
            ("Instalando dependencias...", self.instalar_dependencias),
            ("Creando launcher silencioso...", self.crear_launcher_vbs),
            ("Creando accesos directos...", self.crear_accesos_directos),
            ("Configurando firewall...", self.configurar_firewall),
            ("Creando desinstalador...", self.crear_desinstalador),
        ]
        
        # Para RECEPTORA, agregar paso de crear bases de datos
        if self.tipo_instalacion == "receptora":
            pasos.append(("Inicializando bases de datos...", self._inicializar_bases_datos))
        
        for descripcion, funcion in pasos:
            resultado = funcion()
            if resultado is False:
                print(f"\n  {self.rojo('La instalación falló en este paso.')}")
                input("\n  Presione Enter para salir...")
                return False
        
        # Mostrar resumen final
        self.mostrar_resumen_final()
        return True
    
    def _inicializar_bases_datos(self):
        """Inicializa las bases de datos Excel y archivos JSON si no existen."""
        try:
            import pandas as pd
            from datetime import datetime
            
            print(f"\n  {self.amarillo('→')} Verificando bases de datos...")
            
            # 1. Crear tickets_db.xlsx si no existe o está corrupto
            ruta_tickets = INSTALL_DIR / "tickets_db.xlsx"
            if not ruta_tickets.exists() or ruta_tickets.stat().st_size < 100:
                df_tickets = pd.DataFrame(columns=COLUMNAS_DB)
                df_tickets.to_excel(ruta_tickets, index=False, engine='openpyxl')
                print(f"  {self.verde('✓')} tickets_db.xlsx inicializado")
            else:
                try:
                    pd.read_excel(ruta_tickets, engine='openpyxl', nrows=0)
                    print(f"  {self.verde('✓')} tickets_db.xlsx verificado")
                except:
                    df_tickets = pd.DataFrame(columns=COLUMNAS_DB)
                    df_tickets.to_excel(ruta_tickets, index=False, engine='openpyxl')
                    print(f"  {self.verde('✓')} tickets_db.xlsx reparado")
            
            # 2. Crear tecnicos_db.xlsx si no existe o está corrupto
            ruta_tecnicos = INSTALL_DIR / "tecnicos_db.xlsx"
            if not ruta_tecnicos.exists() or ruta_tecnicos.stat().st_size < 100:
                tecnicos_iniciales = []
                for tec in TECNICOS_INICIALES:
                    tecnicos_iniciales.append({
                        "ID_TECNICO": tec["id"],
                        "NOMBRE": tec["nombre"],
                        "ESTADO": "Disponible",
                        "ESPECIALIDAD": tec["especialidad"],
                        "TICKETS_ATENDIDOS": 0,
                        "TICKET_ACTUAL": "",
                        "ULTIMA_ACTIVIDAD": datetime.now(),
                        "TELEFONO": tec["telefono"],
                        "EMAIL": tec["email"]
                    })
                df_tecnicos = pd.DataFrame(tecnicos_iniciales)
                df_tecnicos.to_excel(ruta_tecnicos, index=False, engine='openpyxl')
                print(f"  {self.verde('✓')} tecnicos_db.xlsx inicializado con técnicos")
            else:
                try:
                    pd.read_excel(ruta_tecnicos, engine='openpyxl', nrows=0)
                    print(f"  {self.verde('✓')} tecnicos_db.xlsx verificado")
                except:
                    tecnicos_iniciales = []
                    for tec in TECNICOS_INICIALES:
                        tecnicos_iniciales.append({
                            "ID_TECNICO": tec["id"],
                            "NOMBRE": tec["nombre"],
                            "ESTADO": "Disponible",
                            "ESPECIALIDAD": tec["especialidad"],
                            "TICKETS_ATENDIDOS": 0,
                            "TICKET_ACTUAL": "",
                            "ULTIMA_ACTIVIDAD": datetime.now(),
                            "TELEFONO": tec["telefono"],
                            "EMAIL": tec["email"]
                        })
                    df_tecnicos = pd.DataFrame(tecnicos_iniciales)
                    df_tecnicos.to_excel(ruta_tecnicos, index=False, engine='openpyxl')
                    print(f"  {self.verde('✓')} tecnicos_db.xlsx reparado")
            
            # 3. Crear equipos_db.xlsx si no existe o está corrupto
            ruta_equipos = INSTALL_DIR / "equipos_db.xlsx"
            if not ruta_equipos.exists() or ruta_equipos.stat().st_size < 100:
                df_equipos = pd.DataFrame(columns=COLUMNAS_EQUIPOS)
                df_equipos.to_excel(ruta_equipos, index=False, engine='openpyxl')
                print(f"  {self.verde('✓')} equipos_db.xlsx inicializado")
            else:
                try:
                    pd.read_excel(ruta_equipos, engine='openpyxl', nrows=0)
                    print(f"  {self.verde('✓')} equipos_db.xlsx verificado")
                except:
                    df_equipos = pd.DataFrame(columns=COLUMNAS_EQUIPOS)
                    df_equipos.to_excel(ruta_equipos, index=False, engine='openpyxl')
                    print(f"  {self.verde('✓')} equipos_db.xlsx reparado")
            
            # 4. Crear archivos JSON si no existen
            archivos_json = {
                "equipos_aprobados.json": {"aprobados": [], "rechazados": []},
                "solicitudes_enlace.json": [],
                "notificaciones_estado.json": {}
            }
            
            for archivo, contenido_default in archivos_json.items():
                ruta = INSTALL_DIR / archivo
                if not ruta.exists():
                    with open(ruta, 'w', encoding='utf-8') as f:
                        json.dump(contenido_default, f, indent=2, ensure_ascii=False)
                    print(f"  {self.verde('✓')} {archivo} creado")
                else:
                    print(f"  {self.verde('✓')} {archivo} verificado")
            
            print(f"\n  {self.verde('✓')} Bases de datos listas")
            return True
            
        except ImportError as e:
            print(f"  {self.amarillo('!')} pandas no disponible - las bases de datos se crearán al iniciar")
            return True
        except Exception as e:
            print(f"  {self.amarillo('!')} Error inicializando bases de datos: {e}")
            print(f"  {self.amarillo('!')} Las bases de datos se crearán al iniciar la aplicación")
            return True  # No fallar la instalación por esto
    
    def mostrar_resumen_final(self):
        """Muestra el resumen de la instalación."""
        tipo = "EMISORA" if self.tipo_instalacion == "emisora" else "RECEPTORA"
        
        print(f"""

{self.cyan('╔══════════════════════════════════════════════════════════════════╗')}
{self.cyan('║')}                                                                  {self.cyan('║')}
{self.cyan('║')}           {self.verde('✓ INSTALACIÓN COMPLETADA EXITOSAMENTE')}               {self.cyan('║')}
{self.cyan('║')}                                                                  {self.cyan('║')}
{self.cyan('╚══════════════════════════════════════════════════════════════════╝')}

{self.amarillo('RESUMEN DE INSTALACIÓN:')}

  {self.verde('→')} Tipo instalado: {self.cyan(tipo)}
  {self.verde('→')} Ubicación: {INSTALL_DIR}
""")
        
        if self.crear_acceso_escritorio:
            print(f"  {self.verde('→')} Acceso directo creado en el Escritorio")
        
        if self.crear_acceso_menu:
            print(f"  {self.verde('→')} Acceso directo creado en Menú Inicio")
        
        if self.iniciar_con_windows:
            print(f"  {self.verde('→')} Se iniciará automáticamente con Windows")
        
        if self.abrir_firewall:
            print(f"  {self.verde('→')} Firewall configurado (puerto 5555)")
        
        if self.tipo_instalacion == "emisora":
            print(f"""
{self.amarillo('CÓMO USAR:')}

  1. Haga doble clic en el acceso directo del Escritorio
  2. La aplicación buscará automáticamente el servidor IT
  3. Si no lo encuentra, puede configurar la IP manualmente
  4. ¡Listo para crear tickets de soporte!

{self.cyan('NOTA:')} La aplicación se ejecuta en segundo plano (sin ventana CMD).
        Para cerrarla, use el Administrador de tareas.
""")
        else:
            print(f"""
{self.amarillo('CÓMO USAR:')}

  1. Haga doble clic en el acceso directo del Escritorio
  2. El panel de IT se iniciará con el servidor activo
  3. Los equipos emisores se conectarán automáticamente
  4. ¡Listo para recibir y gestionar tickets!

{self.cyan('NOTA:')} Asegúrese de que el firewall esté configurado correctamente
        para recibir conexiones en el puerto 5555.
""")
        
        input(f"\n  {self.verde('Presione Enter para finalizar...')}")
    
    def ejecutar(self):
        """Punto de entrada principal del instalador."""
        while True:
            self.mostrar_banner()
            self.detectar_instalaciones()
            self.mostrar_menu_principal()
            
            opcion = input("  Seleccione una opción: ").strip()
            
            if opcion == "0":
                print(f"\n  {self.amarillo('¡Hasta luego!')}")
                break
            elif opcion == "1":
                # Instalación nueva
                if not self.seleccionar_tipo():
                    continue
                if not self.configurar_opciones():
                    continue
                self.ejecutar_instalacion()
                break
            elif opcion == "2":
                # Desinstalar
                self.ejecutar_desinstalacion()
            elif opcion == "3":
                # Reinstalar
                self.ejecutar_reinstalacion()
                break
            elif opcion == "4":
                # Formatear
                self.ejecutar_formateo()
            else:
                print(f"\n  {self.rojo('Opción no válida.')}")
                input(f"  {self.verde('Presione Enter para continuar...')}")


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    instalador = InstaladorConsola()
    instalador.ejecutar()
