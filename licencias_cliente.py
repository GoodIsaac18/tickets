from src.apps.licencias.client import *  # noqa: F401,F403

if __name__ == "__main__":
    import runpy

    runpy.run_module("src.apps.licencias.client", run_name="__main__")
