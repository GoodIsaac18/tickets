@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Sistema de Tickets IT - Panel de Control

set "SCRIPT_DIR=%~dp0"
set "PYTHON_EXE=%SCRIPT_DIR%python_embed\python.exe"

:: ========================================================================
:: CONFIGURACIÓN DE GITHUB
:: ========================================================================
set "GITHUB_REPO=GoodIsaac18/tickets"
set "GITHUB_RAW=https://raw.githubusercontent.com/%GITHUB_REPO%/main"
set "GITHUB_ZIP=https://github.com/%GITHUB_REPO%/archive/refs/heads/main.zip"

:MENU_PRINCIPAL
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║              SISTEMA DE TICKETS IT - Panel de Control            ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

:: Mostrar versión actual
if exist "%SCRIPT_DIR%version.txt" (
    set /p VERSION_LOCAL=<"%SCRIPT_DIR%version.txt"
    echo   Version instalada: !VERSION_LOCAL!
) else (
    set "VERSION_LOCAL=No instalado"
    echo   Version: No instalado
)

:: Verificar si Python está instalado
if exist "%PYTHON_EXE%" (
    echo   Estado: [INSTALADO]
) else (
    echo   Estado: [NO INSTALADO]
)
echo.
echo ════════════════════════════════════════════════════════════════════
echo.
echo   [1] Instalar / Reinstalar sistema
echo   [2] Actualizar desde GitHub
echo   [3] Ejecutar EMISORA (Cliente)
echo   [4] Ejecutar RECEPTORA (Panel IT)
echo.
echo ────────────────────────────────────────────────────────────────────
echo.
echo   [5] Inicializar/Reparar base de datos
echo   [6] Configurar Firewall (puerto 5555)
echo   [7] Desinstalar sistema
echo.
echo ────────────────────────────────────────────────────────────────────
echo.
echo   [8] Publicar actualizacion a GitHub (Admin)
echo   [0] Salir
echo.
echo ════════════════════════════════════════════════════════════════════
echo.
set /p opcion="  Seleccione una opcion: "

if "%opcion%"=="1" goto INSTALAR
if "%opcion%"=="2" goto ACTUALIZAR
if "%opcion%"=="3" goto EJECUTAR_EMISORA
if "%opcion%"=="4" goto EJECUTAR_RECEPTORA
if "%opcion%"=="5" goto INICIALIZAR_DB
if "%opcion%"=="6" goto FIREWALL
if "%opcion%"=="7" goto DESINSTALAR
if "%opcion%"=="8" goto PUBLICAR
if "%opcion%"=="0" exit /b 0

echo.
echo   [!] Opcion no valida
timeout /t 2 >nul
goto MENU_PRINCIPAL

:: ========================================================================
:: 1. INSTALAR SISTEMA
:: ========================================================================
:INSTALAR
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║                    INSTALAR SISTEMA DE TICKETS                   ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

:: Primero verificar actualizaciones en GitHub
echo   Verificando actualizaciones en GitHub...
set "TEMP_VERSION=%TEMP%\tickets_version_check.txt"
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%GITHUB_RAW%/version.txt' -OutFile '%TEMP_VERSION%' -TimeoutSec 10 } catch { exit 1 }}" 2>nul

if exist "%TEMP_VERSION%" (
    set /p VERSION_GITHUB=<"%TEMP_VERSION%"
    del "%TEMP_VERSION%" 2>nul
    
    echo   Version local:  !VERSION_LOCAL!
    echo   Version GitHub: !VERSION_GITHUB!
    echo.
    
    if not "!VERSION_LOCAL!"=="!VERSION_GITHUB!" (
        echo   [!] Hay una version mas reciente: !VERSION_GITHUB!
        echo.
        choice /C SN /M "  Desea descargar la ultima version antes de instalar [S/N]"
        if !errorlevel!==1 (
            call :DESCARGAR_GITHUB
        )
    ) else (
        echo   [OK] Tiene la version mas reciente.
        echo.
    )
) else (
    echo   [!] Sin conexion a GitHub, usando archivos locales.
    echo.
)

