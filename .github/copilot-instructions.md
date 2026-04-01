# 🎫 Tickets System - AI Agent Instructions

**Context**: Professional IT support ticket management system with two desktop applications (Flet UI) communicating over LAN using HTTP + WebSocket. Stored in embedded Python 3.11 environment with SQLite database and auto-update from GitHub.

## Quick Facts

| Property | Value |
|----------|-------|
| **Language** | Python 3.11.9+ |
| **UI Framework** | Flet 0.81 (modern, Flutter-based) |
| **Database** | SQLite (WAL mode, auto-created) |
| **Communication** | HTTP (5555) + WebSocket (5556) on LAN |
| **Deployment** | Embedded Python + PyInstaller executables |
| **Auto-Update** | GitHub (GoodIsaac18/tickets main branch) |
| **Target OS** | Windows 10/11 only |

## How to Run the System

### Development Setup

```bash
# 1. Virtual environment (optional - python_embed/ already embeds Python)
python -m venv venv
venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database (creates tickets.db automatically)
python init_database.py

# 4. In Terminal 1: Start IT panel
python app_receptora.py    # Server component

# 5. In Terminal 2+: Start worker apps
python app_emisora.py      # Worker interface (repeatable for multiple workers)

# 6. Access at: http://localhost:5555 (if needed for web interface)
```

### Quick Commands

```bash
# Reset database (WARNING: loses all data)
python init_database.py --reset

# Build installer executable (requires PyInstaller)
pyinstaller Instalador_Tickets.spec

# Run worker app with console visible (for debugging)
ejecutar_emisora.bat
```

