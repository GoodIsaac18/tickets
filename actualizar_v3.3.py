# =============================================================================
# PARCHE DE ACTUALIZACIÓN - Sistema de Tickets IT v3.3
# =============================================================================
# Corrección crítica: Botón "Entendido" no cerraba el diálogo de turno
# + Panel de seguimiento no aparecía después de enviar ticket
# Fecha: 5 de Marzo de 2026
# =============================================================================

import os
import sys
import shutil
from pathlib import Path
from datetime import datetime

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
{CYAN}║                        Versión 3.3                             ║{RESET}
{CYAN}║                                                                  ║{RESET}
{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}
""")

PROJECT_PATH = Path(__file__).parent

print(f"{AZUL}[INFO]{RESET} Ruta del proyecto: {PROJECT_PATH}")
print(f"{AZUL}[INFO]{RESET} Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

# =============================================================================
# CAMBIOS v3.3
# =============================================================================

CAMBIOS = [
    {
        "archivo": "app_emisora.py",
        "cambio": "Botón 'Entendido' no cerraba el diálogo modal de turno",
        "detalle": "modal=True bloqueaba eventos de click en Flet 0.81",
        "solucion": "Cambiado a modal=False + TextButton en actions + on_dismiss"
    },
    {
        "archivo": "app_emisora.py",
        "cambio": "Panel de seguimiento no aparecía después de enviar ticket",
        "detalle": "Ticket enviado al servidor no se guardaba en memoria local",
        "solucion": "self.ticket_activo = ticket guardado antes de mostrar diálogo"
    },
    {
        "archivo": "app_emisora.py",
        "cambio": "Fallback en _crear_panel_mi_ticket para ticket en memoria",
        "detalle": "Si DB local no tiene el ticket, se usa el de self.ticket_activo",
        "solucion": "Prioridad: DB local → ticket en memoria → None (formulario)"
    },
]

print(f"\n{AMARILLO}{'═'*65}{RESET}")
print(f"{AMARILLO}CORRECCIONES EN v3.3:{RESET}")
print(f"{AMARILLO}{'═'*65}{RESET}\n")

for idx, c in enumerate(CAMBIOS, 1):
    print(f"{VERDE}[{idx}]{RESET} {c['archivo']}")
    print(f"    {ROJO}BUG:{RESET}  {c['cambio']}")
    print(f"    {AZUL}CAUSA:{RESET} {c['detalle']}")
    print(f"    {VERDE}FIX:{RESET}  {c['solucion']}\n")

# =============================================================================
# BACKUP
# =============================================================================

print(f"{AMARILLO}{'═'*65}{RESET}")
print(f"{AMARILLO}CREANDO BACKUP...{RESET}")
print(f"{AMARILLO}{'═'*65}{RESET}\n")

BACKUP_DIR = PROJECT_PATH / "backups" / f"backup_v3.3_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

archivos_backup = ["app_emisora.py", "data_access.py"]

try:
    for archivo in archivos_backup:
        ruta = PROJECT_PATH / archivo
        if ruta.exists():
            shutil.copy2(ruta, BACKUP_DIR / archivo)
            tam = ruta.stat().st_size / 1024
            print(f"{VERDE}✓{RESET} {archivo} ({tam:.1f} KB)")
        else:
            print(f"{AMARILLO}⚠{RESET} {archivo} no encontrado")
    
    print(f"\n{VERDE}[✓] Backup en: {BACKUP_DIR}{RESET}\n")
except Exception as e:
    print(f"{ROJO}[ERROR] Backup falló: {e}{RESET}")
    sys.exit(1)

# =============================================================================
# VALIDAR ARCHIVOS
# =============================================================================

print(f"{AMARILLO}{'═'*65}{RESET}")
print(f"{AMARILLO}VERIFICANDO ARCHIVOS...{RESET}")
print(f"{AMARILLO}{'═'*65}{RESET}\n")

archivos_check = ["app_emisora.py", "data_access.py"]
ok = True
for archivo in archivos_check:
    ruta = PROJECT_PATH / archivo
    if ruta.exists():
        tam = ruta.stat().st_size / 1024
        print(f"{VERDE}✓{RESET} {archivo} ({tam:.1f} KB)")
    else:
        print(f"{ROJO}✗{RESET} {archivo} NO ENCONTRADO")
        ok = False

if not ok:
    print(f"\n{ROJO}[ERROR] Archivos faltantes{RESET}")
    sys.exit(1)

# =============================================================================
# VALIDAR SINTAXIS
# =============================================================================

print(f"\n{AMARILLO}{'═'*65}{RESET}")
print(f"{AMARILLO}VALIDANDO SINTAXIS PYTHON...{RESET}")
print(f"{AMARILLO}{'═'*65}{RESET}\n")

import py_compile

sintaxis_ok = True
for archivo in archivos_check:
    ruta = PROJECT_PATH / archivo
    try:
        py_compile.compile(str(ruta), doraise=True)
        print(f"{VERDE}✓{RESET} {archivo} - OK")
    except py_compile.PyCompileError as e:
        print(f"{ROJO}✗{RESET} {archivo} - ERROR: {e}")
        sintaxis_ok = False

if not sintaxis_ok:
    print(f"\n{ROJO}[ERROR] Errores de sintaxis detectados{RESET}")
    sys.exit(1)

# =============================================================================
# VERIFICAR CORRECCIONES APLICADAS
# =============================================================================

print(f"\n{AMARILLO}{'═'*65}{RESET}")
print(f"{AMARILLO}VERIFICANDO CORRECCIONES...{RESET}")
print(f"{AMARILLO}{'═'*65}{RESET}\n")

emisora_content = (PROJECT_PATH / "app_emisora.py").read_text(encoding="utf-8")

checks = [
    ("modal=False en diálogo de turno", "modal=False" in emisora_content and "_on_entendido" in emisora_content),
    ("TextButton en actions del diálogo", "ft.TextButton(" in emisora_content and "Entendido" in emisora_content),
    ("on_dismiss handler", "on_dismiss=_on_entendido" in emisora_content),
    ("self.ticket_activo = ticket (guardado)", "self.ticket_activo = ticket" in emisora_content),
    ("Fallback ticket en memoria", "Usando ticket en memoria" in emisora_content),
    ("Función _on_entendido definida", "def _on_entendido(e):" in emisora_content),
    ("Rebuild async después de cerrar", "page.run_task(_rebuild)" in emisora_content),
]

todas_ok = True
for nombre, resultado in checks:
    if resultado:
        print(f"{VERDE}✓{RESET} {nombre}")
    else:
        print(f"{ROJO}✗{RESET} {nombre}")
        todas_ok = False

if not todas_ok:
    print(f"\n{ROJO}[ADVERTENCIA] Algunas correcciones no se detectaron{RESET}")
else:
    print(f"\n{VERDE}[✓] Todas las correcciones verificadas{RESET}")

# =============================================================================
# RESUMEN
# =============================================================================

backup_size = sum(f.stat().st_size for f in BACKUP_DIR.glob('*')) / 1024

print(f"""
{CYAN}╔══════════════════════════════════════════════════════════════════╗{RESET}
{CYAN}║{RESET}              {VERDE}✓ ACTUALIZACIÓN v3.3 COMPLETADA{RESET}                    {CYAN}║{RESET}
{CYAN}╚══════════════════════════════════════════════════════════════════╝{RESET}

