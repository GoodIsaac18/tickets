import runpy

# Import estático para que PyInstaller detecte e incluya el paquete src.
import src.apps.receptora.app  # noqa: F401


if __name__ == "__main__":
    runpy.run_module("src.apps.receptora.app", run_name="__main__")
