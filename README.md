# 🎫 Sistema de Gestión de Tickets IT — v4.0.0

Sistema completo de dos aplicaciones de escritorio desarrolladas en Python con **Flet 0.81** para la gestión del ciclo de vida de tickets de soporte técnico. Las aplicaciones se comunican por red local (LAN) sin necesidad de internet, e incluyen un **instalador profesional** con actualización automática desde GitHub.

> **Nota:** Versión compilada disponible en `dist/Instalador_Tickets_4.0.0/` (174 MB) — No requiere Python instalado.

---

## 📋 Estructura del Proyecto

```
tickets/
├── app_emisora.py              # Aplicación para trabajadores (crear tickets)
├── app_receptora.py            # Panel IT (gestión, técnicos, reportes)
├── data_access.py              # Módulo de acceso a datos (SQLite)
├── servidor_red.py             # Servidor HTTP para comunicación LAN (puerto 5555)
├── ws_server.py                # Servidor WebSocket en tiempo real (puerto 5556)
├── notificaciones_windows.py   # Sistema de notificaciones Windows
├── servicio_notificaciones.py  # Servicio de notificaciones en segundo plano
├── instalador.py               # Instalador gráfico profesional (Flet UI)
├── actualizador_github.py      # Sistema de actualizaciones automáticas
├── requirements.txt            # Dependencias del proyecto
├── ejecutar_emisora.bat        # Lanzador App Trabajadores
├── ejecutar_receptora.bat      # Lanzador Panel IT
├── launcher_emisora.vbs        # Launcher silencioso Emisora (con rutas dinámicas)
├── launcher_receptora.vbs      # Launcher silencioso Receptora (con rutas dinámicas)
├── servidor_config.txt         # Configuración del servidor (IP:Puerto)
├── equipos_aprobados.json      # Equipos aprobados por el técnico
├── solicitudes_enlace.json     # Solicitudes de enlace pendientes
├── tickets.db                  # Base de datos SQLite (se crea automáticamente)
├── icons/                      # Iconos de las aplicaciones
│   ├── emisora.ico / .png
│   └── receptora.ico / .png
├── dist/                       # Binarios compilados (PyInstaller --onedir)
│   └── Instalador_Tickets_4.0.0/
│       └── Instalador_Tickets_4.0.0.exe
├── python_embed/               # Python 3.11.9 embebido
└── backups/                    # Backups automáticos de actualizaciones
```

---

## 🚀 Instalación

### Opción 1: Instalador Compilado (Recomendado) — v4.0.0+

El instalador precompilado **no requiere Python instalado**:

```bash
# Ejecutar directamente
.\dist\Instalador_Tickets_4.0.0\Instalador_Tickets_4.0.0.exe
```

**Tamaño:** 174 MB (incluye todas las dependencias: Flet, pandas, openpyxl, etc.)

El instalador presenta un wizard con las siguientes opciones:
- 🎫 **Emisora**: Para equipos de trabajadores
- 🖥️ **Receptora**: Para el equipo del técnico IT

Opciones configurables:
- Crear acceso directo en Escritorio (con rutas dinámicas)
- Crear acceso en Menú Inicio
- Iniciar con Windows (autoarranque)
- Configurar Firewall automáticamente

El instalador detecta instalaciones previas y ofrece:
- **Actualizar** → Conecta a GitHub y descarga parches automáticamente
- **Desinstalar** → Limpia accesos directos, registros y configuraciones
- **Reinstalar** → Instalación limpia conservando datos

### Opción 2: Instalador Gráfico desde Fuente

1. Ejecutar **`SISTEMA_TICKETS.bat`** desde el código fuente
2. Igual que Opción 1

### Opción 3: Instalación Manual

```bash
# Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python app_emisora.py    # Trabajadores
python app_receptora.py  # Panel IT
```

---

## 💻 Aplicaciones

### 🎫 App Emisora (Para Trabajadores)

Interfaz moderna e intuitiva para crear tickets de soporte.