:: Verificar si Python está instalado
if not exist "%PYTHON_EXE%" (
    echo   Python no encontrado. Descargando...
    call :INSTALAR_PYTHON
    if errorlevel 1 (
        echo   [ERROR] No se pudo instalar Python.
        pause
        goto MENU_PRINCIPAL
    )
)

:: Ejecutar instalador gráfico
echo.
echo   Iniciando instalador grafico...
cd /d "%SCRIPT_DIR%"
"%PYTHON_EXE%" "%SCRIPT_DIR%instalador.py"
pause
goto MENU_PRINCIPAL

:: ========================================================================
:: 2. ACTUALIZAR DESDE GITHUB
:: ========================================================================
:ACTUALIZAR
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║              ACTUALIZAR DESDE GITHUB                             ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Repositorio: github.com/%GITHUB_REPO%
echo.
echo   Verificando version en GitHub...

set "TEMP_VERSION=%TEMP%\tickets_version.txt"
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri '%GITHUB_RAW%/version.txt' -OutFile '%TEMP_VERSION%' -TimeoutSec 15 } catch { Write-Host 'Error'; exit 1 }}" 2>nul

if not exist "%TEMP_VERSION%" (
    echo.
    echo   [ERROR] No se pudo conectar a GitHub.
    echo           Verifique su conexion a internet.
    echo.
    pause
    goto MENU_PRINCIPAL
)

set /p VERSION_GITHUB=<"%TEMP_VERSION%"
del "%TEMP_VERSION%" 2>nul

echo.
echo   Version instalada:  !VERSION_LOCAL!
echo   Version en GitHub:  !VERSION_GITHUB!
echo.

if "!VERSION_LOCAL!"=="!VERSION_GITHUB!" (
    echo   [OK] Ya tiene la version mas reciente.
    echo.
    choice /C SN /M "  Desea forzar reinstalacion de archivos [S/N]"
    if !errorlevel!==2 (
        pause
        goto MENU_PRINCIPAL
    )
)

call :DESCARGAR_GITHUB

echo.
echo ════════════════════════════════════════════════════════════════════
echo   [OK] ACTUALIZACION COMPLETADA
echo ════════════════════════════════════════════════════════════════════
echo.
echo   Reinicie la aplicacion para aplicar los cambios.
echo.
pause
goto MENU_PRINCIPAL

:: ========================================================================
:: 3. EJECUTAR EMISORA
:: ========================================================================
:EJECUTAR_EMISORA
cls
if not exist "%PYTHON_EXE%" (
    echo.
    echo   [ERROR] El sistema no esta instalado.
    echo           Seleccione la opcion 1 para instalar.
    echo.
    pause
    goto MENU_PRINCIPAL
)

echo   Iniciando Emisora...
cd /d "%SCRIPT_DIR%"
start "" "%PYTHON_EXE%" "%SCRIPT_DIR%app_emisora.py"
goto MENU_PRINCIPAL

:: ========================================================================
:: 4. EJECUTAR RECEPTORA
:: ========================================================================
:EJECUTAR_RECEPTORA
cls
if not exist "%PYTHON_EXE%" (
    echo.
    echo   [ERROR] El sistema no esta instalado.
    echo           Seleccione la opcion 1 para instalar.
    echo.
    pause
    goto MENU_PRINCIPAL
)

echo   Iniciando Receptora (Panel IT)...
cd /d "%SCRIPT_DIR%"
start "" "%PYTHON_EXE%" "%SCRIPT_DIR%app_receptora.py"
goto MENU_PRINCIPAL

:: ========================================================================
:: 5. INICIALIZAR BASE DE DATOS
:: ========================================================================
:INICIALIZAR_DB
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║              INICIALIZAR / REPARAR BASE DE DATOS                 ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.

