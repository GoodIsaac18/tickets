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
from pathlib import Path

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
{self.cyan('║')}                      {self.amarillo('INSTALADOR v2.0')}                           {self.cyan('║')}
{self.cyan('║')}                                                                  {self.cyan('║')}
{self.cyan('╚══════════════════════════════════════════════════════════════════╝')}
"""
        print(banner)
    
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
        
        for descripcion, funcion in pasos:
            resultado = funcion()
            if resultado is False:
                print(f"\n  {self.rojo('La instalación falló en este paso.')}")
                input("\n  Presione Enter para salir...")
                return False
        
        # Mostrar resumen final
        self.mostrar_resumen_final()
        return True
    
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
        # Seleccionar tipo de instalación
        if not self.seleccionar_tipo():
            print(f"\n  {self.amarillo('Instalación cancelada.')}")
            return
        
        # Configurar opciones
        if not self.configurar_opciones():
            print(f"\n  {self.amarillo('Instalación cancelada.')}")
            return
        
        # Ejecutar instalación
        self.ejecutar_instalacion()


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    instalador = InstaladorConsola()
    instalador.ejecutar()
