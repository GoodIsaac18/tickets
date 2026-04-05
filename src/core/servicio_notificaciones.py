# =============================================================================
# SERVICIO EN SEGUNDO PLANO - servicio_notificaciones.py
# =============================================================================
# Ejecuta el servidor HTTP y el sistema de notificaciones en segundo plano
# Funciona incluso cuando las aplicaciones no están abiertas
# =============================================================================

import sys
import os
import time
import threading
import signal
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Agregar directorio actual al path
sys.path.insert(0, str(PROJECT_ROOT))

# Importar módulos necesarios
from servidor_red import (
    iniciar_servidor_http,
    detener_servidor_http,
    PUERTO_HTTP,
    NOTIFICACIONES_DISPONIBLES
)

# Intentar importar notificaciones
try:
    from notificaciones_windows import (
        iniciar_servicio_notificaciones,
        detener_servicio_notificaciones,
        mostrar_notificacion_windows,
        WINOTIFY_DISPONIBLE
    )
except ImportError:
    WINOTIFY_DISPONIBLE = False


# =============================================================================
# CONFIGURACIÓN
# =============================================================================

SERVICIO_ACTIVO = False


def manejar_cierre(signum, frame):
    """Maneja señales de cierre."""
    global SERVICIO_ACTIVO
    print("\n[SERVICIO] Deteniendo...")
    SERVICIO_ACTIVO = False


def iniciar_servicio():
    """Inicia el servicio completo en segundo plano."""
    global SERVICIO_ACTIVO
    SERVICIO_ACTIVO = True
    
    print("=" * 60)
    print("  SERVICIO DE SOPORTE TÉCNICO - Sistema de Tickets IT")
    print("=" * 60)
    print()
    
    # Verificar notificaciones
    if WINOTIFY_DISPONIBLE:
        print("[OK] Sistema de notificaciones Windows disponible")
    else:
        print("[!] Sistema de notificaciones no disponible")
        print("    Instala con: pip install winotify")
    
    print()
    
    # Iniciar servidor HTTP
    print(f"[SERVIDOR] Iniciando en puerto {PUERTO_HTTP}...")
    if iniciar_servidor_http():
        print(f"[SERVIDOR] ✅ Servidor HTTP activo en puerto {PUERTO_HTTP}")
    else:
        print("[SERVIDOR] ❌ Error al iniciar servidor HTTP")
        return False
    
    # Iniciar servicio de notificaciones
    if WINOTIFY_DISPONIBLE:
        print("[NOTIF] Iniciando servicio de notificaciones...")
        iniciar_servicio_notificaciones()
        print("[NOTIF] ✅ Servicio de notificaciones activo")
        
        # Mostrar notificación de inicio
        mostrar_notificacion_windows(
            titulo="🟢 Servicio Activo",
            mensaje="El sistema de tickets está funcionando en segundo plano",
            tipo="exito",
            duracion="short"
        )
    
    print()
    print("-" * 60)
    print("Servicio ejecutándose en segundo plano")
    print("Presiona Ctrl+C para detener")
    print("-" * 60)
    print()
    
    # Registrar manejador de señales
    signal.signal(signal.SIGINT, manejar_cierre)
    signal.signal(signal.SIGTERM, manejar_cierre)
    
    # Mantener servicio activo
    try:
        while SERVICIO_ACTIVO:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    
    # Detener servicios
    print("\n[SERVICIO] Deteniendo servicios...")
    
    if WINOTIFY_DISPONIBLE:
        detener_servicio_notificaciones()
    
    detener_servidor_http()
    
    print("[SERVICIO] ✅ Servicio detenido correctamente")
    return True


def crear_tarea_programada_windows():
    """Crea una tarea programada en Windows para iniciar con el sistema."""
    print("\n" + "=" * 60)
    print("CREAR TAREA PROGRAMADA DE WINDOWS")
    print("=" * 60)
    print()
    print("Para que el servicio se inicie automáticamente con Windows,")
    print("ejecuta este comando en PowerShell como Administrador:")
    print()
    
    ruta_script = Path(__file__).absolute()
    ruta_python = sys.executable
    
    comando = f'''$Action = New-ScheduledTaskAction -Execute "{ruta_python}" -Argument "{ruta_script}"
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Principal = New-ScheduledTaskPrincipal -UserId "$env:USERNAME" -LogonType Interactive -RunLevel Highest
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "SoporteTecnico_Servicio" -Action $Action -Trigger $Trigger -Principal $Principal -Settings $Settings -Description "Servicio de notificaciones de tickets IT"'''
    
    print(comando)
    print()
    print("=" * 60)


def crear_acceso_directo_inicio():
    """Crea un acceso directo en la carpeta de inicio de Windows."""
    try:
        import winshell
        from win32com.client import Dispatch
        
        ruta_script = str(Path(__file__).absolute())
        ruta_python = sys.executable
        carpeta_inicio = winshell.startup()
        
        acceso = os.path.join(carpeta_inicio, "SoporteTecnico_Servicio.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortcut(acceso)
        shortcut.TargetPath = ruta_python
        shortcut.Arguments = f'"{ruta_script}"'
        shortcut.WorkingDirectory = str(PROJECT_ROOT)
        shortcut.Description = "Servicio de Soporte Técnico IT"
        shortcut.save()
        
        print(f"[OK] Acceso directo creado en: {acceso}")
        return True
        
    except ImportError:
        print("[!] Para crear acceso directo automático, instala:")
        print("    pip install winshell pywin32")
        return False
    except Exception as e:
        print(f"[ERROR] No se pudo crear acceso directo: {e}")
        return False


# =============================================================================
# PUNTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        
        if arg in ["--install", "-i", "install"]:
            crear_tarea_programada_windows()
        
        elif arg in ["--shortcut", "-s", "shortcut"]:
            crear_acceso_directo_inicio()
        
        elif arg in ["--help", "-h", "help"]:
            print("Uso: servicio_notificaciones.py [opción]")
            print()
            print("Opciones:")
            print("  (sin argumentos)  Inicia el servicio")
            print("  --install, -i     Muestra comando para crear tarea programada")
            print("  --shortcut, -s    Crea acceso directo en carpeta de inicio")
            print("  --help, -h        Muestra esta ayuda")
        
        else:
            print(f"Opción desconocida: {arg}")
            print("Usa --help para ver opciones disponibles")
    
    else:
        # Iniciar servicio
        iniciar_servicio()
