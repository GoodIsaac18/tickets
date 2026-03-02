# 🎫 Sistema de Gestión de Tickets IT

Sistema de dos aplicaciones de escritorio desarrolladas en Python con Flet para la gestión del ciclo de vida de tickets de soporte técnico, vinculando cada ticket a la dirección MAC del equipo y al usuario de Active Directory.

## 📋 Estructura del Proyecto

```
tickets/
├── data_access.py         # Módulo de acceso a datos (Excel como DB)
├── app_emisora.py         # Aplicación para trabajadores (crear tickets)
├── app_receptora.py       # Panel IT (gestión, inventario, dashboard)
├── requirements.txt       # Dependencias del proyecto
├── README.md              # Este archivo
├── tickets_db.xlsx        # Base de datos Excel (se crea automáticamente)
├── instalar.bat           # Instalador automático (EJECUTAR PRIMERO)
├── ejecutar_emisora.bat   # Lanzador App Trabajadores
└── ejecutar_receptora.bat # Lanzador Panel IT
```

## 🚀 Instalación Rápida (Recomendada)

### Opción 1: Instalador Automático (Windows)

1. **Ejecutar `instalar.bat`** (doble clic)
   - Descarga Python 3.11 embebido automáticamente
   - Configura pip e instala todas las dependencias
   - No requiere Python instalado previamente

2. **Ejecutar la aplicación:**
   - `ejecutar_emisora.bat` → Para trabajadores
   - `ejecutar_receptora.bat` → Para técnicos IT

### Opción 2: Instalación Manual

1. **Clonar o descargar el proyecto**

2. **Crear entorno virtual (recomendado)**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   source venv/bin/activate  # macOS/Linux
   ```

3. **Instalar dependencias**
   ```bash
   pip install -r requirements.txt
   ```

## 💻 Uso

### App Emisora (Para Trabajadores)
```bash
python app_emisora.py
```
- Ventana de 450x650px con diseño corporativo azul/gris
- Captura automática de: Usuario AD, Hostname, Dirección MAC
- Formulario para seleccionar categoría y describir el problema
- Validación de campos y animación de carga al enviar

### App Receptora (Panel IT)
```bash
python app_receptora.py
```
- Ventana maximizada con modo oscuro
- Navegación por barra lateral (NavigationRail)
- **Módulo Gestión**: DataTable interactivo con filtros
- **Módulo Inventario**: Top 5 equipos problemáticos por MAC
- **Módulo Dashboard**: Gráficos de categorías, carga semanal y KPIs

## 📊 Estructura de la Base de Datos

El archivo Excel `tickets_db.xlsx` contiene las siguientes columnas:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| ID_TICKET | String/UUID | Identificador único |
| FECHA_APERTURA | Datetime | Fecha de creación |
| USUARIO_AD | String | Usuario de Active Directory |
| HOSTNAME | String | Nombre de red del equipo |
| MAC_ADDRESS | String | Dirección física del hardware |
| CATEGORIA | Enum | Red, Hardware, Software, Accesos, Otros |
| DESCRIPCION | Text | Descripción del problema |
| ESTADO | Enum | Abierto, En Proceso, Cerrado |
| TECNICO_ASIGNADO | String | Técnico responsable |
| NOTAS_RESOLUCION | Text | Notas de resolución |
| FECHA_CIERRE | Datetime | Fecha de cierre |

## 🔧 Características Técnicas

### App Emisora
- ✅ Captura silenciosa de MAC usando `getmac` (Windows/macOS compatible)
- ✅ Validación de campos vacíos con AlertDialog
- ✅ Animación de carga (ProgressRing) al enviar
- ✅ Manejo de PermissionError con 3 reintentos si el Excel está bloqueado

### App Receptora
- ✅ Filtros dinámicos por Estado y búsqueda por Usuario/MAC
- ✅ Panel lateral para editar tickets y cambiar estado
- ✅ Groupby por MAC para identificar equipos problemáticos
- ✅ Gráfico de pastel (categorías) y barras (carga semanal)
- ✅ KPIs: Tiempo promedio de cierre, Tickets abiertos hoy

## 📦 Dependencias

- **flet** >= 0.21.0 - Framework de UI moderna
- **pandas** >= 2.0.0 - Manejo de datos
- **openpyxl** >= 3.1.0 - Motor Excel
- **getmac** >= 0.9.0 - Obtención de MAC Address

## 🎨 Paleta de Colores

### App Emisora (Modo Claro)
- Primario: `#1565C0` (Azul corporativo)
- Fondo: `#F5F5F5` (Gris claro)

### App Receptora (Modo Oscuro)
- Fondo: `#121212`
- Superficie: `#1E1E1E`
- Primario: `#BB86FC` (Púrpura)
- Secundario: `#03DAC6` (Cyan)

## 📝 Licencia

Este proyecto es de uso interno para el Departamento de TI.

---
© 2024 - Departamento de Tecnología de la Información
