# AdForge — wrapper do scheduler para @daily-analyst
# Verifica pré-requisitos, executa run.py e loga timestamp + status.
$ErrorActionPreference = "Stop"
$adforge = Join-Path $env:USERPROFILE ".adforge"
$dir     = Join-Path $adforge "daily_analyst"
$logsDir = Join-Path $adforge "logs"
$schedLog = Join-Path $logsDir "scheduler.log"
$envFile = Join-Path $adforge ".env"

New-Item -ItemType Directory -Force -Path $logsDir | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts  $msg`n"
    # Usa .NET diretamente para UTF-8 sem BOM (Add-Content no PS5 adiciona BOM)
    [System.IO.File]::AppendAllText($schedLog, $line, [System.Text.Encoding]::UTF8)
}

Write-Log "=== scheduler start ==="

# 1) Pré-requisito: Python
# Preferir Python 3.14 (tem playwright instalado com Chromium) sobre o venv do hermes (sem pip/playwright)
$py314 = "C:\Users\User\AppData\Local\Programs\Python\Python314\python.exe"
if (Test-Path $py314) {
    $py = [PSCustomObject]@{ Source = $py314 }
} else {
    $py = (Get-Command python -ErrorAction SilentlyContinue)
    if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue) }
    if (-not $py) {
        Write-Log "ERRO: Python não encontrado no PATH. Abortando."
        exit 1
    }
}
Write-Log "Python: $($py.Source)"

# 2) Pré-requisito: .env (equivale a 'AdForge configurado')
if (-not (Test-Path -LiteralPath $envFile)) {
    Write-Log "ERRO: $envFile ausente. Abortando."
    exit 1
}
Write-Log "Ambiente AdForge OK (.env presente)"

# 3) Cowork/Agenda: automação é in-process (Playwright), não há daemon externo a subir.
#    Se Playwright não estiver instalado, o run.py degrada graciosamente (Agenda 'indisponível').
Write-Log "Agenda: automação in-process via Playwright (sem daemon externo)"

# 4) Força modo UTF-8 no Python (evita problemas de encoding no Task Scheduler)
$env:PYTHONUTF8      = "1"
$env:PYTHONIOENCODING = "utf-8"

# 5) Executa o loop — SEM *>> redirect.
#    Python gerencia seu próprio arquivo de log via open("a", encoding="utf-8").
#    O redirect *>> criava conflito de file handle (UTF-16 vs UTF-8) que travava o pipe.
$run = Join-Path $dir "run.py"
Write-Log "Executando: $($py.Source) $run"
try {
    & $py.Source $run
    $code = $LASTEXITCODE
    Write-Log "run.py finalizado com exit code $code"
    exit $code
} catch {
    Write-Log "ERRO ao executar run.py: $($_.Exception.Message)"
    exit 1
}
