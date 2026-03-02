@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%python_embed\python.exe"

:: Verificar que Python esta instalado
if not exist "%PYTHON_EXE%" (
    echo ================================================
    echo  ERROR: Python no esta instalado
    echo ================================================
    echo.
    echo Por favor ejecute primero: instalar.bat
    echo.
    pause
    exit /b 1
)

:: Cambiar al directorio del script
cd /d "%SCRIPT_DIR%"

:: Agregar directorio al PYTHONPATH para encontrar modulos locales
set "PYTHONPATH=%SCRIPT_DIR%"

:: Ejecutar la aplicacion (sin start para ver errores si hay)
"%PYTHON_EXE%" app_emisora.py

:: Si hay error, pausar para ver el mensaje
if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion se cerro con errores.
    pause
)

exit /b 0
