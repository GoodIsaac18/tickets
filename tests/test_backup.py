"""Tests para backup/restore de SQLite."""
import sqlite3
import sys
from pathlib import Path

import pytest

# Agregar src al path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import core.backup as backup_module
from core.backup import DatabaseBackup


def _crear_db_prueba(db_path: Path) -> None:
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE IF NOT EXISTS demo (id INTEGER PRIMARY KEY, nombre TEXT)")
    conn.execute("INSERT INTO demo(nombre) VALUES ('alpha')")
    conn.commit()
    conn.close()


@pytest.fixture
def backup_ctx(tmp_path):
    runtime = tmp_path / "runtime"
    backups = runtime / "backups"
    runtime.mkdir(parents=True, exist_ok=True)
    backups.mkdir(parents=True, exist_ok=True)

    db_path = runtime / "tickets.db"
    _crear_db_prueba(db_path)

    # Monkeypatch de rutas del módulo
    backup_module.BACKUPS_DIR = backups
    DatabaseBackup.DB_PATH = db_path
    DatabaseBackup.METADATA_PATH = backups / "backup_index.json"

    return db_path, backups


def test_crear_backup_ok(backup_ctx):
    _db_path, backups = backup_ctx
    out = DatabaseBackup.crear_backup("test")
    assert out is not None
    assert out.exists()
    assert out.suffix == ".gz"
    assert any(backups.glob("tickets_backup_*.db.gz"))


def test_listar_backups_devuelve_items(backup_ctx):
    DatabaseBackup.crear_backup("test-list")
    backups = DatabaseBackup.listar_backups()
    assert len(backups) >= 1
    assert "descripcion" in backups[0]


def test_restaurar_backup_archivo_inexistente_retorna_false(backup_ctx):
    fake = Path("no_existe_backup.db.gz")
    assert DatabaseBackup.restaurar_backup(fake) is False
