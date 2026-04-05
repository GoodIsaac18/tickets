"""
Sistema de backup y restore para base de datos tickets.
Realiza backups automáticos con compresión e índices de integridad.
"""
import shutil
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import gzip

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
BACKUPS_DIR = RUNTIME_DIR / "backups"
BACKUPS_DIR.mkdir(parents=True, exist_ok=True)


class DatabaseBackup:
    """Gestiona backups de la base de datos tickets."""
    
    DB_PATH = RUNTIME_DIR / "tickets.db"
    METADATA_PATH = BACKUPS_DIR / "backup_index.json"
    
    @staticmethod
    def crear_backup(descripcion: str = "Auto backup") -> Optional[Path]:
        """
        Crea backup comprimido de la base de datos.
        
        Args:
            descripcion: Descripción del backup (ej: "Antes de actualizar")
        
        Returns:
            Path del archivo backup creado o None si falla
        """
        if not DatabaseBackup.DB_PATH.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"tickets_backup_{timestamp}.db.gz"
        backup_path = BACKUPS_DIR / backup_name
        
        try:
            # Crear backup con sqlite3 backup API
            source = sqlite3.connect(str(DatabaseBackup.DB_PATH))
            target = sqlite3.connect(":memory:")
            
            # Copiar DB a memoria
            with source:
                source.backup(target)
            
            # Guardar desde memoria a archivo comprimido
            with open(backup_path, 'wb') as f_out:
                db_data = target.iterdump()
                sql_text = '\n'.join(db_data).encode('utf-8')
                with gzip.GzipFile(fileobj=f_out, mode='wb') as gz:
                    gz.write(sql_text)
            
            # Registrar en índice
            DatabaseBackup._registrar_backup(backup_path, descripcion)
            
            return backup_path
        
        except Exception as e:
            print(f"Error creando backup: {e}")
            return None
        finally:
            try:
                source.close()
                target.close()
            except:
                pass
    
    @staticmethod
    def restaurar_backup(backup_path: Path) -> bool:
        """
        Restaura base de datos desde backup.
        
        Args:
            backup_path: Path al archivo backup .gz
        
        Returns:
            True si éxito, False si falla
        """
        if not backup_path.exists():
            return False
        
        try:
            # Crear backup del actual como safety measure
            DatabaseBackup.crear_backup("Pre-restore backup")
            
            # Descomprimir e importar
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w+b', delete=False, suffix='.sql') as tmp:
                with gzip.open(backup_path, 'rb') as gz:
                    tmp.write(gz.read())
                tmp_path = tmp.name
            
            # Ejecutar SQL
            conn = sqlite3.connect(str(DatabaseBackup.DB_PATH))
            with open(tmp_path, 'r', encoding='utf-8') as f:
                conn.executescript(f.read())
            conn.commit()
            conn.close()
            
            # Limpiar temp
            Path(tmp_path).unlink()
            
            return True
        
        except Exception as e:
            print(f"Error restaurando backup: {e}")
            return False
    
    @staticmethod
    def limpiar_backups_antiguos(dias: int = 30) -> int:
        """
        Elimina backups más antiguos que N días.
        
        Args:
            dias: Días a guardar (default: 30)
        
        Returns:
            Cantidad de archivos eliminados
        """
        limite = datetime.now() - timedelta(days=dias)
        eliminados = 0
        
        for backup in BACKUPS_DIR.glob("tickets_backup_*.db.gz"):
            if datetime.fromtimestamp(backup.stat().st_mtime) < limite:
                backup.unlink()
                eliminados += 1
        
        return eliminados
    
    @staticmethod
    def listar_backups() -> List[Dict]:
        """
        Lista todos los backups disponibles.
        
        Returns:
            Lista de dicts con info de backups (timestamp, tamaño, descripción)
        """
        backups = []
        
        try:
            with open(DatabaseBackup.METADATA_PATH, 'r') as f:
                metadata = json.load(f)
                backups = metadata.get("backups", [])
        except:
            pass
        
        # Verificar que archivos existan
        backups = [b for b in backups if Path(b["path"]).exists()]
        
        return sorted(backups, key=lambda x: x["timestamp"], reverse=True)
    
    @staticmethod
    def _registrar_backup(path: Path, descripcion: str) -> None:
        """Registra metadatos del backup."""
        try:
            metadata = {"backups": []}
            if DatabaseBackup.METADATA_PATH.exists():
                with open(DatabaseBackup.METADATA_PATH, 'r') as f:
                    metadata = json.load(f)
            
            metadata["backups"].append({
                "timestamp": datetime.now().isoformat(),
                "path": str(path),
                "size_mb": path.stat().st_size / (1024 * 1024),
                "descripcion": descripcion
            })
            
            # Mantener solo últimos 50 backups
            metadata["backups"] = metadata["backups"][-50:]
            
            with open(DatabaseBackup.METADATA_PATH, 'w') as f:
                json.dump(metadata, f, indent=2)
        
        except Exception as e:
            print(f"Error registrando backup: {e}")


def auto_backup_diario() -> Optional[Path]:
    """Ejecuta backup diario automático si no hay uno reciente."""
    backups = DatabaseBackup.listar_backups()
    
    if backups:
        ultimo = backups[0]
        horas_desde_ultimo = (datetime.now() - datetime.fromisoformat(ultimo["timestamp"])).total_seconds() / 3600
        if horas_desde_ultimo < 24:
            return None  # Backup reciente existe
    
    # Limpiar backups antiguos y crear uno nuevo
    DatabaseBackup.limpiar_backups_antiguos()
    return DatabaseBackup.crear_backup("Auto-backup diario")
