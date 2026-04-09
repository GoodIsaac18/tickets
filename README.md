# Kubo y Kubito - Sistema de Gestion de Tickets IT - v7.0.0

Plataforma empresarial de soporte tecnico LAN compuesta por dos aplicaciones de escritorio construidas con Python 3.11 y Flet 0.81:

- `Kubo` (receptora): panel IT para operacion, seguimiento, analitica y administracion.
- `Kubito` (emisora): cliente de usuario final para crear y consultar tickets.

Esta version 7.0.0 consolida estabilidad operativa, mejoras de UX/UI, endurecimiento de seguridad y una base de release lista para despliegue productivo.

## Novedades v7.0.0

- Eliminacion de tecnicos hardcodeados por defecto en inicializacion de base de datos.
- Ajustes de experiencia de uso en vistas clave (Configuracion, Gestion de Tecnicos).
- Correcciones de layout y botones en Flet para evitar errores de render y duplicacion visual de iconos.
- Mejora en validaciones de formularios para evitar bloqueos innecesarios en la carga de tickets.
- Alineacion de metadatos de version y panel de licencias a v7.0.0.
- Actualizacion de documentacion tecnica, operativa y de release para instalacion empresarial.

## Especificaciones Tecnicas

- Lenguaje: Python 3.11+
- UI Desktop: Flet 0.81
- Base de datos: SQLite (WAL mode)
- Comunicacion:
  - HTTP: puerto 5555
  - WebSocket: puerto 5556
- Licencias:
  - Servicio local/admin de licencias
  - Frontend React para panel de licencias (modulo separado)
- Sistema operativo objetivo: Windows 10/11

## Arquitectura

- `src/apps/`: aplicaciones de negocio
  - `src/apps/receptora/app.py`
  - `src/apps/emisora/app.py`
  - `src/apps/licencias/server.py`
- `src/core/`: servicios de infraestructura
  - acceso a datos (`data_access.py`)
  - red HTTP (`servidor_red.py`)
  - websocket (`ws_server.py`)
  - validadores y utilidades transversales
- `config/`: configuracion y versionado
- `runtime/`: datos vivos (DB, logs, backups, estados)
- `scripts/`: automatizaciones operativas y de release
- `docs/`: guias de produccion y troubleshooting

## Instalacion y Puesta en Marcha

### 1) Requisitos

- Windows 10/11
- Python 3.11 (opcional si usas `python_embed`)

### 2) Entorno recomendado

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3) Inicializar base de datos

```bash
python scripts/init_database.py
```

### 4) Ejecutar aplicaciones

```bash
./python_embed/python.exe kubo.py
./python_embed/python.exe kubito.py
```

Tambien puedes ejecutar entrypoints internos:

```bash
./python_embed/python.exe src/apps/receptora/app.py
./python_embed/python.exe src/apps/emisora/app.py
```

## Operacion y Monitoreo

### Health checks

```bash
curl http://localhost:5555/health
curl http://localhost:8787/health
```

### Backup y logs

```bash
python scripts/backup_database.py
```

Rutas de logs comunes:

- `runtime/logs/tickets.log`
- `runtime/logs/licencias.log`
- `runtime/logs/api.log`

## Seguridad

- Validacion/sanitizacion centralizada de inputs.
- Rate limiting en endpoints HTTP.
- Controles de CORS y limites de payload.
- Registros de auditoria por ticket y trazabilidad.
- Health checks para supervisar disponibilidad.

## Mejoras Relevantes Incluidas

- Configuracion:
  - Reorganizacion visual de botones de accion.
  - Correccion de errores de render en controles.
- Gestion de Tecnicos:
  - Correccion de botones con iconografia duplicada.
- Emisora:
  - Ajuste de validacion de descripcion para reducir falsos bloqueos.
- Datos:
  - Desactivada la creacion automatica de tecnicos por defecto.

## Produccion Empresarial

- Script recomendado: `scripts/start_produccion_segura.ps1`
- Configuracion de firewall: `scripts/configurar_firewall_empresarial.ps1`
- Guia completa: `docs/PRODUCCION_EMPRESARIAL.md`

## Instalador y Distribucion

- El instalador legado fue retirado en versiones anteriores.
- Distribucion recomendada:
  - `Kubo` y `Kubito` como ejecutables independientes.
  - o ejecucion directa con `python_embed`.

## Historial de Versiones

- v7.0.0 (2026-04-09): release de consolidacion empresarial, mejoras UX/UI, limpieza de defaults, endurecimiento y documentacion integral.
- v6.0.0 (2026-04-05): reorganizacion mayor de raiz, mejoras de licencias y separacion Kubo/Kubito.
- v5.0.0 (2026-04-04): base modular con SQLite, logging y health checks.
