# =============================================================================
# MÓDULO DE ACCESO A DATOS - data_access.py (SQLite Edition v5.0.0)
# =============================================================================
# Usa SQLite (incluido en Python estándar — cero instalación adicional).
# Misma interfaz pública que versiones anteriores (Excel, MongoDB).
# WAL mode → lecturas concurrentes sin bloqueos.
# Un único archivo: tickets.db en la misma carpeta.
# =============================================================================

import sqlite3
import pandas as pd
import os
import uuid
import socket
import subprocess
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================

DB_PATH              = Path(__file__).parent / "tickets.db"
SERVIDOR_PUERTO      = 5555
SERVIDOR_CONFIG_PATH = Path(__file__).parent / "servidor_config.txt"

# Rutas Excel (usadas SOLO en migrar_desde_excel() — puedes ignorar si vienes de cero)
# EXCEL_DB_PATH, TECNICOS_DB_PATH, EQUIPOS_DB_PATH se definen dentro de migrar_desde_excel()

# Columnas
COLUMNAS_DB = [
    "ID_TICKET", "TURNO", "FECHA_APERTURA", "USUARIO_AD", "HOSTNAME",
    "MAC_ADDRESS", "CATEGORIA", "PRIORIDAD", "DESCRIPCION", "ESTADO",
    "TECNICO_ASIGNADO", "NOTAS_RESOLUCION", "HISTORIAL",
    "FECHA_CIERRE", "TIEMPO_ESTIMADO"
]
COLUMNAS_TECNICOS = [
    "ID_TECNICO", "NOMBRE", "ESTADO", "ESPECIALIDAD", "TICKETS_ATENDIDOS",
    "TICKET_ACTUAL", "ULTIMA_ACTIVIDAD", "TELEFONO", "EMAIL"
]
COLUMNAS_EQUIPOS = [
    "MAC_ADDRESS", "NOMBRE_EQUIPO", "HOSTNAME", "USUARIO_ASIGNADO", "GRUPO",
    "UBICACION", "MARCA", "MODELO", "NUMERO_SERIE", "TIPO_EQUIPO",
    "SISTEMA_OPERATIVO", "PROCESADOR", "RAM_GB", "DISCO_GB",
    "FECHA_COMPRA", "GARANTIA_HASTA", "ESTADO_EQUIPO", "NOTAS",
    "FECHA_REGISTRO", "ULTIMA_CONEXION", "TOTAL_TICKETS"
]
COLUMNAS_RED = [
    "IP_ADDRESS", "MAC_ADDRESS", "HOSTNAME", "ESTADO_RED",
    "ULTIMO_PING", "PRIMERA_VEZ", "IP_ANTERIOR", "CAMBIOS_IP", "COMENTARIO"
]

GRUPOS_EQUIPOS    = ["Administración", "Contabilidad", "Recursos Humanos", "Ventas",
                     "Marketing", "Producción", "Almacén", "Gerencia", "IT",
                     "Recepción", "Sin Asignar"]
TIPOS_EQUIPO      = ["Desktop", "Laptop", "Servidor", "Impresora", "Router/Switch", "Otro"]
ESTADOS_EQUIPO    = ["Activo", "Inactivo", "En Mantenimiento", "Baja"]
ESTADOS_RED       = ["Online", "Offline", "Desconocido"]
CATEGORIAS_DISPONIBLES = ["Red", "Hardware", "Software", "Accesos", "Impresoras",
                           "Email", "Otros"]
ESTADOS_TICKET    = ["Abierto", "En Cola", "En Proceso", "En Espera", "Cerrado", "Cancelado"]
ESTADOS_TECNICO   = ["Disponible", "Ocupado", "Ausente", "En Descanso"]
PRIORIDADES       = ["Crítica", "Alta", "Media", "Baja"]
MAX_REINTENTOS    = 3
TIEMPO_ESPERA_REINTENTO = 2

TECNICOS_EQUIPO = [
    {"id": "TEC001", "nombre": "Carlos Rodríguez", "especialidad": "Hardware/Red",
     "telefono": "ext. 101", "email": "carlos.rodriguez@empresa.com"},
    {"id": "TEC002", "nombre": "María García",     "especialidad": "Software/Accesos",
     "telefono": "ext. 102", "email": "maria.garcia@empresa.com"}
]

# Locks de escritura (WAL mode permite lecturas concurrentes)
_lock_escritura   = threading.RLock()
_lock_tickets_db  = _lock_escritura   # alias de compatibilidad
_lock_tecnicos_db = _lock_escritura
_lock_equipos_db  = _lock_escritura


# =============================================================================
# HELPERS DE CONEXIÓN
# =============================================================================

