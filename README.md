# Kubo y Kubito - Sistema de Gestion de Tickets IT - v6.0.0

Sistema empresarial de dos aplicaciones de escritorio desarrolladas en Python 3.11 y Flet 0.81 para la gestion completa de tickets de soporte tecnico en LAN.

## Novedades v6.0.0

- Estabilizacion de la vista de busqueda global en receptora.
- Correccion de errores runtime de UI en Flet (alignment y propiedades de contenedor).
- Simplificacion de la seccion de busqueda y eliminacion del bloque visual excesivo.
- Mejoras importantes del sistema de licencias (validaciones, endpoints admin y controles de seguridad).
- Hardening de red LAN con rate limit, CORS y limites de payload.
- Logging JSON y health checks para monitoreo operativo.
- Ajustes de launchers emisora/receptora para evitar advertencias de doble carga con runpy.
- Reorganizacion de la raiz y la estructura general del proyecto para despliegue mas limpio.
- Eliminacion del instalador legado: ahora Kubo y Kubito se ejecutan de forma independiente.

## Estructura principal

- `src/apps/` aplicaciones principales: emisora, receptora y licencias.
- `src/core/` infraestructura compartida: DB, red, websocket, logging, backup y validadores.
- `frontend/licencias-panel-react/` panel web de licencias.
- `config/` configuracion centralizada.
- `runtime/` datos operativos (db, logs, backups, estados).
- `scripts/` utilidades de operacion.
- `docs/` documentacion tecnica y operativa.

## Apps finales

- `Kubo`: aplicacion receptora (panel IT / administracion).
- `Kubito`: aplicacion emisora (cliente para crear tickets).
- Ambos entrypoints son independientes y estan en raiz:
  - `kubo.py`
  - `kubito.py`

## Inicio rapido

```bash
./python_embed/python.exe kubo.py
./python_embed/python.exe kubito.py
```

## Health checks

```bash
curl http://localhost:5555/health
curl http://localhost:8787/health
```

## Backup y logging

```bash
python scripts/backup_database.py
```

Logs en:

- `runtime/logs/tickets.log`
- `runtime/logs/licencias.log`
- `runtime/logs/api.log`

## Seguridad

- Validacion y sanitizacion centralizada de entradas.
- Rate limiting en APIs.
- Controles de CORS y payload.
- Health checks para monitoreo.

## Produccion empresarial

- Script recomendado: `scripts/start_produccion_segura.ps1`
- Configuracion de firewall: `scripts/configurar_firewall_empresarial.ps1`
- Guia: `docs/PRODUCCION_EMPRESARIAL.md`

## Instalador legado

El instalador anterior fue retirado en v6.0.0 por obsoleto.
La ejecucion recomendada es directa e independiente con `kubo.py` y `kubito.py`.

## Linea de versiones

- v6.0.0 (2026-04-05): version estable con multiples correcciones, raiz reorganizada, mejoras de licencias y separacion Kubo/Kubito sin instalador legado.
- v5.0.0 (2026-04-04): base de arquitectura modular, logging y health checks.
