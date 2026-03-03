@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul 2>&1
title Publicar Actualización a GitHub - Sistema de Tickets IT

set "SCRIPT_DIR=%~dp0"
set "GITHUB_REPO=GoodIsaac18/tickets"

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║       PUBLICAR ACTUALIZACIÓN A GITHUB - Sistema de Tickets       ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Repositorio: github.com/%GITHUB_REPO%
echo.

:: Verificar si git está instalado
where git >nul 2>&1
if errorlevel 1 (
    echo   [ERROR] Git no esta instalado.
    echo.
    echo   Instale Git desde: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

:: Leer versión actual
if exist "%SCRIPT_DIR%version.txt" (
    set /p VERSION_ACTUAL=<"%SCRIPT_DIR%version.txt"
) else (
    set "VERSION_ACTUAL=1.0.0"
    echo 1.0.0>"%SCRIPT_DIR%version.txt"
)

echo   Version actual: %VERSION_ACTUAL%
echo.

:: Preguntar nueva versión
echo   Ingrese la nueva version (actual: %VERSION_ACTUAL%)
echo   Formato: X.Y.Z (ejemplo: 1.0.1, 1.1.0, 2.0.0)
echo.
set /p NUEVA_VERSION="  Nueva version: "

if "%NUEVA_VERSION%"=="" (
    echo   [ERROR] Debe ingresar una version.
    pause
    exit /b 1
)

:: Actualizar version.txt
echo %NUEVA_VERSION%>"%SCRIPT_DIR%version.txt"
echo.
echo   [OK] Version actualizada a %NUEVA_VERSION%
echo.

:: Verificar si es un repositorio git
if not exist "%SCRIPT_DIR%.git" (
    echo   [!] Inicializando repositorio Git...
    cd /d "%SCRIPT_DIR%"
    git init
    git remote add origin https://github.com/%GITHUB_REPO%.git
    echo.
)

cd /d "%SCRIPT_DIR%"

:: Crear/actualizar .gitignore
echo   [1/4] Configurando .gitignore...
(
    echo # Archivos de Python
    echo __pycache__/
    echo *.pyc
    echo *.pyo
    echo.
    echo # Archivos de datos locales ^(no subir bases de datos^)
    echo tickets_db.xlsx
    echo tecnicos_db.xlsx
    echo equipos_db.xlsx
    echo red_db.xlsx
    echo equipos_aprobados.json
    echo solicitudes_enlace.json
    echo notificaciones_estado.json
    echo servidor_config.txt
    echo ruta_actualizaciones.txt
    echo actualizacion_config.txt
    echo.
    echo # Reportes generados
    echo reporte_*.xlsx
    echo.
    echo # Python embebido ^(muy grande para GitHub^)
    echo python_embed/
    echo.
    echo # Build y distribución
    echo build/
    echo dist/
    echo *.spec
    echo.
    echo # Archivos temporales
    echo *.log
    echo *.tmp
    echo.
    echo # IDE
    echo .vscode/
    echo .idea/
) > "%SCRIPT_DIR%.gitignore"

echo   [2/4] Agregando archivos al commit...
git add -A

echo   [3/4] Creando commit...
git commit -m "Version %NUEVA_VERSION% - Actualización del sistema de tickets"

echo   [4/4] Subiendo a GitHub...
echo.
echo   NOTA: Si es la primera vez, se le pedira autenticacion.
echo         Use su token de GitHub como contraseña.
echo.
git push -u origin main

if errorlevel 1 (
    echo.
    echo   [!] Si el push fallo, intente con:
    echo       git push -u origin master
    echo.
    echo   O si el repositorio esta vacio:
    echo       git branch -M main
    echo       git push -u origin main
    echo.
    pause
    exit /b 1
)

echo.
echo ╔══════════════════════════════════════════════════════════════════╗
echo ║        OK ACTUALIZACION PUBLICADA EN GITHUB EXITOSAMENTE         ║
echo ╚══════════════════════════════════════════════════════════════════╝
echo.
echo   Version: %NUEVA_VERSION%
echo   Repositorio: https://github.com/%GITHUB_REPO%
echo.
echo   Los usuarios podran actualizar ejecutando:
echo   - INSTALAR_SISTEMA.bat ^(verificara automaticamente^)
echo   - ACTUALIZAR_SISTEMA.bat ^(actualizacion manual^)
echo.
pause
