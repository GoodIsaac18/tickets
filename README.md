# 🎫 Sistema de Gestión de Tickets IT

Sistema completo de dos aplicaciones de escritorio desarrolladas en Python con Flet para la gestión del ciclo de vida de tickets de soporte técnico. Las aplicaciones se comunican por red local (LAN) sin necesidad de internet.

## 📋 Estructura del Proyecto

```
tickets/
├── app_emisora.py           # Aplicación para trabajadores (crear tickets)
├── app_receptora.py         # Panel IT (gestión, técnicos, reportes)
├── data_access.py           # Módulo de acceso a datos (Excel como DB)
├── servidor_red.py          # Servidor HTTP para comunicación LAN
├── notificaciones_windows.py # Sistema de notificaciones Windows
├── servicio_notificaciones.py # Servicio de notificaciones
├── instalador.py            # Instalador interactivo de consola
├── INSTALAR_SISTEMA.bat     # Ejecutar para instalar
├── DESINSTALAR.bat          # Desinstalador
├── ejecutar_emisora.bat     # Lanzador App Trabajadores
├── ejecutar_receptora.bat   # Lanzador Panel IT
├── launcher_emisora.vbs     # Launcher silencioso Emisora
├── launcher_receptora.vbs   # Launcher silencioso Receptora
├── servidor_config.txt      # Configuración del servidor
├── tickets_db.xlsx          # Base de datos Excel (se crea automáticamente)
├── icons/                   # Iconos de las aplicaciones
│   ├── emisora.ico
│   ├── emisora.png
│   ├── receptora.ico
│   └── receptora.png
└── python_embed/            # Python embebido (se descarga automáticamente)
```

## 🚀 Instalación

### Opción 1: Instalador Automático (Recomendado)

1. **Ejecutar `INSTALAR_SISTEMA.bat`** como administrador
2. El instalador te permite elegir:
   - 🎫 **Emisora**: Para equipos de trabajadores
   - 🖥️ **Receptora**: Para el equipo del técnico IT
3. Opciones configurables:
   - Crear acceso directo en Escritorio
   - Crear acceso en Menú Inicio
   - Iniciar con Windows
   - Configurar Firewall automáticamente

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

## 💻 Aplicaciones

### 🎫 App Emisora (Para Trabajadores)

Interfaz moderna e intuitiva para crear tickets de soporte.

**Características:**
- ✅ Captura automática de: Usuario AD, Hostname, MAC Address
- ✅ Formulario de ticket con categorías predefinidas
- ✅ Sistema de turnos (como banco)
- ✅ Panel de ticket activo con estado en tiempo real
- ✅ **Configuración de Conexión** (nuevo):
  - Detección automática del servidor en la red
  - Configuración manual de IP y puerto
  - Prueba de conexión
- ✅ Notificaciones de estado del ticket
- ✅ Opciones: Recordar ticket, Cancelar ticket

**Acceso a Configuración:** Clic en el icono ⚙️ en la esquina superior derecha

### 🖥️ App Receptora (Panel IT)

Panel completo de administración para técnicos de soporte.

**Módulos disponibles:**

1. **📊 Dashboard**
   - Estadísticas en tiempo real
   - Tickets abiertos, en proceso, cerrados
   - Equipos conectados en la red

2. **🎫 Tickets**
   - Lista completa de tickets con filtros
   - Asignar técnico, cambiar estado
   - Notas de resolución
   - Historial completo

3. **👥 Técnicos**
   - Gestión de técnicos IT
   - Estado: Disponible/Ocupado
   - Especialización y contacto

4. **🔗 Equipos**
   - Solicitudes de enlace pendientes
   - Aprobar/Rechazar equipos
   - Revocar acceso
   - Ver equipos conectados en tiempo real

5. **📈 Reportes** (nuevo):
   - **Resumen General**: KPIs principales, métricas del día/semana/mes
   - **Análisis de Tickets**: Por categoría, prioridad, tiempo de resolución
   - **Rendimiento de Técnicos**: Tickets por técnico, tiempo promedio
   - **Tendencias**: Gráficos de evolución semanal
   - **Análisis de Equipos**: Equipos más problemáticos
   - **Exportar a Excel**: Descarga reportes completos

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

## 📊 Base de Datos (Excel)

El archivo `tickets_db.xlsx` contiene:

### Hoja: TICKETS
| Campo | Descripción |
|-------|-------------|
| ID_TICKET | Identificador único (UUID) |
| TURNO | Número de turno (ej: A-001) |
| FECHA_APERTURA | Fecha y hora de creación |
| USUARIO_AD | Usuario de Active Directory |
| HOSTNAME | Nombre del equipo |
| MAC_ADDRESS | Dirección MAC |
| CATEGORIA | Hardware, Software, Red, etc. |
| PRIORIDAD | Baja, Media, Alta, Urgente |
| DESCRIPCION | Descripción del problema |
| ESTADO | Abierto, En Cola, En Proceso, etc. |
| TECNICO_ASIGNADO | Técnico responsable |
| NOTAS_RESOLUCION | Notas de cierre |
| FECHA_CIERRE | Fecha de resolución |

### Hoja: TECNICOS
| Campo | Descripción |
|-------|-------------|
| ID_TECNICO | Identificador único |
| NOMBRE | Nombre completo |
| EMAIL | Correo electrónico |
| TELEFONO | Teléfono de contacto |
| ESPECIALIDAD | Área de especialización |
| ESTADO | Disponible/Ocupado |

## 🔧 Características Técnicas

- **Framework UI**: Flet (Flutter para Python)
- **Base de datos**: Excel con openpyxl
- **Servidor**: HTTP con sockets nativos
- **Plataforma**: Windows (con Python embebido)
- **Iconos**: Personalizados para cada aplicación
- **Notificaciones**: Windows Toast Notifications

## 📦 Dependencias

```
flet>=0.81.0
pandas>=2.0.0
openpyxl>=3.1.0
getmac>=0.9.0
winotify>=1.1.0
pillow>=10.0.0
```

## 🎨 Diseño

### App Emisora (Modo Claro)
- Gradiente azul-violeta en header
- Interfaz limpia y minimalista
- Icono verde con ticket

### App Receptora (Modo Oscuro)
- Panel lateral con navegación
- Cards con información
- Icono azul con monitor

## 📝 Versión Actual

**Commit:** `e13a2e9`
**Fecha:** Marzo 2026

**Características incluidas:**
- ✅ Sistema de tickets completo
- ✅ Comunicación LAN sin internet
- ✅ Sistema de enlace de equipos
- ✅ Dashboard con estadísticas
- ✅ Gestión de técnicos
- ✅ Sistema de reportes profesional
- ✅ Exportación a Excel
- ✅ Configuración de conexión en Emisora
- ✅ Iconos personalizados
- ✅ Instalador profesional
- ✅ Ejecución en segundo plano

---
© 2026 - Departamento de Tecnología de la Información
