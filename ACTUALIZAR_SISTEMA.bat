@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Actualizar Sistema - Tickets IT

set "SCRIPT_DIR=%~dp0"

:: Configuración de GitHub
set "GITHUB_REPO=GoodIsaac18/tickets"
set "GITHUB_RAW=https://raw.githubusercontent.com/%GITHUB_REPO%/main"
set "GITHUB_ZIP=https://github.com/%GITHUB_REPO%/archive/refs/heads/main.zip"

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║         ACTUALIZAR SISTEMA DE TICKETS IT (GITHUB)                ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Repositorio: github.com/%GITHUB_REPO%
echo.

:: Leer versión local
if exist "%SCRIPT_DIR%version.txt" (
    set /p VERSION_LOCAL=<"%SCRIPT_DIR%version.txt"
) else (
    set "VERSION_LOCAL=0.0.0"
)

echo   Verificando version en GitHub...

:: Descargar version.txt desde GitHub
set "TEMP_VERSION=%TEMP%\tickets_version.txt"
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%GITHUB_RAW%/version.txt' -OutFile '%TEMP_VERSION%' -TimeoutSec 15 } catch { Write-Host 'Error de conexion'; exit 1 }}" 2>nul

if not exist "%TEMP_VERSION%" (
    echo.
    echo   [ERROR] No se pudo conectar a GitHub.
    echo           Verifique su conexion a internet.
    echo.
    pause
    exit /b 1
)

set /p VERSION_GITHUB=<"%TEMP_VERSION%"
del "%TEMP_VERSION%" 2>nul

echo.
echo   Version instalada:  !VERSION_LOCAL!
echo   Version en GitHub:  !VERSION_GITHUB!
echo.

if "!VERSION_LOCAL!"=="!VERSION_GITHUB!" (
    echo   [OK] Ya tiene la version mas reciente instalada.
    echo.
    choice /C SN /M "  Desea forzar reinstalacion de archivos [S/N]"
    if !errorlevel!==2 (
        echo   Operacion cancelada.
        pause
        exit /b 0
    )
)

echo.
echo   Descargando actualizacion desde GitHub...
echo.

:: Descargar ZIP del repositorio
set "TEMP_ZIP=%TEMP%\tickets_update.zip"
set "TEMP_EXTRACT=%TEMP%\tickets_extract"

echo   [1/5] Descargando repositorio...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%GITHUB_ZIP%' -OutFile '%TEMP_ZIP%'}" 2>nul

if not exist "%TEMP_ZIP%" (
    echo   [ERROR] No se pudo descargar el repositorio.
    pause
    exit /b 1
)

echo   [2/5] Extrayendo archivos...
if exist "%TEMP_EXTRACT%" rmdir /s /q "%TEMP_EXTRACT%" 2>nul
powershell -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%TEMP_EXTRACT%' -Force" 2>nul

set "SRC_DIR=%TEMP_EXTRACT%\tickets-main"

echo   [3/5] Actualizando archivos Python...
if exist "%SRC_DIR%\app_emisora.py" copy /Y "%SRC_DIR%\app_emisora.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - app_emisora.py
if exist "%SRC_DIR%\app_receptora.py" copy /Y "%SRC_DIR%\app_receptora.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - app_receptora.py
if exist "%SRC_DIR%\data_access.py" copy /Y "%SRC_DIR%\data_access.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - data_access.py
if exist "%SRC_DIR%\instalador.py" copy /Y "%SRC_DIR%\instalador.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - instalador.py
if exist "%SRC_DIR%\servidor_red.py" copy /Y "%SRC_DIR%\servidor_red.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - servidor_red.py
if exist "%SRC_DIR%\servicio_notificaciones.py" copy /Y "%SRC_DIR%\servicio_notificaciones.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - servicio_notificaciones.py
if exist "%SRC_DIR%\notificaciones_windows.py" copy /Y "%SRC_DIR%\notificaciones_windows.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - notificaciones_windows.py
if exist "%SRC_DIR%\init_database.py" copy /Y "%SRC_DIR%\init_database.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - init_database.py
if exist "%SRC_DIR%\generar_iconos.py" copy /Y "%SRC_DIR%\generar_iconos.py" "%SCRIPT_DIR%" >nul 2>&1 && echo         - generar_iconos.py

echo   [4/5] Actualizando scripts y launchers...
if exist "%SRC_DIR%\INSTALAR_SISTEMA.bat" copy /Y "%SRC_DIR%\INSTALAR_SISTEMA.bat" "%SCRIPT_DIR%" >nul 2>&1 && echo         - INSTALAR_SISTEMA.bat
if exist "%SRC_DIR%\ACTUALIZAR_SISTEMA.bat" copy /Y "%SRC_DIR%\ACTUALIZAR_SISTEMA.bat" "%SCRIPT_DIR%" >nul 2>&1 && echo         - ACTUALIZAR_SISTEMA.bat
if exist "%SRC_DIR%\ejecutar_emisora.bat" copy /Y "%SRC_DIR%\ejecutar_emisora.bat" "%SCRIPT_DIR%" >nul 2>&1 && echo         - ejecutar_emisora.bat
if exist "%SRC_DIR%\ejecutar_receptora.bat" copy /Y "%SRC_DIR%\ejecutar_receptora.bat" "%SCRIPT_DIR%" >nul 2>&1 && echo         - ejecutar_receptora.bat
if exist "%SRC_DIR%\ejecutar_emisora_oculto.vbs" copy /Y "%SRC_DIR%\ejecutar_emisora_oculto.vbs" "%SCRIPT_DIR%" >nul 2>&1 && echo         - ejecutar_emisora_oculto.vbs
if exist "%SRC_DIR%\ejecutar_receptora_oculto.vbs" copy /Y "%SRC_DIR%\ejecutar_receptora_oculto.vbs" "%SCRIPT_DIR%" >nul 2>&1 && echo         - ejecutar_receptora_oculto.vbs
if exist "%SRC_DIR%\launcher_emisora.vbs" copy /Y "%SRC_DIR%\launcher_emisora.vbs" "%SCRIPT_DIR%" >nul 2>&1 && echo         - launcher_emisora.vbs
if exist "%SRC_DIR%\launcher_receptora.vbs" copy /Y "%SRC_DIR%\launcher_receptora.vbs" "%SCRIPT_DIR%" >nul 2>&1 && echo         - launcher_receptora.vbs

if exist "%SRC_DIR%\icons\*" (
    echo   [5/5] Actualizando iconos...
    if not exist "%SCRIPT_DIR%icons" mkdir "%SCRIPT_DIR%icons" 2>nul
    xcopy /Y /E /I "%SRC_DIR%\icons" "%SCRIPT_DIR%icons" >nul 2>&1
    echo         - Carpeta icons actualizada
) else (
    echo   [5/5] Sin iconos nuevos.
)

:: Actualizar version.txt
if exist "%SRC_DIR%\version.txt" copy /Y "%SRC_DIR%\version.txt" "%SCRIPT_DIR%" >nul 2>&1

:: Limpiar
echo.
echo   Limpiando archivos temporales...
del "%TEMP_ZIP%" 2>nul
rmdir /s /q "%TEMP_EXTRACT%" 2>nul

set /p VERSION_NUEVA=<"%SCRIPT_DIR%version.txt"

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║            OK ACTUALIZACION COMPLETADA EXITOSAMENTE              ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Version anterior: !VERSION_LOCAL!
echo   Version actual:   !VERSION_NUEVA!
echo.
echo   Reinicie la aplicacion para aplicar los cambios.
echo.
pause