if not exist "%PYTHON_EXE%" (
    echo   [ERROR] Python no esta instalado.
    echo           Instale el sistema primero (opcion 1).
    echo.
    pause
    goto MENU_PRINCIPAL
)

echo   [!] ADVERTENCIA: Esto reiniciara las bases de datos.
echo       Los datos existentes se perderan.
echo.
choice /C SN /M "  Esta seguro de continuar [S/N]"
if !errorlevel!==2 (
    goto MENU_PRINCIPAL
)

echo.
echo   Inicializando bases de datos...
"%PYTHON_EXE%" "%SCRIPT_DIR%init_database.py"
echo.
pause
goto MENU_PRINCIPAL

:: ========================================================================
:: 6. CONFIGURAR FIREWALL
:: ========================================================================
:FIREWALL
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║              CONFIGURAR FIREWALL                                 ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Se abrira el puerto 5555 para permitir conexiones del sistema.
echo.
echo   [!] Se requieren permisos de administrador.
echo.
choice /C SN /M "  Desea continuar [S/N]"
if !errorlevel!==2 (
    goto MENU_PRINCIPAL
)

echo.
echo   Configurando firewall...

:: Eliminar reglas existentes
netsh advfirewall firewall delete rule name="TicketsIT_Servidor" >nul 2>&1
netsh advfirewall firewall delete rule name="TicketsIT_Cliente" >nul 2>&1

:: Crear nuevas reglas
netsh advfirewall firewall add rule name="TicketsIT_Servidor" dir=in action=allow protocol=TCP localport=5555 >nul 2>&1
netsh advfirewall firewall add rule name="TicketsIT_Cliente" dir=out action=allow protocol=TCP localport=5555 >nul 2>&1

if errorlevel 1 (
    echo.
    echo   [ERROR] No se pudo configurar el firewall.
    echo           Ejecute este script como Administrador.
) else (
    echo   [OK] Firewall configurado correctamente.
    echo       Puerto 5555 abierto para TCP entrada/salida.
)

echo.
pause
goto MENU_PRINCIPAL

:: ========================================================================
:: 7. DESINSTALAR
:: ========================================================================
:DESINSTALAR
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║              DESINSTALAR SISTEMA DE TICKETS                      ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Esto eliminara:
echo   - Accesos directos del escritorio
echo   - Accesos directos del menu inicio
echo   - Configuracion de inicio automatico
echo   - Reglas de firewall
echo.
echo   Los archivos de programa y datos NO se eliminaran.
echo.
set /p confirmar="  Escriba SI para confirmar: "

if /i not "%confirmar%"=="SI" (
    echo.
    echo   Desinstalacion cancelada.
    pause
    goto MENU_PRINCIPAL
)

echo.
echo   Eliminando accesos directos...

:: Emisora
del "%USERPROFILE%\Desktop\Tickets IT - Emisora.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Sistema Tickets IT\Tickets IT - Emisora.lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Tickets IT - Emisora.lnk" 2>nul

:: Receptora
del "%USERPROFILE%\Desktop\Tickets IT - Receptora (Panel IT).lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Sistema Tickets IT\Tickets IT - Receptora (Panel IT).lnk" 2>nul
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Tickets IT - Receptora (Panel IT).lnk" 2>nul

:: Carpeta menu inicio
rmdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Sistema Tickets IT" 2>nul

echo   Eliminando reglas de firewall...
netsh advfirewall firewall delete rule name="TicketsIT_Servidor" >nul 2>&1
netsh advfirewall firewall delete rule name="TicketsIT_Cliente" >nul 2>&1

echo.
echo ════════════════════════════════════════════════════════════════════
echo   [OK] DESINSTALACION COMPLETADA
echo ════════════════════════════════════════════════════════════════════
echo.
echo   Los archivos del programa permanecen en:
echo   %SCRIPT_DIR%
echo.
echo   Puede eliminarlos manualmente si lo desea.
echo.
pause
goto MENU_PRINCIPAL

