# Produccion Empresarial - Hardening y Operacion

Este documento resume la configuracion recomendada para desplegar el sistema en LAN empresarial.

## 1) Requisitos de seguridad minimos

- Definir TICKETS_MODE=produccion.
- Definir TICKETS_STRICT_SECURITY=1.
- Definir TICKETS_HTTP_REQUIRE_API_KEY=1.
- Usar TICKETS_HTTP_API_KEY con 24+ caracteres.
- Usar TICKETS_LICENSE_ADMIN_KEY con 24+ caracteres.
- Definir TICKETS_HTTP_BIND_HOST y TICKETS_WS_BIND_HOST con IP fija del servidor.
- Definir TICKETS_LICENSE_HOST con IP fija del servidor.
- Restringir TICKETS_HTTP_CORS_ORIGINS y TICKETS_LICENSE_CORS_ORIGINS.

Con modo estricto, el servidor puede rechazar el inicio si detecta configuracion insegura.

## 2) Arranque recomendado

Usar el script:

- scripts/start_produccion_segura.ps1

Ejemplo:

- powershell -ExecutionPolicy Bypass -File scripts/start_produccion_segura.ps1 -ServerIp 192.168.1.50 -HttpApiKey "TU_API_KEY_LARGA_24_MINIMO" -LicenseAdminKey "TU_ADMIN_KEY_LARGA_24_MINIMO"

Antes de ejecutar, definir:

- IP del servidor
- API keys

## 3) Firewall recomendado (Windows)

Permitir entrada solo desde subred corporativa para puertos:

- 5555 (HTTP Tickets)
- 5556 (WebSocket)
- 8787 (Licencias)

Script incluido:

- powershell -ExecutionPolicy Bypass -File scripts/configurar_firewall_empresarial.ps1 -AllowedSubnet 192.168.1.0/24

Bloquear estos puertos en perfiles Public y permitir solo Domain/Private segun politica corporativa.

## 4) Operacion y monitoreo

- Revisar health endpoints periodicamente.
- Revisar logs en runtime/logs/.
- Verificar tamano de runtime/ y backups.
- Programar rotacion/retencion de backups.

## 5) Checklist de validacion previa a produccion

- Tests de endpoints y seguridad en verde.
- App receptora inicia con strict security activo.
- API key requerida para POST de tickets.
- CORS no acepta origenes no autorizados.
- Admin key de licencias no usa valor por defecto.
- Puertos accesibles solo desde red autorizada.
