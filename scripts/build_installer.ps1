# Genera dist\SistemaPOS.exe con PyInstaller y luego el instalador dist\installer\SistemaPOS-Setup-x.y.z.exe
# con Inno Setup 6. Ejecutar desde cualquier carpeta:
#     powershell -ExecutionPolicy Bypass -File scripts\build_installer.ps1
# Requisitos: el venv creado con requirements-dev.txt e Inno Setup 6 instalado.

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

$python = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $python)) { throw "No existe venv\Scripts\python.exe. Cree el entorno con requirements-dev.txt." }
$version = & $python -c "from utils.version import APP_VERSION; print(APP_VERSION)"
Write-Host "Empaquetando SistemaPOS $version con PyInstaller..."
& $python -m PyInstaller SistemaPOS.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falló." }

$candidates = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)
$iscc = $candidates | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1
if (-not $iscc) { throw "No se encontró Inno Setup 6. Descárguelo de https://jrsoftware.org/isdl.php e instálelo." }

Write-Host "Generando el instalador con Inno Setup..."
& $iscc "/DAppVersion=$version" (Join-Path $root "installer\SistemaPOS.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup falló." }

Write-Host ""
Write-Host "Listo: dist\installer\SistemaPOS-Setup-$version.exe"
