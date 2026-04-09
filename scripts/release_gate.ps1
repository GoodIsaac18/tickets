param(
    [int]$CoverageMin = 85,
    [int]$DataAccessCoverageMin = 38,
    [switch]$SkipPackageSmoke
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Action
    )

    Write-Host "[GATE] $Name"
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "[GATE] Falló etapa: $Name"
    }
}

$ProjectRoot = (Resolve-Path "$PSScriptRoot\..").Path
$PythonExe = Join-Path $ProjectRoot "python_embed\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "No se encontró python embebido en: $PythonExe"
}

Invoke-Step "Compilación sintáctica" {
    & $PythonExe -m py_compile "$ProjectRoot\kubo.py" "$ProjectRoot\kubito.py" "$ProjectRoot\app_receptora.py" "$ProjectRoot\app_emisora.py" "$ProjectRoot\app_licencias.py"
}

Invoke-Step "Pruebas + cobertura startup_guard" {
    & $PythonExe -m pytest -q --cov=src.core.startup_guard --cov-report=term-missing --cov-fail-under=$CoverageMin "$ProjectRoot\tests"
}

Invoke-Step "Cobertura mínima data_access" {
    & $PythonExe -m pytest -q --cov=core.data_access --cov-report=term-missing --cov-fail-under=$DataAccessCoverageMin "$ProjectRoot\tests"
}

Invoke-Step "Startup smoke (kubo/kubito/licencias)" {
    $env:TICKETS_SMOKE_STARTUP = "1"
    try {
        & $PythonExe "$ProjectRoot\kubo.py"
        if ($LASTEXITCODE -ne 0) { throw "Smoke kubo falló" }

        & $PythonExe "$ProjectRoot\kubito.py"
        if ($LASTEXITCODE -ne 0) { throw "Smoke kubito falló" }

        $env:TICKETS_LICENSE_ADMIN_KEY = "test-admin-key-very-strong-123456"
        & $PythonExe "$ProjectRoot\app_licencias.py"
        if ($LASTEXITCODE -ne 0) { throw "Smoke app_licencias falló" }
    }
    finally {
        Remove-Item Env:TICKETS_SMOKE_STARTUP -ErrorAction SilentlyContinue
    }
}

if (-not $SkipPackageSmoke) {
    Invoke-Step "PyInstaller smoke (kubo entrypoint)" {
        $smokeDist = Join-Path $ProjectRoot "runtime\smoke_dist"
        $smokeBuild = Join-Path $ProjectRoot "runtime\smoke_build"
        $smokeSpec = Join-Path $ProjectRoot "runtime\smoke_spec"
        New-Item -ItemType Directory -Force -Path $smokeDist | Out-Null
        New-Item -ItemType Directory -Force -Path $smokeBuild | Out-Null
        New-Item -ItemType Directory -Force -Path $smokeSpec | Out-Null

        & $PythonExe -m PyInstaller --noconfirm --clean --onedir --name SmokeKubo --distpath "$smokeDist" --workpath "$smokeBuild" --specpath "$smokeSpec" "$ProjectRoot\kubo.py"
    }
}

Write-Host "[GATE] OK: calidad mínima validada"