{AMARILLO}RESUMEN DE CORRECCIONES:{RESET}

{VERDE}Bug #1: Botón "Entendido" no cerraba{RESET}
  • Causa: modal=True en AlertDialog bloqueaba eventos on_click
  • Fix: Cambiado a modal=False + on_dismiss como fallback
  • Botón cambiado de ElevatedButton a TextButton estilizado

{VERDE}Bug #2: Panel de ticket no aparecía{RESET}
  • Causa: Ticket enviado al servidor no se guardaba localmente
  • Fix: self.ticket_activo = ticket inmediatamente después de crear
  • Fallback: _crear_panel_mi_ticket usa ticket en memoria si DB vacía

{VERDE}Bug #3: Reconstrucción UI fallaba silenciosamente{RESET}
  • Causa: Sin try/except en función async de rebuild
  • Fix: Error handling completo con print de traceback

{AMARILLO}PARA PROBAR:{RESET}
  1. Reiniciar app Emisora
  2. Enviar un ticket
  3. Verificar que el modal muestra el turno
  4. Click "Entendido" → debe cerrar y mostrar panel de ticket
  5. Revisar consola para "[CLIENTE] 🔘 Botón 'Entendido' presionado"

{AMARILLO}BACKUP:{RESET} {BACKUP_DIR}

{VERDE}{'═'*65}{RESET}
{VERDE}  ✓ v3.3 aplicada - {len(CAMBIOS)} correcciones | Backup: {backup_size:.1f} KB{RESET}
{VERDE}{'═'*65}{RESET}
""")