def _conectar(db_path: Path = DB_PATH) -> sqlite3.Connection:
    """Abre conexión SQLite con WAL mode y row_factory."""
    conn = sqlite3.connect(str(db_path), check_same_thread=False,
                           timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def _row_to_dict(row) -> dict:
    """Convierte sqlite3.Row a dict."""
    if row is None:
        return {}
    return dict(row)


def _rows_to_df(rows: list, columnas: list) -> pd.DataFrame:
    """Convierte lista de sqlite3.Row a DataFrame con columnas garantizadas."""
    if not rows:
        return pd.DataFrame(columns=columnas)
    df = pd.DataFrame([dict(r) for r in rows])
    for col in columnas:
        if col not in df.columns:
            df[col] = None
    # Retornar solo las columnas definidas (en orden)
    cols_existentes = [c for c in columnas if c in df.columns]
    return df[cols_existentes]


def _dt_str(dt) -> Optional[str]:
    """Convierte datetime a string ISO para SQLite."""
    if dt is None:
        return None
    if isinstance(dt, datetime):
        return dt.isoformat(sep=" ", timespec="seconds")
    return str(dt)


def _str_dt(s) -> Optional[datetime]:
    """Convierte string ISO de SQLite a datetime."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s))
    except Exception:
        return None


# =============================================================================
# DDL — Creación de tablas
# =============================================================================

_DDL_TICKETS = """
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
);
CREATE INDEX IF NOT EXISTS idx_tickets_usuario_mac ON tickets(USUARIO_AD, MAC_ADDRESS);
CREATE INDEX IF NOT EXISTS idx_tickets_estado      ON tickets(ESTADO);
CREATE INDEX IF NOT EXISTS idx_tickets_fecha       ON tickets(FECHA_APERTURA);
"""

_DDL_TECNICOS = """
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
);
"""

_DDL_EQUIPOS = """
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
);
"""

_DDL_RED = """
CREATE TABLE IF NOT EXISTS red (
    IP_ADDRESS  TEXT PRIMARY KEY,
    MAC_ADDRESS TEXT DEFAULT '',
    HOSTNAME    TEXT DEFAULT '',
    ESTADO_RED  TEXT DEFAULT 'Desconocido',
    ULTIMO_PING TEXT,
    PRIMERA_VEZ TEXT,
    IP_ANTERIOR TEXT DEFAULT '',
    CAMBIOS_IP  INTEGER DEFAULT 0,
    COMENTARIO  TEXT DEFAULT ''
);
"""

_DDL_COUNTERS = """
CREATE TABLE IF NOT EXISTS counters (
    fecha TEXT PRIMARY KEY,
    seq   INTEGER DEFAULT 0
);
"""


def _crear_tablas(conn: sqlite3.Connection):
    for ddl in [_DDL_TICKETS, _DDL_TECNICOS, _DDL_EQUIPOS, _DDL_RED, _DDL_COUNTERS]:
        conn.executescript(ddl)


# =============================================================================
# GESTOR PRINCIPAL
# =============================================================================

class GestorTickets:
    """
    Acceso a datos sobre SQLite.
    Misma interfaz pública que versiones anteriores.
    """

    def __init__(self,
                 db_path: Path = DB_PATH,
                 # Parámetros legacy ignorados (compatibilidad con código viejo)
                 mongo_uri: str = "",
                 db_name: str = "",
                 **kwargs):
        """Inicializa el gestor. Solo se usa db_path; el resto es compatibilidad."""
        self.db_path = Path(db_path)

        # Conexión principal (usada en hilos de la receptora)
        self._conn = _conectar(self.db_path)
        _crear_tablas(self._conn)
        self._inicializar_tecnicos()
        print(f"[SQLite] Base de datos lista: {self.db_path}")

    # ------------------------------------------------------------------
    # Conexión thread-local para accesos concurrentes (hilos HTTP)
    # ------------------------------------------------------------------

    _local = threading.local()

    def _c(self) -> sqlite3.Connection:
        """Retorna una conexión por-hilo para evitar problemas de concurrencia."""
        if not hasattr(self._local, "conn"):
            self._local.conn = _conectar(self.db_path)
        return self._local.conn

    def _ejecutar(self, sql: str, params=()):
        """Ejecuta INSERT/UPDATE/DELETE con lock de escritura."""
        with _lock_escritura:
            conn = self._c()
            conn.execute(sql, params)

    def _consultar(self, sql: str, params=()) -> list:
        """Ejecuta SELECT y retorna lista de sqlite3.Row."""
        conn = self._c()
        cur = conn.execute(sql, params)
        return cur.fetchall()

    def _consultar_uno(self, sql: str, params=()):
        """Ejecuta SELECT y retorna un sqlite3.Row o None."""
        conn = self._c()
        cur = conn.execute(sql, params)
        return cur.fetchone()

    # ------------------------------------------------------------------
    # Inicialización
    # ------------------------------------------------------------------

    def _inicializar_tecnicos(self):
        existe = self._consultar_uno("SELECT COUNT(*) as c FROM tecnicos")
        if existe and existe["c"] == 0:
            for tec in TECNICOS_EQUIPO:
                self._ejecutar(
                    """INSERT OR IGNORE INTO tecnicos
                       (ID_TECNICO, NOMBRE, ESTADO, ESPECIALIDAD,
                        TICKETS_ATENDIDOS, TICKET_ACTUAL, ULTIMA_ACTIVIDAD,
                        TELEFONO, EMAIL)
                       VALUES (?,?,?,?,?,?,?,?,?)""",
                    (tec["id"], tec["nombre"], "Disponible", tec["especialidad"],
                     0, "", _dt_str(datetime.now()), tec["telefono"], tec["email"])
                )
            print("[SQLite] Técnicos iniciales creados")

    # ------------------------------------------------------------------
    # Lectura como DataFrame (para análisis)
    # ------------------------------------------------------------------

    def _leer_datos(self) -> pd.DataFrame:
        rows = self._consultar("SELECT * FROM tickets")
        df = _rows_to_df(rows, COLUMNAS_DB)
        for col in ["FECHA_APERTURA", "FECHA_CIERRE"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        for col in ["TURNO", "TIEMPO_ESTIMADO"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        for col in ["TECNICO_ASIGNADO", "NOTAS_RESOLUCION", "HISTORIAL"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).replace("nan", "")
        return df

    def _leer_tecnicos(self) -> pd.DataFrame:
        rows = self._consultar("SELECT * FROM tecnicos")
        df = _rows_to_df(rows, COLUMNAS_TECNICOS)
        if "TICKETS_ATENDIDOS" in df.columns:
            df["TICKETS_ATENDIDOS"] = pd.to_numeric(
                df["TICKETS_ATENDIDOS"], errors="coerce").fillna(0).astype(int)
        return df

    def _leer_equipos(self) -> pd.DataFrame:
        rows = self._consultar("SELECT * FROM equipos")
        df = _rows_to_df(rows, COLUMNAS_EQUIPOS)
        for col in ["FECHA_COMPRA", "GARANTIA_HASTA", "FECHA_REGISTRO", "ULTIMA_CONEXION"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        for col in ["RAM_GB", "DISCO_GB", "TOTAL_TICKETS"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        return df

    # Legacy no-op
    def _escribir_datos(self, df: pd.DataFrame, reintentos: int = MAX_REINTENTOS) -> bool:
        return True

    def _escribir_tecnicos(self, df: pd.DataFrame) -> bool:
        return True

    def _escribir_equipos(self, df: pd.DataFrame) -> bool:
        return True

    # ------------------------------------------------------------------
    # TURNO — contador atómico por fecha
    # ------------------------------------------------------------------

    def obtener_siguiente_turno(self) -> int:
        """Número de turno del día, autoincremental y atómico."""
        fecha_hoy = str(datetime.now().date())
        with _lock_escritura:
            conn = self._c()
            conn.execute(
                "INSERT INTO counters(fecha, seq) VALUES(?,1) "
                "ON CONFLICT(fecha) DO UPDATE SET seq = seq + 1",
                (fecha_hoy,)
            )
            row = conn.execute(
                "SELECT seq FROM counters WHERE fecha=?", (fecha_hoy,)
            ).fetchone()
        return row["seq"] if row else 1

    # ------------------------------------------------------------------
    # TÉCNICOS
    # ------------------------------------------------------------------

    def obtener_tecnicos(self) -> pd.DataFrame:
        return self._leer_tecnicos()

    def obtener_tecnico_por_id(self, id_tecnico: str) -> Optional[Dict]:
        row = self._consultar_uno(
            "SELECT * FROM tecnicos WHERE ID_TECNICO=?", (id_tecnico,)
        )
        return _row_to_dict(row) or None

    def agregar_tecnico(self, nombre: str, especialidad: str,
                        telefono: str = "", email: str = "") -> Dict:
        row = self._consultar_uno("SELECT COUNT(*) as c FROM tecnicos")
        count = row["c"] if row else 0
        id_tec = f"TEC{count + 1:03d}"
        self._ejecutar(
            """INSERT INTO tecnicos
               (ID_TECNICO, NOMBRE, ESTADO, ESPECIALIDAD,
                TICKETS_ATENDIDOS, TICKET_ACTUAL, ULTIMA_ACTIVIDAD, TELEFONO, EMAIL)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (id_tec, nombre, "Disponible", especialidad,
             0, "", _dt_str(datetime.now()), telefono, email)
        )
        return {"ID_TECNICO": id_tec, "NOMBRE": nombre, "ESTADO": "Disponible",
                "ESPECIALIDAD": especialidad, "TELEFONO": telefono, "EMAIL": email}

    def eliminar_tecnico(self, id_tecnico: str) -> bool:
        with _lock_escritura:
            conn = self._c()
            cur = conn.execute(
                "DELETE FROM tecnicos WHERE ID_TECNICO=?", (id_tecnico,)
            )
        return cur.rowcount > 0

    def actualizar_estado_tecnico(self, id_tecnico: str, nuevo_estado: str,
                                   ticket_actual: str = "") -> bool:
        if nuevo_estado not in ESTADOS_TECNICO:
            return False
        self._ejecutar(
            """UPDATE tecnicos SET ESTADO=?, TICKET_ACTUAL=?, ULTIMA_ACTIVIDAD=?
               WHERE ID_TECNICO=?""",
            (nuevo_estado, ticket_actual or "", _dt_str(datetime.now()), id_tecnico)
        )
        return True

    def hay_tecnico_disponible(self) -> bool:
        row = self._consultar_uno(
            "SELECT COUNT(*) as c FROM tecnicos WHERE ESTADO='Disponible'"
        )
        return (row["c"] > 0) if row else False

    def obtener_tecnicos_disponibles(self) -> pd.DataFrame:
        rows = self._consultar(
            "SELECT * FROM tecnicos WHERE ESTADO='Disponible'"
        )
        return _rows_to_df(rows, COLUMNAS_TECNICOS)

    def asignar_ticket_a_tecnico(self, id_ticket: str, id_tecnico: str) -> bool:
        tec = self.obtener_tecnico_por_id(id_tecnico)
        if not tec:
            return False
        nombre = tec.get("NOMBRE", "")
        with _lock_escritura:
            conn = self._c()
            conn.execute(
                "UPDATE tickets SET ESTADO='En Proceso', TECNICO_ASIGNADO=? WHERE ID_TICKET=?",
                (nombre, id_ticket)
            )
            conn.execute(
                """UPDATE tecnicos SET ESTADO='Ocupado', TICKET_ACTUAL=?,
                   ULTIMA_ACTIVIDAD=? WHERE ID_TECNICO=?""",
                (id_ticket, _dt_str(datetime.now()), id_tecnico)
            )
        return True

    def liberar_tecnico(self, id_tecnico: str) -> bool:
        tec = self.obtener_tecnico_por_id(id_tecnico)
        if not tec:
            return False
        atendidos = (tec.get("TICKETS_ATENDIDOS") or 0) + 1
        self._ejecutar(
            """UPDATE tecnicos
               SET ESTADO='Disponible', TICKET_ACTUAL='',
                   TICKETS_ATENDIDOS=?, ULTIMA_ACTIVIDAD=?
               WHERE ID_TECNICO=?""",
            (atendidos, _dt_str(datetime.now()), id_tecnico)
        )
        return True

    # ------------------------------------------------------------------
    # TICKETS — CRUD
    # ------------------------------------------------------------------

    def crear_ticket(self, usuario_ad: str, hostname: str, mac_address: str,
                     categoria: str, descripcion: str,
                     prioridad: str = "Media") -> Dict:
        if categoria not in CATEGORIAS_DISPONIBLES:
            raise ValueError(f"Categoría inválida: {categoria}")

        self.registrar_o_actualizar_equipo(mac_address, hostname, usuario_ad)

        id_ticket = str(uuid.uuid4())[:8].upper()
        turno     = self.obtener_siguiente_turno()
        hay_disp  = self.hay_tecnico_disponible()
        estado    = "Abierto" if hay_disp else "En Cola"
        ahora     = _dt_str(datetime.now())

        self._ejecutar(
            """INSERT INTO tickets
               (ID_TICKET, TURNO, FECHA_APERTURA, USUARIO_AD, HOSTNAME,
                MAC_ADDRESS, CATEGORIA, PRIORIDAD, DESCRIPCION, ESTADO,
                TECNICO_ASIGNADO, NOTAS_RESOLUCION, HISTORIAL,
                FECHA_CIERRE, TIEMPO_ESTIMADO)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (id_ticket, turno, ahora, usuario_ad, hostname,
             mac_address, categoria, prioridad, descripcion, estado,
             "", "", "", None, 0)
        )

        estado_sis = self.obtener_mensaje_estado_sistema()
        return {
            "ID_TICKET": id_ticket, "TURNO": turno,
            "FECHA_APERTURA": ahora, "USUARIO_AD": usuario_ad,
            "HOSTNAME": hostname, "MAC_ADDRESS": mac_address,
            "CATEGORIA": categoria, "PRIORIDAD": prioridad,
            "DESCRIPCION": descripcion, "ESTADO": estado,
            "TECNICO_ASIGNADO": "", "NOTAS_RESOLUCION": "", "HISTORIAL": "",
            "FECHA_CIERRE": None, "TIEMPO_ESTIMADO": 0,
            "posicion_cola": self.obtener_posicion_cola(id_ticket),
            "mensaje_sistema": estado_sis["mensaje"],
            "hay_tecnico_disponible": hay_disp,
            "tiempo_espera_estimado": estado_sis["tiempo_estimado"]
        }

    def obtener_todos_tickets(self) -> pd.DataFrame:
        return self._leer_datos()

    def obtener_ticket_por_id(self, id_ticket: str) -> Optional[Dict]:
        row = self._consultar_uno(
            "SELECT * FROM tickets WHERE ID_TICKET=?", (id_ticket,)
        )
        return _row_to_dict(row) if row else None

    def obtener_tickets_activos(self) -> pd.DataFrame:
        rows = self._consultar(
            "SELECT * FROM tickets WHERE ESTADO NOT IN ('Cerrado','Cancelado')"
        )
        return _rows_to_df(rows, COLUMNAS_DB)

    def obtener_tickets_en_cola(self) -> pd.DataFrame:
        rows = self._consultar(
            "SELECT * FROM tickets WHERE ESTADO IN ('Abierto','En Cola') ORDER BY TURNO ASC"
        )
        return _rows_to_df(rows, COLUMNAS_DB)

    def obtener_historial(self) -> pd.DataFrame:
        rows = self._consultar(
            "SELECT * FROM tickets WHERE ESTADO IN ('Cerrado','Cancelado')"
        )
        return _rows_to_df(rows, COLUMNAS_DB)

    def obtener_ticket_activo_usuario(self, usuario_ad: str,
                                       mac_address: str = "") -> Optional[Dict]:
        if mac_address:
            row = self._consultar_uno(
                """SELECT * FROM tickets
                   WHERE LOWER(USUARIO_AD)=LOWER(?) AND LOWER(MAC_ADDRESS)=LOWER(?)
                     AND ESTADO NOT IN ('Cerrado','Cancelado')
                   ORDER BY FECHA_APERTURA DESC LIMIT 1""",
                (usuario_ad, mac_address)
            )
        else:
            row = self._consultar_uno(
                """SELECT * FROM tickets
                   WHERE LOWER(USUARIO_AD)=LOWER(?)
                     AND ESTADO NOT IN ('Cerrado','Cancelado')
                   ORDER BY FECHA_APERTURA DESC LIMIT 1""",
                (usuario_ad,)
            )
        return _row_to_dict(row) if row else None

    def obtener_tickets_activos_usuario(self, usuario_ad: str,
                                         mac_address: str = "") -> list:
        if mac_address:
            rows = self._consultar(
                """SELECT * FROM tickets
                   WHERE LOWER(USUARIO_AD)=LOWER(?) AND LOWER(MAC_ADDRESS)=LOWER(?)
                     AND ESTADO NOT IN ('Cerrado','Cancelado')""",
                (usuario_ad, mac_address)
            )
        else:
            rows = self._consultar(
                """SELECT * FROM tickets
                   WHERE LOWER(USUARIO_AD)=LOWER(?)
                     AND ESTADO NOT IN ('Cerrado','Cancelado')""",
                (usuario_ad,)
            )
        return [_row_to_dict(r) for r in rows]

    def obtener_tickets_usuario(self, usuario_ad: str, limite: int = 20,
                                 mac_address: str = "") -> list:
        if mac_address:
            rows = self._consultar(
                """SELECT * FROM tickets
                   WHERE LOWER(USUARIO_AD)=LOWER(?) AND LOWER(MAC_ADDRESS)=LOWER(?)
                   ORDER BY FECHA_APERTURA DESC LIMIT ?""",
                (usuario_ad, mac_address, limite)
            )
        else:
            rows = self._consultar(
                """SELECT * FROM tickets
                   WHERE LOWER(USUARIO_AD)=LOWER(?)
                   ORDER BY FECHA_APERTURA DESC LIMIT ?""",
                (usuario_ad, limite)
            )
        return [_row_to_dict(r) for r in rows]

    def actualizar_ticket(self, id_ticket: str,
                          estado: Optional[str] = None,
                          tecnico_asignado: Optional[str] = None,
                          notas_resolucion: Optional[str] = None,
                          historial: Optional[str] = None,
                          fecha_cierre: Optional[datetime] = None) -> bool:
        doc = self.obtener_ticket_por_id(id_ticket)
        if not doc:
            return False
        if doc.get("ESTADO") in ["Cerrado", "Cancelado"]:
            raise ValueError("No se puede editar un ticket cerrado o cancelado.")

        sets, params = [], []
        if estado is not None:
            if estado not in ESTADOS_TICKET:
                raise ValueError(f"Estado inválido: {estado}")
            sets.append("ESTADO=?"); params.append(estado)
            if estado in ["Cerrado", "Cancelado"]:
                sets.append("FECHA_CIERRE=?")
                params.append(_dt_str(datetime.now()))
        if tecnico_asignado is not None:
            sets.append("TECNICO_ASIGNADO=?"); params.append(tecnico_asignado)
        if notas_resolucion is not None:
            sets.append("NOTAS_RESOLUCION=?"); params.append(notas_resolucion)
        if historial is not None:
            sets.append("HISTORIAL=?"); params.append(historial)
        if fecha_cierre is not None:
            sets.append("FECHA_CIERRE=?"); params.append(_dt_str(fecha_cierre))
        if not sets:
            return True
        params.append(id_ticket)
        self._ejecutar(
            f"UPDATE tickets SET {', '.join(sets)} WHERE ID_TICKET=?",
            params
        )
        return True

    def filtrar_tickets(self, estado: Optional[str] = None,
                        usuario: Optional[str] = None,
                        mac_address: Optional[str] = None) -> pd.DataFrame:
        clauses, params = [], []
        if estado:
            clauses.append("ESTADO=?"); params.append(estado)
        if usuario:
            clauses.append("LOWER(USUARIO_AD) LIKE LOWER(?)"); params.append(f"%{usuario}%")
        if mac_address:
            clauses.append("LOWER(MAC_ADDRESS) LIKE LOWER(?)"); params.append(f"%{mac_address}%")
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows  = self._consultar(f"SELECT * FROM tickets {where}", params)
        return _rows_to_df(rows, COLUMNAS_DB)

    # ------------------------------------------------------------------
    # COLA
    # ------------------------------------------------------------------

    def obtener_posicion_cola(self, id_ticket: str) -> int:
        doc = self.obtener_ticket_por_id(id_ticket)
        if not doc:
            return -1
        estado = doc.get("ESTADO", "")
        if estado in ["En Proceso", "Cerrado", "Cancelado"]:
            return 0
        turno = doc.get("TURNO", 0)
        hoy   = str(datetime.now().date())
        row   = self._consultar_uno(
            """SELECT COUNT(*) as c FROM tickets
               WHERE ESTADO IN ('Abierto','En Cola')
                 AND TURNO < ?
                 AND DATE(FECHA_APERTURA) = ?""",
            (turno, hoy)
        )
        return (row["c"] + 1) if row else 1

    # ------------------------------------------------------------------
    # ESTADO DEL SISTEMA
    # ------------------------------------------------------------------

    def obtener_mensaje_estado_sistema(self) -> Dict:
        row      = self._consultar_uno(
            "SELECT COUNT(*) as c FROM tecnicos WHERE ESTADO='Disponible'"
        )
        disponibles = row["c"] if row else 0
        row2     = self._consultar_uno(
            "SELECT COUNT(*) as c FROM tickets WHERE ESTADO IN ('Abierto','En Cola')"
        )
        en_cola  = row2["c"] if row2 else 0

        if disponibles > 0:
            rows_t  = self._consultar(
                "SELECT NOMBRE FROM tecnicos WHERE ESTADO='Disponible'"
            )
            nombres = [r["NOMBRE"] for r in rows_t]
            return {
                "hay_disponible": True,
                "mensaje": f"✅ Hay {disponibles} técnico(s) disponible(s)",
                "color": "green",
                "tecnicos_disponibles": nombres,
                "tickets_en_cola": en_cola,
                "tiempo_estimado": en_cola * 15
            }
        return {
            "hay_disponible": False,
            "mensaje": "⏳ Todos los técnicos están ocupados. Se te asignará un turno.",
            "color": "orange",
            "tecnicos_disponibles": [],
            "tickets_en_cola": en_cola,
            "tiempo_estimado": (en_cola + 1) * 15
        }

    # ------------------------------------------------------------------
    # EQUIPOS
    # ------------------------------------------------------------------

    def obtener_equipos(self) -> pd.DataFrame:
        return self._leer_equipos()

    def obtener_equipo_por_mac(self, mac_address: str) -> Optional[Dict]:
        row = self._consultar_uno(
            "SELECT * FROM equipos WHERE LOWER(MAC_ADDRESS)=LOWER(?)",
            (mac_address,)
        )
        return _row_to_dict(row) if row else None

    def registrar_o_actualizar_equipo(self, mac_address: str, hostname: str,
                                       usuario_ad: str) -> Dict:
        try:
            ahora = _dt_str(datetime.now())
            row   = self._consultar_uno(
                "SELECT COUNT(*) as c FROM tickets WHERE MAC_ADDRESS=?", (mac_address,)
            )
            total_tickets = row["c"] if row else 0
            with _lock_escritura:
                conn = self._c()
                conn.execute(
                    """INSERT INTO equipos
                       (MAC_ADDRESS, NOMBRE_EQUIPO, HOSTNAME, USUARIO_ASIGNADO, GRUPO,
                        FECHA_REGISTRO, ULTIMA_CONEXION, TOTAL_TICKETS,
                        UBICACION, MARCA, MODELO, NUMERO_SERIE, TIPO_EQUIPO,
                        SISTEMA_OPERATIVO, PROCESADOR, RAM_GB, DISCO_GB,
                        ESTADO_EQUIPO, NOTAS)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                       ON CONFLICT(MAC_ADDRESS) DO UPDATE SET
                           HOSTNAME=excluded.HOSTNAME,
                           USUARIO_ASIGNADO=excluded.USUARIO_ASIGNADO,
                           ULTIMA_CONEXION=excluded.ULTIMA_CONEXION,
                           TOTAL_TICKETS=excluded.TOTAL_TICKETS""",
                    (mac_address, hostname, hostname, usuario_ad, "Sin Asignar",
                     ahora, ahora, total_tickets,
                     "", "", "", "", "Desktop", "", "", 0, 0, "Activo", "")
                )
            return self.obtener_equipo_por_mac(mac_address) or {}
        except Exception as e:
            print(f"[SQLite] Error equipo: {e}")
            return {}

    def actualizar_equipo(self, mac_address: str, **datos) -> bool:
        if not datos:
            return False
        sets   = [f"{k}=?" for k in datos]
        params = list(datos.values()) + [mac_address]
        with _lock_escritura:
            conn = self._c()
            cur  = conn.execute(
                f"UPDATE equipos SET {', '.join(sets)} WHERE MAC_ADDRESS=?", params
            )
        return cur.rowcount > 0

    def eliminar_equipo(self, mac_address: str) -> bool:
        with _lock_escritura:
            conn = self._c()
            cur  = conn.execute(
                "DELETE FROM equipos WHERE MAC_ADDRESS=?", (mac_address,)
            )
        return cur.rowcount > 0

    def obtener_grupos_con_conteo(self) -> Dict[str, int]:
        rows = self._consultar(
            "SELECT GRUPO, COUNT(*) as c FROM equipos GROUP BY GRUPO"
        )
        return {r["GRUPO"] or "Sin Asignar": r["c"] for r in rows}

    def obtener_equipos_por_grupo(self, grupo: str) -> pd.DataFrame:
        rows = self._consultar(
            "SELECT * FROM equipos WHERE GRUPO=?", (grupo,)
        )
        return _rows_to_df(rows, COLUMNAS_EQUIPOS)

    def obtener_estadisticas_equipos(self) -> Dict:
        total = self._consultar_uno("SELECT COUNT(*) as c FROM equipos")
        rows  = self._consultar(
            "SELECT ESTADO_EQUIPO, COUNT(*) as c FROM equipos GROUP BY ESTADO_EQUIPO"
        )
        sin_nombre_row = self._consultar_uno(
            "SELECT COUNT(*) as c FROM equipos WHERE NOMBRE_EQUIPO IS NULL OR NOMBRE_EQUIPO = ''"
        )
        por_estado = {r["ESTADO_EQUIPO"]: r["c"] for r in rows}
        total_val   = total["c"] if total else 0
        activos_val = por_estado.get("Activo", 0)
        mant_val    = por_estado.get("En Mantenimiento", 0)
        sin_nombre_val = sin_nombre_row["c"] if sin_nombre_row else 0
        return {
            # Claves originales
            "total": total_val,
            "activos": activos_val,
            "inactivos": por_estado.get("Inactivo", 0),
            "mantenimiento": mant_val,
            "bajas": por_estado.get("Baja", 0),
            # Alias usados en _vista_inventario
            "total_equipos": total_val,
            "equipos_activos": activos_val,
            "equipos_mantenimiento": mant_val,
            "sin_nombre": sin_nombre_val,
        }

    # ------------------------------------------------------------------
    # ESTADÍSTICAS / ANÁLISIS
    # ------------------------------------------------------------------

    def contar_tickets_abiertos_hoy(self) -> int:
        hoy = str(datetime.now().date())
        row = self._consultar_uno(
            """SELECT COUNT(*) as c FROM tickets
               WHERE DATE(FECHA_APERTURA)=?
                 AND ESTADO NOT IN ('Cerrado','Cancelado')""",
            (hoy,)
        )
        return row["c"] if row else 0

    def calcular_tiempo_promedio_cierre(self) -> float:
        rows = self._consultar(
            """SELECT FECHA_APERTURA, FECHA_CIERRE FROM tickets
               WHERE ESTADO IN ('Cerrado','Cancelado')
                 AND FECHA_APERTURA IS NOT NULL
                 AND FECHA_CIERRE IS NOT NULL"""
        )
        tiempos = []
        for r in rows:
            fa = _str_dt(r["FECHA_APERTURA"])
            fc = _str_dt(r["FECHA_CIERRE"])
            if fa and fc:
                diff = (fc - fa).total_seconds() / 60
                if 0 < diff < 10000:
                    tiempos.append(diff)
        return round(sum(tiempos) / len(tiempos), 1) if tiempos else 0.0

    def obtener_estadisticas_generales(self) -> Dict:
        try:
            def _cnt(where="", params=()):
                r = self._consultar_uno(
                    f"SELECT COUNT(*) as c FROM tickets {where}", params
                )
                return r["c"] if r else 0
            return {
                "total_tickets": _cnt(),
                "tickets_abiertos": _cnt("WHERE ESTADO='Abierto'"),
                "tickets_en_proceso": _cnt("WHERE ESTADO='En Proceso'"),
                "tickets_cerrados": _cnt("WHERE ESTADO='Cerrado'"),
                "tickets_hoy": self.contar_tickets_abiertos_hoy(),
                "tiempo_promedio_cierre": self.calcular_tiempo_promedio_cierre()
            }
        except Exception as e:
            print(f"[SQLite] Error estadísticas: {e}")
            return {"total_tickets": 0, "tickets_abiertos": 0, "tickets_en_proceso": 0,
                    "tickets_cerrados": 0, "tickets_hoy": 0, "tiempo_promedio_cierre": 0.0}

    def obtener_distribucion_categorias(self) -> pd.DataFrame:
        rows = self._consultar(
            "SELECT CATEGORIA, COUNT(*) as TOTAL FROM tickets GROUP BY CATEGORIA"
        )
        return pd.DataFrame([dict(r) for r in rows]) if rows else \
               pd.DataFrame(columns=["CATEGORIA", "TOTAL"])

    def obtener_distribucion_prioridades(self) -> pd.DataFrame:
        rows = self._consultar(
            "SELECT PRIORIDAD, COUNT(*) as TOTAL FROM tickets GROUP BY PRIORIDAD"
        )
        return pd.DataFrame([dict(r) for r in rows]) if rows else \
               pd.DataFrame(columns=["PRIORIDAD", "TOTAL"])

    def obtener_tickets_por_dia_semana(self) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["DIA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce").dt.day_name()
        return df.groupby("DIA").size().reset_index(name="TOTAL")

    def obtener_tickets_por_mes(self, meses: int = 12) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["MES"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce") \
                      .dt.to_period("M").astype(str)
        return df.groupby("MES").size().reset_index(name="TOTAL")

    def obtener_tickets_por_hora(self) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["HORA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce").dt.hour
        return df.groupby("HORA").size().reset_index(name="TOTAL")

    def obtener_rendimiento_tecnicos(self) -> pd.DataFrame:
        rows = self._consultar(
            """SELECT TECNICO_ASIGNADO as NOMBRE, COUNT(*) as TICKETS_ATENDIDOS
               FROM tickets
               WHERE ESTADO IN ('Cerrado','Cancelado')
                 AND TECNICO_ASIGNADO != ''
               GROUP BY TECNICO_ASIGNADO"""
        )
        return pd.DataFrame([dict(r) for r in rows]) if rows else \
               pd.DataFrame(columns=["NOMBRE", "TICKETS_ATENDIDOS"])

    def obtener_tendencia_semanal(self, semanas: int = 8) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["SEMANA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce") \
                         .dt.to_period("W").astype(str)
        return df.groupby("SEMANA").size().reset_index(name="TOTAL")

    def obtener_tiempo_resolucion_por_categoria(self) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce")
        df["FECHA_CIERRE"]   = pd.to_datetime(df["FECHA_CIERRE"],   errors="coerce")
        df = df.dropna(subset=["FECHA_APERTURA", "FECHA_CIERRE"])
        if df.empty:
            return pd.DataFrame()
        df["TIEMPO_MIN"] = (df["FECHA_CIERRE"] - df["FECHA_APERTURA"]).dt.total_seconds() / 60
        return df.groupby("CATEGORIA")["TIEMPO_MIN"].mean().reset_index()

    def obtener_equipos_problematicos(self, top_n: int = 5) -> pd.DataFrame:
        rows = self._consultar(
            f"""SELECT MAC_ADDRESS, HOSTNAME, COUNT(*) as TOTAL_TICKETS
                FROM tickets
                GROUP BY MAC_ADDRESS
                ORDER BY TOTAL_TICKETS DESC
                LIMIT {int(top_n)}"""
        )
        return pd.DataFrame([dict(r) for r in rows]) if rows else \
               pd.DataFrame(columns=["MAC_ADDRESS", "HOSTNAME", "TOTAL_TICKETS"])

    def obtener_estadisticas_completas(self) -> Dict:
        generales  = self.obtener_estadisticas_generales()
        categorias = self.obtener_distribucion_categorias()
        return {
            **generales,
            "distribucion_categorias": categorias.to_dict("records") if not categorias.empty else [],
            "tecnicos": self._leer_tecnicos().to_dict("records")
        }

    # ------------------------------------------------------------------
    # EXPORTACIÓN EXCEL
    # ------------------------------------------------------------------

    def exportar_reporte_excel(self, ruta_salida: Path = None) -> str:
        if ruta_salida is None:
            ruta_salida = Path(__file__).parent / \
                          f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df = self._leer_datos()
        df.to_excel(str(ruta_salida), index=False, engine="openpyxl")
        return str(ruta_salida)

    # ------------------------------------------------------------------
    # MIGRACIÓN DESDE EXCEL
    # ------------------------------------------------------------------

    def migrar_desde_excel(self) -> Dict[str, int]:
        """Importa datos de archivos Excel existentes a SQLite (uso único, si tienes datos viejos)."""
        resultado = {"tickets": 0, "tecnicos": 0, "equipos": 0}

        # Rutas Excel definidas localmente — solo usadas aquí
        EXCEL_DB_PATH    = Path(__file__).parent / "tickets_db.xlsx"

        if EXCEL_DB_PATH.exists():
            try:
                df = pd.read_excel(EXCEL_DB_PATH, engine="openpyxl")
                for _, row in df.iterrows():
                    d = {k: (None if pd.isna(v) else v) for k, v in row.to_dict().items()}
                    try:
                        self._ejecutar(
                            """INSERT OR IGNORE INTO tickets
                               (ID_TICKET,TURNO,FECHA_APERTURA,USUARIO_AD,HOSTNAME,
                                MAC_ADDRESS,CATEGORIA,PRIORIDAD,DESCRIPCION,ESTADO,
                                TECNICO_ASIGNADO,NOTAS_RESOLUCION,HISTORIAL,
                                FECHA_CIERRE,TIEMPO_ESTIMADO)
                               VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                            (d.get("ID_TICKET"), d.get("TURNO"), d.get("FECHA_APERTURA"),
                             d.get("USUARIO_AD"), d.get("HOSTNAME"), d.get("MAC_ADDRESS"),
                             d.get("CATEGORIA"), d.get("PRIORIDAD"), d.get("DESCRIPCION"),
                             d.get("ESTADO"), d.get("TECNICO_ASIGNADO",""),
                             d.get("NOTAS_RESOLUCION",""), d.get("HISTORIAL",""),
                             d.get("FECHA_CIERRE"), d.get("TIEMPO_ESTIMADO", 0))
                        )
                        resultado["tickets"] += 1
                    except Exception:
                        pass
            except Exception as e:
                print(f"[Migración] Error tickets: {e}")

        print(f"[Migración] {resultado['tickets']} tickets migrados")
        return resultado

    def obtener_mac_address(self) -> str:
        return obtener_mac_address()


