# =============================================================================
# MÓDULO DE ACTUALIZACIONES — Sistema de Tickets IT
# =============================================================================
# Consulta GitHub para buscar nuevas versiones, parches y changelogs.
# Se conecta a la API de GitHub (sin token) para obtener releases y archivos.
# =============================================================================

import json
import os
import sys
import shutil
import hashlib
import tempfile
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List, Tuple

# Para las peticiones HTTP (usa urllib para no depender de requests)
import urllib.request
import urllib.error
import ssl
import socket

# =============================================================================
# CONFIGURACIÓN DEL REPOSITORIO
# =============================================================================

GITHUB_OWNER = "GoodIsaac18"
GITHUB_REPO = "tickets"
GITHUB_BRANCH = "main"

# URLs base de GitHub API y raw content
GITHUB_API_BASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_RAW_BASE = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/{GITHUB_BRANCH}"

# Archivos clave que se pueden actualizar
ARCHIVOS_ACTUALIZABLES = [
    "app_emisora.py",
    "app_receptora.py",
    "data_access.py",
    "servidor_red.py",
    "servicio_notificaciones.py",
    "notificaciones_windows.py",
    "instalador.py",
    "actualizador_github.py",
    "version.json",
]

# Archivo local que guarda el estado de actualizaciones
ESTADO_ACTUALIZACIONES = "update_state.json"

# Timeout para conexiones HTTP (segundos)
HTTP_TIMEOUT = 15


# =============================================================================
# EXCEPCIONES PERSONALIZADAS
# =============================================================================

class SinConexionError(Exception):
    """No hay conexión a internet."""
    pass

class GitHubAPIError(Exception):
    """Error al comunicarse con la API de GitHub."""
    pass

class ActualizacionError(Exception):
    """Error durante el proceso de actualización."""
    pass


# =============================================================================
# FUNCIONES DE CONECTIVIDAD
# =============================================================================

def verificar_conexion_internet(timeout: int = 5) -> bool:
    """
    Verifica si hay conexión a internet intentando alcanzar varios servidores.
    
    Returns:
        True si hay conexión, False si no.
    """
    servidores = [
        ("8.8.8.8", 53),        # Google DNS
        ("1.1.1.1", 53),        # Cloudflare DNS
        ("208.67.222.222", 53),  # OpenDNS
    ]
    
    for ip, puerto in servidores:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            sock.connect((ip, puerto))
            sock.close()
            return True
        except (socket.timeout, socket.error, OSError):
            continue
    
    return False


def verificar_conexion_github(timeout: int = 8) -> bool:
    """
    Verifica si se puede acceder a GitHub.
    
    Returns:
        True si GitHub es accesible, False si no.
    """
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(
            f"{GITHUB_API_BASE}",
            headers={"User-Agent": "TicketsIT-Updater/1.0"}
        )
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.status == 200
    except Exception:
        return False


def verificar_wifi_conectado() -> Dict[str, any]:
    """
    Verifica el estado de la conexión WiFi/Red en Windows.
    
    Returns:
        Dict con estado de conexión, SSID, etc.
    """
    resultado = {
        "conectado": False,
        "tipo": "Desconocido",
        "ssid": "",
        "internet": False,
        "github": False,
    }
    
    try:
        import subprocess
        # Verificar interfaz de red activa
        output = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True, text=True, timeout=5
        )
        
        if output.returncode == 0:
            lines = output.stdout.split("\n")
            for line in lines:
                line = line.strip()
                if "Estado" in line or "State" in line:
                    if "conectado" in line.lower() or "connected" in line.lower():
                        resultado["conectado"] = True
                        resultado["tipo"] = "WiFi"
                if "SSID" in line and "BSSID" not in line:
                    parts = line.split(":")
                    if len(parts) >= 2:
                        resultado["ssid"] = parts[1].strip()
        
        # Si no es WiFi, verificar Ethernet
        if not resultado["conectado"]:
            output2 = subprocess.run(
                ["netsh", "interface", "show", "interface"],
                capture_output=True, text=True, timeout=5
            )
            if output2.returncode == 0:
                for line in output2.stdout.split("\n"):
                    if ("Conectado" in line or "Connected" in line) and "Ethernet" in line:
                        resultado["conectado"] = True
                        resultado["tipo"] = "Ethernet"
                        break
    except Exception:
        pass
    
    # Verificar internet real
    resultado["internet"] = verificar_conexion_internet()
    
    # Verificar GitHub
    if resultado["internet"]:
        resultado["github"] = verificar_conexion_github()
    
    return resultado


