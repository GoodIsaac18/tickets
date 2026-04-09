$ErrorActionPreference = "Stop"

param(
	[string]$ServerIp = "",
	[string]$HttpApiKey = "",
	[string]$LicenseAdminKey = "",
	[string]$CorsOrigins = "http://localhost:5173,http://127.0.0.1:5173",
	[switch]$SkipQualityGate
)

function Get-LocalIPv4 {
	$candidate = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
		Where-Object { $_.IPAddress -notlike "169.254.*" -and $_.IPAddress -ne "127.0.0.1" } |
		Select-Object -First 1 -ExpandProperty IPAddress
	if (-not $candidate) {
		throw "No se pudo detectar IP IPv4 local. Pasa -ServerIp manualmente."
	}
	return $candidate
}

if (-not $ServerIp) {
	$ServerIp = Get-LocalIPv4
}

if ($HttpApiKey.Length -lt 24) {
	throw "Debes pasar -HttpApiKey con al menos 24 caracteres."
}

if ($LicenseAdminKey.Length -lt 24) {
	throw "Debes pasar -LicenseAdminKey con al menos 24 caracteres."
}

if ($CorsOrigins -match "\*") {
	throw "No se permite wildcard en -CorsOrigins para producción segura."
}

# Perfil base de seguridad/produccion para servidor LAN
$env:TICKETS_MODE = "produccion"
$env:TICKETS_STRICT_SECURITY = "1"

# Bind LAN
$env:TICKETS_HTTP_BIND_HOST = $ServerIp
$env:TICKETS_WS_BIND_HOST = $ServerIp
$env:TICKETS_LICENSE_HOST = $ServerIp

# Seguridad obligatoria
$env:TICKETS_HTTP_REQUIRE_API_KEY = "1"
$env:TICKETS_HTTP_API_KEY_HEADER = "X-Tickets-Key"
$env:TICKETS_HTTP_API_KEY = $HttpApiKey
$env:TICKETS_LICENSE_ADMIN_KEY = $LicenseAdminKey

# CORS restringido
$env:TICKETS_HTTP_CORS_ORIGINS = $CorsOrigins
$env:TICKETS_LICENSE_CORS_ORIGINS = $CorsOrigins

if (-not $SkipQualityGate) {
	Write-Host "Ejecutando quality gate previo a producción..."
	& "$PSScriptRoot\release_gate.ps1" -CoverageMin 85 -DataAccessCoverageMin 38 -SkipPackageSmoke
	if ($LASTEXITCODE -ne 0) {
		throw "Quality gate falló. No se iniciará producción."
	}
}

# Tuning operativo
$env:TICKETS_DISCOVERY_CACHE_TTL = "30"
$env:TICKETS_DISCOVERY_MAX_WORKERS = "24"
$env:TICKETS_EQUIPO_DB_SYNC_MIN_INTERVAL = "15"
$env:TICKETS_LICENSE_VALIDATE_RATE_MAX = "60"
$env:TICKETS_LICENSE_VALIDATE_RATE_WINDOW = "60"

Write-Host "Iniciando app_receptora con perfil de produccion segura en $ServerIp ..."
& "$PSScriptRoot\..\python_embed\python.exe" "$PSScriptRoot\..\app_receptora.py"