**Características:**
- ✅ Captura automática de: Usuario AD, Hostname, MAC Address
- ✅ Formulario de ticket con categorías predefinidas
- ✅ Sistema de turnos tipo banco (A-001, A-002...)
- ✅ Panel de ticket activo con estado en tiempo real
- ✅ Configuración de conexión (detección automática + manual)
- ✅ Notificaciones de cambio de estado del ticket
- ✅ Opciones: Recordar ticket, Cancelar ticket
- ✅ Diálogo de turno con cierre correcto (fix v3.3)
- ✅ Panel de seguimiento visible después de enviar ticket (fix v3.3)

**Acceso a Configuración:** Clic en el icono ⚙️ en la esquina superior derecha

### 🖥️ App Receptora (Panel IT)

Panel completo de administración para técnicos de soporte.

**Módulos disponibles:**

| Módulo | Descripción |
|--------|-------------|
| 📊 **Dashboard** | KPIs en tiempo real, tickets abiertos/proceso/cerrados, equipos conectados |
| 🎫 **Tickets** | Lista con filtros, asignar técnico, cambiar estado, notas, historial |
| 👥 **Técnicos** | Gestión de técnicos, estado, especialización, contacto |
| 🔗 **Equipos** | Solicitudes de enlace, aprobar/rechazar, revocar, equipos online |
| 📈 **Reportes** | Resumen general, análisis por categoría/prioridad, rendimiento, tendencias, exportar a Excel |

---

## 🔄 Sistema de Actualizaciones (v3.3 — Nuevo)

El instalador incluye un sistema completo de actualización automática desde GitHub.

### Flujo de actualización:

```
1. Verificar WiFi conectado (netsh)
2. Verificar acceso a Internet (SSL → github.com:443)
3. Conectar a API de GitHub (commits + version.json)
4. Comparar hashes SHA-256 de archivos locales vs remotos
5. Mostrar changelog con commits recientes
6. Descargar archivos diferentes con backup automático
7. Validar sintaxis Python (.py) antes de escribir
8. Actualizar install_info.json con nueva versión
```

### Módulo: `actualizador_github.py`

| Función | Descripción |
|---------|-------------|
| `verificar_wifi_conectado()` | Detecta conexión WiFi activa via `netsh` |
| `verificar_conexion_internet()` | Prueba SSL a github.com:443 |
| `verificar_conexion_github()` | Valida acceso a la API de GitHub |
| `obtener_commits_recientes()` | Obtiene últimos N commits del repo |
| `obtener_version_remota()` | Lee `version.json` del repositorio |
| `hay_actualizacion_disponible()` | Compara versión local vs remota |
| `obtener_archivos_diferentes()` | Compara SHA-256 local vs remoto |
| `ejecutar_actualizacion()` | Descarga, valida y aplica parches con backup |
| `calcular_hash_archivo()` | SHA-256 de un archivo local |

**Repositorio:** `https://github.com/GoodIsaac18/tickets.git`  
**Branch:** `main`  
**Sin token requerido** — usa la API pública de GitHub con `urllib`

---

## 🌐 Comunicación en Red

El sistema funciona en red local (LAN) sin necesidad de internet:

- **Servidor HTTP** en puerto 5555 (configurable)
- **Descubrimiento automático** de servidor en la red
- **Sistema de enlace** para aprobar equipos
- **Heartbeat** para detectar equipos online/offline
- **Comunicación bidireccional** en tiempo real

### Flujo de conexión:

1. La Receptora inicia el servidor al arrancar
2. La Emisora busca automáticamente el servidor en la red
3. Si no lo encuentra, permite configuración manual
4. Al conectarse, Emisora envía solicitud de enlace
5. El técnico en Receptora aprueba/rechaza el equipo
6. Una vez aprobado, el equipo puede enviar tickets

---

## � Compilación (PyInstaller)

Para compilar una nueva versión del instalador:

