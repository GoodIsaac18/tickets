import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core import startup_guard
from src.core.startup_guard import StartupGuardError, _release_lock, bootstrap_entrypoint


@pytest.fixture
def project_tmp(monkeypatch, tmp_path):
    (tmp_path / "runtime").mkdir(parents=True, exist_ok=True)
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)
    (tmp_path / "icons").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("TICKETS_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("TICKETS_SINGLE_INSTANCE", "1")
    yield tmp_path


def test_bootstrap_crea_lock(project_tmp):
    bootstrap_entrypoint("test_app", required_paths=("runtime",), security_profile=None)
    lock = project_tmp / "runtime" / "locks" / "test_app.lock"
    assert lock.exists()
    data = json.loads(lock.read_text(encoding="utf-8"))
    assert data["app_id"] == "test_app"
    _release_lock("test_app")


def test_bootstrap_bloquea_doble_instancia(project_tmp):
    lock_dir = project_tmp / "runtime" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock = lock_dir / "dup_app.lock"
    lock.write_text(json.dumps({"app_id": "dup_app", "pid": os.getpid()}), encoding="utf-8")

    with pytest.raises(StartupGuardError):
        bootstrap_entrypoint("dup_app", required_paths=("runtime",), security_profile=None)


def test_bootstrap_falla_si_falta_path(monkeypatch, tmp_path):
    monkeypatch.setenv("TICKETS_PROJECT_ROOT", str(tmp_path))
    with pytest.raises(StartupGuardError):
        bootstrap_entrypoint("miss_app", required_paths=("runtime", "config"), security_profile=None)


def test_profile_receptora_failfast_en_produccion(project_tmp, monkeypatch):
    monkeypatch.setenv("TICKETS_MODE", "produccion")
    monkeypatch.setenv("TICKETS_HTTP_REQUIRE_API_KEY", "0")
    monkeypatch.setenv("TICKETS_HTTP_API_KEY", "clave-corta")
    monkeypatch.setenv("TICKETS_HTTP_CORS_ORIGINS", "*")

    with pytest.raises(StartupGuardError):
        bootstrap_entrypoint("kubo_guard", required_paths=("runtime",), security_profile="receptora")


def test_profile_licencias_failfast_en_produccion(project_tmp, monkeypatch):
    monkeypatch.setenv("TICKETS_MODE", "produccion")
    monkeypatch.setenv("TICKETS_LICENSE_ADMIN_KEY", "123")
    monkeypatch.setenv("TICKETS_LICENSE_CORS_ORIGINS", "*")

    with pytest.raises(StartupGuardError):
        bootstrap_entrypoint("lic_guard", required_paths=("runtime",), security_profile="licencias")


def test_project_root_usa_variable_entorno(monkeypatch, tmp_path):
    monkeypatch.setenv("TICKETS_PROJECT_ROOT", str(tmp_path))
    assert startup_guard._project_root() == tmp_path.resolve()


def test_pid_running_branch_posix_false(monkeypatch):
    monkeypatch.setattr(startup_guard.os, "name", "posix", raising=False)
    monkeypatch.setattr(startup_guard.os, "kill", lambda pid, sig: (_ for _ in ()).throw(OSError("dead")))
    assert startup_guard._pid_running(12345) is False


def test_read_lock_pid_con_archivo_invalido(tmp_path):
    lock_path = tmp_path / "bad.lock"
    lock_path.write_text("not-json", encoding="utf-8")
    assert startup_guard._read_lock_pid(lock_path) == 0


def test_read_lock_pid_excepcion_de_lectura(monkeypatch, tmp_path):
    lock_path = tmp_path / "bad2.lock"

    def raise_io(*args, **kwargs):
        raise OSError("boom")

    monkeypatch.setattr(Path, "read_text", raise_io, raising=False)
    assert startup_guard._read_lock_pid(lock_path) == 0


def test_acquire_single_instance_limpia_lock_huerfano(monkeypatch, project_tmp):
    lock_dir = project_tmp / "runtime" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock = lock_dir / "orph.lock"
    lock.write_text(json.dumps({"app_id": "orph", "pid": 0}), encoding="utf-8")

    handle = startup_guard._acquire_single_instance("orph")
    try:
        assert handle.lock_path.exists()
    finally:
        _release_lock("orph")


def test_release_lock_sin_handle_no_falla():
    _release_lock("missing-app")


def test_bootstrap_single_instance_desactivado(monkeypatch, project_tmp):
    monkeypatch.setenv("TICKETS_SINGLE_INSTANCE", "0")
    bootstrap_entrypoint("no_lock_app", required_paths=("runtime",), security_profile=None)
    assert "no_lock_app" not in startup_guard._ACTIVE_LOCKS


def test_runtime_dir_crea_carpeta(monkeypatch, tmp_path):
    monkeypatch.setenv("TICKETS_PROJECT_ROOT", str(tmp_path))
    runtime_dir = startup_guard._runtime_dir()
    assert runtime_dir.exists()
    assert runtime_dir.name == "runtime"


def test_pid_running_branch_windows_true(monkeypatch):
    fake_kernel32 = SimpleNamespace(
        OpenProcess=lambda flags, inherit, pid: 123,
        CloseHandle=lambda handle: True,
    )
    fake_ctypes = SimpleNamespace(windll=SimpleNamespace(kernel32=fake_kernel32))
    monkeypatch.setattr(startup_guard.os, "name", "nt", raising=False)
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    assert startup_guard._pid_running(321) is True


def test_pid_running_branch_windows_false(monkeypatch):
    fake_kernel32 = SimpleNamespace(
        OpenProcess=lambda flags, inherit, pid: 0,
        CloseHandle=lambda handle: True,
    )
    fake_ctypes = SimpleNamespace(windll=SimpleNamespace(kernel32=fake_kernel32))
    monkeypatch.setattr(startup_guard.os, "name", "nt", raising=False)
    monkeypatch.setitem(sys.modules, "ctypes", fake_ctypes)
    assert startup_guard._pid_running(321) is False


def test_validate_production_security_noop_si_no_strict(monkeypatch):
    monkeypatch.setenv("TICKETS_MODE", "desarrollo")
    monkeypatch.setenv("TICKETS_STRICT_SECURITY", "0")
    startup_guard._validate_production_security("receptora")


def test_bootstrap_idempotente_si_ya_esta_activo(monkeypatch):
    startup_guard._ACTIVE_LOCKS["dup"] = startup_guard._LockHandle("dup", Path("ignored"))
    try:
        bootstrap_entrypoint("dup", required_paths=(), security_profile=None)
    finally:
        startup_guard._ACTIVE_LOCKS.pop("dup", None)


def test_startup_report_incluye_run_id_y_bind(project_tmp, monkeypatch):
    monkeypatch.setenv("TICKETS_HTTP_BIND_HOST", "127.0.0.1")
    monkeypatch.setenv("TICKETS_HTTP_PORT", "5555")
    report = startup_guard.build_startup_report(
        "kubo",
        required_paths=("runtime", "config"),
        security_profile="receptora",
    )
    assert report.get("run_id")
    assert report.get("bind_target") == "127.0.0.1:5555"
    assert isinstance(report.get("bind_available"), bool)


def test_profile_runtime_falla_si_puerto_ocupado(monkeypatch):
    monkeypatch.setattr(startup_guard, "_is_port_available", lambda host, port: False)
    monkeypatch.setenv("TICKETS_LICENSE_HOST", "127.0.0.1")
    monkeypatch.setenv("TICKETS_LICENSE_PORT", "8787")
    with pytest.raises(StartupGuardError):
        startup_guard._validate_profile_runtime("licencias")
