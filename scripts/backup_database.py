#!/usr/bin/env python3
"""
Script para crear backup manual de la base de datos tickets.
Uso: python scripts/backup_database.py [descripcion]

Ejemplo:
  python scripts/backup_database.py "Backup antes de cambios importantes"
"""
import sys
from pathlib import Path

# Agregar src al path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from core.backup import DatabaseBackup


def main():
    """Ejecuta backup manual."""
    descripcion = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Backup manual"
    
    print(f"📦 Creando backup: {descripcion}")
    backup_path = DatabaseBackup.crear_backup(descripcion)
    
    if backup_path:
        size_mb = backup_path.stat().st_size / (1024 * 1024)
        print(f"✅ Backup creado exitosamente")
        print(f"📍 Ubicación: {backup_path}")
        print(f"📊 Tamaño: {size_mb:.2f} MB")
    else:
        print("❌ Error creando backup")
        sys.exit(1)
    
    # Listar backups recientes
    print("\n📋 Últimos 5 backups:")
    backups = DatabaseBackup.listar_backups()
    for i, backup in enumerate(backups[:5], 1):
        timestamp = backup['timestamp']
        size = backup['size_mb']
        desc = backup['descripcion']
        print(f"  {i}. [{timestamp}] {size:.2f}MB - {desc}")
    
    # Limpiar backups antiguos
    removed = DatabaseBackup.limpiar_backups_antiguos(dias=30)
    if removed > 0:
        print(f"\n🧹 Limpiados {removed} backup(s) más antiguo(s) de 30 días")


if __name__ == "__main__":
    main()