# =============================================================================
# FUNCIONES UTILITARIAS DE RED (sin cambios)
# =============================================================================

def obtener_mac_address() -> str:
    try:
        import getmac
        mac = getmac.get_mac_address()
        return mac.upper() if mac else "00:00:00:00:00:00"
    except Exception:
        return "00:00:00:00:00:00"


def obtener_usuario_ad() -> str:
    """Obtiene el nombre de usuario del sistema (Windows AD / local)."""
    try:
        import getpass
        return getpass.getuser()
    except Exception:
        try:
            import os
            return os.environ.get("USERNAME", os.environ.get("USER", "usuario"))
        except Exception:
            return "usuario"


def obtener_hostname() -> str:
    """Obtiene el nombre del equipo (hostname)."""
    try:
        return socket.gethostname()
    except Exception:
        return "equipo"


def ping_host(ip: str, timeout: int = 1) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout * 1000), ip],
            capture_output=True, timeout=timeout + 1, creationflags=0x08000000
        )
        return result.returncode == 0
    except Exception:
        return False


def obtener_mac_desde_arp(ip: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["arp", "-a", ip], capture_output=True, text=True,
            timeout=3, creationflags=0x08000000
        )
        for line in result.stdout.split("\n"):
            if ip in line:
                match = re.search(
                    r"([0-9a-f]{2}[-:][0-9a-f]{2}[-:][0-9a-f]{2}"
                    r"[-:][0-9a-f]{2}[-:][0-9a-f]{2}[-:][0-9a-f]{2})",
                    line, re.I
                )
                if match:
                    return match.group(1).upper()
    except Exception:
        pass
    return None


