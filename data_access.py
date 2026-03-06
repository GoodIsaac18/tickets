# =============================================================================
# MÓDULO DE ACCESO A DATOS - data_access.py (MongoDB Edition v4.0.0)
# =============================================================================
# Misma interfaz que la versión Excel, ahora persistido en MongoDB.
# La receptora corre MongoDB localmente; la emisora accede via HTTP/WebSocket.
# =============================================================================

import pymongo
import pandas as pd
import os
import time
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

MONGO_URI     = "mongodb://localhost:27017/"
MONGO_DB_NAME = "tickets_it"

SERVIDOR_PUERTO      = 5555
SERVIDOR_CONFIG_PATH = Path(__file__).parent / "servidor_config.txt"

# Rutas Excel (solo para exportaciones y migración inicial)
EXCEL_DB_PATH    = Path(__file__).parent / "tickets_db.xlsx"
TECNICOS_DB_PATH = Path(__file__).parent / "tecnicos_db.xlsx"
EQUIPOS_DB_PATH  = Path(__file__).parent / "equipos_db.xlsx"

# Definición de columnas
COLUMNAS_DB = [
    "ID_TICKET", "TURNO", "FECHA_APERTURA", "USUARIO_AD", "HOSTNAME",
    "MAC_ADDRESS", "CATEGORIA", "PRIORIDAD", "DESCRIPCION", "ESTADO",
    "TECNICO_ASIGNADO", "NOTAS_RESOLUCION", "FECHA_CIERRE", "TIEMPO_ESTIMADO"
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
CATEGORIAS_DISPONIBLES = ["Red", "Hardware", "Software", "Accesos", "Impresoras", "Email", "Otros"]
ESTADOS_TICKET    = ["Abierto", "En Cola", "En Proceso", "En Espera", "Cerrado", "Cancelado"]
ESTADOS_TECNICO   = ["Disponible", "Ocupado", "Ausente", "En Descanso"]
PRIORIDADES       = ["Crítica", "Alta", "Media", "Baja"]
MAX_REINTENTOS    = 3
TIEMPO_ESPERA_REINTENTO = 2

TECNICOS_EQUIPO = [
    {"id": "TEC001", "nombre": "Carlos Rodríguez", "especialidad": "Hardware/Red",
     "telefono": "ext. 101", "email": "carlos.rodriguez@empresa.com"},
    {"id": "TEC002", "nombre": "María García", "especialidad": "Software/Accesos",
     "telefono": "ext. 102", "email": "maria.garcia@empresa.com"}
]

# Locks de compatibilidad (las escrituras ya son atómicas en MongoDB)
_lock_tickets_db  = threading.RLock()
_lock_tecnicos_db = threading.RLock()
_lock_equipos_db  = threading.RLock()


# =============================================================================
# HELPERS
# =============================================================================

def _clean_doc(doc: dict) -> dict:
    """Elimina _id de MongoDB y retorna copia limpia."""
    if doc is None:
        return {}
    d = dict(doc)
    d.pop("_id", None)
    return d


def _docs_to_df(docs: list, columnas: list) -> pd.DataFrame:
    """Convierte lista de docs MongoDB a DataFrame con columnas garantizadas."""
    if not docs:
        return pd.DataFrame(columns=columnas)
    df = pd.DataFrame([_clean_doc(d) for d in docs])
    for col in columnas:
        if col not in df.columns:
            df[col] = None
    return df[columnas]


# =============================================================================
# GESTOR PRINCIPAL
# =============================================================================

class GestorTickets:
    """
    Acceso a datos sobre MongoDB.
    Misma interfaz pública que la versión Excel anterior.
    """

    def __init__(self,
                 mongo_uri: str = MONGO_URI,
                 db_name: str = MONGO_DB_NAME,
                 # Parámetros legacy aceptados pero ignorados
                 ruta_excel: Path = EXCEL_DB_PATH,
                 ruta_tecnicos: Path = TECNICOS_DB_PATH,
                 ruta_equipos: Path = EQUIPOS_DB_PATH):

        self.mongo_uri    = mongo_uri
        self.db_name      = db_name
        self.ruta_excel   = ruta_excel
        self.ruta_tecnicos = ruta_tecnicos
        self.ruta_equipos  = ruta_equipos

        try:
            self.client    = pymongo.MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            self.db        = self.client[db_name]
            self._tickets  = self.db["tickets"]
            self._tecs     = self.db["tecnicos"]
            self._equipos  = self.db["equipos"]
            self._counters = self.db["counters"]
            self._red      = self.db["red"]

            self.client.admin.command("ping")
            print(f"[MongoDB] Conectado a {mongo_uri}{db_name}")

            self._inicializar_indices()
            self._inicializar_tecnicos()
        except Exception as e:
            print(f"[MongoDB] ERROR de conexión: {e}")
            raise ConnectionError(
                f"No se puede conectar a MongoDB ({mongo_uri}).\n"
                "Instala y ejecuta MongoDB Community Server desde:\n"
                "https://www.mongodb.com/try/download/community"
            ) from e

    # ──────────────────────────────────────────────────
    # Inicialización de índices y datos base
    # ──────────────────────────────────────────────────

    def _inicializar_indices(self):
        try:
            self._tickets.create_index("ID_TICKET", unique=True, background=True)
            self._tickets.create_index(
                [("USUARIO_AD", pymongo.ASCENDING), ("MAC_ADDRESS", pymongo.ASCENDING)],
                background=True
            )
            self._tickets.create_index("ESTADO", background=True)
            self._tickets.create_index("FECHA_APERTURA", background=True)
            self._tecs.create_index("ID_TECNICO", unique=True, background=True)
            self._equipos.create_index("MAC_ADDRESS", unique=True, background=True)
        except Exception as e:
            print(f"[MongoDB] Advertencia índices: {e}")

    def _inicializar_tecnicos(self):
        if self._tecs.count_documents({}) == 0:
            for tec in TECNICOS_EQUIPO:
                doc = {
                    "ID_TECNICO": tec["id"],
                    "NOMBRE": tec["nombre"],
                    "ESTADO": "Disponible",
                    "ESPECIALIDAD": tec["especialidad"],
                    "TICKETS_ATENDIDOS": 0,
                    "TICKET_ACTUAL": "",
                    "ULTIMA_ACTIVIDAD": datetime.now(),
                    "TELEFONO": tec["telefono"],
                    "EMAIL": tec["email"]
                }
                try:
                    self._tecs.insert_one(doc)
                except pymongo.errors.DuplicateKeyError:
                    pass
            print("[MongoDB] Técnicos iniciales creados")

    # ──────────────────────────────────────────────────
    # Lectura como DataFrame (para análisis y compatibilidad)
    # ──────────────────────────────────────────────────

    def _leer_datos(self) -> pd.DataFrame:
        docs = list(self._tickets.find({}, {"_id": 0}))
        df = _docs_to_df(docs, COLUMNAS_DB)
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
        docs = list(self._tecs.find({}, {"_id": 0}))
        df = _docs_to_df(docs, COLUMNAS_TECNICOS)
        if "TICKETS_ATENDIDOS" in df.columns:
            df["TICKETS_ATENDIDOS"] = pd.to_numeric(
                df["TICKETS_ATENDIDOS"], errors="coerce").fillna(0).astype(int)
        return df

    def _leer_equipos(self) -> pd.DataFrame:
        docs = list(self._equipos.find({}, {"_id": 0}))
        df = _docs_to_df(docs, COLUMNAS_EQUIPOS)
        for col in ["FECHA_COMPRA", "GARANTIA_HASTA", "FECHA_REGISTRO", "ULTIMA_CONEXION"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        for col in ["RAM_GB", "DISCO_GB", "TOTAL_TICKETS"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
        return df

    # Legacy no-op (las escrituras son operaciones atómicas de MongoDB)
    def _escribir_datos(self, df: pd.DataFrame, reintentos: int = MAX_REINTENTOS) -> bool:
        return True

    def _escribir_tecnicos(self, df: pd.DataFrame) -> bool:
        return True

    def _escribir_equipos(self, df: pd.DataFrame) -> bool:
        return True

    # ──────────────────────────────────────────────────
    # TURNO — contador atómico
    # ──────────────────────────────────────────────────

    def obtener_siguiente_turno(self) -> int:
        """Genera el siguiente número de turno del día de forma atómica."""
        fecha_hoy = str(datetime.now().date())
        result = self._counters.find_one_and_update(
            {"_id": "turno", "fecha": fecha_hoy},
            {"$inc": {"seq": 1}},
            upsert=True,
            return_document=pymongo.ReturnDocument.AFTER
        )
        return result["seq"]

    # ──────────────────────────────────────────────────
    # TÉCNICOS
    # ──────────────────────────────────────────────────

    def obtener_tecnicos(self) -> pd.DataFrame:
        return self._leer_tecnicos()

    def obtener_tecnico_por_id(self, id_tecnico: str) -> Optional[Dict]:
        return _clean_doc(self._tecs.find_one({"ID_TECNICO": id_tecnico}, {"_id": 0})) or None

    def agregar_tecnico(self, nombre: str, especialidad: str,
                        telefono: str = "", email: str = "") -> Dict:
        count = self._tecs.count_documents({})
        id_tec = f"TEC{count + 1:03d}"
        doc = {
            "ID_TECNICO": id_tec, "NOMBRE": nombre, "ESTADO": "Disponible",
            "ESPECIALIDAD": especialidad, "TICKETS_ATENDIDOS": 0,
            "TICKET_ACTUAL": "", "ULTIMA_ACTIVIDAD": datetime.now(),
            "TELEFONO": telefono, "EMAIL": email
        }
        self._tecs.insert_one(doc)
        return _clean_doc(doc)

    def eliminar_tecnico(self, id_tecnico: str) -> bool:
        return self._tecs.delete_one({"ID_TECNICO": id_tecnico}).deleted_count > 0

    def actualizar_estado_tecnico(self, id_tecnico: str, nuevo_estado: str,
                                   ticket_actual: str = "") -> bool:
        if nuevo_estado not in ESTADOS_TECNICO:
            return False
        updates: dict = {"ESTADO": nuevo_estado, "ULTIMA_ACTIVIDAD": datetime.now()}
        if ticket_actual is not None:
            updates["TICKET_ACTUAL"] = ticket_actual
        return self._tecs.update_one(
            {"ID_TECNICO": id_tecnico}, {"$set": updates}
        ).modified_count > 0

    def hay_tecnico_disponible(self) -> bool:
        return self._tecs.count_documents({"ESTADO": "Disponible"}) > 0

    def obtener_tecnicos_disponibles(self) -> pd.DataFrame:
        docs = list(self._tecs.find({"ESTADO": "Disponible"}, {"_id": 0}))
        return _docs_to_df(docs, COLUMNAS_TECNICOS)

    def asignar_ticket_a_tecnico(self, id_ticket: str, id_tecnico: str) -> bool:
        tec = self._tecs.find_one({"ID_TECNICO": id_tecnico}, {"_id": 0})
        if not tec:
            return False
        nombre = tec.get("NOMBRE", "")
        r1 = self._tickets.update_one(
            {"ID_TICKET": id_ticket},
            {"$set": {"ESTADO": "En Proceso", "TECNICO_ASIGNADO": nombre}}
        )
        r2 = self._tecs.update_one(
            {"ID_TECNICO": id_tecnico},
            {"$set": {"ESTADO": "Ocupado", "TICKET_ACTUAL": id_ticket,
                      "ULTIMA_ACTIVIDAD": datetime.now()}}
        )
        return r1.modified_count > 0 and r2.modified_count > 0

    def liberar_tecnico(self, id_tecnico: str) -> bool:
        tec = self._tecs.find_one({"ID_TECNICO": id_tecnico}, {"_id": 0})
        if not tec:
            return False
        atendidos = tec.get("TICKETS_ATENDIDOS", 0) + 1
        self._tecs.update_one(
            {"ID_TECNICO": id_tecnico},
            {"$set": {"ESTADO": "Disponible", "TICKET_ACTUAL": "",
                      "TICKETS_ATENDIDOS": atendidos,
                      "ULTIMA_ACTIVIDAD": datetime.now()}}
        )
        return True

    # ──────────────────────────────────────────────────
    # TICKETS — CRUD
    # ──────────────────────────────────────────────────

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

        doc = {
            "ID_TICKET": id_ticket,
            "TURNO": turno,
            "FECHA_APERTURA": datetime.now(),
            "USUARIO_AD": usuario_ad,
            "HOSTNAME": hostname,
            "MAC_ADDRESS": mac_address,
            "CATEGORIA": categoria,
            "PRIORIDAD": prioridad,
            "DESCRIPCION": descripcion,
            "ESTADO": estado,
            "TECNICO_ASIGNADO": "",
            "NOTAS_RESOLUCION": "",
            "HISTORIAL": "",
            "FECHA_CIERRE": None,
            "TIEMPO_ESTIMADO": 0
        }
        self._tickets.insert_one(doc)

        estado_sis = self.obtener_mensaje_estado_sistema()
        resultado  = _clean_doc(doc)
        resultado["posicion_cola"]          = self.obtener_posicion_cola(id_ticket)
        resultado["mensaje_sistema"]        = estado_sis["mensaje"]
        resultado["hay_tecnico_disponible"] = hay_disp
        resultado["tiempo_espera_estimado"] = estado_sis["tiempo_estimado"]
        return resultado

    def obtener_todos_tickets(self) -> pd.DataFrame:
        return self._leer_datos()

    def obtener_ticket_por_id(self, id_ticket: str) -> Optional[Dict]:
        doc = self._tickets.find_one({"ID_TICKET": id_ticket}, {"_id": 0})
        return _clean_doc(doc) if doc else None

    def obtener_tickets_activos(self) -> pd.DataFrame:
        docs = list(self._tickets.find(
            {"ESTADO": {"$nin": ["Cerrado", "Cancelado"]}}, {"_id": 0}
        ))
        return _docs_to_df(docs, COLUMNAS_DB)

    def obtener_tickets_en_cola(self) -> pd.DataFrame:
        docs = list(self._tickets.find(
            {"ESTADO": {"$in": ["Abierto", "En Cola"]}}, {"_id": 0}
        ).sort("TURNO", pymongo.ASCENDING))
        return _docs_to_df(docs, COLUMNAS_DB)

    def obtener_historial(self) -> pd.DataFrame:
        docs = list(self._tickets.find(
            {"ESTADO": {"$in": ["Cerrado", "Cancelado"]}}, {"_id": 0}
        ))
        return _docs_to_df(docs, COLUMNAS_DB)

    def obtener_ticket_activo_usuario(self, usuario_ad: str,
                                       mac_address: str = "") -> Optional[Dict]:
        query: dict = {
            "ESTADO": {"$nin": ["Cerrado", "Cancelado"]},
            "USUARIO_AD": re.compile(f"^{re.escape(usuario_ad)}$", re.I)
        }
        if mac_address:
            query["MAC_ADDRESS"] = re.compile(f"^{re.escape(mac_address)}$", re.I)
        doc = self._tickets.find_one(query, {"_id": 0},
                                     sort=[("FECHA_APERTURA", pymongo.DESCENDING)])
        return _clean_doc(doc) if doc else None

    def obtener_tickets_activos_usuario(self, usuario_ad: str,
                                         mac_address: str = "") -> list:
        query: dict = {
            "ESTADO": {"$nin": ["Cerrado", "Cancelado"]},
            "USUARIO_AD": re.compile(f"^{re.escape(usuario_ad)}$", re.I)
        }
        if mac_address:
            query["MAC_ADDRESS"] = re.compile(f"^{re.escape(mac_address)}$", re.I)
        docs = list(self._tickets.find(query, {"_id": 0}))
        return [_clean_doc(d) for d in docs]

    def obtener_tickets_usuario(self, usuario_ad: str, limite: int = 20,
                                 mac_address: str = "") -> list:
        query: dict = {
            "USUARIO_AD": re.compile(f"^{re.escape(usuario_ad)}$", re.I)
        }
        if mac_address:
            query["MAC_ADDRESS"] = re.compile(f"^{re.escape(mac_address)}$", re.I)
        docs = list(
            self._tickets.find(query, {"_id": 0})
            .sort("FECHA_APERTURA", pymongo.DESCENDING)
            .limit(limite)
        )
        return [_clean_doc(d) for d in docs]

    def actualizar_ticket(self, id_ticket: str,
                          estado: Optional[str] = None,
                          tecnico_asignado: Optional[str] = None,
                          notas_resolucion: Optional[str] = None,
                          historial: Optional[str] = None,
                          fecha_cierre: Optional[datetime] = None) -> bool:
        doc_actual = self._tickets.find_one({"ID_TICKET": id_ticket}, {"_id": 0})
        if not doc_actual:
            return False

        if doc_actual.get("ESTADO") in ["Cerrado", "Cancelado"]:
            raise ValueError("No se puede editar un ticket cerrado o cancelado.")

        updates: dict = {}
        if estado is not None:
            if estado not in ESTADOS_TICKET:
                raise ValueError(f"Estado inválido: {estado}")
            updates["ESTADO"] = estado
            if estado in ["Cerrado", "Cancelado"]:
                updates["FECHA_CIERRE"] = datetime.now()
        if tecnico_asignado is not None:
            updates["TECNICO_ASIGNADO"] = tecnico_asignado
        if notas_resolucion is not None:
            updates["NOTAS_RESOLUCION"] = notas_resolucion
        if historial is not None:
            updates["HISTORIAL"] = historial
        if fecha_cierre is not None:
            updates["FECHA_CIERRE"] = fecha_cierre

        if not updates:
            return True

        return self._tickets.update_one(
            {"ID_TICKET": id_ticket}, {"$set": updates}
        ).modified_count > 0

    def filtrar_tickets(self, estado: Optional[str] = None,
                        usuario: Optional[str] = None,
                        mac_address: Optional[str] = None) -> pd.DataFrame:
        query: dict = {}
        if estado:
            query["ESTADO"] = estado
        if usuario:
            query["USUARIO_AD"] = re.compile(usuario, re.I)
        if mac_address:
            query["MAC_ADDRESS"] = re.compile(mac_address, re.I)
        docs = list(self._tickets.find(query, {"_id": 0}))
        return _docs_to_df(docs, COLUMNAS_DB)

    # ──────────────────────────────────────────────────
    # COLA
    # ──────────────────────────────────────────────────

    def obtener_posicion_cola(self, id_ticket: str) -> int:
        doc = self._tickets.find_one({"ID_TICKET": id_ticket}, {"_id": 0})
        if not doc:
            return -1
        estado = doc.get("ESTADO", "")
        if estado in ["En Proceso", "Cerrado", "Cancelado"]:
            return 0
        turno = doc.get("TURNO", 0)
        hoy   = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        count = self._tickets.count_documents({
            "ESTADO": {"$in": ["Abierto", "En Cola"]},
            "TURNO": {"$lt": turno},
            "FECHA_APERTURA": {"$gte": hoy}
        })
        return count + 1

    # ──────────────────────────────────────────────────
    # ESTADO DEL SISTEMA
    # ──────────────────────────────────────────────────

    def obtener_mensaje_estado_sistema(self) -> Dict:
        disponibles  = self._tecs.count_documents({"ESTADO": "Disponible"})
        tickets_cola = self._tickets.count_documents({"ESTADO": {"$in": ["Abierto", "En Cola"]}})
        if disponibles > 0:
            nombres = [d["NOMBRE"] for d in
                       self._tecs.find({"ESTADO": "Disponible"}, {"NOMBRE": 1, "_id": 0})]
            return {
                "hay_disponible": True,
                "mensaje": f"✅ Hay {disponibles} técnico(s) disponible(s)",
                "color": "green",
                "tecnicos_disponibles": nombres,
                "tickets_en_cola": tickets_cola,
                "tiempo_estimado": tickets_cola * 15
            }
        return {
            "hay_disponible": False,
            "mensaje": "⏳ Todos los técnicos están ocupados. Se te asignará un turno.",
            "color": "orange",
            "tecnicos_disponibles": [],
            "tickets_en_cola": tickets_cola,
            "tiempo_estimado": (tickets_cola + 1) * 15
        }

    # ──────────────────────────────────────────────────
    # EQUIPOS
    # ──────────────────────────────────────────────────

    def obtener_equipos(self) -> pd.DataFrame:
        return self._leer_equipos()

    def obtener_equipo_por_mac(self, mac_address: str) -> Optional[Dict]:
        doc = self._equipos.find_one(
            {"MAC_ADDRESS": re.compile(f"^{re.escape(mac_address)}$", re.I)},
            {"_id": 0}
        )
        return _clean_doc(doc) if doc else None

    def registrar_o_actualizar_equipo(self, mac_address: str, hostname: str,
                                       usuario_ad: str) -> Dict:
        try:
            ahora = datetime.now()
            total_tickets = self._tickets.count_documents({"MAC_ADDRESS": mac_address})
            self._equipos.update_one(
                {"MAC_ADDRESS": mac_address},
                {
                    "$set": {
                        "HOSTNAME": hostname,
                        "USUARIO_ASIGNADO": usuario_ad,
                        "ULTIMA_CONEXION": ahora,
                        "TOTAL_TICKETS": total_tickets
                    },
                    "$setOnInsert": {
                        "MAC_ADDRESS": mac_address,
                        "NOMBRE_EQUIPO": hostname,
                        "GRUPO": "Sin Asignar",
                        "UBICACION": "",
                        "MARCA": "",
                        "MODELO": "",
                        "NUMERO_SERIE": "",
                        "TIPO_EQUIPO": "Desktop",
                        "SISTEMA_OPERATIVO": "",
                        "PROCESADOR": "",
                        "RAM_GB": 0,
                        "DISCO_GB": 0,
                        "FECHA_COMPRA": None,
                        "GARANTIA_HASTA": None,
                        "ESTADO_EQUIPO": "Activo",
                        "NOTAS": "",
                        "FECHA_REGISTRO": ahora
                    }
                },
                upsert=True
            )
            return self.obtener_equipo_por_mac(mac_address) or {}
        except Exception as e:
            print(f"[MongoDB] Error equipo: {e}")
            return {}

    def actualizar_equipo(self, mac_address: str, **datos) -> bool:
        if not datos:
            return False
        return self._equipos.update_one(
            {"MAC_ADDRESS": mac_address}, {"$set": datos}
        ).matched_count > 0

    def eliminar_equipo(self, mac_address: str) -> bool:
        return self._equipos.delete_one({"MAC_ADDRESS": mac_address}).deleted_count > 0

    def obtener_grupos_con_conteo(self) -> Dict[str, int]:
        pipeline = [{"$group": {"_id": "$GRUPO", "count": {"$sum": 1}}}]
        return {d["_id"] or "Sin Asignar": d["count"]
                for d in self._equipos.aggregate(pipeline)}

    def obtener_equipos_por_grupo(self, grupo: str) -> pd.DataFrame:
        docs = list(self._equipos.find({"GRUPO": grupo}, {"_id": 0}))
        return _docs_to_df(docs, COLUMNAS_EQUIPOS)

    def obtener_estadisticas_equipos(self) -> Dict:
        total = self._equipos.count_documents({})
        pipeline = [{"$group": {"_id": "$ESTADO_EQUIPO", "count": {"$sum": 1}}}]
        por_estado = {d["_id"]: d["count"] for d in self._equipos.aggregate(pipeline)}
        return {
            "total": total,
            "activos": por_estado.get("Activo", 0),
            "inactivos": por_estado.get("Inactivo", 0),
            "mantenimiento": por_estado.get("En Mantenimiento", 0),
            "bajas": por_estado.get("Baja", 0)
        }

    # ──────────────────────────────────────────────────
    # ESTADÍSTICAS / ANÁLISIS
    # ──────────────────────────────────────────────────

    def contar_tickets_abiertos_hoy(self) -> int:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        return self._tickets.count_documents({
            "FECHA_APERTURA": {"$gte": hoy},
            "ESTADO": {"$nin": ["Cerrado", "Cancelado"]}
        })

    def calcular_tiempo_promedio_cierre(self) -> float:
        try:
            docs = list(self._tickets.find(
                {"ESTADO": {"$in": ["Cerrado", "Cancelado"]},
                 "FECHA_APERTURA": {"$exists": True},
                 "FECHA_CIERRE": {"$exists": True, "$ne": None}},
                {"FECHA_APERTURA": 1, "FECHA_CIERRE": 1, "_id": 0}
            ))
            if not docs:
                return 0.0
            tiempos = []
            for d in docs:
                fa, fc = d.get("FECHA_APERTURA"), d.get("FECHA_CIERRE")
                if fa and fc:
                    if isinstance(fa, str):
                        fa = datetime.fromisoformat(fa)
                    if isinstance(fc, str):
                        fc = datetime.fromisoformat(fc)
                    diff = (fc - fa).total_seconds() / 60
                    if 0 < diff < 10000:
                        tiempos.append(diff)
            return round(sum(tiempos) / len(tiempos), 1) if tiempos else 0.0
        except Exception as e:
            print(f"[MongoDB] Error tiempo promedio: {e}")
            return 0.0

    def obtener_estadisticas_generales(self) -> Dict:
        try:
            return {
                "total_tickets": self._tickets.count_documents({}),
                "tickets_abiertos": self._tickets.count_documents({"ESTADO": "Abierto"}),
                "tickets_en_proceso": self._tickets.count_documents({"ESTADO": "En Proceso"}),
                "tickets_cerrados": self._tickets.count_documents({"ESTADO": "Cerrado"}),
                "tickets_hoy": self.contar_tickets_abiertos_hoy(),
                "tiempo_promedio_cierre": self.calcular_tiempo_promedio_cierre()
            }
        except Exception as e:
            print(f"[MongoDB] Error estadísticas: {e}")
            return {"total_tickets": 0, "tickets_abiertos": 0, "tickets_en_proceso": 0,
                    "tickets_cerrados": 0, "tickets_hoy": 0, "tiempo_promedio_cierre": 0.0}

    def obtener_distribucion_categorias(self) -> pd.DataFrame:
        pipeline = [{"$group": {"_id": "$CATEGORIA", "count": {"$sum": 1}}}]
        docs = [{"CATEGORIA": d["_id"], "TOTAL": d["count"]}
                for d in self._tickets.aggregate(pipeline)]
        return pd.DataFrame(docs) if docs else pd.DataFrame(columns=["CATEGORIA", "TOTAL"])

    def obtener_distribucion_prioridades(self) -> pd.DataFrame:
        pipeline = [{"$group": {"_id": "$PRIORIDAD", "count": {"$sum": 1}}}]
        docs = [{"PRIORIDAD": d["_id"], "TOTAL": d["count"]}
                for d in self._tickets.aggregate(pipeline)]
        return pd.DataFrame(docs) if docs else pd.DataFrame(columns=["PRIORIDAD", "TOTAL"])

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
        df["MES"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce").dt.to_period("M").astype(str)
        return df.groupby("MES").size().reset_index(name="TOTAL")

    def obtener_tickets_por_hora(self) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["HORA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce").dt.hour
        return df.groupby("HORA").size().reset_index(name="TOTAL")

    def obtener_rendimiento_tecnicos(self) -> pd.DataFrame:
        pipeline = [
            {"$match": {"ESTADO": {"$in": ["Cerrado", "Cancelado"]},
                        "TECNICO_ASIGNADO": {"$ne": "", "$exists": True}}},
            {"$group": {"_id": "$TECNICO_ASIGNADO", "tickets_atendidos": {"$sum": 1}}}
        ]
        docs = [{"NOMBRE": d["_id"], "TICKETS_ATENDIDOS": d["tickets_atendidos"]}
                for d in self._tickets.aggregate(pipeline)]
        return pd.DataFrame(docs) if docs else pd.DataFrame(
            columns=["NOMBRE", "TICKETS_ATENDIDOS"])

    def obtener_tendencia_semanal(self, semanas: int = 8) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["SEMANA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce").dt.to_period("W").astype(str)
        return df.groupby("SEMANA").size().reset_index(name="TOTAL")

    def obtener_tiempo_resolucion_por_categoria(self) -> pd.DataFrame:
        df = self._leer_datos()
        if df.empty:
            return pd.DataFrame()
        df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors="coerce")
        df["FECHA_CIERRE"]   = pd.to_datetime(df["FECHA_CIERRE"], errors="coerce")
        df = df.dropna(subset=["FECHA_APERTURA", "FECHA_CIERRE"])
        if df.empty:
            return pd.DataFrame()
        df["TIEMPO_MIN"] = (df["FECHA_CIERRE"] - df["FECHA_APERTURA"]).dt.total_seconds() / 60
        return df.groupby("CATEGORIA")["TIEMPO_MIN"].mean().reset_index()

    def obtener_equipos_problematicos(self, top_n: int = 5) -> pd.DataFrame:
        pipeline = [
            {"$group": {"_id": "$MAC_ADDRESS",
                        "total": {"$sum": 1},
                        "hostname": {"$first": "$HOSTNAME"}}},
            {"$sort": {"total": -1}},
            {"$limit": top_n}
        ]
        docs = [{"MAC_ADDRESS": d["_id"], "HOSTNAME": d.get("hostname", ""),
                 "TOTAL_TICKETS": d["total"]}
                for d in self._tickets.aggregate(pipeline)]
        return pd.DataFrame(docs) if docs else pd.DataFrame(
            columns=["MAC_ADDRESS", "HOSTNAME", "TOTAL_TICKETS"])

    def obtener_estadisticas_completas(self) -> Dict:
        generales  = self.obtener_estadisticas_generales()
        categorias = self.obtener_distribucion_categorias()
        return {
            **generales,
            "distribucion_categorias": categorias.to_dict("records") if not categorias.empty else [],
            "tecnicos": self._leer_tecnicos().to_dict("records")
        }

    # ──────────────────────────────────────────────────
    # EXPORTACIÓN EXCEL
    # ──────────────────────────────────────────────────

    def exportar_reporte_excel(self, ruta_salida: Path = None) -> str:
        if ruta_salida is None:
            ruta_salida = Path(__file__).parent / f"reporte_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        df = self._leer_datos()
        df.to_excel(str(ruta_salida), index=False, engine="openpyxl")
        return str(ruta_salida)

    # ──────────────────────────────────────────────────
    # MIGRACIÓN DESDE EXCEL
    # ──────────────────────────────────────────────────

    def migrar_desde_excel(self) -> Dict[str, int]:
        """Importa datos de los archivos Excel existentes a MongoDB (uso único)."""
        resultado = {"tickets": 0, "tecnicos": 0, "equipos": 0}
        for path, col, key, cat in [
            (EXCEL_DB_PATH, self._tickets, "ID_TICKET", "tickets"),
            (TECNICOS_DB_PATH, self._tecs, "ID_TECNICO", "tecnicos"),
            (EQUIPOS_DB_PATH, self._equipos, "MAC_ADDRESS", "equipos")
        ]:
            try:
                if path.exists():
                    df = pd.read_excel(path, engine="openpyxl")
                    for _, row in df.iterrows():
                        doc = {k: (None if pd.isna(v) else v)
                               for k, v in row.to_dict().items()}
                        doc.pop("_id", None)
                        id_val = doc.get(key, "")
                        if not id_val:
                            continue
                        try:
                            col.update_one({key: id_val}, {"$setOnInsert": doc}, upsert=True)
                            resultado[cat] += 1
                        except Exception:
                            pass
                    print(f"[Migración] {resultado[cat]} {cat} migrados")
            except Exception as e:
                print(f"[Migración] Error {cat}: {e}")
        return resultado

    # ──────────────────────────────────────────────────
    # MAC Address
    # ──────────────────────────────────────────────────

    def obtener_mac_address(self) -> str:
        return obtener_mac_address()


# =============================================================================
# FUNCIONES UTILITARIAS DE RED
# =============================================================================

def obtener_mac_address() -> str:
    try:
        import getmac
        mac = getmac.get_mac_address()
        return mac.upper() if mac else "00:00:00:00:00:00"
    except Exception:
        return "00:00:00:00:00:00"


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
            "ULTIMO_PING": datetime.now()
        }
    return None


# =============================================================================
# ESCÁNER DE RED
# =============================================================================

class EscanerRed:
    """Escanea la red local. Persiste resultados en MongoDB."""

    def __init__(self, gestor: Optional[GestorTickets] = None):
        self._gestor  = gestor
        self.escaneando = False

    def escanear_red(self, rango_inicio: int = 1, rango_fin: int = 254,
                     hilos: int = 50) -> List[Dict]:
        self.escaneando = True
        try:
            ip_local = socket.gethostbyname(socket.gethostname())
            red_base = ".".join(ip_local.split(".")[:3])
        except Exception:
            red_base = "192.168.1"

        ips = [f"{red_base}.{i}" for i in range(rango_inicio, rango_fin + 1)]
        encontrados: List[Dict] = []

        with ThreadPoolExecutor(max_workers=hilos) as executor:
            futures = {executor.submit(escanear_ip, ip): ip for ip in ips}
            for future in as_completed(futures):
                if not self.escaneando:
                    break
                result = future.result()
                if result:
                    encontrados.append(result)
                    if self._gestor is not None:
                        try:
                            self._gestor._red.update_one(
                                {"IP_ADDRESS": result["IP_ADDRESS"]},
                                {
                                    "$set": result,
                                    "$setOnInsert": {
                                        "PRIMERA_VEZ": datetime.now(),
                                        "IP_ANTERIOR": "",
                                        "CAMBIOS_IP": 0,
                                        "COMENTARIO": ""
                                    }
                                },
                                upsert=True
                            )
                        except Exception:
                            pass
        self.escaneando = False
        return encontrados

    def detener_escaneo(self):
        self.escaneando = False

    def obtener_historial_red(self) -> pd.DataFrame:
        if self._gestor is None:
            return pd.DataFrame(columns=COLUMNAS_RED)
        docs = list(self._gestor._red.find({}, {"_id": 0}))
        return _docs_to_df(docs, COLUMNAS_RED)


# Compatibilidad: algunos módulos importan GestorRed
GestorRed = EscanerRed
