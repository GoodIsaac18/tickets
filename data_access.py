# =============================================================================
# MÓDULO DE ACCESO A DATOS - data_access.py
# =============================================================================
# Este módulo contiene toda la lógica de persistencia y manipulación de datos
# utilizando pandas y openpyxl para manejar archivos Excel como base de datos.
# Está diseñado para ser independiente de la interfaz gráfica.
# Incluye gestión de técnicos, estados, sistema de turnos y escaneo de red.
# =============================================================================

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
from typing import Optional, List, Dict, Any, Callable
from pathlib import Path

# =============================================================================
# CONFIGURACIÓN GLOBAL
# =============================================================================

# Ruta del archivo Excel que actúa como base de datos compartida
EXCEL_DB_PATH = Path(__file__).parent / "tickets_db.xlsx"
TECNICOS_DB_PATH = Path(__file__).parent / "tecnicos_db.xlsx"
EQUIPOS_DB_PATH = Path(__file__).parent / "equipos_db.xlsx"
RED_DB_PATH = Path(__file__).parent / "red_db.xlsx"

# Configuración del servidor de tickets
SERVIDOR_PUERTO = 5555
SERVIDOR_CONFIG_PATH = Path(__file__).parent / "servidor_config.txt"

# Definición de los encabezados y estructura de la base de datos de tickets
COLUMNAS_DB = [
    "ID_TICKET",           # String/UUID único - Identificador del ticket
    "TURNO",               # Int - Número de turno asignado
    "FECHA_APERTURA",      # Datetime - Fecha y hora de creación
    "USUARIO_AD",          # String - Usuario de Active Directory
    "HOSTNAME",            # String - Nombre de red del equipo
    "MAC_ADDRESS",         # String - Dirección MAC del hardware
    "CATEGORIA",           # Dropdown - Tipo de incidencia
    "PRIORIDAD",           # String - Alta, Media, Baja
    "DESCRIPCION",         # Long Text - Descripción del problema
    "ESTADO",              # Enum - Estado actual del ticket
    "TECNICO_ASIGNADO",    # String - Técnico responsable
    "NOTAS_RESOLUCION",    # Long Text - Notas de resolución
    "FECHA_CIERRE",        # Datetime - Fecha de cierre
    "TIEMPO_ESTIMADO"      # Int - Minutos estimados de resolución
]

# Columnas para base de datos de técnicos
COLUMNAS_TECNICOS = [
    "ID_TECNICO",          # String - Identificador único
    "NOMBRE",              # String - Nombre del técnico
    "ESTADO",              # String - Disponible/Ocupado/Ausente/En Descanso
    "ESPECIALIDAD",        # String - Área de especialización
    "TICKETS_ATENDIDOS",   # Int - Total de tickets atendidos
    "TICKET_ACTUAL",       # String - ID del ticket en atención
    "ULTIMA_ACTIVIDAD",    # Datetime - Última actividad registrada
    "TELEFONO",            # String - Número de contacto
    "EMAIL"                # String - Correo electrónico
]

# Columnas para base de datos de equipos/inventario
COLUMNAS_EQUIPOS = [
    "MAC_ADDRESS",         # String - Dirección MAC (clave primaria)
    "NOMBRE_EQUIPO",       # String - Nombre asignado por IT
    "HOSTNAME",            # String - Nombre de red detectado
    "USUARIO_ASIGNADO",    # String - Usuario principal del equipo
    "GRUPO",               # String - Grupo/Departamento
    "UBICACION",           # String - Ubicación física
    "MARCA",               # String - Marca del equipo
    "MODELO",              # String - Modelo del equipo
    "NUMERO_SERIE",        # String - Número de serie
    "TIPO_EQUIPO",         # String - Desktop/Laptop/Servidor/Impresora/Otro
    "SISTEMA_OPERATIVO",   # String - Sistema operativo
    "PROCESADOR",          # String - CPU
    "RAM_GB",              # Int - Memoria RAM en GB
    "DISCO_GB",            # Int - Almacenamiento en GB
    "FECHA_COMPRA",        # Date - Fecha de adquisición
    "GARANTIA_HASTA",      # Date - Fecha fin de garantía
    "ESTADO_EQUIPO",       # String - Activo/Inactivo/Mantenimiento/Baja
    "NOTAS",               # Text - Notas adicionales
    "FECHA_REGISTRO",      # Datetime - Fecha de registro en sistema
    "ULTIMA_CONEXION",     # Datetime - Última vez que se conectó
    "TOTAL_TICKETS"        # Int - Cantidad de tickets generados
]

# Grupos predefinidos para equipos
GRUPOS_EQUIPOS = [
    "Administración",
    "Contabilidad", 
    "Recursos Humanos",
    "Ventas",
    "Marketing",
    "Producción",
    "Almacén",
    "Gerencia",
    "IT",
    "Recepción",
    "Sin Asignar"
]

# Tipos de equipo
TIPOS_EQUIPO = ["Desktop", "Laptop", "Servidor", "Impresora", "Router/Switch", "Otro"]

# Estados de equipo
ESTADOS_EQUIPO = ["Activo", "Inactivo", "En Mantenimiento", "Baja"]

# Columnas para base de datos de red/escaneo
COLUMNAS_RED = [
    "IP_ADDRESS",          # String - Dirección IP actual
    "MAC_ADDRESS",         # String - Dirección MAC
    "HOSTNAME",            # String - Nombre de red
    "ESTADO_RED",          # String - Online/Offline
    "ULTIMO_PING",         # Datetime - Última vez que respondió
    "PRIMERA_VEZ",         # Datetime - Primera detección
    "IP_ANTERIOR",         # String - IP anterior (si cambió)
    "CAMBIOS_IP",          # Int - Cantidad de veces que cambió IP
    "COMENTARIO"           # String - Notas del admin
]

# Estados de red
ESTADOS_RED = ["Online", "Offline", "Desconocido"]

# Categorías disponibles para clasificar los tickets
CATEGORIAS_DISPONIBLES = ["Red", "Hardware", "Software", "Accesos", "Impresoras", "Email", "Otros"]

# Estados posibles de un ticket
ESTADOS_TICKET = ["Abierto", "En Cola", "En Proceso", "En Espera", "Cerrado", "Cancelado"]

# Estados posibles de técnicos
ESTADOS_TECNICO = ["Disponible", "Ocupado", "Ausente", "En Descanso"]

# Prioridades de tickets
PRIORIDADES = ["Alta", "Media", "Baja"]

# Técnicos del equipo (configuración inicial)
TECNICOS_EQUIPO = [
    {"id": "TEC001", "nombre": "Carlos Rodríguez", "especialidad": "Hardware/Red", "telefono": "ext. 101", "email": "carlos.rodriguez@empresa.com"},
    {"id": "TEC002", "nombre": "María García", "especialidad": "Software/Accesos", "telefono": "ext. 102", "email": "maria.garcia@empresa.com"}
]

# Número máximo de reintentos si el archivo está bloqueado
MAX_REINTENTOS = 3
TIEMPO_ESPERA_REINTENTO = 2

# Lock global para operaciones de archivos Excel (protección contra race conditions)
import threading
_lock_tickets_db = threading.RLock()
_lock_tecnicos_db = threading.RLock()
_lock_equipos_db = threading.RLock()


# =============================================================================
# CLASE PRINCIPAL DE ACCESO A DATOS
# =============================================================================