# =============================================================================
# FUNCIONES DE GITHUB API
# =============================================================================

def _hacer_peticion_github(url: str, timeout: int = HTTP_TIMEOUT) -> dict:
    """Hace una petición GET a la API de GitHub."""
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={
            "User-Agent": "TicketsIT-Updater/1.0",
            "Accept": "application/vnd.github.v3+json",
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GitHubAPIError(f"No encontrado: {url}")
        elif e.code == 403:
            raise GitHubAPIError("Límite de API de GitHub alcanzado. Intente en unos minutos.")
        raise GitHubAPIError(f"Error HTTP {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise SinConexionError(f"No se pudo conectar a GitHub: {e.reason}")
    except socket.timeout:
        raise SinConexionError("Tiempo de espera agotado al conectar con GitHub")
    except Exception as e:
        raise GitHubAPIError(f"Error inesperado: {e}")


def _descargar_archivo_raw(ruta_archivo: str, timeout: int = HTTP_TIMEOUT) -> str:
    """Descarga un archivo raw desde GitHub."""
    url = f"{GITHUB_RAW_BASE}/{ruta_archivo}"
    try:
        ctx = ssl.create_default_context()
        req = urllib.request.Request(url, headers={
            "User-Agent": "TicketsIT-Updater/1.0",
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise GitHubAPIError(f"Archivo no encontrado en repo: {ruta_archivo}")
        raise GitHubAPIError(f"Error descargando {ruta_archivo}: {e}")
    except Exception as e:
        raise GitHubAPIError(f"Error descargando {ruta_archivo}: {e}")


# =============================================================================
# OBTENER INFORMACIÓN DE RELEASES / VERSIONES
# =============================================================================

def obtener_ultimo_release() -> Optional[Dict]:
    """
    Obtiene la información del último release publicado en GitHub.
    
    Returns:
        Dict con información del release o None si no hay releases.
    """
    try:
        data = _hacer_peticion_github(f"{GITHUB_API_BASE}/releases/latest")
        return {
            "version": data.get("tag_name", "").lstrip("v"),
            "nombre": data.get("name", "Sin nombre"),
            "descripcion": data.get("body", "Sin descripción"),
            "fecha": data.get("published_at", "")[:10],
            "url": data.get("html_url", ""),
            "prerelease": data.get("prerelease", False),
            "assets": [
                {
                    "nombre": a["name"],
                    "url": a["browser_download_url"],
                    "tamaño": a["size"],
                }
                for a in data.get("assets", [])
            ],
        }
    except GitHubAPIError:
        return None


def obtener_todos_releases(limite: int = 10) -> List[Dict]:
    """
    Obtiene los últimos N releases publicados.
    
    Returns:
        Lista de releases con su información.
    """
    try:
        data = _hacer_peticion_github(f"{GITHUB_API_BASE}/releases?per_page={limite}")
        releases = []
        for r in data:
            releases.append({
                "version": r.get("tag_name", "").lstrip("v"),
                "nombre": r.get("name", "Sin nombre"),
                "descripcion": r.get("body", "Sin descripción"),
                "fecha": r.get("published_at", "")[:10],
                "url": r.get("html_url", ""),
                "prerelease": r.get("prerelease", False),
            })
        return releases
    except GitHubAPIError:
        return []


def obtener_commits_recientes(limite: int = 15) -> List[Dict]:
    """
    Obtiene los últimos commits del repositorio como changelog alternativo.
    
    Returns:
        Lista de commits con mensaje, autor y fecha.
    """
    try:
        data = _hacer_peticion_github(f"{GITHUB_API_BASE}/commits?per_page={limite}")
        commits = []
        for c in data:
            commit_info = c.get("commit", {})
            autor = commit_info.get("author", {})
            commits.append({
                "sha": c.get("sha", "")[:7],
                "mensaje": commit_info.get("message", "").split("\n")[0],  # Primera línea
                "autor": autor.get("name", "Desconocido"),
                "fecha": autor.get("date", "")[:10],
                "url": c.get("html_url", ""),
            })
        return commits
    except GitHubAPIError:
        return []


def obtener_changelog() -> Optional[str]:
    """
    Intenta descargar el archivo CHANGELOG.md o version.json del repositorio.
    
    Returns:
        Contenido del changelog o None.
    """
    # Intentar varios nombres comunes
    for nombre in ["CHANGELOG.md", "changelog.md", "CHANGES.md", "HISTORIAL.md"]:
        try:
            return _descargar_archivo_raw(nombre)
        except GitHubAPIError:
            continue
    return None


def obtener_version_remota() -> Optional[Dict]:
    """
    Obtiene la versión remota desde version.json en el repo.
    Si no existe, usa el último release o el último commit.
    
    Returns:
        Dict con version, cambios, fecha, etc.
    """
    # Primero intentar version.json (fuente más confiable)
    try:
        contenido = _descargar_archivo_raw("version.json")
        data = json.loads(contenido)
        return {
            "version": data.get("version", ""),
            "fecha": data.get("fecha", ""),
            "cambios": data.get("cambios", []),
            "descripcion": data.get("descripcion", ""),
            "critico": data.get("critico", False),
            "archivos_modificados": data.get("archivos_modificados", []),
            "fuente": "version.json",
        }
    except (GitHubAPIError, json.JSONDecodeError):
        pass
    
    # Fallback: usar último release
    release = obtener_ultimo_release()
    if release:
        # Parsear cambios del body del release
        cambios = []
        if release["descripcion"]:
            for linea in release["descripcion"].split("\n"):
                linea = linea.strip()
                if linea.startswith("- ") or linea.startswith("* ") or linea.startswith("• "):
                    cambios.append(linea.lstrip("-*• ").strip())
        
        return {
            "version": release["version"],
            "fecha": release["fecha"],
            "cambios": cambios,
            "descripcion": release["descripcion"],
            "critico": False,
            "archivos_modificados": [],
            "fuente": "release",
        }
    
    # Último fallback: usar commits
    commits = obtener_commits_recientes(5)
    if commits:
        return {
            "version": f"dev-{commits[0]['sha']}",
            "fecha": commits[0]["fecha"],
            "cambios": [c["mensaje"] for c in commits[:5]],
            "descripcion": "Últimos cambios del repositorio",
            "critico": False,
            "archivos_modificados": [],
            "fuente": "commits",
        }
    
    return None


# =============================================================================
# COMPARACIÓN DE VERSIONES
# =============================================================================

def comparar_versiones(local: str, remota: str) -> int:
    """
    Compara dos versiones semánticas.
    
    Returns:
        -1 si local < remota (hay actualización)
         0 si son iguales
         1 si local > remota
    """
    def parsear(v: str) -> tuple:
        v = v.lstrip("v").strip()
        # Ignorar sufijos como -dev, -beta, etc.
        v = v.split("-")[0]
        partes = []
        for p in v.split("."):
            try:
                partes.append(int(p))
            except ValueError:
                partes.append(0)
        # Asegurar al menos 3 componentes
        while len(partes) < 3:
            partes.append(0)
        return tuple(partes)
    
    try:
        vl = parsear(local)
        vr = parsear(remota)
        if vl < vr:
            return -1
        elif vl > vr:
            return 1
        return 0
    except Exception:
        return 0


def hay_actualizacion_disponible(version_local: str) -> Tuple[bool, Optional[Dict]]:
    """
    Verifica si hay una actualización disponible.
    
    Args:
        version_local: Versión actual instalada.
        
    Returns:
        (hay_update, info_version) - Tupla con bool y datos de la versión remota.
    """
    info = obtener_version_remota()
    if not info:
        return False, None
    
    version_remota = info.get("version", "")
    if not version_remota or version_remota.startswith("dev-"):
        # Si es un commit, siempre ofrecer actualizar
        return True, info
    
    resultado = comparar_versiones(version_local, version_remota)
    return resultado < 0, info


# =============================================================================
# VERIFICAR ARCHIVOS MODIFICADOS
# =============================================================================

def calcular_hash_archivo(ruta: Path) -> str:
    """Calcula el hash SHA256 de un archivo local (normaliza line endings)."""
    try:
        # Leer como texto para normalizar \r\n → \n (consistente con GitHub)
        with open(ruta, "r", encoding="utf-8") as f:
            contenido = f.read()
        return hashlib.sha256(contenido.encode("utf-8")).hexdigest()
    except UnicodeDecodeError:
        # Archivo binario: leer en modo raw
        try:
            sha256 = hashlib.sha256()
            with open(ruta, "rb") as f:
                for bloque in iter(lambda: f.read(8192), b""):
                    sha256.update(bloque)
            return sha256.hexdigest()
        except Exception:
            return ""
    except Exception:
        return ""


def obtener_archivos_diferentes(directorio_local: Path) -> List[Dict]:
    """
    Compara los archivos locales con los del repositorio de GitHub.
    
    Returns:
        Lista de archivos que difieren (necesitan actualización).
    """
    archivos_diff = []
    
    for nombre in ARCHIVOS_ACTUALIZABLES:
        ruta_local = directorio_local / nombre
        
        if not ruta_local.exists():
            archivos_diff.append({
                "nombre": nombre,
                "estado": "faltante",
                "hash_local": "",
                "hash_remoto": "",
            })
            continue
        
        try:
            # Descargar versión remota
            contenido_remoto = _descargar_archivo_raw(nombre)
            hash_remoto = hashlib.sha256(contenido_remoto.encode("utf-8")).hexdigest()
            hash_local = calcular_hash_archivo(ruta_local)
            
            if hash_local != hash_remoto:
                archivos_diff.append({
                    "nombre": nombre,
                    "estado": "modificado",
                    "hash_local": hash_local[:12],
                    "hash_remoto": hash_remoto[:12],
                })
        except GitHubAPIError:
            # Si no existe en el repo, no se cuenta como diferencia
            continue
    
    return archivos_diff


# =============================================================================
# PROCESO DE ACTUALIZACIÓN
# =============================================================================

def crear_backup_actualizacion(directorio: Path) -> Path:
    """
    Crea un backup de los archivos antes de actualizar.
    
    Returns:
        Path al directorio de backup.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = directorio / "backups" / f"pre_update_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    for nombre in ARCHIVOS_ACTUALIZABLES:
        ruta = directorio / nombre
        if ruta.exists():
            shutil.copy2(ruta, backup_dir / nombre)
    
    return backup_dir


def actualizar_archivo(nombre: str, directorio: Path) -> Tuple[bool, str]:
    """
    Descarga y reemplaza un archivo desde GitHub.
    
    Returns:
        (éxito, mensaje)
    """
    try:
        contenido = _descargar_archivo_raw(nombre)
        ruta_destino = directorio / nombre
        
        # Verificar sintaxis Python antes de escribir
        if nombre.endswith(".py"):
            try:
                compile(contenido, nombre, "exec")
            except SyntaxError as e:
                return False, f"Error de sintaxis en archivo remoto: {e}"
        
        # Escribir archivo en modo binario para preservar line endings (\n)
        with open(ruta_destino, "wb") as f:
            f.write(contenido.encode("utf-8"))
        
        return True, f"Actualizado correctamente"
    except GitHubAPIError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Error escribiendo archivo: {e}"


def ejecutar_actualizacion(directorio: Path, archivos: List[str] = None,
                           callback=None) -> Dict:
    """
    Ejecuta la actualización de archivos desde GitHub.
    
    Args:
        directorio: Directorio de instalación.
        archivos: Lista de archivos a actualizar (None = todos los modificados).
        callback: Función callback(progreso, mensaje) para reportar progreso.
        
    Returns:
        Dict con resultados de la actualización.
    """
    resultados = {
        "exito": True,
        "backup_dir": "",
        "archivos_actualizados": [],
        "archivos_fallidos": [],
        "timestamp": datetime.now().isoformat(),
    }
    
    if callback:
        callback(0.05, "Creando backup de seguridad...")
    
    # Backup
    try:
        backup_dir = crear_backup_actualizacion(directorio)
        resultados["backup_dir"] = str(backup_dir)
        if callback:
            callback(0.15, f"Backup creado en: {backup_dir.name}")
    except Exception as e:
        resultados["exito"] = False
        resultados["archivos_fallidos"].append(("backup", str(e)))
        return resultados
    
    # Determinar archivos a actualizar
    if archivos is None:
        if callback:
            callback(0.20, "Comparando archivos con repositorio...")
        diff = obtener_archivos_diferentes(directorio)
        archivos = [d["nombre"] for d in diff]
    
    if not archivos:
        if callback:
            callback(1.0, "No hay archivos que actualizar.")
        return resultados
    
    # Actualizar cada archivo
    total = len(archivos)
    for idx, nombre in enumerate(archivos):
        progreso = 0.25 + (0.70 * (idx / total))
        if callback:
            callback(progreso, f"Actualizando {nombre}... ({idx+1}/{total})")
        
        exito, mensaje = actualizar_archivo(nombre, directorio)
        if exito:
            resultados["archivos_actualizados"].append(nombre)
        else:
            resultados["archivos_fallidos"].append((nombre, mensaje))
            resultados["exito"] = False
    
    # Actualizar estado local
    if callback:
        callback(0.97, "Guardando estado de actualización...")
    
    guardar_estado_actualizacion(directorio, resultados)
    
    if callback:
        callback(1.0, f"¡Actualización completada! ({len(resultados['archivos_actualizados'])} archivos)")
    
    return resultados


# =============================================================================
# ESTADO LOCAL DE ACTUALIZACIONES
# =============================================================================

def guardar_estado_actualizacion(directorio: Path, resultados: Dict):
    """Guarda el estado de la última actualización."""
    estado_path = directorio / ESTADO_ACTUALIZACIONES
    
    estado = cargar_estado_actualizacion(directorio)
    estado["ultima_verificacion"] = datetime.now().isoformat()
    estado["ultima_actualizacion"] = resultados.get("timestamp", "")
    estado["archivos_actualizados"] = resultados.get("archivos_actualizados", [])
    estado["backup_dir"] = resultados.get("backup_dir", "")
    
    # Historial (últimas 20 actualizaciones)
    if "historial" not in estado:
        estado["historial"] = []
    estado["historial"].insert(0, {
        "fecha": resultados.get("timestamp", ""),
        "archivos": resultados.get("archivos_actualizados", []),
        "exito": resultados.get("exito", False),
    })
    estado["historial"] = estado["historial"][:20]
    
    try:
        with open(estado_path, "w", encoding="utf-8") as f:
            json.dump(estado, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def cargar_estado_actualizacion(directorio: Path) -> Dict:
    """Carga el estado guardado de actualizaciones."""
    estado_path = directorio / ESTADO_ACTUALIZACIONES
    try:
        if estado_path.exists():
            with open(estado_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


# =============================================================================
# FUNCIÓN PRINCIPAL DE VERIFICACIÓN RÁPIDA  
# =============================================================================

def verificacion_rapida(version_local: str, directorio: Path) -> Dict:
    """
    Hace una verificación rápida del estado de actualizaciones.
    Usada por el instalador para mostrar información en el menú.
    
    Returns:
        Dict con toda la información necesaria para la UI.
    """
    resultado = {
        "conexion": verificar_wifi_conectado(),
        "hay_actualizacion": False,
        "version_remota": None,
        "archivos_diferentes": [],
        "commits_recientes": [],
        "changelog": None,
        "error": None,
    }
    
    if not resultado["conexion"]["internet"]:
        resultado["error"] = "Sin conexión a internet"
        return resultado
    
    if not resultado["conexion"]["github"]:
        resultado["error"] = "No se puede acceder a GitHub"
        return resultado
    
    try:
        # Verificar si hay nueva versión
        hay_update, info = hay_actualizacion_disponible(version_local)
        resultado["hay_actualizacion"] = hay_update
        resultado["version_remota"] = info
        
        # Obtener commits recientes como changelog
        resultado["commits_recientes"] = obtener_commits_recientes(10)
        
    except Exception as e:
        resultado["error"] = str(e)
    
    return resultado
