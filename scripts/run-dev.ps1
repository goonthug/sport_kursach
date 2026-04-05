<#
  Запуск SportRent на Windows (PowerShell).

  Делает: venv → pip install → .env из примера (если нет) → migrate → (опционально) populate_db → runserver.

  Требуется заранее: установленный PostgreSQL, созданная БД, корректный sportrent/.env (или скопируйте из .env.example).

  Запуск из корня репозитория:
    .\scripts\run-dev.ps1

  С тестовыми данными (первый раз):
    .\scripts\run-dev.ps1 -Seed

  Если политика запрещает скрипты:
    Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
#>

param(
    [switch]$Seed,
    [switch]$NoServer
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$SportrentDir = Join-Path $RepoRoot "sportrent"
$VenvDir = Join-Path $RepoRoot "venv"
$EnvExample = Join-Path $RepoRoot ".env.example"
$EnvTarget = Join-Path $SportrentDir ".env"

function Test-CommandExists {
    param([string]$Name)
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

Write-Host "==> Репозиторий: $RepoRoot" -ForegroundColor Cyan

if (-not (Test-Path $SportrentDir)) {
    Write-Error "Не найден каталог sportrent: $SportrentDir"
}

# Python
$Py = $null
if (Test-CommandExists "python") {
    $Py = "python"
} elseif (Test-CommandExists "py") {
    $Py = "py"
} else {
    Write-Error "Не найден Python. Установите Python 3 с https://www.python.org/downloads/ и добавьте в PATH."
}

Write-Host "==> Python: $Py" -ForegroundColor Cyan
& $Py --version

# venv
if (-not (Test-Path $VenvDir)) {
    Write-Host "==> Создаю виртуальное окружение: $VenvDir" -ForegroundColor Cyan
    & $Py -m venv $VenvDir
}

$Activate = Join-Path $VenvDir "Scripts\Activate.ps1"
if (-not (Test-Path $Activate)) {
    Write-Error "Не найден $Activate"
}

Write-Host "==> Активирую venv" -ForegroundColor Cyan
. $Activate

$PythonExe = Join-Path $VenvDir "Scripts\python.exe"

Write-Host "==> pip install -r requirements.txt" -ForegroundColor Cyan
& $PythonExe -m pip install --upgrade pip -q
& $PythonExe -m pip install -r (Join-Path $RepoRoot "requirements.txt")

# python-docx (договоры)
& $PythonExe -m pip install "python-docx" -q 2>$null

# .env
if (-not (Test-Path $EnvTarget)) {
    if (Test-Path $EnvExample) {
        Write-Host "==> Копирую .env.example -> sportrent\.env (проверьте DB_*!)" -ForegroundColor Yellow
        Copy-Item $EnvExample $EnvTarget
    } else {
        Write-Host "==> ВНИМАНИЕ: нет sportrent\.env и нет .env.example. Создайте .env вручную." -ForegroundColor Red
    }
} else {
    Write-Host "==> Найден sportrent\.env" -ForegroundColor Green
}

Set-Location $SportrentDir

$LogsDir = Join-Path $SportrentDir "logs"
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
    Write-Host "==> Создан каталог logs" -ForegroundColor Cyan
}

Write-Host "==> django migrate" -ForegroundColor Cyan
& $PythonExe manage.py migrate

if ($Seed) {
    Write-Host "==> populate_db (тестовые данные)" -ForegroundColor Cyan
    & $PythonExe manage.py populate_db
}

if (-not $NoServer) {
    Write-Host "==> Запуск сервера http://127.0.0.1:8000/ (Ctrl+C — остановить)" -ForegroundColor Green
    & $PythonExe manage.py runserver
} else {
    Write-Host "==> Готово (сервер не запускался: -NoServer)" -ForegroundColor Green
}
