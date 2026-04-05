#!/usr/bin/env python3
# =============================================================================
# SCRIPT DE INICIALIZACIÓN DE BASE DE DATOS (SQLite v5.0.0)
# =============================================================================
# Resetea y valida tickets.db. Úsalo si tienes problemas al iniciar la app.
#
# Uso:
#   python init_database.py          # Verifica / crea si no existe
#   python init_database.py --reset  # Borra y recrea (PIERDE DATOS)
# =============================================================================

import sqlite3
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = RUNTIME_DIR / "tickets.db"

TECNICOS_INICIALES = [
    {"id": "TEC001", "nombre": "Carlos Rodriguez",  "especialidad": "Hardware/Red",
     "telefono": "ext. 101", "email": "carlos.rodriguez@empresa.com"},
    {"id": "TEC002", "nombre": "Maria Garcia",      "especialidad": "Software/Accesos",
     "telefono": "ext. 102", "email": "maria.garcia@empresa.com"},
    {"id": "TEC003", "nombre": "Luis Hernandez",    "especialidad": "Redes/Seguridad",
     "telefono": "ext. 103", "email": "luis.hernandez@empresa.com"},
]


def crear_base_datos(borrar_existente: bool = False):
    """Crea o verifica tickets.db con todas las tablas necesarias."""
    print(f"\n  DB SQLite: {DB_PATH}")

    if borrar_existente and DB_PATH.exists():
        DB_PATH.unlink(missing_ok=True)
        for ext in (".db-wal", ".db-shm"):
            path_wal = DB_PATH.parent / (DB_PATH.name + ext)
            path_wal.unlink(missing_ok=True)
        print("  Archivo existente eliminado.")

    conn = sqlite3.connect(str(DB_PATH), isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ID_TICKET       TEXT PRIMARY KEY,
            TURNO           INTEGER DEFAULT 0,
            FECHA_APERTURA  TEXT,
            USUARIO_AD      TEXT,
            HOSTNAME        TEXT,
            MAC_ADDRESS     TEXT,
            CATEGORIA       TEXT,
            PRIORIDAD       TEXT DEFAULT 'Media',
            DESCRIPCION     TEXT,
            ESTADO          TEXT DEFAULT 'Abierto',
            TECNICO_ASIGNADO TEXT DEFAULT '',
            NOTAS_RESOLUCION TEXT DEFAULT '',
            HISTORIAL       TEXT DEFAULT '',
            FECHA_CIERRE    TEXT,
            TIEMPO_ESTIMADO INTEGER DEFAULT 0
        )""")
    print("  Tabla tickets:   OK")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tecnicos (
            ID_TECNICO       TEXT PRIMARY KEY,
            NOMBRE           TEXT,
            ESTADO           TEXT DEFAULT 'Disponible',
            ESPECIALIDAD     TEXT,
            TICKETS_ATENDIDOS INTEGER DEFAULT 0,
            TICKET_ACTUAL    TEXT DEFAULT '',
            ULTIMA_ACTIVIDAD TEXT,
            TELEFONO         TEXT DEFAULT '',
            EMAIL            TEXT DEFAULT ''
        )""")
    print("  Tabla tecnicos:  OK")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS equipos (
            MAC_ADDRESS      TEXT PRIMARY KEY,
            NOMBRE_EQUIPO    TEXT,
            HOSTNAME         TEXT,
            USUARIO_ASIGNADO TEXT,
            GRUPO            TEXT DEFAULT 'Sin Asignar',
            UBICACION        TEXT DEFAULT '',
            MARCA            TEXT DEFAULT '',
            MODELO           TEXT DEFAULT '',
            NUMERO_SERIE     TEXT DEFAULT '',
            TIPO_EQUIPO      TEXT DEFAULT 'Desktop',
            SISTEMA_OPERATIVO TEXT DEFAULT '',
            PROCESADOR       TEXT DEFAULT '',
            RAM_GB           INTEGER DEFAULT 0,
            DISCO_GB         INTEGER DEFAULT 0,
            FECHA_COMPRA     TEXT,
            GARANTIA_HASTA   TEXT,
            ESTADO_EQUIPO    TEXT DEFAULT 'Activo',
            NOTAS            TEXT DEFAULT '',
            FECHA_REGISTRO   TEXT,
            ULTIMA_CONEXION  TEXT,
            TOTAL_TICKETS    INTEGER DEFAULT 0
        )""")
    print("  Tabla equipos:   OK")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            fecha TEXT PRIMARY KEY,
            seq   INTEGER DEFAULT 0
        )""")
    print("  Tabla counters:  OK")

    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tickets_estado ON tickets(ESTADO)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tickets_usuario_mac "
        "ON tickets(USUARIO_AD, MAC_ADDRESS)")

    # Técnicos iniciales (solo si la tabla está vacía)
    ahora = datetime.now().isoformat(sep=" ", timespec="seconds")
    n_antes = conn.execute("SELECT COUNT(*) FROM tecnicos").fetchone()[0]
    if n_antes == 0:
        for t in TECNICOS_INICIALES:
            conn.execute(
                """INSERT OR IGNORE INTO tecnicos
                   (ID_TECNICO, NOMBRE, ESTADO, ESPECIALIDAD,
                    TICKETS_ATENDIDOS, TICKET_ACTUAL, ULTIMA_ACTIVIDAD,
                    TELEFONO, EMAIL)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (t["id"], t["nombre"], "Disponible", t["especialidad"],
                 0, "", ahora, t["telefono"], t["email"])
            )
        print(f"  Tecnicos iniciales insertados: {len(TECNICOS_INICIALES)}")
    else:
        print(f"  Tecnicos existentes: {n_antes} (no se sobreescribieron)")

    conn.close()
    print(f"\n  Base de datos lista: {DB_PATH}")
    return True


def validar():
    """Valida que la DB exista y todas las tablas estén presentes."""
    print("\n  Validando tickets.db...")
    if not DB_PATH.exists():
        print(f"  No existe: {DB_PATH}")
        return False
    try:
        conn = sqlite3.connect(str(DB_PATH), timeout=3)
        tablas = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        esperadas = {"tickets", "tecnicos", "equipos", "counters"}
        faltantes = esperadas - tablas
        if faltantes:
            print(f"  Tablas faltantes: {faltantes}")
            return False
        print(f"  Tablas encontradas: {sorted(tablas)}")
        print("  Validacion: OK")
        return True
    except Exception as e:
        print(f"  Error de acceso: {e}")
        return False


def main():
    print("=" * 62)
    print("  INICIALIZACION DE BASE DE DATOS — Sistema de Tickets v5.0.0")
    print("=" * 62)
    print(f"\n  Ubicacion: {PROJECT_ROOT}")

    reset = "--reset" in sys.argv

    if reset:
        print("\n  Modo RESET: se eliminara la DB existente (se pierden datos).")
        resp = input("  Esta seguro? (s/N): ").strip().lower()
        if resp != "s":
            print("  Cancelado.")
            return

    try:
        crear_base_datos(borrar_existente=reset)
        if validar():
            print("\n  INICIALIZACION COMPLETADA EXITOSAMENTE")
            print("  Ahora puedes ejecutar: python app_receptora.py")
        else:
            print("\n  La base de datos tiene problemas.")
            print("  Ejecuta con --reset para recrearla desde cero.")
            sys.exit(1)
    except Exception as e:
        print(f"\n  Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
