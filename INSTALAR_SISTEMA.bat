@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Instalador - Sistema de Tickets IT

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%python_embed\python.exe"
set "CONFIG_ACTUALIZACION=%SCRIPT_DIR%ruta_actualizaciones.txt"

:: ========================================================================
:: CONFIGURACIÓN DE GITHUB
:: ========================================================================
set "GITHUB_REPO=GoodIsaac18/tickets"
set "GITHUB_RAW=https://raw.githubusercontent.com/%GITHUB_REPO%/main"
set "GITHUB_ZIP=https://github.com/%GITHUB_REPO%/archive/refs/heads/main.zip"

:: ========================================================================
:: VERIFICAR ACTUALIZACIONES DESDE GITHUB
:: ========================================================================

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║           VERIFICANDO ACTUALIZACIONES EN GITHUB...               ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

:: Leer versión local
if exist "%SCRIPT_DIR%version.txt" (
    set /p VERSION_LOCAL=<"%SCRIPT_DIR%version.txt"
) else (
    set "VERSION_LOCAL=0.0.0"
)

echo   Version local: !VERSION_LOCAL!

:: Descargar version.txt desde GitHub
set "TEMP_VERSION=%TEMP%\tickets_version_check.txt"
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%GITHUB_RAW%/version.txt' -OutFile '%TEMP_VERSION%' -TimeoutSec 10 } catch { exit 1 }}" 2>nul

if exist "%TEMP_VERSION%" (
    set /p VERSION_GITHUB=<"%TEMP_VERSION%"
    del "%TEMP_VERSION%" 2>nul
    
    echo   Version en GitHub: !VERSION_GITHUB!
    echo.
    
    :: Comparar versiones
    if not "!VERSION_LOCAL!"=="!VERSION_GITHUB!" (
        echo   [!] HAY UNA NUEVA VERSION DISPONIBLE: !VERSION_GITHUB!
        echo.
        choice /C SN /M "  Desea actualizar ahora [S=Si, N=No]"
        if !errorlevel!==1 (
            echo.
            echo   Descargando actualizacion desde GitHub...
            echo.
            
            :: Descargar ZIP completo del repositorio
            set "TEMP_ZIP=%TEMP%\tickets_update.zip"
            set "TEMP_EXTRACT=%TEMP%\tickets_extract"
            
            echo   [1/4] Descargando repositorio...
            powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%GITHUB_ZIP%' -OutFile '!TEMP_ZIP!'}" 2>nul
            
            if exist "!TEMP_ZIP!" (
                echo   [2/4] Extrayendo archivos...
                if exist "!TEMP_EXTRACT!" rmdir /s /q "!TEMP_EXTRACT!" 2>nul
                powershell -Command "Expand-Archive -Path '!TEMP_ZIP!' -DestinationPath '!TEMP_EXTRACT!' -Force" 2>nul
                
                echo   [3/4] Actualizando archivos...
                :: La carpeta extraída será tickets-main
                set "SRC_DIR=!TEMP_EXTRACT!\tickets-main"
                
                :: Copiar archivos Python principales
                if exist "!SRC_DIR!\app_emisora.py" copy /Y "!SRC_DIR!\app_emisora.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\app_receptora.py" copy /Y "!SRC_DIR!\app_receptora.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\data_access.py" copy /Y "!SRC_DIR!\data_access.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\instalador.py" copy /Y "!SRC_DIR!\instalador.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\servidor_red.py" copy /Y "!SRC_DIR!\servidor_red.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\servicio_notificaciones.py" copy /Y "!SRC_DIR!\servicio_notificaciones.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\notificaciones_windows.py" copy /Y "!SRC_DIR!\notificaciones_windows.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\init_database.py" copy /Y "!SRC_DIR!\init_database.py" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\generar_iconos.py" copy /Y "!SRC_DIR!\generar_iconos.py" "%SCRIPT_DIR%" >nul 2>&1
                
                :: Copiar scripts BAT
                if exist "!SRC_DIR!\INSTALAR_SISTEMA.bat" copy /Y "!SRC_DIR!\INSTALAR_SISTEMA.bat" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\ejecutar_emisora.bat" copy /Y "!SRC_DIR!\ejecutar_emisora.bat" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\ejecutar_receptora.bat" copy /Y "!SRC_DIR!\ejecutar_receptora.bat" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\ACTUALIZAR_SISTEMA.bat" copy /Y "!SRC_DIR!\ACTUALIZAR_SISTEMA.bat" "%SCRIPT_DIR%" >nul 2>&1
                
                :: Copiar launchers VBS
                if exist "!SRC_DIR!\ejecutar_emisora_oculto.vbs" copy /Y "!SRC_DIR!\ejecutar_emisora_oculto.vbs" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\ejecutar_receptora_oculto.vbs" copy /Y "!SRC_DIR!\ejecutar_receptora_oculto.vbs" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\launcher_emisora.vbs" copy /Y "!SRC_DIR!\launcher_emisora.vbs" "%SCRIPT_DIR%" >nul 2>&1
                if exist "!SRC_DIR!\launcher_receptora.vbs" copy /Y "!SRC_DIR!\launcher_receptora.vbs" "%SCRIPT_DIR%" >nul 2>&1
                
                :: Copiar iconos
                if exist "!SRC_DIR!\icons\*" (
                    if not exist "%SCRIPT_DIR%icons" mkdir "%SCRIPT_DIR%icons" 2>nul
                    xcopy /Y /E /I "!SRC_DIR!\icons" "%SCRIPT_DIR%icons" >nul 2>&1
                )
                
                :: Copiar version.txt
                if exist "!SRC_DIR!\version.txt" copy /Y "!SRC_DIR!\version.txt" "%SCRIPT_DIR%" >nul 2>&1
                
                echo   [4/4] Limpiando archivos temporales...
                del "!TEMP_ZIP!" 2>nul
                rmdir /s /q "!TEMP_EXTRACT!" 2>nul
                
                echo.
                echo   [OK] Actualizado a version !VERSION_GITHUB!
                echo.
                timeout /t 2 >nul
            ) else (
                echo   [ERROR] No se pudo descargar la actualizacion.
                echo           Verifique su conexion a internet.
                timeout /t 3 >nul
            )
        )
    ) else (
        echo   [OK] Ya tiene la version mas reciente.
        echo.
        timeout /t 1 >nul
    )
) else (
    echo   [!] No se pudo verificar actualizaciones (sin conexion?)
    echo       Continuando con la version local...
    echo.
    timeout /t 2 >nul
)

:: ========================================================================
:: CONTINUAR CON INSTALACIÓN NORMAL
:: ========================================================================

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
