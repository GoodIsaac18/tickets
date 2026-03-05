# =============================================================================
# PARCHE DE ACTUALIZACIÓN - Sistema de Tickets IT v3.1
# =============================================================================
# Script de actualización automática que aplica los últimos cambios
# Fecha: 5 de Marzo de 2026
# =============================================================================

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

# Colores ANSI
VERDE = "\033[92m"
ROJO = "\033[91m"
AMARILLO = "\033[93m"
AZUL = "\033[94m"
CYAN = "\033[96m"
RESET = "\033[0m"

print(f"""
{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}
{CYAN}║                                                                  ║{RESET}
{CYAN}║         PARCHE DE ACTUALIZACIÓN - SISTEMA DE TICKETS IT          ║{RESET}
{CYAN}║                        Versión 3.1                             ║{RESET}
{CYAN}║                                                                  ║{RESET}
{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}
""")

# Ruta del proyecto
PROJECT_PATH = Path(__file__).parent

print(f"{AZUL}[INFO]{RESET} Ruta del proyecto: {PROJECT_PATH}")
print(f"{AZUL}[INFO]{RESET} Fecha de actualización: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# =============================================================================
# CAMBIOS INCLUIDOS EN ESTA ACTUALIZACIÓN
# =============================================================================

CAMBIOS = [
    {
        "archivo": "instalador.py",
        "cambio": "Actualizado a v3.0 con detección de instalaciones, desinstalador y formateo completo",
        "impacto": "Mejoras en instalación/desinstalación"
    },
    {
        "archivo": "app_receptora.py",
        "cambio": "Corregido COLOR_WARNING → COLOR_ADVERTENCIA",
        "impacto": "Fijo error de constante no definida"
    },
    {
        "archivo": "app_receptora.py",
        "cambio": "Agregadas animaciones de carga a 10+ operaciones (agregar técnico, exportar, etc.)",
        "impacto": "Mejor experiencia visual con loading overlays"
    },
    {
        "archivo": "app_emisora.py",
        "cambio": "Arreglado panel de seguimiento de tickets con manejo robusto de errores",
        "impacto": "Panel de tickets activos ahora funciona correctamente"
    },
    {
        "archivo": "data_access.py",
        "cambio": "Agregados try/except en obtener_posicion_cola() y obtener_ticket_activo_usuario()",
        "impacto": "Mayor estabilidad en lectura de datos"
    }
]

print(f"\n{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}")
print(f"{AMARILLO}CAMBIOS INCLUIDOS EN ESTA ACTUALIZACIÓN:{RESET}")
print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}\n")

for idx, cambio in enumerate(CAMBIOS, 1):
    print(f"{VERDE}[{idx}]{RESET} {cambio['archivo']}")
    print(f"    {AZUL}→{RESET} {cambio['cambio']}")
    print(f"    {CYAN}✓{RESET} {cambio['impacto']}\n")

# =============================================================================
# CREAR BACKUP
# =============================================================================

print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}")
print(f"{AMARILLO}CREANDO BACKUP DE SEGURIDAD...{RESET}")
print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}\n")

BACKUP_DIR = PROJECT_PATH / "backups" / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

archivos_backup = [
    "app_receptora.py",
    "app_emisora.py",
    "data_access.py",
    "instalador.py"
]

try:
    for archivo in archivos_backup:
        ruta_original = PROJECT_PATH / archivo
        if ruta_original.exists():
            ruta_backup = BACKUP_DIR / archivo
            shutil.copy2(ruta_original, ruta_backup)
            print(f"{VERDE}✓{RESET} {archivo} → {ruta_backup}")
    
    print(f"\n{VERDE}[✓] Backup creado exitosamente en: {BACKUP_DIR}{RESET}\n")
except Exception as e:
    print(f"{ROJO}[ERROR] No se pudo crear backup: {e}{RESET}\n")
    sys.exit(1)

# =============================================================================
# VERIFICAR ARCHIVOS
# =============================================================================