:: ========================================================================
:: 8. PUBLICAR ACTUALIZACION A GITHUB
:: ========================================================================
:PUBLICAR
cls
echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║          PUBLICAR ACTUALIZACION A GITHUB (Admin)                 ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Repositorio: github.com/%GITHUB_REPO%
echo.

:: Verificar git
where git >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Git no esta instalado.
    echo           Instale Git desde: https://git-scm.com/download/win
    echo.
    pause
    goto MENU_PRINCIPAL
)

echo   Version actual: !VERSION_LOCAL!
echo.
echo   Ingrese la nueva version (formato: X.Y.Z)
set /p NUEVA_VERSION="  Nueva version: "

if "%NUEVA_VERSION%"=="" (
    echo   [ERROR] Debe ingresar una version.
    pause
    goto MENU_PRINCIPAL
)

:: Actualizar version.txt
echo %NUEVA_VERSION%>"%SCRIPT_DIR%version.txt"

cd /d "%SCRIPT_DIR%"

:: Verificar si es repositorio git
if not exist "%SCRIPT_DIR%.git" (
    echo   Inicializando repositorio Git...
    git init
    git remote add origin https://github.com/%GITHUB_REPO%.git
)

echo.
echo   Preparando archivos para subir...
git add -A
git commit -m "Version %NUEVA_VERSION%"

echo.
echo   Subiendo a GitHub...
echo   (Se le pedira autenticacion si es necesario)
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo   [!] Si fallo el push, intente:
    echo       git branch -M main
    echo       git push -u origin main --force
)

echo.
echo ════════════════════════════════════════════════════════════════════
echo   Version %NUEVA_VERSION% publicada
echo ════════════════════════════════════════════════════════════════════
echo.
pause
goto MENU_PRINCIPAL

:: ========================================================================
:: FUNCIONES AUXILIARES
:: ========================================================================

:DESCARGAR_GITHUB
echo.
echo   Descargando desde GitHub...

set "TEMP_ZIP=%TEMP%\tickets_update.zip"
set "TEMP_EXTRACT=%TEMP%\tickets_extract"

echo   [1/4] Descargando repositorio...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%GITHUB_ZIP%' -OutFile '%TEMP_ZIP%'}" 2>nul

if not exist "%TEMP_ZIP%" (
    echo   [ERROR] No se pudo descargar.
    goto :EOF
)

echo   [2/4] Extrayendo archivos...
if exist "%TEMP_EXTRACT%" rmdir /s /q "%TEMP_EXTRACT%" 2>nul
powershell -Command "Expand-Archive -Path '%TEMP_ZIP%' -DestinationPath '%TEMP_EXTRACT%' -Force" 2>nul

set "SRC_DIR=%TEMP_EXTRACT%\tickets-main"

echo   [3/4] Actualizando archivos...

:: Archivos Python
if exist "%SRC_DIR%\app_emisora.py" copy /Y "%SRC_DIR%\app_emisora.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\app_receptora.py" copy /Y "%SRC_DIR%\app_receptora.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\data_access.py" copy /Y "%SRC_DIR%\data_access.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\instalador.py" copy /Y "%SRC_DIR%\instalador.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\servidor_red.py" copy /Y "%SRC_DIR%\servidor_red.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\servicio_notificaciones.py" copy /Y "%SRC_DIR%\servicio_notificaciones.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\notificaciones_windows.py" copy /Y "%SRC_DIR%\notificaciones_windows.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\init_database.py" copy /Y "%SRC_DIR%\init_database.py" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\generar_iconos.py" copy /Y "%SRC_DIR%\generar_iconos.py" "%SCRIPT_DIR%" >nul 2>&1

