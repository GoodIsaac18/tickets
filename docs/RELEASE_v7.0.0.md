# Release v7.0.0 - Kubo y Kubito

Fecha: 2026-04-09
Estado: Estable
Tipo: Release mayor de consolidacion empresarial

## Resumen Ejecutivo

La version 7.0.0 consolida el sistema de tickets para un entorno empresarial LAN con foco en estabilidad operativa, consistencia visual, control de calidad y documentacion de despliegue.

Esta entrega prioriza:

- fiabilidad de arranque y ejecucion diaria,
- UX/UI mas consistente en paneles operativos,
- eliminacion de defaults no deseados (tecnicos hardcodeados),
- robustez de validaciones y componentes de red,
- mejor trazabilidad para auditoria y soporte.

## Alcance Funcional

### 1. Operacion de Tickets

- Receptora (Kubo): gestion central de tickets, tecnicos, dashboard, busqueda y configuracion.
- Emisora (Kubito): creacion/seguimiento de tickets por usuario final.
- Comunicacion en tiempo real: HTTP + WebSocket en LAN.

### 2. Datos y Persistencia

- SQLite en modo WAL para concurrencia lectura/escritura.
- Estructura de runtime separada para db, logs, backups y estados.
- Eliminada la insercion automatica de tecnicos por defecto en inicializacion.

### 3. Licencias

- Metadatos y defaults internos alineados a v7.0.0.
- Panel y backend preparados para administracion de versiones actuales.

## Mejoras y Correcciones Relevantes

### UX/UI

- Correccion de layout en Configuracion para evitar errores de render.
- Normalizacion de botones con iconografia unica (sin duplicados en texto + icono).
- Ajustes en Gestion de Tecnicos para una accion visual mas clara.

### Validaciones

- Ajustes de validacion en emisora para evitar bloqueos innecesarios al describir incidencias.
- Reglas de estado y flujos revisados con mensajes de error mas claros.

### Calidad y Pruebas

- Nuevos scripts y pruebas de smoke/arranque.
- Cobertura de casos de seguridad y validadores reforzada.
- Verificaciones de pipeline y utilidades de ejecucion de tests.

## Instalacion

## Requisitos

- Windows 10/11
- Python 3.11+
- Dependencias de `requirements.txt`

## Ejecucion recomendada

```bash
./python_embed/python.exe kubo.py
./python_embed/python.exe kubito.py
```

## Inicializacion de base de datos

```bash
python scripts/init_database.py
```

## Especificaciones de Infraestructura

- Puerto HTTP principal: 5555
- Puerto WebSocket: 5556
- DB: runtime/tickets.db
- Logs: runtime/logs/
- Backups: runtime/backups/

## Tecnologias

- Python 3.11
- Flet 0.81
- SQLite (WAL)
- WebSocket
- PowerShell (scripts operativos)
- Pytest (aseguramiento de calidad)

## Cambios de Compatibilidad

- Ya no se crean tecnicos seed automaticamente en instalaciones nuevas.
- El sistema mantiene compatibilidad de operacion con bases existentes.

## Seguridad y Operacion

- Endurecimiento de servicios HTTP y validacion de payload.
- Validadores de entrada mas estrictos y centralizados.
- Trazabilidad operativa en logs y auditoria de eventos.

## Archivos Clave de la Release

- README.md
- config/version.json
- src/apps/receptora/app.py
- src/apps/emisora/app.py
- src/apps/licencias/server.py
- src/core/data_access.py
- src/core/validators.py
- src/core/servidor_red.py
- src/core/ws_server.py
- scripts/init_database.py
- scripts/release_gate.ps1
- scripts/run_pytest.py

## Notas de Despliegue

1. Asegurar una sola instancia de receptora por host (evitar conflicto de puertos).
2. Validar conectividad LAN y reglas de firewall para 5555/5556.
3. Confirmar estado de licencia y version visible desde panel admin.
4. Ejecutar pruebas base antes de promover a produccion.

## Comando sugerido de validacion rapida

```bash
./python_embed/python.exe -m pytest tests/test_validators.py -q
```

## Cierre

v7.0.0 es una version recomendada para operacion productiva en red local corporativa, con foco en estabilidad, mantenibilidad y una base documental robusta para soporte y evolucion continua.