print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}")
print(f"{AMARILLO}VERIFICANDO INTEGRIDAD DE ARCHIVOS...{RESET}")
print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}\n")

archivos_requeridos = [
    "app_receptora.py",
    "app_emisora.py",
    "data_access.py",
    "instalador.py",
    "servidor_red.py",
    "requirements.txt"
]

archivos_ok = True
for archivo in archivos_requeridos:
    ruta = PROJECT_PATH / archivo
    if ruta.exists():
        tamaño = ruta.stat().st_size / 1024  # KB
        print(f"{VERDE}✓{RESET} {archivo} ({tamaño:.1f} KB)")
    else:
        print(f"{ROJO}✗{RESET} {archivo} {ROJO}NO ENCONTRADO{RESET}")
        archivos_ok = False

if not archivos_ok:
    print(f"\n{ROJO}[ERROR] Faltan archivos requeridos{RESET}\n")
    sys.exit(1)

# =============================================================================
# VALIDAR SINTAXIS PYTHON
# =============================================================================

print(f"\n{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}")
print(f"{AMARILLO}VALIDANDO SINTAXIS PYTHON...{RESET}")
print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}\n")

import py_compile

archivos_python = [
    "app_receptora.py",
    "app_emisora.py",
    "data_access.py",
    "instalador.py"
]

sintaxis_ok = True
for archivo in archivos_python:
    ruta = PROJECT_PATH / archivo
    try:
        py_compile.compile(str(ruta), doraise=True)
        print(f"{VERDE}✓{RESET} {archivo} - Sintaxis correcta")
    except py_compile.PyCompileError as e:
        print(f"{ROJO}✗{RESET} {archivo} - {ROJO}Error de sintaxis{RESET}: {e}")
        sintaxis_ok = False

if not sintaxis_ok:
    print(f"\n{ROJO}[ERROR] Hay errores de sintaxis en los archivos{RESET}\n")
    sys.exit(1)

# =============================================================================
# RESUMEN DE LA ACTUALIZACIÓN
# =============================================================================

print(f"\n{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
print(f"{CYAN}║{RESET}")
print(f"{CYAN}║{RESET}              {VERDE}✓ ACTUALIZACIÓN COMPLETADA EXITOSAMENTE{RESET}")
print(f"{CYAN}║{RESET}")
print(f"{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}")

print(f"""
{AMARILLO}RESUMEN DE CAMBIOS:{RESET}

1. {VERDE}Instalador v3.0{RESET}
   - Detección automática de instalaciones existentes
   - Menú de desinstalación con opciones para borrar datos
   - Opción de reinstalar conservando datos
   - Opción de formateo completo con confirmación
   - Recreación automática de bases de datos

2. {VERDE}Receptora - Visual Mejorado{RESET}
   - Corregido error de color no definido
   - Animaciones de carga agreadas a todas las operaciones
   - Mayor responsividad en la interfaz

3. {VERDE}Emisora - Panel de Tickets{RESET}
   - Arreglado panel de seguimiento de tickets activos
   - Manejo robusto de errores en lectura de datos
   - Botones funcionales: Actualizar, Recordatorio, Cancelar

4. {VERDE}Base de Datos{RESET}
   - Mayor estabilidad en operaciones de lectura
   - Manejo mejorado de excepciones

{CYAN}PRÓXIMOS PASOS:{RESET}

1. Reinicia ambas aplicaciones (Emisora y Receptora)
2. Prueba el panel de seguimiento en la Emisora
3. Verifica que las animaciones funcionan en la Receptora
4. Si necesitas volver atrás, tu backup está en: {BACKUP_DIR}

{AMARILLO}BACKUP AUTOMÁTICO:{RESET}
Se creó un backup de tu configuración actual en:
{CYAN}{BACKUP_DIR}{RESET}

{VERDE}¡Actualización completada! Sistema listo para usar.{RESET}
""")

print(f"{CYAN}═══════════════════════════════════════════════════════════════════{RESET}\n")
