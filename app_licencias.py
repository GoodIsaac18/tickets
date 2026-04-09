from src.apps.licencias.server import *  # noqa: F401,F403
from src.apps.licencias.server import main as _main
from src.core.startup_guard import StartupGuardError, bootstrap_entrypoint
from pathlib import Path
from datetime import datetime
import os
import traceback


def _log_startup_fatal(app_id: str, exc: Exception) -> None:
    """Persistencia mínima para fallos fatales de arranque."""
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
            app_id="app_licencias",
            required_paths=("runtime",),
            security_profile="licencias",
        )
    except StartupGuardError as exc:
        print(f"[STARTUP][ERROR] {exc}")
        _log_startup_fatal("app_licencias", exc)
        raise SystemExit(1)

    if os.getenv("TICKETS_SMOKE_STARTUP", "0") == "1":
        print("[STARTUP][SMOKE] app_licencias preflight OK")
        raise SystemExit(0)

    try:
        _main()
    except Exception as exc:
        print(f"[STARTUP][FATAL] app_licencias: {exc}")
        _log_startup_fatal("app_licencias", exc)
        raise SystemExit(1)