**Reference**: [README.md](../README.md#-instalación) for detailed setup instructions.

## Core Application Architecture

### Components

```
app_receptora.py (IT Panel - Management Hub)
  ├─ Creates/opens tickets.db (auto-init if missing)
  ├─ Hosts HTTP server (port 5555)
  ├─ Hosts WebSocket server (port 5556)
  └─ Manages technician assignments, reports, equipment scanning

  ↕ (HTTP + WebSocket over LAN)

app_emisora.py (Worker Application - Ticket Submission)
  ├─ Captures: Windows user, hostname, MAC address (automatic)
  ├─ Creates tickets with category/priority/description
  ├─ Receives real-time status updates via WebSocket
  └─ Multiple instances can connect to same server

Data Layer:
  ├─ data_access.py    → SQLite interface (handles concurrent access via locks)
  ├─ servidor_red.py   → HTTP communication + device discovery
  └─ ws_server.py      → WebSocket push notifications
```

### Key Module Purposes

| File | Purpose | Lines | Critical? |
|------|---------|-------|-----------|
| [app_emisora.py](../app_emisora.py) | Worker ticket submission UI | ~2000 | ✓ Core |
| [app_receptora.py](../app_receptora.py) | IT admin dashboard | ~3000 | ✓ Core |
| [data_access.py](../data_access.py) | SQLite data layer | ~1000+ | ✓ Core |
| [servidor_red.py](../servidor_red.py) | HTTP server + device discovery | ~1500 | ✓ Core |
| [ws_server.py](../ws_server.py) | WebSocket real-time sync | ~500 | ✓ Core |
| [notificaciones_windows.py](../notificaciones_windows.py) | Windows toast notifications | ~300 | ◐ Support |
| [instalador.py](../instalador.py) | Graphical installer | ~2000 | ◐ Support |
| [actualizador_github.py](../actualizador_github.py) | Auto-update from GitHub | ~400 | ◐ Support |
| [init_database.py](../init_database.py) | Database initialization utility | ~200 | ◐ Utility |

**Legacy/Cleanup**: `actualizar_v3.2.py`, `actualizar_v3.3.py`, `app_emisora_backup.py` can be removed.

## Database Schema

### 4 Core Tables

1. **tickets** (15 columns)
   - `ID_TICKET` (PK), `TURNO` (A-001, A-002...),  `USUARIO_AD`, `HOSTNAME`, `MAC_ADDRESS`
   - `CATEGORIA`, `PRIORIDAD`, `DESCRIPCION`, `ESTADO` (Abierto/En Cola/En Proceso/Cerrado)
   - `TECNICO_ASIGNADO`, `NOTAS_RESOLUCION`, `HISTORIAL` (JSON), `FECHA_APERTURA`, `FECHA_CIERRE`

2. **tecnicos** (9 columns)
   - `ID_TECNICO` (PK), `NOMBRE`, `ESTADO`, `ESPECIALIDAD`
   - `TICKETS_ATENDIDOS`, `TICKET_ACTUAL`, `ULTIMA_ACTIVIDAD`, `TELEFONO`, `EMAIL`

3. **equipos** (23 columns - network inventory)
   - MAC address-centric with specs: OS, CPU, RAM, disk, purchase date, warranty, status

4. **inventario_red** (9 columns - network discovery cache)
   - IP address, MAC, hostname, network status, ping history, IP change tracking

### Database Initialization

- **Auto**: First run of `app_receptora.py` creates `tickets.db` in app root
- **Manual**: `python init_database.py` forces creation/validation
- **Reset**: `python init_database.py --reset` (deletes all data)
- **Location**: `<app_root>/tickets.db` (+ `.db-wal`, `.db-shm` for Write-Ahead Logging)

### Initial Data

Default technicians from [init_database.py](../init_database.py):
- `TEC001` - Carlos Rodriguez (Hardware/Red)
- `TEC002` - Maria Garcia (Software/Accesos)
- `TEC003` - Luis Hernandez (Redes/Seguridad)

## Configuration & Files

### Configuration Files

| File | Format | Purpose | Default |
|------|--------|---------|---------|
| [servidor_config.txt](../servidor_config.txt) | `IP:PORT` | Network address (e.g., `192.168.1.112:5555`) | Auto-detect, fallback: `127.0.0.1:5555` |
| [version.json](../version.json) | JSON | Current version + changelog | `{ "version": "5.0.0", ... }` |
| [version.txt](../version.txt) | Plain text | Version number | `5.0.0` |
| [install_info.json](../install_info.json) | JSON | Installation metadata | Auto-generated by installer |
| [solicitudes_enlace.json](../solicitudes_enlace.json) | JSON array | Technician approval queue | `[]` |
| [equipos_aprobados.json](../equipos_aprobados.json) | JSON array | Approved equipment registry | `[]` |

### Programmatic Configuration

Hardcoded constants in [data_access.py](../data_access.py#L1-L30):

```python
CATEGORIAS_DISPONIBLES = ["Red", "Hardware", "Software", "Accesos", "Impresoras", "Email", "Otros"]
ESTADOS_TICKET       = ["Abierto", "En Cola", "En Proceso", "En Espera", "Cerrado", "Cancelado"]
PRIORIDADES          = ["Crítica", "Alta", "Media", "Baja"]
PUERTO_HTTP          = 5555
PUERTO_WEBSOCKET     = 5556
HEARTBEAT_INTERVAL   = 30  # seconds
```

## Common Development Tasks

### Creating a New Technician

```python
# Use data_access.py interface
# In Python REPL or script:
from data_access import DatabaseTickets

db = DatabaseTickets()
db.agregar_tecnico("TEC004", "Juan Perez", "Hardware/Red", "ext.104", "juan@company.com")
```

### Debugging Database Issues

Common symptoms and solutions:

| Issue | Cause | Fix |
|-------|-------|-----|
| "DATABASE locked" | Multiple instances accessing DB simultaneously | Close all instances, restart |
| DB won't initialize | File permissions or disk space | Check folder permissions, free disk space |
| Data disappeared | Database reset or manual deletion | Restore from backup if available |
| WebSocket connection fails | Network/port issue | Check firewall rules for ports 5555/5556 |

**Troubleshooting guide**: See [SOLUCIONAR_DATABASE_ERROR.md](../SOLUCIONAR_DATABASE_ERROR.md)

### PowerShell Database Reset

```powershell
# Safe database reset (closes app first, then cleans up locking files)
$AppPath = "C:\path\to\app"
Stop-Process -Name "app_receptora" -ErrorAction SilentlyContinue
Stop-Process -Name "app_emisora" -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

Remove-Item "$AppPath\tickets.db" -ErrorAction SilentlyContinue
Remove-Item "$AppPath\tickets.db-wal" -ErrorAction SilentlyContinue
Remove-Item "$AppPath\tickets.db-shm" -ErrorAction SilentlyContinue

Write-Host "Database cleaned. App will recreate on next run."
```

### Building Executables

```bash
# Ensure PyInstaller is installed
pip install pyinstaller

# Build main installer
pyinstaller Instalador_Tickets.spec
# Output: dist/Instalador_Tickets.exe

# Build app executable
pyinstaller SoporteTecnico_Emisora.spec
# Output: dist/app_emisora.exe
```

## Development Patterns & Conventions

### Naming Conventions

| Pattern | Purpose | Examples |
|---------|---------|----------|
| `app_*.py` | Main application modules | app_emisora.py, app_receptora.py |
| `servidor_*.py` | Server/network layer | servidor_red.py |
| `ws_*.py` | WebSocket functionality | ws_server.py |
| `data_*.py` | Data access layer | data_access.py |
| `*_database*.py` | Database utilities | init_database.py |
| `notificaciones_*.py` | Notification system | notificaciones_windows.py |
| `actualizador_*.py` | Update system | actualizador_github.py |

### Code Organization

- **Data layer** (`data_access.py`): All database operations, thread-safe locks for concurrent access
- **Network layer** (`servidor_red.py`, `ws_server.py`): HTTP and WebSocket communication
- **UI layer** (`app_emisora.py`, `app_receptora.py`): Flet components and user interaction
- **Utilities** (`notificaciones_windows.py`, `instalador.py`): Support functionality

### Common Patterns

**Database access** (synchronized):
```python
from data_access import DatabaseTickets
db = DatabaseTickets()
ticket = db.obtener_ticket("ID_001")
db.actualizar_estado_ticket("ID_001", "En Proceso")
```

**Real-time updates** (WebSocket):
Handled automatically by `ws_server.py` — push notifications update both UI and database.

**Configuration loading** (server_config.txt):
```python
# Auto-detected from servidor_config.txt or environment
IP_ADDRESS = "192.168.1.X"
PUERTO = 5555
```

## Known Limitations & Workarounds

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| **LAN-only** (no internet ops) | Cannot use across WAN | Deploy VPN or local network only |
| **Windows-only** notifications | No Linux/Mac toast notifications | Flet UI still works, notifications fail gracefully |
| **No user authentication** | Security risk in untrusted networks | Use firewalled/closed networks only |
| **Single UPDATE check on startup** | Auto-update needs internet connectivity | Manual update via .exe replacement if offline |
| **SQLite WAL overhead** | 2-3x larger disk space during operation | Acceptable for small deployments |
| **Max initial technicians** | Only 3 loaded at startup | Add more via `agregar_tecnico()` method |

## Update Mechanism

**GitHub Repository**: [github.com/GoodIsaac18/tickets](https://github.com/GoodIsaac18/tickets) (main branch)

**Updatable files** (9 core components):
- `app_emisora.py`, `app_receptora.py`, `data_access.py`
- `servidor_red.py`, `servicio_notificaciones.py`, `notificaciones_windows.py`
- `instalador.py`, `actualizador_github.py`, `version.json`

**Update flow**: Auto-update checker compares local `version.json` with GitHub. If newer available, downloads files, verifies checksums, backs up old versions, and restarts app.

## File Inventory

### Core Application Files
- [app_emisora.py](../app_emisora.py) — Worker ticket submission application
- [app_receptora.py](../app_receptora.py) — IT admin management panel
- [data_access.py](../data_access.py) — SQLite abstraction layer
- [servidor_red.py](../servidor_red.py) — HTTP server for LAN communication
- [ws_server.py](../ws_server.py) — WebSocket server for real-time sync
- [init_database.py](../init_database.py) — Database initialization and reset utility

### Support Files
- [notificaciones_windows.py](../notificaciones_windows.py) — Windows toast notifications
- [servicio_notificaciones.py](../servicio_notificaciones.py) — Background notification service
- [instalador.py](../instalador.py) — Graphical installer (Flet-based, includes repair/update options)
- [actualizador_github.py](../actualizador_github.py) — Auto-update retrieval from GitHub

### Configuration & Data
- [requirements.txt](../requirements.txt) — Python dependencies (Flet, pandas, openpyxl, websockets, winotify, getmac)
- [version.json](../version.json) — Current version and changelog (source of truth for auto-update)
- [version.txt](../version.txt) — Version string
- [servidor_config.txt](../servidor_config.txt) — Server IP:PORT (auto-detect fallback: 127.0.0.1:5555)
- [install_info.json](../install_info.json) — Installation metadata
- [solicitudes_enlace.json](../solicitudes_enlace.json) — Pending technician link requests
- [equipos_aprobados.json](../equipos_aprobados.json) — Approved equipment registry
- [LICENSE](../LICENSE) — Project license
- [README.md](../README.md) — Full documentation

### Launchers & Builders
- [SISTEMA_TICKETS.bat](../SISTEMA_TICKETS.bat) — Main entry point for installation
- [ejecutar_emisora.bat](../ejecutar_emisora.bat) — Worker app launcher (visible console)
- [ejecutar_receptora.bat](../ejecutar_receptora.bat) — IT panel launcher (visible console)
- [launcher_emisora.vbs](../launcher_emisora.vbs) — Silent worker app launcher
- [launcher_receptora.vbs](../launcher_receptora.vbs) — Silent IT panel launcher
- [compilar_instalador.bat](../compilar_instalador.bat) — Build script for .exe packages
- [Instalador_Tickets.spec](../Instalador_Tickets.spec) — PyInstaller config (installer)
- [SoporteTecnico_Emisora.spec](../SoporteTecnico_Emisora.spec) — PyInstaller config (app)

### Legacy/Deprecated Files (Can Remove)
- `actualizar_v3.2.py`, `actualizar_v3.3.py` — Old update scripts
- `app_emisora_backup.py` — Backup copy
- `generar_iconos.py` — Icon generation (one-time use)

### Resources
- [icons/](../icons/) — Application icons (emisora.ico, receptora.ico, .png variants)
- [python_embed/](../python_embed/) — Embedded Python 3.11.9 runtime with pre-installed dependencies

## AI Agent Development Tips

1. **Always start with `app_receptora.py`** — It initializes the database and starts servers. Without it running, `app_emisora.py` cannot connect.

2. **Database locks are normal** — WAL mode is intentional. If you see "DATABASE locked", restart the affected process.

3. **Test network communication** — Use `servidor_config.txt` to verify IP:PORT settings. Default localhost is `127.0.0.1:5555`.

4. **WebSocket heartbeat** — Automatic 30-second heartbeat keeps connections alive. Don't modify unless necessary.

5. **Thread safety** — `data_access.py` uses locks. Avoid direct SQLite calls — always use the provided abstraction layer.

6. **Version updates** — When modifying code, remember to update `version.json` and `version.txt` for auto-update compatibility.

7. **Flet UI debugging** — Flet-based apps run a local HTTP server for UI rendering. Check for port conflicts on 5555/5556.

8. **Embedded Python** — The `python_embed/` folder is self-contained. Don't assume system Python will have all dependencies.

## References

- **Full Documentation**: [README.md](../README.md)
- **Troubleshooting**: [SOLUCIONAR_DATABASE_ERROR.md](../SOLUCIONAR_DATABASE_ERROR.md)
- **GitHub Repository**: [github.com/GoodIsaac18/tickets](https://github.com/GoodIsaac18/tickets)
- **Technology Links**: 
  - [Flet Documentation](https://flet.dev) (UI framework)
  - [SQLite Documentation](https://sqlite.org) (database)
  - [websockets Library](https://websockets.readthedocs.io) (real-time sync)
  - [pandas Documentation](https://pandas.pydata.org) (data processing)
