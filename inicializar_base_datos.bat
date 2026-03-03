@echo off
echo ========================================
echo INICIALIZACIÓN DE BASE DE DATOS
echo ========================================
echo.
echo Ejecutando script de inicialización...
python_embed\python.exe init_database.py

echo.
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ Base de datos inicializada exitosamente!
    echo Presiona cualquier tecla para cerrar...
    pause > nul
) else (
    echo.
    echo ✗ Error durante la inicialización
    echo Revisa los mensajes de error arriba
    pause
)
