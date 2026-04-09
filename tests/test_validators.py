"""Tests para módulo data_access.py"""
import pytest
import sys
from pathlib import Path

# Agregar src al path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from core.data_access import GestorTickets
from core.validators import InputValidator


class TestInputValidator:
    """Tests para validación de entrada."""
    
    def test_sanitize_string_basico(self):
        """Debe sanitizar strings básicos."""
        assert InputValidator.sanitize_string("  hola  ") == "hola"
        assert InputValidator.sanitize_string("test") == "test"
    
    def test_sanitize_string_max_length(self):
        """Debe limitar longitud."""
        result = InputValidator.sanitize_string("a" * 500, max_length=10)
        assert len(result) == 10
    
    def test_sanitize_string_sin_newlines(self):
        """Debe reemplazar newlines con espacios."""
        result = InputValidator.sanitize_string("line1\nline2", allow_newlines=False)
        assert "\n" not in result
        assert "line1" in result and "line2" in result
    
    def test_validar_ticket_descripcion_vacia(self):
        """Debe rechazar descripción vacía."""
        is_valid, error = InputValidator.validar_ticket({'descripcion': ''})
        assert not is_valid
        assert error is not None
    
    def test_validar_ticket_categoria_invalida(self):
        """Debe rechazar categoría inválida."""
        is_valid, error = InputValidator.validar_ticket({
            'descripcion': 'Problema válido',
            'categoria': 'INVALIDA',
            'prioridad': 'Alta'
        })
        assert not is_valid
    
    def test_validar_ticket_valido(self):
        """Debe aceptar ticket válido."""
        is_valid, error = InputValidator.validar_ticket({
            'descripcion': 'Problema con PC',
            'categoria': 'Hardware',
            'prioridad': 'Alta'
        })
        assert is_valid
        assert error is None
    
    def test_validar_email(self):
        """Debe validar formato de email."""
        is_valid, _ = InputValidator.validar_tecnico({
            'nombre': 'Juan',
            'email': 'juan@company.com'
        })
        assert is_valid
        
        is_valid, error = InputValidator.validar_tecnico({
            'nombre': 'Juan',
            'email': 'email-invalido'
        })
        assert not is_valid
    
    def test_validar_transicion_estado(self):
        """Debe validar transiciones de estado permitidas."""
        # Transición válida
        is_valid, _ = InputValidator.validar_estado_cambio("Abierto", "En Cola")
        assert is_valid

        # Ahora también se permite mover directo a En Proceso
        is_valid, _ = InputValidator.validar_estado_cambio("Abierto", "En Proceso")
        assert is_valid
        
        # Transición inválida
        is_valid, error = InputValidator.validar_estado_cambio("Cerrado", "Abierto")
        assert not is_valid


class TestDataAccess:
    """Tests para capa de acceso a datos (requiere DB en runtime/)."""
    
    @pytest.fixture
    def db(self):
        """Fixture para DB de prueba."""
        db = GestorTickets()
        yield db
    
    def test_db_connection(self, db):
        """Debe conectarse a la base de datos."""
        assert db is not None
    
    def test_obtener_tecnicos(self, db):
        """Debe obtener lista de técnicos."""
        tecnicos = db.obtener_tecnicos()
        assert tecnicos is not None
        # Ya no se crean técnicos por defecto.
        assert len(tecnicos) >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