:: Scripts
if exist "%SRC_DIR%\SISTEMA_TICKETS.bat" copy /Y "%SRC_DIR%\SISTEMA_TICKETS.bat" "%SCRIPT_DIR%" >nul 2>&1

:: Launchers VBS
if exist "%SRC_DIR%\ejecutar_emisora_oculto.vbs" copy /Y "%SRC_DIR%\ejecutar_emisora_oculto.vbs" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\ejecutar_receptora_oculto.vbs" copy /Y "%SRC_DIR%\ejecutar_receptora_oculto.vbs" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\launcher_emisora.vbs" copy /Y "%SRC_DIR%\launcher_emisora.vbs" "%SCRIPT_DIR%" >nul 2>&1
if exist "%SRC_DIR%\launcher_receptora.vbs" copy /Y "%SRC_DIR%\launcher_receptora.vbs" "%SCRIPT_DIR%" >nul 2>&1

:: Iconos
if exist "%SRC_DIR%\icons\*" (
    if not exist "%SCRIPT_DIR%icons" mkdir "%SCRIPT_DIR%icons" 2>nul
    xcopy /Y /E /I "%SRC_DIR%\icons" "%SCRIPT_DIR%icons" >nul 2>&1
)

:: Version
if exist "%SRC_DIR%\version.txt" copy /Y "%SRC_DIR%\version.txt" "%SCRIPT_DIR%" >nul 2>&1

echo   [4/4] Limpiando...
del "%TEMP_ZIP%" 2>nul
rmdir /s /q "%TEMP_EXTRACT%" 2>nul

set /p VERSION_LOCAL=<"%SCRIPT_DIR%version.txt"
echo   [OK] Actualizado a version !VERSION_LOCAL!
goto :EOF

:INSTALAR_PYTHON
set "PYTHON_DIR=%SCRIPT_DIR%python_embed"
set "PYTHON_VERSION=3.11.9"
set "PYTHON_ZIP_FILE=python-%PYTHON_VERSION%-embed-amd64.zip"
set "PYTHON_URL=https://www.python.org/ftp/python/%PYTHON_VERSION%/%PYTHON_ZIP_FILE%"

if not exist "%PYTHON_DIR%" mkdir "%PYTHON_DIR%"

echo   [1/4] Descargando Python %PYTHON_VERSION%...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri '%PYTHON_URL%' -OutFile '%SCRIPT_DIR%%PYTHON_ZIP_FILE%'}" 2>nul

if not exist "%SCRIPT_DIR%%PYTHON_ZIP_FILE%" (
    echo   [ERROR] No se pudo descargar Python.
    exit /b 1
)

echo   [2/4] Extrayendo Python...
powershell -Command "Expand-Archive -Path '%SCRIPT_DIR%%PYTHON_ZIP_FILE%' -DestinationPath '%PYTHON_DIR%' -Force"
del "%SCRIPT_DIR%%PYTHON_ZIP_FILE%" 2>nul

echo   [3/4] Configurando Python...
(
    echo import site
    echo site.main^(^)
) > "%PYTHON_DIR%\sitecustomize.py"

(
    echo python311.zip
    echo .
    echo ..
    echo Lib
    echo Lib\site-packages
    echo import site
) > "%PYTHON_DIR%\python311._pth"

if not exist "%PYTHON_DIR%\Lib" mkdir "%PYTHON_DIR%\Lib"
if not exist "%PYTHON_DIR%\Lib\site-packages" mkdir "%PYTHON_DIR%\Lib\site-packages"
if not exist "%PYTHON_DIR%\Scripts" mkdir "%PYTHON_DIR%\Scripts"

echo   [4/4] Instalando pip...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; $ProgressPreference = 'SilentlyContinue'; Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile '%PYTHON_DIR%\get-pip.py'}"
"%PYTHON_EXE%" "%PYTHON_DIR%\get-pip.py" --no-warn-script-location >nul 2>&1

echo   [OK] Python instalado.
exit /b 0
