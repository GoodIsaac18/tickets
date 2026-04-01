#  GUÍA DE SOLUCIÓN DE PROBLEMAS  DATABASE ERROR (SQLite)

##  El error "DATABASE" significa que hay un problema al acceder a 	ickets.db

Desde **v5.0.0** la base de datos es SQLite (un único archivo 	ickets.db).
Ya **no** se usan archivos Excel (	ickets_db.xlsx, 	ecnicos_db.xlsx, equipos_db.xlsx).

---

##  Causas Comunes

1. **	ickets.db bloqueado**  otra instancia de la app está usando el archivo
2. **Permisos de escritura insuficientes** en la carpeta de instalación
3. **Primera ejecución**  la DB aún no se creó (debe crearse automáticamente)
4. **Archivo corrupto**  poco probable, SQLite tiene journaling WAL

---

##  SOLUCIONES (en orden de probabilidad)

### **Solución 1: Reinicia la Aplicación (60% de efectividad)**

```
1. Cierra completamente la aplicación
2. Espera 2-3 segundos
3. Ejecuta nuevamente
```

SQLite libera el archivo cuando la app cierra. Si aún falla, continúa.

---

### **Solución 2: Verificar si 	ickets.db existe**

`powershell
\ = "c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets"
Get-ChildItem \ -Filter "tickets.db" | Select-Object Name, Length, LastWriteTime
`

- **Si el archivo existe**  puede estar corrupto o bloqueado  ir a Solución 3
- **Si no existe**  se creará automáticamente la próxima vez que corra la app

---

### **Solución 3: Recrear la base de datos manualmente**

Solo si el archivo está corrupto (cierra la app antes):

`powershell
cd "c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets"
# Borrar DB corrupta (los datos se perderán)
Remove-Item tickets.db -ErrorAction SilentlyContinue
Remove-Item tickets.db-wal -ErrorAction SilentlyContinue
Remove-Item tickets.db-shm -ErrorAction SilentlyContinue
# La próxima vez que arranques app_receptora.py, la DB se recreará sola
`

---

### **Solución 4: Verificar permisos de carpeta**

`powershell
# En PowerShell como Administrador:
icacls "c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets" /grant Everyone:F
`

---

##  CHECKLIST DE DIAGNÓSTICO

`powershell
\ = "c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets"

# Verificar archivo SQLite
Write-Host " Base de datos:"
Get-ChildItem \ -Filter "tickets.db*" | Select-Object Name, Length

# Verificar permisos
Write-Host "
 Permisos:"
Get-Acl \ | Format-List

# Verificar Python
Write-Host "
 Python disponible:"
& "\\python_embed\python.exe" --version

# Verificar sqlite3 (siempre disponible en Python 3.x)
Write-Host "
 SQLite disponible:"
& "\\python_embed\python.exe" -c "import sqlite3; print('SQLite', sqlite3.sqlite_version, 'OK')"
`

---

##  Si Ninguna Solución Funciona

1. **Screenshot del error**  toma foto del mensaje exacto
2. **Revisa los logs** en PowerShell:
   `powershell
   cd "c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets"
   .\python_embed\python.exe app_receptora.py 2>&1 | Tee-Object error_log.txt
   `
3. Verifica que haya espacio en disco suficiente (mínimo 100 MB libres)

---

##  INFORMACIÓN TÉCNICA

**Base de datos:** 	ickets.db (SQLite con WAL mode)

| Tabla | Contenido |
|-------|-----------|
| 	ickets | Todos los tickets de soporte |
| 	ecnicos | Datos de los técnicos IT |
| equipos | Inventario de equipos |
| red | Estado de equipos en red |
| counters | Contador atómico de turnos |

**Archivos WAL** (normales, no son errores):
- 	ickets.db-wal  Write-Ahead Log (se fusiona automáticamente al cerrar)
- 	ickets.db-shm  Memoria compartida WAL

**Requisitos:**
- Python 3.11+ (embebido en python_embed/)
- sqlite3 ya incluido  cero instalación adicional
- Permisos de escritura en la carpeta de la aplicación
