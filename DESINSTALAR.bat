@echo off
chcp 65001 >nul 2>&1
title Desinstalador - Sistema de Tickets IT

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║              DESINSTALADOR - SISTEMA DE TICKETS            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo ¿Está seguro de que desea desinstalar Tickets IT - Emisora?
echo.
echo Esto eliminará:
echo   - Accesos directos del escritorio
echo   - Accesos directos del menú inicio
echo   - Configuración de inicio automático
echo.
echo Los archivos de datos (tickets, equipos) NO se eliminarán.
echo.
set /p confirmar="Escriba SI para confirmar: "

if /i "%confirmar%"=="SI" (
    echo.
    echo Eliminando accesos directos...
    
    del "%USERPROFILE%\Desktop\Tickets IT - Emisora.lnk" 2>nul
    del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Sistema Tickets IT\Tickets IT - Emisora.lnk" 2>nul
    del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Tickets IT - Emisora.lnk" 2>nul
    rmdir "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Sistema Tickets IT" 2>nul
    
    echo Eliminando reglas de firewall...
    netsh advfirewall firewall delete rule name=TicketsIT_Servidor 2>nul
    
    echo.
    echo ════════════════════════════════════════════════════════════
    echo   DESINSTALACIÓN COMPLETADA
    echo ════════════════════════════════════════════════════════════
    echo.
    echo Los archivos del programa permanecen en:
    echo C:\Users\PROTECNICA\Desktop\tickets\tickets\tickets
    echo.
    echo Puede eliminarlos manualmente si lo desea.
) else (
    echo.
    echo Desinstalación cancelada.
)

echo.
pause
