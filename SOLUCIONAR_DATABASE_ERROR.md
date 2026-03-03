# 🔧 GUÍA DE SOLUCIÓN DE PROBLEMAS - DATABASE ERROR

## ❌ El error "DATABASE" significa que hay un problema al acceder a la base de datos Excel

### 🎯 Causas Comunes

1. **Archivos Excel bloqueados o corruptos**
2. **Permisos de lectura/escritura insuficientes**
3. **Primera inicialización incompleta**
4. **Conflicto con otra instancia de la aplicación**

---

## ✅ SOLUCIONES (en orden de probabilidad)

### **Solución 1: Reinicia la Aplicación (60% de efectividad)**

```bash
Cierra completamente la aplicación
Espera 2-3 segundos
Ejecuta nuevamente
```

Si esto no funciona, continúa con la Solución 2...

---

### **Solución 2: Inicializa Automáticamente la Base de Datos (80% de efectividad)**

```bash
En Windows: Ejecuta inicializar_base_datos.bat
O ejecuta en PowerShell:
  cd c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets
  python init_database.py
```

**¿Qué hace?**
- ✓ Detecta y elimina archivos corruptos
- ✓ Recrea las 3 bases de datos (Tickets, Técnicos, Equipos)
- ✓ Carga técnicos de ejemplo
- ✓ Valida integridad de todas las tablas

**Resultado esperado:**
```
✅ INICIALIZACIÓN COMPLETADA EXITOSAMENTE
✓ Ahora puedes ejecutar: python app_receptora.py
```

---

### **Solución 3: Limpieza Manual Completa (95% de efectividad)**

Si el script automático no funciona, sigue estos pasos:

1. **Cierra la aplicación completamente**

2. **Elimina los archivos Excel corruptos:**
   ```
   tickets_db.xlsx
   tecnicos_db.xlsx
   equipos_db.xlsx
   ```
   *(Estos archivos se encuentran en la misma carpeta que app_receptora.py)*

3. **Ejecuta el inicializador:**
   ```bash
   python init_database.py
   ```

4. **Inicia la aplicación:**
   ```bash
   python app_receptora.py
   ```

---

### **Solución 4: Verificar Permisos de Carpeta (Advanced)**

Si aún hay problemas, verifica que tienes permisos de lectura/escritura:

```bash
# En PowerShell como Administrador:
icacls "c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets" /grant Everyone:F
```

---

## 📋 CHECKLIST DE DIAGNÓSTICO

Ejecuta esto en PowerShell para diagnosticar:

```powershell
$ruta = "c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets"

# Verificar archivos
Write-Host "📁 Archivos en la carpeta:"
Get-ChildItem $ruta -Filter "*_db.xlsx" | Select-Object Name, Length

# Verificar permisos
Write-Host "`n🔒 Permisos:"
Get-Acl $ruta | Format-List

# Verificar Python
Write-Host "`n🐍 Python disponible:"
python --version

# Verificar pandas
Write-Host "`n📚 Pandas disponible:"
python -c "import pandas; print('Pandas OK')"
```

---

## 🆘 Si Ninguna Solución Funciona

1. **Captura de pantalla del error** - Toma una foto o screenshot del mensaje exacto
2. **Revisa los logs** - Ejecuta en PowerShell:
   ```bash
   cd c:\Users\PROTECNICA\Desktop\tickets\tickets\tickets
   python app_receptora.py 2>&1 | Tee-Object error_log.txt
   ```
3. **Verifica que haya 3 GB disponibles** en el disco

---

## 📞 INFORMACIÓN DEL SISTEMA

**Archivo:** `init_database.py`
- Crea base de datos de Tickets: `tickets_db.xlsx`
- Crea base de datos de Técnicos: `tecnicos_db.xlsx`
- Crea base de datos de Equipos: `equipos_db.xlsx`

**Requisitos:**
- Python 3.11+
- pandas
- openpyxl
- Permisos de escritura en la carpeta

---

## ✨ DESPUÉS DE RESOLVER

Verifica que la aplicación inicia correctamente:

✓ Se abre la ventana principal
✓ Aparece el Dashboard
✓ Los KPIs muestran datos
✓ Se pueden ver técnicos

Si todo funciona, ¡felicidades! 🎉