class GestorTickets:
    """
    Clase que encapsula todas las operaciones de lectura y escritura
    sobre la base de datos de tickets en formato Excel.
    
    Implementa el patrón Repository para separar la lógica de datos
    de la lógica de presentación. Incluye gestión de técnicos, turnos y equipos.
    Thread-safe con locks para operaciones concurrentes.
    """
    
    def __init__(self, ruta_excel: Path = EXCEL_DB_PATH, ruta_tecnicos: Path = TECNICOS_DB_PATH, ruta_equipos: Path = EQUIPOS_DB_PATH):
        """
        Constructor de la clase GestorTickets.
        
        Args:
            ruta_excel: Ruta al archivo Excel de tickets.
            ruta_tecnicos: Ruta al archivo Excel de técnicos.
            ruta_equipos: Ruta al archivo Excel de equipos/inventario.
        """
        self.ruta_excel = ruta_excel
        self.ruta_tecnicos = ruta_tecnicos
        self.ruta_equipos = ruta_equipos
        
        # Intentar inicializar las bases de datos con manejo robusto de errores
        try:
            self._asegurar_existencia_db()
        except Exception as e:
            print(f"[WARNING] Error al crear DB de tickets: {e}")
            print(f"[INFO] Usando base de datos en memoria para tickets")
        
        try:
            self._asegurar_existencia_tecnicos()
        except Exception as e:
            print(f"[WARNING] Error al crear DB de técnicos: {e}")
            print(f"[INFO] Usando base de datos en memoria para técnicos")
        
        try:
            self._asegurar_existencia_equipos()
        except Exception as e:
            print(f"[WARNING] Error al crear DB de equipos: {e}")
            print(f"[INFO] Usando base de datos en memoria para equipos")
    
    def _asegurar_existencia_db(self) -> None:
        """
        Verifica si el archivo Excel de tickets existe. Si no existe, lo crea.
        """
        try:
            if not self.ruta_excel.exists():
                # Asegurar que el directorio existe
                self.ruta_excel.parent.mkdir(parents=True, exist_ok=True)
                
                df_vacio = pd.DataFrame(columns=COLUMNAS_DB)
                df_vacio.to_excel(self.ruta_excel, index=False, engine='openpyxl')
                print(f"[INFO] Base de datos de tickets creada en: {self.ruta_excel}")
            elif not self._validar_integridad_db(self.ruta_excel, COLUMNAS_DB):
                # Si existe pero está corrupta, recrearla
                print(f"[WARNING] Base de datos de tickets corrupta, recreando...")
                self.ruta_excel.unlink()
                df_vacio = pd.DataFrame(columns=COLUMNAS_DB)
                df_vacio.to_excel(self.ruta_excel, index=False, engine='openpyxl')
                print(f"[INFO] Base de datos de tickets recreada")
        except PermissionError:
            print(f"[ERROR] Permiso denegado para crear: {self.ruta_excel}")
            raise
        except Exception as e:
            print(f"[ERROR] Error inesperado al crear DB de tickets: {type(e).__name__}: {e}")
            raise
    
    def _asegurar_existencia_tecnicos(self) -> None:
        """
        Verifica si el archivo de técnicos existe. Si no, lo crea con los técnicos iniciales.
        """
        try:
            if not self.ruta_tecnicos.exists():
                # Asegurar que el directorio existe
                self.ruta_tecnicos.parent.mkdir(parents=True, exist_ok=True)
                
                tecnicos_iniciales = []
                for tec in TECNICOS_EQUIPO:
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
                df_tecnicos.to_excel(self.ruta_tecnicos, index=False, engine='openpyxl')
                print(f"[INFO] Base de datos de técnicos creada en: {self.ruta_tecnicos}")
            elif not self._validar_integridad_db(self.ruta_tecnicos, COLUMNAS_TECNICOS):
                # Si existe pero está corrupta, recrearla
                print(f"[WARNING] Base de datos de técnicos corrupta, recreando...")
                self.ruta_tecnicos.unlink()
                tecnicos_iniciales = []
                for tec in TECNICOS_EQUIPO:
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
                df_tecnicos.to_excel(self.ruta_tecnicos, index=False, engine='openpyxl')
                print(f"[INFO] Base de datos de técnicos recreada")
        except PermissionError:
            print(f"[ERROR] Permiso denegado para crear: {self.ruta_tecnicos}")
            raise
        except Exception as e:
            print(f"[ERROR] Error inesperado al crear DB de técnicos: {type(e).__name__}: {e}")
            raise
    
    def _asegurar_existencia_equipos(self) -> None:
        """
        Verifica si el archivo de equipos/inventario existe. Si no, lo crea vacío.
        """
        try:
            if not self.ruta_equipos.exists():
                # Asegurar que el directorio existe
                self.ruta_equipos.parent.mkdir(parents=True, exist_ok=True)
                
                df_equipos = pd.DataFrame(columns=COLUMNAS_EQUIPOS)
                df_equipos.to_excel(self.ruta_equipos, index=False, engine='openpyxl')
                print(f"[INFO] Base de datos de equipos creada en: {self.ruta_equipos}")
            elif not self._validar_integridad_db(self.ruta_equipos, COLUMNAS_EQUIPOS):
                # Si existe pero está corrupta, recrearla
                print(f"[WARNING] Base de datos de equipos corrupta, recreando...")
                self.ruta_equipos.unlink()
                df_equipos = pd.DataFrame(columns=COLUMNAS_EQUIPOS)
                df_equipos.to_excel(self.ruta_equipos, index=False, engine='openpyxl')
                print(f"[INFO] Base de datos de equipos recreada")
        except PermissionError:
            print(f"[ERROR] Permiso denegado para crear: {self.ruta_equipos}")
            raise
        except Exception as e:
            print(f"[ERROR] Error inesperado al crear DB de equipos: {type(e).__name__}: {e}")
            raise
    
    def _validar_integridad_db(self, ruta: Path, columnas_esperadas: list) -> bool:
        """
        Valida que el archivo Excel tenga las columnas esperadas.
        
        Args:
            ruta: Ruta al archivo Excel.
            columnas_esperadas: Lista de columnas que se esperan.
        
        Returns:
            True si la DB es válida, False si está corrupta.
        """
        try:
            df = pd.read_excel(ruta, engine='openpyxl', nrows=0)
            # Verificar que al menos tenga las columnas clave
            for col in columnas_esperadas[:3]:  # Verificar primeras 3 columnas
                if col not in df.columns:
                    return False
            return True
        except:
            return False
    
    def _leer_datos(self) -> pd.DataFrame:
        """
        Lee todos los datos del archivo Excel y los retorna como DataFrame.
        Thread-safe con lock.
        
        Returns:
            DataFrame con todos los tickets almacenados. Retorna vacío si hay error.
        """
        with _lock_tickets_db:
            max_intentos = 3
            for intento in range(max_intentos):
                try:
                    # Verificar que el archivo existe
                    if not self.ruta_excel.exists():
                        print(f"[WARNING] Archivo de tickets no existe, creando...")
                        self._asegurar_existencia_db()
                        return pd.DataFrame(columns=COLUMNAS_DB)
                    
                    # Intentar leer el archivo
                    df = pd.read_excel(self.ruta_excel, engine='openpyxl')
                    
                    # Si el DataFrame está vacío, retornar con columnas correctas
                    if df.empty:
                        df = pd.DataFrame(columns=COLUMNAS_DB)
                        return df
                    
                    # Asegurar tipos de datos correctos
                    for col in ["FECHA_APERTURA", "FECHA_CIERRE", "ULTIMA_ACTIVIDAD"]:
                        if col in df.columns:
                            try:
                                df[col] = pd.to_datetime(df[col], errors='coerce')
                            except:
                                continue
                    
                    # Manejar columnas numéricas
                    for col in ["TURNO", "TIEMPO_ESTIMADO"]:
                        if col in df.columns:
                            try:
                                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                            except:
                                continue
                    
                    # Manejar columnas de texto
                    for col in ["TECNICO_ASIGNADO", "NOTAS_RESOLUCION"]:
                        if col in df.columns:
                            try:
                                df[col] = df[col].fillna("").astype(str)
                                df[col] = df[col].replace("nan", "")
                            except:
                                continue
                    
                    return df
                    
                except PermissionError:
                    if intento < max_intentos - 1:
                        print(f"[WARNING] Permiso denegado al leer DB, reintentando ({intento + 1}/{max_intentos})...")
                        time.sleep(0.5)
                        continue
                    else:
                        print(f"[ERROR] Permiso denegado después de {max_intentos} intentos")
                        return pd.DataFrame(columns=COLUMNAS_DB)
                
                except Exception as e:
                    if intento < max_intentos - 1:
                        print(f"[WARNING] Error leyendo DB: {type(e).__name__}, reintentando ({intento + 1}/{max_intentos})...")
                        time.sleep(0.5)
                        continue
                    else:
                        print(f"[ERROR] Error al leer base de datos después de {max_intentos} intentos: {e}")
                        return pd.DataFrame(columns=COLUMNAS_DB)
    
    def _escribir_datos(self, df: pd.DataFrame, reintentos: int = MAX_REINTENTOS) -> bool:
        """
        Escribe el DataFrame completo al archivo Excel.
        Thread-safe con lock.
        
        Implementa lógica de reintentos para manejar casos donde
        el archivo está bloqueado por otro usuario.
        
        Args:
            df: DataFrame con los datos a escribir.
            reintentos: Número de intentos antes de fallar.
        
        Returns:
            True si la escritura fue exitosa, False en caso contrario.
        
        Raises:
            PermissionError: Si después de todos los reintentos no se puede escribir.
        """
        with _lock_tickets_db:
            # Convertir fechas a string para evitar problemas de Excel
            df_copy = df.copy()
            for col in ["FECHA_APERTURA", "FECHA_CIERRE", "ULTIMA_ACTIVIDAD"]:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col].apply(
                        lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) and hasattr(x, 'strftime') else (str(x) if pd.notna(x) else "")
                    )
            
            # Manejar columnas numéricas - convertir valores vacíos/None a 0
            for col in ["TURNO", "TIEMPO_ESTIMADO"]:
                if col in df_copy.columns:
                    # Reemplazar None, NaN y strings vacíos con 0, luego convertir a int
                    df_copy[col] = df_copy[col].fillna(0)
                    df_copy[col] = df_copy[col].replace("", 0)
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0).astype(int)
            
            for intento in range(reintentos):
                try:
                    df_copy.to_excel(self.ruta_excel, index=False, engine='openpyxl')
                    return True
                except PermissionError:
                    if intento < reintentos - 1:
                        print(f"[AVISO] Archivo bloqueado. Reintentando en {TIEMPO_ESPERA_REINTENTO}s... ({intento + 1}/{reintentos})")
                        time.sleep(TIEMPO_ESPERA_REINTENTO)
                    else:
                        raise PermissionError(
                            f"No se pudo acceder al archivo después de {reintentos} intentos. "
                            "Por favor, cierre el archivo Excel si está abierto."
                        )
                except Exception as e:
                    print(f"[ERROR] Error escribiendo datos: {e}")
                    return False
            return False
    
    # =========================================================================
    # FUNCIONES DE GESTIÓN DE TÉCNICOS
    # =========================================================================
    
    def _leer_tecnicos(self) -> pd.DataFrame:
        """Lee la base de datos de técnicos con reintentos."""
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                if not self.ruta_tecnicos.exists():
                    self._asegurar_existencia_tecnicos()
                    return pd.DataFrame(columns=COLUMNAS_TECNICOS)
                
                df = pd.read_excel(self.ruta_tecnicos, engine='openpyxl')
                
                if df.empty:
                    return pd.DataFrame(columns=COLUMNAS_TECNICOS)
                
                if "ULTIMA_ACTIVIDAD" in df.columns:
                    try:
                        df["ULTIMA_ACTIVIDAD"] = pd.to_datetime(df["ULTIMA_ACTIVIDAD"], errors='coerce')
                    except:
                        pass
                if "TICKETS_ATENDIDOS" in df.columns:
                    try:
                        df["TICKETS_ATENDIDOS"] = pd.to_numeric(df["TICKETS_ATENDIDOS"], errors='coerce').fillna(0).astype(int)
                    except:
                        pass
                if "TICKET_ACTUAL" in df.columns:
                    try:
                        df["TICKET_ACTUAL"] = df["TICKET_ACTUAL"].fillna("").astype(str)
                        df["TICKET_ACTUAL"] = df["TICKET_ACTUAL"].replace("nan", "")
                    except:
                        pass
                return df
            except PermissionError:
                if intento < max_intentos - 1:
                    print(f"[WARNING] Permiso al leer técnicos, reintentando...")
                    time.sleep(0.5)
                    continue
                return pd.DataFrame(columns=COLUMNAS_TECNICOS)
            except Exception as e:
                if intento < max_intentos - 1:
                    print(f"[WARNING] Error técnicos: {type(e).__name__}")
                    time.sleep(0.5)
                    continue
                print(f"[ERROR] Técnicos: {e}")
                return pd.DataFrame(columns=COLUMNAS_TECNICOS)

    def _escribir_tecnicos(self, df: pd.DataFrame) -> bool:
        """Escribe la base de datos de técnicos."""
        try:
            # Convertir fechas a string
            df_copy = df.copy()
            if "ULTIMA_ACTIVIDAD" in df_copy.columns:
                df_copy["ULTIMA_ACTIVIDAD"] = df_copy["ULTIMA_ACTIVIDAD"].apply(
                    lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) and hasattr(x, 'strftime') else (str(x) if pd.notna(x) else "")
                )
            # Manejar columnas numéricas
            if "TICKETS_ATENDIDOS" in df_copy.columns:
                df_copy["TICKETS_ATENDIDOS"] = df_copy["TICKETS_ATENDIDOS"].fillna(0)
                df_copy["TICKETS_ATENDIDOS"] = df_copy["TICKETS_ATENDIDOS"].replace("", 0)
                df_copy["TICKETS_ATENDIDOS"] = pd.to_numeric(df_copy["TICKETS_ATENDIDOS"], errors='coerce').fillna(0).astype(int)
            df_copy.to_excel(self.ruta_tecnicos, index=False, engine='openpyxl')
            return True
        except Exception as e:
            print(f"[ERROR] Error escribiendo técnicos: {e}")
            return False
    
    def obtener_tecnicos(self) -> pd.DataFrame:
        """Obtiene todos los técnicos."""
        return self._leer_tecnicos()
    
    def obtener_tecnico_por_id(self, id_tecnico: str) -> Optional[Dict[str, Any]]:
        """Obtiene un técnico por su ID."""
        df = self._leer_tecnicos()
        tecnico = df[df["ID_TECNICO"] == id_tecnico]
        return tecnico.iloc[0].to_dict() if not tecnico.empty else None
    
    def agregar_tecnico(self, nombre: str, especialidad: str, telefono: str = "", email: str = "") -> Dict[str, Any]:
        """
        Agrega un nuevo técnico al sistema.
        
        Args:
            nombre: Nombre completo del técnico.
            especialidad: Área de especialización.
            telefono: Número de teléfono (opcional).
            email: Correo electrónico (opcional).
        
        Returns:
            Diccionario con los datos del técnico creado.
        """
        df = self._leer_tecnicos()
        
        # Generar ID único
        id_tecnico = f"TEC{len(df) + 1:03d}"
        
        # Verificar que el ID no exista
        while id_tecnico in df["ID_TECNICO"].values:
            num = int(id_tecnico[3:]) + 1
            id_tecnico = f"TEC{num:03d}"
        
        nuevo_tecnico = {
            "ID_TECNICO": id_tecnico,
            "NOMBRE": nombre,
            "ESPECIALIDAD": especialidad,
            "ESTADO": "Disponible",
            "TICKET_ACTUAL": "",
            "TICKETS_ATENDIDOS": 0,
            "ULTIMA_ACTIVIDAD": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "TELEFONO": telefono,
            "EMAIL": email
        }
        
        df = pd.concat([df, pd.DataFrame([nuevo_tecnico])], ignore_index=True)
        self._escribir_tecnicos(df)
        
        return nuevo_tecnico
    
    def eliminar_tecnico(self, id_tecnico: str) -> bool:
        """
        Elimina un técnico del sistema.
        
        Args:
            id_tecnico: ID del técnico a eliminar.
        
        Returns:
            True si se eliminó correctamente, False si no existe o está ocupado.
        """
        df = self._leer_tecnicos()
        idx = df[df["ID_TECNICO"] == id_tecnico].index
        
        if idx.empty:
            return False
        
        # No permitir eliminar si está ocupado
        if df.at[idx[0], "ESTADO"] == "Ocupado":
            return False
        
        df = df.drop(idx)
        self._escribir_tecnicos(df)
        return True
    
    def actualizar_estado_tecnico(self, id_tecnico: str, nuevo_estado: str, ticket_actual: str = "") -> bool:
        """
        Actualiza el estado de un técnico.
        
        Args:
            id_tecnico: ID del técnico.
            nuevo_estado: Nuevo estado (Disponible/Ocupado/Ausente/En Descanso).
            ticket_actual: ID del ticket que está atendiendo (si aplica).
        """
        if nuevo_estado not in ESTADOS_TECNICO:
            return False
        
        df = self._leer_tecnicos()
        idx = df[df["ID_TECNICO"] == id_tecnico].index
        
        if idx.empty:
            return False
        
        # Convertir columna ULTIMA_ACTIVIDAD a object para evitar problemas de dtype
        if "ULTIMA_ACTIVIDAD" in df.columns:
            df["ULTIMA_ACTIVIDAD"] = df["ULTIMA_ACTIVIDAD"].astype(object)
        
        df.at[idx[0], "ESTADO"] = nuevo_estado
        df.at[idx[0], "TICKET_ACTUAL"] = ticket_actual
        df.at[idx[0], "ULTIMA_ACTIVIDAD"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if nuevo_estado == "Disponible":
            df.at[idx[0], "TICKET_ACTUAL"] = ""
        
        return self._escribir_tecnicos(df)
    
    def hay_tecnico_disponible(self) -> bool:
        """Verifica si hay al menos un técnico disponible."""
        df = self._leer_tecnicos()
        return len(df[df["ESTADO"] == "Disponible"]) > 0
    
    def obtener_tecnicos_disponibles(self) -> pd.DataFrame:
        """Obtiene los técnicos disponibles."""
        df = self._leer_tecnicos()
        return df[df["ESTADO"] == "Disponible"]
    
    def obtener_siguiente_turno(self) -> int:
        """Genera el siguiente número de turno del día basado en tickets activos."""
        try:
            df = self._leer_datos()
            if df.empty:
                return 1
            
            # Filtrar tickets de hoy que NO estén cerrados ni cancelados
            hoy = datetime.now().date()
            df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors='coerce')
            df = df.dropna(subset=["FECHA_APERTURA"])
            
            if df.empty:
                return 1
            
            # Solo tickets de hoy que están activos (no cerrados ni cancelados)
            tickets_hoy = df[(df["FECHA_APERTURA"].dt.date == hoy) & (~df["ESTADO"].isin(["Cerrado", "Cancelado"]))]
            
            if tickets_hoy.empty or "TURNO" not in tickets_hoy.columns:
                return 1
            
            # El turno es simplemente la cantidad de tickets activos + 1
            return len(tickets_hoy) + 1
        except Exception as e:
            print(f"[ERROR] Error obteniendo siguiente turno: {e}")
            return 1
    
    def obtener_posicion_cola(self, id_ticket: str) -> int:
        """
        Obtiene la posición en la cola de un ticket.
        
        Returns:
            Posición en cola (1 = siguiente), 0 si ya está siendo atendido, -1 si no existe.
        """
        df = self._leer_datos()
        ticket = df[df["ID_TICKET"] == id_ticket]
        
        if ticket.empty:
            return -1
        
        estado = ticket.iloc[0]["ESTADO"]
        if estado in ["En Proceso", "Cerrado"]:
            return 0
        
        # Contar solo tickets en cola de hoy antes de este
        hoy = datetime.now().date()
        df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors='coerce')
        
        turno_ticket = ticket.iloc[0].get("TURNO", 0)
        fecha_ticket = ticket.iloc[0].get("FECHA_APERTURA")
        
        # Solo contar tickets activos del mismo día
        tickets_cola = df[
            (df["ESTADO"].isin(["Abierto", "En Cola"])) & 
            (df["FECHA_APERTURA"].dt.date == hoy)
        ]
        
        if tickets_cola.empty:
            return 1
        
        posicion = len(tickets_cola[tickets_cola["TURNO"] < turno_ticket]) + 1
        return posicion
    
    def asignar_ticket_a_tecnico(self, id_ticket: str, id_tecnico: str) -> bool:
        """Asigna un ticket a un técnico y actualiza estados."""
        df_tickets = self._leer_datos()
        df_tecnicos = self._leer_tecnicos()
        
        idx_ticket = df_tickets[df_tickets["ID_TICKET"] == id_ticket].index
        idx_tecnico = df_tecnicos[df_tecnicos["ID_TECNICO"] == id_tecnico].index
        
        if idx_ticket.empty or idx_tecnico.empty:
            return False
        
        nombre_tecnico = df_tecnicos.at[idx_tecnico[0], "NOMBRE"]
        
        # Actualizar ticket
        df_tickets.at[idx_ticket[0], "ESTADO"] = "En Proceso"
        df_tickets.at[idx_ticket[0], "TECNICO_ASIGNADO"] = nombre_tecnico
        
        # Convertir columna ULTIMA_ACTIVIDAD a object para evitar problemas de dtype
        if "ULTIMA_ACTIVIDAD" in df_tecnicos.columns:
            df_tecnicos["ULTIMA_ACTIVIDAD"] = df_tecnicos["ULTIMA_ACTIVIDAD"].astype(object)
        
        # Actualizar técnico
        df_tecnicos.at[idx_tecnico[0], "ESTADO"] = "Ocupado"
        df_tecnicos.at[idx_tecnico[0], "TICKET_ACTUAL"] = id_ticket
        df_tecnicos.at[idx_tecnico[0], "ULTIMA_ACTIVIDAD"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._escribir_datos(df_tickets)
        self._escribir_tecnicos(df_tecnicos)
        return True
    
    def liberar_tecnico(self, id_tecnico: str) -> bool:
        """Libera un técnico y marca su ticket actual como cerrado."""
        df = self._leer_tecnicos()
        idx = df[df["ID_TECNICO"] == id_tecnico].index
        
        if idx.empty:
            return False
        
        ticket_actual = df.at[idx[0], "TICKET_ACTUAL"]
        tickets_atendidos = df.at[idx[0], "TICKETS_ATENDIDOS"]
        
        # Convertir columna ULTIMA_ACTIVIDAD a object para evitar problemas de dtype
        if "ULTIMA_ACTIVIDAD" in df.columns:
            df["ULTIMA_ACTIVIDAD"] = df["ULTIMA_ACTIVIDAD"].astype(object)
        
        df.at[idx[0], "ESTADO"] = "Disponible"
        df.at[idx[0], "TICKET_ACTUAL"] = ""
        df.at[idx[0], "TICKETS_ATENDIDOS"] = tickets_atendidos + 1
        df.at[idx[0], "ULTIMA_ACTIVIDAD"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        self._escribir_tecnicos(df)
        return True
    
    def obtener_tickets_en_cola(self) -> pd.DataFrame:
        """Obtiene tickets en cola ordenados por turno."""
        df = self._leer_datos()
        cola = df[df["ESTADO"].isin(["Abierto", "En Cola"])]
        if not cola.empty and "TURNO" in cola.columns:
            cola = cola.sort_values("TURNO")
        return cola
    
    def obtener_historial(self) -> pd.DataFrame:
        """
        Obtiene todos los tickets cerrados (historial).
        
        Los tickets cerrados no pueden ser editados ni eliminados.
        
        Returns:
            DataFrame con tickets cerrados ordenados por fecha de cierre (más recientes primero).
        """
        df = self._leer_datos()
        cerrados = df[df["ESTADO"] == "Cerrado"].copy()
        
        if not cerrados.empty:
            # Convertir fecha de cierre y ordenar
            cerrados["FECHA_CIERRE"] = pd.to_datetime(cerrados["FECHA_CIERRE"], errors='coerce')
            cerrados = cerrados.sort_values("FECHA_CIERRE", ascending=False)
        
        return cerrados
    
    def obtener_tickets_activos(self) -> pd.DataFrame:
        """
        Obtiene todos los tickets que NO están cerrados ni cancelados.
        
        Returns:
            DataFrame con tickets activos (abiertos, en proceso, etc).
        """
        df = self._leer_datos()
        return df[~df["ESTADO"].isin(["Cerrado", "Cancelado"])]
    
    def obtener_ticket_activo_usuario(self, usuario_ad: str) -> Optional[Dict]:
        """
        Obtiene el ticket activo más reciente de un usuario específico.
        
        Args:
            usuario_ad: Usuario de Active Directory.
            
        Returns:
            Diccionario con el ticket activo o None si no hay.
        """
        df = self._leer_datos()
        # Filtrar por usuario y tickets no cerrados ni cancelados
        tickets_usuario = df[
            (df["USUARIO_AD"].str.lower() == usuario_ad.lower()) & 
            (~df["ESTADO"].isin(["Cerrado", "Cancelado"]))
        ]
        
        if tickets_usuario.empty:
            return None
        
        # Retornar el más reciente
        return tickets_usuario.iloc[-1].to_dict()
    
    def obtener_mensaje_estado_sistema(self) -> Dict[str, Any]:
        """
        Obtiene el mensaje de estado del sistema para mostrar al usuario.
        
        Returns:
            Diccionario con información del estado del sistema.
        """
        df_tecnicos = self._leer_tecnicos()
        disponibles = df_tecnicos[df_tecnicos["ESTADO"] == "Disponible"]
        ocupados = df_tecnicos[df_tecnicos["ESTADO"] == "Ocupado"]
        
        tickets_cola = len(self.obtener_tickets_en_cola())
        
        if len(disponibles) > 0:
            return {
                "hay_disponible": True,
                "mensaje": f"✅ Hay {len(disponibles)} técnico(s) disponible(s)",
                "color": "green",
                "tecnicos_disponibles": disponibles["NOMBRE"].tolist(),
                "tickets_en_cola": tickets_cola,
                "tiempo_estimado": tickets_cola * 15  # 15 min promedio por ticket
            }
        else:
            return {
                "hay_disponible": False,
                "mensaje": "⏳ Todos los técnicos están ocupados. Se te asignará un turno.",
                "color": "orange",
                "tecnicos_disponibles": [],
                "tickets_en_cola": tickets_cola,
                "tiempo_estimado": (tickets_cola + 1) * 15
            }
    
    # =========================================================================
    # FUNCIONES DE GESTIÓN DE EQUIPOS/INVENTARIO
    # =========================================================================
    
    def _leer_equipos(self) -> pd.DataFrame:
        """Lee la base de datos de equipos con reintentos."""
        max_intentos = 3
        for intento in range(max_intentos):
            try:
                if not self.ruta_equipos.exists():
                    self._asegurar_existencia_equipos()
                    return pd.DataFrame(columns=COLUMNAS_EQUIPOS)
                
                df = pd.read_excel(self.ruta_equipos, engine='openpyxl')
                
                if df.empty:
                    return pd.DataFrame(columns=COLUMNAS_EQUIPOS)
                
                for col in ["FECHA_COMPRA", "GARANTIA_HASTA", "FECHA_REGISTRO", "ULTIMA_CONEXION"]:
                    if col in df.columns:
                        try:
                            df[col] = pd.to_datetime(df[col], errors='coerce')
                        except:
                            pass
                
                for col in ["RAM_GB", "DISCO_GB", "TOTAL_TICKETS"]:
                    if col in df.columns:
                        try:
                            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)
                        except:
                            pass
                
                return df
            except PermissionError:
                if intento < max_intentos - 1:
                    print(f"[WARNING] Permiso al leer equipos, reintentando...")
                    time.sleep(0.5)
                    continue
                return pd.DataFrame(columns=COLUMNAS_EQUIPOS)
            except Exception as e:
                if intento < max_intentos - 1:
                    print(f"[WARNING] Error equipos: {type(e).__name__}")
                    time.sleep(0.5)
                    continue
                print(f"[ERROR] Equipos: {e}")
                return pd.DataFrame(columns=COLUMNAS_EQUIPOS)
    
    def _escribir_equipos(self, df: pd.DataFrame) -> bool:
        """Escribe la base de datos de equipos."""
        try:
            df_copy = df.copy()
            # Convertir columnas numéricas correctamente
            for col in ["RAM_GB", "DISCO_GB", "TOTAL_TICKETS"]:
                if col in df_copy.columns:
                    df_copy[col] = pd.to_numeric(df_copy[col], errors='coerce').fillna(0).astype(int)
            # Convertir fechas a string
            for col in ["FECHA_COMPRA", "GARANTIA_HASTA", "FECHA_REGISTRO", "ULTIMA_CONEXION"]:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col].apply(
                        lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) and hasattr(x, 'strftime') else (str(x) if pd.notna(x) else "")
                    )
            df_copy.to_excel(self.ruta_equipos, index=False, engine='openpyxl')
            return True
        except Exception as e:
            print(f"[ERROR] Error escribiendo equipos: {e}")
            return False
    
    def obtener_equipos(self) -> pd.DataFrame:
        """Obtiene todos los equipos del inventario."""
        return self._leer_equipos()
    
    def obtener_equipo_por_mac(self, mac_address: str) -> Optional[Dict[str, Any]]:
        """Obtiene un equipo por su dirección MAC."""
        df = self._leer_equipos()
        equipo = df[df["MAC_ADDRESS"].str.upper() == mac_address.upper()]
        return equipo.iloc[0].to_dict() if not equipo.empty else None
    
    def registrar_o_actualizar_equipo(self, mac_address: str, hostname: str, usuario_ad: str) -> Dict[str, Any]:
        """
        Registra un nuevo equipo o actualiza la última conexión si ya existe.
        Se llama automáticamente cuando un equipo envía un ticket.
        
        Args:
            mac_address: Dirección MAC del equipo.
            hostname: Nombre de red del equipo.
            usuario_ad: Usuario que está usando el equipo.
        
        Returns:
            Diccionario con los datos del equipo.
        """
        df = self._leer_equipos()
        idx = df[df["MAC_ADDRESS"].str.upper() == mac_address.upper()].index
        
        ahora = datetime.now()
        
        if not idx.empty:
            # Equipo existe, actualizar última conexión y contador de tickets
            df.at[idx[0], "ULTIMA_CONEXION"] = ahora
            df.at[idx[0], "HOSTNAME"] = hostname
            df.at[idx[0], "USUARIO_ASIGNADO"] = usuario_ad
            df.at[idx[0], "TOTAL_TICKETS"] = int(df.at[idx[0], "TOTAL_TICKETS"]) + 1
            self._escribir_equipos(df)
            return df.loc[idx[0]].to_dict()
        else:
            # Nuevo equipo, registrar
            nuevo_equipo = {
                "MAC_ADDRESS": mac_address.upper(),
                "NOMBRE_EQUIPO": "",  # Por asignar
                "HOSTNAME": hostname,
                "USUARIO_ASIGNADO": usuario_ad,
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
                "FECHA_COMPRA": "",
                "GARANTIA_HASTA": "",
                "ESTADO_EQUIPO": "Activo",
                "NOTAS": "",
                "FECHA_REGISTRO": ahora,
                "ULTIMA_CONEXION": ahora,
                "TOTAL_TICKETS": 1
            }
            df = pd.concat([df, pd.DataFrame([nuevo_equipo])], ignore_index=True)
            self._escribir_equipos(df)
            return nuevo_equipo
    
    def actualizar_equipo(self, mac_address: str, **datos) -> bool:
        """
        Actualiza los datos de un equipo existente.
        
        Args:
            mac_address: MAC del equipo a actualizar.
            **datos: Campos a actualizar (nombre_equipo, grupo, ubicacion, marca, modelo, etc.)
        
        Returns:
            True si se actualizó correctamente.
        """
        df = self._leer_equipos()
        idx = df[df["MAC_ADDRESS"].str.upper() == mac_address.upper()].index
        
        if idx.empty:
            return False
        
        # Mapeo de nombres de parámetros a columnas
        mapeo = {
            "nombre_equipo": "NOMBRE_EQUIPO",
            "grupo": "GRUPO",
            "ubicacion": "UBICACION",
            "marca": "MARCA",
            "modelo": "MODELO",
            "numero_serie": "NUMERO_SERIE",
            "tipo_equipo": "TIPO_EQUIPO",
            "sistema_operativo": "SISTEMA_OPERATIVO",
            "procesador": "PROCESADOR",
            "ram_gb": "RAM_GB",
            "disco_gb": "DISCO_GB",
            "fecha_compra": "FECHA_COMPRA",
            "garantia_hasta": "GARANTIA_HASTA",
            "estado_equipo": "ESTADO_EQUIPO",
            "notas": "NOTAS"
        }
        
        # Campos numéricos que requieren conversión
        campos_numericos = ["ram_gb", "disco_gb"]
        
        # Campos de texto que deben ser string
        campos_texto = ["nombre_equipo", "grupo", "ubicacion", "marca", "modelo", 
                       "numero_serie", "tipo_equipo", "sistema_operativo", 
                       "procesador", "estado_equipo", "notas"]
        
        for campo, valor in datos.items():
            if campo in mapeo and valor is not None:
                # Convertir campos numéricos
                if campo in campos_numericos:
                    try:
                        valor = int(valor) if valor else 0
                    except (ValueError, TypeError):
                        valor = 0
                # Convertir campos de texto a string y manejar valores vacíos
                elif campo in campos_texto:
                    valor = str(valor) if valor else ""
                    # Convertir la columna a object (string) si es necesario
                    if df[mapeo[campo]].dtype != object:
                        df[mapeo[campo]] = df[mapeo[campo]].astype(object)
                df.at[idx[0], mapeo[campo]] = valor
        
        return self._escribir_equipos(df)
    
    def obtener_equipos_por_grupo(self, grupo: str) -> pd.DataFrame:
        """Obtiene todos los equipos de un grupo específico."""
        df = self._leer_equipos()
        return df[df["GRUPO"] == grupo]
    
    def obtener_grupos_con_conteo(self) -> Dict[str, int]:
        """Obtiene todos los grupos con la cantidad de equipos en cada uno."""
        df = self._leer_equipos()
        if df.empty:
            return {g: 0 for g in GRUPOS_EQUIPOS}
        
        conteo = df["GRUPO"].value_counts().to_dict()
        # Asegurar que todos los grupos estén presentes
        for grupo in GRUPOS_EQUIPOS:
            if grupo not in conteo:
                conteo[grupo] = 0
        return conteo
    
    def eliminar_equipo(self, mac_address: str) -> bool:
        """Elimina un equipo del inventario."""
        df = self._leer_equipos()
        idx = df[df["MAC_ADDRESS"].str.upper() == mac_address.upper()].index
        
        if idx.empty:
            return False
        
        df = df.drop(idx)
        return self._escribir_equipos(df)
    
    def obtener_estadisticas_equipos(self) -> Dict[str, Any]:
        """Obtiene estadísticas del inventario de equipos."""
        df = self._leer_equipos()
        
        if df.empty:
            return {
                "total_equipos": 0,
                "equipos_activos": 0,
                "equipos_inactivos": 0,
                "equipos_mantenimiento": 0,
                "equipos_baja": 0,
                "por_tipo": {},
                "por_grupo": {},
                "sin_nombre": 0,
                "garantia_vencida": 0
            }
        
        hoy = datetime.now()
        
        return {
            "total_equipos": len(df),
            "equipos_activos": len(df[df["ESTADO_EQUIPO"] == "Activo"]),
            "equipos_inactivos": len(df[df["ESTADO_EQUIPO"] == "Inactivo"]),
            "equipos_mantenimiento": len(df[df["ESTADO_EQUIPO"] == "En Mantenimiento"]),
            "equipos_baja": len(df[df["ESTADO_EQUIPO"] == "Baja"]),
            "por_tipo": df["TIPO_EQUIPO"].value_counts().to_dict() if "TIPO_EQUIPO" in df.columns else {},
            "por_grupo": df["GRUPO"].value_counts().to_dict() if "GRUPO" in df.columns else {},
            "sin_nombre": len(df[df["NOMBRE_EQUIPO"].fillna("") == ""]),
            "garantia_vencida": len(df[pd.to_datetime(df["GARANTIA_HASTA"], errors='coerce') < hoy]) if "GARANTIA_HASTA" in df.columns else 0
        }
    
    # =========================================================================
    # FUNCIONES DE TICKETS (ACTUALIZADAS)
    # =========================================================================
    
    def crear_ticket(self, 
                     usuario_ad: str,
                     hostname: str,
                     mac_address: str,
                     categoria: str,
                     descripcion: str,
                     prioridad: str = "Media") -> Dict[str, Any]:
        """
        Crea un nuevo ticket en la base de datos con sistema de turnos.
        
        Args:
            usuario_ad: Usuario de Active Directory.
            hostname: Nombre de red del equipo.
            mac_address: Dirección MAC del equipo.
            categoria: Categoría del ticket.
            descripcion: Descripción detallada del problema.
            prioridad: Prioridad del ticket (Alta/Media/Baja).
        
        Returns:
            Diccionario con los datos del ticket creado, incluyendo turno y estado.
        """
        # Validar categoría
        if categoria not in CATEGORIAS_DISPONIBLES:
            raise ValueError(f"Categoría inválida. Debe ser una de: {CATEGORIAS_DISPONIBLES}")
        
        # Registrar o actualizar equipo en inventario automáticamente
        self.registrar_o_actualizar_equipo(mac_address, hostname, usuario_ad)
        
        # Generar ID único y turno
        id_ticket = str(uuid.uuid4())[:8].upper()
        turno = self.obtener_siguiente_turno()
        
        # Verificar disponibilidad de técnicos
        hay_disponible = self.hay_tecnico_disponible()
        estado_inicial = "Abierto" if hay_disponible else "En Cola"
        
        # Crear registro del nuevo ticket
        nuevo_ticket = {
            "ID_TICKET": id_ticket,
            "TURNO": turno,
            "FECHA_APERTURA": datetime.now(),
            "USUARIO_AD": usuario_ad,
            "HOSTNAME": hostname,
            "MAC_ADDRESS": mac_address,
            "CATEGORIA": categoria,
            "PRIORIDAD": prioridad,
            "DESCRIPCION": descripcion,
            "ESTADO": estado_inicial,
            "TECNICO_ASIGNADO": "",
            "NOTAS_RESOLUCION": "",
            "FECHA_CIERRE": None,
            "TIEMPO_ESTIMADO": 0
        }
        
        # Leer datos existentes y agregar nuevo ticket
        df = self._leer_datos()
        df = pd.concat([df, pd.DataFrame([nuevo_ticket])], ignore_index=True)
        
        # Guardar cambios
        self._escribir_datos(df)
        
        # Añadir información adicional para la respuesta
        estado_sistema = self.obtener_mensaje_estado_sistema()
        nuevo_ticket["posicion_cola"] = self.obtener_posicion_cola(id_ticket)
        nuevo_ticket["mensaje_sistema"] = estado_sistema["mensaje"]
        nuevo_ticket["hay_tecnico_disponible"] = hay_disponible
        nuevo_ticket["tiempo_espera_estimado"] = estado_sistema["tiempo_estimado"]
        
        return nuevo_ticket
    
    def obtener_todos_tickets(self) -> pd.DataFrame:
        """
        Obtiene todos los tickets de la base de datos.
        
        Returns:
            DataFrame con todos los tickets.
        """
        return self._leer_datos()
    
    def obtener_ticket_por_id(self, id_ticket: str) -> Optional[Dict[str, Any]]:
        """
        Obtiene un ticket específico por su ID.
        
        Args:
            id_ticket: ID único del ticket a buscar.
        
        Returns:
            Diccionario con los datos del ticket, o None si no existe.
        """
        df = self._leer_datos()
        ticket = df[df["ID_TICKET"] == id_ticket]
        
        if ticket.empty:
            return None
        
        return ticket.iloc[0].to_dict()
    
    def actualizar_ticket(self, 
                          id_ticket: str,
                          estado: Optional[str] = None,
                          tecnico_asignado: Optional[str] = None,
                          notas_resolucion: Optional[str] = None,
                          historial: Optional[str] = None,
                          fecha_cierre: Optional[datetime] = None) -> bool:
        """
        Actualiza los campos de un ticket existente.
        
        Args:
            id_ticket: ID del ticket a actualizar.
            estado: Nuevo estado del ticket (opcional).
            tecnico_asignado: Nombre del técnico asignado (opcional).
            notas_resolucion: Notas de resolución (opcional).
            historial: Historial del ticket (opcional).
            fecha_cierre: Fecha de cierre del ticket (opcional).
        
        Returns:
            True si la actualización fue exitosa, False si el ticket no existe o está cerrado.
        
        Raises:
            ValueError: Si el estado no es válido o si el ticket ya está cerrado.
        """
        df = self._leer_datos()
        
        # Buscar el índice del ticket
        idx = df[df["ID_TICKET"] == id_ticket].index
        
        if idx.empty:
            return False
        
        idx = idx[0]
        
        # Verificar si el ticket ya está cerrado o cancelado
        estado_actual = df.at[idx, "ESTADO"]
        if estado_actual in ["Cerrado", "Cancelado"]:
            raise ValueError("No se puede editar un ticket cerrado o cancelado. Consulte el historial.")
        
        # Actualizar campos si se proporcionan
        if estado is not None:
            if estado not in ESTADOS_TICKET:
                raise ValueError(f"Estado inválido. Debe ser uno de: {ESTADOS_TICKET}")
            df.at[idx, "ESTADO"] = estado
            
            # Si se cierra el ticket, registrar fecha de cierre
            if estado == "Cerrado":
                # Convertir columna FECHA_CIERRE a object para evitar problemas de dtype
                if "FECHA_CIERRE" in df.columns:
                    df["FECHA_CIERRE"] = df["FECHA_CIERRE"].astype(object)
                df.at[idx, "FECHA_CIERRE"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if tecnico_asignado is not None:
            df.at[idx, "TECNICO_ASIGNADO"] = tecnico_asignado
        
        if notas_resolucion is not None:
            df.at[idx, "NOTAS_RESOLUCION"] = notas_resolucion
        
        if historial is not None:
            # Asegurar que la columna HISTORIAL exista y sea de tipo object
            if "HISTORIAL" not in df.columns:
                df["HISTORIAL"] = ""
            df["HISTORIAL"] = df["HISTORIAL"].astype(object)
            df.at[idx, "HISTORIAL"] = historial
        
        if fecha_cierre is not None:
            if "FECHA_CIERRE" in df.columns:
                df["FECHA_CIERRE"] = df["FECHA_CIERRE"].astype(object)
            df.at[idx, "FECHA_CIERRE"] = fecha_cierre.strftime("%Y-%m-%d %H:%M:%S") if hasattr(fecha_cierre, 'strftime') else str(fecha_cierre)
        
        # Guardar cambios
        self._escribir_datos(df)
        return True
    
    def filtrar_tickets(self, 
                        estado: Optional[str] = None,
                        usuario: Optional[str] = None,
                        mac_address: Optional[str] = None) -> pd.DataFrame:
        """
        Filtra tickets según los criterios especificados.
        
        Args:
            estado: Filtrar por estado (Abierto, En Proceso, Cerrado).
            usuario: Filtrar por usuario (búsqueda parcial).
            mac_address: Filtrar por dirección MAC (búsqueda parcial).
        
        Returns:
            DataFrame con los tickets que cumplen los criterios.
        """
        df = self._leer_datos()
        
        if estado:
            df = df[df["ESTADO"] == estado]
        
        if usuario:
            df = df[df["USUARIO_AD"].str.contains(usuario, case=False, na=False)]
        
        if mac_address:
            df = df[df["MAC_ADDRESS"].str.contains(mac_address, case=False, na=False)]
        
        return df
    
    def obtener_equipos_problematicos(self, top_n: int = 5) -> pd.DataFrame:
        """
        Obtiene los equipos (por MAC) con más tickets reportados.
        
        Realiza un groupby por MAC_ADDRESS para identificar equipos
        con fallas recurrentes.
        
        Args:
            top_n: Número de equipos a mostrar en el ranking.
        
        Returns:
            DataFrame con las MACs más problemáticas y su conteo.
        """
        df = self._leer_datos()
        
        if df.empty:
            return pd.DataFrame(columns=["MAC_ADDRESS", "HOSTNAME", "TOTAL_TICKETS"])
        
        # Agrupar por MAC y contar tickets
        equipos = df.groupby("MAC_ADDRESS").agg({
            "ID_TICKET": "count",
            "HOSTNAME": "first"  # Tomar el primer hostname asociado
        }).reset_index()
        
        # Renombrar columnas para claridad
        equipos.columns = ["MAC_ADDRESS", "TOTAL_TICKETS", "HOSTNAME"]
        
        # Ordenar por número de tickets descendente
        equipos = equipos.sort_values("TOTAL_TICKETS", ascending=False)
        
        return equipos.head(top_n)
    
    def obtener_distribucion_categorias(self) -> pd.DataFrame:
        """
        Obtiene la distribución porcentual de tickets por categoría.
        
        Útil para generar gráficos de pastel (pie chart).
        
        Returns:
            DataFrame con categorías, conteo y porcentaje.
        """
        df = self._leer_datos()
        
        if df.empty:
            return pd.DataFrame(columns=["CATEGORIA", "CANTIDAD", "PORCENTAJE"])
        
        # Contar tickets por categoría
        distribucion = df["CATEGORIA"].value_counts().reset_index()
        distribucion.columns = ["CATEGORIA", "CANTIDAD"]
        
        # Calcular porcentaje
        total = distribucion["CANTIDAD"].sum()
        distribucion["PORCENTAJE"] = (distribucion["CANTIDAD"] / total * 100).round(2)
        
        return distribucion
    
    def obtener_tickets_por_dia_semana(self) -> pd.DataFrame:
        """
        Obtiene la cantidad de tickets creados por día de la semana.
        
        Útil para analizar la carga semanal del equipo de soporte.
        
        Returns:
            DataFrame con día de la semana y cantidad de tickets.
        """
        try:
            df = self._leer_datos()
            
            if df.empty:
                return pd.DataFrame(columns=["DIA_SEMANA", "CANTIDAD"])
            
            # Convertir fecha a día de la semana con manejo de errores
            df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors='coerce')
            df = df.dropna(subset=["FECHA_APERTURA"])
            
            if df.empty:
                return pd.DataFrame(columns=["DIA_SEMANA", "CANTIDAD"])
            
            df["DIA_SEMANA"] = df["FECHA_APERTURA"].dt.day_name()
            
            # Mapeo a español
            dias_es = {
                "Monday": "Lunes",
                "Tuesday": "Martes",
                "Wednesday": "Miércoles",
                "Thursday": "Jueves",
                "Friday": "Viernes",
                "Saturday": "Sábado",
                "Sunday": "Domingo"
            }
            df["DIA_SEMANA"] = df["DIA_SEMANA"].map(dias_es)
            
            # Contar por día
            por_dia = df["DIA_SEMANA"].value_counts().reset_index()
            por_dia.columns = ["DIA_SEMANA", "CANTIDAD"]
            
            # Ordenar por día de la semana
            orden_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            por_dia["ORDEN"] = por_dia["DIA_SEMANA"].apply(lambda x: orden_dias.index(x) if x in orden_dias else 7)
            por_dia = por_dia.sort_values("ORDEN").drop("ORDEN", axis=1)
            
            return por_dia
        except Exception as e:
            print(f"[ERROR] Error obteniendo tickets por día de semana: {e}")
            return pd.DataFrame(columns=["DIA_SEMANA", "CANTIDAD"])
    
    def calcular_tiempo_promedio_cierre(self) -> float:
        """
        Calcula el tiempo promedio de cierre de tickets en horas.
        
        Solo considera tickets que han sido cerrados.
        
        Returns:
            Tiempo promedio en horas, o 0 si no hay tickets cerrados.
        """
        try:
            df = self._leer_datos()
            
            # Filtrar solo tickets cerrados con fechas válidas
            cerrados = df[df["ESTADO"] == "Cerrado"].copy()
            
            if cerrados.empty:
                return 0.0
            
            # Convertir fechas con manejo de errores
            cerrados["FECHA_APERTURA"] = pd.to_datetime(cerrados["FECHA_APERTURA"], errors='coerce')
            cerrados["FECHA_CIERRE"] = pd.to_datetime(cerrados["FECHA_CIERRE"], errors='coerce')
            
            # Filtrar registros con fechas válidas
            cerrados = cerrados.dropna(subset=["FECHA_APERTURA", "FECHA_CIERRE"])
            
            if cerrados.empty:
                return 0.0
            
            # Calcular diferencia
            cerrados["TIEMPO_CIERRE"] = (cerrados["FECHA_CIERRE"] - cerrados["FECHA_APERTURA"]).dt.total_seconds() / 3600
            
            resultado = cerrados["TIEMPO_CIERRE"].mean()
            return resultado if pd.notna(resultado) else 0.0
        except Exception as e:
            print(f"[ERROR] Error calculando tiempo promedio: {e}")
            return 0.0
    
    def contar_tickets_abiertos_hoy(self) -> int:
        """
        Cuenta los tickets abiertos en el día de hoy.
        
        Returns:
            Número de tickets creados hoy.
        """
        try:
            df = self._leer_datos()
            
            if df.empty:
                return 0
            
            # Obtener fecha de hoy
            hoy = datetime.now().date()
            
            # Filtrar tickets de hoy con manejo de errores
            df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors='coerce')
            df = df.dropna(subset=["FECHA_APERTURA"])
            
            if df.empty:
                return 0
            
            tickets_hoy = df[df["FECHA_APERTURA"].dt.date == hoy]
            
            return len(tickets_hoy)
        except Exception as e:
            print(f"[ERROR] Error contando tickets de hoy: {e}")
            return 0
    
    def obtener_estadisticas_generales(self) -> Dict[str, Any]:
        """
        Obtiene un resumen de estadísticas generales del sistema.
        
        Returns:
            Diccionario con métricas clave del sistema.
        """
        try:
            df = self._leer_datos()
            
            total = len(df)
            abiertos = len(df[df["ESTADO"] == "Abierto"]) if not df.empty else 0
            en_proceso = len(df[df["ESTADO"] == "En Proceso"]) if not df.empty else 0
            cerrados = len(df[df["ESTADO"] == "Cerrado"]) if not df.empty else 0
            
            try:
                tickets_hoy = self.contar_tickets_abiertos_hoy()
            except:
                tickets_hoy = 0
            
            try:
                tiempo_promedio = self.calcular_tiempo_promedio_cierre()
            except:
                tiempo_promedio = 0.0
            
            return {
                "total_tickets": total,
                "tickets_abiertos": abiertos,
                "tickets_en_proceso": en_proceso,
                "tickets_cerrados": cerrados,
                "tickets_hoy": tickets_hoy,
                "tiempo_promedio_cierre": tiempo_promedio
            }
        except Exception as e:
            print(f"[ERROR] Error obteniendo estadísticas: {e}")
            return {
                "total_tickets": 0,
                "tickets_abiertos": 0,
                "tickets_en_proceso": 0,
                "tickets_cerrados": 0,
                "tickets_hoy": 0,
                "tiempo_promedio_cierre": 0.0
            }

    # =========================================================================
    # ESTADÍSTICAS AVANZADAS PARA REPORTES
    # =========================================================================
    
    def obtener_tickets_por_mes(self, meses: int = 12) -> pd.DataFrame:
        """
        Obtiene la cantidad de tickets por mes para los últimos N meses.
        
        Args:
            meses: Número de meses hacia atrás a considerar.
        
        Returns:
            DataFrame con mes/año y cantidad de tickets.
        """
        try:
            df = self._leer_datos()
            
            if df.empty:
                return pd.DataFrame(columns=["MES", "AÑO", "CANTIDAD", "CERRADOS", "PENDIENTES"])
            
            df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors='coerce')
            df = df.dropna(subset=["FECHA_APERTURA"])
            
            if df.empty:
                return pd.DataFrame(columns=["MES", "AÑO", "CANTIDAD", "CERRADOS", "PENDIENTES"])
            
            # Filtrar por fecha
            from datetime import timedelta
            fecha_limite = datetime.now() - timedelta(days=meses * 30)
            df = df[df["FECHA_APERTURA"] >= fecha_limite]
            
            df["MES"] = df["FECHA_APERTURA"].dt.month
            df["AÑO"] = df["FECHA_APERTURA"].dt.year
            
            # Agrupar por mes y año
            por_mes = df.groupby(["AÑO", "MES"]).agg({
                "ID_TICKET": "count",
                "ESTADO": lambda x: (x == "Cerrado").sum()
            }).reset_index()
            
            por_mes.columns = ["AÑO", "MES", "CANTIDAD", "CERRADOS"]
            por_mes["PENDIENTES"] = por_mes["CANTIDAD"] - por_mes["CERRADOS"]
            
            # Nombres de meses en español
            meses_es = {1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
                       7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"}
            por_mes["MES_NOMBRE"] = por_mes["MES"].map(meses_es)
            por_mes["ETIQUETA"] = por_mes["MES_NOMBRE"] + " " + por_mes["AÑO"].astype(str)
            
            return por_mes.sort_values(["AÑO", "MES"])
        except Exception as e:
            print(f"[ERROR] Error obteniendo tickets por mes: {e}")
            return pd.DataFrame(columns=["MES", "AÑO", "CANTIDAD", "CERRADOS", "PENDIENTES"])
    
    def obtener_tickets_por_hora(self) -> pd.DataFrame:
        """
        Obtiene la distribución de tickets por hora del día.
        
        Returns:
            DataFrame con hora y cantidad de tickets.
        """
        try:
            df = self._leer_datos()
            
            if df.empty:
                return pd.DataFrame(columns=["HORA", "CANTIDAD"])
            
            df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors='coerce')
            df = df.dropna(subset=["FECHA_APERTURA"])
            
            if df.empty:
                return pd.DataFrame(columns=["HORA", "CANTIDAD"])
            
            df["HORA"] = df["FECHA_APERTURA"].dt.hour
            
            por_hora = df["HORA"].value_counts().reset_index()
            por_hora.columns = ["HORA", "CANTIDAD"]
            por_hora = por_hora.sort_values("HORA")
            
            return por_hora
        except Exception as e:
            print(f"[ERROR] Error obteniendo tickets por hora: {e}")
            return pd.DataFrame(columns=["HORA", "CANTIDAD"])
    
    def obtener_rendimiento_tecnicos(self) -> pd.DataFrame:
        """
        Obtiene métricas de rendimiento por técnico.
        
        Returns:
            DataFrame con estadísticas por técnico.
        """
        try:
            df = self._leer_datos()
            tecnicos = self._leer_tecnicos()
            
            if df.empty:
                return tecnicos[["ID_TECNICO", "NOMBRE", "ESTADO", "TICKETS_ATENDIDOS"]].copy()
            
            # Tickets asignados a cada técnico
            asignados = df[df["TECNICO_ASIGNADO"].notna()].groupby("TECNICO_ASIGNADO").agg({
                "ID_TICKET": "count",
                "ESTADO": lambda x: (x == "Cerrado").sum()
            }).reset_index()
            asignados.columns = ["NOMBRE", "TICKETS_ASIGNADOS", "TICKETS_CERRADOS"]
            
            # Calcular tiempo promedio por técnico
            cerrados = df[(df["ESTADO"] == "Cerrado") & (df["TECNICO_ASIGNADO"].notna())].copy()
            if not cerrados.empty:
                cerrados["FECHA_APERTURA"] = pd.to_datetime(cerrados["FECHA_APERTURA"], errors='coerce')
                cerrados["FECHA_CIERRE"] = pd.to_datetime(cerrados["FECHA_CIERRE"], errors='coerce')
                cerrados = cerrados.dropna(subset=["FECHA_APERTURA", "FECHA_CIERRE"])
                if not cerrados.empty:
                    cerrados["TIEMPO_HORAS"] = (cerrados["FECHA_CIERRE"] - cerrados["FECHA_APERTURA"]).dt.total_seconds() / 3600
                    tiempo_prom = cerrados.groupby("TECNICO_ASIGNADO")["TIEMPO_HORAS"].mean().reset_index()
                    tiempo_prom.columns = ["NOMBRE", "TIEMPO_PROMEDIO"]
                    asignados = asignados.merge(tiempo_prom, on="NOMBRE", how="left")
            
            if "TIEMPO_PROMEDIO" not in asignados.columns:
                asignados["TIEMPO_PROMEDIO"] = 0.0
            
            # Unir con datos de técnicos
            resultado = tecnicos.merge(asignados, on="NOMBRE", how="left")
            resultado["TICKETS_ASIGNADOS"] = resultado["TICKETS_ASIGNADOS"].fillna(0).astype(int)
            resultado["TICKETS_CERRADOS"] = resultado["TICKETS_CERRADOS"].fillna(0).astype(int)
            resultado["TIEMPO_PROMEDIO"] = resultado["TIEMPO_PROMEDIO"].fillna(0.0).round(2)
            resultado["EFICIENCIA"] = (resultado["TICKETS_CERRADOS"] / resultado["TICKETS_ASIGNADOS"].replace(0, 1) * 100).round(1)
            
            return resultado
        except Exception as e:
            print(f"[ERROR] Error obteniendo rendimiento de técnicos: {e}")
            return pd.DataFrame()
    
    def obtener_tendencia_semanal(self, semanas: int = 8) -> pd.DataFrame:
        """
        Obtiene la tendencia de tickets por semana.
        
        Args:
            semanas: Número de semanas hacia atrás.
        
        Returns:
            DataFrame con semana y cantidad de tickets.
        """
        try:
            df = self._leer_datos()
            
            if df.empty:
                return pd.DataFrame(columns=["SEMANA", "CANTIDAD", "CERRADOS"])
            
            df["FECHA_APERTURA"] = pd.to_datetime(df["FECHA_APERTURA"], errors='coerce')
            df = df.dropna(subset=["FECHA_APERTURA"])
            
            if df.empty:
                return pd.DataFrame(columns=["SEMANA", "CANTIDAD", "CERRADOS"])
            
            from datetime import timedelta
            fecha_limite = datetime.now() - timedelta(weeks=semanas)
            df = df[df["FECHA_APERTURA"] >= fecha_limite]
            
            df["SEMANA"] = df["FECHA_APERTURA"].dt.isocalendar().week
            df["AÑO"] = df["FECHA_APERTURA"].dt.year
            
            por_semana = df.groupby(["AÑO", "SEMANA"]).agg({
                "ID_TICKET": "count",
                "ESTADO": lambda x: (x == "Cerrado").sum()
            }).reset_index()
            
            por_semana.columns = ["AÑO", "SEMANA", "CANTIDAD", "CERRADOS"]
            por_semana = por_semana.sort_values(["AÑO", "SEMANA"])
            por_semana["ETIQUETA"] = "S" + por_semana["SEMANA"].astype(str)
            
            return por_semana
        except Exception as e:
            print(f"[ERROR] Error obteniendo tendencia semanal: {e}")
            return pd.DataFrame(columns=["SEMANA", "CANTIDAD", "CERRADOS"])
    
    def obtener_distribucion_prioridades(self) -> pd.DataFrame:
        """
        Obtiene la distribución de tickets por prioridad.
        
        Returns:
            DataFrame con prioridad, cantidad y porcentaje.
        """
        try:
            df = self._leer_datos()
            
            if df.empty:
                return pd.DataFrame(columns=["PRIORIDAD", "CANTIDAD", "PORCENTAJE"])
            
            dist = df["PRIORIDAD"].value_counts().reset_index()
            dist.columns = ["PRIORIDAD", "CANTIDAD"]
            
            total = dist["CANTIDAD"].sum()
            dist["PORCENTAJE"] = (dist["CANTIDAD"] / total * 100).round(2)
            
            return dist
        except Exception as e:
            print(f"[ERROR] Error obteniendo distribución de prioridades: {e}")
            return pd.DataFrame(columns=["PRIORIDAD", "CANTIDAD", "PORCENTAJE"])
    
    def obtener_tiempo_resolucion_por_categoria(self) -> pd.DataFrame:
        """
        Obtiene el tiempo promedio de resolución por categoría.
        
        Returns:
            DataFrame con categoría y tiempo promedio en horas.
        """
        try:
            df = self._leer_datos()
            
            cerrados = df[df["ESTADO"] == "Cerrado"].copy()
            
            if cerrados.empty:
                return pd.DataFrame(columns=["CATEGORIA", "TIEMPO_PROMEDIO", "TOTAL_CERRADOS"])
            
            cerrados["FECHA_APERTURA"] = pd.to_datetime(cerrados["FECHA_APERTURA"], errors='coerce')
            cerrados["FECHA_CIERRE"] = pd.to_datetime(cerrados["FECHA_CIERRE"], errors='coerce')
            cerrados = cerrados.dropna(subset=["FECHA_APERTURA", "FECHA_CIERRE"])
            
            if cerrados.empty:
                return pd.DataFrame(columns=["CATEGORIA", "TIEMPO_PROMEDIO", "TOTAL_CERRADOS"])
            
            cerrados["TIEMPO_HORAS"] = (cerrados["FECHA_CIERRE"] - cerrados["FECHA_APERTURA"]).dt.total_seconds() / 3600
            
            por_cat = cerrados.groupby("CATEGORIA").agg({
                "TIEMPO_HORAS": "mean",
                "ID_TICKET": "count"
            }).reset_index()
            
            por_cat.columns = ["CATEGORIA", "TIEMPO_PROMEDIO", "TOTAL_CERRADOS"]
            por_cat["TIEMPO_PROMEDIO"] = por_cat["TIEMPO_PROMEDIO"].round(2)
            
            return por_cat.sort_values("TIEMPO_PROMEDIO")
        except Exception as e:
            print(f"[ERROR] Error obteniendo tiempo por categoría: {e}")
            return pd.DataFrame(columns=["CATEGORIA", "TIEMPO_PROMEDIO", "TOTAL_CERRADOS"])
    
    def obtener_estadisticas_completas(self) -> Dict[str, Any]:
        """
        Obtiene todas las estadísticas del sistema en un solo diccionario.
        
        Returns:
            Diccionario con todas las métricas y datos para reportes.
        """
        try:
            df = self._leer_datos()
            tecnicos = self._leer_tecnicos()
            equipos = self._leer_equipos()
            
            # Estadísticas básicas
            total_tickets = len(df)
            tickets_abiertos = len(df[df["ESTADO"] == "Abierto"]) if not df.empty else 0
            tickets_en_proceso = len(df[df["ESTADO"] == "En Proceso"]) if not df.empty else 0
            tickets_cerrados = len(df[df["ESTADO"] == "Cerrado"]) if not df.empty else 0
            tickets_hoy = self.contar_tickets_abiertos_hoy()
            
            # Tasa de resolución
            tasa_resolucion = (tickets_cerrados / max(total_tickets, 1)) * 100
            
            # Tiempo promedio
            tiempo_promedio = self.calcular_tiempo_promedio_cierre()
            
            # Tickets por técnico
            tickets_por_tecnico = {}
            if not df.empty:
                for nombre in tecnicos["NOMBRE"].unique():
                    tickets_por_tecnico[nombre] = len(df[df["TECNICO_ASIGNADO"] == nombre])
            
            # Tickets por estado
            tickets_por_estado = df["ESTADO"].value_counts().to_dict() if not df.empty else {}
            
            # Tickets por categoría
            tickets_por_categoria = df["CATEGORIA"].value_counts().to_dict() if not df.empty else {}
            
            # Tickets por prioridad
            tickets_por_prioridad = df["PRIORIDAD"].value_counts().to_dict() if not df.empty else {}
            
            return {
                "resumen": {
                    "total_tickets": total_tickets,
                    "tickets_abiertos": tickets_abiertos,
                    "tickets_en_proceso": tickets_en_proceso,
                    "tickets_cerrados": tickets_cerrados,
                    "tickets_hoy": tickets_hoy,
                    "tasa_resolucion": round(tasa_resolucion, 2),
                    "tiempo_promedio_horas": round(tiempo_promedio, 2),
                    "total_tecnicos": len(tecnicos),
                    "tecnicos_disponibles": len(tecnicos[tecnicos["ESTADO"] == "Disponible"]),
                    "total_equipos": len(equipos)
                },
                "por_estado": tickets_por_estado,
                "por_categoria": tickets_por_categoria,
                "por_prioridad": tickets_por_prioridad,
                "por_tecnico": tickets_por_tecnico,
                "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            print(f"[ERROR] Error obteniendo estadísticas completas: {e}")
            return {}
    
    def exportar_reporte_excel(self, ruta_salida: Path = None) -> str:
        """
        Exporta un reporte completo a Excel con múltiples hojas.
        
        Args:
            ruta_salida: Ruta donde guardar el archivo.
        
        Returns:
            Ruta del archivo generado.
        """
        try:
            if ruta_salida is None:
                fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
                ruta_salida = Path(__file__).parent / f"reporte_tickets_{fecha}.xlsx"
            
            with pd.ExcelWriter(ruta_salida, engine='openpyxl') as writer:
                # Hoja 1: Todos los tickets
                df_tickets = self._leer_datos()
                df_tickets.to_excel(writer, sheet_name='Tickets', index=False)
                
                # Hoja 2: Estadísticas generales
                stats = self.obtener_estadisticas_completas()
                df_resumen = pd.DataFrame([stats["resumen"]])
                df_resumen.to_excel(writer, sheet_name='Resumen', index=False)
                
                # Hoja 3: Por categoría
                df_categorias = self.obtener_distribucion_categorias()
                df_categorias.to_excel(writer, sheet_name='Por Categoria', index=False)
                
                # Hoja 4: Por día de semana
                df_dias = self.obtener_tickets_por_dia_semana()
                df_dias.to_excel(writer, sheet_name='Por Dia', index=False)
                
                # Hoja 5: Equipos problemáticos
                df_equipos = self.obtener_equipos_problematicos(top_n=20)
                df_equipos.to_excel(writer, sheet_name='Equipos Problematicos', index=False)
                
                # Hoja 6: Rendimiento técnicos
                df_tecnicos = self.obtener_rendimiento_tecnicos()
                if not df_tecnicos.empty:
                    df_tecnicos.to_excel(writer, sheet_name='Rendimiento Tecnicos', index=False)
                
                # Hoja 7: Tendencia mensual
                df_mensual = self.obtener_tickets_por_mes()
                if not df_mensual.empty:
                    df_mensual.to_excel(writer, sheet_name='Tendencia Mensual', index=False)
                
                # Hoja 8: Tiempo por categoría
                df_tiempo = self.obtener_tiempo_resolucion_por_categoria()
                if not df_tiempo.empty:
                    df_tiempo.to_excel(writer, sheet_name='Tiempo por Categoria', index=False)
            
            return str(ruta_salida)
        except Exception as e:
            print(f"[ERROR] Error exportando reporte: {e}")
            return ""


# =============================================================================
# FUNCIONES AUXILIARES PARA OBTENCIÓN DE INFORMACIÓN DEL SISTEMA
# =============================================================================

def obtener_mac_address() -> str:
    """
    Obtiene la dirección MAC del equipo actual.
    
    Utiliza la librería getmac que es compatible con Windows y macOS.
    
    Returns:
        Dirección MAC como string, o "00:00:00:00:00:00" si no se puede obtener.
    """
    try:
        from getmac import get_mac_address
        mac = get_mac_address()
        return mac if mac else "00:00:00:00:00:00"
    except Exception as e:
        print(f"[ERROR] No se pudo obtener la MAC: {e}")
        return "00:00:00:00:00:00"


def obtener_usuario_ad() -> str:
    """
    Obtiene el nombre de usuario de Active Directory (sesión actual).
    
    Utiliza os.getlogin() para obtener el usuario de Windows/macOS.
    
    Returns:
        Nombre de usuario, o "DESCONOCIDO" si no se puede obtener.
    """
    try:
        import os
        return os.getlogin()
    except Exception as e:
        print(f"[ERROR] No se pudo obtener el usuario: {e}")
        return "DESCONOCIDO"


def obtener_hostname() -> str:
    """
    Obtiene el nombre de red (hostname) del equipo.
    
    Returns:
        Nombre del equipo, o "DESCONOCIDO" si no se puede obtener.
    """
    try:
        import socket
        return socket.gethostname()
    except Exception as e:
        print(f"[ERROR] No se pudo obtener el hostname: {e}")
        return "DESCONOCIDO"


# =============================================================================
# FUNCIONES DE ESCANEO DE RED
# =============================================================================

def obtener_ip_local() -> str:
    """Obtiene la IP local del equipo."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        try:
            return socket.gethostbyname(socket.gethostname())
        except:
            return "127.0.0.1"


def obtener_rango_red() -> tuple:
    """
    Obtiene el rango de red basado en la IP local.
    Retorna (ip_base, inicio, fin) para escanear.
    """
    ip_local = obtener_ip_local()
    partes = ip_local.split(".")
    ip_base = ".".join(partes[:3])
    return ip_base, 1, 254


def ping_host(ip: str, timeout: int = 1) -> bool:
    """
    Hace ping a un host para verificar si está online.
    
    Args:
        ip: Dirección IP a verificar.
        timeout: Tiempo de espera en segundos.
    
    Returns:
        True si el host responde, False si no.
    """
    try:
        # Windows usa -n para número de pings y -w para timeout en ms
        resultado = subprocess.run(
            ["ping", "-n", "1", "-w", str(timeout * 1000), ip],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        return resultado.returncode == 0
    except Exception as e:
        return False


def obtener_mac_desde_arp(ip: str) -> Optional[str]:
    """
    Obtiene la dirección MAC de una IP desde la tabla ARP.
    
    Args:
        ip: Dirección IP para buscar.
    
    Returns:
        Dirección MAC o None si no se encuentra.
    """
    try:
        resultado = subprocess.run(
            ["arp", "-a", ip],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        
        # Buscar patrón MAC en la salida (formato XX-XX-XX-XX-XX-XX o XX:XX:XX:XX:XX:XX)
        patron_mac = re.compile(r"([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})")
        match = patron_mac.search(resultado.stdout)
        
        if match:
            mac = match.group(1).upper().replace("-", ":")
            return mac
        return None
    except Exception as e:
        return None


def obtener_hostname_remoto(ip: str) -> str:
    """
    Intenta obtener el hostname de una IP remota.
    
    Args:
        ip: Dirección IP.
    
    Returns:
        Hostname o "Desconocido" si no se puede resolver.
    """
    try:
        hostname = socket.gethostbyaddr(ip)[0]
        return hostname
    except:
        return "Desconocido"


def escanear_ip(ip: str) -> Optional[Dict[str, Any]]:
    """
    Escanea una IP específica y retorna información si responde.
    
    Args:
        ip: Dirección IP a escanear.
    
    Returns:
        Diccionario con info del host o None si no responde.
    """
    if ping_host(ip):
        mac = obtener_mac_desde_arp(ip)
        hostname = obtener_hostname_remoto(ip)
        
        return {
            "IP_ADDRESS": ip,
            "MAC_ADDRESS": mac or "No detectada",
            "HOSTNAME": hostname,
            "ESTADO_RED": "Online",
            "ULTIMO_PING": datetime.now()
        }
    return None


class EscanerRed:
    """
    Clase para escanear la red local y detectar equipos.
    """
    
    def __init__(self, ruta_db: Path = RED_DB_PATH):
        self.ruta_db = ruta_db
        self.escaneando = False
        self.progreso = 0
        self.total = 254
        self.equipos_encontrados = []
        self.callback_progreso: Optional[Callable] = None
        self.callback_equipo: Optional[Callable] = None
        self._asegurar_existencia_db()
    
    def _asegurar_existencia_db(self) -> None:
        """Crea la base de datos de red si no existe."""
        if not self.ruta_db.exists():
            df = pd.DataFrame(columns=COLUMNAS_RED)
            df.to_excel(self.ruta_db, index=False, engine='openpyxl')
            print(f"[INFO] Base de datos de red creada en: {self.ruta_db}")
    
    def _leer_datos(self) -> pd.DataFrame:
        """Lee la base de datos de red."""
        try:
            return pd.read_excel(self.ruta_db, engine='openpyxl')
        except:
            self._asegurar_existencia_db()
            return pd.DataFrame(columns=COLUMNAS_RED)
    
    def _escribir_datos(self, df: pd.DataFrame) -> bool:
        """Escribe la base de datos de red."""
        try:
            df_copy = df.copy()
            for col in ["ULTIMO_PING", "PRIMERA_VEZ"]:
                if col in df_copy.columns:
                    df_copy[col] = df_copy[col].apply(
                        lambda x: x.strftime("%Y-%m-%d %H:%M:%S") if pd.notna(x) and hasattr(x, 'strftime') else (str(x) if pd.notna(x) else "")
                    )
            df_copy.to_excel(self.ruta_db, index=False, engine='openpyxl')
            return True
        except Exception as e:
            print(f"[ERROR] Error escribiendo red DB: {e}")
            return False
    
    def escanear_red(self, rango_inicio: int = 1, rango_fin: int = 254, hilos: int = 50) -> List[Dict]:
        """
        Escanea un rango de IPs en la red local.
        
        Args:
            rango_inicio: Primera IP del rango (último octeto).
            rango_fin: Última IP del rango (último octeto).
            hilos: Número de hilos para escaneo paralelo.
        
        Returns:
            Lista de equipos encontrados.
        """
        self.escaneando = True
        self.equipos_encontrados = []
        self.progreso = 0
        self.total = rango_fin - rango_inicio + 1
        
        ip_base, _, _ = obtener_rango_red()
        ips_a_escanear = [f"{ip_base}.{i}" for i in range(rango_inicio, rango_fin + 1)]
        
        df_actual = self._leer_datos()
        cambios_detectados = []
        
        with ThreadPoolExecutor(max_workers=hilos) as executor:
            futures = {executor.submit(escanear_ip, ip): ip for ip in ips_a_escanear}
            
            for future in as_completed(futures):
                self.progreso += 1
                
                if self.callback_progreso:
                    try:
                        self.callback_progreso(self.progreso, self.total)
                    except:
                        pass
                
                resultado = future.result()
                if resultado:
                    # Verificar si la MAC ya existe con otra IP (cambio de IP)
                    mac = resultado["MAC_ADDRESS"]
                    ip_nueva = resultado["IP_ADDRESS"]
                    
                    if mac != "No detectada":
                        equipo_existente = df_actual[df_actual["MAC_ADDRESS"] == mac]
                        
                        if not equipo_existente.empty:
                            ip_anterior = equipo_existente.iloc[0]["IP_ADDRESS"]
                            if ip_anterior != ip_nueva:
                                cambios = int(equipo_existente.iloc[0].get("CAMBIOS_IP", 0)) + 1
                                resultado["IP_ANTERIOR"] = ip_anterior
                                resultado["CAMBIOS_IP"] = cambios
                                cambios_detectados.append({
                                    "mac": mac,
                                    "ip_anterior": ip_anterior,
                                    "ip_nueva": ip_nueva,
                                    "hostname": resultado["HOSTNAME"]
                                })
                    
                    self.equipos_encontrados.append(resultado)
                    
                    if self.callback_equipo:
                        try:
                            self.callback_equipo(resultado)
                        except:
                            pass
        
        self.escaneando = False
        
        # Guardar resultados
        self._actualizar_base_datos(self.equipos_encontrados)
        
        return self.equipos_encontrados, cambios_detectados
    
    def _actualizar_base_datos(self, equipos: List[Dict]) -> None:
        """Actualiza la base de datos con los equipos encontrados."""
        df = self._leer_datos()
        ahora = str(datetime.now())  # Convertir a string para pandas
        
        for equipo in equipos:
            mac = equipo.get("MAC_ADDRESS", "")
            ip = equipo.get("IP_ADDRESS", "")
            
            if mac == "No detectada":
                # Buscar por IP si no hay MAC
                idx = df[df["IP_ADDRESS"] == ip].index
            else:
                # Buscar por MAC
                idx = df[df["MAC_ADDRESS"] == mac].index
            
            if idx.empty:
                # Nuevo equipo
                nuevo = {
                    "IP_ADDRESS": ip,
                    "MAC_ADDRESS": mac,
                    "HOSTNAME": equipo.get("HOSTNAME", ""),
                    "ESTADO_RED": "Online",
                    "ULTIMO_PING": ahora,
                    "PRIMERA_VEZ": ahora,
                    "IP_ANTERIOR": "",
                    "CAMBIOS_IP": 0,
                    "COMENTARIO": ""
                }
                df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
            else:
                # Actualizar existente
                df.at[idx[0], "IP_ADDRESS"] = ip
                df.at[idx[0], "HOSTNAME"] = equipo.get("HOSTNAME", df.at[idx[0], "HOSTNAME"])
                df.at[idx[0], "ESTADO_RED"] = "Online"
                df.at[idx[0], "ULTIMO_PING"] = ahora
                
                if equipo.get("IP_ANTERIOR"):
                    df.at[idx[0], "IP_ANTERIOR"] = equipo["IP_ANTERIOR"]
                    df.at[idx[0], "CAMBIOS_IP"] = equipo.get("CAMBIOS_IP", 0)
        
        # Marcar como Offline los que no respondieron
        ips_online = [e["IP_ADDRESS"] for e in equipos]
        for idx, row in df.iterrows():
            if row["IP_ADDRESS"] not in ips_online:
                df.at[idx, "ESTADO_RED"] = "Offline"
        
        self._escribir_datos(df)
    
    def obtener_equipos_red(self) -> pd.DataFrame:
        """Obtiene todos los equipos de la base de datos de red."""
        return self._leer_datos()
    
    def obtener_equipos_online(self) -> pd.DataFrame:
        """Obtiene solo los equipos online."""
        df = self._leer_datos()
        return df[df["ESTADO_RED"] == "Online"]
    
    def obtener_cambios_ip(self) -> pd.DataFrame:
        """Obtiene equipos que han cambiado de IP."""
        df = self._leer_datos()
        return df[df["CAMBIOS_IP"] > 0]
    
    def guardar_comentario(self, mac_o_ip: str, comentario: str) -> bool:
        """Guarda un comentario para un equipo de red."""
        df = self._leer_datos()
        
        idx = df[df["MAC_ADDRESS"] == mac_o_ip].index
        if idx.empty:
            idx = df[df["IP_ADDRESS"] == mac_o_ip].index
        
        if idx.empty:
            return False
        
        df.at[idx[0], "COMENTARIO"] = comentario
        return self._escribir_datos(df)


def guardar_config_servidor(ip: str, puerto: int = SERVIDOR_PUERTO) -> None:
    """Guarda la configuración del servidor para que los emisores sepan dónde conectar."""
    with open(SERVIDOR_CONFIG_PATH, "w") as f:
        f.write(f"{ip}:{puerto}")


def cargar_config_servidor() -> tuple:
    """Carga la configuración del servidor."""
    try:
        if SERVIDOR_CONFIG_PATH.exists():
            with open(SERVIDOR_CONFIG_PATH, "r") as f:
                contenido = f.read().strip()
                ip, puerto = contenido.split(":")
                return ip, int(puerto)
    except:
        pass
    return None, SERVIDOR_PUERTO


# =============================================================================
# BLOQUE DE PRUEBAS (Solo se ejecuta si se corre directamente este archivo)
# =============================================================================

if __name__ == "__main__":
    # Pruebas básicas del módulo
    print("=" * 50)
    print("PRUEBAS DEL MÓDULO DE ACCESO A DATOS")
    print("=" * 50)
    
    # Obtener información del sistema
    print(f"\nUsuario AD: {obtener_usuario_ad()}")
    print(f"Hostname: {obtener_hostname()}")
    print(f"MAC Address: {obtener_mac_address()}")
    
    # Crear instancia del gestor
    gestor = GestorTickets()
    
    # Mostrar estadísticas
    stats = gestor.obtener_estadisticas_generales()
    print(f"\nEstadísticas del sistema:")
    for key, value in stats.items():
        print(f"  - {key}: {value}")
