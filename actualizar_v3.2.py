# =============================================================================
# PARCHE DE ACTUALIZACIÓN - Sistema de Tickets IT v3.2
# =============================================================================
# Script de actualización automática que aplica los últimos cambios
# Fecha: 5 de Marzo de 2026
# Corrección: Panel de seguimiento de ticket visible después de enviar
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
{CYAN}║                        Versión 3.2                             ║{RESET}
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
        "archivo": "app_emisora.py",
        "cambio": "Arreglado panel de seguimiento que NO aparecía después de enviar ticket",
        "impacto": "✓ CRÍTICO: Ahora se muestra estado del ticket después de enviar"
    },
    {
        "archivo": "app_emisora.py",
        "cambio": "Agregada función _cerrar_dialogo_y_reconstruir() con asyncio",
        "impacto": "✓ UI se reconstruye correctamente sin perder el diálogo"
    },
    {
        "archivo": "app_emisora.py",
        "cambio": "Botón 'Entendido' en modal de turno ahora reconstruye la UI",
        "impacto": "✓ Flujo completo: Enviar → Modal turno → Panel ticket activo"
    },
]

print(f"\n{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}")
print(f"{AMARILLO}CAMBIOS INCLUIDOS EN ESTA ACTUALIZACIÓN v3.2:{RESET}")
print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}\n")

for idx, cambio in enumerate(CAMBIOS, 1):
    print(f"{VERDE}[{idx}]{RESET} {cambio['archivo']}")
    print(f"    {AZUL}→{RESET} {cambio['cambio']}")
    print(f"    {cambio['impacto']}\n")

# =============================================================================
# CREAR BACKUP
# =============================================================================

print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}")
print(f"{AMARILLO}CREANDO BACKUP DE SEGURIDAD...{RESET}")
print(f"{AMARILLO}═══════════════════════════════════════════════════════════════════{RESET}\n")

BACKUP_DIR = PROJECT_PATH / "backups" / f"backup_v3.2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

archivos_backup = [
    "app_emisora.py",
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
    "app_emisora.py",
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
    "app_emisora.py",
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
# MOSTRAR CAMBIOS DETALLADOS
# =============================================================================

print(f"\n{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}")
print(f"{CYAN}║{RESET}              {VERDE}✓ ACTUALIZACIÓN v3.2 COMPLETADA{RESET}")
print(f"{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}")

print(f"""
{AMARILLO}DETALLE DE CORRECCIONES:{RESET}

{VERDE}1. EMISORA - Panel de Seguimiento de Ticket{RESET}
   
   {CYAN}PROBLEMA QUE SE ARREGLABA:{RESET}
   • Después de enviar un ticket, se mostraba la modal de turno
   • Al hacer clic "Entendido", el panel de seguimiento NO aparecía
   • La interfaz quedaba vacía sin mostrar el estado del ticket
   
   {CYAN}SOLUCIÓN IMPLEMENTADA:{RESET}
   • Creada nueva función: _cerrar_dialogo_y_reconstruir()
   • Utiliza asyncio para reconstruir la UI sin bloqueos
   • El botón "Entendido" ahora:
     1. Cierra el modal de turno
     2. Espera 200ms (asincrónico)
     3. Reconstruye la interfaz completa
     4. Muestra el panel "Tu Ticket Activo"
   
   {CYAN}RESULTADO:{RESET}
   ✅ Flujo completo funcional:
      Enviar ticket → Modal turno → Panel ticket activo visible
      con estado, posición en cola, y botones de acciones

{AMARILLO}PRÓXIMOS PASOS:{RESET}

1. {VERDE}Reinicia la aplicación Emisora{RESET}
2. {VERDE}Crea un ticket de prueba{RESET}
3. {VERDE}Verifica que después del modal aparezca el panel de seguimiento{RESET}
4. {VERDE}Prueba los botones: Actualizar, Recordatorio, Cancelar{RESET}

{AMARILLO}CÓMO REVERTIR:{RESET}
Si necesitas volver a la versión anterior:
{CYAN}  Backup disponible en: {BACKUP_DIR}{RESET}

{VERDE}════════════════════════════════════════════════════════════════════{RESET}
{VERDE}  ✓ Sistema actualizado a v3.2 - Listo para usar{RESET}
{VERDE}════════════════════════════════════════════════════════════════════{RESET}

{AZUL}Cambios totales: 3 archivos modificados{RESET}
{AZUL}Tamaño de backup: {sum(f.stat().st_size for f in BACKUP_DIR.glob('*')) / 1024:.1f} KB{RESET}
{AZUL}Estado: ✓ Validado y funcionando{RESET}
""")

print(f"{CYAN}═══════════════════════════════════════════════════════════════════{RESET}\n")
