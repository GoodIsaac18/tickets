import runpy
import os
import traceback
from datetime import datetime
from pathlib import Path

# Import estático para que PyInstaller detecte e incluya el paquete src.
import src.apps.receptora.app  # noqa: F401
from src.core.startup_guard import StartupGuardError, bootstrap_entrypoint


def _log_startup_fatal(app_id: str, exc: Exception) -> None:
    runtime_logs = Path(__file__).resolve().parent / "runtime" / "logs"
    runtime_logs.mkdir(parents=True, exist_ok=True)
    log_path = runtime_logs / f"startup_{app_id}_fatal.log"
    run_id = os.getenv("TICKETS_STARTUP_RUN_ID", "")
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"[{datetime.utcnow().isoformat()}] run_id={run_id} {type(exc).__name__}: {exc}\n")
        f.write(traceback.format_exc() + "\n")


if __name__ == "__main__":
    try:
        bootstrap_entrypoint(
            app_id="kubo",
            required_paths=("config", "runtime", "icons"),
            security_profile="receptora",
        )
    except StartupGuardError as exc:
        print(f"[STARTUP][ERROR] {exc}")
        _log_startup_fatal("kubo", exc)
        raise SystemExit(1)

    if os.getenv("TICKETS_SMOKE_STARTUP", "0") == "1":
        print("[STARTUP][SMOKE] kubo preflight OK")
        raise SystemExit(0)

    try:
        runpy.run_module("src.apps.receptora.app", run_name="__main__")
    except Exception as exc:
        print(f"[STARTUP][FATAL] kubo: {exc}")
        _log_startup_fatal("kubo", exc)
        raise SystemExit(1)
