@echo off
title Compilar Instalador - Sistema de Tickets IT
echo ============================================
echo  COMPILAR INSTALADOR A .EXE
echo ============================================
echo.

cd /d "%~dp0"

echo [1/3] Compilando con PyInstaller...
python_embed\python.exe -m PyInstaller Instalador_Tickets.spec --clean --noconfirm
if errorlevel 1 (
    echo.
    echo [ERROR] Fallo la compilacion.
    pause
    exit /b 1
)

echo.
echo [2/3] Copiando .exe a carpeta principal...
copy /y "dist\Instalador_Tickets_IT.exe" "." >nul

echo [3/3] Limpiando temporales...
rmdir /s /q build\Instalador_Tickets 2>nul

echo.
echo ============================================
echo  LISTO! Instalador_Tickets_IT.exe generado
echo ============================================
echo.
pause