```bash
# Limpiar compilaciones anteriores
Remove-Item -Path "dist", "build" -Recurse -Force -ErrorAction SilentlyContinue

# Compilar con todas las dependencias incluidas
.\python_embed\python.exe -m PyInstaller `
  --onedir `
  --windowed `
  --name "Instalador_Tickets_4.0.0" `
  --icon="icons/receptora.ico" `
  --add-data "icons:icons" `
  --collect-all flet `
  --collect-all flet_desktop `
  --hidden-import=flet.controls.material.icons `
  --hidden-import=flet_desktop `
  --hidden-import=pandas `
  --hidden-import=openpyxl `
  instalador.py
```

**Resultado:** `dist/Instalador_Tickets_4.0.0/Instalador_Tickets_4.0.0.exe` (~174 MB)

### Flags importantes:

| Flag | Descripción |
|------|-------------|
| `--onedir` | Directorio con todos los archivos (mejor para actualizaciones) |
| `--windowed` | Sin consola (aplicación de escritorio) |
| `--collect-all flet` | Incluye TODOS los recursos de Flet (assets, fuentes) |
| `--collect-all flet_desktop` | Incluye binarios de Flet Desktop (`app/flet`) |
| `--hidden-import=` | Importaciones dinámicas no detectadas automáticamente |

---

## �📊 Base de Datos (SQLite)

**Archivo:** `tickets.db` (creado automáticamente al primer arranque)

Usa SQLite con WAL mode — incluido en Python estándar, cero instalación adicional.

### Tabla: `tickets`

| Campo | Descripción |
|-------|-------------|
| ID_TICKET | Identificador único (UUID) |
| TURNO | Número de turno (ej: A-001) |
| FECHA_APERTURA | Fecha y hora de creación |
| USUARIO_AD | Usuario de Active Directory |
| HOSTNAME | Nombre del equipo |
| MAC_ADDRESS | Dirección MAC |
| CATEGORIA | Hardware, Software, Red, etc. |
| PRIORIDAD | Baja, Media, Alta, Crítica |
| DESCRIPCION | Descripción del problema |
| ESTADO | Abierto, En Cola, En Proceso, En Espera, Cerrado, Cancelado |
| TECNICO_ASIGNADO | Técnico responsable |
| NOTAS_RESOLUCION | Notas de cierre |
| HISTORIAL | Historial de cambios |
| FECHA_CIERRE | Fecha de resolución |

### Tabla: `tecnicos`

| Campo | Descripción |
|-------|-------------|
| ID_TECNICO | Identificador único |
| NOMBRE | Nombre completo |
| EMAIL | Correo electrónico |
| TELEFONO | Teléfono de contacto |
| ESPECIALIDAD | Área de especialización |
| ESTADO | Disponible / Ocupado / Ausente |

### Tablas adicionales: `equipos`, `red`, `counters`

---

## 🔧 Características Técnicas

| Componente | Tecnología |
|------------|------------|
| **Framework UI** | Flet 0.81 (Flutter para Python) |
| **Base de datos** | SQLite (`sqlite3` stdlib, WAL mode, cero instalación) |
| **Servidor HTTP** | ThreadedHTTPServer nativo (puerto 5555) |
| **Tiempo real** | WebSocket (`websockets>=12.0`, puerto 5556) |
| **Plataforma** | Windows 10/11 con Python 3.11+ embebido |
| **Notificaciones** | Windows Toast Notifications (winotify) |
| **Red** | netsh (WiFi), getmac (MAC), socket (LAN) |

---

## 📦 Dependencias

```
flet>=0.21.0
pandas>=2.0.0
openpyxl>=3.1.0    # requerido solo para exportar reportes a Excel
getmac>=0.9.0
winotify>=1.1.0
websockets>=12.0   # sincronización en tiempo real entre emisora y receptora
# sqlite3 ya viene incluido con Python — sin instalación adicional
```

---

## 🎨 Diseño

### App Emisora (Modo Claro)
- Gradiente azul-violeta en header
- Interfaz limpia y minimalista
- Icono verde con ticket

### App Receptora (Modo Oscuro)
- Panel lateral con navegación
- Cards con información en tiempo real
- Icono azul con monitor

