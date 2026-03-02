@echo off
echo ============================================
echo   CONFIGURACION DE FIREWALL - SOPORTE TECNICO
echo ============================================
echo.

:: Verificar permisos de administrador
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [ERROR] Este script debe ejecutarse como ADMINISTRADOR
    echo.
    echo Haz clic derecho en este archivo y selecciona
    echo "Ejecutar como administrador"
    pause
    exit /b 1
)

echo Agregando reglas de firewall para el puerto 5555...
echo.

:: Eliminar regla anterior si existe
netsh advfirewall firewall delete rule name="Soporte Tecnico Servidor" >nul 2>&1

:: Agregar regla para TCP entrante
netsh advfirewall firewall add rule name="Soporte Tecnico Servidor" dir=in action=allow protocol=tcp localport=5555

if %errorLevel% equ 0 (
    echo.
    echo [OK] Regla de firewall creada correctamente
    echo [OK] Puerto 5555 TCP abierto para conexiones entrantes
) else (
    echo [ERROR] No se pudo crear la regla de firewall
)

echo.
echo ============================================
echo   Tu IP actual es:
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4"') do echo   %%a
echo.
echo   Los emisores deben configurar esta IP en
echo   su archivo servidor_config.txt
echo ============================================
echo.
pause
