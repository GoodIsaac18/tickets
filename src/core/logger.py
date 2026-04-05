"""
Logger centralizado para todo el sistema con rotación automática.
Genera logs JSON con timestamp, nivel, módulo y mensaje estructurado.
"""
import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import sys
from typing import Optional, Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIR = PROJECT_ROOT / "runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR = RUNTIME_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """Formatea logs en JSON para fácil parsing."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def get_logger(name: str, level: str = "INFO") -> logging.Logger:
    """
    Obtiene un logger configurado con file + console handlers.
    
    Args:
        name: Nombre del módulo/logger
        level: Nivel de logging (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        logging.Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))
    
    # Evitar duplicados
    if logger.handlers:
        return logger
    
    # File handler con rotación (100 MB por archivo, max 30 archivos)
    file_handler = logging.handlers.RotatingFileHandler(
        filename=LOGS_DIR / f"{name.lower().replace('.', '_')}.log",
        maxBytes=100 * 1024 * 1024,  # 100 MB
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setFormatter(JSONFormatter())
    logger.addHandler(file_handler)
    
    # Console handler para desarrollo (solo WARNING+)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    console_formatter = logging.Formatter(
        '[%(levelname)s] %(name)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    return logger


def log_info(logger: logging.Logger, message: str, **metadata):
    """Log con metadata opcional."""
    if metadata:
        message = f"{message} | {json.dumps(metadata, ensure_ascii=False)}"
    logger.info(message)


def log_error(logger: logging.Logger, message: str, exception: Optional[Exception] = None, **metadata):
    """Log de error con stack trace opcional."""
    if metadata:
        message = f"{message} | {json.dumps(metadata, ensure_ascii=False)}"
    if exception:
        logger.error(message, exc_info=exception)
    else:
        logger.error(message)


# Singleton loggers iniciados
_loggers: Dict[str, logging.Logger] = {}


def init_logging(level_override: Optional[str] = None) -> None:
    """Inicializa el sistema de logging global."""
    from pathlib import Path
    import json
    
    # Cargar nivel desde config/app.json si existe
    config_path = PROJECT_ROOT / "config" / "app.json"
    level = level_override or "INFO"
    
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                level = config.get("logging", {}).get("nivel", "INFO")
        except Exception:
            pass
    
    # Pre-crear loggers principales
    _loggers["tickets"] = get_logger("tickets", level)
    _loggers["licencias"] = get_logger("licencias", level)
    _loggers["api"] = get_logger("api", level)


# Inicializar loggers al importar
init_logging()