### Instalador (Modo Oscuro)
- UI profesional con wizard paso a paso
- Barra de progreso animada
- Vista de actualizaciones con changelog en vivo

---

## 📝 Historial de Versiones

### v4.0.0 — 1 de Abril 2026 (Actual)
- ✅ **Compilación profesional con PyInstaller** (`--onedir`)
  - Ejecutable independiente: `Instalador_Tickets_4.0.0.exe` (174 MB)
  - Incluye Python 3.11.9 embebido + todas las dependencias
  - No requiere instalación previa de Python
  - Todos los binarios de Flet Desktop incluidos
- ✅ **Rutas dinámicas en VBS launchers** (fix para múltiples Windows locales)
  - `launcher_receptora.vbs` y `launcher_emisora.vbs` actualizados
  - Usan `GetParentFolderName()` en lugar de rutas hardcodeadas
  - Funciona en cualquier camino de instalación
- ✅ **Fix: Flet Icons error** — Agregadas dependencias ocultas (`--hidden-import`)
- ✅ **Limpieza de archivos obsoletos**
  - Eliminados: `actualizar.py`, `actualizar_v3.2.py`, `actualizar_v3.3.py`
  - Eliminados: `app_emisora_backup.py`, `generar_iconos.py`, `instalador_backup.py`
  - Repositorio más limpio y mantenible
- ✅ **Version.json** actualizado a 4.0.0

### v3.3.0 — 5 de Marzo 2026
- ✅ **Sistema de actualización automática desde GitHub**
  - Verificación de WiFi / Internet / GitHub
  - Comparación de archivos por SHA-256
  - Descarga con backup automático
  - Validación de sintaxis Python antes de aplicar
- ✅ **Fix: Botón "Entendido" no cerraba** — `modal=False` + `ft.TextButton` en actions
- ✅ **Fix: Panel de seguimiento invisible** — Ticket guardado en memoria + fallback
- ✅ **Fix: Scroll en vista Actualizar** — `scroll=ft.ScrollMode.AUTO` en Column
- ✅ **Nuevo módulo:** `actualizador_github.py` (~500 líneas)
- ✅ **Nuevo archivo:** `version.json` para control de versiones remoto

### v3.0.0 — Marzo 2026
- ✅ Instalador gráfico profesional con Flet UI
- ✅ Detección de instalación existente
- ✅ Desinstalación completa
- ✅ Sistema de reportes profesional con exportación Excel
- ✅ Animaciones de carga en operaciones de la Receptora
- ✅ Formateo mejorado en base de datos

### v2.0.0 — Febrero 2026
- ✅ Sistema de tickets completo (crear, asignar, resolver, cerrar)
- ✅ Comunicación LAN sin internet
- ✅ Sistema de enlace de equipos
- ✅ Dashboard con estadísticas
- ✅ Gestión de técnicos
- ✅ Notificaciones de Windows

---

## 🐛 Problemas Conocidos y Soluciones

| Problema | Causa | Solución | Estado |
|----------|-------|----------|--------|
| `scroll` en `Container` o `Row` falla | Flet 0.81 solo soporta scroll en `Column` | Mover `scroll=` a parent `Column` | ✅ Resuelto v4.0.0 |
| Flet Icons cargan en error (FileNotFoundError) | Falta incluir binarios de `flet_desktop` | PyInstaller con `--collect-all flet_desktop` | ✅ Resuelto v4.0.0 |
| Launchers VBS fallan en diferentes rutas | Rutas hardcodeadas | Usar `GetParentFolderName()` dinámico | ✅ Resuelto v4.0.0 |
| `modal=True` bloquea clics en Flet 0.81 | Bug de Flet | Usar `modal=False` + `on_dismiss` | ✅ Resuelto v3.3.0 |
| Ticket no aparece después de enviar | Servidor no retorna datos localmente | Guardar en `self.ticket_activo` + fallback | ✅ Resuelto v3.3.0 |

---

## 📄 Licencia

© 2026 — Departamento de Tecnología de la Información
