@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Instalador - Sistema de Tickets IT

echo.
echo ==============================================
echo   INSTALADOR - SISTEMA DE TICKETS IT
echo ==============================================
echo.

set "INSTALL_DIR=%~dp0"
set "PYTHON_DIR=%INSTALL_DIR%python_embed"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"
set "PIP_EXE=%PYTHON_DIR%\Scripts\pip.exe"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_ZIP=python-3.11.9-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/3.11.9/%PYTHON_ZIP%"

:: Verificar si ya está instalado
if exist "%PYTHON_EXE%" (
    echo [INFO] Python embebido ya esta instalado.
    goto :install_deps
)

echo [1/4] Descargando Python %PYTHON_VERSION% embebido...
echo       Esto puede tardar unos minutos...

:: Crear directorio
if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

:: Descargar Python usando PowerShell
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%INSTALL_DIR%%PYTHON_ZIP%'}" 2>nul

if not exist "%INSTALL_DIR%%PYTHON_ZIP%" (
    echo [ERROR] No se pudo descargar Python. Verifica tu conexion a internet.
    echo         URL: %PYTHON_URL%
    pause
    exit /b 1
)

echo [2/4] Extrayendo Python...
powershell -Command "Expand-Archive -Path '%INSTALL_DIR%%PYTHON_ZIP%' -DestinationPath '%PYTHON_DIR%' -Force"

:: Eliminar archivo zip
del "%INSTALL_DIR%%PYTHON_ZIP%" 2>nul

:: Habilitar pip en Python embebido
echo [3/4] Configurando pip...
(
    echo import site
    echo site.main()
) > "%PYTHON_DIR%\sitecustomize.py"

:: Modificar python311._pth para habilitar site-packages y directorio padre
(
    echo python311.zip
    echo .
    echo ..
    echo Lib
    echo Lib\site-packages
    echo import site
) > "%PYTHON_DIR%\python311._pth"

:: Descargar get-pip.py
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'}"

:: Instalar pip
"%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location

:: Crear directorio Lib\site-packages si no existe
if not exist "%PYTHON_DIR%\Lib" mkdir "%PYTHON_DIR%\Lib"
if not exist "%PYTHON_DIR%\Lib\site-packages" mkdir "%PYTHON_DIR%\Lib\site-packages"

:install_deps
echo [4/4] Instalando dependencias...
"%PYTHON_EXE%" -m pip install --upgrade pip --quiet --no-warn-script-location 2>nul
"%PYTHON_EXE%" -m pip install flet pandas openpyxl getmac --quiet --no-warn-script-location

if errorlevel 1 (
    echo [ADVERTENCIA] Hubo problemas instalando algunas dependencias.
    echo               Intentando instalacion alternativa...
    "%PYTHON_EXE%" -m pip install flet pandas openpyxl getmac --no-warn-script-location
)

echo.
echo ==============================================
echo   INSTALACION COMPLETADA
echo ==============================================
echo.
echo Para ejecutar la aplicacion use:
echo   - ejecutar_emisora.bat (Trabajadores)
echo   - ejecutar_receptora.bat (Tecnicos IT)
echo.
pause
