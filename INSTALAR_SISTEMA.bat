@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Instalador - Sistema de Tickets IT

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%python_embed\python.exe"

:: Si Python ya esta instalado, ejecutar el instalador directamente
if exist "%PYTHON_EXE%" (
    cd /d "%SCRIPT_DIR%"
    "%PYTHON_EXE%" "%SCRIPT_DIR%instalador.py"
    exit /b 0
)

:: Si no hay Python, necesitamos descargarlo primero con PowerShell
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║           INSTALADOR - SISTEMA DE TICKETS IT                     ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo Preparando instalador... Descargando Python embebido...
echo.

set "PYTHON_DIR=%SCRIPT_DIR%python_embed"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_ZIP=python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_ZIP%"

:: Crear directorio
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

:: Descargar Python usando PowerShell
echo [1/4] Descargando Python %PYTHON_VERSION%...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%SCRIPT_DIR%%PYTHON_ZIP%'}" 2>nul

if not exist "%SCRIPT_DIR%%PYTHON_ZIP%" (
    echo [ERROR] No se pudo descargar Python.
    echo         Verifique su conexion a internet.
    pause
    exit /b 1
)

echo [2/4] Extrayendo Python...
powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

:: Eliminar zip
del "%SCRIPT_DIR%%PYTHON_ZIP%" 2>nul

echo [3/4] Configurando Python...
:: Crear sitecustomize.py
(
    echo import site
    echo site.main^(^)
) > "%PYTHON_DIR%\sitecustomize.py"

:: Modificar python311._pth
(
    echo python311.zip
    echo .
    echo ..
    echo Lib
    echo Lib\site-packages
    echo import site
) > "%PYTHON_DIR%\python311._pth"

:: Crear directorios necesarios
if not exist "%PYTHON_DIR%\Lib" mkdir "%PYTHON_DIR%\Lib"
if not exist "%PYTHON_DIR%\Lib\site-packages" mkdir "%PYTHON_DIR%\Lib\site-packages"
if not exist "%PYTHON_DIR%\Scripts" mkdir "%PYTHON_DIR%\Scripts"

:: Descargar e instalar pip
echo [4/4] Instalando pip...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'}"
"%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location >nul 2>&1

echo.
echo Python instalado. Iniciando instalador grafico...
echo.

:: Ejecutar el instalador de Python
cd /d "%SCRIPT_DIR%"
"%PYTHON_EXE%" "%SCRIPT_DIR%instalador.py"

exit /b 0
