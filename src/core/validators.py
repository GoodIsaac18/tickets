"""
Validación y sanitización de inputs para todo el sistema.
Previene inyecciones, campos vacíos y datos inválidos.
"""
from typing import Dict, Any, Optional, List
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class InputValidator:
    """Valida y sanitiza inputs del usuario."""
    
    # Límites de caracteres
    MAX_DESCRIPCION = 5000
    MAX_NOTAS = 10000
    MAX_NOMBRE = 255
    MAX_EMAIL = 254
    MAX_TELEFONO = 30
    
    # Categorías y estados permitidos
    CATEGORIAS_VALIDAS = ["Red", "Hardware", "Software", "Accesos", "Impresoras", "Email", "Otros"]
    ESTADOS_VALIDOS = ["Abierto", "En Cola", "En Proceso", "En Espera", "Cerrado", "Cancelado"]
    PRIORIDADES_VALIDAS = ["Crítica", "Alta", "Media", "Baja"]
    
    @staticmethod
    def sanitize_string(text: str, max_length: int = 255, allow_newlines: bool = False) -> str:
        """
        Sanitiza un string: elimina espacios, controla longitud.
        
        Args:
            text: String a sanitizar
            max_length: Longitud máxima permitida
            allow_newlines: Si permite saltos de línea
        
        Returns:
            String sanitizado
        """
        if not isinstance(text, str):
            return ""
        
        # Eliminar whitespace extremo
        text = text.strip()
        
        # Si no permite saltos de línea, reemplazarlos con espacios
        if not allow_newlines:
            text = text.replace('\n', ' ').replace('\r', ' ')
        
        # Limitar longitud
        if len(text) > max_length:
            text = text[:max_length]
        
        # Eliminar caracteres de control (excepto newlines si permitidos)
        if allow_newlines:
            text = ''.join(c for c in text if ord(c) >= 32 or c in '\n\r\t')
        else:
            text = ''.join(c for c in text if ord(c) >= 32 or c == '\t')
        
        return text
    
    @staticmethod
    def validar_ticket(datos: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Valida datos para crear/actualizar ticket.
        
        Returns:
            (válido, mensaje_error)
        """
        # Descripción es obligatoria y no vacía
        descripcion = InputValidator.sanitize_string(
            datos.get('descripcion', ''),
            max_length=InputValidator.MAX_DESCRIPCION,
            allow_newlines=True
        )
        if not descripcion or len(descripcion) < 3:
            return False, "La descripción debe tener al menos 3 caracteres"
        
        # Categoría validación
        categoria = datos.get('categoria', '').strip()
        if categoria not in InputValidator.CATEGORIAS_VALIDAS:
            return False, f"Categoría inválida. Válidas: {', '.join(InputValidator.CATEGORIAS_VALIDAS)}"
        
        # Prioridad validación
        prioridad = datos.get('prioridad', '').strip()
        if prioridad not in InputValidator.PRIORIDADES_VALIDAS:
            return False, f"Prioridad inválida. Válidas: {', '.join(InputValidator.PRIORIDADES_VALIDAS)}"
        
        # Usuario y hostname (campos automáticos, pero validar si vienen)
        usuario = InputValidator.sanitize_string(datos.get('usuario_ad', ''), max_length=100)
        hostname = InputValidator.sanitize_string(datos.get('hostname', ''), max_length=100)
        
        if usuario and not re.match(r'^[a-zA-Z0-9._-]+$', usuario):
            return False, "Usuario inválido"
        
        if hostname and not re.match(r'^[a-zA-Z0-9.-]+$', hostname):
            return False, "Hostname inválido"
        
        return True, None
    
    @staticmethod
    def validar_notas_resolucion(notas: str) -> tuple[bool, Optional[str]]:
        """Valida notas de resolución."""
        notas = InputValidator.sanitize_string(
            notas,
            max_length=InputValidator.MAX_NOTAS,
            allow_newlines=True
        )
        if not notas or len(notas) < 1:
            return False, "Las notas no pueden estar vacías"
        
        return True, None
    
    @staticmethod
    def validar_tecnico(datos: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Valida datos de técnico."""
        nombre = InputValidator.sanitize_string(
            datos.get('nombre', ''),
            max_length=InputValidator.MAX_NOMBRE
        )
        if not nombre or len(nombre) < 2:
            return False, "Nombre debe tener al menos 2 caracteres"
        
        # Validar email si existe
        email = datos.get('email', '').strip()
        if email and not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
            return False, "Email inválido"
        
        # Validar teléfono si existe
        telefono = datos.get('telefono', '').strip()
        if telefono and not re.match(r'^[\d\s\-\+\(\)\.]+$', telefono):
            return False, "Teléfono inválido"
        
        return True, None
    
    @staticmethod
    def validar_estado_cambio(estado_actual: str, estado_nuevo: str) -> tuple[bool, Optional[str]]:
        """Valida transición de estado."""
        if estado_actual == estado_nuevo:
            return False, "El estado ya es el mismo"
        
        if estado_nuevo not in InputValidator.ESTADOS_VALIDOS:
            return False, f"Estado inválido: {estado_nuevo}"
        
        # Flujo flexible:
        # - Los estados terminales no pueden cambiarse desde validación de transición.
        # - Entre estados activos se permite mover libremente para no bloquear operación.
        transiciones_validas = {
            "Abierto": ["En Cola", "En Proceso", "En Espera", "Cerrado", "Cancelado"],
            "En Cola": ["Abierto", "En Proceso", "En Espera", "Cerrado", "Cancelado"],
            "En Proceso": ["Abierto", "En Cola", "En Espera", "Cerrado", "Cancelado"],
            "En Espera": ["Abierto", "En Cola", "En Proceso", "Cerrado", "Cancelado"],
            "Cerrado": [],
            "Cancelado": []
        }
        
        if estado_actual not in transiciones_validas:
            return True, None  # Si el estado actual es desconocido, permitir
        
        if estado_nuevo not in transiciones_validas[estado_actual]:
            return False, f"Transición de {estado_actual} -> {estado_nuevo} no permitida"
        
        return True, None


def validar_ip(ip: str) -> bool:
    """Valida formato de dirección IP."""
    parts = ip.split('.')
    if len(parts) != 4:
        return False
    try:
        return all(0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def validar_mac_address(mac: str) -> bool:
    """Valida formato de MAC address."""
    return bool(re.match(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$', mac))


def sanitize_filename(filename: str) -> str:
    """Sanitiza nombre de archivo."""
    # Reemplazar caracteres inválidos
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    filename = re.sub(invalid_chars, '_', filename)
    # Limitar longitud
    return filename[:255]
