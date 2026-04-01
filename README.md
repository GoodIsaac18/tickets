# 🎫 Sistema de Gestión de Tickets IT — v5.0.0

Sistema completo de dos aplicaciones de escritorio desarrolladas en Python con **Flet 0.81** para la gestión del ciclo de vida de tickets de soporte técnico. Las aplicaciones se comunican por red local (LAN) sin necesidad de internet, e incluyen un **instalador profesional** con actualización automática desde GitHub.

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
├── requirements.txt            # Dependencias del proyecto
├── ejecutar_emisora.bat        # Lanzador App Trabajadores
├── ejecutar_receptora.bat      # Lanzador Panel IT
├── launcher_emisora.vbs        # Launcher silencioso Emisora
├── launcher_receptora.vbs      # Launcher silencioso Receptora
├── servidor_config.txt         # Configuración del servidor (IP:Puerto)
├── equipos_aprobados.json      # Equipos aprobados por el técnico
├── solicitudes_enlace.json     # Solicitudes de enlace pendientes
├── tickets.db                  # Base de datos SQLite (se crea automáticamente)
├── icons/                      # Iconos de las aplicaciones
│   ├── emisora.ico / .png
│   └── receptora.ico / .png
├── python_embed/               # Python 3.11.9 embebido
└── backups/                    # Backups automáticos de actualizaciones
```

---

## 🚀 Instalación

### Opción 1: Instalador Gráfico (Recomendado)

1. Ejecutar **`SISTEMA_TICKETS.bat`** o **`Instalador_Tickets_IT.exe`**
2. El instalador presenta un wizard con las siguientes opciones:
   - 🎫 **Emisora**: Para equipos de trabajadores
   - 🖥️ **Receptora**: Para el equipo del técnico IT
3. Opciones configurables:
   - Crear acceso directo en Escritorio
   - Crear acceso en Menú Inicio
   - Iniciar con Windows (autoarranque)
   - Configurar Firewall automáticamente

El instalador detecta instalaciones previas y ofrece:
- **Actualizar** → Conecta a GitHub y descarga parches automáticamente
- **Desinstalar** → Limpia accesos directos, registros y configuraciones
- **Reinstalar** → Instalación limpia conservando datos

### Opción 2: Instalación Manual

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

## 📊 Base de Datos (SQLite)

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

### v5.0.0 — 6 de Marzo 2026 (Actual)
- ✅ **Migración completa a SQLite** — cero instalación adicional
  - `sqlite3` está incluido en Python estándar
  - WAL mode para lecturas concurrentes sin bloqueos
  - Turno atómico con `INSERT ON CONFLICT DO UPDATE`
  - Un solo archivo: `tickets.db`
- ✅ **Servidor WebSocket** (`ws_server.py`) en puerto 5556
  - Emisoras reciben actualización instantánea sin polling
  - Auto-reconexiones con reintentos cada 5 s
  - Fallback HTTP polling cada 30 s
- ✅ Eliminados `tickets_db.xlsx`, `tecnicos_db.xlsx`, `equipos_db.xlsx`
- ✅ `notificaciones_windows.py` actualizado a SQLite
- ✅ `instalador.py` actualizado: crea `tickets.db` en instalación

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
- ✅ Vista "Actualizar" del instalador reescrita con conexión GitHub en vivo

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

| Problema | Causa | Solución |
|----------|-------|----------|
| `modal=True` bloquea clics en Flet 0.81 | Bug de Flet | Usar `modal=False` + `on_dismiss` |
| Ticket no aparece después de enviar | Servidor no retorna datos localmente | Guardar en `self.ticket_activo` + fallback |
| No se puede scrollear en Actualizar | Column sin `scroll` | Agregar `scroll=ft.ScrollMode.AUTO` |
| Error `COLOR_WARNING` no definido | Variable faltante | Definir en paleta de colores |

---

## 📄 Licencia

© 2026 — Departamento de Tecnología de la Información