def obtener_hostname_remoto(ip: str) -> str:
    try:
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return "Desconocido"


def escanear_ip(ip: str) -> Optional[Dict]:
    if ping_host(ip):
        return {
            "IP_ADDRESS": ip,
            "MAC_ADDRESS": obtener_mac_desde_arp(ip) or "No detectada",
            "HOSTNAME": obtener_hostname_remoto(ip),
            "ESTADO_RED": "Online",
            "ULTIMO_PING": _dt_str(datetime.now())
        }
    return None


# =============================================================================
# ESCÁNER DE RED
# =============================================================================

class EscanerRed:
    """Escanea la red local. Persiste resultados en SQLite."""

    def __init__(self, gestor: Optional[GestorTickets] = None):
        # Si no se provee gestor, crear uno propio para persistir resultados
        self._gestor = gestor if gestor is not None else GestorTickets()
        self.escaneando = False
        # Callbacks opcionales: fn(actual, total) y fn(equipo_dict)
        self.callback_progreso = None
        self.callback_equipo   = None

    def escanear_red(self, rango_inicio: int = 1, rango_fin: int = 254,
                     hilos: int = 50):
        """Escanea la red y retorna (encontrados, cambios_ip)."""
        self.escaneando = True
        try:
            ip_local = socket.gethostbyname(socket.gethostname())
            red_base = ".".join(ip_local.split(".")[:3])
        except Exception:
            red_base = "192.168.1"

        ips = [f"{red_base}.{i}" for i in range(rango_inicio, rango_fin + 1)]
        total = len(ips)
        encontrados: List[Dict] = []
        cambios:     List[Dict] = []
        procesados = 0

        with ThreadPoolExecutor(max_workers=hilos) as executor:
            futures = {executor.submit(escanear_ip, ip): ip for ip in ips}
            for future in as_completed(futures):
                if not self.escaneando:
                    break
                procesados += 1
                # Notificar progreso
                if callable(self.callback_progreso):
                    try:
                        self.callback_progreso(procesados, total)
                    except Exception:
                        pass
                result = future.result()
                if result:
                    encontrados.append(result)
                    # Notificar equipo encontrado
                    if callable(self.callback_equipo):
                        try:
                            self.callback_equipo(result)
                        except Exception:
                            pass
                    # Persistir en BD y detectar cambios de IP
                    try:
                        ahora = _dt_str(datetime.now())
                        ip_nueva  = result["IP_ADDRESS"]
                        mac        = result["MAC_ADDRESS"]
                        # Verificar si la MAC ya existía con otra IP (cambio de IP)
                        existente = self._gestor._consultar_uno(
                            "SELECT IP_ADDRESS, CAMBIOS_IP FROM red WHERE MAC_ADDRESS=?",
                            (mac,)
                        ) if mac and mac != "No detectada" else None
                        if existente and existente["IP_ADDRESS"] != ip_nueva:
                            # Cambio de IP detectado
                            cambio_count = (existente["CAMBIOS_IP"] or 0) + 1
                            result["IP_ANTERIOR"] = existente["IP_ADDRESS"]
                            result["CAMBIOS_IP"]  = cambio_count
                            cambios.append(result)
                            self._gestor._ejecutar(
                                """UPDATE red SET IP_ADDRESS=?, ESTADO_RED='Online',
                                       ULTIMO_PING=?, CAMBIOS_IP=?
                                   WHERE MAC_ADDRESS=?""",
                                (ip_nueva, ahora, cambio_count, mac)
                            )
                        else:
                            cambios_ip_val = result.get("CAMBIOS_IP", 0)
                            self._gestor._ejecutar(
                                """INSERT INTO red
                                   (IP_ADDRESS, MAC_ADDRESS, HOSTNAME, ESTADO_RED,
                                    ULTIMO_PING, PRIMERA_VEZ, CAMBIOS_IP, COMENTARIO)
                                   VALUES (?,?,?,?,?,?,?,?)
                                   ON CONFLICT(IP_ADDRESS) DO UPDATE SET
                                       MAC_ADDRESS=excluded.MAC_ADDRESS,
                                       HOSTNAME=excluded.HOSTNAME,
                                       ESTADO_RED='Online',
                                       ULTIMO_PING=excluded.ULTIMO_PING""",
                                (ip_nueva, mac, result["HOSTNAME"],
                                 "Online", ahora, ahora, cambios_ip_val, "")
                            )
                    except Exception as ex:
                        print(f"[EscanerRed] Error guardando {result}: {ex}")

        self.escaneando = False
        return encontrados, cambios

    def detener_escaneo(self):
        self.escaneando = False

    def obtener_equipos_red(self) -> pd.DataFrame:
        """Retorna todos los equipos detectados en escaneos anteriores."""
        rows = self._gestor._consultar("SELECT * FROM red ORDER BY ULTIMO_PING DESC")
        return _rows_to_df(rows, COLUMNAS_RED)

    def obtener_historial_red(self) -> pd.DataFrame:
        """Alias de obtener_equipos_red para compatibilidad."""
        return self.obtener_equipos_red()

    def descartar_cambios_ip(self, mac: str) -> bool:
        """Resetea el contador de cambios de IP para un equipo (descarta la alerta)."""
        try:
            self._gestor._ejecutar(
                "UPDATE red SET CAMBIOS_IP=0, IP_ANTERIOR=NULL WHERE MAC_ADDRESS=?",
                (mac,)
            )
            return True
        except Exception as ex:
            print(f"[EscanerRed] Error descartando cambios IP de {mac}: {ex}")
            return False


# Alias de compatibilidad
GestorRed = EscanerRed


# ---------------------------------------------------------------------------
# Funciones de red auxiliares (IP local, rango, config servidor)
# ---------------------------------------------------------------------------

def obtener_ip_local() -> str:
    """Obtiene la IP local del equipo."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.1)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "127.0.0.1"


def obtener_rango_red() -> str:
    """Obtiene el rango de red local en formato CIDR (ej: 192.168.1.0/24)."""
    ip = obtener_ip_local()
    partes = ip.rsplit(".", 1)
    return f"{partes[0]}.0/24" if len(partes) == 2 else "192.168.1.0/24"


def guardar_config_servidor(ip: str, puerto: int = SERVIDOR_PUERTO) -> bool:
    """Guarda la IP y puerto del servidor receptora en servidor_config.txt."""
    try:
        SERVIDOR_CONFIG_PATH.write_text(f"{ip}:{puerto}", encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error guardando config servidor: {e}")
        return False
